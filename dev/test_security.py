"""Tests for security_no_dangerous_patterns: 8 rules.

The dangerous patterns no file under `scripts/` may carry, in the form each
language `scripts/` holds, Python, shell and JavaScript, spells them, plus the
argv hardening that keeps a repository-supplied string out of git's option
position.
"""

import glob
import json
import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from purlin import drift as purlin_drift  # noqa: E402
from purlin import status as purlin_status  # noqa: E402

# The three languages `scripts/` holds, the ones the anchor's rules name. Its
# tests read every file under scripts/, where all of Purlin's executable code
# lives.
SCRIPT_EXTENSIONS = ('.py', '.sh', '.js')


def _all_script_files(root=SCRIPTS_DIR, extensions=SCRIPT_EXTENSIONS):
    files = []
    for ext in extensions:
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
}

# RULE-2: the per-language opt-in to a shell.
_SHELL_FLAG_BY_EXT = {
    '.py': [('shell=True', r'shell\s*=\s*True')],
    '.js': [('shell: true', r'shell\s*:\s*true')],
}

# RULE-3: the builtin that hands a whole command line to the OS shell.
_SYSTEM_CALL_BY_EXT = {
    '.py': [('os.system(', r'os\.system\s*\(')],
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
# `=` in every language and also with `:` in JavaScript object fields. The
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
        if ext == '.js':
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
_JS_CALL = re.compile(r'\b(spawn|spawnSync|execFile|execFileSync)\s*\(')


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
        elif ext == '.js':
            for m in _JS_CALL.finditer(content):
                if not re.match(r'[^,)]*,\s*\[', content[m.end():]):
                    faults.append(f"{m.group(1)} at {where(m)} args argument "
                                  f"is not an array literal: ...{head(m)[:30]}")
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
    read: every file of the three types under the folder, found by its ending."""
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
    def test_no_py_sh_or_js_file_under_scripts_runs_a_string_as_code(self):
        files = _all_script_files(extensions=('.py', '.sh', '.js'))
        assert files, "no .py, .sh or .js file found under scripts/"
        hits = _pattern_hits(files, _DANGEROUS_BY_EXT)
        assert not hits, "\n".join(f"Found {form!r} in {path}"
                                   for path, form in hits)

    # purlin: security_no_dangerous_patterns PROOF-14
    def test_python_eval_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'x = eval(src)\n', 'eval(')

    # purlin: security_no_dangerous_patterns PROOF-22
    def test_a_python_comment_naming_eval_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.py', '# eval(src) is never called\n')], _DANGEROUS_BY_EXT)


class TestRule2OptsNoSubprocessIntoAShell:

    # purlin: security_no_dangerous_patterns PROOF-2
    def test_no_py_or_js_file_under_scripts_asks_for_a_shell(self):
        files = _all_script_files(extensions=('.py', '.js'))
        assert files, "no .py or .js file found under scripts/"
        hits = _pattern_hits(files, _SHELL_FLAG_BY_EXT, strip=False)
        assert not hits, "\n".join(f"Found {form!r} in {path}"
                                   for path, form in hits)

    # purlin: security_no_dangerous_patterns PROOF-24
    def test_python_shell_true_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'subprocess.run(argv, shell=True)\n',
                      'shell=True', _SHELL_FLAG_BY_EXT, strip=False)

    # purlin: security_no_dangerous_patterns PROOF-28
    def test_python_shell_false_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.py', 'subprocess.run(argv, shell=False)\n')],
            _SHELL_FLAG_BY_EXT, strip=False)


class TestRule3CallsNoShellBuiltin:

    # purlin: security_no_dangerous_patterns PROOF-3
    def test_no_py_file_under_scripts_calls_os_system(self):
        files = _all_script_files(extensions=('.py',))
        assert files, "no .py file found under scripts/"
        assert re.search(_SYSTEM_CALL_BY_EXT['.py'][0][1], 'os.system (cmd)')
        hits = _pattern_hits(files, _SYSTEM_CALL_BY_EXT)
        assert not hits, "\n".join(f"Found {form!r} in {path}"
                                   for path, form in hits)

    # purlin: security_no_dangerous_patterns PROOF-29
    def test_python_os_system_is_found(self, tmp_path):
        _assert_names(tmp_path, 'a.py', 'os.system(cmd)\n', 'os.system(',
                      _SYSTEM_CALL_BY_EXT)

    # purlin: security_no_dangerous_patterns PROOF-31
    def test_a_python_comment_naming_os_system_is_not_counted(self, tmp_path):
        _assert_none_counted(tmp_path, [
            ('a.py', '# os.system(cmd) is never called\n')],
            _SYSTEM_CALL_BY_EXT)


class TestRule4AssignsNoCredential:

    # purlin: security_no_dangerous_patterns PROOF-4
    def test_no_py_sh_or_js_file_under_scripts_assigns_a_credential(self):
        files = _all_script_files(extensions=('.py', '.sh', '.js'))
        assert files, "no .py, .sh or .js file found under scripts/"
        hits = _credential_hits(files)
        assert not hits, "\n".join(f"Found a credential in {path}: {matches}"
                                   for path, matches in hits)

    # purlin: security_no_dangerous_patterns PROOF-7
    def test_an_api_key_given_with_an_equals_sign_is_found(self, tmp_path):
        _assert_each_credential_named(tmp_path, [
            ('a.py', 'API_KEY = "abc"\n', 'API_KEY')])

    # purlin: security_no_dangerous_patterns PROOF-34
    def test_a_file_named_test_is_not_counted(self, tmp_path):
        _assert_no_credential_counted(tmp_path, [
            ('test_a.py', 'password = "x"\n')])


class TestRule5LaunchesWithAnArgumentVector:

    # purlin: security_no_dangerous_patterns PROOF-5
    def test_no_launch_in_a_py_or_js_file_under_scripts_is_handed_a_command_string(self):
        files = _all_script_files(extensions=('.py', '.js'))
        assert files, "no .py or .js file found under scripts/"
        faults = _launch_faults(files)
        assert not faults, "\n".join(faults)

    # purlin: security_no_dangerous_patterns PROOF-35
    def test_python_run_given_a_string_is_found(self, tmp_path):
        _assert_each_launch_found(tmp_path, [
            ('a.py', 'subprocess.run("git status")\n')])

    # purlin: security_no_dangerous_patterns PROOF-36
    def test_python_run_given_a_list_is_not_counted(self, tmp_path):
        _assert_no_launch_counted(tmp_path, [
            ('a.py', 'subprocess.run(["git", "status"])\n')])


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
        json.dumps({'version': '1.0.0', 'tests': []}))
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


class TestGitArgvHardening:
    """RULE-6, RULE-7 and RULE-8: nothing repository-supplied reaches git in
    option position."""

    # purlin: security_no_dangerous_patterns PROOF-6
    def test_a_source_beginning_with_a_dash_is_refused(self, tmp_path,
                                                       monkeypatch):
        _assert_refused(tmp_path, monkeypatch, 'evil_policy', EVIL_SOURCE,
                        'evil_policy: anchor source refused. Its > Source: '
                        'line begins with "-". Run purlin:spec evil_policy.')

    # purlin: security_no_dangerous_patterns PROOF-47
    def test_a_source_naming_the_ext_transport_is_refused(self, tmp_path,
                                                          monkeypatch):
        _assert_refused(tmp_path, monkeypatch, 'ext_policy', EXT_SOURCE,
                        'ext_policy: anchor source refused. Its > Source: '
                        'line names an ext:: transport. Run purlin:spec '
                        'ext_policy.')

    # purlin: security_no_dangerous_patterns PROOF-48
    def test_a_source_naming_the_fd_transport_is_refused(self, tmp_path,
                                                         monkeypatch):
        _assert_refused(tmp_path, monkeypatch, 'fd_policy', FD_SOURCE,
                        'fd_policy: anchor source refused. Its > Source: line '
                        'names an fd:: transport. Run purlin:spec fd_policy.')

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
    def test_drift_hands_rev_list_diff_and_show_each_commit_after_end_of_options(
            self, tmp_path, monkeypatch):
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
