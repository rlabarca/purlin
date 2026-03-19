"""Unit tests for Builder QA Mode feature.

Covers automated scenarios from features/builder_qa_mode.md.
Outputs test results to tests/builder_qa_mode/tests.json.
"""

import unittest
from unittest.mock import patch
import os
import json
import sys
import tempfile

from serve import (
    generate_startup_briefing,
    extract_category,
)


def _make_qa_mode_env(tmpdir, features=None, config=None):
    """Create a temp environment for QA mode tests.

    Each feature dict may include 'category' to write a > Category: line.
    """
    features_dir = os.path.join(tmpdir, "features")
    tests_dir = os.path.join(tmpdir, "tests")
    cache_dir = os.path.join(tmpdir, ".purlin", "cache")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    features = features or {}
    for stem, cfg in features.items():
        fpath = os.path.join(features_dir, f"{stem}.md")
        scenarios = cfg.get("scenarios", [])
        category = cfg.get("category", "")
        with open(fpath, 'w') as f:
            f.write(f'# Feature: {stem}\n\n')
            f.write(f'> Label: "{cfg.get("label", stem)}"\n')
            if category:
                f.write(f'> Category: "{category}"\n')
            f.write('\n')
            for s in scenarios:
                f.write(f'#### Scenario: {s}\n\n')

        tdir = os.path.join(tests_dir, stem)
        os.makedirs(tdir, exist_ok=True)
        role_status = cfg.get("role_status", {
            "architect": "DONE", "builder": "TODO",
            "qa": "N/A", "pm": "N/A"})
        cdata = {
            "role_status": role_status,
            "action_items": {
                "architect": [],
                "builder": [{"feature": stem, "priority": "HIGH",
                             "description": f"Implement {stem}"}],
                "qa": [], "pm": [],
            },
            "implementation_gate": {
                "checks": {"policy_adherence": {
                    "status": "PASS", "violations": []}}},
            "verification_effort": {
                "summary": "no QA items", "total_auto": 0, "total_manual": 0},
        }
        with open(os.path.join(tdir, "critic.json"), 'w') as f:
            json.dump(cdata, f)

    graph_data = {"features": [], "cycles": [], "orphans": []}
    with open(os.path.join(cache_dir, "dependency_graph.json"), 'w') as f:
        json.dump(graph_data, f)

    resolved_config = config or {
        "agents": {
            "builder": {"find_work": True, "auto_start": True,
                        "model": "test-model", "effort": "high",
                        "qa_mode": False},
            "qa": {"find_work": True, "auto_start": False,
                   "model": "test-model", "effort": "medium"},
            "architect": {"find_work": False, "auto_start": False,
                          "model": "test-model", "effort": "high"},
            "pm": {"find_work": False, "auto_start": False,
                   "model": "test-model", "effort": "high"},
        }
    }

    return {
        "features_dir": features_dir,
        "tests_dir": tests_dir,
        "cache_dir": cache_dir,
        "config": resolved_config,
        "project_root": tmpdir,
    }


def _run_briefing(env, config_override=None, env_vars=None):
    """Run generate_startup_briefing with patched environment."""
    config = config_override if config_override else env["config"]
    env_patches = env_vars or {}

    with patch('serve.FEATURES_ABS', env["features_dir"]), \
         patch('serve.FEATURES_REL', 'features'), \
         patch('serve.TESTS_DIR', env["tests_dir"]), \
         patch('serve.CACHE_DIR', env["cache_dir"]), \
         patch('serve.DEPENDENCY_GRAPH_PATH',
               os.path.join(env["cache_dir"], "dependency_graph.json")), \
         patch('serve.CONFIG', config), \
         patch('serve.PROJECT_ROOT', env["project_root"]), \
         patch('serve.build_status_commit_cache', return_value={}), \
         patch.dict(os.environ, env_patches, clear=False), \
         patch('serve.run_command') as mock_cmd:
        mock_cmd.side_effect = lambda c: {
            "git rev-parse --abbrev-ref HEAD": "main",
            "git status --porcelain": "",
        }.get(c.strip(), "")
        return generate_startup_briefing("builder")


