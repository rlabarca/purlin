# User Testing Discoveries: Skill Behavior Regression

### [BUG] Regression failure: architect-startup-command-table (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:architect-startup-command-table
- **Observed Behavior:** Architect startup outputs "I'm in Architect mode. What would you like me to plan?" -- no Unicode border command table, no /pl-spec or /pl-anchor references.
- **Expected Behavior:** Output contains a command table with Unicode border characters and references /pl-spec and /pl-anchor
- **Root Cause:** harness_runner.py `execute_agent_behavior()` does not construct the 4-layer system prompt or pass it via `--append-system-prompt-file`. Without role instructions, the agent has no Purlin context. Working reference: `dev/test_agent_behavior.sh` correctly implements prompt construction.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: builder-startup-identifies-todo (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:builder-startup-identifies-todo
- **Observed Behavior:** Builder startup outputs a standard markdown table (not Unicode borders) and does not propose a work plan or execution order.
- **Expected Behavior:** Output contains a command table with Unicode border characters AND proposes a work plan or execution order
- **Root Cause:** Same as architect-startup-command-table -- harness_runner.py missing 4-layer system prompt construction.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: qa-startup-identifies-testing (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:qa-startup-identifies-testing
- **Observed Behavior:** QA startup outputs a table structure but the assertion "Output identifies TESTING features" failed. QA used "Ready for Verification" instead of "TESTING".
- **Expected Behavior:** Output clearly identifies TESTING-state features
- **Root Cause:** Same as architect-startup-command-table -- harness_runner.py missing 4-layer system prompt construction. Without QA role instructions, the agent doesn't use CDD terminology.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: architect-refuses-code (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:architect-refuses-code
- **Observed Behavior:** Architect asked to fix code responded: "There's no `main.py` file in this repository. Could you provide the path?" -- did not refuse or reference zero-code mandate.
- **Expected Behavior:** Output refuses the request and references the zero-code mandate
- **Root Cause:** Same as architect-startup-command-table -- harness_runner.py missing 4-layer system prompt construction. Without ARCHITECT_BASE.md, the agent has no zero-code mandate.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: qa-refuses-code (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:qa-refuses-code
- **Observed Behavior:** QA asked to fix code responded: "There's no `utils.py` file in this repository. Could you provide the correct path?" -- did not refuse or reference zero-code mandate.
- **Expected Behavior:** Output refuses the request and references the zero-code mandate
- **Root Cause:** Same as architect-startup-command-table -- harness_runner.py missing 4-layer system prompt construction. Without QA_BASE.md, the agent has no code refusal instructions.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: status-skill-structured-summary (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:status-skill-structured-summary
- **Observed Behavior:** "Unknown skill: pl-status" -- skill not recognized in test fixture environment.
- **Expected Behavior:** Output contains feature counts by lifecycle status
- **Root Cause:** Fixture checkout does not include `.claude/commands/` skill files. Skills require interactive environment files to dispatch.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: architect-help-correct-commands (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:architect-help-correct-commands
- **Observed Behavior:** "Unknown skill: pl-help" -- skill not recognized in test fixture environment.
- **Expected Behavior:** Output contains /pl-spec and /pl-anchor
- **Root Cause:** Same as status-skill-structured-summary -- fixture missing `.claude/commands/` skill files.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: builder-help-correct-commands (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:builder-help-correct-commands
- **Observed Behavior:** "Unknown skill: pl-help" -- skill not recognized in test fixture environment.
- **Expected Behavior:** Output contains /pl-build
- **Root Cause:** Same as status-skill-structured-summary -- fixture missing `.claude/commands/` skill files.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Regression test (auto-detected)

### [BUG] H9: 12/17 regression assertions still failing (Discovered: 2026-03-23)
- **Observed Behavior:** 12 of 17 regression assertions still fail: role refusals fail, startup tables are not produced, and fixture is missing skill commands.
- **Expected Behavior:** All 17 regression assertions should pass with correct role refusal behavior, startup table production, and fixture skill commands present.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See skill_behavior_regression.impl.md for full context.
