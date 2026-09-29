"""Tests for security_no_dangerous_patterns: 6 rules.

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

# Every executable language that ships under scripts/. The anchor's > Scope:
# names exactly these six extensions; keep the two in step.
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


# RULE-1: dynamic code and command strings, in the form each language spells it.
_DANGEROUS_BY_EXT = {
    '.py': [r'\beval\s*\(', r'\bexec\s*\('],
    # eval in command position: a line's start (indented or not), after ;, &,
    # |, ( or $( or !, or after a keyword that runs a command next.
    '.sh': [r'(^|[;&|(!{]|\b(if|then|else|elif|do|while|until|time|command|'
            r'builtin|exec))\s*eval\b', r'`[^`]*`'],
    '.js': [r'\beval\s*\(', r'new\s+Function\s*\(', r'\bexecSync\s*\(',
            r'child_process\s*\.\s*exec\s*\('],
    '.ts': [r'\beval\s*\(', r'new\s+Function\s*\(', r'\bexecSync\s*\(',
            r'child_process\s*\.\s*exec\s*\('],
    '.php': [r'\beval\s*\(', r'\bexec\s*\(', r'\bshell_exec\s*\(',
             r'\bsystem\s*\(', r'\bpassthru\s*\(', r'`[^`]*`'],
    '.cs': [r'Process\s*\.\s*Start\s*\(\s*"'],
}

# RULE-2: the per-language opt-in to a shell.
_SHELL_FLAG_BY_EXT = {
    '.py': [r'shell\s*=\s*True'],
    '.js': [r'shell\s*:\s*true'],
    '.ts': [r'shell\s*:\s*true'],
    '.cs': [r'UseShellExecute\s*=\s*true'],
}

# RULE-3: the builtins that hand a whole command line to the OS shell.
_SYSTEM_CALL_BY_EXT = {
    '.py': [r'os\.system\s*\('],
    '.php': [r'\bsystem\s*\(', r'\bpassthru\s*\('],
}


def _pattern_hits(paths, table, strip=True):
    """`[(path, pattern), ...]` for each form of `table` a file holds."""
    hits = []
    for path in paths:
        ext = _ext(path)
        content = _read(path)
        if strip:
            content = _strip_comments(content, ext)
        for pattern in table.get(ext, []):
            if re.search(pattern, content, re.MULTILINE):
                hits.append((path, pattern))
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
            # A launch imported by name, under its own name or an alias.
            for imported in _PY_IMPORTED.findall(content):
                for entry in (e.split() for e in imported.split(',')):
                    if not entry:
                        continue
                    bare = re.compile(r'(?<![\w.])%s\s*\(' % entry[-1])
                    if entry[0] in _PY_LAUNCHES:
                        calls += bare.finditer(content)
                    elif entry[0] == 'Popen':
                        for m in bare.finditer(content):
                            if re.match(r'[fbr]?["\']', head(m)):
                                faults.append(f"Popen with string arg at {where(m)}")
            for m in calls:
                if not head(m).startswith(('[', '*')):
                    faults.append(f"subprocess call at {where(m)} first arg is "
                                  f"not a list literal: ...{head(m)[:30]}")
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


def _plant(root, index, name, text):
    """Write `text` to `<root>/<index>/<name>` and return its path."""
    folder = os.path.join(str(root), str(index))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return path


def _misses(root, samples, finds):
    """The samples for which `finds([path])` found nothing."""
    return [(name, text) for i, (name, text) in enumerate(samples)
            if not finds([_plant(root, i, name, text)])]


def _false_alarms(root, samples, finds):
    """The samples for which `finds([path])` found something."""
    return [(name, text) for i, (name, text) in enumerate(samples)
            if finds([_plant(root, 'clean-%d' % i, name, text)])]


# A file holding one form of each rule, and files that hold none.
_PLANTED_DYNAMIC = [
    ('a.py', 'x = eval(src)\n'), ('a.py', 'exec (src)\n'),
    ('a.py', 'x = eval(src)  # only a comment follows\n'),
    ('a.sh', 'eval "$cmd"\n'), ('a.sh', '    eval "$cmd"\n'),
    ('a.sh', 'if eval "$cmd"; then :; fi\n'), ('a.sh', 'out=$(eval "$cmd")\n'),
    ('a.sh', 'true && eval "$cmd"\n'), ('a.sh', 'out=`date`\n'),
    ('a.js', 'eval(src);\n'), ('a.js', 'const f = new Function(src);\n'),
    ('a.js', 'execSync(cmd);\n'), ('a.js', 'child_process.exec(cmd);\n'),
    ('a.js', 'eval(src); // only a comment follows\n'),
    ('a.ts', 'eval(src);\n'), ('a.ts', 'const f = new Function(src);\n'),
    ('a.ts', 'execSync(cmd);\n'), ('a.ts', 'child_process.exec(cmd);\n'),
    ('a.php', '<?php eval($src);\n'), ('a.php', '<?php exec($cmd);\n'),
    ('a.php', '<?php shell_exec($cmd);\n'), ('a.php', '<?php system($cmd);\n'),
    ('a.php', '<?php passthru($cmd);\n'), ('a.php', '<?php $o = `ls`;\n'),
    ('a.cs', 'Process.Start("cmd.exe /c dir");\n'),
]
_CLEAN_DYNAMIC = [
    ('a.py', '# eval(src) is never called\nx = evaluate(src)\n'),
    ('a.sh', '  # eval "$cmd" is never run\nrun_evaluation "$x"\n'),
    ('a.js', '// eval(src) is never called\nconst x = evaluate(src);\n'),
    ('a.cs', 'Process.Start(info);\n'),
]


class TestSecurityPatterns:

    # purlin: security_no_dangerous_patterns PROOF-1
    def test_no_dynamic_code_execution(self):
        hits = _pattern_hits(_all_script_files(), _DANGEROUS_BY_EXT)
        assert not hits, "\n".join(f"Found dynamic-code pattern {pattern!r} in {path}"
                                   for path, pattern in hits)

    # purlin: security_no_dangerous_patterns PROOF-1
    def test_planted_dynamic_code_is_found(self, tmp_path):
        finds = lambda paths: _pattern_hits(paths, _DANGEROUS_BY_EXT)  # noqa: E731
        assert not _misses(tmp_path, _PLANTED_DYNAMIC, finds), \
            "a planted form went unfound"
        assert not _false_alarms(tmp_path, _CLEAN_DYNAMIC, finds), \
            "a comment-only line or a harmless word was counted"
        # The scan of a folder finds every planted file, and names it.
        found = {path for path, _ in _pattern_hits(_all_script_files(str(tmp_path)),
                                                   _DANGEROUS_BY_EXT)}
        assert len(found) == len(_PLANTED_DYNAMIC), found

    # purlin: security_no_dangerous_patterns PROOF-2
    def test_no_shell_true(self):
        hits = _pattern_hits(_all_script_files(), _SHELL_FLAG_BY_EXT, strip=False)
        assert not hits, "\n".join(f"Found shell opt-in {pattern!r} in {path}"
                                   for path, pattern in hits)

    # purlin: security_no_dangerous_patterns PROOF-2
    def test_planted_shell_opt_in_is_found(self, tmp_path):
        finds = lambda paths: _pattern_hits(paths, _SHELL_FLAG_BY_EXT,  # noqa: E731
                                            strip=False)
        planted = [('a.py', 'subprocess.run(argv, shell=True)\n'),
                   ('a.py', 'subprocess.run(argv, shell = True)\n'),
                   ('a.py', '# subprocess.run(argv, shell=True)\n'),
                   ('a.js', 'spawn("ls", [], { shell: true });\n'),
                   ('a.ts', 'spawn("ls", [], { shell :true });\n'),
                   ('a.cs', 'psi.UseShellExecute = true;\n'),
                   ('a.cs', 'psi.UseShellExecute=true;\n')]
        clean = [('a.py', 'subprocess.run(argv, shell=False)\n'),
                 ('a.js', 'spawn("ls", [], { shell: false });\n'),
                 ('a.cs', 'psi.UseShellExecute = false;\n')]
        assert not _misses(tmp_path, planted, finds), "a planted opt-in went unfound"
        assert not _false_alarms(tmp_path, clean, finds), "an opt-out was counted"

    # purlin: security_no_dangerous_patterns PROOF-3
    def test_no_os_system(self):
        hits = _pattern_hits(_all_script_files(), _SYSTEM_CALL_BY_EXT)
        assert not hits, "\n".join(f"Found shell-command builtin {pattern!r} in {path}"
                                   for path, pattern in hits)

    # purlin: security_no_dangerous_patterns PROOF-3
    def test_planted_system_call_is_found(self, tmp_path):
        finds = lambda paths: _pattern_hits(paths, _SYSTEM_CALL_BY_EXT)  # noqa: E731
        planted = [('a.py', 'os.system(cmd)\n'), ('a.py', 'os.system (cmd)\n'),
                   ('a.php', '<?php system($cmd);\n'),
                   ('a.php', '<?php passthru ($cmd);\n')]
        clean = [('a.py', '# os.system(cmd) is never called\n'),
                 ('a.php', '<?php\n// system($cmd) is never called\n')]
        assert not _misses(tmp_path, planted, finds), "a planted call went unfound"
        assert not _false_alarms(tmp_path, clean, finds), "a comment was counted"

    # purlin: security_no_dangerous_patterns PROOF-4
    def test_no_hardcoded_credentials(self):
        hits = _credential_hits(_all_script_files())
        assert not hits, "\n".join(f"Found hardcoded credential in {path}: {matches}"
                                   for path, matches in hits)

    # purlin: security_no_dangerous_patterns PROOF-7
    def test_planted_credential_is_found(self, tmp_path):
        planted = [('a.py', 'API_KEY = "abc"\n', 'API_KEY'),
                   ('a.py', "db_password='x'\n", 'db_password'),
                   ('a.sh', 'GITHUB_TOKEN="abc"\n', 'GITHUB_TOKEN'),
                   ('a.py', 'TOKEN_NAME = "abc"\n', 'TOKEN_NAME'),
                   ('a.js', 'const cfg = { password: "x" };\n', 'password'),
                   ('a.ts', 'const auth = { Token : "abc" };\n', 'Token')]
        for index, (name, text, matched) in enumerate(planted):
            path = _plant(tmp_path, index, name, text)
            assert _credential_hits([path]) == [(path, [matched])], (
                name, text, _credential_hits([path]))

    # purlin: security_no_dangerous_patterns PROOF-8
    def test_an_empty_value_a_comparison_or_a_test_file_is_not_counted(
            self, tmp_path):
        clean = [('a.py', 'API_KEY = ""\n'), ('a.py', 'if token == "x":\n    pass\n'),
                 ('test_a.py', 'password = "x"\n'),
                 ('a.py', 'row = {"password": ""}\n')]
        assert not _false_alarms(tmp_path, clean, _credential_hits), \
            "an empty value, a comparison or a test file was counted"

    # purlin: security_no_dangerous_patterns PROOF-5
    def test_subprocess_uses_list_args(self):
        faults = _launch_faults(_all_script_files())
        assert not faults, "\n".join(faults)

    # purlin: security_no_dangerous_patterns PROOF-5
    def test_planted_command_string_launch_is_found(self, tmp_path):
        planted = [('a.py', 'subprocess.run("git status")\n'),
                   ('a.py', 'subprocess.run(cmd)\n'),
                   ('a.py', 'subprocess.Popen("git status")\n'),
                   ('a.py', 'subprocess.Popen(f"git {verb}")\n'),
                   ('a.py', 'from subprocess import run\nrun("git status")\n'),
                   ('a.py', 'from subprocess import check_output as co, call\n'
                            'co("git status")\n'),
                   ('a.py', 'from subprocess import Popen\nPopen("git status")\n'),
                   ('a.php', '<?php proc_open("ls -la", $spec, $pipes);\n'),
                   ('a.js', 'spawn("ls", "-la");\n'), ('a.js', 'spawn("ls -la");\n'),
                   ('a.ts', 'execFileSync(cmd);\n'),
                   ('a.cs', 'psi.Arguments = "status --short";\n')]
        clean = [('a.py', 'subprocess.run(["git", "status"])\n'),
                 ('a.py', 'subprocess.run(*argv)\n'),
                 ('a.py', 'from subprocess import run\nrun(["git", "status"])\n'),
                 ('a.py', 'subprocess.Popen(command, cwd=root)\n'),
                 ('a.php', '<?php proc_open(["ls", "-la"], $spec, $pipes);\n'),
                 ('a.js', 'spawn("ls", ["-la"]);\n'),
                 ('a.cs', 'psi.ArgumentList.Add("status");\n')]
        assert not _misses(tmp_path, planted, _launch_faults), \
            "a planted command-string launch went unfound"
        assert not _false_alarms(tmp_path, clean, _launch_faults), \
            "a launch handed an argument vector was counted"


EVIL_SOURCE = '--upload-pack=/bin/echo'
# The two transports git will run a command for. RULE-6 refuses both
# before any subprocess starts, not after quoting them safely.
EXT_SOURCE = 'ext::sh -c "touch /tmp/purlin-pwned"'
FD_SOURCE = 'fd::7'


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


def _launched_by(monkeypatch, read):
    """`(result, git argvs)` of `read()`, every git command it started."""
    calls = _record_launches(monkeypatch)
    result = read()
    monkeypatch.undo()
    return result, [argv for argv in calls if argv and argv[0] == 'git']


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
    """RULE-6: nothing repository-supplied reaches git in option position."""

    # purlin: security_no_dangerous_patterns PROOF-6
    def test_a_hostile_source_is_refused_before_any_command(self, tmp_path,
                                                             monkeypatch):
        project = _project(tmp_path, [('evil_policy', EVIL_SOURCE),
                                      ('ext_policy', EXT_SOURCE),
                                      ('fd_policy', FD_SOURCE)])
        text, calls = _launched_by(
            monkeypatch, lambda: purlin_status.sync_status(str(project)))
        assert calls, "no git command captured"
        for rejected in (EVIL_SOURCE, EXT_SOURCE, FD_SOURCE):
            for argv in calls:
                assert rejected not in argv, (
                    f"{rejected!r} reached git; RULE-6 refuses it before any "
                    f"subprocess starts: {argv}")
        for reason in ('(source rejected: begins with "-")',
                       '(source rejected: names an ext:: transport)',
                       '(source rejected: names an fd:: transport)'):
            assert reason in text, (
                f"status text does not name the rejection {reason!r}:\n{text}")

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