# --- Ten features: 8 normal, 2 Test Infrastructure ---
_MIXED_FEATURES = {
    "app_auth": {
        "label": "App Auth",
        "category": "Agent Skills",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_dashboard": {
        "label": "App Dashboard",
        "category": "CDD Dashboard",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_settings": {
        "label": "App Settings",
        "category": "Install, Update & Scripts",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_release": {
        "label": "App Release",
        "category": "Release Process",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_design": {
        "label": "App Design",
        "category": "Common Design Standards",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_lifecycle": {
        "label": "App Lifecycle",
        "category": "Coordination & Lifecycle",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_remote": {
        "label": "App Remote",
        "category": "Agent Skills",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_misc": {
        "label": "App Misc",
        "category": "Uncategorized",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "test_fixture_repo": {
        "label": "Test Fixture Repo",
        "category": "Test Infrastructure",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "regression_harness": {
        "label": "Regression Harness",
        "category": "Test Infrastructure",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
}


class TestDefaultModeHidesTestInfrastructure(unittest.TestCase):
    """Scenario: Default mode hides test infrastructure features

    Given the project has 10 features, 2 in "Test Infrastructure" category
    And qa_mode is false (default)
    When the Builder runs startup find_work
    Then 8 features appear in the work plan
    And the 2 Test Infrastructure features are not listed
    """

    def test_default_mode_excludes_test_infra(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        features = result["features"]
        feature_labels = [f["label"] for f in features]

        # 8 normal features visible
        self.assertEqual(len(features), 8)

        # Test Infrastructure features NOT listed
        self.assertNotIn("Test Fixture Repo", feature_labels)
        self.assertNotIn("Regression Harness", feature_labels)

        # Normal features ARE listed
        self.assertIn("App Auth", feature_labels)
        self.assertIn("App Dashboard", feature_labels)

    def test_default_mode_filters_action_items(self):
        """Action items for Test Infrastructure features are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        action_features = {item.get("feature") for item in result["action_items"]}
        self.assertNotIn("test_fixture_repo", action_features)
        self.assertNotIn("regression_harness", action_features)

    def test_in_scope_features_also_filtered(self):
        """in_scope_features mirrors the filtered features list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        in_scope_labels = [f["label"] for f in result["in_scope_features"]]
        self.assertEqual(len(in_scope_labels), 8)
        self.assertNotIn("Test Fixture Repo", in_scope_labels)


class TestQaModeShowsOnlyTestInfrastructure(unittest.TestCase):
    """Scenario: QA mode shows only test infrastructure features

    Given the project has 10 features, 2 in "Test Infrastructure" category
    And qa_mode is true
    When the Builder runs startup find_work
    Then only the 2 Test Infrastructure features appear in the work plan
    And the 8 non-test features are not listed
    """

    def test_qa_mode_includes_only_test_infra(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agents": {
                    "builder": {"find_work": True, "auto_start": True,
                                "model": "test-model", "effort": "high",
                                "qa_mode": True},
                    "qa": {"find_work": True, "auto_start": False,
                           "model": "test-model", "effort": "medium"},
                    "architect": {"find_work": False, "auto_start": False,
                                  "model": "test-model", "effort": "high"},
                    "pm": {"find_work": False, "auto_start": False,
                           "model": "test-model", "effort": "high"},
                }
            }
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES,
                                    config=config)
            result = _run_briefing(env)

        features = result["features"]
        feature_labels = [f["label"] for f in features]

        # Only 2 Test Infrastructure features visible
        self.assertEqual(len(features), 2)
        self.assertIn("Test Fixture Repo", feature_labels)
        self.assertIn("Regression Harness", feature_labels)

        # Normal features NOT listed
        self.assertNotIn("App Auth", feature_labels)
        self.assertNotIn("App Dashboard", feature_labels)

    def test_qa_mode_filters_action_items_to_test_infra(self):
        """Only Test Infrastructure action items are returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agents": {
                    "builder": {"find_work": True, "auto_start": True,
                                "model": "test-model", "effort": "high",
                                "qa_mode": True},
                    "qa": {"find_work": True, "auto_start": False,
                           "model": "test-model", "effort": "medium"},
                    "architect": {"find_work": False, "auto_start": False,
                                  "model": "test-model", "effort": "high"},
                    "pm": {"find_work": False, "auto_start": False,
                           "model": "test-model", "effort": "high"},
                }
            }
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES,
                                    config=config)
            result = _run_briefing(env)

        action_features = {item.get("feature") for item in result["action_items"]}
        # Only test infra features should have action items
        for f in action_features:
            if f:  # skip feature-less items
                self.assertIn(f, {"test_fixture_repo", "regression_harness"})


class TestQaModePrintsHeaderIndicator(unittest.TestCase):
    """Scenario: QA mode prints header indicator

    Given qa_mode is true
    When the Builder prints its startup command table
    Then the header includes "[QA Builder Mode]"

    Implementation: qa_mode is returned in the config block so the
    Builder agent can prepend [QA Builder Mode] to its header.
    """

    def test_config_block_includes_qa_mode_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agents": {
                    "builder": {"find_work": True, "auto_start": True,
                                "model": "test-model", "effort": "high",
                                "qa_mode": True},
                    "qa": {"find_work": True, "auto_start": False,
                           "model": "test-model", "effort": "medium"},
                    "architect": {"find_work": False, "auto_start": False,
                                  "model": "test-model", "effort": "high"},
                    "pm": {"find_work": False, "auto_start": False,
                           "model": "test-model", "effort": "high"},
                }
            }
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES,
                                    config=config)
            result = _run_briefing(env)

        self.assertIn("qa_mode", result["config"])
        self.assertTrue(result["config"]["qa_mode"])

    def test_config_block_includes_qa_mode_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        self.assertIn("qa_mode", result["config"])
        self.assertFalse(result["config"]["qa_mode"])


class TestEnvironmentVariableOverridesConfig(unittest.TestCase):
    """Scenario: Environment variable overrides config

    Given .purlin/config.json has qa_mode: false
    And PURLIN_BUILDER_QA=true is set in the environment
    When the Builder reads startup flags
    Then qa_mode is true
    And only Test Infrastructure features are visible
    """

    def test_env_var_overrides_config_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Config has qa_mode: false
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            # But env var says true
            result = _run_briefing(env, env_vars={"PURLIN_BUILDER_QA": "true"})

        # qa_mode should be true
        self.assertTrue(result["config"]["qa_mode"])

        # Only Test Infrastructure features visible
        features = result["features"]
        self.assertEqual(len(features), 2)
        feature_labels = [f["label"] for f in features]
        self.assertIn("Test Fixture Repo", feature_labels)
        self.assertIn("Regression Harness", feature_labels)

    def test_env_var_false_does_not_override(self):
        """PURLIN_BUILDER_QA=false doesn't force qa_mode on."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agents": {
                    "builder": {"find_work": True, "auto_start": True,
                                "model": "test-model", "effort": "high",
                                "qa_mode": True},
                    "qa": {"find_work": True, "auto_start": False,
                           "model": "test-model", "effort": "medium"},
                    "architect": {"find_work": False, "auto_start": False,
                                  "model": "test-model", "effort": "high"},
                    "pm": {"find_work": False, "auto_start": False,
                           "model": "test-model", "effort": "high"},
                }
            }
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES,
                                    config=config)
            # env var set to false — falls through to config which says true
            result = _run_briefing(env, env_vars={"PURLIN_BUILDER_QA": "false"})

        # Config says true, env var says false, so falls through to config
        self.assertTrue(result["config"]["qa_mode"])


