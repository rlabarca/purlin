"""Automated tests for the handoff checklist system.

Tests all automated scenarios from features/workflow_checklist_system.md.
Results written to tests/workflow_checklist_system/tests.json.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))

# Add tools directories to path
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools', 'release'))

from run import filter_by_role, evaluate_step, infer_role_from_branch, run_handoff
from resolve import resolve_checklist


class TestHandoffCLIFiltersStepsByRole(unittest.TestCase):
    """Scenario: Handoff CLI Filters Steps by Role

    Given the handoff global_steps.json contains steps with roles: ["all"],
          ["architect"], ["builder"], and ["qa"],
    When run.sh --role architect is invoked,
    Then only steps with roles: ["all"] or ["architect"] are included,
    And steps with roles: ["builder"] or ["qa"] are excluded.
    """

    def setUp(self):
        """Load global_steps.json and resolve all steps."""
        self.resolved, _, _ = resolve_checklist(checklist_type="handoff")
        # Verify we have steps for all roles in the source data
        all_roles_seen = set()
        for step in self.resolved:
            roles = step.get("roles") or []
            for r in roles:
                all_roles_seen.add(r)
        self.assertIn("all", all_roles_seen)
        self.assertIn("architect", all_roles_seen)
        self.assertIn("builder", all_roles_seen)
        self.assertIn("qa", all_roles_seen)

    def test_architect_gets_only_all_and_architect_steps(self):
        steps = filter_by_role(self.resolved, "architect")
        for step in steps:
            roles = step.get("roles", [])
            self.assertTrue(
                "all" in roles or "architect" in roles,
                f"Step {step['id']} has roles={roles}, expected 'all' or 'architect'"
            )

    def test_architect_excludes_builder_and_qa_steps(self):
        steps = filter_by_role(self.resolved, "architect")
        step_ids = {s["id"] for s in steps}
        # These should NOT be in architect's list
        self.assertNotIn("purlin.handoff.tests_pass", step_ids)
        self.assertNotIn("purlin.handoff.impl_notes_updated", step_ids)
        self.assertNotIn("purlin.handoff.status_commit_made", step_ids)
        self.assertNotIn("purlin.handoff.scenarios_complete", step_ids)
        self.assertNotIn("purlin.handoff.discoveries_addressed", step_ids)
        self.assertNotIn("purlin.handoff.complete_commit_made", step_ids)

    def test_builder_gets_only_all_and_builder_steps(self):
        steps = filter_by_role(self.resolved, "builder")
        for step in steps:
            roles = step.get("roles", [])
            self.assertTrue(
                "all" in roles or "builder" in roles,
                f"Step {step['id']} has roles={roles}, expected 'all' or 'builder'"
            )

    def test_qa_gets_only_all_and_qa_steps(self):
        steps = filter_by_role(self.resolved, "qa")
        for step in steps:
            roles = step.get("roles", [])
            self.assertTrue(
                "all" in roles or "qa" in roles,
                f"Step {step['id']} has roles={roles}, expected 'all' or 'qa'"
            )

    def test_each_role_gets_correct_count(self):
        # 3 shared + 3 role-specific = 6 per role
        for role in ("architect", "builder", "qa"):
            steps = filter_by_role(self.resolved, role)
            self.assertEqual(len(steps), 6,
                             f"{role} should have 6 steps, got {len(steps)}")


class TestHandoffCLIPassesWhenAllAutoStepsPass(unittest.TestCase):
    """Scenario: Handoff CLI Passes When All Auto-Steps Pass

    Given the current branch is spec/task-crud,
    And the working directory is clean,
    And all modified features pass the Critic Spec Gate,
    When run.sh --role architect is invoked,
    Then the CLI exits with code 0,
    And prints a summary with all steps PASS.
    """

    def setUp(self):
        """Create a temp project where all auto steps pass."""
        self.temp_dir = tempfile.mkdtemp()
        # Initialize git repo
        subprocess.run(["git", "init", "-q"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                        cwd=self.temp_dir, check=True)
        # Create project structure
        os.makedirs(os.path.join(self.temp_dir, ".purlin"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "features"), exist_ok=True)
        with open(os.path.join(self.temp_dir, ".purlin", "config.json"), 'w') as f:
            json.dump({"tools_root": "tools"}, f)
        with open(os.path.join(self.temp_dir, "features", "test.md"), 'w') as f:
            f.write("# Test\n")
        # Create branch and commit
        subprocess.run(["git", "add", "-A"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", "spec/task-crud"],
                        cwd=self.temp_dir, check=True)
        # Create a custom global_steps.json with only passing code steps
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"), exist_ok=True)
        steps_data = {"steps": [
            {
                "id": "purlin.handoff.git_clean",
                "friendly_name": "Git Working Directory Clean",
                "description": "No uncommitted changes",
                "code": "git diff --exit-code && git diff --cached --exit-code",
                "agent_instructions": None,
                "roles": ["all"]
            },
            {
                "id": "purlin.handoff.spec_gate_pass",
                "friendly_name": "Spec Gate Pass",
                "description": "All specs pass",
                "code": "true",
                "agent_instructions": None,
                "roles": ["architect"]
            }
        ]}
        with open(os.path.join(self.temp_dir, "tools", "handoff",
                               "global_steps.json"), 'w') as f:
            json.dump(steps_data, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_all_auto_steps_pass_exits_0(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "run.py"),
             "--role", "architect",
             "--project-root", self.temp_dir],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                         f"Expected exit 0 but got {result.returncode}.\n"
                         f"stdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertIn("PASS", result.stdout)
        self.assertNotIn("FAIL", result.stdout)
        self.assertNotIn("PENDING", result.stdout)


class TestHandoffCLIExits1WhenAnyStepFails(unittest.TestCase):
    """Scenario: Handoff CLI Exits 1 When Any Step Fails

    Given the current branch is build/task-crud,
    And tests/task_crud/tests.json does not exist,
    When run.sh --role builder is invoked,
    Then the CLI exits with code 1,
    And reports the failing step (purlin.handoff.tests_pass) as FAIL.
    """

    def setUp(self):
        """Create a temp project with a step that fails."""
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                        cwd=self.temp_dir, check=True)
        os.makedirs(os.path.join(self.temp_dir, ".purlin"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "features"), exist_ok=True)
        with open(os.path.join(self.temp_dir, ".purlin", "config.json"), 'w') as f:
            json.dump({"tools_root": "tools"}, f)
        with open(os.path.join(self.temp_dir, "features", "test.md"), 'w') as f:
            f.write("# Test\n")
        subprocess.run(["git", "add", "-A"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", "build/task-crud"],
                        cwd=self.temp_dir, check=True)
        # Create steps with one that will fail
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"), exist_ok=True)
        steps_data = {"steps": [
            {
                "id": "purlin.handoff.git_clean",
                "friendly_name": "Git Working Directory Clean",
                "description": "No uncommitted changes",
                "code": "git diff --exit-code && git diff --cached --exit-code",
                "agent_instructions": None,
                "roles": ["all"]
            },
            {
                "id": "purlin.handoff.tests_pass",
                "friendly_name": "Tests Pass",
                "description": "Tests must exist and pass",
                "code": "test -f tests/task_crud/tests.json",
                "agent_instructions": "Verify tests.json exists.",
                "roles": ["builder"]
            }
        ]}
        with open(os.path.join(self.temp_dir, "tools", "handoff",
                               "global_steps.json"), 'w') as f:
            json.dump(steps_data, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_failing_step_exits_1(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "run.py"),
             "--role", "builder",
             "--project-root", self.temp_dir],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1,
                         f"Expected exit 1 but got {result.returncode}.\n"
                         f"stdout: {result.stdout}")
        self.assertIn("FAIL", result.stdout)
        self.assertIn("Tests Pass", result.stdout)


class TestRoleInferredFromBranchName(unittest.TestCase):
    """Scenario: Role Inferred from Branch Name

    Given the current branch is qa/task-filtering,
    When /pl-handoff-check is invoked without a --role argument,
    Then the checklist runs with role="qa",
    And only QA-specific and shared steps are included.
    """

    def setUp(self):
        """Create temp git repos on different branches."""
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                        cwd=self.temp_dir, check=True)
        os.makedirs(os.path.join(self.temp_dir, ".purlin"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "features"), exist_ok=True)
        with open(os.path.join(self.temp_dir, ".purlin", "config.json"), 'w') as f:
            json.dump({"tools_root": "tools"}, f)
        with open(os.path.join(self.temp_dir, "features", "test.md"), 'w') as f:
            f.write("# Test\n")
        subprocess.run(["git", "add", "-A"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                        cwd=self.temp_dir, check=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_qa_branch_infers_qa_role(self):
        subprocess.run(["git", "checkout", "-q", "-b", "qa/task-filtering"],
                        cwd=self.temp_dir, check=True)
        role = infer_role_from_branch(self.temp_dir)
        self.assertEqual(role, "qa")

    def test_spec_branch_infers_architect_role(self):
        subprocess.run(["git", "checkout", "-q", "-b", "spec/task-crud"],
                        cwd=self.temp_dir, check=True)
        role = infer_role_from_branch(self.temp_dir)
        self.assertEqual(role, "architect")

    def test_build_branch_infers_builder_role(self):
        subprocess.run(["git", "checkout", "-q", "-b", "build/task-crud"],
                        cwd=self.temp_dir, check=True)
        role = infer_role_from_branch(self.temp_dir)
        self.assertEqual(role, "builder")

    def test_main_branch_returns_none(self):
        role = infer_role_from_branch(self.temp_dir)
        self.assertIsNone(role)

    def test_qa_branch_cli_runs_qa_checklist(self):
        """Full integration: run without --role on qa/ branch."""
        subprocess.run(["git", "checkout", "-q", "-b", "qa/task-filtering"],
                        cwd=self.temp_dir, check=True)
        # Create steps with a QA step that passes
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"),
                    exist_ok=True)
        steps_data = {"steps": [
            {
                "id": "purlin.handoff.git_clean",
                "friendly_name": "Git Working Directory Clean",
                "description": "No uncommitted changes",
                "code": "git diff --exit-code && git diff --cached --exit-code",
                "agent_instructions": None,
                "roles": ["all"]
            },
            {
                "id": "purlin.handoff.scenarios_complete",
                "friendly_name": "Manual Scenarios Complete",
                "description": "All scenarios verified",
                "code": "true",
                "agent_instructions": None,
                "roles": ["qa"]
            },
            {
                "id": "purlin.handoff.tests_pass",
                "friendly_name": "Tests Pass",
                "description": "Builder step — should be excluded",
                "code": "true",
                "agent_instructions": None,
                "roles": ["builder"]
            }
        ]}
        with open(os.path.join(self.temp_dir, "tools", "handoff",
                               "global_steps.json"), 'w') as f:
            json.dump(steps_data, f)

        # Run without --role flag
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "run.py"),
             "--project-root", self.temp_dir],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                         f"Expected exit 0.\nstdout: {result.stdout}\n"
                         f"stderr: {result.stderr}")
        # QA-specific step should be present
        self.assertIn("Manual Scenarios Complete", result.stdout)
        # Builder-specific step should be absent
        self.assertNotIn("Tests Pass", result.stdout)


class TestPlWorkPushMergesWhenAllChecksPass(unittest.TestCase):
    """Scenario: pl-work-push Merges Branch When All Checks Pass

    Given the current branch is build/collab
    And tools/handoff/run.sh exits with code 0
    And the main checkout is on branch main
    When /pl-work-push is invoked
    Then git merge --ff-only build/collab is executed from PROJECT_ROOT
    And the command succeeds

    Tests the underlying components: run.py exits 0 for a passing checklist,
    and the skill file instructs the agent to perform ff-only merge.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                        cwd=self.temp_dir, check=True)
        os.makedirs(os.path.join(self.temp_dir, ".purlin"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "features"), exist_ok=True)
        with open(os.path.join(self.temp_dir, ".purlin", "config.json"), 'w') as f:
            json.dump({"tools_root": "tools"}, f)
        with open(os.path.join(self.temp_dir, "features", "test.md"), 'w') as f:
            f.write("# Test\n")
        subprocess.run(["git", "add", "-A"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", "build/collab"],
                        cwd=self.temp_dir, check=True)
        # Create a passing handoff step
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"), exist_ok=True)
        steps_data = {"steps": [
            {"id": "purlin.handoff.git_clean",
             "friendly_name": "Git Clean", "description": "Clean",
             "code": "git diff --exit-code && git diff --cached --exit-code",
             "agent_instructions": None, "roles": ["all"]}
        ]}
        with open(os.path.join(self.temp_dir, "tools", "handoff",
                               "global_steps.json"), 'w') as f:
            json.dump(steps_data, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_handoff_passes_on_build_branch(self):
        """run.py exits 0 when checklist passes on build/* branch."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "run.py"),
             "--project-root", self.temp_dir],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                         f"Expected exit 0.\nstdout: {result.stdout}\n"
                         f"stderr: {result.stderr}")

    def test_skill_file_instructs_ff_only_merge(self):
        """The pl-work-push skill file specifies --ff-only merge."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-push.md")
        self.assertTrue(os.path.exists(skill_path),
                        "pl-work-push.md skill file must exist")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("--ff-only", content)
        self.assertIn("merge", content)


class TestPlWorkPushBlocksMergeWhenChecksFail(unittest.TestCase):
    """Scenario: pl-work-push Blocks Merge When Handoff Checks Fail

    Given the current branch is build/collab
    And tools/handoff/run.sh exits with code 1
    When /pl-work-push is invoked
    Then the failing items are printed
    And no merge is executed
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                        cwd=self.temp_dir, check=True)
        os.makedirs(os.path.join(self.temp_dir, ".purlin"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "features"), exist_ok=True)
        with open(os.path.join(self.temp_dir, ".purlin", "config.json"), 'w') as f:
            json.dump({"tools_root": "tools"}, f)
        with open(os.path.join(self.temp_dir, "features", "test.md"), 'w') as f:
            f.write("# Test\n")
        subprocess.run(["git", "add", "-A"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", "build/collab"],
                        cwd=self.temp_dir, check=True)
        # Create an uncommitted file to make git_clean fail
        with open(os.path.join(self.temp_dir, "dirty.txt"), 'w') as f:
            f.write("dirty\n")
        subprocess.run(["git", "add", "dirty.txt"], cwd=self.temp_dir, check=True)
        # Create steps
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"), exist_ok=True)
        steps_data = {"steps": [
            {"id": "purlin.handoff.git_clean",
             "friendly_name": "Git Clean", "description": "Clean",
             "code": "git diff --exit-code && git diff --cached --exit-code",
             "agent_instructions": None, "roles": ["all"]}
        ]}
        with open(os.path.join(self.temp_dir, "tools", "handoff",
                               "global_steps.json"), 'w') as f:
            json.dump(steps_data, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_handoff_fails_and_exits_1(self):
        """run.py exits 1 when checklist fails — merge should not happen."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "run.py"),
             "--project-root", self.temp_dir],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)


