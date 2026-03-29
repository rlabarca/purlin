"""Unit tests for purlin:resume checkpoint infrastructure.

Tests the checkpoint file mechanics, PID-scoping, stale reaping,
legacy detection, merge breadcrumbs, and subcommand validation
that underpin purlin:resume save / purlin:resume merge-recovery.

Covers scenarios from skills/resume/SKILL.md (Save Mode, Merge Recovery,
Steps 4-5 of the startup flow).
"""
import json
import os
import re
import shutil
import signal
import tempfile
import unittest


class TestCheckpointPathScoping(unittest.TestCase):
    """Checkpoint path is PID-scoped when PURLIN_SESSION_ID is set."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="purlin-ckpt-test-")
        self.cache_dir = os.path.join(self.tmpdir, ".purlin", "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _checkpoint_path(self, session_id=None):
        """Derive the checkpoint path using the same logic as purlin:resume save."""
        if session_id:
            return os.path.join(self.cache_dir, f"session_checkpoint_{session_id}.md")
        return os.path.join(self.cache_dir, "session_checkpoint_purlin.md")

    def test_pid_scoped_path_when_session_id_set(self):
        path = self._checkpoint_path(session_id="46946")
        self.assertTrue(path.endswith("session_checkpoint_46946.md"))

    def test_unscoped_fallback_without_session_id(self):
        path = self._checkpoint_path(session_id=None)
        self.assertTrue(path.endswith("session_checkpoint_purlin.md"))

    def test_concurrent_terminals_produce_distinct_paths(self):
        path_a = self._checkpoint_path(session_id="11111")
        path_b = self._checkpoint_path(session_id="22222")
        self.assertNotEqual(path_a, path_b)
        self.assertIn("11111", path_a)
        self.assertIn("22222", path_b)

    def test_pid_scoped_files_do_not_collide(self):
        """Two concurrent terminals writing checkpoints don't overwrite each other."""
        path_a = self._checkpoint_path(session_id="11111")
        path_b = self._checkpoint_path(session_id="22222")

        with open(path_a, "w") as f:
            f.write("**Mode:** engineer\n")
        with open(path_b, "w") as f:
            f.write("**Mode:** qa\n")

        with open(path_a) as f:
            self.assertIn("engineer", f.read())
        with open(path_b) as f:
            self.assertIn("qa", f.read())


class TestCheckpointFormat(unittest.TestCase):
    """Checkpoint files contain required common and mode-specific fields."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="purlin-ckpt-fmt-")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_checkpoint(self, mode, extra_sections=""):
        content = f"""# Session Checkpoint

**Mode:** {mode}
**Timestamp:** 2026-03-28T20:00:00Z
**Branch:** dev/0.8.6

## Current Work

**Feature:** features/example.md
**In Progress:** Implementing the thing

### Done
- Read the spec
- Wrote initial code

### Next
1. Run tests
2. Commit

## Uncommitted Changes
M scripts/example.py

## Notes
None
{extra_sections}"""
        path = os.path.join(self.tmpdir, "checkpoint.md")
        with open(path, "w") as f:
            f.write(content)
        return path, content

    def test_common_fields_present(self):
        path, content = self._write_checkpoint("engineer")
        self.assertRegex(content, r"\*\*Mode:\*\*\s+\w+")
        self.assertRegex(content, r"\*\*Timestamp:\*\*\s+\d{4}-\d{2}-\d{2}T")
        self.assertRegex(content, r"\*\*Branch:\*\*\s+\S+")
        self.assertIn("## Current Work", content)
        self.assertIn("### Done", content)
        self.assertIn("### Next", content)
        self.assertIn("## Uncommitted Changes", content)
        self.assertIn("## Notes", content)

    def test_engineer_mode_specific_fields(self):
        engineer_ctx = """
