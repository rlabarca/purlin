"""Tests for security_no_dangerous_patterns — 5 rules.

FORBIDDEN pattern checks across all executable Purlin framework code.
"""

import glob
import os
import re

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')


def _py_files():
    return glob.glob(os.path.join(SCRIPTS_DIR, '**', '*.py'), recursive=True)


def _all_script_files():
    patterns = ('**/*.py', '**/*.sh', '**/*.js')
    files = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(SCRIPTS_DIR, p), recursive=True))
    return files


def _read(path):
    with open(path) as f:
        return f.read()


def _strip_comments(content, ext):
    """Remove comments to avoid false positives."""
    if ext == '.py':
        # Remove # comments (not in strings)
        lines = []
        for line in content.splitlines():
            stripped = line.lstrip()
            if not stripped.startswith('#'):
                lines.append(line)
        return '\n'.join(lines)
    return content


class TestSecurityPatterns:

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-1", "RULE-1")
    def test_no_eval_or_exec(self):
        for path in _py_files():
            content = _strip_comments(_read(path), '.py')
            # Match eval( or exec( as function calls, not in strings/comments
            matches = re.findall(r'\beval\s*\(', content)
            assert not matches, f"Found eval() in {path}"
            matches = re.findall(r'\bexec\s*\(', content)
            assert not matches, f"Found exec() in {path}"

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-2", "RULE-2")
    def test_no_shell_true(self):
        for path in _py_files():
            content = _read(path)
            matches = re.findall(r'shell\s*=\s*True', content)
            assert not matches, f"Found shell=True in {path}"

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-3", "RULE-3")
    def test_no_os_system(self):
        for path in _py_files():
            content = _read(path)
            matches = re.findall(r'os\.system\s*\(', content)
            assert not matches, f"Found os.system() in {path}"

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
            content = _strip_comments(_read(path), os.path.splitext(path)[1])
            matches = cred_pattern.findall(content)
            assert not matches, \
                f"Found hardcoded credential in {path}: {matches}"

    @pytest.mark.proof("security_no_dangerous_patterns", "PROOF-5", "RULE-5")
    def test_subprocess_uses_list_args(self):
        call_pattern = re.compile(r'subprocess\.(run|call|check_call|check_output)\s*\(')
        string_arg = re.compile(r'subprocess\.\w+\(\s*["\']')
        for path in _py_files():
            content = _read(path)
            if not call_pattern.search(content):
                continue
            matches = string_arg.findall(content)
            assert not matches, \
                f"Found subprocess with string arg in {path}"