class TestPlWorkPullAbortsWhenDirty(unittest.TestCase):
    """Scenario: pl-work-pull Aborts When Working Tree Is Dirty

    Given the current worktree has uncommitted changes
    When /pl-work-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git merge is executed
    """

    def test_skill_file_checks_clean_state(self):
        """The pl-work-pull skill file instructs checking for clean state."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-pull.md")
        self.assertTrue(os.path.exists(skill_path),
                        "pl-work-pull.md skill file must exist")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("Commit or stash changes before pulling", content)
        self.assertIn("git status --porcelain", content)


class TestPlWorkPullRebasesMainWhenBehind(unittest.TestCase):
    """Scenario: pl-work-pull Rebases Main Into Worktree When Branch Is BEHIND

    Given the current worktree is clean
    And main has 3 new commits not in the worktree
    And the worktree branch has no commits not in main
    When /pl-work-pull is invoked
    Then the state label "BEHIND" is printed
    And git rebase main is executed (not git merge main)
    And the output reports 3 new commits incorporated
    """

    def test_skill_file_instructs_rebase_main(self):
        """The pl-work-pull skill file instructs rebasing onto main."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git rebase main", content)
        self.assertNotIn("git merge main", content)

    def test_skill_file_prints_behind_state(self):
        """The pl-work-pull skill file prints BEHIND state label."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("BEHIND", content)
        self.assertIn("fast-forward", content.lower())


class TestPlWorkPushAllowsQAMergeWithOpenDiscoveries(unittest.TestCase):
    """Scenario: pl-work-push Allows QA Merge When Discoveries Are Committed But Open

    Given the current branch is qa/collab
    And features/cdd_collab_mode.md has 3 OPEN entries in ## User Testing Discoveries
    And all discovery entries are committed to the branch
    And all manual scenarios have been attempted (failed ones have BUG discoveries)
    And no in-scope feature is fully clean (no [Complete] commit needed)
    When /pl-work-push is invoked
    Then discoveries_addressed evaluates as PASS
    And complete_commit_made evaluates as PASS
    And the branch is merged to main
    """

    def test_skill_file_qa_discoveries_addressed_allows_open(self):
        """pl-work-push QA evaluation: discoveries_addressed passes when OPEN entries are committed."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-push.md")
        with open(skill_path) as f:
            content = f.read()
        # The skill file must instruct that OPEN status is acceptable
        self.assertIn("OPEN status is expected and acceptable", content,
                       "QA discoveries_addressed must accept committed OPEN entries")

    def test_skill_file_qa_complete_commit_passes_when_all_have_bugs(self):
        """pl-work-push QA evaluation: complete_commit_made passes when no clean features exist."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-push.md")
        with open(skill_path) as f:
            content = f.read()
        # The skill file must handle the case where all features have open discoveries
        self.assertIn("PASS if all in-scope features have open discoveries", content,
                       "QA complete_commit_made must pass when no clean features exist")

    def test_global_steps_qa_descriptions_match_spec(self):
        """global_steps.json QA step descriptions reflect push-with-bugs semantics."""
        steps_path = os.path.join(SCRIPT_DIR, "global_steps.json")
        with open(steps_path) as f:
            data = json.load(f)
        steps_by_id = {s["id"]: s for s in data["steps"]}

        # scenarios_complete: allows deferred scenarios blocked by BUG
        sc = steps_by_id["purlin.handoff.scenarios_complete"]
        self.assertIn("BUG", sc["description"])

        # discoveries_addressed: OPEN status acceptable
        da = steps_by_id["purlin.handoff.discoveries_addressed"]
        self.assertIn("OPEN status is acceptable", da["description"])

        # complete_commit_made: PASS when all have open discoveries
        cc = steps_by_id["purlin.handoff.complete_commit_made"]
        self.assertIn("PASS when all in-scope features have open discoveries",
                       cc["description"])


class TestPlWorkPullRebasesWhenDiverged(unittest.TestCase):
    """Scenario: pl-work-pull Rebases When Branch Is DIVERGED

    Given the current worktree is clean
    And the worktree branch has 2 commits not in main
    And main has 3 commits not in the worktree branch
    When /pl-work-pull is invoked
    Then the state label "DIVERGED" is printed
    And the DIVERGED context report is printed showing incoming commits from main
    And git rebase main is executed (not git merge main)
    And on success the branch is AHEAD of main by 2 commits
    """

    def test_skill_file_handles_diverged_state(self):
        """The pl-work-pull skill file handles DIVERGED with context report."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("git log HEAD..main --stat --oneline", content)
        self.assertIn("git rebase main", content)