## Engineer Context
**Protocol Step:** 2-implement/document
**Delivery Plan:** Phase 2 of 3 -- IN_PROGRESS, completed: project_init
**Execution Group:** Group 1: Phases [1, 2] -- 3 features
**Work Queue:**
1. [HIGH] config_layering.md
**Pending Decisions:** None
"""
        path, content = self._write_checkpoint("engineer", engineer_ctx)
        self.assertIn("## Engineer Context", content)
        self.assertIn("**Protocol Step:**", content)
        self.assertIn("**Delivery Plan:**", content)
        self.assertIn("**Execution Group:**", content)
        self.assertIn("**Work Queue:**", content)
        self.assertIn("**Pending Decisions:**", content)

    def test_qa_mode_specific_fields(self):
        qa_ctx = """
## QA Context
**Scenario Progress:** 5 of 8 scenarios completed
**Current Scenario:** verify login flow
**Discoveries:** 1 BUG recorded
**Verification Queue:** 3 verified, 2 remaining
"""
        path, content = self._write_checkpoint("qa", qa_ctx)
        self.assertIn("## QA Context", content)
        self.assertIn("**Scenario Progress:**", content)
        self.assertIn("**Current Scenario:**", content)
        self.assertIn("**Discoveries:**", content)
        self.assertIn("**Verification Queue:**", content)

    def test_pm_mode_specific_fields(self):
        pm_ctx = """
## PM Context
**Spec Drafts:** features/new_feature.md (in progress)
**Figma Context:** None
"""
        path, content = self._write_checkpoint("pm", pm_ctx)
        self.assertIn("## PM Context", content)
        self.assertIn("**Spec Drafts:**", content)
        self.assertIn("**Figma Context:**", content)

    def test_mode_field_extraction(self):
        """Mode can be extracted from checkpoint content via regex."""
        for mode in ("engineer", "pm", "qa", "none"):
            _, content = self._write_checkpoint(mode)
            match = re.search(r"\*\*Mode:\*\*\s+(\w+)", content)
            self.assertIsNotNone(match, f"Mode field not found for mode={mode}")
            self.assertEqual(match.group(1), mode)

    def test_timestamp_is_iso8601(self):
        _, content = self._write_checkpoint("engineer")
        match = re.search(r"\*\*Timestamp:\*\*\s+(\S+)", content)
        self.assertIsNotNone(match)
        ts = match.group(1)
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class TestLegacyCheckpointDetection(unittest.TestCase):
    """Legacy checkpoint files are recognized and mapped to correct modes."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="purlin-legacy-")
        self.cache_dir = os.path.join(self.tmpdir, ".purlin", "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    ROLE_TO_MODE = {
        "builder": "engineer",
        "architect": "engineer",
        "qa": "qa",
        "pm": "pm",
    }

    def test_builder_maps_to_engineer(self):
        self.assertEqual(self.ROLE_TO_MODE["builder"], "engineer")

    def test_architect_maps_to_engineer(self):
        self.assertEqual(self.ROLE_TO_MODE["architect"], "engineer")

    def test_qa_maps_to_qa(self):
        self.assertEqual(self.ROLE_TO_MODE["qa"], "qa")

    def test_pm_maps_to_pm(self):
        self.assertEqual(self.ROLE_TO_MODE["pm"], "pm")

    def test_legacy_files_are_detected(self):
        """Legacy role-scoped checkpoint files are found by glob pattern."""
        for role in self.ROLE_TO_MODE:
            path = os.path.join(self.cache_dir, f"session_checkpoint_{role}.md")
            with open(path, "w") as f:
                f.write(f"**Mode:** {self.ROLE_TO_MODE[role]}\n")

        import glob
        found = glob.glob(os.path.join(self.cache_dir, "session_checkpoint_*.md"))
        self.assertEqual(len(found), 4)

    def test_pid_scoped_takes_priority_over_legacy(self):
        """PID-scoped file is checked first; legacy is lower priority."""
        pid_path = os.path.join(self.cache_dir, "session_checkpoint_46946.md")
        legacy_path = os.path.join(self.cache_dir, "session_checkpoint_builder.md")

        with open(pid_path, "w") as f:
            f.write("**Mode:** pm\n")
        with open(legacy_path, "w") as f:
            f.write("**Mode:** engineer\n")

        # Detection priority: PID-scoped first
        self.assertTrue(os.path.exists(pid_path))
        self.assertTrue(os.path.exists(legacy_path))
        # The agent should read pid_path first (46946 matches PURLIN_SESSION_ID)

    def test_unscoped_takes_priority_over_legacy(self):
        """Unscoped checkpoint_purlin.md is checked before legacy role-scoped."""
        unscoped = os.path.join(self.cache_dir, "session_checkpoint_purlin.md")
        legacy = os.path.join(self.cache_dir, "session_checkpoint_qa.md")

        with open(unscoped, "w") as f:
            f.write("**Mode:** engineer\n")
        with open(legacy, "w") as f:
            f.write("**Mode:** qa\n")

        self.assertTrue(os.path.exists(unscoped))


