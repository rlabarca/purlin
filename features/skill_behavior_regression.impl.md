## Implementation Notes

**[CLARIFICATION]** The scenario JSON negative assertions (e.g., "output does not contain /pl-build") use regex patterns that match when the unwanted string is absent. These are Tier 3 assertions because they verify role-inappropriate commands are not shown. (Severity: INFO)

**[CLARIFICATION]** The dev runner script (`dev/run_skill_regression.sh`) uses the three-tier fixture repo resolution (config > convention path) and falls back to running the setup script if the repo is missing. This matches the fixture resolution pattern used by other test infrastructure. (Severity: INFO)

**[CLARIFICATION]** The 3 fixture tags (`main/skill_behavior/mixed-lifecycle`, `main/skill_behavior/fresh-init`, `main/skill_behavior/architect-backlog`) were created in the local fixture repo and pushed to the remote (`git@github.com:rlabarca/purlin-fixtures.git`) via `fixture push`. Push completed 2026-03-23 and verified with `fixture list` via SSH. (Severity: INFO)

**[DISCOVERY] [ACKNOWLEDGED]** Critic could not validate fixture tags via HTTPS URL on private repo. Fixed: spec URL switched to SSH format (`git@github.com:rlabarca/purlin-fixtures.git`). Critic SSH fallback also spec'd in test_fixture_repo.md Section 2.9 for long-term robustness. (Severity: HIGH)

### Audit Finding -- 2026-03-23

**[DISCOVERY] [ACKNOWLEDGED]** 12/17 regression assertions still failing
**Source:** /pl-spec-code-audit --deep (H9)
**Severity:** HIGH
**Details:** Two failure classes: (A) Fixture missing skill commands -- `main/skill_behavior/mixed-lifecycle` fixture lacks `.claude/commands/pl-status.md` and `pl-help.md`, causing scenarios 7-9 to fail with "Unknown skill". (B) Instruction-level behavior -- Architect/QA role refusals fail (agents try to locate the requested file instead of refusing); startup command tables not produced in expected Unicode border format. Builder's `copy_skill_files()` fix partially addressed this but 12/17 still fail.
**Suggested fix:** (A) Rebuild fixture tag with skill commands included. (B) Investigate instruction file compliance -- role refusal must fire before file lookup; startup print sequence must produce command table.

**[DISCOVERY] [ACKNOWLEDGED] [RESOLVED]** All 8 regression failures fixed. (1) `harness_runner.py` `execute_agent_behavior()` now implements spec Section 2.3 steps 2-4: constructs 4-layer system prompt from fixture instruction files via `construct_system_prompt()`, writes to temp file, passes via `--append-system-prompt-file`. Also uses `--no-session-persistence`, `--model claude-haiku-4-5-20251001`, `--output-format json` with `.result` extraction. (2) `copy_skill_files()` copies `.claude/commands/` from project root to fixture dir when absent, ensuring skill dispatch works without modifying fixture tags. (Severity: HIGH)

### Print-Mode Context Augmentation -- 2026-03-24

**[CLARIFICATION]** `claude --print` mode has no tool access (Read, Bash, Glob, etc.). The 4-layer instruction files tell agents to "Read `instructions/references/builder_commands.md`" and "Run `tools/cdd/status.sh`" -- impossible in `--print` mode. The model approximates (markdown lists instead of Unicode tables, file-lookup instead of role refusal). Fix: `build_print_mode_context()` pre-loads data that agents would normally obtain via tool calls -- command tables, feature status, skill content, and role enforcement reinforcement. This is appended after the 4-layer prompt as a supplementary section. (Severity: INFO)

**[CLARIFICATION]** `scan_fixture_features()` reads the fixture's `features/` directory to extract lifecycle status ([TODO], [TESTING], [COMPLETE]) and feature labels. This provides the feature status data that `status.sh --startup` would normally return. Skips companion files, discovery sidecars, and anchor nodes. (Severity: INFO)

**[CLARIFICATION]** Role enforcement reinforcement is added because `--print` mode lacks tool-level guardrails. In interactive mode, Claude Code's tool permissions block unauthorized file writes. In `--print` mode, only the system prompt constrains the model. The supplementary section adds explicit REFUSE instructions for each role's boundaries. (Severity: INFO)

### Test Quality Audit
- Rubric: 6/6 PASS
- Tests: 40 total, 40 passed
- AP scan: clean
- Date: 2026-03-24
