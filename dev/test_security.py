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
import purlin_server  # noqa: E402

# Every executable language that ships under scripts/. The anchor's > Scope:
# names exactly these six extensions; keep the two in step.
SCRIPT_EXTENSIONS = ('.py', '.sh', '.js', '.ts', '.php', '.cs')


def _all_script_files():
    files = []
    for ext in SCRIPT_EXTENSIONS:
        files.extend(glob.glob(os.path.join(SCRIPTS_DIR, '**', '*' + ext),
                               recursive=True))
    return files


def _read(path):
    with open(path) as f:
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
    '.sh': [r'(^|[;&|]\s*)eval\s', r'`[^`]*`'],
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


class TestSecurityPatterns:

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-1", "RULE-1")
    def test_no_dynamic_code_execution(self):
        for path in _all_script_files():
            ext = _ext(path)
            content = _strip_comments(_read(path), ext)
            for pattern in _DANGEROUS_BY_EXT.get(ext, []):
                assert not re.search(pattern, content, re.MULTILINE), \
                    f"Found dynamic-code pattern {pattern!r} in {path}"

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-2", "RULE-2")
    def test_no_shell_true(self):
        for path in _all_script_files():
            ext = _ext(path)
            content = _read(path)
            for pattern in _SHELL_FLAG_BY_EXT.get(ext, []):
                assert not re.search(pattern, content), \
                    f"Found shell opt-in {pattern!r} in {path}"

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-3", "RULE-3")
    def test_no_os_system(self):
        for path in _all_script_files():
            ext = _ext(path)
            content = _strip_comments(_read(path), ext)
            for pattern in _SYSTEM_CALL_BY_EXT.get(ext, []):
                assert not re.search(pattern, content), \
                    f"Found shell-command builtin {pattern!r} in {path}"

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-4", "RULE-4")
    def test_no_hardcoded_credentials(self):
        cred_pattern = re.compile(
            r'(password|secret|api_key|token)\s*=\s*["\'][^"\']+["\']',
            re.IGNORECASE
        )
        for path in _all_script_files():
            basename = os.path.basename(path)
            if basename.startswith('test_'):
                continue
            content = _strip_comments(_read(path), _ext(path))
            matches = cred_pattern.findall(content)
            assert not matches, \
                f"Found hardcoded credential in {path}: {matches}"

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-5", "RULE-5")
    def test_subprocess_uses_list_args(self):
        py_call = re.compile(r'subprocess\.(run|call|check_call|check_output)\s*\(')
        py_string_arg = re.compile(
            r'subprocess\.(run|call|check_call|check_output)\s*\(\s*["\']')
        php_call = re.compile(r'\bproc_open\s*\(')
        js_call = re.compile(
            r'\b(spawn|spawnSync|execFile|execFileSync)\s*\([^,)]*,\s*')
        cs_string_args = re.compile(r'\.Arguments\s*=\s*"')

        for path in _all_script_files():
            ext = _ext(path)
            content = _strip_comments(_read(path), ext)

            if ext == '.py':
                assert not py_string_arg.findall(content), \
                    f"Found subprocess with string arg in {path}"
                for m in py_call.finditer(content):
                    after_paren = content[m.end():m.end() + 50].lstrip()
                    assert after_paren.startswith('[') or after_paren.startswith('*'), \
                        f"subprocess call at {path}:{content[:m.start()].count(chr(10))+1} " \
                        f"first arg is not a list literal: ...{after_paren[:30]}"
            elif ext == '.php':
                for m in php_call.finditer(content):
                    after_paren = content[m.end():m.end() + 50].lstrip()
                    assert after_paren.startswith('['), \
                        f"proc_open at {path}:{content[:m.start()].count(chr(10))+1} " \
                        f"first arg is not an array literal: ...{after_paren[:30]}"
            elif ext in ('.js', '.ts'):
                for m in js_call.finditer(content):
                    after_comma = content[m.end():m.end() + 50].lstrip()
                    assert after_comma.startswith('['), \
                        f"{m.group(1)} at {path}:{content[:m.start()].count(chr(10))+1} " \
                        f"args argument is not an array literal: ...{after_comma[:30]}"
            elif ext == '.cs':
                assert not cs_string_args.findall(content), \
                    f"Found ProcessStartInfo.Arguments string assignment in {path}"


