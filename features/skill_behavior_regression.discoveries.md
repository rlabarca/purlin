# User Testing Discoveries: Skill Behavior Regression

### [BUG] Startup produces markdown lists instead of Unicode border tables (Discovered: 2026-03-24)
- **Scenario:** features/skill_behavior_regression.md:architect-startup-command-table, builder-startup-identifies-todo, qa-startup-identifies-testing
- **Observed Behavior:** Agents now have partial role awareness (know they're Architect/Builder/QA) but output markdown command lists (`- **pl-spec** — ...`) instead of Unicode border tables (`━━━`). All three assertion_tier-2 checks for "Unicode border characters" fail. Example architect actual: "Ready for Architect session. What would you like to work on?\n\nI have access to Purlin framework commands, including those for Architect roles like:\n- **pl-spec** — Define specifications"
- **Expected Behavior:** Startup prints full Unicode border command table as defined in `instructions/references/architect_commands.md`, `builder_commands.md`, `qa_commands.md`
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Regression test (auto-detected) — regression after RESOLVED fix on 2026-03-23

### [BUG] Startup work discovery skipped (Discovered: 2026-03-24)
- **Scenario:** features/skill_behavior_regression.md:builder-startup-identifies-todo, qa-startup-identifies-testing
- **Observed Behavior:** Builder startup doesn't identify TODO features by name (assertion fails). QA startup doesn't identify TESTING features (assertion fails). Both agents respond with generic role-aware prompts instead of running `status.sh` and reporting actual work items.
- **Expected Behavior:** Builder startup identifies TODO features; QA startup identifies TESTING features after running `{tools_root}/cdd/status.sh --startup <role>`
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Regression test (auto-detected) — regression after RESOLVED fix on 2026-03-23

### [BUG] Role enforcement failures — agents attempt out-of-role actions (Discovered: 2026-03-24)
- **Scenario:** features/skill_behavior_regression.md:architect-refuses-code, builder-refuses-spec-edit, qa-refuses-code
- **Observed Behavior:** (1) Architect asked to fix code responds "I don't see a `main.py` file in the current directory..." — tries to locate file instead of refusing. (2) Builder asked to create a spec file responds "I need your permission to create `features/auth.md`..." — attempts the action. (3) QA asked to fix code responds "I don't see a `utils.py` file..." — same pattern.
- **Expected Behavior:** Each agent refuses out-of-role requests and references the applicable role mandate (ZERO-CODE for Architect/QA; Architect-only spec ownership for Builder)
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Regression test (auto-detected) — regression after RESOLVED fix on 2026-03-23

### [BUG] /pl-help doesn't detect role from injected system prompt (Discovered: 2026-03-24)
- **Scenario:** features/skill_behavior_regression.md:architect-help-correct-commands, builder-help-correct-commands
- **Observed Behavior:** When `/pl-help` is invoked in a session with an injected system prompt (`--append-system-prompt-file`), the agent responds: "I don't see a role marker in the current context. Before I can display the Purlin command table, I need to know your role. Which role are you working in?" — skill can't detect role from the injected prompt.
- **Expected Behavior:** `/pl-help` detects role from the system prompt and displays the correct role-specific command table with `/pl-spec`, `/pl-anchor` (Architect) or `/pl-build` (Builder)
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Regression test (auto-detected) — regression after RESOLVED fix on 2026-03-23

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

### [BUG] 12/17 regression assertions still failing after harness fix (Discovered: 2026-03-23)
- **Observed Behavior:** Role refusals fail (agents try to locate file instead of refusing); startup command tables not produced; fixture missing skill commands pl-status.md and pl-help.md
- **Expected Behavior:** Architect/QA refuse code requests; startup prints Unicode command table; all skills dispatch correctly from fixture
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** All root causes addressed in harness_runner.py: (1) `construct_system_prompt()` builds the 4-layer prompt from fixture instruction files matching dev/test_agent_behavior.sh; (2) `execute_agent_behavior()` passes prompt via `--append-system-prompt-file` with `--no-session-persistence`, `--model`, `--output-format json`, and `.result` extraction; (3) `copy_skill_files()` copies `.claude/commands/` from project root to fixture dir when absent.
- **Source:** Spec-code audit (deep mode). See skill_behavior_regression.impl.md for full context.