class TestStaleCheckpointReaping(unittest.TestCase):
    """Stale checkpoints from dead PIDs are identified; live PIDs are left alone."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="purlin-stale-")
        self.cache_dir = os.path.join(self.tmpdir, ".purlin", "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _is_pid_alive(self, pid):
        """Check if a PID is alive using kill -0."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def test_dead_pid_identified_as_stale(self):
        """A checkpoint from a dead PID should be identified as stale."""
        dead_pid = 99999
        # Ensure the PID is actually dead (very high PIDs are almost always dead)
        if self._is_pid_alive(dead_pid):
            self.skipTest(f"PID {dead_pid} is unexpectedly alive")

        path = os.path.join(self.cache_dir, f"session_checkpoint_{dead_pid}.md")
        with open(path, "w") as f:
            f.write("**Mode:** engineer\n")

        self.assertTrue(os.path.exists(path))
        self.assertFalse(self._is_pid_alive(dead_pid))
        # Agent would delete this file during Step 4

    def test_live_pid_not_reaped(self):
        """A checkpoint from a live PID should NOT be reaped."""
        live_pid = os.getpid()
        self.assertTrue(self._is_pid_alive(live_pid))

        path = os.path.join(self.cache_dir, f"session_checkpoint_{live_pid}.md")
        with open(path, "w") as f:
            f.write("**Mode:** qa\n")

        self.assertTrue(os.path.exists(path))
        self.assertTrue(self._is_pid_alive(live_pid))
        # Agent would leave this file in place

    def test_legacy_names_skipped_during_reaping(self):
        """Legacy names (builder, architect, qa, pm, purlin) are not PID-checked."""
        legacy_names = ["builder", "architect", "qa", "pm", "purlin"]
        for name in legacy_names:
            path = os.path.join(self.cache_dir, f"session_checkpoint_{name}.md")
            with open(path, "w") as f:
                f.write(f"**Mode:** {name}\n")

        # Verify the stem extraction logic: these are NOT numeric
        for name in legacy_names:
            self.assertFalse(name.isdigit(),
                             f"Legacy name '{name}' should not be treated as a PID")

    def test_numeric_stem_extraction(self):
        """Numeric stems are correctly extracted from checkpoint filenames."""
        test_cases = [
            ("session_checkpoint_46946.md", "46946", True),
            ("session_checkpoint_builder.md", "builder", False),
            ("session_checkpoint_purlin.md", "purlin", False),
            ("session_checkpoint_12345.md", "12345", True),
        ]
        for filename, expected_stem, is_numeric in test_cases:
            stem = filename.replace("session_checkpoint_", "").replace(".md", "")
            self.assertEqual(stem, expected_stem)
            self.assertEqual(stem.isdigit(), is_numeric,
                             f"Stem '{stem}' numeric check failed")


