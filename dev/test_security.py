"""Tests for security_no_dangerous_patterns: 8 rules.

FORBIDDEN pattern checks across all executable Purlin framework code, plus the
argv-hardening rule that keeps repository-supplied strings out of git's option
position.
"""

import glob
import json
import os
import re
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from purlin import drift as purlin_drift  # noqa: E402
from purlin import status as purlin_status  # noqa: E402

# Every executable language the anchor's rules name. Its > Scope: names the
# three that scripts/ holds; the other three are read wherever they appear.
SCRIPT_EXTENSIONS = ('.py', '.sh', '.js', '.ts', '.php', '.cs')


def _all_script_files(root=SCRIPTS_DIR):
    files = []
    for ext in SCRIPT_EXTENSIONS:
        files.extend(glob.glob(os.path.join(root, '**', '*' + ext),
                               recursive=True))
    return files


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


# Whole-line comment openers per language. The stripper is deliberately shallow:
# it drops a line that is nothing but a comment and nothing else, so a dangerous
# call sharing a line with code is still matched.
_COMMENT_OPENERS = {
    '.py': ('#',),
    '.sh': ('#',),
    '.js': ('//', '*', '/*'),
    '.ts': ('//', '*', '/*'),
    '.php': ('//', '#', '*', '/*'),
    '.cs': ('//', '*', '/*'),
}


def _strip_comments(content, ext):
    """Remove whole-line comments to avoid false positives."""
    openers = _COMMENT_OPENERS.get(ext, ())
    lines = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if openers and stripped.startswith(openers):
            continue
        lines.append(line)
    return '\n'.join(lines)


def _ext(path):
    return os.path.splitext(path)[1]


# RULE-1: dynamic code and command strings, in the form each language spells
# it. Each form carries the name a finding reports.
_DANGEROUS_BY_EXT = {
    '.py': [('eval(', r'\beval\s*\('), ('exec(', r'\bexec\s*\(')],
    # eval in command position: a line's start (indented or not), after ;, &,
    # |, ( or $( or !, or after a keyword that runs a command next.
    '.sh': [('eval', r'(^|[;&|(!{]|\b(if|then|else|elif|do|while|until|time|'
                     r'command|builtin|exec))\s*eval\b'),
            ('backticks', r'`[^`]*`')],
    '.js': [('eval(', r'\beval\s*\('), ('new Function(', r'new\s+Function\s*\('),
            ('execSync(', r'\bexecSync\s*\('),
            ('child_process.exec(', r'child_process\s*\.\s*exec\s*\(')],
    '.php': [('eval(', r'\beval\s*\('), ('exec(', r'\bexec\s*\('),
             ('shell_exec(', r'\bshell_exec\s*\('), ('backticks', r'`[^`]*`')],
}
_DANGEROUS_BY_EXT['.ts'] = _DANGEROUS_BY_EXT['.js']

# RULE-2: the per-language opt-in to a shell.
_SHELL_FLAG_BY_EXT = {
    '.py': [('shell=True', r'shell\s*=\s*True')],
    '.js': [('shell: true', r'shell\s*:\s*true')],
    '.ts': [('shell: true', r'shell\s*:\s*true')],
    '.cs': [('UseShellExecute = true', r'UseShellExecute\s*=\s*true')],
}

# RULE-3: the builtins that hand a whole command line to the OS shell.
_SYSTEM_CALL_BY_EXT = {
    '.py': [('os.system(', r'os\.system\s*\(')],
    '.php': [('system(', r'\bsystem\s*\('), ('passthru(', r'\bpassthru\s*\(')],
}


def _pattern_hits(paths, table, strip=True):
    """`[(path, form), ...]` for each form of `table` a file holds."""
    hits = []
    for path in paths:
        ext = _ext(path)
        content = _read(path)
        if strip:
            content = _strip_comments(content, ext)
        for form, pattern in table.get(ext, []):
            if re.search(pattern, content, re.MULTILINE):
                hits.append((path, form))
    return hits


# RULE-4: a quoted value given to a name containing a credential word, with
# `=` in every language and also with `:` in JS and TS object fields. The
# group is the whole name, so a finding says which name matched.
_CRED_NAME = r'(\w*(?:password|secret|api_key|token)\w*)'
_CRED_ASSIGN = re.compile(
    _CRED_NAME + r'\s*=\s*["\'][^"\']+["\']', re.IGNORECASE)
_CRED_FIELD = re.compile(
    _CRED_NAME + r'\s*:\s*["\'][^"\']+["\']', re.IGNORECASE)


def _credential_hits(paths):
    hits = []
    for path in paths:
        if os.path.basename(path).startswith('test_'):
            continue
        ext = _ext(path)
        content = _strip_comments(_read(path), ext)
        matches = _CRED_ASSIGN.findall(content)
        if ext in ('.js', '.ts'):
            matches += _CRED_FIELD.findall(content)
        if matches:
            hits.append((path, matches))
    return hits


