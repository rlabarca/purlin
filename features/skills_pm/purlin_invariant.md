# Feature: Invariant Management

> Label: "Agent Skills: PM: purlin:invariant Invariant Management"
> Category: "Agent Skills: PM"
> Owner: PM

## 1. Overview

The invariant management skill provides a unified interface for importing, syncing, validating, and auditing externally-sourced, locally-immutable constraint documents (invariants). Invariants extend the anchor node system with external authority — they originate from git repos or Figma and cannot be modified locally. The `purlin:invariant` command handles all invariant lifecycle operations.

Invariants enforce organizational mandates across project specs and code: architecture standards (CISO, tech lead), compliance (legal, security), operational requirements (ops teams), product goals (product management), and design systems (Figma).

---

## 2. Requirements

### 2.1 Invariant Identification

- All invariant files use the `i_` prefix prepended to the anchor type prefix: `i_arch_*`, `i_design_*`, `i_policy_*`, `i_ops_*`, `i_prodbrief_*`.
- The `i_` prefix is the single detection mechanism. `filename.startswith('i_')` identifies an invariant.
- Stripping `i_` yields the anchor type prefix for domain classification.

### 2.2 Anchor Type Extensions

Two new anchor type prefixes are introduced, available as both local anchors and invariants:

- `ops_*.md` — Operational integration: CI/CD, deployment, monitoring, infrastructure mandates. PM-owned.
- `prodbrief_*.md` — Product goals: user stories, outcomes, KPIs, success criteria. PM-owned.

The full anchor prefix set becomes: `('arch_', 'design_', 'policy_', 'ops_', 'prodbrief_')`.

### 2.3 Invariant Format

All invariant files MUST conform to the canonical format defined in `references/invariant_format.md`. Key requirements:

- Required metadata: `> Format-Version:`, `> Invariant: true`, `> Version:`, `> Source:`, `> Scope:`.
- Git-sourced invariants additionally require: `> Source-Path:`, `> Source-SHA:`, `> Synced-At:`.
- Figma-sourced invariants additionally require: `> Figma-URL:`, `> Synced-At:`.
- Required sections vary by type (see `references/invariant_format.md`):
  - arch/policy/ops: `## Purpose` + `## <Domain> Invariants`
  - design (including Figma-sourced): `## Purpose` + either `## <Domain> Invariants` or `## Figma Source`
  - prodbrief: `## Purpose` + `## User Stories` + `## Success Criteria`
  - `## Annotations` is optional for Figma design invariants (advisory content, not structurally required)

### 2.4 Format Versioning

- The invariant format spec is versioned (starting at `1.0`).
- Each invariant declares `> Format-Version:` to indicate conformance.
- The `purlin:invariant validate` subcommand warns when a file's format version exceeds Purlin's supported version.

### 2.5 Immutability

- No agent mode (Engineer, PM, QA) can write to `features/i_*.md` files.
- Changes come ONLY via `purlin:invariant add`, `purlin:invariant add-figma`, or `purlin:invariant sync`.
- The mode guard blocks all write attempts with a redirect message.
- The scan detects tampered invariant files via SHA-256 comparison against cached hashes.

### 2.6 Global vs Scoped Invariants

- `> Scope: global` — auto-applies to every non-anchor feature. No `> Prerequisite:` declaration needed.
- `> Scope: scoped` — features must explicitly declare `> Prerequisite: features/i_<type>_<name>.md`.
- Global invariants appear in `dependency_graph.json` under a `global_invariants` key, not as graph edges.

### 2.7 Cascade Behavior

- When a global invariant is updated via `sync`: ALL non-anchor features reset to `[TODO]`.
- When a scoped invariant is updated: only features with direct/transitive prerequisite links reset.
- Cascade scope follows semver:
  - MAJOR bump → full cascade.
  - MINOR bump → cascade with warning.
  - PATCH bump → no cascade (informational only).
- The commit tag `invariant-sync(...)` exempts sync commits from false "modified after completion" flags.

### 2.8 No Separate Manifest

- No `.purlin/invariants.json` manifest file. The `i_*` files in `features/` ARE the source of truth.
- Tools discover invariants via glob `features/i_*.md` and read `>` metadata lines with early-termination regex.
- Tamper detection uses SHA-256 hashes stored in `.purlin/cache/scan.json`.

### 2.9 Storage

- Invariant files live in `features/` alongside regular anchors.
- Tamper detection hashes and scan state for invariants are stored within `.purlin/cache/scan.json` (no separate constraint cache file).

---

