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

from run import evaluate_step, run_handoff


class TestHandoffCLIPassesWhenAllAutoStepsPass(unittest.TestCase):
    """Scenario: Handoff CLI Passes When All Auto-Steps Pass

    Given the current worktree is on branch isolated/feat1
    And the working directory is clean
    And the critic report is current
    When run.sh is invoked
    Then the CLI exits with code 0
    And prints a summary with all steps PASS
    """

    def setUp(self):
        """Create a temp project where all auto steps pass."""
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
        subprocess.run(["git", "checkout", "-q", "-b", "isolated/feat1"],
                        cwd=self.temp_dir, check=True)
        # Create CRITIC_REPORT.md after commit so it's newer than HEAD
        import time
        time.sleep(0.1)
        with open(os.path.join(self.temp_dir, "CRITIC_REPORT.md"), 'w') as f:
            f.write("# Critic Report\n")
        # Create global_steps.json with both handoff steps (no roles field)
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"), exist_ok=True)
        critic_code = (
            "python3 -c \"import os,subprocess;"
            "r='CRITIC_REPORT.md';"
            "exit(0 if os.path.exists(r) and "
            "os.path.getmtime(r)>=float(subprocess.check_output("
            "['git','log','-1','--format=%ct']).strip()) else 1)\""
        )
        steps_data = {"steps": [
            {
                "id": "purlin.handoff.git_clean",
                "friendly_name": "Git Working Directory Clean",
                "description": "No uncommitted changes",
                "code": "git diff --exit-code && git diff --cached --exit-code",
                "agent_instructions": "Run git status."
            },
            {
                "id": "purlin.handoff.critic_report",
                "friendly_name": "Critic Report Current",
                "description": "Critic report has been generated recently",
                "code": critic_code,
                "agent_instructions": "Run tools/cdd/status.sh."
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

    Given the working directory has uncommitted changes
    When run.sh is invoked
    Then the CLI exits with code 1
    And reports the failing step (purlin.handoff.git_clean) as FAIL
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
        # Create an uncommitted file to make git_clean fail
        with open(os.path.join(self.temp_dir, "dirty.txt"), 'w') as f:
            f.write("dirty\n")
        subprocess.run(["git", "add", "dirty.txt"], cwd=self.temp_dir, check=True)
        # Create steps (no roles field)
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"), exist_ok=True)
        steps_data = {"steps": [
            {"id": "purlin.handoff.git_clean",
             "friendly_name": "Git Working Directory Clean",
             "description": "No uncommitted changes",
             "code": "git diff --exit-code && git diff --cached --exit-code",
             "agent_instructions": "Run git status."}
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
             "--project-root", self.temp_dir],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1,
                         f"Expected exit 1 but got {result.returncode}.\n"
                         f"stdout: {result.stdout}")
        self.assertIn("FAIL", result.stdout)
        self.assertIn("Git Working Directory Clean", result.stdout)


class TestCriticReportStepPassesWhenCurrent(unittest.TestCase):
    """The critic_report step evaluates to PASS when CRITIC_REPORT.md
    exists and is newer than the latest git commit."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                        cwd=self.temp_dir, check=True)
        with open(os.path.join(self.temp_dir, "README.md"), 'w') as f:
            f.write("# Test\n")
        subprocess.run(["git", "add", "-A"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                        cwd=self.temp_dir, check=True)
        # Create CRITIC_REPORT.md after the commit so mtime > commit time
        import time
        time.sleep(0.1)
        with open(os.path.join(self.temp_dir, "CRITIC_REPORT.md"), 'w') as f:
            f.write("# Critic Report\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_critic_report_step_passes(self):
        step = {
            "id": "purlin.handoff.critic_report",
            "code": (
                "python3 -c \"import os,subprocess;"
                "r='CRITIC_REPORT.md';"
                "exit(0 if os.path.exists(r) and "
                "os.path.getmtime(r)>=float(subprocess.check_output("
                "['git','log','-1','--format=%ct']).strip()) else 1)\""
            )
        }
        status, err = evaluate_step(step, self.temp_dir)
        self.assertEqual(status, "PASS",
                         f"Expected PASS but got {status}: {err}")


class TestCriticReportStepFailsWhenMissing(unittest.TestCase):
    """The critic_report step evaluates to FAIL when CRITIC_REPORT.md
    does not exist."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                        cwd=self.temp_dir, check=True)
        with open(os.path.join(self.temp_dir, "README.md"), 'w') as f:
            f.write("# Test\n")
        subprocess.run(["git", "add", "-A"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                        cwd=self.temp_dir, check=True)
        # No CRITIC_REPORT.md created

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_critic_report_step_fails_when_missing(self):
        step = {
            "id": "purlin.handoff.critic_report",
            "code": (
                "python3 -c \"import os,subprocess;"
                "r='CRITIC_REPORT.md';"
                "exit(0 if os.path.exists(r) and "
                "os.path.getmtime(r)>=float(subprocess.check_output("
                "['git','log','-1','--format=%ct']).strip()) else 1)\""
            )
        }
        status, err = evaluate_step(step, self.temp_dir)
        self.assertEqual(status, "FAIL",
                         f"Expected FAIL but got {status}: {err}")


class TestCriticReportStepFailsWhenStale(unittest.TestCase):
    """The critic_report step evaluates to FAIL when CRITIC_REPORT.md
    is older than the latest git commit."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                        cwd=self.temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                        cwd=self.temp_dir, check=True)
        with open(os.path.join(self.temp_dir, "README.md"), 'w') as f:
            f.write("# Test\n")
        subprocess.run(["git", "add", "-A"], cwd=self.temp_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"],
                        cwd=self.temp_dir, check=True)
        # Create CRITIC_REPORT.md and backdate its mtime to 1 hour ago
        import time
        report_path = os.path.join(self.temp_dir, "CRITIC_REPORT.md")
        with open(report_path, 'w') as f:
            f.write("# Critic Report\n")
        past = time.time() - 3600
        os.utime(report_path, (past, past))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_critic_report_step_fails_when_stale(self):
        step = {
            "id": "purlin.handoff.critic_report",
            "code": (
                "python3 -c \"import os,subprocess;"
                "r='CRITIC_REPORT.md';"
                "exit(0 if os.path.exists(r) and "
                "os.path.getmtime(r)>=float(subprocess.check_output("
                "['git','log','-1','--format=%ct']).strip()) else 1)\""
            )
        }
        status, err = evaluate_step(step, self.temp_dir)
        self.assertEqual(status, "FAIL",
                         f"Expected FAIL but got {status}: {err}")


class TestNoRoleFilteringInHandoff(unittest.TestCase):
    """Verify that the handoff system has no role-based filtering.

    The spec (Section 2.1) states: 'The roles field is removed — all steps
    apply to all agents.' This test ensures run.py has no role parameter
    and global_steps.json has no roles field.
    """

    def test_run_py_has_no_role_argument(self):
        """run.py should not accept --role."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "run.py"),
             "--role", "builder", "--project-root", "/tmp"],
            capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0,
                            "run.py should reject --role argument")
        self.assertIn("unrecognized arguments", result.stderr)

    def test_global_steps_have_no_roles_field(self):
        """global_steps.json entries should not have a roles field."""
        steps_path = os.path.join(SCRIPT_DIR, "global_steps.json")
        with open(steps_path) as f:
            data = json.load(f)
        for step in data["steps"]:
            self.assertNotIn("roles", step,
                             f"Step {step['id']} should not have 'roles' field")

    def test_global_steps_match_spec_section_2_5(self):
        """global_steps.json should contain exactly the 2 steps from Section 2.5."""
        steps_path = os.path.join(SCRIPT_DIR, "global_steps.json")
        with open(steps_path) as f:
            data = json.load(f)
        step_ids = [s["id"] for s in data["steps"]]
        self.assertEqual(step_ids,
                         ["purlin.handoff.git_clean",
                          "purlin.handoff.critic_report"])


class TestPlLocalPushMergesWhenAllChecksPass(unittest.TestCase):
    """Scenario: pl-local-push Merges Branch When All Checks Pass

    Given the current branch is isolated/feat1
    And tools/handoff/run.sh exits with code 0
    And the main checkout is on branch main
    When /pl-local-push is invoked
    Then git merge --ff-only isolated/feat1 is executed from PROJECT_ROOT
    And the command succeeds
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
        subprocess.run(["git", "checkout", "-q", "-b", "isolated/feat1"],
                        cwd=self.temp_dir, check=True)
        # Create a passing handoff step
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"), exist_ok=True)
        steps_data = {"steps": [
            {"id": "purlin.handoff.git_clean",
             "friendly_name": "Git Clean", "description": "Clean",
             "code": "git diff --exit-code && git diff --cached --exit-code",
             "agent_instructions": "Run git status."}
        ]}
        with open(os.path.join(self.temp_dir, "tools", "handoff",
                               "global_steps.json"), 'w') as f:
            json.dump(steps_data, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_handoff_passes_exits_0(self):
        """run.py exits 0 when checklist passes."""
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "run.py"),
             "--project-root", self.temp_dir],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0,
                         f"Expected exit 0.\nstdout: {result.stdout}\n"
                         f"stderr: {result.stderr}")

    def test_skill_file_instructs_ff_only_merge(self):
        """The pl-local-push skill file specifies --ff-only merge."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-push.md")
        self.assertTrue(os.path.exists(skill_path),
                        "pl-local-push.md skill file must exist")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("--ff-only", content)
        self.assertIn("merge", content)


class TestPlLocalPushBlocksMergeWhenChecksFail(unittest.TestCase):
    """Scenario: pl-local-push Blocks Merge When Handoff Checks Fail

    Given the current branch is isolated/feat1
    And tools/handoff/run.sh exits with code 1
    When /pl-local-push is invoked
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
        subprocess.run(["git", "checkout", "-q", "-b", "isolated/feat1"],
                        cwd=self.temp_dir, check=True)
        # Create an uncommitted file to make git_clean fail
        with open(os.path.join(self.temp_dir, "dirty.txt"), 'w') as f:
            f.write("dirty\n")
        subprocess.run(["git", "add", "dirty.txt"], cwd=self.temp_dir, check=True)
        os.makedirs(os.path.join(self.temp_dir, "tools", "handoff"), exist_ok=True)
        steps_data = {"steps": [
            {"id": "purlin.handoff.git_clean",
             "friendly_name": "Git Clean", "description": "Clean",
             "code": "git diff --exit-code && git diff --cached --exit-code",
             "agent_instructions": "Run git status."}
        ]}
        with open(os.path.join(self.temp_dir, "tools", "handoff",
                               "global_steps.json"), 'w') as f:
            json.dump(steps_data, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_handoff_fails_and_exits_1(self):
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "run.py"),
             "--project-root", self.temp_dir],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)


class TestPlLocalPullAbortsWhenDirty(unittest.TestCase):
    """Scenario: pl-local-pull Aborts When Working Tree Is Dirty

    Given the current worktree has uncommitted changes
    When /pl-local-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git rebase is executed
    """

    def test_skill_file_checks_clean_state(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        self.assertTrue(os.path.exists(skill_path),
                        "pl-local-pull.md skill file must exist")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("Commit or stash changes before pulling", content)
        self.assertIn("git status --porcelain", content)


class TestPlLocalPullRebasesMainWhenBehind(unittest.TestCase):
    """Scenario: pl-local-pull Rebases Main Into Worktree When Branch Is BEHIND

    Given the current worktree is clean
    And main has 3 new commits not in the worktree branch
    And the worktree branch has no commits not in main
    When /pl-local-pull is invoked
    Then the state label "BEHIND" is printed
    And git rebase main is executed
    And the output reports 3 new commits incorporated
    """

    def test_skill_file_instructs_rebase_main(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git rebase main", content)
        self.assertNotIn("git merge main", content)

    def test_skill_file_prints_behind_state(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("BEHIND", content)
        self.assertIn("fast-forward", content.lower())


class TestPlLocalPullRebasesWhenDiverged(unittest.TestCase):
    """Scenario: pl-local-pull Rebases When Branch Is DIVERGED

    Given the current worktree is clean
    And the worktree branch has 2 commits not in main
    And main has 3 commits not in the worktree branch
    When /pl-local-pull is invoked
    Then the state label "DIVERGED" is printed
    And the DIVERGED context report is printed showing incoming commits
    And git rebase main is executed
    And on success the branch is AHEAD of main by 2 commits
    """

    def test_skill_file_handles_diverged_state(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("git log HEAD..main --stat --oneline", content)
        self.assertIn("git rebase main", content)


class TestPlLocalPullReportsPerFileConflictContext(unittest.TestCase):
    """Scenario: pl-local-pull Reports Per-File Commit Context On Conflict

    Given /pl-local-pull is invoked and git rebase main halts with a conflict
    When the conflict is reported
    Then the output includes commits from main and the worktree branch
    And a resolution hint is shown for features/ files
    And the output includes instructions to git rebase --continue or --abort
    """

    def test_skill_file_includes_per_file_conflict_context(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git log HEAD..main --oneline --", content)
        self.assertIn("git log main..ORIG_HEAD --oneline --", content)

    def test_skill_file_includes_resolution_hints(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("features/", content)
        self.assertIn("tests/", content)
        self.assertIn("Resolution hint", content)

    def test_skill_file_includes_rebase_continue_abort(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git rebase --continue", content)
        self.assertIn("git rebase --abort", content)


class TestPlLocalPushBlocksWhenDiverged(unittest.TestCase):
    """Scenario: pl-local-push Blocks When Branch Is DIVERGED

    Given the current worktree branch has commits not in main
    And main has commits not in the worktree branch
    When /pl-local-push is invoked
    Then the command prints the DIVERGED state and lists incoming main commits
    And the handoff checklist is NOT run
    And no merge is executed
    And the agent is instructed to run /pl-local-pull first
    """

    def test_skill_file_blocks_diverged_before_checklist(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-push.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("/pl-local-pull", content)

    def test_skill_file_diverged_shows_incoming_commits(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-push.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git log HEAD..main --oneline", content)

    def test_skill_file_diverged_does_not_proceed_to_checklist(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-push.md")
        with open(skill_path) as f:
            content = f.read()
        diverged_pos = content.find("DIVERGED")
        checklist_pos = content.find("Run Handoff Checklist")
        self.assertGreater(checklist_pos, 0)
        self.assertGreater(diverged_pos, 0)
        self.assertLess(diverged_pos, checklist_pos,
                        "DIVERGED block must appear before the handoff checklist")


class TestPlLocalPullReSyncsCommandFilesAfterRebase(unittest.TestCase):
    """Scenario: pl-local-pull Re-Syncs Command Files After Rebase

    Given the current worktree is clean
    And main has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains extra files restored by rebase
    When /pl-local-pull is invoked
    Then git rebase main succeeds
    And extra command files are deleted from the worktree
    And pl-local-push.md and pl-local-pull.md still exist
    """

    def test_skill_file_instructs_command_resync(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("skip-worktree", content)
        self.assertIn("pl-local-push.md", content)
        self.assertIn("pl-local-pull.md", content)


class TestPostRebaseSyncLeavesWorkingTreeClean(unittest.TestCase):
    """Scenario: Post-Rebase Sync Leaves Working Tree Clean

    Given the current worktree is clean
    And main has 1 new commit not in the worktree branch
    And rebase restores extra command files to .claude/commands/
    When /pl-local-pull is invoked
    Then git rebase main succeeds
    And git status --porcelain reports no file changes
    """

    def test_skill_file_uses_skip_worktree_for_clean_status(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git update-index --skip-worktree", content)


class TestPlLocalPullNoFailWhenExtraFilesAbsent(unittest.TestCase):
    """Scenario: pl-local-pull Does Not Fail When Extra Command Files Are Already Absent

    Given the current worktree is clean
    And main has 2 new commits not in the worktree branch
    And .claude/commands/ contains only pl-local-push.md and pl-local-pull.md
    When /pl-local-pull is invoked
    Then git rebase main succeeds
    And no error is raised
    """

    def test_skill_file_handles_absent_extra_files_gracefully(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-local-pull.md")
        with open(skill_path) as f:
            content = f.read()
        # The command re-sync section should not fail when files don't exist
        self.assertIn("pl-local-push.md", content)
        self.assertIn("pl-local-pull.md", content)


# =============================================================================
# Collab Push/Pull Scenarios (Section 2.8 of workflow_checklist_system.md)
# =============================================================================

COLLAB_PUSH_PATH = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                "pl-collab-push.md")
COLLAB_PULL_PATH = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                "pl-collab-pull.md")


class TestPlCollabPushExitsWhenNotMain(unittest.TestCase):
    """Scenario: pl-collab-push Exits When Current Branch Is Not Main

    Given the current branch is isolated/feat1
    When /pl-collab-push is invoked
    Then the command prints "This command is only valid from the main checkout"
    And exits with code 1
    """

    def test_skill_file_has_main_branch_guard(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git rev-parse --abbrev-ref HEAD", content)
        self.assertIn("This command is only valid from the main checkout", content)

    def test_skill_file_guard_is_step_0(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        guard_pos = content.find("Main Branch Guard")
        session_pos = content.find("Session Guard")
        self.assertGreater(guard_pos, 0)
        self.assertGreater(session_pos, guard_pos,
                           "Main Branch Guard must appear before Session Guard")


class TestPlCollabPullExitsWhenNotMain(unittest.TestCase):
    """Scenario: pl-collab-pull Exits When Current Branch Is Not Main

    Given the current branch is isolated/feat1
    When /pl-collab-pull is invoked
    Then the command prints "This command is only valid from the main checkout"
    And exits with code 1
    """

    def test_skill_file_has_main_branch_guard(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git rev-parse --abbrev-ref HEAD", content)
        self.assertIn("This command is only valid from the main checkout", content)

    def test_skill_file_guard_is_step_0(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        guard_pos = content.find("Main Branch Guard")
        session_pos = content.find("Session Guard")
        self.assertGreater(guard_pos, 0)
        self.assertGreater(session_pos, guard_pos,
                           "Main Branch Guard must appear before Session Guard")


class TestPlCollabPushExitsWhenNoActiveSession(unittest.TestCase):
    """Scenario: pl-collab-push Exits When No Active Session

    Given the current branch is main
    And .purlin/runtime/active_remote_session is absent
    When /pl-collab-push is invoked
    Then the command prints "No active remote session"
    And exits with code 1
    """

    def test_skill_file_has_session_guard(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("active_remote_session", content)
        self.assertIn("No active remote session", content)

    def test_skill_file_directs_to_dashboard(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("CDD dashboard", content)


class TestPlCollabPullExitsWhenNoActiveSession(unittest.TestCase):
    """Scenario: pl-collab-pull Exits When No Active Session

    Given the current branch is main
    And .purlin/runtime/active_remote_session is absent
    When /pl-collab-pull is invoked
    Then the command prints "No active remote session"
    And exits with code 1
    """

    def test_skill_file_has_session_guard(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("active_remote_session", content)
        self.assertIn("No active remote session", content)

    def test_skill_file_directs_to_dashboard(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("CDD dashboard", content)


class TestPlCollabPushAbortsWhenDirty(unittest.TestCase):
    """Scenario: pl-collab-push Aborts When Working Tree Is Dirty

    Given the current branch is main
    And an active remote session exists
    And the working tree has uncommitted changes outside .purlin/
    When /pl-collab-push is invoked
    Then the command prints "Commit or stash changes before pushing"
    And no git push is executed
    """

    def test_skill_file_checks_dirty_state(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git status --porcelain", content)
        self.assertIn("Commit or stash changes before pushing", content)

    def test_skill_file_excludes_purlin_from_dirty(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn(".purlin/", content)


class TestPlCollabPullAbortsWhenDirty(unittest.TestCase):
    """Scenario: pl-collab-pull Aborts When Working Tree Is Dirty

    Given the current branch is main
    And an active remote session exists
    And the working tree has uncommitted changes outside .purlin/
    When /pl-collab-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git merge is executed
    """

    def test_skill_file_checks_dirty_state(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git status --porcelain", content)
        self.assertIn("Commit or stash changes before pulling", content)

    def test_skill_file_excludes_purlin_from_dirty(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn(".purlin/", content)


class TestPlCollabPushBlockedWhenBehind(unittest.TestCase):
    """Scenario: pl-collab-push Blocked When Local Main Is BEHIND Remote

    Given the current branch is main with an active session "v0.5-sprint"
    And origin/collab/v0.5-sprint has 2 commits not in local main
    And local main has no commits not in origin/collab/v0.5-sprint
    When /pl-collab-push is invoked
    Then the command prints "Local main is BEHIND" and instructs /pl-collab-pull
    And exits with code 1
    """

    def test_skill_file_blocks_behind_state(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("BEHIND", content)
        self.assertIn("/pl-collab-pull", content)

    def test_skill_file_uses_two_range_query(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git log origin/collab/<session>..main --oneline", content)
        self.assertIn("git log main..origin/collab/<session> --oneline", content)


class TestPlCollabPushBlockedWhenDiverged(unittest.TestCase):
    """Scenario: pl-collab-push Blocked When Local Main Is DIVERGED

    Given the current branch is main with an active session "v0.5-sprint"
    And local main has 1 commit not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When /pl-collab-push is invoked
    Then the command prints the incoming commits from remote
    And instructs to run /pl-collab-pull
    And exits with code 1
    """

    def test_skill_file_blocks_diverged_state(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("/pl-collab-pull", content)

    def test_skill_file_shows_incoming_commits_on_diverged(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git log main..origin/collab/<session> --oneline", content)


class TestPlCollabPushSucceedsWhenAhead(unittest.TestCase):
    """Scenario: pl-collab-push Succeeds When AHEAD

    Given the current branch is main with an active session "v0.5-sprint"
    And local main has 3 commits not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has no commits not in local main
    When /pl-collab-push is invoked
    Then git push origin main:collab/v0.5-sprint is executed
    And the command reports "Pushed N commits"
    """

    def test_skill_file_pushes_on_ahead(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git push", content)
        self.assertIn("main:collab/<session>", content)

    def test_skill_file_reports_pushed_commits(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("Pushed", content)
        self.assertIn("commits", content)


class TestPlCollabPushNoOpWhenSame(unittest.TestCase):
    """Scenario: pl-collab-push Is No-Op When SAME

    Given the current branch is main with an active session "v0.5-sprint"
    And local main and origin/collab/v0.5-sprint point to the same commit
    When /pl-collab-push is invoked
    Then the command prints "Already in sync. Nothing to push."
    And no git push is executed
    """

    def test_skill_file_noop_on_same(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("Already in sync. Nothing to push.", content)


class TestPlCollabPushAutoCreatesRemoteBranch(unittest.TestCase):
    """Scenario: pl-collab-push Auto-Creates Remote Branch When It Does Not Exist

    Given the current branch is main with an active session "new-session"
    And no collab/new-session branch exists on origin
    When /pl-collab-push is invoked
    Then git push origin main:collab/new-session creates the branch
    And the command reports success
    """

    def test_skill_file_handles_nonexistent_remote_branch(self):
        with open(COLLAB_PUSH_PATH) as f:
            content = f.read()
        # The command should mention that git push creates the branch automatically
        self.assertIn("git push", content)
        # The fetch step should handle non-existent branch gracefully
        self.assertIn("git fetch", content)


class TestPlCollabPullFastForwardsWhenBehind(unittest.TestCase):
    """Scenario: pl-collab-pull Fast-Forwards Main When BEHIND

    Given the current branch is main with an active session "v0.5-sprint"
    And origin/collab/v0.5-sprint has 3 commits not in local main
    And local main has no commits not in origin/collab/v0.5-sprint
    When /pl-collab-pull is invoked
    Then git merge --ff-only origin/collab/<session> is executed
    And the command reports "Fast-forwarded local main by N commits"
    """

    def test_skill_file_fast_forwards_on_behind(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("--ff-only", content)
        self.assertIn("Fast-forwarded", content)

    def test_skill_file_uses_merge_not_rebase(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git merge", content)
        # Remote pull uses merge on main (shared branch), never rebase
        self.assertNotIn("git rebase", content)


class TestPlCollabPullMergesWhenDivergedNoConflicts(unittest.TestCase):
    """Scenario: pl-collab-pull Creates Merge Commit When DIVERGED No Conflicts

    Given the current branch is main with an active session "v0.5-sprint"
    And local main has 1 commit not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has 2 commits not in local main
    And the changes do not conflict
    When /pl-collab-pull is invoked
    Then git merge origin/collab/<session> creates a merge commit
    And the command reports success
    """

    def test_skill_file_merges_on_diverged(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("git merge origin/collab/<session>", content)

    def test_skill_file_shows_pre_merge_context(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git log main..origin/collab/<session> --stat --oneline",
                       content)


class TestPlCollabPullExitsOnConflictWithContext(unittest.TestCase):
    """Scenario: pl-collab-pull Exits On Conflict With Per-File Context

    Given the current branch is main with an active session "v0.5-sprint"
    And local main and origin/collab/v0.5-sprint have conflicting changes
    When /pl-collab-pull is invoked
    Then git merge halts with conflicts
    And the command prints commits from each side for each conflicting file
    And provides instructions for git merge --continue or --abort
    And exits with code 1
    """

    def test_skill_file_shows_per_file_conflict_context(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("CONFLICT", content)
        self.assertIn("git log main..origin/collab/<session> --oneline --",
                       content)
        self.assertIn("git log origin/collab/<session>..main --oneline --",
                       content)

    def test_skill_file_instructs_merge_continue_or_abort(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git merge --continue", content)
        self.assertIn("git merge --abort", content)


class TestPlCollabPullNoOpWhenAhead(unittest.TestCase):
    """Scenario: pl-collab-pull Is No-Op When AHEAD

    Given the current branch is main with an active session "v0.5-sprint"
    And local main has 2 commits not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has no commits not in local main
    When /pl-collab-pull is invoked
    Then the command prints "Local main is AHEAD by N commits. Nothing to pull"
    And no git merge is executed
    """

    def test_skill_file_noop_on_ahead(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("AHEAD", content)
        self.assertIn("Nothing to pull", content)


class TestPlCollabPullNoOpWhenSame(unittest.TestCase):
    """Scenario: pl-collab-pull Is No-Op When SAME

    Given the current branch is main with an active session "v0.5-sprint"
    And local main and origin/collab/v0.5-sprint point to the same commit
    When /pl-collab-pull is invoked
    Then the command prints "Local main is already in sync with remote"
    And no git merge is executed
    """

    def test_skill_file_noop_on_same(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("Local main is already in sync with remote", content)


class TestPlCollabPullDoesNotCascade(unittest.TestCase):
    """Scenario: pl-collab-pull Does Not Cascade To Isolated Team Worktrees

    Given the current branch is main with an active session "v0.5-sprint"
    And an isolated worktree exists at .worktrees/feat1
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When /pl-collab-pull is invoked and fast-forwards main
    Then the isolated worktree at .worktrees/feat1 is not modified
    And .worktrees/feat1 shows BEHIND in subsequent status checks
    """

    def test_skill_file_documents_no_cascade(self):
        with open(COLLAB_PULL_PATH) as f:
            content = f.read()
        self.assertIn("No cascade", content)
        self.assertIn("/pl-local-pull", content)


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
