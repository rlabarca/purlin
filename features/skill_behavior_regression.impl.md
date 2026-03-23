## Implementation Notes

**[CLARIFICATION]** The scenario JSON negative assertions (e.g., "output does not contain /pl-build") use regex patterns that match when the unwanted string is absent. These are Tier 3 assertions because they verify role-inappropriate commands are not shown. (Severity: INFO)

**[CLARIFICATION]** The dev runner script (`dev/run_skill_regression.sh`) uses the three-tier fixture repo resolution (config > convention path) and falls back to running the setup script if the repo is missing. This matches the fixture resolution pattern used by other test infrastructure. (Severity: INFO)

**[DISCOVERY]** The 3 fixture tags declared in Section 2.9 (`main/skill_behavior/mixed-lifecycle`, `main/skill_behavior/fresh-init`, `main/skill_behavior/architect-backlog`) need to be created in the purlin-fixtures remote repo (https://github.com/rlabarca/purlin-fixtures). The setup script at `dev/setup_fixture_repo.sh` needs to be extended to generate these tags with the state descriptions from Section 2.1. This requires constructing consumer project state snapshots with the correct directory structure (`.purlin/`, `features/`, `instructions/`, `tests/`). The Builder created the scenario JSON and dev runner but the fixture tags themselves require manual setup or an extended setup script run. (Severity: HIGH)
