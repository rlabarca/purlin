## Implementation Notes

**[CLARIFICATION]** The scenario JSON negative assertions (e.g., "output does not contain /pl-build") use regex patterns that match when the unwanted string is absent. These are Tier 3 assertions because they verify role-inappropriate commands are not shown. (Severity: INFO)

**[CLARIFICATION]** The dev runner script (`dev/run_skill_regression.sh`) uses the three-tier fixture repo resolution (config > convention path) and falls back to running the setup script if the repo is missing. This matches the fixture resolution pattern used by other test infrastructure. (Severity: INFO)

**[CLARIFICATION]** The 3 fixture tags (`main/skill_behavior/mixed-lifecycle`, `main/skill_behavior/fresh-init`, `main/skill_behavior/architect-backlog`) were created in the local fixture repo and pushed to the remote (`git@github.com:rlabarca/purlin-fixtures.git`) via `fixture push`. Push completed 2026-03-23 and verified with `fixture list` via SSH. (Severity: INFO)

**[DISCOVERY]** The Critic cannot validate fixture tags because the spec declares `> Test Fixtures: https://github.com/rlabarca/purlin-fixtures` (HTTPS), but the repo is private and HTTPS auth is not configured on this machine. The Critic calls `fixture list <HTTPS-URL>` which runs `git ls-remote --tags` and gets empty results, causing all 3 tags (appearing 6 times due to duplicate table entries in Sections 2.1 and 2.9) to show as "missing". Tags confirmed present via SSH: `git ls-remote --tags git@github.com:rlabarca/purlin-fixtures.git`. Fix options: (A) update spec to use SSH URL `git@github.com:rlabarca/purlin-fixtures.git`, (B) configure HTTPS credentials, or (C) make the repo public. (Severity: HIGH)