class TestQaModeComposesWithContinuousMode(unittest.TestCase):
    """Scenario: QA mode composes with continuous mode

    Given qa_mode is true
    And the continuous phase flag is active
    And there are 4 Test Infrastructure features in TODO state
    When the Builder creates a delivery plan
    Then the plan contains only Test Infrastructure features
    And phase analysis operates on the filtered set

    Implementation: The startup briefing returns only Test Infrastructure
    features when qa_mode is true. The continuous phase builder consumes
    this filtered list to create the delivery plan. We verify the
    briefing output is correctly filtered with 4 TI features.
    """

    def test_qa_mode_with_multiple_test_infra_features(self):
        features = {
            "app_auth": {
                "label": "App Auth",
                "category": "Agent Skills",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "app_dashboard": {
                "label": "App Dashboard",
                "category": "CDD Dashboard",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_fixture_repo": {
                "label": "Test Fixture Repo",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1", "S2"],
            },
            "regression_harness": {
                "label": "Regression Harness",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1", "S2", "S3"],
            },
            "agent_behavior": {
                "label": "Agent Behavior Tests",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_quality": {
                "label": "Test Quality",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agents": {
                    "builder": {"find_work": True, "auto_start": True,
                                "model": "test-model", "effort": "high",
                                "qa_mode": True},
                    "qa": {"find_work": True, "auto_start": False,
                           "model": "test-model", "effort": "medium"},
                    "architect": {"find_work": False, "auto_start": False,
                                  "model": "test-model", "effort": "high"},
                    "pm": {"find_work": False, "auto_start": False,
                           "model": "test-model", "effort": "high"},
                }
            }
            env = _make_qa_mode_env(tmpdir, features=features, config=config)
            result = _run_briefing(env)

        # Only Test Infrastructure features visible
        visible = result["features"]
        self.assertEqual(len(visible), 4)
        labels = {f["label"] for f in visible}
        self.assertEqual(labels, {"Test Fixture Repo", "Regression Harness",
                                  "Agent Behavior Tests", "Test Quality"})

        # in_scope_features matches
        in_scope = result["in_scope_features"]
        self.assertEqual(len(in_scope), 4)

        # phasing_recommended should work on the filtered set
        # (4 features >= 3 threshold)
        self.assertTrue(result.get("phasing_recommended", False))


class TestAgentConfigCommandTogglesQaMode(unittest.TestCase):
    """Scenario: Agent config command toggles QA mode

    Given qa_mode is currently false in .purlin/config.local.json
    When the user runs /pl-agent-config and sets qa_mode to true
    Then .purlin/config.local.json contains "qa_mode": true under builder
    And the next Builder session will enter QA builder mode

    Implementation: This tests that the config is correctly read by
    generate_startup_briefing and that qa_mode in config drives filtering.
    The /pl-agent-config command itself is an instruction-level skill,
    so we test the config -> behavior pipeline.
    """

    def test_config_qa_mode_true_activates_filtering(self):
        """Setting qa_mode: true in config activates Test Infrastructure filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "agents": {
                    "builder": {"find_work": True, "auto_start": True,
                                "model": "test-model", "effort": "high",
                                "qa_mode": True},
                    "qa": {"find_work": True, "auto_start": False,
                           "model": "test-model", "effort": "medium"},
                    "architect": {"find_work": False, "auto_start": False,
                                  "model": "test-model", "effort": "high"},
                    "pm": {"find_work": False, "auto_start": False,
                           "model": "test-model", "effort": "high"},
                }
            }
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES,
                                    config=config)
            result = _run_briefing(env)

        # qa_mode reflected in config block
        self.assertTrue(result["config"]["qa_mode"])

        # Only Test Infrastructure features
        self.assertEqual(len(result["features"]), 2)
        labels = {f["label"] for f in result["features"]}
        self.assertEqual(labels, {"Test Fixture Repo", "Regression Harness"})

    def test_config_qa_mode_false_hides_test_infra(self):
        """Setting qa_mode: false in config hides Test Infrastructure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        self.assertFalse(result["config"]["qa_mode"])
        self.assertEqual(len(result["features"]), 8)
        labels = {f["label"] for f in result["features"]}
        self.assertNotIn("Test Fixture Repo", labels)
        self.assertNotIn("Regression Harness", labels)


class TestExtractCategory(unittest.TestCase):
    """Additional tests for the extract_category helper."""

    def test_extracts_category_from_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         delete=False) as f:
            f.write('# Feature\n\n> Label: "Test"\n> Category: "Test Infrastructure"\n')
            f.flush()
            result = extract_category(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "Test Infrastructure")

    def test_returns_uncategorized_when_missing(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         delete=False) as f:
            f.write('# Feature\n\n> Label: "Test"\n')
            f.flush()
            result = extract_category(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "Uncategorized")

    def test_returns_uncategorized_for_nonexistent_file(self):
        result = extract_category("/nonexistent/path.md")
        self.assertEqual(result, "Uncategorized")


