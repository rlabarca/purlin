#!/usr/bin/env python3
"""Tests for the sync_docs_to_github_wiki release step.

Covers unit test scenarios from features/release_sync_docs_github_wiki.md:
- Wiki repo URL derived from github remote
- Filename derives correct wiki page name
- Home page generated with TOC
- Sidebar generated with navigation
- Synced pages have tracking markers
- Manually-created wiki pages are preserved
- Wiki not enabled triggers setup guidance
- No changes results in skip

This release step has code: null (interactive). These tests verify the
underlying utility functions and behavioral contracts that the agent
relies on when executing the step interactively.
"""
import json
import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))

# Add dev/ to path so we can import the wiki utility module
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'dev'))
import github_wiki_utils as gwu

# Add project root for release resolve module
sys.path.insert(0, PROJECT_ROOT)
from tools.release.resolve import resolve_checklist


def _resolve_wiki_step():
    """Resolve the sync_docs_to_github_wiki step via the release resolver."""
    resolved, _warnings, _errors = resolve_checklist()
    matches = [s for s in resolved if s['id'] == 'sync_docs_to_github_wiki']
    if not matches:
        raise ValueError('sync_docs_to_github_wiki step not found')
    return matches[0]


class TestWikiRepoUrlDerived(unittest.TestCase):
    """Scenario: Wiki repo URL derived from github remote

    Given the github remote is "git@github.com:rlabarca/purlin.git"
    When the step derives the wiki repo URL
    Then the URL is "git@github.com:rlabarca/purlin.wiki.git"
    """

    def test_ssh_url_derives_wiki_url(self):
        """SSH remote URL derives correct wiki repo URL."""
        self.assertEqual(
            gwu.derive_wiki_repo_url('git@github.com:rlabarca/purlin.git'),
            'git@github.com:rlabarca/purlin.wiki.git')

    def test_https_url_derives_wiki_url(self):
        """HTTPS remote URL derives correct wiki repo URL."""
        self.assertEqual(
            gwu.derive_wiki_repo_url('https://github.com/rlabarca/purlin.git'),
            'https://github.com/rlabarca/purlin.wiki.git')

    def test_url_without_dot_git_suffix(self):
        """URL without .git suffix gets .wiki.git appended."""
        self.assertEqual(
            gwu.derive_wiki_repo_url('https://github.com/rlabarca/purlin'),
            'https://github.com/rlabarca/purlin.wiki.git')

    def test_resolved_step_references_wiki_git(self):
        """Resolved step's agent instructions reference .wiki.git derivation."""
        step = _resolve_wiki_step()
        self.assertIn('.wiki.git', step['agent_instructions'])


class TestFilenameDeriveWikiPageName(unittest.TestCase):
    """Scenario: Filename derives correct wiki page name

    Given a markdown file named "testing-workflow-guide.md" in docs/
    When the step derives the wiki page name
    Then the page name is "Testing-Workflow-Guide.md"
    """

    def test_hyphenated_filename_to_wiki_name(self):
        """Hyphenated filename derives title-cased wiki page name."""
        self.assertEqual(
            gwu.derive_wiki_page_name('testing-workflow-guide.md'),
            'Testing-Workflow-Guide.md')

    def test_single_word_filename(self):
        """Single-word filename capitalizes correctly."""
        self.assertEqual(
            gwu.derive_wiki_page_name('overview.md'),
            'Overview.md')

    def test_parallel_execution_guide(self):
        """Verify with another actual project doc filename."""
        self.assertEqual(
            gwu.derive_wiki_page_name('parallel-execution-guide.md'),
            'Parallel-Execution-Guide.md')

    def test_md_extension_preserved_in_output(self):
        """Output keeps the .md extension."""
        result = gwu.derive_wiki_page_name('my-doc.md')
        self.assertTrue(result.endswith('.md'))
        self.assertEqual(result, 'My-Doc.md')


