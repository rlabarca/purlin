# Hard Gates (Always Active)

These mechanical checks apply **regardless of how work started** — skill invocation, resume flow, user instruction, or auto-start. They are non-negotiable. For full orchestration (parallel dispatch, merge protocol, phase transitions), invoke the skill (`purlin:build`, `purlin:spec`, `purlin:verify`).

## Engineer Gates

**Before implementation:**
- **Spec existence:** `features/<name>.md` MUST exist. If missing, offer PM mode switch. STOP if declined.
- **FORBIDDEN pre-scan:** Collect invariants (global from `dependency_graph.json` + scoped from `> Prerequisite:` chain). Extract `## FORBIDDEN Patterns`. Grep feature code files. Any match **blocks the build** with file:line and fix guidance.
- **Re-verification fast path:** If scan shows `has_passing_tests: true` AND no scenario diff AND no requirements changed, run existing tests and re-tag. Do NOT re-implement.
- **Role-blocked skip:** In delivery plans, skip features with `architect: TODO`, `builder: BLOCKED`, or `builder: INFEASIBLE`. Log skip and proceed to next.

**During implementation:**
- **Companion file minimum:** Every code commit for a feature MUST include a companion file update — at minimum one `[IMPL]` line. No "matches spec = no entry needed" exemption.
- **Execution group dispatch:** When delivery plan has 2+ independent features in the active group, check `dependency_graph.json` pairwise independence and spawn `engineer-worker` sub-agents. Sequential processing of independent features is a protocol violation.
- **Fast feedback only:** Engineer's build loop runs unit tests (seconds) and web tests (seconds per page). Regression suites (minutes) are QA-owned and MUST NOT gate the build cycle. If a feature has no unit tests, write them — don't substitute regression scenarios.

**Before status tag:**
- **Status tag is a separate commit.** Never combine with implementation work.
- **Pre-checks (ALL must pass):**
  - Companion file has new entries this session
  - Web test passed with zero BUG and zero DRIFT if feature has `> Web Test:` or `> AFT Web:` metadata
  - Spec alignment: re-read spec, walk each requirement and scenario, verify implementation addresses each, log gaps as `[DISCOVERY]`
  - Plan alignment: if delivery plan was used, verify deliverables match
- **`[Verified]` is QA-only.** Engineer MUST NOT include `[Verified]` in status commits.
- **Web Test TBD:** If feature has `> Web Test: TBD`, replace TBD with actual URL after building server. This resets to TODO; follow re-verification fast path.
- **`tests.json` must come from a test runner** — never hand-written. Required: `status`, `passed`, `failed`, `total` (> 0).
- **Cross-cutting triage:** When a fix reveals undocumented constraints, use `purlin:propose` to record `[SPEC_PROPOSAL: NEW_ANCHOR]`. Use `[DISCOVERY]` only when the constraint fits an existing anchor's scope.

## PM Gates

- **Scenario heading format:** MUST use `#### Scenario: Title` (four hashes). NOT `###`, NOT bold, NOT list items. The scan parser depends on this exact format.
- **Required sections:** Every feature file MUST contain headings matching `overview`, `requirements`, and `scenarios` (case-insensitive). Without these, the scan cannot parse the feature.
- **No Implementation Notes:** Feature files MUST NOT contain `## Implementation Notes`. Implementation knowledge belongs in companion files (`features/<name>.impl.md`).
- **Prerequisite checklist:** Before committing a new or updated spec, check: renders UI -> design anchors; accesses data -> arch anchors; governed process -> policy anchors; design artifacts -> `design_artifact_pipeline.md`; operational mandate -> ops anchors.
- **Scenarios are untagged:** Write scenarios without `@auto`/`@manual` tags. Tags are QA-owned.

## QA Gates

- **Lifecycle diagnostic:** After scan, if scoped feature is TODO, search git log on other branches for status commits. If found on another branch, report branch divergence and STOP (interactive) or log and exit (auto_start).
- **Regression readiness:** Before Phase A tests run, all in-scope `@auto` scenarios MUST have regression JSON in `tests/qa/scenarios/`. In auto mode, author missing JSON via internal Engineer switch. In interactive mode, surface gaps in strategy menu.
- **Auto-start silence:** When `auto_start: true`, execute ALL Phase A steps without user prompts. No approval gates, no "shall I proceed?" questions.
- **Scoped verification modes:** Respect scope from status tag — `full` (default), `targeted:A,B` (named scenarios only), `cosmetic` (skip), `dependency-only` (listed scenarios only).
- **`[Verified]` is mandatory:** QA status commits MUST include `[Verified]` tag.
- **Delivery plan gating:** Do NOT mark `[Complete]` if the feature appears in a PENDING phase.
- **Companion file edits do NOT reset status.** Only edits to the feature spec (`<name>.md`) trigger lifecycle resets.
