#!/usr/bin/env python3
"""Tests for the refresh_docs release step.

Covers unit test scenarios from features/release_refresh_docs.md:
- Stale documentation detected and updated
- Documentation is current, no changes needed
- Step never creates new doc files other than index
- Index page generated with four sections
- No doc appears in multiple sections
- Index uses relative markdown links

This release step has code: null (interactive). These tests verify the
resolved step's agent_instructions contain the correct behavioral
contracts that the agent relies on when executing the step interactively.
"""
import json
import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
sys.path.insert(0, PROJECT_ROOT)
from tools.release.resolve import resolve_checklist


def _resolve_step():
    """Resolve the refresh_docs step via the release resolver."""
    resolved, _warnings, _errors = resolve_checklist()
    matches = [s for s in resolved if s['id'] == 'refresh_docs']
    if not matches:
        raise ValueError('refresh_docs step not found in resolved checklist')
    return matches[0]


class TestStaleDocumentationDetectedAndUpdated(unittest.TestCase):
    """Scenario: Stale documentation detected and updated

    Given docs/testing-workflow-guide.md references a command that was
    renamed in the current implementation
    When the step executes the freshness review
    Then the stale reference is updated to the current command name
    And the change is committed with message "docs: update
    testing-workflow-guide.md for current implementation"
    """

    def test_agent_instructions_contain_freshness_review_phase(self):
        """Phase 1 Doc Freshness Review is defined in agent_instructions."""
        step = _resolve_step()
        self.assertIn('Doc Freshness Review', step['agent_instructions'])

    def test_agent_instructions_use_git_log_for_freshness(self):
        """Freshness detection uses git log to find last commit date."""
        step = _resolve_step()
        self.assertIn('git log', step['agent_instructions'])

    def test_agent_instructions_cross_reference_implementation(self):
        """Freshness review cross-references docs against implementation
        by identifying referenced files and checking for changes."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        # Instructions describe identifying what a doc covers and checking
        # referenced files for changes since the doc was last updated
        self.assertIn('referenced file', instructions.lower())
        self.assertIn('check what has changed', instructions.lower())

    def test_agent_instructions_specify_commit_message_format(self):
        """Commit message format matches spec: docs: update <filename>
        for current implementation."""
        step = _resolve_step()
        self.assertIn(
            'docs: update <filename> for current implementation',
            step['agent_instructions'])

    def test_agent_instructions_commit_each_doc_separately(self):
        """Each doc update is committed separately."""
        step = _resolve_step()
        self.assertIn(
            'Commit each doc update separately',
            step['agent_instructions'])


class TestDocumentationIsCurrentNoChangesNeeded(unittest.TestCase):
    """Scenario: Documentation is current, no changes needed

    Given all docs/**/*.md files accurately reflect the current
    implementation
    When the step executes the freshness review
    Then no commits are made for freshness updates
    And the step reports docs are current
    """

    def test_agent_instructions_confirm_current_when_no_staleness(self):
        """Instructions include flow for docs with no staleness."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        # Phase 1 step 5: "For docs with no staleness: confirm they are current"
        self.assertIn('no staleness', instructions.lower())

    def test_agent_instructions_include_no_commits_flow(self):
        """Instructions describe a path where no commits are needed."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        # When there are no changes, the git log --since check returns no commits
        self.assertIn('git log --oneline --since', instructions)

    def test_agent_instructions_present_freshness_report(self):
        """Instructions specify presenting a per-doc freshness report."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        self.assertIn('freshness report', instructions.lower())