class TestHomePageGeneratedWithTOC(unittest.TestCase):
    """Scenario: Home page generated with TOC

    Given docs/ contains "testing-workflow-guide.md" and
    "parallel-execution-guide.md"
    When the step generates Home.md
    Then Home.md contains wiki links [[Testing-Workflow-Guide]] and
    [[Parallel-Execution-Guide]]
    And Home.md contains a purlin-sync marker
    """

    def test_convert_links_to_wiki_format(self):
        """Relative markdown links are converted to wiki links."""
        content = ('* [Testing Guide](testing-workflow-guide.md)\n'
                   '* [Parallel Guide](parallel-execution-guide.md)\n')
        result = gwu.convert_links_to_wiki(content)
        self.assertIn('[[Testing-Workflow-Guide]]', result)
        self.assertIn('[[Parallel-Execution-Guide]]', result)

    def test_non_md_links_preserved(self):
        """Links to non-markdown files are left unchanged."""
        content = '[Image](diagram.png)'
        result = gwu.convert_links_to_wiki(content)
        self.assertEqual(result, '[Image](diagram.png)')

    def test_resolved_step_references_home_and_index(self):
        """Resolved step's agent instructions reference Home.md and index.md."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        self.assertIn('Home.md', instructions)
        self.assertIn('index.md', instructions)

    def test_resolved_step_references_purlin_sync_marker(self):
        """Resolved step's agent instructions include purlin-sync marker for Home."""
        step = _resolve_wiki_step()
        self.assertIn('purlin-sync: _generated', step['agent_instructions'])


class TestSidebarGeneratedWithNavigation(unittest.TestCase):
    """Scenario: Sidebar generated with navigation

    Given docs/ contains "testing-workflow-guide.md" and
    "parallel-execution-guide.md"
    When the step generates _Sidebar.md
    Then _Sidebar.md contains wiki links for both pages
    And _Sidebar.md contains a purlin-sync marker
    """

    def test_sidebar_contains_wiki_links(self):
        """Generated sidebar contains wiki links for all pages."""
        pages = ['Testing-Workflow-Guide', 'Parallel-Execution-Guide']
        sidebar = gwu.generate_sidebar_content(pages)
        self.assertIn('[[Testing-Workflow-Guide]]', sidebar)
        self.assertIn('[[Parallel-Execution-Guide]]', sidebar)

    def test_sidebar_has_purlin_docs_heading(self):
        """Sidebar starts with 'Purlin Docs' heading."""
        pages = ['Overview']
        sidebar = gwu.generate_sidebar_content(pages)
        self.assertIn('# Purlin Docs', sidebar)

    def test_sidebar_links_are_bulleted(self):
        """Each page link is on a bulleted line."""
        pages = ['Testing-Workflow-Guide', 'Overview']
        sidebar = gwu.generate_sidebar_content(pages)
        self.assertIn('* [[Testing-Workflow-Guide]]', sidebar)
        self.assertIn('* [[Overview]]', sidebar)

    def test_resolved_step_references_sidebar(self):
        """Resolved step's agent instructions reference _Sidebar.md."""
        step = _resolve_wiki_step()
        self.assertIn('_Sidebar.md', step['agent_instructions'])


class TestSyncedPagesHaveTrackingMarkers(unittest.TestCase):
    """Scenario: Synced pages have tracking markers

    Given docs/testing-workflow-guide.md is synced to the wiki
    When the wiki page is generated
    Then the page ends with "<!-- purlin-sync: testing-workflow-guide.md -->"
    """

    def test_has_purlin_sync_marker_detects_marker(self):
        """has_purlin_sync_marker returns True for content with marker."""
        content = '# Title\n\nSome content.\n\n<!-- purlin-sync: testing-workflow-guide.md -->'
        self.assertTrue(gwu.has_purlin_sync_marker(content))

    def test_extract_purlin_sync_source_returns_path(self):
        """extract_purlin_sync_source returns the source path."""
        content = '# Title\n\nSome content.\n\n<!-- purlin-sync: testing-workflow-guide.md -->'
        self.assertEqual(
            gwu.extract_purlin_sync_source(content),
            'testing-workflow-guide.md')

    def test_extract_generated_marker(self):
        """extract_purlin_sync_source returns '_generated' for generated pages."""
        content = '# Home\n\nContent.\n\n<!-- purlin-sync: _generated -->'
        self.assertEqual(
            gwu.extract_purlin_sync_source(content),
            '_generated')

    def test_marker_with_trailing_whitespace(self):
        """Marker detection works with trailing whitespace."""
        content = '# Title\n\n<!-- purlin-sync: overview.md -->  \n'
        self.assertTrue(gwu.has_purlin_sync_marker(content))