EVIL_SOURCE = '--upload-pack=/bin/echo'


def _git(args, cwd=None, check=True):
    return subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                          text=True, check=check)


def _make_bare_repo(bare_path, work_path):
    """Create a bare repo with one commit. Returns its HEAD SHA."""
    _git(['init', '--bare', '-q', bare_path])
    _git(['clone', '-q', bare_path, work_path])
    with open(os.path.join(work_path, 'policy.md'), 'w') as f:
        f.write('# policy\n')
    _git(['config', 'user.email', 'test@test.com'], cwd=work_path)
    _git(['config', 'user.name', 'Test'], cwd=work_path)
    _git(['add', '-A'], cwd=work_path)
    _git(['commit', '-q', '-m', 'initial policy'], cwd=work_path)
    _git(['push', '-q', 'origin', 'HEAD:refs/heads/main'], cwd=work_path)
    return _git(['rev-parse', 'HEAD'], cwd=work_path).stdout.strip()


def _write_anchor(anchors_dir, name, source, pinned):
    with open(os.path.join(anchors_dir, name + '.md'), 'w') as f:
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


class TestGitArgvHardening:
    """RULE-6: nothing repository-supplied reaches git in option position."""

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-6", "RULE-6",
                       tier="integration")
    def test_source_url_never_reaches_git_in_option_position(self, tmp_path,
                                                             monkeypatch):
        project = tmp_path / 'project'
        purlin_dir = project / '.purlin'
        purlin_dir.mkdir(parents=True)
        (purlin_dir / 'config.json').write_text(
            json.dumps({'version': '1.0.0', 'project_name': 'spy'}))
        anchors = project / 'specs' / '_anchors'
        anchors.mkdir(parents=True)

        # A reachable source, so a legitimate ls-remote really happens. Without
        # it the positive control below would pass vacuously.
        bare = str(tmp_path / 'good-policy.git')
        good_sha = _make_bare_repo(bare, str(tmp_path / 'good-work'))
        _write_anchor(str(anchors), 'good_policy', bare, good_sha)
        _write_anchor(str(anchors), 'evil_policy', EVIL_SOURCE,
                      '1234567890abcdef1234567890abcdef12345678')

        _git(['init', '-q'], cwd=str(project))
        _git(['config', 'user.email', 'test@test.com'], cwd=str(project))
        _git(['config', 'user.name', 'Test'], cwd=str(project))
        _git(['add', '-A'], cwd=str(project))
        _git(['commit', '-q', '-m', 'chore: project under test'], cwd=str(project))

        calls = []
        real_run = subprocess.run

        def spy(args, *rest, **kwargs):
            calls.append(list(args) if isinstance(args, (list, tuple)) else [args])
            return real_run(args, *rest, **kwargs)

        monkeypatch.setattr(purlin_server.subprocess, 'run', spy)
        text = purlin_server.sync_status(str(project))
        monkeypatch.undo()

        assert calls, "no subprocess calls captured"

        # The rejected Source never reaches git at all, and certainly never
        # ahead of an end-of-options separator.
        for argv in calls:
            if EVIL_SOURCE in argv:
                idx = argv.index(EVIL_SOURCE)
                seps = [i for i, a in enumerate(argv)
                        if a in ('--end-of-options', '--')]
                assert seps and min(seps) < idx, \
                    f"{EVIL_SOURCE} reached git in option position: {argv}"

        # Positive control: the safe url did reach ls-remote, and
        # --end-of-options sits immediately in front of it every time.
        ls_remotes = [a for a in calls
                      if len(a) >= 2 and a[0] == 'git' and a[1] == 'ls-remote']
        assert ls_remotes, \
            "no git ls-remote captured; the positive control would be vacuous"
        for argv in ls_remotes:
            assert EVIL_SOURCE not in argv, \
                f"rejected Source reached ls-remote: {argv}"
            assert bare in argv, f"expected the safe url in {argv}"
            url_idx = argv.index(bare)
            assert url_idx > 0 and argv[url_idx - 1] == '--end-of-options', \
                f"--end-of-options does not precede the url: {argv}"

        assert '(source rejected: begins with "-")' in text, \
            f"status text does not name the rejection:\n{text}"