# RULE-5: the launch forms and what their argument vector must look like.
_PY_LAUNCHES = ('run', 'call', 'check_call', 'check_output')
_PY_CALL = re.compile(r'subprocess\.(run|call|check_call|check_output)\s*\(')
# `Popen` is held to a list written in place: its first argument opens `[`.
_PY_POPEN = re.compile(r'subprocess\.Popen\s*\(')
_PY_STRING_ARG = re.compile(
    r'subprocess\.(run|call|check_call|check_output|Popen)\s*\(\s*[fbr]?["\']')
_PY_IMPORTED = re.compile(r'^\s*from\s+subprocess\s+import\s+\(?([\w\s,]+)',
                          re.MULTILINE)
_PHP_CALL = re.compile(r'\bproc_open\s*\(')
_JS_CALL = re.compile(r'\b(spawn|spawnSync|execFile|execFileSync)\s*\(')
_CS_STRING_ARGS = re.compile(r'\.Arguments\s*=\s*"')


def _launch_faults(paths):
    """One message per launch that is not handed an argument vector."""
    faults = []
    for path in paths:
        ext = _ext(path)
        content = _strip_comments(_read(path), ext)

        def where(m):
            return f"{path}:{content[:m.start()].count(chr(10)) + 1}"

        def head(m):
            return content[m.end():m.end() + 50].lstrip()

        if ext == '.py':
            if _PY_STRING_ARG.findall(content):
                faults.append(f"Found subprocess with string arg in {path}")
            calls = list(_PY_CALL.finditer(content))
            popens = list(_PY_POPEN.finditer(content))
            # A launch imported by name, under its own name or an alias.
            for imported in _PY_IMPORTED.findall(content):
                for entry in (e.split() for e in imported.split(',')):
                    if not entry:
                        continue
                    bare = re.compile(r'(?<![\w.])%s\s*\(' % entry[-1])
                    if entry[0] in _PY_LAUNCHES:
                        calls += bare.finditer(content)
                    elif entry[0] == 'Popen':
                        popens += bare.finditer(content)
            for m in calls:
                if not head(m).startswith(('[', '*')):
                    faults.append(f"subprocess call at {where(m)} first arg is "
                                  f"not a list literal: ...{head(m)[:30]}")
            for m in popens:
                if not head(m).startswith('['):
                    faults.append(f"Popen at {where(m)} first arg is not a "
                                  f"list written in place: ...{head(m)[:30]}")
        elif ext == '.php':
            for m in _PHP_CALL.finditer(content):
                if not head(m).startswith('['):
                    faults.append(f"proc_open at {where(m)} first arg is not "
                                  f"an array literal: ...{head(m)[:30]}")
        elif ext in ('.js', '.ts'):
            for m in _JS_CALL.finditer(content):
                if not re.match(r'[^,)]*,\s*\[', content[m.end():]):
                    faults.append(f"{m.group(1)} at {where(m)} args argument "
                                  f"is not an array literal: ...{head(m)[:30]}")
        elif ext == '.cs':
            if _CS_STRING_ARGS.findall(content):
                faults.append(f"Found ProcessStartInfo.Arguments string "
                              f"assignment in {path}")
    return faults


def _plant_each(root, samples):
    """Write each `(name, text)` to a folder of its own under `root`, and
    return the paths in the order given."""
    paths = []
    for index, (name, text) in enumerate(samples):
        folder = os.path.join(str(root), str(index))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        paths.append(path)
    return paths


def _forms_found(root, samples, table, strip=True):
    """`{path: {form, ...}}` for planted samples, read the way `scripts/` is
    read: every file of the six types under the folder, found by its ending."""
    paths = _plant_each(root, samples)
    found = {path: set() for path in paths}
    for path, form in _pattern_hits(_all_script_files(str(root)), table, strip):
        found[path].add(form)
    return [(sample, found[path]) for sample, path in zip(samples, paths)]


def _assert_each_names(root, samples, table, strip=True):
    """Every planted `(name, text, form)` is found once, naming that form."""
    results = _forms_found(root, [(n, t) for n, t, _ in samples], table, strip)
    for (name, text, form), (_, forms) in zip(samples, results):
        assert forms == {form}, (
            f"a planted {name} holding {text!r} should be found as {form!r}; "
            f"found {sorted(forms)}")


def _assert_names(root, name, text, form, table=_DANGEROUS_BY_EXT,
                  strip=True):
    """One planted file `name` holding `text` is found once, naming `form`."""
    _assert_each_names(root, [(name, text, form)], table, strip)


def _assert_none_counted(root, samples, table, strip=True):
    """No planted `(name, text)` is found."""
    for (name, text), forms in _forms_found(root, samples, table, strip):
        assert not forms, f"{name} holding {text!r} was counted as {sorted(forms)}"


