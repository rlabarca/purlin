## Implementation Notes

**[CLARIFICATION]** The scenario JSON negative assertions (e.g., "output does not contain /pl-build") use regex patterns that match when the unwanted string is absent. These are Tier 3 assertions because they verify role-inappropriate commands are not shown. (Severity: INFO)

**[CLARIFICATION]** The dev runner script (`dev/run_skill_regression.sh`) uses the three-tier fixture repo resolution (config > convention path) and falls back to running the setup script if the repo is missing. This matches the fixture resolution pattern used by other test infrastructure. (Severity: INFO)

**[CLARIFICATION]** The 3 fixture tags (`main/skill_behavior/mixed-lifecycle`, `main/skill_behavior/fresh-init`, `main/skill_behavior/architect-backlog`) were created in the local fixture repo and pushed to the remote (`git@github.com:rlabarca/purlin-fixtures.git`) via `fixture push`. The Critic validates against the remote URL, so tags must exist there. Push completed 2026-03-23. (Severity: INFO)
