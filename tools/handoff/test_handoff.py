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


class TestPlIsolatedPushMergesWhenAllChecksPass(unittest.TestCase):
    """Scenario: pl-isolated-push Merges Branch When All Checks Pass

    Given the current branch is isolated/feat1
    And tools/handoff/run.sh exits with code 0
    And the main checkout is on the collaboration branch
    When /pl-isolated-push is invoked
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
        """The pl-isolated-push skill file specifies --ff-only merge."""
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-push.md")
        self.assertTrue(os.path.exists(skill_path),
                        "pl-isolated-push.md skill file must exist")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("--ff-only", content)
        self.assertIn("merge", content)


class TestPlIsolatedPushBlocksMergeWhenChecksFail(unittest.TestCase):
    """Scenario: pl-isolated-push Blocks Merge When Handoff Checks Fail

    Given the current branch is isolated/feat1
    And tools/handoff/run.sh exits with code 1
    When /pl-isolated-push is invoked
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


class TestPlIsolatedPullAbortsWhenDirty(unittest.TestCase):
    """Scenario: pl-isolated-pull Aborts When Working Tree Is Dirty

    Given the current worktree has uncommitted changes
    When /pl-isolated-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git rebase is executed
    """

    def test_skill_file_checks_clean_state(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        self.assertTrue(os.path.exists(skill_path),
                        "pl-isolated-pull.md skill file must exist")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("Commit or stash changes before pulling", content)
        self.assertIn("git status --porcelain", content)


class TestPlIsolatedPullRebasesWhenBehind(unittest.TestCase):
    """Scenario: pl-isolated-pull Rebases Collaboration Branch Into Worktree When Branch Is BEHIND

    Given the current worktree is clean
    And the collaboration branch has 3 new commits not in the worktree branch
    And the worktree branch has no commits not in the collaboration branch
    When /pl-isolated-pull is invoked
    Then the state label "BEHIND" is printed
    And git rebase <collaboration-branch> is executed
    And the output reports 3 new commits incorporated
    """

    def test_skill_file_instructs_rebase(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git rebase <collaboration-branch>", content)
        self.assertNotIn("git merge <collaboration-branch>", content)

    def test_skill_file_prints_behind_state(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("BEHIND", content)
        self.assertIn("fast-forward", content.lower())


class TestPlIsolatedPullRebasesWhenDiverged(unittest.TestCase):
    """Scenario: pl-isolated-pull Rebases When Branch Is DIVERGED

    Given the current worktree is clean
    And the worktree branch has 2 commits not in the collaboration branch
    And the collaboration branch has 3 commits not in the worktree branch
    When /pl-isolated-pull is invoked
    Then the state label "DIVERGED" is printed
    And the DIVERGED context report is printed showing incoming commits
    And git rebase <collaboration-branch> is executed
    And on success the branch is AHEAD of the collaboration branch by 2 commits
    """

    def test_skill_file_handles_diverged_state(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("git log HEAD..<collaboration-branch> --stat --oneline",
                       content)
        self.assertIn("git rebase <collaboration-branch>", content)


class TestPlIsolatedPullReportsPerFileConflictContext(unittest.TestCase):
    """Scenario: pl-isolated-pull Reports Per-File Commit Context On Conflict

    Given /pl-isolated-pull is invoked and git rebase halts with a conflict
    When the conflict is reported
    Then the output includes commits from the collaboration branch and worktree branch
    And a resolution hint is shown for features/ files
    And the output includes instructions to git rebase --continue or --abort
    """

    def test_skill_file_includes_per_file_conflict_context(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git log HEAD..<collaboration-branch> --oneline --", content)
        self.assertIn("git log <collaboration-branch>..ORIG_HEAD --oneline --",
                       content)

    def test_skill_file_includes_resolution_hints(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("features/", content)
        self.assertIn("tests/", content)
        self.assertIn("Resolution hint", content)

    def test_skill_file_includes_rebase_continue_abort(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git rebase --continue", content)
        self.assertIn("git rebase --abort", content)


class TestPlIsolatedPushBlocksWhenDiverged(unittest.TestCase):
    """Scenario: pl-isolated-push Blocks When Branch Is DIVERGED

    Given the current worktree branch has commits not in the collaboration branch
    And the collaboration branch has commits not in the worktree branch
    When /pl-isolated-push is invoked
    Then the command prints the DIVERGED state
    And the handoff checklist is NOT run
    And no merge is executed
    And the agent is instructed to run /pl-isolated-pull first
    """

    def test_skill_file_blocks_diverged_before_checklist(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-push.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("/pl-isolated-pull", content)

    def test_skill_file_diverged_shows_incoming_commits(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-push.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git log HEAD..<collaboration-branch> --oneline", content)

    def test_skill_file_diverged_does_not_proceed_to_checklist(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-push.md")
        with open(skill_path) as f:
            content = f.read()
        diverged_pos = content.find("DIVERGED")
        checklist_pos = content.find("Run Handoff Checklist")
        self.assertGreater(checklist_pos, 0)
        self.assertGreater(diverged_pos, 0)
        self.assertLess(diverged_pos, checklist_pos,
                        "DIVERGED block must appear before the handoff checklist")


class TestPlIsolatedPullReSyncsCommandFilesAfterRebase(unittest.TestCase):
    """Scenario: pl-isolated-pull Re-Syncs Command Files After Rebase

    Given the current worktree is clean
    And the collaboration branch has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains pl-isolated-push.md,
        pl-isolated-pull.md, and pl-status.md (restored by rebase)
    When /pl-isolated-pull is invoked
    Then git rebase succeeds
    And .claude/commands/pl-status.md is deleted from the worktree
    And .claude/commands/pl-isolated-push.md and pl-isolated-pull.md still exist
    """

    def test_skill_file_instructs_command_resync(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("skip-worktree", content)
        self.assertIn("pl-isolated-push.md", content)
        self.assertIn("pl-isolated-pull.md", content)


class TestPostRebaseSyncLeavesWorkingTreeClean(unittest.TestCase):
    """Scenario: Post-Rebase Sync Leaves Working Tree Clean

    Given the current worktree is clean
    And the collaboration branch has 1 new commit not in the worktree branch
    And rebase restores extra command files to .claude/commands/ in the worktree
    When /pl-isolated-pull is invoked
    Then git rebase succeeds
    And git status --porcelain reports no file changes in the worktree
    And .claude/commands/ in the worktree contains only pl-isolated-push.md
        and pl-isolated-pull.md
    """

    def test_skill_file_uses_skip_worktree_for_clean_status(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("git update-index --skip-worktree", content)


class TestPlIsolatedPullNoFailWhenExtraFilesAbsent(unittest.TestCase):
    """Scenario: pl-isolated-pull Does Not Fail When Extra Command Files Are Already Absent

    Given the current worktree is clean
    And the collaboration branch has 2 new commits not in the worktree branch
    And .claude/commands/ in the worktree contains only pl-isolated-push.md
        and pl-isolated-pull.md (no extra files)
    When /pl-isolated-pull is invoked
    Then git rebase succeeds
    And no error is raised
    """

    def test_skill_file_handles_absent_extra_files_gracefully(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("pl-isolated-push.md", content)
        self.assertIn("pl-isolated-pull.md", content)


class TestPlIsolatedPullUsesActiveCollaborationBranch(unittest.TestCase):
    """Scenario: pl-isolated-pull Uses Active Collaboration Branch

    Given the current worktree is clean
    And an active branch "feature/auth" exists at PROJECT_ROOT in
        .purlin/runtime/active_branch
    And the collaboration branch feature/auth has 2 new commits
    When /pl-isolated-pull is invoked
    Then the state detection uses feature/auth as the reference branch
    And git rebase feature/auth is executed
    """

    def test_skill_file_reads_active_branch(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-pull.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("active_branch", content)
        self.assertIn("collaboration branch", content.lower())

class TestPlIsolatedPushUsesActiveCollaborationBranch(unittest.TestCase):
    """Scenario: pl-isolated-push Merges to Active Collaboration Branch

    Given the current branch is isolated/feat1
    And an active branch "feature/auth" exists at PROJECT_ROOT in
        .purlin/runtime/active_branch
    And tools/handoff/run.sh exits with code 0
    And the main checkout is on branch feature/auth
    When /pl-isolated-push is invoked
    Then git merge --ff-only isolated/feat1 is executed from PROJECT_ROOT on feature/auth
    And the command succeeds
    """

    def test_skill_file_reads_active_branch(self):
        skill_path = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                  "pl-isolated-push.md")
        with open(skill_path) as f:
            content = f.read()
        self.assertIn("active_branch", content)
        self.assertIn("collaboration branch", content.lower())


# =============================================================================
# Remote Push/Pull Scenarios (features/pl_remote_push.md, pl_remote_pull.md)
# =============================================================================

REMOTE_PUSH_PATH = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                "pl-remote-push.md")
REMOTE_PULL_PATH = os.path.join(PROJECT_ROOT, ".claude", "commands",
                                "pl-remote-pull.md")


class TestPlRemotePushExitsWhenNotOnCollabBranch(unittest.TestCase):
    """Scenario: pl-remote-push Exits When Not On Collaboration Branch

    Given the current branch is main
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote-push is invoked
    Then the command prints "This command must be run from the collaboration branch"
    And exits with code 1
    """

    def test_skill_file_has_collaboration_branch_guard(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git rev-parse --abbrev-ref HEAD", content)
        self.assertIn("This command must be run from the collaboration branch",
                       content)

    def test_skill_file_branch_guard_before_config(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        guard_pos = content.find("Collaboration Branch Guard")
        config_pos = content.find("Load Config")
        self.assertGreater(guard_pos, 0)
        self.assertGreater(config_pos, guard_pos,
                           "Branch guard must appear before Load Config")


class TestPlRemotePushExitsWhenOnWrongBranch(unittest.TestCase):
    """Scenario: pl-remote-push Exits When On Wrong Branch

    Given the current branch is hotfix/urgent
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote-push is invoked
    Then the command prints "This command must be run from the collaboration branch (feature/auth)"
    And exits with code 1
    """

    def test_skill_file_checks_branch_match(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("collaboration branch", content.lower())
        self.assertIn("git rev-parse --abbrev-ref HEAD", content)


class TestPlRemotePullExitsWhenNotOnCollabBranch(unittest.TestCase):
    """Scenario: pl-remote-pull Exits When Not On Collaboration Branch

    Given the current branch is main
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    When /pl-remote-pull is invoked
    Then the command prints "This command must be run from the collaboration branch"
    And exits with code 1
    """

    def test_skill_file_has_collaboration_branch_guard(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git rev-parse --abbrev-ref HEAD", content)
        self.assertIn("This command must be run from the collaboration branch",
                       content)

    def test_skill_file_branch_guard_before_config(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        guard_pos = content.find("Collaboration Branch Guard")
        config_pos = content.find("Load Config")
        self.assertGreater(guard_pos, 0)
        self.assertGreater(config_pos, guard_pos,
                           "Branch guard must appear before Load Config")


class TestPlRemotePushExitsWhenNoActiveBranch(unittest.TestCase):
    """Scenario: pl-remote-push Exits When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    When /pl-remote-push is invoked
    Then the command prints "No active collaboration branch"
    And exits with code 1
    """

    def test_skill_file_has_branch_guard(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("active_branch", content)
        self.assertIn("No active collaboration branch", content)

    def test_skill_file_directs_to_dashboard(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("CDD dashboard", content)


class TestPlRemotePullExitsWhenNoActiveBranch(unittest.TestCase):
    """Scenario: pl-remote-pull Exits When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    When /pl-remote-pull is invoked
    Then the command prints "No active collaboration branch"
    And exits with code 1
    """

    def test_skill_file_has_branch_guard(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("active_branch", content)
        self.assertIn("No active collaboration branch", content)

    def test_skill_file_directs_to_dashboard(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("CDD dashboard", content)


class TestPlRemotePushAbortsWhenDirty(unittest.TestCase):
    """Scenario: pl-remote-push Aborts When Working Tree Is Dirty

    Given the current branch is feature/auth
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    And the working tree has uncommitted changes outside .purlin/
    When /pl-remote-push is invoked
    Then the command prints "Commit or stash changes before pushing"
    And no git push is executed
    """

    def test_skill_file_checks_dirty_state(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git status --porcelain", content)
        self.assertIn("Commit or stash changes before pushing", content)

    def test_skill_file_excludes_purlin_from_dirty(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn(".purlin/", content)


class TestPlRemotePullAbortsWhenDirty(unittest.TestCase):
    """Scenario: pl-remote-pull Aborts When Working Tree Is Dirty

    Given the current branch is feature/auth
    And an active branch "feature/auth" exists in .purlin/runtime/active_branch
    And the working tree has uncommitted changes outside .purlin/
    When /pl-remote-pull is invoked
    Then the command prints "Commit or stash changes before pulling"
    And no git merge is executed
    """

    def test_skill_file_checks_dirty_state(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git status --porcelain", content)
        self.assertIn("Commit or stash changes before pulling", content)

    def test_skill_file_excludes_purlin_from_dirty(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn(".purlin/", content)


class TestPlRemotePushBlockedWhenBehind(unittest.TestCase):
    """Scenario: pl-remote-push Blocked When Local Is BEHIND Remote

    Given the current branch is feature/auth with an active branch "feature/auth"
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    When /pl-remote-push is invoked
    Then the command prints "Local <branch> is BEHIND" and instructs /pl-remote-pull
    And exits with code 1
    """

    def test_skill_file_blocks_behind_state(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("BEHIND", content)
        self.assertIn("/pl-remote-pull", content)

    def test_skill_file_uses_two_range_query(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git log <remote>/<branch>..<branch> --oneline", content)
        self.assertIn("git log <branch>..<remote>/<branch> --oneline", content)


class TestPlRemotePushBlockedWhenDiverged(unittest.TestCase):
    """Scenario: pl-remote-push Blocked When Local Is DIVERGED

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 1 commit not in origin/feature/auth
    And origin/feature/auth has 2 commits not in local feature/auth
    When /pl-remote-push is invoked
    Then the command prints the incoming commits from remote
    And instructs to run /pl-remote-pull
    And exits with code 1
    """

    def test_skill_file_blocks_diverged_state(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("/pl-remote-pull", content)

    def test_skill_file_shows_incoming_commits_on_diverged(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git log <branch>..<remote>/<branch> --oneline", content)


class TestPlRemotePushSucceedsWhenAhead(unittest.TestCase):
    """Scenario: pl-remote-push Succeeds When AHEAD

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 3 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    When /pl-remote-push is invoked
    Then git push origin feature/auth is executed
    And the command reports "Pushed 3 commits"
    """

    def test_skill_file_pushes_on_ahead(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("git push <remote> <branch>", content)

    def test_skill_file_reports_pushed_commits(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("Pushed", content)
        self.assertIn("commits", content)


class TestPlRemotePushNoOpWhenSame(unittest.TestCase):
    """Scenario: pl-remote-push Is No-Op When SAME

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth point to the same commit
    When /pl-remote-push is invoked
    Then the command prints "Already in sync. Nothing to push."
    And no git push is executed
    """

    def test_skill_file_noop_on_same(self):
        with open(REMOTE_PUSH_PATH) as f:
            content = f.read()
        self.assertIn("Already in sync. Nothing to push.", content)


class TestPlRemotePullFastForwardsWhenBehind(unittest.TestCase):
    """Scenario: pl-remote-pull Fast-Forwards When BEHIND

    Given the current branch is feature/auth with an active branch "feature/auth"
    And origin/feature/auth has 3 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    When /pl-remote-pull is invoked
    Then git merge --ff-only origin/feature/auth is executed
    And the command reports "Fast-forwarded local feature/auth by 3 commits"
    """

    def test_skill_file_fast_forwards_on_behind(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("--ff-only", content)
        self.assertIn("Fast-forwarded", content)

    def test_skill_file_uses_merge_not_rebase(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git merge", content)
        # Remote pull uses merge on collaboration branch (shared), never rebase
        self.assertNotIn("git rebase", content)


class TestPlRemotePullMergesWhenDivergedNoConflicts(unittest.TestCase):
    """Scenario: pl-remote-pull Creates Merge Commit When DIVERGED No Conflicts

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 1 commit not in origin/feature/auth
    And origin/feature/auth has 2 commits not in local feature/auth
    And the changes do not conflict
    When /pl-remote-pull is invoked
    Then git merge origin/feature/auth creates a merge commit
    And the command reports success
    """

    def test_skill_file_merges_on_diverged(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("DIVERGED", content)
        self.assertIn("git merge <remote>/<branch>", content)

    def test_skill_file_shows_pre_merge_context(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git log <branch>..<remote>/<branch> --stat --oneline",
                       content)


class TestPlRemotePullExitsOnConflictWithContext(unittest.TestCase):
    """Scenario: pl-remote-pull Exits On Conflict With Per-File Context

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth have conflicting changes to features/foo.md
    When /pl-remote-pull is invoked
    Then git merge halts with conflicts
    And the command prints commits from each side that touched features/foo.md
    And provides instructions for git add and git merge --continue or git merge --abort
    And exits with code 1
    """

    def test_skill_file_shows_per_file_conflict_context(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("CONFLICT", content)
        self.assertIn("git log <branch>..<remote>/<branch> --oneline --",
                       content)
        self.assertIn("git log <remote>/<branch>..<branch> --oneline --",
                       content)

    def test_skill_file_instructs_merge_continue_or_abort(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("git merge --continue", content)
        self.assertIn("git merge --abort", content)


class TestPlRemotePullNoOpWhenAhead(unittest.TestCase):
    """Scenario: pl-remote-pull Is No-Op When AHEAD

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth has 2 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    When /pl-remote-pull is invoked
    Then the command prints "Local <branch> is AHEAD by 2 commits. Nothing to pull"
    And no git merge is executed
    """

    def test_skill_file_noop_on_ahead(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("AHEAD", content)
        self.assertIn("Nothing to pull", content)


class TestPlRemotePullNoOpWhenSame(unittest.TestCase):
    """Scenario: pl-remote-pull Is No-Op When SAME

    Given the current branch is feature/auth with an active branch "feature/auth"
    And local feature/auth and origin/feature/auth point to the same commit
    When /pl-remote-pull is invoked
    Then the command prints "Local <branch> is already in sync with remote"
    And no git merge is executed
    """

    def test_skill_file_noop_on_same(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("already in sync with remote", content)


class TestPlRemotePullDoesNotCascade(unittest.TestCase):
    """Scenario: pl-remote-pull Does Not Cascade To Isolated Team Worktrees

    Given the current branch is feature/auth with an active branch "feature/auth"
    And an isolated worktree exists at .worktrees/feat1
    And origin/feature/auth has 2 commits not in local feature/auth
    When /pl-remote-pull is invoked and fast-forwards feature/auth
    Then the isolated worktree at .worktrees/feat1 is not modified
    And .worktrees/feat1 shows BEHIND in subsequent status checks
    """

    def test_skill_file_documents_no_cascade(self):
        with open(REMOTE_PULL_PATH) as f:
            content = f.read()
        self.assertIn("No cascade", content)
        self.assertIn("/pl-isolated-pull", content)


def _write_feature_results(feature_name, status, passed=0, failed=0, total=0):
    """Write tests.json for a specific feature."""
    tests_dir = os.path.join(PROJECT_ROOT, "tests", feature_name)
    os.makedirs(tests_dir, exist_ok=True)
    with open(os.path.join(tests_dir, "tests.json"), 'w') as f:
        json.dump({
            "status": status,
            "passed": passed,
            "failed": failed,
            "total": total,
            "test_file": "tools/handoff/test_handoff.py",
        }, f, indent=2)


# Map test class name prefixes to feature names
_FEATURE_PREFIX_MAP = {
    "TestHandoff": "workflow_checklist_system",
    "TestCriticReport": "workflow_checklist_system",
    "TestNoRoleFiltering": "workflow_checklist_system",
    "TestPlIsolatedPush": "pl_isolated_push",
    "TestPlIsolatedPull": "pl_isolated_pull",
    "TestPostRebaseSync": "pl_isolated_pull",
    "TestPlRemotePush": "pl_remote_push",
    "TestPlRemotePull": "pl_remote_pull",
}


def _classify_test(test_id):
    """Return feature name for a test based on its class name."""
    class_name = test_id.split(".")[-2] if "." in test_id else test_id
    for prefix, feature in _FEATURE_PREFIX_MAP.items():
        if class_name.startswith(prefix):
            return feature
    return "workflow_checklist_system"


def _classify_by_class(test):
    """Return feature name for a test case using its class name directly."""
    class_name = test.__class__.__name__
    for prefix, feature in _FEATURE_PREFIX_MAP.items():
        if class_name.startswith(prefix):
            return feature
    return "workflow_checklist_system"


def _iter_tests(suite):
    """Recursively iterate all test cases in a suite."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def run_tests():
    """Run all tests and write per-feature results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    # Pre-count totals per feature before running (suite is consumed by run)
    feature_totals = {}
    all_tests = list(_iter_tests(suite))
    for test in all_tests:
        feature = _classify_by_class(test)
        feature_totals[feature] = feature_totals.get(feature, 0) + 1

    # Reload suite (list() consumed it) and run
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Count failures by feature
    feature_failures = {}
    for test, _ in result.failures + result.errors:
        feature = _classify_by_class(test)
        feature_failures[feature] = feature_failures.get(feature, 0) + 1

    # Write per-feature tests.json
    all_features = set(_FEATURE_PREFIX_MAP.values())
    for feature in all_features:
        total = feature_totals.get(feature, 0)
        failed = feature_failures.get(feature, 0)
        passed = total - failed
        status = "FAIL" if failed > 0 else "PASS"
        _write_feature_results(feature, status, passed=passed,
                               failed=failed, total=total)
        print(f"  tests/{feature}/tests.json: {status} ({passed}/{total})")

    overall = "PASS" if result.wasSuccessful() else "FAIL"
    print(f"\nOverall: {overall}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