def _assert_each_launch_found(root, samples):
    """Each planted launch is found, and its finding names its file."""
    for path, (name, text) in zip(_plant_each(root, samples), samples):
        faults = _launch_faults([path])
        assert faults, f"{name} holding {text!r} went unfound"
        assert all(path in fault for fault in faults), faults


def _assert_launch_found_at(root, name, text, line):
    """A planted launch is found, and the finding names its file and line."""
    path = _plant_each(root, [(name, text)])[0]
    faults = _launch_faults([path])
    assert any(f"{path}:{line}" in fault for fault in faults), (
        f"{name} holding {text!r} was not found at line {line}: {faults}")


def _assert_no_launch_counted(root, samples):
    for path, (name, text) in zip(_plant_each(root, samples), samples):
        faults = _launch_faults([path])
        assert not faults, f"{name} holding {text!r} was counted: {faults}"


def _assert_each_credential_named(root, samples):
    """Each planted `(name, text, matched)` is found, naming its file and the
    name that matched."""
    paths = _plant_each(root, [(n, t) for n, t, _ in samples])
    for path, (name, text, matched) in zip(paths, samples):
        assert _credential_hits([path]) == [(path, [matched])], (
            name, text, _credential_hits([path]))


def _assert_no_credential_counted(root, samples):
    for path, (name, text) in zip(_plant_each(root, samples), samples):
        assert not _credential_hits([path]), f"{name} holding {text!r} was counted"