class TestPlWorkPullReportsPerFileConflictContext(unittest.TestCase):
    """Scenario: pl-work-pull Reports Per-File Commit Context On Conflict

    Given /pl-work-pull is invoked and git rebase main halts with a conflict
    When the conflict is reported
    Then the output includes commits from main and the worktree branch
    And a role-scoped resolution hint is shown
    And the output includes instructions to git rebase --continue or --abort
    """

    def test_skill_file_includes_per_file_conflict_context(self):
        """The pl-work-pull skill file provides per-file commit context."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-pull.md")
        with open(skill_path) as f:
            content = f.read()
        # Per-file context using git log for each side
        self.assertIn("git log HEAD..main --oneline --", content)
        self.assertIn("git log main..ORIG_HEAD --oneline --", content)

    def test_skill_file_includes_role_scoped_hints(self):
        """The pl-work-pull skill file provides role-scoped resolution hints."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("features/", content)
        self.assertIn("tests/", content)
        self.assertIn("Resolution hint", content)

    def test_skill_file_includes_rebase_continue_abort(self):
        """The pl-work-pull skill file includes rebase continue/abort instructions."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git rebase --continue", content)
        self.assertIn("git rebase --abort", content)


class TestPlWorkPushBlocksWhenDiverged(unittest.TestCase):
    """Scenario: pl-work-push Blocks When Branch Is DIVERGED

    Given the current worktree branch has commits not in main
    And main has commits not in the worktree branch
    When /pl-work-push is invoked
    Then the command prints the DIVERGED state and lists incoming main commits
    And the handoff checklist is NOT run
    And no merge is executed
    And the agent is instructed to run /pl-work-pull first
    """

    def test_skill_file_blocks_diverged_before_checklist(self):
        """The pl-work-push skill file blocks DIVERGED state before checklist."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-push.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("/pl-work-pull", content)

    def test_skill_file_diverged_shows_incoming_commits(self):
        """The pl-work-push skill file lists incoming main commits on DIVERGED."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-push.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git log HEAD..main --oneline", content)

    def test_skill_file_diverged_does_not_proceed_to_checklist(self):
        """The pl-work-push skill file stops before checklist on DIVERGED."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-work-push.md")
        with open(skill_path) as f:
            content = f.read()
        # The DIVERGED block must come before the checklist section
        diverged_pos = content.find("DIVERGED")
        checklist_pos = content.find("Agent-Driven Handoff Evaluation")
        self.assertGreater(checklist_pos, 0)
        self.assertGreater(diverged_pos, 0)
        self.assertLess(diverged_pos, checklist_pos,
                        "DIVERGED block must appear before the handoff checklist")


def run_tests():
    """Run all tests and write results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Write tests.json
    tests_dir = os.path.join(PROJECT_ROOT, "tests", "workflow_checklist_system")
    os.makedirs(tests_dir, exist_ok=True)
    status = "PASS" if result.wasSuccessful() else "FAIL"
    with open(os.path.join(tests_dir, "tests.json"), 'w') as f:
        json.dump({"status": status}, f)

    print(f"\ntests.json: {status}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
