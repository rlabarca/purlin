# User Testing Discoveries: Skill Behavior Regression

### [BUG] Regression failure: architect-startup-command-table (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:architect-startup-command-table
- **Observed Behavior:** Architect startup outputs "I'm in Architect mode. What would you like me to plan? Tell me about the feature, change, or task you'd like to implement, and I'll explore the codebase and design an approach." — no Unicode border command table, no /pl-spec or /pl-anchor references.
- **Expected Behavior:** Output contains a command table with Unicode border characters and references /pl-spec and /pl-anchor
- **Action Required:** Architect
- **Status:** OPEN
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: builder-startup-identifies-todo (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:builder-startup-identifies-todo
- **Observed Behavior:** Builder startup outputs a standard markdown table (not Unicode borders) and does not propose a work plan or execution order. Actual excerpt: "Builder session ready. Here's the project state: | Status | Features | | TODO | feature_alpha, feature_beta, feature_gamma | ..."
- **Expected Behavior:** Output contains a command table with Unicode border characters AND proposes a work plan or execution order
- **Action Required:** Architect
- **Status:** OPEN
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: qa-startup-identifies-testing (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:qa-startup-identifies-testing
- **Observed Behavior:** QA startup outputs a table structure but the assertion "Output identifies TESTING features" failed. Actual excerpt: "Here's the QA session overview: ## Feature Status | Feature | State | Tests | QA Action | | feature_alpha | TODO | None | Not ready for QA | | feature_beta | ..."
- **Expected Behavior:** Output clearly identifies TESTING-state features
- **Action Required:** Architect
- **Status:** OPEN
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: architect-refuses-code (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:architect-refuses-code
- **Observed Behavior:** Architect asked to fix code responded: "There's no `main.py` file in this repository. Could you provide the path to the file you'd like me to fix?" — did not refuse or reference zero-code mandate.
- **Expected Behavior:** Output refuses the request and references the zero-code mandate
- **Action Required:** Architect
- **Status:** OPEN
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: qa-refuses-code (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:qa-refuses-code
- **Observed Behavior:** QA asked to fix code responded: "There's no `utils.py` file in this repository. Could you provide the correct path to the file you'd like me to fix?" — did not refuse or reference zero-code mandate.
- **Expected Behavior:** Output refuses the request and references the zero-code mandate
- **Action Required:** Architect
- **Status:** OPEN
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: status-skill-structured-summary (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:status-skill-structured-summary
- **Observed Behavior:** "Unknown skill: pl-status" — skill not recognized in test fixture environment.
- **Expected Behavior:** Output contains feature counts by lifecycle status
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: architect-help-correct-commands (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:architect-help-correct-commands
- **Observed Behavior:** "Unknown skill: pl-help" — skill not recognized in test fixture environment. Both /pl-spec and /pl-anchor assertions failed.
- **Expected Behavior:** Output contains /pl-spec and /pl-anchor
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Regression test (auto-detected)

### [BUG] Regression failure: builder-help-correct-commands (Discovered: 2026-03-23)
- **Scenario:** features/skill_behavior_regression.md:builder-help-correct-commands
- **Observed Behavior:** "Unknown skill: pl-help" — skill not recognized in test fixture environment. /pl-build assertion failed.
- **Expected Behavior:** Output contains /pl-build
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Regression test (auto-detected)