class TestRule1RunsNoStringAsCode:

    # purlin: security_no_dangerous_patterns PROOF-1
    def test_no_file_under_scripts_runs_a_string_as_code(self):
        hits = _pattern_hits(_all_script_files(), _DANGEROUS_BY_EXT)
        assert not hits, "\n".join(f"Found {form!r} in {path}"
                                   for path, form in hits)

    # purlin: security_no_dangerous_patterns PROOF-14
    def test_python_eval_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'x = eval(src)\n', 'eval(')

    # purlin: security_no_dangerous_patterns PROOF-49
    def test_python_exec_with_a_space_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'exec (src)\n', 'exec(')

    # purlin: security_no_dangerous_patterns PROOF-50
    def test_python_eval_before_a_trailing_comment_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py',
                      'x = eval(src)  # only a comment follows\n', 'eval(')

    # purlin: security_no_dangerous_patterns PROOF-15
    def test_shell_eval_at_the_start_of_a_line_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.sh', 'eval "$cmd"\n', 'eval')

    # purlin: security_no_dangerous_patterns PROOF-51
    def test_shell_eval_indented_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.sh', '    eval "$cmd"\n', 'eval')

    # purlin: security_no_dangerous_patterns PROOF-52
    def test_shell_eval_after_if_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.sh', 'if eval "$cmd"; then :; fi\n', 'eval')

    # purlin: security_no_dangerous_patterns PROOF-53
    def test_shell_eval_in_a_substitution_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.sh', 'out=$(eval "$cmd")\n', 'eval')

    # purlin: security_no_dangerous_patterns PROOF-54
    def test_shell_eval_after_and_and_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.sh', 'true && eval "$cmd"\n', 'eval')

    # purlin: security_no_dangerous_patterns PROOF-16
    def test_shell_backticks_are_found(self, tmp_path):
        _assert_names(tmp_path, 'a.sh', 'out=`date`\n', 'backticks')

    # purlin: security_no_dangerous_patterns PROOF-17
    def test_javascript_eval_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.js', 'eval(src);\n', 'eval(')

    # purlin: security_no_dangerous_patterns PROOF-55
    def test_javascript_new_function_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.js', 'const f = new Function(src);\n',
                      'new Function(')

    # purlin: security_no_dangerous_patterns PROOF-56
    def test_javascript_exec_sync_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.js', 'execSync(cmd);\n', 'execSync(')

    # purlin: security_no_dangerous_patterns PROOF-57
    def test_javascript_child_process_exec_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.js', 'child_process.exec(cmd);\n',
                      'child_process.exec(')

    # purlin: security_no_dangerous_patterns PROOF-58
    def test_javascript_eval_before_a_trailing_comment_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.js',
                      'eval(src); // only a comment follows\n', 'eval(')

    # purlin: security_no_dangerous_patterns PROOF-18
    def test_typescript_eval_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.ts', 'eval(src);\n', 'eval(')

    # purlin: security_no_dangerous_patterns PROOF-59
    def test_typescript_new_function_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.ts', 'const f = new Function(src);\n',
                      'new Function(')

    # purlin: security_no_dangerous_patterns PROOF-60
    def test_typescript_exec_sync_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.ts', 'execSync(cmd);\n', 'execSync(')

    # purlin: security_no_dangerous_patterns PROOF-61
    def test_typescript_child_process_exec_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.ts', 'child_process.exec(cmd);\n',
                      'child_process.exec(')

    # purlin: security_no_dangerous_patterns PROOF-19
    def test_php_eval_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.php', '<?php eval($src);\n', 'eval(')

    # purlin: security_no_dangerous_patterns PROOF-62
    def test_php_exec_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.php', '<?php exec($cmd);\n', 'exec(')

    # purlin: security_no_dangerous_patterns PROOF-63
    def test_php_shell_exec_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.php', '<?php shell_exec($cmd);\n',
                      'shell_exec(')

    # purlin: security_no_dangerous_patterns PROOF-64
    def test_php_backticks_are_found(self, tmp_path):
        _assert_names(tmp_path, 'a.php', '<?php $o = `ls`;\n', 'backticks')

    # purlin: security_no_dangerous_patterns PROOF-22
    def test_a_python_comment_naming_eval_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.py', '# eval(src) is never called\n')], _DANGEROUS_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-65
    def test_a_shell_comment_naming_eval_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.sh', '  # eval "$cmd" is never run\n')], _DANGEROUS_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-66
    def test_a_javascript_comment_naming_eval_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.js', '// eval(src) is never called\n')], _DANGEROUS_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-23
    def test_a_python_word_containing_eval_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [('a.py', 'x = evaluate(src)\n')],
                             _DANGEROUS_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-67
    def test_a_shell_word_containing_eval_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [('a.sh', 'run_evaluation "$x"\n')],
                             _DANGEROUS_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-68
    def test_a_javascript_word_containing_eval_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.js', 'const x = evaluate(src);\n')], _DANGEROUS_BY_EXT)


class TestRule2OptsNoSubprocessIntoAShell:

    # purlin: security_no_dangerous_patterns PROOF-2
    def test_no_file_under_scripts_asks_for_a_shell(self):
        hits = _pattern_hits(_all_script_files(), _SHELL_FLAG_BY_EXT, strip=False)
        assert not hits, "\n".join(f"Found {form!r} in {path}"
                                   for path, form in hits)

    # purlin: security_no_dangerous_patterns PROOF-24
    def test_python_shell_true_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'subprocess.run(argv, shell=True)\n',
                      'shell=True', _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-69
    def test_python_shell_true_with_spaces_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'subprocess.run(argv, shell = True)\n',
                      'shell=True', _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-25
    def test_a_comment_writing_shell_true_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', '# subprocess.run(argv, shell=True)\n',
                      'shell=True', _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-26
    def test_javascript_shell_true_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.js', 'spawn("ls", [], { shell: true });\n',
                      'shell: true', _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-70
    def test_typescript_shell_true_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.ts', 'spawn("ls", [], { shell :true });\n',
                      'shell: true', _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-27
    def test_csharp_use_shell_execute_true_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.cs', 'psi.UseShellExecute = true;\n',
                      'UseShellExecute = true', _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-71
    def test_csharp_use_shell_execute_true_unspaced_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.cs', 'psi.UseShellExecute=true;\n',
                      'UseShellExecute = true', _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-28
    def test_python_shell_false_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.py', 'subprocess.run(argv, shell=False)\n')],
            _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-72
    def test_javascript_shell_false_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.js', 'spawn("ls", [], { shell: false });\n')],
            _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-73
    def test_csharp_use_shell_execute_false_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.cs', 'psi.UseShellExecute = false;\n')],
            _SHELL_FLAG_BY_EXT, strip=False)


class TestRule3CallsNoShellBuiltin:

    # purlin: security_no_dangerous_patterns PROOF-3
    def test_no_file_under_scripts_calls_the_shell_builtin(self):
        hits = _pattern_hits(_all_script_files(), _SYSTEM_CALL_BY_EXT)
        assert not hits, "\n".join(f"Found {form!r} in {path}"
                                   for path, form in hits)

    # purlin: security_no_dangerous_patterns PROOF-29
    def test_python_os_system_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'os.system(cmd)\n', 'os.system(',
                      _SYSTEM_CALL_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-74
    def test_python_os_system_with_a_space_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'os.system (cmd)\n', 'os.system(',
                      _SYSTEM_CALL_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-30
    def test_php_system_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.php', '<?php system($cmd);\n', 'system(',
                      _SYSTEM_CALL_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-75
    def test_php_passthru_with_a_space_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.php', '<?php passthru ($cmd);\n',
                      'passthru(', _SYSTEM_CALL_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-31
    def test_a_python_comment_naming_os_system_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.py', '# os.system(cmd) is never called\n')],
            _SYSTEM_CALL_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-76
    def test_a_php_comment_naming_system_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.php', '<?php\n// system($cmd) is never called\n')],
            _SYSTEM_CALL_BY_EXT)


