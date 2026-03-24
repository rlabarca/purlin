## Implementation Notes

**[CLARIFICATION]** The scenario JSON negative assertions (e.g., "output does not contain /pl-build") use regex patterns that match when the unwanted string is absent. These are Tier 3 assertions because they verify role-inappropriate commands are not shown. (Severity: INFO)

**[CLARIFICATION]** The dev runner script (`dev/run_skill_regression.sh`) uses the three-tier fixture repo resolution (config > convention path) and falls back to running the setup script if the repo is missing. This matches the fixture resolution pattern used by other test infrastructure. (Severity: INFO)

**[CLARIFICATION]** The 3 fixture tags (`main/skill_behavior/mixed-lifecycle`, `main/skill_behavior/fresh-init`, `main/skill_behavior/architect-backlog`) were created in the local fixture repo and pushed to the remote (`git@github.com:rlabarca/purlin-fixtures.git`) via `fixture push`. Push completed 2026-03-23 and verified with `fixture list` via SSH. (Severity: INFO)

**[DISCOVERY] [ACKNOWLEDGED]** Critic could not validate fixture tags via HTTPS URL on private repo. Fixed: spec URL switched to SSH format (`git@github.com:rlabarca/purlin-fixtures.git`). Critic SSH fallback also spec'd in test_fixture_repo.md Section 2.9 for long-term robustness. (Severity: HIGH)

**[DISCOVERY] [ACKNOWLEDGED]** All 8 regression failures share two root causes. (1) `harness_runner.py` `execute_agent_behavior()` does not implement spec Section 2.3 steps 2-4: it runs `claude --print -p <prompt>` without constructing the 4-layer system prompt or passing it via `--append-system-prompt-file`. Without role instructions, agents have no Purlin context (no command tables, no zero-code mandate, no CDD terminology). A working reference implementation exists in `dev/test_agent_behavior.sh` which correctly builds the prompt file and passes it to Claude. (2) Fixture tags do not include `.claude/commands/` skill files, so skill dispatch scenarios (`/pl-status`, `/pl-help`) fail with "Unknown skill". Fixtures need skill files added or these scenarios need an alternative approach. (Severity: HIGH)
