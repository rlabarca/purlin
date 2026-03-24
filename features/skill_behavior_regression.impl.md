## Implementation Notes

**[CLARIFICATION]** The scenario JSON negative assertions (e.g., "output does not contain /pl-build") use regex patterns that match when the unwanted string is absent. These are Tier 3 assertions because they verify role-inappropriate commands are not shown. (Severity: INFO)

**[CLARIFICATION]** The dev runner script (`dev/run_skill_regression.sh`) uses the three-tier fixture repo resolution (config > convention path) and falls back to running the setup script if the repo is missing. This matches the fixture resolution pattern used by other test infrastructure. (Severity: INFO)

**[CLARIFICATION]** The 3 fixture tags (`main/skill_behavior/mixed-lifecycle`, `main/skill_behavior/fresh-init`, `main/skill_behavior/architect-backlog`) were created in the local fixture repo and pushed to the remote (`git@github.com:rlabarca/purlin-fixtures.git`) via `fixture push`. Push completed 2026-03-23 and verified with `fixture list` via SSH. (Severity: INFO)

**[DISCOVERY] [ACKNOWLEDGED]** Critic could not validate fixture tags via HTTPS URL on private repo. Fixed: spec URL switched to SSH format (`git@github.com:rlabarca/purlin-fixtures.git`). Critic SSH fallback also spec'd in test_fixture_repo.md Section 2.9 for long-term robustness. (Severity: HIGH)

### Audit Finding -- 2026-03-23

**[DISCOVERY]** 12/17 regression assertions still failing
**Source:** /pl-spec-code-audit --deep (H9)
**Severity:** HIGH
**Details:** Two failure classes: (A) Fixture missing skill commands -- `main/skill_behavior/mixed-lifecycle` fixture lacks `.claude/commands/pl-status.md` and `pl-help.md`, causing scenarios 7-9 to fail with "Unknown skill". (B) Instruction-level behavior -- Architect/QA role refusals fail (agents try to locate the requested file instead of refusing); startup command tables not produced in expected Unicode border format. Builder's `copy_skill_files()` fix partially addressed this but 12/17 still fail.
**Suggested fix:** (A) Rebuild fixture tag with skill commands included. (B) Investigate instruction file compliance -- role refusal must fire before file lookup; startup print sequence must produce command table.

**[DISCOVERY] [ACKNOWLEDGED] [RESOLVED]** All 8 regression failures fixed. (1) `harness_runner.py` `execute_agent_behavior()` now implements spec Section 2.3 steps 2-4: constructs 4-layer system prompt from fixture instruction files via `construct_system_prompt()`, writes to temp file, passes via `--append-system-prompt-file`. Also uses `--no-session-persistence`, `--model claude-haiku-4-5-20251001`, `--output-format json` with `.result` extraction. (2) `copy_skill_files()` copies `.claude/commands/` from project root to fixture dir when absent, ensuring skill dispatch works without modifying fixture tags. (Severity: HIGH)