class TestRule4AssignsNoCredential:

    # purlin: security_no_dangerous_patterns PROOF-4
    def test_no_file_under_scripts_assigns_a_credential(self):
        hits = _credential_hits(_all_script_files())
        assert not hits, "\n".join(f"Found a credential in {path}: {matches}"
                                   for path, matches in hits)

    # purlin: security_no_dangerous_patterns PROOF-7
    def test_an_api_key_given_with_an_equals_sign_is_found(self, tmp_path):
        _assert_each_credential_named(tmp_path, [
            ('a.py', 'API_KEY = "abc"\n', 'API_KEY')])

    # purlin: security_no_dangerous_patterns PROOF-77
    def test_a_password_in_single_quotes_is_found(self, tmp_path):
        _assert_each_credential_named(tmp_path, [
            ('a.py', "db_password='x'\n", 'db_password')])

    # purlin: security_no_dangerous_patterns PROOF-78
    def test_a_name_beginning_with_token_is_found(self, tmp_path):
        _assert_each_credential_named(tmp_path, [
            ('a.py', 'TOKEN_NAME = "abc"\n', 'TOKEN_NAME')])

    # purlin: security_no_dangerous_patterns PROOF-79
    def test_a_token_in_a_shell_file_is_found(self, tmp_path):
        _assert_each_credential_named(tmp_path, [
            ('a.sh', 'GITHUB_TOKEN="abc"\n', 'GITHUB_TOKEN')])

    # purlin: security_no_dangerous_patterns PROOF-32
    def test_a_password_field_in_javascript_is_found(self, tmp_path):
        _assert_each_credential_named(tmp_path, [
            ('a.js', 'const cfg = { password: "x" };\n', 'password')])

    # purlin: security_no_dangerous_patterns PROOF-80
    def test_a_token_field_in_typescript_is_found(self, tmp_path):
        _assert_each_credential_named(tmp_path, [
            ('a.ts', 'const auth = { Token : "abc" };\n', 'Token')])

    # purlin: security_no_dangerous_patterns PROOF-8
    def test_an_empty_api_key_is_not_counted(self, tmp_path):
        _assert_no_credential_counted(tmp_path, [('a.py', 'API_KEY = ""\n')])

    # purlin: security_no_dangerous_patterns PROOF-81
    def test_an_empty_password_in_a_python_dict_is_not_counted(self, tmp_path):
        _assert_no_credential_counted(tmp_path, [
            ('a.py', 'row = {"password": ""}\n')])

    # purlin: security_no_dangerous_patterns PROOF-82
    def test_an_empty_password_field_in_javascript_is_not_counted(
            self, tmp_path):
        _assert_no_credential_counted(tmp_path, [
            ('a.js', 'const cfg = { password: "" };\n')])

    # purlin: security_no_dangerous_patterns PROOF-33
    def test_a_comparison_is_not_counted(self, tmp_path):
        _assert_no_credential_counted(tmp_path, [
            ('a.py', 'if token == "x":\n    pass\n')])

    # purlin: security_no_dangerous_patterns PROOF-34
    def test_a_file_named_test_is_not_counted(self, tmp_path):
        _assert_no_credential_counted(tmp_path, [
            ('test_a.py', 'password = "x"\n')])