class TestManuallyCreatedPagesPreserved(unittest.TestCase):
    """Scenario: Manually-created wiki pages are preserved

    Given the wiki contains a page "Custom-Notes.md" without a
    purlin-sync marker
    When the step syncs docs/ to the wiki
    Then "Custom-Notes.md" is not modified or deleted
    """

    def test_no_marker_returns_false(self):
        """has_purlin_sync_marker returns False for pages without markers."""
        content = '# Custom Notes\n\nManually created content.\n'
        self.assertFalse(gwu.has_purlin_sync_marker(content))

    def test_extract_returns_none_for_no_marker(self):
        """extract_purlin_sync_source returns None for pages without markers."""
        content = '# Custom Notes\n\nNo sync marker here.\n'
        self.assertIsNone(gwu.extract_purlin_sync_source(content))

    def test_resolved_step_forbids_deleting_manual_pages(self):
        """Resolved step's agent instructions forbid deleting unmarked pages."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        # The step instructions reference removing only previously-synced
        # pages (those with markers), preserving manual content
        self.assertIn('markers', instructions.lower())
        self.assertIn('manually-created', instructions.lower())

    def test_step_is_interactive_only(self):
        """Step has code: null (no automated deletion possible)."""
        step = _resolve_wiki_step()
        self.assertIsNone(step['code'])


class TestWikiNotEnabledTriggersSetupGuidance(unittest.TestCase):
    """Scenario: Wiki not enabled triggers setup guidance

    Given the github remote exists but the wiki repo clone fails
    When the step executes Phase 0
    Then the step directs the user to enable the wiki in GitHub Settings
    And the step halts until the clone succeeds
    """

    def test_resolved_step_references_wiki_enable(self):
        """Resolved step's agent instructions guide enabling the wiki."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        self.assertIn('enable', instructions.lower())
        self.assertIn('Settings', instructions)

    def test_resolved_step_references_clone_failure(self):
        """Resolved step handles clone failure scenario."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        self.assertIn('clone fails', instructions.lower())

    def test_resolved_step_halts_on_failure(self):
        """Resolved step halts until clone succeeds."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        self.assertIn('Halt', instructions)

    def test_resolved_step_references_initial_page_creation(self):
        """Resolved step guides user to create initial wiki page via web UI."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        self.assertIn('web UI', instructions)


class TestNoChangesResultsInSkip(unittest.TestCase):
    """Scenario: No changes results in skip

    Given all docs/ files match the current wiki pages exactly
    When the step checks for changes after generation
    Then no commit is created
    And the step reports the wiki is up to date
    """

    def test_resolved_step_checks_for_changes(self):
        """Resolved step checks for changes before committing."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        self.assertIn('git status --porcelain', instructions)

    def test_resolved_step_skips_push_when_no_changes(self):
        """Resolved step skips push when no changes detected."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        # Check that instructions mention skipping when no changes
        self.assertIn('no changes', instructions.lower())
        self.assertIn('skip', instructions.lower())

    def test_resolved_step_reports_up_to_date(self):
        """Resolved step reports wiki is up to date when no changes."""
        step = _resolve_wiki_step()
        instructions = step['agent_instructions']
        self.assertIn('up to date', instructions.lower())


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    failed = len(result.failures) + len(result.errors)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'tests.json'), 'w') as f:
        json.dump({
            'status': 'PASS' if result.wasSuccessful() else 'FAIL',
            'passed': result.testsRun - failed,
            'failed': failed,
            'total': result.testsRun,
        }, f)
    sys.exit(0 if result.wasSuccessful() else 1)