class TestCategoryInApiStatus(unittest.TestCase):
    """Verify category field is present in API status features."""

    def test_category_included_in_features(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features={
                "feat_a": {
                    "label": "Feature A",
                    "category": "Agent Skills",
                    "role_status": {"architect": "DONE", "builder": "TODO",
                                    "qa": "N/A", "pm": "N/A"},
                    "scenarios": ["S1"],
                },
            })
            result = _run_briefing(env)

        self.assertTrue(len(result["features"]) > 0)
        feat = result["features"][0]
        self.assertEqual(feat["category"], "Agent Skills")


# ===================================================================
# Test runner with output to tests/builder_qa_mode/tests.json
# ===================================================================

if __name__ == '__main__':
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../'))
    tests_out_dir = os.path.join(project_root, "tests", "builder_qa_mode")
    os.makedirs(tests_out_dir, exist_ok=True)
    status_file = os.path.join(tests_out_dir, "tests.json")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = "PASS" if result.wasSuccessful() else "FAIL"
    failed = len(result.failures) + len(result.errors)
    report = {
        "status": status,
        "passed": result.testsRun - failed,
        "failed": failed,
        "total": result.testsRun,
        "test_file": "tools/cdd/test_builder_qa_mode.py"
    }
    with open(status_file, 'w') as f:
        json.dump(report, f)
    print(f"\n{status_file}: {status}")

    sys.exit(0 if result.wasSuccessful() else 1)
