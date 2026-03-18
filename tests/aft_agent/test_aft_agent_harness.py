"""Traceability proxy for dev/test_aft_agent_harness.py.

The actual tests live in dev/ (Purlin-dev-specific, not consumer-facing).
This file re-exports them so the regex-based traceability scanner can find
def test_* patterns matching scenario keywords.
"""
import importlib.util
import os
import unittest

_dev_test = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'dev', 'test_aft_agent_harness.py'
))
_spec = importlib.util.spec_from_file_location(
    'test_aft_agent_harness', _dev_test
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class TestSingleTurnStructuredOutput(_mod.TestSingleTurnStructuredOutput):
    """Scenario: Single-turn structured output"""

    def test_fixture_checkout_creates_directory(self):
        super().test_fixture_checkout_creates_directory()

    def test_release_prompt_includes_step_instructions(self):
        super().test_release_prompt_includes_step_instructions()

    def test_result_json_structure_is_valid(self):
        super().test_result_json_structure_is_valid()


class TestMultiTurnSessionResume(_mod.TestMultiTurnSessionResume):
    """Scenario: Multi-turn session resume"""

    def test_first_turn_uses_session_id_flag(self):
        super().test_first_turn_uses_session_id_flag()

    def test_subsequent_turn_uses_resume_flag(self):
        super().test_subsequent_turn_uses_resume_flag()

    def test_session_id_generation_format(self):
        super().test_session_id_generation_format()

    def test_reset_session_clears_state(self):
        super().test_reset_session_clears_state()


class TestModelOverride(_mod.TestModelOverride):
    """Scenario: Model override accepted"""

    def test_model_override_accepted_via_flag(self):
        super().test_model_override_accepted_via_flag()

    def test_default_model_is_haiku(self):
        super().test_default_model_is_haiku()

    def test_model_override_passed_to_claude(self):
        super().test_model_override_passed_to_claude()


class TestScenarioSelection(_mod.TestScenarioSelection):
    """Scenario: Single scenario selection"""

    def test_single_scenario_selection_flag(self):
        super().test_single_scenario_selection_flag()

    def test_should_run_scenario_function_exists(self):
        super().test_should_run_scenario_function_exists()

    def test_single_selection_gates_each_scenario(self):
        super().test_single_selection_gates_each_scenario()


class TestMissingFixtureTagSkip(_mod.TestMissingFixtureTagSkip):
    """Scenario: Missing fixture tag skip"""

    def test_checkout_safe_function_exists(self):
        super().test_checkout_safe_function_exists()

    def test_missing_tag_triggers_checkout_failure(self):
        super().test_missing_tag_triggers_checkout_failure()

    def test_skip_does_not_count_as_failure(self):
        super().test_skip_does_not_count_as_failure()

    def test_skip_includes_tag_name(self):
        super().test_skip_includes_tag_name()


class TestReleasePromptConstruction(_mod.TestReleasePromptConstruction):
    """Scenario: Release prompt construction"""

    def test_construct_release_prompt_function_exists(self):
        super().test_construct_release_prompt_function_exists()

    def test_construct_release_prompt_reads_global_steps(self):
        super().test_construct_release_prompt_reads_global_steps()

    def test_construct_release_prompt_extracts_step_instructions(self):
        super().test_construct_release_prompt_extracts_step_instructions()

    def test_construct_release_prompt_handles_missing_steps_file(self):
        super().test_construct_release_prompt_handles_missing_steps_file()

    def test_global_steps_json_is_valid(self):
        super().test_global_steps_json_is_valid()