## 3. Subcommands

If no subcommand is provided, print the usage table and stop.

### 3.1 `add <repo-url> [file-path]`

**Mode:** PM

Import an invariant from an external git repo.

1. Shallow-clone the external repo (depth 1).
2. Locate the target file in the repo's `features/` directory (or specified path).
3. Validate format: required sections and `> Version:` metadata present.
4. If `> Scope:` is missing, prompt PM to choose global or scoped.
5. Inject/verify invariant metadata (`> Format-Version: 1.1` if not present, `> Invariant: true`, `> Source:`, `> Source-Path:`, `> Source-SHA:`, `> Synced-At:`).
6. Copy to `features/` with `i_` prefix prepended to the filename.
7. Commit with tag: `invariant-add(features/i_<type>_<name>.md): v<version> from <repo>`.
8. Run `scan.sh` to integrate into dependency graph and trigger cascade if global.
9. Clean up shallow clone.

### 3.2 `add-figma <figma-url> [existing-anchor]`

**Mode:** PM. **Requires Figma MCP** — no fallback.

Create a Figma-sourced design invariant.

1. Verify Figma MCP is available (check for `get_design_context` in tool list). If not, provide setup instructions and stop.
2. Fetch Figma file metadata via `get_metadata` (fileKey from URL): version ID, last modified, file name.
3. Extract design context via `get_design_context` (fileKey + nodeId): annotations (behavioral notes, interaction descriptions, edge cases), design token CSS variables, and Code Connect snippets (if configured).
4. Extract variable definitions via `get_variable_defs` (fileKey): variable names, types, and collection groupings. Stored in `## Design Variables` section (names and types only, not resolved values).
5. Check Code Connect: if `get_design_context` returned Code Connect snippets, note their presence in `## Code Connect` section (informational).
6. Create a thin pointer file `features/_invariants/i_design_<name>.md` with invariant metadata, Purpose (PM provides), Figma Source boilerplate, Design Variables, Code Connect (if present), and Annotations section (advisory).
7. If upgrading an existing `design_*.md` anchor:
   - Update all `> Prerequisite:` and `> **Design Anchor:**` references in feature files.
   - Delete the old `design_*.md` file.
8. Commit with tag: `invariant-add(features/_invariants/i_design_<name>.md): Figma-sourced`.
9. Run `purlin_scan` to cascade-reset dependent features.

### 3.3 `sync [file-name | --all]`

**Mode:** PM

Pull latest version from source.

**Git-sourced:**
1. Shallow-clone the source repo.
2. Compare version and content against local.
3. If unchanged: report "already current".
4. If changed: show diff, report version delta (MAJOR = breaking, flag prominently).
5. Present cascade impact (features that will reset).
6. On confirmation: overwrite local file, update embedded metadata.
7. Commit with tag: `invariant-sync(features/i_<name>.md): v<old> -> v<new>`.
8. Run `scan.sh` to trigger cascade (semver-gated).

**Figma-sourced:**
1. Fetch current Figma file metadata via `get_metadata` (fileKey).
2. Compare `figma_version_id` against stored `> Version:`.
3. If changed: update pointer metadata (`> Version:`, `> Synced-At:`), re-extract annotations via `get_design_context`, re-extract variable definitions via `get_variable_defs`, update Code Connect presence, flag briefs as stale.
4. Commit and cascade same as git-sourced.

### 3.4 `check-updates`

**Mode:** Any (read-only)

Check all invariants for new versions. Fast — no clone.

- Git-sourced: `git ls-remote <source-url> HEAD` to compare SHA.
- Figma-sourced: fetch file version ID via `get_metadata` (fileKey) if available.
- Report summary: N checked, M have updates available.

### 3.5 `check-conflicts`

**Mode:** Any (read-only)

Agent-driven semantic analysis of invariant statements:

1. Group all invariants by type prefix.
2. Extract invariant statements from each.
3. Also extract local anchors of matching types.
4. Analyze for invariant-to-invariant and invariant-to-anchor contradictions.
5. Report conflicts with severity and specific contradicting statements.

### 3.6 `check-feature <feature> [--all]`

**Mode:** Any (read-only)

Check feature adherence to applicable invariants:

1. Determine applicable invariants (global + transitive scoped prerequisites).
2. For each: grep FORBIDDEN patterns, check invariant statement coverage, validate Token Maps (design).
3. Report per-feature, per-invariant, per-constraint compliance with file:line evidence.

### 3.7 `validate`

**Mode:** Any (read-only)

Validate all `i_*` files:

1. Required metadata fields present.
2. Format version compatibility.
3. Required sections per type.
4. Type prefix valid after stripping `i_`.
5. Report issues per file.

### 3.8 `list`

**Mode:** Any (read-only)

List all active invariants with version, scope, source type, and sync status.

### 3.9 `remove <file-name>`

**Mode:** PM

Remove an invariant: delete file, update prerequisite links in dependent features, commit, run scan.

---

## 4. Design Invariant Specifics

### 4.1 Three-Tier Design Model

| Tier | Source | Local File | Invariant? |
|------|--------|-----------|-----------|
| Git markdown | External git repo | `i_design_*.md` (full content) | Yes |
| Figma | Figma document | `i_design_*.md` (thin pointer) | Yes |
| Local | Project team | `design_*.md` (regular anchor) | No |

Local assets (images, PDFs, web URLs) are regular `design_*.md` anchors, not invariants.

### 4.2 Figma Pointer Model

Figma invariants are thin pointer files. The Figma document is the authority. The pointer captures three categories of Figma data:

- **Design Variables** (from `get_variable_defs`) — variable names and types grouped by collection. Used by `purlin:spec` for Token Map auto-seeding and by `purlin:design-audit` for drift detection.
- **Code Connect** (from `get_design_context`, optional) — presence indicator for component-to-code mappings. Used by `purlin:spec` to auto-populate `brief.json`.
- **Annotations** (from `get_design_context`) — advisory behavioral notes for PM spec authoring.

Per-feature `brief.json` files cache resolved Figma data (dimensions, token values, Code Connect mappings) for Engineers. Briefs are created during `purlin:spec` when PM specifies Figma frames for a feature.

### 4.3 Annotation Model

Figma annotations extracted via `get_design_context` are stored in the pointer's `## Annotations` section. They are **advisory, not binding** — like user stories in a prodbrief. PM reads them during `purlin:spec` and decides which to adopt, adapt, or skip.

### 4.4 Design Enforcement Weight

| Aspect | Enforcement |
|--------|-------------|
| Colors / design tokens | Strict — build warns, audit flags as HIGH. Hardcoded hex = FORBIDDEN. |
| Typography | Strict — measurable from brief.json |
| Spacing / layout | Moderate — warned, not blocked |
| Annotations (behavioral) | Advisory — informs spec only |

### 4.5 `purlin:design-ingest` Retirement

`purlin:design-ingest` is retired. Its responsibilities are split across `purlin:invariant add-figma`, `purlin:invariant sync`, and `purlin:spec` (Visual Specification authoring).

---

## 5. Enforcement Integration Points

### 5.1 `purlin:build` Step 0 (Preflight)

- Collect applicable invariants (global + scoped prerequisites).
- FORBIDDEN pre-scan: compile patterns into combined regex per scope glob (P1 optimization). Block on violations.
- Surface behavioral invariants as reminders.
- For Figma design invariants: check brief staleness, compare CSS/styles against Token Map in Step 3.

### 5.2 `purlin:spec` (Spec Authoring)

- Advisory: show applicable global invariants before commit.
- Suggest scoped invariant prerequisites based on domain overlap.
- When feature references a Figma invariant: auto-seed Token Map from `get_design_context` and `get_variable_defs` output, generate brief.json (with Code Connect data if available), author checklists.

### 5.3 `purlin:spec-code-audit` (Audit)

- Phase 0.3: auto-include global invariants in constraint payload.
- Phase 1: FORBIDDEN scan + invariant coverage check. Split payload by checkability (P4 optimization).
- New Dimension 14: Invariant Source Compliance.

### 5.4 Companion Files

- Companion entries SHOULD reference invariant constraints: `[IMPL] ... per i_arch_api_standards.md INV-2`.
- Invariant deviations escalate as "invariant conflict" rather than normal "spec deviation".

---

## 6. Reporting

### 6.1 Invariant Audit Subcommand

`purlin:invariant audit` — comprehensive audit combining format validation, sync status, feature compliance, cross-invariant conflict detection, and a structured violation report. Runs in any mode (read-only). See `skills/invariant/SKILL.md` for the full protocol.

### 6.2 `purlin:spec-code-audit` Dimension 14

Invariant source compliance: FORBIDDEN violations (HIGH), coverage gaps (MEDIUM), staleness (LOW).

---

## 7. Performance

Key mitigations from the performance analysis:

- P1: Compile FORBIDDEN patterns into combined regex per scope glob (2-3 passes vs 15-25).
- P2: Scope CSS/style comparison to `git diff --name-only` changed files.
- P3: Semver-gated cascade (PATCH = no cascade).
- P4: Split subagent payloads by checkability.
- P5: Invert `check-feature --all` to O(patterns) instead of O(features × patterns).
- P6: Batch Figma MCP extraction.
- P7: Cache conflict results by invariant content hashes.

---

### Unit Tests

Scenario: Detect invariant files
  Given a features directory with `i_arch_api.md` and `arch_data.md`
  When the scan runs
  Then `i_arch_api.md` is classified as an invariant
  And `arch_data.md` is classified as a regular anchor

Scenario: Validate invariant metadata
  Given an `i_policy_security.md` file missing `> Scope:` metadata
  When `purlin:invariant validate` runs
  Then a validation error is reported for the missing Scope field

Scenario: Detect tampered invariant
  Given an `i_arch_api.md` file that was manually edited after the last scan
  And no recent `invariant-sync(...)` commit
  When the scan runs
  Then the file is flagged as `invariant_tampered`

Scenario: Global invariant cascade
  Given a global invariant `i_policy_security.md` at version 2.0.0
  When the invariant is synced to version 3.0.0 (MAJOR bump)
  Then all non-anchor features reset to `[TODO]`

Scenario: PATCH bump does not cascade
  Given a global invariant `i_policy_security.md` at version 2.1.0
  When the invariant is synced to version 2.1.1 (PATCH bump)
  Then no features are reset
  And the scan surfaces the update as informational

Scenario: FORBIDDEN pattern blocks build
  Given a feature governed by `i_policy_security.md` with FORBIDDEN pattern `eval\(`
  And the feature's code contains `eval(user_input)` at `handler.py:42`
  When `purlin:build` runs Step 0 preflight
  Then the build is blocked with an actionable violation message

Scenario: Prodbrief section detection
  Given an `i_prodbrief_q2.md` file with `## User Stories` and `## Success Criteria`
  When `purlin:invariant validate` runs
  Then the file passes validation (prodbrief sections detected correctly)

### QA Scenarios

Scenario: Add invariant from git repo @auto
  Given an external git repo with `features/policy_security.md`
  When PM runs `purlin:invariant add <repo-url> policy_security.md`
  Then `features/_invariants/i_policy_security.md` is created with injected metadata
  And the dependency graph includes the new invariant
  And the scan shows the invariant in its output

Scenario: Add Figma design invariant @auto
  Given Figma MCP is available
  And a Figma file URL for the project design system
  When PM runs `purlin:invariant add-figma <figma-url>`
  Then `features/_invariants/i_design_<name>.md` is created as a thin pointer
  And the Annotations section contains behavioral notes extracted via `get_design_context`
  And the Design Variables section contains variable names and types from `get_variable_defs`
  And dependent features are cascade-reset

Scenario: Add Figma design invariant with Code Connect @auto
  Given Figma MCP is available
  And a Figma file URL with Code Connect mappings configured
  When PM runs `purlin:invariant add-figma <figma-url>`
  Then the pointer includes a Code Connect section noting mappings are available
  And the Annotations section contains behavioral notes

Scenario: Sync detects Figma update @auto
  Given a Figma invariant at version v100
  And the Figma file has been updated to version v200
  When PM runs `purlin:invariant sync i_design_<name>.md`
  Then the pointer's `> Version:` is updated to v200
  And annotations are re-extracted via `get_design_context`
  And variable definitions are re-extracted via `get_variable_defs`
  And dependent features' briefs are flagged as stale

Scenario: Mode guard blocks invariant write @manual
  Given the agent is in Engineer mode
  When the agent attempts to write to `features/_invariants/i_policy_security.md`
  Then the write is blocked
  And the agent displays a redirect message mentioning `purlin:invariant sync`

Scenario: Upgrade existing design anchor to Figma invariant @auto
  Given `features/design_visual_standards.md` exists with 5 dependent features
  When PM runs `purlin:invariant add-figma <figma-url> design_visual_standards.md`
  Then the old file is deleted
  And `features/i_design_visual_standards.md` is created
  And all 5 features' prerequisite links are updated to the new filename
  And all 5 features are cascade-reset to `[TODO]`

Scenario: Invariant audit subcommand @manual
  Given 3 invariants exist (1 global, 2 scoped) and 1 has a FORBIDDEN pattern violation
  When the user runs `purlin:invariant audit`
  Then the report shows format validation, sync status, feature compliance, cross-invariant conflicts, and actionable violations with owners