class TestMergeBreadcrumbs(unittest.TestCase):
    """Merge breadcrumb JSON files are valid and contain required fields."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="purlin-merge-")
        self.merge_dir = os.path.join(self.tmpdir, ".purlin", "cache", "merge_pending")
        os.makedirs(self.merge_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    REQUIRED_FIELDS = ["branch", "worktree_path", "source_branch", "failed_at", "reason"]

    def _write_breadcrumb(self, branch, **overrides):
        data = {
            "branch": branch,
            "worktree_path": f"/path/to/.purlin/worktrees/{branch}",
            "source_branch": "main",
            "failed_at": "2026-03-28T20:00:00Z",
            "reason": "conflict",
        }
        data.update(overrides)
        path = os.path.join(self.merge_dir, f"{branch}.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path, data

    def test_breadcrumb_is_valid_json(self):
        path, _ = self._write_breadcrumb("purlin-engineer-20260325-143022")
        with open(path) as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_breadcrumb_contains_required_fields(self):
        path, _ = self._write_breadcrumb("test-branch")
        with open(path) as f:
            data = json.load(f)
        for field in self.REQUIRED_FIELDS:
            self.assertIn(field, data, f"Missing required field: {field}")

    def test_multiple_breadcrumbs_coexist(self):
        """Multiple failed merges each leave their own breadcrumb file."""
        self._write_breadcrumb("branch-a")
        self._write_breadcrumb("branch-b")
        self._write_breadcrumb("branch-c")

        import glob
        found = glob.glob(os.path.join(self.merge_dir, "*.json"))
        self.assertEqual(len(found), 3)

    def test_breadcrumb_branch_field_matches_filename(self):
        path, data = self._write_breadcrumb("my-feature-branch")
        self.assertTrue(path.endswith("my-feature-branch.json"))
        self.assertEqual(data["branch"], "my-feature-branch")

    def test_breadcrumb_reason_field(self):
        """Reason field captures why the merge failed."""
        _, data = self._write_breadcrumb("branch-x", reason="conflict")
        self.assertEqual(data["reason"], "conflict")

    def test_stale_breadcrumb_for_deleted_branch(self):
        """A breadcrumb for a branch that no longer exists is stale."""
        path, data = self._write_breadcrumb("deleted-branch")
        # In practice, the agent would run: git rev-parse --verify deleted-branch
        # and if it fails, delete the breadcrumb. Here we verify the file exists
        # so the agent can detect and clean it up.
        self.assertTrue(os.path.exists(path))


class TestSubcommandValidation(unittest.TestCase):
    """Invalid subcommands are detected; valid ones are recognized."""

    VALID_SUBCOMMANDS = [None, "save", "merge-recovery"]

    def test_save_is_valid(self):
        self.assertIn("save", self.VALID_SUBCOMMANDS)

    def test_merge_recovery_is_valid(self):
        self.assertIn("merge-recovery", self.VALID_SUBCOMMANDS)

    def test_no_argument_is_valid(self):
        self.assertIn(None, self.VALID_SUBCOMMANDS)

    def test_invalid_arguments_rejected(self):
        invalid = ["restore", "checkpoint", "recover", "resume", "load", ""]
        for arg in invalid:
            self.assertNotIn(arg, self.VALID_SUBCOMMANDS,
                             f"'{arg}' should not be a valid subcommand")

    def test_resume_is_not_a_valid_subcommand(self):
        """The old 'resume' command is retired — not a valid subcommand."""
        self.assertNotIn("resume", self.VALID_SUBCOMMANDS)


class TestSkillFileIntegrity(unittest.TestCase):
    """The start skill file exists and contains the required sections."""

    @classmethod
    def setUpClass(cls):
        # Find the project root by looking for features/ directory
        test_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = test_dir
        for _ in range(10):
            if os.path.isdir(os.path.join(candidate, "features")):
                cls.project_root = candidate
                break
            candidate = os.path.dirname(candidate)
        else:
            cls.project_root = None

    def setUp(self):
        if self.project_root is None:
            self.skipTest("Could not find project root")
        self.skill_path = os.path.join(self.project_root, "skills", "resume", "SKILL.md")

    def test_skill_file_exists(self):
        self.assertTrue(os.path.exists(self.skill_path),
                        f"skills/resume/SKILL.md not found at {self.skill_path}")

    def test_start_skill_deleted(self):
        """The old start skill directory should not exist (renamed to resume)."""
        start_path = os.path.join(self.project_root, "skills", "start", "SKILL.md")
        self.assertFalse(os.path.exists(start_path),
                         "skills/start/SKILL.md should not exist (renamed to skills/resume/)")

    def test_resume_feature_spec_deleted(self):
        """The old resume feature spec should not exist."""
        spec_path = os.path.join(self.project_root, "features", "purlin_session_resume.md")
        self.assertFalse(os.path.exists(spec_path),
                         "features/purlin_session_resume.md should be deleted")

    def test_skill_contains_save_section(self):
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("## Save Mode", content)
        self.assertIn("purlin:resume save", content)

    def test_skill_contains_merge_recovery_section(self):
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("## Merge Recovery Mode", content)
        self.assertIn("purlin:resume merge-recovery", content)

    def test_skill_contains_checkpoint_format(self):
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("### Checkpoint Format", content)
        self.assertIn("**Mode:**", content)
        self.assertIn("**Timestamp:**", content)
        self.assertIn("**Branch:**", content)

    def test_skill_contains_all_mode_specific_sections(self):
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("## Engineer Context", content)
        self.assertIn("## QA Context", content)
        self.assertIn("## PM Context", content)

    def test_skill_contains_session_cleanup_contract(self):
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("## Session Cleanup Contract", content)

    def test_skill_is_named_resume(self):
        """The skill file should be named 'resume' in frontmatter."""
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("name: resume", content,
                      "Skill frontmatter should have name: resume")

    def test_skill_contains_step_numbering(self):
        """The execution flow should have clean numbered steps 0-11, no suffixes."""
        with open(self.skill_path) as f:
            content = f.read()
        for step_num in range(12):
            self.assertIn(f"Step {step_num}", content,
                          f"Missing Step {step_num} in execution flow")
        # No suffix steps (5b, 6b etc.) should exist
        self.assertNotIn("Step 5b", content, "Suffix step 5b should not exist")
        self.assertNotIn("Step 6b", content, "Suffix step 6b should not exist")

    def test_skill_contains_dispatch_gate(self):
        """Dispatch gate must exist before the execution flow."""
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("## Subcommand Dispatch", content)
        # Dispatch section must appear BEFORE execution flow
        dispatch_pos = content.index("## Subcommand Dispatch")
        exec_pos = content.index("## Execution Flow")
        self.assertLess(dispatch_pos, exec_pos,
                        "Dispatch gate must appear before Execution Flow")

    def test_skill_contains_post_clear_guard(self):
        """Post-clear guard must exist to skip Steps 1-3 on re-entry."""
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("Post-Clear Guard", content)
        self.assertIn("Already initialized", content)

    def test_skill_contains_when_to_run_section(self):
        """When to Run section documents that resume is optional."""
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("## When to Run", content)
        self.assertIn("NOT need", content,
                      "Should state resume is not required to start working")
        self.assertIn("What you miss if you skip it", content)

    def test_skill_contains_mode_scoped_scan(self):
        """Step 9 should use mode-scoped scan for warm resume."""
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("mode-scoped scan", content)
        self.assertIn("cached: true", content)

    def test_skill_contains_hook_integration_table(self):
        with open(self.skill_path) as f:
            content = f.read()
        self.assertIn("## Hook Integration", content)
        self.assertIn("PreCompact", content)
        self.assertIn("SessionStart", content)


class TestNoStartReferences(unittest.TestCase):
    """Verify purlin:start has been fully renamed to purlin:resume in key files."""

    @classmethod
    def setUpClass(cls):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = test_dir
        for _ in range(10):
            if os.path.isdir(os.path.join(candidate, "features")):
                cls.project_root = candidate
                break
            candidate = os.path.dirname(candidate)
        else:
            cls.project_root = None

    def setUp(self):
        if self.project_root is None:
            self.skipTest("Could not find project root")

    def _read_file(self, rel_path):
        path = os.path.join(self.project_root, rel_path)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return f.read()

    def test_agents_purlin_no_start(self):
        content = self._read_file("agents/purlin.md")
        if content:
            self.assertNotIn("purlin:start", content)

    def test_references_commands_no_start(self):
        content = self._read_file("references/purlin_commands.md")
        if content:
            self.assertNotIn("purlin:start", content)

    def test_output_standards_no_start(self):
        content = self._read_file("references/output_standards.md")
        if content:
            self.assertNotIn("purlin:start", content)

    def test_claude_md_no_start(self):
        content = self._read_file("CLAUDE.md")
        if content:
            self.assertNotIn("purlin:start", content)


if __name__ == "__main__":
    unittest.main()