class TestRule5LaunchesWithAnArgumentVector:

    # purlin: security_no_dangerous_patterns PROOF-5
    def test_no_launch_under_scripts_is_handed_a_command_string(self):
        faults = _launch_faults(_all_script_files())
        assert not faults, "\n".join(faults)

    # purlin: security_no_dangerous_patterns PROOF-35
    def test_python_run_given_a_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.py', 'subprocess.run("git status")\n')])

    # purlin: security_no_dangerous_patterns PROOF-83
    def test_python_run_given_a_name_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [('a.py', 'subprocess.run(cmd)\n')])

    # purlin: security_no_dangerous_patterns PROOF-36
    def test_python_run_given_a_list_is_not_counted(self, tmp_path):
        _assert_no_launch_counted(tmp_path, [
            ('a.py', 'subprocess.run(["git", "status"])\n')])

    # purlin: security_no_dangerous_patterns PROOF-84
    def test_python_run_given_a_star_is_not_counted(self, tmp_path):
        _assert_no_launch_counted(tmp_path, [('a.py', 'subprocess.run(*argv)\n')])

    # purlin: security_no_dangerous_patterns PROOF-37
    def test_python_popen_given_a_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.py', 'subprocess.Popen("git status")\n')])

    # purlin: security_no_dangerous_patterns PROOF-85
    def test_python_popen_given_an_f_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.py', 'subprocess.Popen(f"git {verb}")\n')])

    # purlin: security_no_dangerous_patterns PROOF-38
    def test_python_popen_given_a_name_is_found_with_its_line(self, tmp_path):
        _assert_launch_found_at(tmp_path, 'a.py',
                                'import subprocess\n\n'
                                'subprocess.Popen(command, cwd=root)\n', 3)

    # purlin: security_no_dangerous_patterns PROOF-86
    def test_python_popen_given_a_star_is_found_with_its_line(self, tmp_path):
        _assert_launch_found_at(tmp_path, 'a.py',
                                'import subprocess\n\n'
                                'subprocess.Popen(*argv)\n', 3)

    # purlin: security_no_dangerous_patterns PROOF-87
    def test_python_popen_given_a_list_written_in_place_is_not_counted(
            self, tmp_path):
        _assert_no_launch_counted(tmp_path, [
            ('a.py', 'subprocess.Popen([*command], cwd=root)\n')])

    # purlin: security_no_dangerous_patterns PROOF-39
    def test_run_imported_by_name_given_a_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.py', 'from subprocess import run\nrun("git status")\n')])

    # purlin: security_no_dangerous_patterns PROOF-88
    def test_a_launch_imported_under_an_alias_given_a_string_is_found(
            self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.py', 'from subprocess import check_output as co, call\n'
                     'co("git status")\n')])

    # purlin: security_no_dangerous_patterns PROOF-89
    def test_popen_imported_by_name_given_a_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.py', 'from subprocess import Popen\nPopen("git status")\n')])

    # purlin: security_no_dangerous_patterns PROOF-40
    def test_a_launch_imported_by_name_given_a_list_is_not_counted(
            self, tmp_path):
        _assert_no_launch_counted(tmp_path, [
            ('a.py', 'from subprocess import run\nrun(["git", "status"])\n')])

    # purlin: security_no_dangerous_patterns PROOF-41
    def test_php_proc_open_given_a_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.php', '<?php proc_open("ls -la", $spec, $pipes);\n')])

    # purlin: security_no_dangerous_patterns PROOF-42
    def test_php_proc_open_given_an_array_is_not_counted(self, tmp_path):
        _assert_no_launch_counted(tmp_path, [
            ('a.php', '<?php proc_open(["ls", "-la"], $spec, $pipes);\n')])

    # purlin: security_no_dangerous_patterns PROOF-43
    def test_javascript_spawn_given_a_string_argument_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [('a.js', 'spawn("ls", "-la");\n')])

    # purlin: security_no_dangerous_patterns PROOF-90
    def test_javascript_spawn_given_one_command_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [('a.js', 'spawn("ls -la");\n')])

    # purlin: security_no_dangerous_patterns PROOF-91
    def test_typescript_exec_file_sync_given_a_name_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [('a.ts', 'execFileSync(cmd);\n')])

    # purlin: security_no_dangerous_patterns PROOF-44
    def test_javascript_spawn_with_an_args_array_is_not_counted(self, tmp_path):
        _assert_no_launch_counted(tmp_path, [('a.js', 'spawn("ls", ["-la"]);\n')])

    # purlin: security_no_dangerous_patterns PROOF-45
    def test_csharp_arguments_set_to_a_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.cs', 'psi.Arguments = "status --short";\n')])

    # purlin: security_no_dangerous_patterns PROOF-46
    def test_csharp_argument_list_is_not_counted(self, tmp_path):
        _assert_no_launch_counted(tmp_path, [
            ('a.cs', 'psi.ArgumentList.Add("status");\n')])


# Each hostile source ends in `.git`, so it reads as a repository and would
# be handed to `git ls-remote` if the refusal did not stop it first. The two
# transports are the ones git will run a command for; RULE-8 refuses both
# before any subprocess starts, not after quoting them safely.
EVIL_SOURCE = '--upload-pack=/bin/echo /tmp/policy.git'
EXT_SOURCE = 'ext::sh -c "touch /tmp/purlin-pwned" /tmp/policy.git'
FD_SOURCE = 'fd::7/policy.git'


def _git(args, cwd=None, check=True):
    return subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                          text=True, check=check)


def _make_bare_repo(bare_path, work_path):
    """Create a bare repo with one commit. Returns its HEAD SHA."""
    _git(['-c', 'init.defaultBranch=main', 'init', '--bare', '-q', bare_path])
    _git(['clone', '-q', bare_path, work_path])
    with open(os.path.join(work_path, 'policy.md'), 'w',
              encoding='utf-8') as f:
        f.write('# policy\n')
    _git(['config', 'user.email', 'test@test.com'], cwd=work_path)
    _git(['config', 'user.name', 'Test'], cwd=work_path)
    _git(['add', '-A'], cwd=work_path)
    _git(['commit', '-q', '-m', 'initial policy'], cwd=work_path)
    _git(['push', '-q', 'origin', 'HEAD:refs/heads/main'], cwd=work_path)
    return _git(['rev-parse', 'HEAD'], cwd=work_path).stdout.strip()


