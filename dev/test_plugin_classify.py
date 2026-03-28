#!/usr/bin/env python3
"""Tests for classify_file() in scripts/mcp/config_engine.py.

Validates that the mode-guard file classification logic correctly maps
file paths to CODE, SPEC, QA, or INVARIANT categories.
"""

import os
import sys
import unittest

# ---------------------------------------------------------------------------
# Path setup: derive PLUGIN_ROOT from __file__ and add scripts/mcp/ to path.
# Walk up from this file's directory looking for scripts/mcp/config_engine.py.
# This supports both the main repo layout and git worktree checkouts.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_plugin_root():
    """Walk up from __file__ to find a directory containing scripts/mcp/config_engine.py."""
    candidate = os.path.dirname(_THIS_DIR)  # dev/ -> project root
    for _ in range(10):
        if os.path.isfile(os.path.join(candidate, 'scripts', 'mcp', 'config_engine.py')):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    # Worktree fallback: resolve the main repo via the git common dir.
    # In a worktree, .git is a file (not a directory) containing a gitdir pointer
    # like "gitdir: /main-repo/.git/worktrees/<name>".  Walk up 3 levels from
    # that absolute path to reach the main repo root.
    git_dir = os.path.join(os.path.dirname(_THIS_DIR), '.git')
    if os.path.isfile(git_dir):
        with open(git_dir, 'r') as f:
            content = f.read().strip()
        if content.startswith('gitdir:'):
            real_git = os.path.abspath(content.split(':', 1)[1].strip())
            # /main-repo/.git/worktrees/<name> -> up 3 -> /main-repo
            main_repo = os.path.dirname(os.path.dirname(os.path.dirname(real_git)))
            if os.path.isfile(os.path.join(main_repo, 'scripts', 'mcp', 'config_engine.py')):
                return main_repo
    return os.path.dirname(_THIS_DIR)


PLUGIN_ROOT = _find_plugin_root()
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import classify_file


class TestClassifyFile(unittest.TestCase):
    """Test classify_file() against all classification patterns."""

    # ----- INVARIANT files -----

    def test_invariant_i_security(self):
        """features/i_*.md files are INVARIANT."""
        result = classify_file('features/i_arch_security.md')
        self.assertEqual(result, 'INVARIANT')

    def test_invariant_i_data_retention(self):
        """Another invariant pattern with underscore-prefixed name."""
        result = classify_file('features/i_policy_data_retention.md')
        self.assertEqual(result, 'INVARIANT')

    # ----- QA files -----

    def test_qa_discoveries(self):
        """*.discoveries.md files are QA-owned."""
        result = classify_file('features/foo.discoveries.md')
        self.assertEqual(result, 'QA')

    def test_qa_regression_json(self):
        """regression.json inside a /tests/ path segment is QA-owned.

        Note: classify_file checks for '/tests/' (with leading slash), so a
        bare 'tests/...' path at the repo root does not match.  A prefixed
        path like 'src/tests/...' does match.
        """
        # Bare 'tests/' at root does NOT contain '/tests/' -- falls to CODE
        self.assertEqual(classify_file('tests/foo/regression.json'), 'CODE')
        # Prefixed path DOES contain '/tests/' -- correctly returns QA
        self.assertEqual(classify_file('src/tests/foo/regression.json'), 'QA')

    # ----- CODE files (companion / impl) -----

    def test_code_impl_companion(self):
        """*.impl.md files inside features/ are CODE (Engineer-owned companions)."""
        result = classify_file('features/foo.impl.md')
        self.assertEqual(result, 'CODE')

    # ----- SPEC files (PM-owned) -----

    def test_spec_feature_file(self):
        """Regular feature specs are SPEC."""
        result = classify_file('features/user_auth.md')
        self.assertEqual(result, 'SPEC')

    def test_spec_arch_anchor(self):
        """Arch anchors in features/ are SPEC (they live in features/)."""
        result = classify_file('features/arch_testing.md')
        self.assertEqual(result, 'SPEC')

    def test_spec_tombstoned_feature(self):
        """Tombstoned features under features/tombstones/ are still SPEC."""
        result = classify_file('features/tombstones/legacy_auth.md')
        self.assertEqual(result, 'SPEC')

    # ----- CODE files (default bucket) -----

    def test_code_src_file(self):
        """Application source files are CODE."""
        result = classify_file('src/app.py')
        self.assertEqual(result, 'CODE')

    def test_code_mcp_server(self):
        """MCP scripts are CODE."""
        result = classify_file('scripts/mcp/server.py')
        self.assertEqual(result, 'CODE')

    def test_code_hook_script(self):
        """Hook scripts are CODE."""
        result = classify_file('hooks/mode-guard.sh')
        self.assertEqual(result, 'CODE')

    def test_code_readme(self):
        """README.md at the root is CODE (default)."""
        result = classify_file('README.md')
        self.assertEqual(result, 'CODE')

    def test_code_purlin_overrides(self):
        """.purlin/PURLIN_OVERRIDES.md is CODE (not in features/)."""
        result = classify_file('.purlin/PURLIN_OVERRIDES.md')
        self.assertEqual(result, 'CODE')

    def test_code_tests_non_regression_json(self):
        """Non-regression JSON in tests/ falls through to CODE."""
        result = classify_file('tests/foo/tests.json')
        self.assertEqual(result, 'CODE')

    def test_code_empty_path(self):
        """Empty string path falls through all patterns to CODE."""
        result = classify_file('')
        self.assertEqual(result, 'CODE')


if __name__ == '__main__':
    unittest.main()