class TestStepNeverCreatesNewDocFilesOtherThanIndex(unittest.TestCase):
    """Scenario: Step never creates new doc files other than index

    Given a documentation gap is detected during freshness review
    When the step considers remediation
    Then no new files are created in docs/ other than index.md
    And the gap is listed in the Recommendations section of the
    completion report
    """

    def test_step_is_interactive_only(self):
        """Step has code: null (interactive, no automated file creation)."""
        step = _resolve_step()
        self.assertIsNone(step['code'])

    def test_agent_instructions_include_recommendations_section(self):
        """Agent instructions mention the Recommendations section."""
        step = _resolve_step()
        self.assertIn('Recommendations', step['agent_instructions'])

    def test_agent_instructions_mention_completion_report(self):
        """Phase 3 Completion Report is defined in agent_instructions."""
        step = _resolve_step()
        self.assertIn('Completion Report', step['agent_instructions'])

    def test_agent_instructions_describe_scope_constraint(self):
        """Agent instructions describe the scope: only update existing
        docs and generate index.md, never create new doc files."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        # The instructions describe updating existing docs and generating index
        # The scope constraint is enforced by limiting operations to:
        # - Phase 1: Read and update existing docs
        # - Phase 2: Generate docs/index.md only
        self.assertIn('excluding index.md', instructions)
        self.assertIn('Generate docs/index.md', instructions)


class TestIndexPageGeneratedWithFourSections(unittest.TestCase):
    """Scenario: Index page generated with four sections

    Given docs/ contains documentation files
    When the step generates docs/index.md
    Then index.md contains sections "Agent Use", "CDD Dashboard",
    "Workflow & Process", and "Collaboration"
    """

    def test_agent_instructions_mention_agent_use_section(self):
        """Agent Use section is specified in instructions."""
        step = _resolve_step()
        self.assertIn('Agent Use', step['agent_instructions'])

    def test_agent_instructions_mention_cdd_dashboard_section(self):
        """CDD Dashboard section is specified in instructions."""
        step = _resolve_step()
        self.assertIn('CDD Dashboard', step['agent_instructions'])

    def test_agent_instructions_mention_workflow_process_section(self):
        """Workflow & Process section is specified in instructions."""
        step = _resolve_step()
        self.assertIn('Workflow & Process', step['agent_instructions'])

    def test_agent_instructions_mention_collaboration_section(self):
        """Collaboration section is specified in instructions."""
        step = _resolve_step()
        self.assertIn('Collaboration', step['agent_instructions'])

    def test_agent_instructions_specify_section_order(self):
        """Four sections appear in the correct order in instructions."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        agent_use_idx = instructions.index('Agent Use')
        cdd_idx = instructions.index('CDD Dashboard')
        workflow_idx = instructions.index('Workflow & Process')
        collab_idx = instructions.index('Collaboration')
        self.assertLess(agent_use_idx, cdd_idx)
        self.assertLess(cdd_idx, workflow_idx)
        self.assertLess(workflow_idx, collab_idx)

    def test_agent_instructions_specify_index_generation(self):
        """Instructions describe generating docs/index.md."""
        step = _resolve_step()
        self.assertIn('docs/index.md', step['agent_instructions'])

    def test_phase_2_defines_index_page_generation(self):
        """Phase 2 is specifically named Index Page Generation."""
        step = _resolve_step()
        self.assertIn('Index Page Generation', step['agent_instructions'])


class TestNoDocAppearsInMultipleSections(unittest.TestCase):
    """Scenario: No doc appears in multiple sections

    Given docs/ contains documentation files
    When the step generates docs/index.md
    Then each doc filename appears exactly once in the index
    """

    def test_agent_instructions_specify_exactly_one_section(self):
        """Instructions state each doc appears in exactly one section."""
        step = _resolve_step()
        self.assertIn(
            'exactly one section',
            step['agent_instructions'].lower())

    def test_agent_instructions_specify_most_specific_match(self):
        """Instructions specify preferring the most specific match."""
        step = _resolve_step()
        self.assertIn(
            'most specific match',
            step['agent_instructions'].lower())

    def test_agent_instructions_define_classification_rules(self):
        """Instructions define classification criteria for each section."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        # Each section has a classification description
        self.assertIn('agent role', instructions.lower())
        self.assertIn('dashboard', instructions.lower())
        self.assertIn('end-to-end workflow', instructions.lower())
        self.assertIn('collaboration', instructions.lower())


class TestIndexUsesRelativeMarkdownLinks(unittest.TestCase):
    """Scenario: Index uses relative markdown links

    Given docs/ contains documentation files
    When the step generates docs/index.md
    Then each entry uses the link format "[Title](filename.md)"
    """

    def test_agent_instructions_specify_link_format(self):
        """Instructions specify the [Title](filename.md) link format."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        # The instructions specify the entry format with markdown links
        self.assertIn('[Title](filename.md)', instructions)

    def test_agent_instructions_specify_entry_format(self):
        """Instructions define the full entry format with description."""
        step = _resolve_step()
        instructions = step['agent_instructions']
        # Each entry as: * [Title](filename.md) -- one-line description
        self.assertIn('one-line description', instructions.lower())

    def test_step_code_is_null_interactive(self):
        """Step is interactive-only (code: null), index generated by agent."""
        step = _resolve_step()
        self.assertIsNone(step['code'])


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