def _write_anchor(anchors_dir, name, source, pinned):
    with open(os.path.join(anchors_dir, name + '.md'), 'w',
              encoding='utf-8') as f:
        f.write(
            f'# Anchor: {name}\n\n'
            f'> Source: {source}\n'
            f'> Pinned: {pinned}\n'
            f'> Description: Anchor under test.\n\n'
            '## Rules\n\n'
            '- RULE-1: External constraint one\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Call it and verify it returns 1\n'
        )


_SHA = re.compile(r'\b[0-9a-f]{40}\b')


def _record_launches(monkeypatch):
    """Record the argv of every process started through the subprocess module.

    It records at the process itself, so a launch through `run`, `call`,
    `check_output` or `Popen` directly is recorded alike.
    """
    calls = []
    real_popen = subprocess.Popen

    class Recording(real_popen):
        def __init__(self, args, *rest, **kwargs):
            calls.append(list(args) if isinstance(args, (list, tuple)) else [args])
            super().__init__(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', Recording)
    return calls


def _project(tmp_path, sources=()):
    """A committed project holding one anchor per `(name, source)`."""
    project = tmp_path / 'project'
    purlin_dir = project / '.purlin'
    purlin_dir.mkdir(parents=True)
    (purlin_dir / 'config.json').write_text(
        json.dumps({'version': '1.0.0', 'project_name': 'spy'}))
    anchors = project / 'specs' / '_anchors'
    anchors.mkdir(parents=True)
    for name, source in sources:
        _write_anchor(str(anchors), name, source,
                      '1234567890abcdef1234567890abcdef12345678')
    _git(['-c', 'init.defaultBranch=main', 'init', '-q'], cwd=str(project))
    _git(['config', 'user.email', 'test@test.com'], cwd=str(project))
    _git(['config', 'user.name', 'Test'], cwd=str(project))
    _git(['add', '-A'], cwd=str(project))
    _git(['commit', '-q', '-m', 'chore: project under test'], cwd=str(project))
    return project


def _branch_changing_a_spec(project):
    """A branch and two commits changing a spec, so drift measures a range from
    the checkout and hands git revisions: a count, a diff, a show."""
    _git(['checkout', '-q', '-b', 'topic'], cwd=str(project))
    spec = project / 'specs' / 'demo' / 'demo.md'
    spec.parent.mkdir(parents=True)
    for body in ('- RULE-1: One\n', '- RULE-1: One\n- RULE-2: Two\n'):
        spec.write_text('# Feature: demo\n\n## Rules\n\n' + body)
        _git(['add', '-A'], cwd=str(project))
        _git(['commit', '-q', '-m', 'spec(demo): rules'], cwd=str(project))


def _every_launch_of(monkeypatch, read):
    """`(result, argvs)` of `read()`, every command it started."""
    calls = _record_launches(monkeypatch)
    result = read()
    monkeypatch.undo()
    return result, calls


def _launched_by(monkeypatch, read):
    """`(result, git argvs)` of `read()`, every git command it started."""
    result, calls = _every_launch_of(monkeypatch, read)
    return result, [argv for argv in calls if argv and argv[0] == 'git']


def _status_of_a_hostile_source(tmp_path, monkeypatch, anchor, source):
    """`(status lines, every command started)` for a project whose one anchor
    names `source`."""
    project = _project(tmp_path, [(anchor, source)])
    text, calls = _every_launch_of(
        monkeypatch, lambda: purlin_status.sync_status(str(project)))
    return text.splitlines(), calls


def _assert_refused(tmp_path, monkeypatch, anchor, source, line):
    lines, calls = _status_of_a_hostile_source(tmp_path, monkeypatch, anchor,
                                               source)
    assert calls, "the status read started no command at all"
    carrying = [argv for argv in calls if any(source in str(a) for a in argv)]
    assert not carrying, (
        f"{source!r} reached a command; RULE-8 refuses it before any "
        f"subprocess starts: {carrying}")
    assert line in lines, f"the status has no line {line!r}:\n" + "\n".join(lines)


def _is_revision(arg):
    """A commit, a range or a `<commit>:<path>`; the fixed word `HEAD` alone,
    which Purlin writes itself, is left out."""
    if arg.startswith('-') or arg == 'HEAD':
        return False
    return bool(_SHA.search(arg)) or 'HEAD' in arg


def _is_path_operand(arg):
    """A path the tests hand git here: `specs/` or a spec path under it."""
    if _SHA.search(arg):
        return False  # `<sha>:specs/x.md` is a revision
    return arg == 'specs/' or arg.startswith('specs/') or arg.endswith('.md')


def _each_revision_follows_end_of_options(calls):
    """Every git argv carrying a revision has `--end-of-options` just before it."""
    for argv in calls:
        revisions = [i for i, a in enumerate(argv) if _is_revision(a)]
        if revisions:
            assert argv[min(revisions) - 1] == '--end-of-options', (
                f"a revision reaches git with no --end-of-options immediately "
                f"before it: {argv}")


class TestGitArgvHardening:
    """RULE-6, RULE-7 and RULE-8: nothing repository-supplied reaches git in
    option position."""

    # purlin: security_no_dangerous_patterns PROOF-6
    def test_a_source_beginning_with_a_dash_is_refused(self, tmp_path,
                                                       monkeypatch):
        _assert_refused(tmp_path, monkeypatch, 'evil_policy', EVIL_SOURCE,
                        'evil_policy: (source rejected: begins with "-")')

    # purlin: security_no_dangerous_patterns PROOF-47
    def test_a_source_naming_the_ext_transport_is_refused(self, tmp_path,
                                                          monkeypatch):
        _assert_refused(tmp_path, monkeypatch, 'ext_policy', EXT_SOURCE,
                        'ext_policy: (source rejected: names an ext:: '
                        'transport)')

    # purlin: security_no_dangerous_patterns PROOF-48
    def test_a_source_naming_the_fd_transport_is_refused(self, tmp_path,
                                                         monkeypatch):
        _assert_refused(tmp_path, monkeypatch, 'fd_policy', FD_SOURCE,
                        'fd_policy: (source rejected: names an fd:: transport)')

    # purlin: security_no_dangerous_patterns PROOF-9
    def test_a_source_reaches_ls_remote_after_end_of_options(self, tmp_path,
                                                             monkeypatch):
        bare = str(tmp_path / 'good-policy.git')
        _make_bare_repo(bare, str(tmp_path / 'good-work'))
        project = _project(tmp_path, [('good_policy', bare)])
        _text, calls = _launched_by(
            monkeypatch, lambda: purlin_status.sync_status(str(project)))
        ls_remotes = [a for a in calls if len(a) >= 2 and a[1] == 'ls-remote']
        assert ls_remotes, "no git ls-remote captured"
        for argv in ls_remotes:
            assert bare in argv, f"expected the repository in {argv}"
            at = argv.index(bare)
            assert at > 0 and argv[at - 1] == '--end-of-options', (
                f"--end-of-options does not precede the repository: {argv}")

    # purlin: security_no_dangerous_patterns PROOF-10
    def test_every_revision_follows_end_of_options(self, tmp_path,
                                                   monkeypatch):
        project = _project(tmp_path)
        _branch_changing_a_spec(project)
        _report, calls = _launched_by(
            monkeypatch, lambda: purlin_drift.drift(str(project)))
        took_a_revision = set()
        for argv in calls:
            revisions = [i for i, a in enumerate(argv) if _is_revision(a)]
            if not revisions:
                continue
            took_a_revision.add(argv[1])
            first = min(revisions)
            assert argv[first - 1] == '--end-of-options', (
                f"a revision reaches git with no --end-of-options immediately "
                f"before it: {argv}")
        assert {'rev-list', 'diff', 'show'} <= took_a_revision, (
            f"drift handed git no revision in some of rev-list, diff and show; "
            f"only {sorted(took_a_revision)}")

    # purlin: security_no_dangerous_patterns PROOF-12
    def test_a_date_hands_its_commit_after_end_of_options(self, tmp_path,
                                                         monkeypatch):
        project = _project(tmp_path)
        _branch_changing_a_spec(project)
        _report, calls = _launched_by(
            monkeypatch,
            lambda: purlin_drift.drift(str(project), since='2000-01-01'))
        parents = [argv for argv in calls
                   if any(a.endswith('^') and _is_revision(a) for a in argv)]
        assert parents, f"drift handed git no <commit>^: {calls}"
        _each_revision_follows_end_of_options(calls)

    # purlin: security_no_dangerous_patterns PROOF-13
    def test_a_count_hands_its_commits_after_end_of_options(self, tmp_path,
                                                          monkeypatch):
        project = _project(tmp_path)
        _branch_changing_a_spec(project)
        _report, calls = _launched_by(
            monkeypatch, lambda: purlin_drift.drift(str(project), since='1'))
        diffs = [argv for argv in calls if argv[1] == 'diff'
                 and any(_is_revision(a) for a in argv)]
        assert diffs, f"drift handed git no commit to diff from: {calls}"
        _each_revision_follows_end_of_options(calls)

    # purlin: security_no_dangerous_patterns PROOF-11
    def test_every_path_follows_a_double_dash(self, tmp_path, monkeypatch):
        project = _project(tmp_path)
        _branch_changing_a_spec(project)
        _report, calls = _launched_by(
            monkeypatch, lambda: purlin_drift.drift(str(project)))
        carried_a_path = []
        for argv in calls:
            operands = [i for i, a in enumerate(argv) if _is_path_operand(a)]
            if not operands:
                continue
            carried_a_path.append(argv)
            first = min(operands)
            assert first > 0 and argv[first - 1] == '--', (
                f"a path reaches git with no -- immediately before it, so a "
                f"path beginning with '-' would be read as an option: {argv}")
        assert carried_a_path, "no git command carried a path"
