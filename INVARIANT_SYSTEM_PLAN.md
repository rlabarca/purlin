# Invariant System Design Plan

## Context

Purlin's existing anchor nodes (`arch_*`, `design_*`, `policy_*`) define project-internal constraints that cascade-reset dependent features when edited. The invariant system extends this with **externally-sourced, locally-immutable constraint documents** — pulled from external git repos or Figma — that enforce organizational mandates (architecture standards, compliance, operational requirements, product goals, design systems) across all project specs and code.

The core problem: anchors today are locally authored and locally editable. Organizations need constraints that originate from external authorities (a CISO's compliance repo, an architect's standards repo, a Figma design system) and cannot be modified by the project team — only synced from the external source.

---

## 1. Core Invariant Model

### 1.1 Identification: `i_` Filename Prefix

ALL invariants use the `i_` prefix prepended to the type prefix. This is the single detection mechanism — no dual-signal approach.

```
features/i_arch_api_contracts.md       # Architecture invariant from external repo
features/i_policy_gdpr_compliance.md   # Compliance invariant from CISO repo
features/i_ops_cicd_pipeline.md        # Operational invariant
features/i_prodbrief_q2_goals.md       # Product brief invariant
features/i_design_visual_standards.md  # Design invariant (Figma-upgraded)
```

Detection in scan.py: `filename.startswith('i_')` identifies an invariant. Strip `i_` to get the anchor type prefix for domain classification.

### 1.2 New Anchor Types: `ops_` and `prodbrief_`

Two new anchor type prefixes available as BOTH local anchors and invariants:

| Prefix | Domain | Owner | As Local Anchor | As Invariant |
|--------|--------|-------|-----------------|-------------|
| `ops_*.md` | Operational integration — CI/CD, deployment, monitoring, infrastructure mandates | PM | Yes | `i_ops_*.md` |
| `prodbrief_*.md` | Product goals — user stories, outcomes, KPIs, success criteria | PM | Yes | `i_prodbrief_*.md` |
| `arch_*.md` | (existing) Software architecture | Engineer | Yes | `i_arch_*.md` |
| `design_*.md` | (existing) Design language & UX | PM | Yes | `i_design_*.md` |
| `policy_*.md` | (existing) Governance & compliance | PM | Yes | `i_policy_*.md` |

Full anchor prefix set becomes: `('arch_', 'design_', 'policy_', 'ops_', 'prodbrief_')`
Full invariant detection: any file in `features/` starting with `i_` followed by one of the above prefixes.

### 1.3 Invariant Spec Version

The invariant format itself is versioned. The canonical format reference at `instructions/references/invariant_format.md` declares a format version (starting at `1.0`). Invariant files declare `> Format-Version: 1.0` to indicate which version of the Purlin invariant spec they conform to.

This allows:
- External repos to target a specific format version
- Purlin to validate and warn on format version mismatches (e.g., "this invariant uses format 2.0 but your Purlin only supports 1.x")
- Future format evolution without breaking existing invariants

### 1.4 Canonical Invariant Markdown Format

This format MUST be stored as a reference document in the Purlin project at `instructions/references/invariant_format.md` for easy reference by external invariant authors. The reference doc itself carries `Format-Version: 1.0`.

#### Base Template (arch_, policy_, ops_)

```markdown
# <Type>: <Name>

> Label: "<Category>: <Name>"
> Category: "<Category>"
> Format-Version: 1.0
> Invariant: true
> Version: <semver>
> Source: <git-repo-url>
> Source-Path: <path-within-repo>
> Source-SHA: <git-commit-sha>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>

## Purpose

<One paragraph: what constraints this invariant enforces and why they exist.
Must answer: What organizational authority mandates these constraints?>

## <Domain> Invariants

### <Invariant Group Name>

- <INV-1> <Invariant statement — specific, testable, unambiguous>
- <INV-2> <Invariant statement>

### <Another Group>

- <INV-3> <Invariant statement>

## FORBIDDEN Patterns

<Optional. Machine-grepable patterns that MUST NOT appear in code.>

*   <Description of violation> (Invariant <INV-N>).
    *   **Pattern:** `<regex>`
    *   **Scope:** `<glob pattern for target files>`
    *   **Exemption:** <When the pattern is acceptable, if ever>

## Verification Scenarios

<Scenarios that describe how compliance with this invariant should be verified.
These are NOT directly executable by Purlin QA — they are requirements that
the project's features must satisfy. The project maps these to concrete
feature-level QA scenarios and unit tests.>

### <Scenario Group>

Scenario: <Scenario Name>
  Given <precondition>
  When <action>
  Then <expected outcome that demonstrates invariant compliance>
```

#### Product Brief Template (prodbrief_)

Product briefs have a different shape — they define outcomes, not technical constraints. User stories and acceptance criteria replace the invariant statements.

```markdown
# Product Brief: <Name>

> Label: "Product: <Name>"
> Category: "<Category>"
> Format-Version: 1.0
> Invariant: true
> Version: <semver>
> Source: <git-repo-url>
> Source-Path: <path-within-repo>
> Source-SHA: <git-commit-sha>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>

## Purpose

<One paragraph: the product goal this brief defines. What problem does this
solve for users? What business outcome does it drive?>

## User Stories

### <Epic or Theme Name>

- As a <role>, I want to <goal>, so that <benefit>
- As a <role>, I want to <goal>, so that <benefit>

### <Another Epic>

- As a <role>, I want to <goal>, so that <benefit>

## Success Criteria

<Measurable outcomes that define whether the product goal has been met.
These are the KPIs and acceptance thresholds the product must achieve.>

- <KPI-1> <Measurable outcome with target — e.g., "User onboarding completes in <2 minutes">
- <KPI-2> <Measurable outcome>

## Acceptance Scenarios

<Concrete scenarios that demonstrate the product meets user stories.
These map to feature-level QA scenarios. PM uses these to verify the
product meets the brief; QA uses them as the basis for test design.>

### <Story Reference>

Scenario: <Scenario Name>
  Given <user context>
  When <user action>
  Then <expected product behavior>
```

#### Design Invariant — Git-Hosted Markdown (design_)

A design invariant hosted in an external git repo uses the base template. It defines design constraints, tokens, and FORBIDDEN patterns as markdown — same as arch/policy/ops. **No local asset references allowed** (no images, PDFs, or web URLs). If you need those, use a regular local `design_*.md` anchor instead.

```markdown
# Design: <Name>

> Label: "Design: <Name>"
> Category: "<Category>"
> Format-Version: 1.0
> Invariant: true
> Version: <semver>
> Source: <git-repo-url>
> Source-Path: <path-within-repo>
> Source-SHA: <git-commit-sha>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>

## Purpose

<What visual/interaction constraints this design system enforces.>

## Design Invariants

### <Token/Pattern Group>

- <INV-1> <Design constraint — e.g., "All primary actions use var(--accent)">

## FORBIDDEN Patterns

<Grepable violations of design tokens.>

## Verification Scenarios

<Visual verification scenarios.>

Scenario: <Screen or Component>
  Given the <component> is rendered
  Then the background uses var(--surface)
  And the primary text uses var(--primary)
```

#### Design Invariant — Figma-Sourced (design_)

A Figma-sourced design invariant is a **thin pointer file**. The Figma document IS the authority — the local file just links to it. Per-feature `brief.json` files cache Figma data for Engineers.

```markdown
# Design: <Name>

> Label: "Design: <Name>"
> Category: "<Category>"
> Format-Version: 1.0
> Invariant: true
> Version: <figma-version-id>
> Source: figma
> Figma-URL: <figma-file-url>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>

## Purpose

<One paragraph: what design system this Figma file defines.>

## Figma Source

This invariant is governed by the Figma document linked above.
Design tokens, constraints, and visual standards are defined in Figma
and cached locally in per-feature `brief.json` files during spec authoring.

## Annotations

<Advisory behavioral notes extracted from Figma annotations during
add/sync. These are NOT binding — they inform spec authoring like
user stories in a product brief. PM validates and may discard.>

- <Annotation from Figma: e.g., "Empty state shows illustration + CTA">
- <Annotation: e.g., "Loading skeleton uses shimmer animation">
- <Annotation: e.g., "Error state preserves form input">
```

The Figma invariant file is intentionally minimal. No token tables, no FORBIDDEN patterns, no verification scenarios — those live in the Figma document. Annotations are advisory, not absolute.

**Enforcement weight within Figma invariants:**

| Aspect | Weight | Rationale |
|--------|--------|-----------|
| Colors / design tokens | **Strict** — build warns, audit flags | Colors are objective, machine-verifiable, directly from Figma variables |
| Layout / spacing / typography | **Strict** — build warns, audit flags | Measurable properties extracted to brief.json |
| Annotations (behavioral) | **Advisory** — informs spec writing | Like prodbrief user stories. PM decides what becomes a scenario. |

#### Design References That Are NOT Invariants

Local images, PDFs, web page screenshots, HTML mockups — these are regular `design_*.md` anchor files, locally authored and locally editable. They never get the `i_` prefix. The distinction:

| Source | File | Invariant? | Editable locally? |
|--------|------|-----------|-------------------|
| External git repo (markdown only) | `i_design_*.md` | Yes | No — sync from source |
| Figma (via MCP) | `i_design_*.md` (pointer) | Yes | No — sync from Figma |
| Local images, PDFs, web URLs | `design_*.md` | No | Yes — regular anchor |

### 1.5 Scenarios Section: What It Is and What It Isn't

**Invariant scenarios are requirements, not tests.** They describe how compliance with the invariant should be verified — the shape of correctness. They are NOT directly executable by Purlin QA.

**How they flow into the project:**
1. PM reads invariant scenarios when writing feature specs
2. PM maps relevant invariant scenarios to concrete feature-level QA scenarios and unit tests
3. Engineer implements the feature-level tests
4. QA executes the feature-level tests
5. `/pl-spec-code-audit` checks if invariant scenarios have corresponding feature-level coverage

**Per invariant type:**

| Type | Scenarios Describe | Maps To |
|------|-------------------|---------|
| `arch_` | Technical compliance verification | Unit tests, integration tests |
| `policy_` | Compliance/security verification | QA scenarios, audit checks |
| `ops_` | Operational integration verification | Integration tests, deployment checks |
| `prodbrief_` | Product acceptance verification | QA scenarios (functional + UX) |
| `design_` | Visual compliance verification | Visual Specification checklists, `/pl-web-test` |

**Coverage checking:** `/pl-spec-code-audit` Phase 1 already checks if each invariant statement has scenario/code coverage. With explicit verification scenarios in the invariant, this check becomes more precise — the audit can match invariant scenarios to feature-level scenarios by name or content overlap.

### 1.6 Required Metadata Fields

| Field | Required | Description |
|-------|----------|-------------|
| `> Format-Version:` | Yes | Invariant spec format version (e.g., `1.0`) |
| `> Invariant: true` | Yes | Marks this as an externally-sourced invariant |
| `> Version:` | Yes | Content version (semver). If absent in source, defaults to `0.0.0` |
| `> Source:` | Yes | Git repo URL (for git-sourced) or `figma` (for Figma-sourced) |
| `> Source-Path:` | Yes (git) | Original file path within the source repo |
| `> Source-SHA:` | Yes (git) | Git commit SHA the file was pulled from |
| `> Synced-At:` | Yes | ISO 8601 timestamp of last sync |
| `> Scope:` | Yes | `global` (applies to all features) or `scoped` (requires prerequisite declaration) |

### 1.7 Required Sections by Type

| Section | arch_ / policy_ / ops_ | prodbrief_ | design_ |
|---------|----------------------|------------|---------|
| `## Purpose` | Required | Required | Required |
| `## <Domain> Invariants` | Required | — | Required |
| `## User Stories` | — | Required | — |
| `## Success Criteria` | — | Required | — |
| `## FORBIDDEN Patterns` | Optional (recommended) | — | Optional |
| `## Verification Scenarios` or `## Acceptance Scenarios` | Optional (recommended) | Optional (recommended) | Optional |

The scan detects the appropriate sections per type: for prodbrief_ it checks for `## User Stories` instead of `## * Invariants`.

**Source repo requirements:** The external repo needs only a `features/` directory containing markdown files in this format. No other structure is required.

### 1.8 No Separate Manifest — Files ARE the Source of Truth

**Rejected: `.purlin/invariants.json` manifest.** The scan already reads all 73+ feature files with aggressive caching and early-termination. Adding 5-20 invariant files costs ~100-380 KB of I/O — negligible. A separate manifest would duplicate metadata already embedded in the markdown files, create a sync problem (manifest vs file drift), and add a committed file to maintain. Not worth the complexity.

**How tools discover invariants:** Glob `features/i_*.md`. The scan already does this for all feature files. Tools that need source URLs, versions, or scope read the `>` metadata lines directly — the same early-termination regex extraction used for Label, Category, and Prerequisite today.

**Tamper detection:** The scan computes SHA-256 of each `i_*` file on every run and compares against the hash from the previous scan (stored in `.purlin/cache/scan.json` alongside other scan state). No separate hash registry needed.

### 1.9 Storage

Invariant files live in `features/` alongside regular anchors. The `i_` prefix provides visual clustering in directory listings and programmatic separation. No separate subdirectory — the dependency graph already scans `features/` flat.

The constraint cache `.purlin/cache/invariant_constraints.json` is gitignored (regenerated from source files). No other invariant-specific state files are needed.

---

## 2. Immutability Enforcement

### 2.1 Mode Guard (Primary)

Add INVARIANT classification to `instructions/references/file_classification.md`:

```
## INVARIANT (External, immutable)

- Invariant files (`features/i_*.md`)
- NO mode (Engineer, PM, QA) can write to these files
- Changes ONLY via `/pl-invariant sync` or `/pl-invariant add`
- The mode guard blocks ALL write attempts with:
  "This is an externally-sourced invariant. Changes come only from
   the external source via /pl-invariant sync."
```

This is the primary enforcement. The agent's mode guard checks file classification before every write.

### 2.2 Scan-Time Integrity Check (Secondary)

New function `scan_invariant_integrity()` in `scan.py`:
1. Read each `i_*` file from `features/`
2. Compute SHA-256 of file content
3. Compare against the hash stored in the previous scan's cached state (`.purlin/cache/scan.json`)
4. If hash changed and no recent `invariant-sync(...)` commit tag: flag as `invariant_tampered` in scan output
5. This catches edits via git, external editors, or any path bypassing the mode guard

### 2.3 Commit Tag Exemption

When `/pl-invariant sync` updates a file, it uses the commit tag `invariant-sync(...)`. The scan's exemption logic recognizes this tag so invariant sync commits don't trigger false "modified after completion" flags.

---

## 3. Global vs Scoped Invariants

### 3.1 Scope Metadata

Each invariant declares `> Scope: global` or `> Scope: scoped` in its metadata.

- **Global** (`> Scope: global`): Auto-applies to EVERY non-anchor feature. No `> Prerequisite:` declaration needed. Examples: security compliance, coding standards, operational mandates.
- **Scoped** (`> Scope: scoped`): Features must explicitly declare `> Prerequisite: features/i_arch_api_contracts.md`. Examples: API-specific architecture, feature-specific design standards.

### 3.2 Graph Integration

The dependency graph JSON gains a new top-level key:

```json
{
  "generated_at": "...",
  "features": [...],
  "cycles": [...],
  "orphans": [...],
  "global_invariants": ["features/i_policy_security.md", "features/i_arch_coding_standards.md"]
}
```

Global invariants are NOT stored as edges in the graph (would create visual noise — every feature connected to every global invariant). Instead they're a separate overlay. Tools that need the full constraint set (build preflight, audit) combine explicit prerequisites + global invariants.

Scoped invariants work identically to existing anchors — they appear as normal prerequisite edges in the graph.

### 3.3 Cascade on Update

- **Global invariant updated:** ALL non-anchor features reset to `[TODO]`. Severe but correct — a security policy change genuinely requires re-validation of everything.
- **Scoped invariant updated:** Only features with direct/transitive prerequisite links reset. Same as existing anchor cascade.

---

## 4. The `/pl-invariant` Command

New skill file: `.claude/commands/pl-invariant.md`
Feature spec: `features/pl_invariant.md`
Mode: PM (invariants are constraints, PM's domain) for write operations; any mode for read operations.

### 4.1 Subcommands

| Subcommand | Mode | Description |
|------------|------|-------------|
| `add <repo-url> [file-path]` | PM | Import an invariant from an external git repo |
| `add-figma <figma-url> <anchor-file>` | PM | Upgrade an existing design anchor to a Figma-sourced invariant |
| `sync [file-name \| --all]` | PM | Pull latest version from source (git or Figma) |
| `check-updates` | Any | Check all invariants for new versions (fast, no clone — uses `git ls-remote`) |
| `check-conflicts` | Any | Detect invariant-to-invariant and invariant-to-anchor conflicts |
| `check-feature <feature> [--all]` | Any | Check if feature(s) adhere to applicable invariants |
| `validate` | Any | Validate all invariant files have correct format and required metadata |
| `list` | Any | List all active invariants with version, scope, and sync status |
| `remove <file-name>` | PM | Remove an invariant from the project (deletes file, updates prerequisite links) |

### 4.2 `add` Workflow (Git-Sourced)

1. Shallow-clone the external repo (depth 1)
2. Locate the target file in the repo's `features/` directory (or specified path)
3. Validate format: has `## Purpose`, has `## * Invariants`, has `> Version:` metadata
4. If `> Scope:` is missing, prompt PM to choose global or scoped
5. Inject/verify invariant metadata (`> Invariant: true`, `> Source:`, `> Source-Path:`, `> Source-SHA:`, `> Synced-At:`)
6. Copy to `features/` with `i_` prefix prepended to the filename
7. Commit with tag: `invariant-add(features/i_policy_gdpr.md): v2.1.0 from <repo>`
8. Run `scan.sh` to integrate into dependency graph and trigger cascade if global
9. Clean up shallow clone

### 4.3 `add-figma` Workflow (Figma-Sourced Design Invariant)

**Requires Figma MCP.** No fallback — if MCP is unavailable, guide setup and stop.

1. Verify Figma MCP is available. If not, provide setup instructions and stop.
2. Fetch Figma file metadata via MCP (version ID, last modified, design variables)
3. Extract annotations via `get_design_context` — behavioral notes, interaction descriptions, edge cases
4. Create a thin pointer file `features/i_design_<name>.md` with:
   - Invariant metadata (`> Invariant: true`, `> Source: figma`, `> Figma-URL:`, `> Version: <figma_version_id>`, `> Synced-At: <now>`)
   - Purpose section (PM provides)
   - Figma Source section (boilerplate)
   - Annotations section (extracted behavioral notes, clearly marked as advisory)
5. If an existing `design_*.md` anchor is being upgraded:
   - **Migration step:** Update all `> Prerequisite:` and `> **Design Anchor:**` references in feature files
   - Delete the old `design_*.md` file (its content was local — the Figma doc is now the authority)
6. Commit with tag: `invariant-add(features/i_design_<name>.md): Figma-sourced`
7. Run `scan.sh` to cascade-reset dependent features

### 4.4 `sync` Workflow

**Git-sourced:**
1. Shallow-clone the source repo
2. Read the updated file, compare version and content against local
3. If unchanged: report "already current"
4. If changed: show diff, report version delta (MAJOR = breaking, flag prominently)
5. Present cascade impact (list features that will reset to TODO)
6. On confirmation: overwrite local file, update embedded metadata (Version, Source-SHA, Synced-At)
7. Commit with tag: `invariant-sync(features/i_policy_gdpr.md): v2.0.0 -> v2.1.0`
8. Run `scan.sh` to trigger cascade

**Figma-sourced:**
1. Fetch current Figma file metadata via MCP
2. Compare `figma_version_id` against stored `> Version:`
3. If unchanged: report "already current"
4. If changed:
   - Update `> Version:` and `> Synced-At:` in the pointer file
   - Re-extract annotations, update Annotations section (new/changed/removed notes)
   - Flag affected features' `brief.json` as potentially stale
5. Commit and cascade same as git-sourced

### 4.5 `check-updates` Workflow (Fast, No Clone)

For each `i_*` file in `features/` (reads `> Source:` and `> Source-SHA:` metadata):
- **Git-sourced:** `git ls-remote <source-url> HEAD` to get remote HEAD SHA. Compare against `source_sha`. If different: "Update may be available for `i_policy_gdpr.md` (local SHA: abc123, remote HEAD: def456)"
- **Figma-sourced:** If Figma MCP available, fetch file version ID. Compare against stored version. If different: "Figma design updated for `i_design_visual_standards.md`"
- Report summary: N invariants checked, M have updates available

### 4.6 `check-conflicts` Workflow

Agent-driven semantic analysis (invariant statements are natural language):

1. Group all invariants by type prefix
2. Within each type group, extract invariant statements (bullets under `## * Invariants`)
3. Also extract local anchors of matching types
4. Present grouped statements to the agent for conflict analysis:
   - **Invariant-to-invariant:** Two invariants of the same type making contradictory claims
   - **Invariant-to-anchor:** A local anchor's constraints contradicting an imported invariant
5. Report conflicts with severity and specific contradicting statements

### 4.7 `check-feature` Workflow (Feature Adherence)

For a given feature (or `--all` features):
1. Determine applicable invariants:
   - All global invariants
   - All scoped invariants in the feature's transitive prerequisite chain
2. For each applicable invariant:
   - **FORBIDDEN patterns:** Grep the feature's code files for violations
   - **Invariant statements:** Check if the feature's spec and implementation address each constraint
   - **Token Map validation** (design invariants): Verify Token Map values match invariant's token table
3. Report: per-feature, per-invariant, per-constraint compliance status with file:line evidence

### 4.8 `validate` Workflow

Check all `i_*` files for:
1. Required metadata fields present (`> Format-Version:`, `> Invariant: true`, `> Version:`, `> Source:`, `> Scope:`)
2. Format version compatibility (warn if file's format version exceeds Purlin's supported version)
3. Required sections per type: `## Purpose` + `## * Invariants` for arch/policy/ops/design; `## Purpose` + `## User Stories` + `## Success Criteria` for prodbrief
4. Type prefix is valid (after stripping `i_`)
5. Report issues with specific file and field

---

## 5. Enforcement Integration

### 5.1 Classification: What Gets Checked Where

| Check Type | Example | Automated? | Where Enforced | Blocks? |
|------------|---------|-----------|----------------|---------|
| FORBIDDEN patterns (grepable) | `eval()`, hardcoded hex colors | Yes — grep | `/pl-build` Step 0, `/pl-spec-code-audit` Phase 1 | Yes (build preflight) |
| Structural invariants | File naming, directory org, required config | Yes — glob/stat | `/pl-spec-code-audit` Phase 1 | No (audit finding) |
| Behavioral invariants | "API responses include correlation ID" | No — agent judgment | `/pl-spec-code-audit` Phase 1 (coverage check) | No (audit finding) |
| Process invariants | "PII encrypted at rest" | No — agent/QA judgment | `/pl-spec-code-audit` Phase 2, QA verification | No (audit finding) |
| Design token compliance | Token Map vs invariant tokens | Yes — comparison | `/pl-build` Step 0 (warning), `/pl-design-audit` | Warn only (build) |

**Key principle:** Only FORBIDDEN patterns are automated gatekeepers that block builds. Everything else is surfaced as findings for human judgment. This prevents invariants from being "super annoying" while ensuring adherence.

### 5.2 `/pl-build` Step 0 — Preflight (Primary Fast Gate)

**Current behavior:** Reads spec, checks prerequisites, surfaces anchor constraints.

**Extended behavior:**
1. Collect applicable invariants for the target feature:
   - All global invariants (from `dependency_graph.json` -> `global_invariants`)
   - All scoped invariants from transitive prerequisites
2. Read each invariant's FORBIDDEN patterns
3. **FORBIDDEN pre-scan:** Grep the feature's existing code files for violations. Scoped to feature files only (fast — seconds, not minutes)
4. If violations found: **block with actionable message**
   ```
   INVARIANT VIOLATION — build blocked
   i_policy_security.md (INV-3): No eval() in user-facing code
   Pattern: eval\(
   Found: tools/auth/handler.py:42
   Fix: Replace eval() with ast.literal_eval() or json.loads()
   ```
5. Surface behavioral invariant statements as **reminders** (not blockers):
   ```
   Applicable invariants (for awareness during implementation):
   - i_arch_api_standards.md: All endpoints must return structured error responses (INV-2)
   - i_policy_gdpr.md: User data access must be logged (INV-5)
   ```
6. For Figma design invariants:
   - Check if feature's brief.json version matches the invariant pointer's version. Warn if stale.
   - During Step 3 (verify locally): compare implemented CSS/styles against Token Map values.
   - **Colors are strict:** hardcoded hex values that should be design tokens are flagged as violations (same weight as FORBIDDEN patterns).
   - Layout/spacing mismatches are warned but don't block.

### 5.3 `/pl-spec` — Spec Authoring (Advisory)

When PM finishes writing/updating a spec, before commit:
1. Identify applicable global invariants and show reminder:
   ```
   This feature is subject to 3 global invariants:
   - i_policy_security.md (v2.1.0)
   - i_arch_coding_standards.md (v1.0.0)
   - i_ops_monitoring.md (v1.2.0)
   ```
2. For scoped invariants: suggest relevant ones based on domain overlap:
   ```
   Consider adding prerequisite:
   - features/i_design_accessibility.md (this feature has a Visual Specification)
   ```
3. Advisory only — does not block spec commit. The audit catches gaps later.

### 5.4 `/pl-spec-code-audit` — Deep Validation (Thorough)

**Extended Phase 0.3 (Collect Anchor Constraints):**
- Already collects FORBIDDEN patterns and invariant statements from transitive ancestors
- Extension: automatically include ALL global invariants in the constraint payload, regardless of prerequisite links
- Extract invariant source metadata for provenance in the report

**Extended Phase 1 (Subagents):**
- FORBIDDEN scan: already greps source files — now includes invariant FORBIDDEN patterns
- Invariant coverage: already checks if each invariant statement has scenario/code coverage — now includes invariant constraints
- No new subagent logic needed; the constraint payload is just larger

**New Dimension 14 — Invariant Source Compliance:**

| # | Dimension | Description |
|---|-----------|-------------|
| 14 | Invariant source compliance | For features governed by invariants: (a) no FORBIDDEN pattern violations, (b) behavioral invariants have scenario/code coverage, (c) design Token Maps validate against invariant token table, (d) invariant version is not stale. Violations: HIGH for FORBIDDEN, MEDIUM for coverage gaps, LOW for staleness. |

**Phase 2 synthesis** includes invariant violations in the gap table with "Invariant Source" column showing `i_policy_security INV-3.2`.

### 5.5 Companion File Integration

When Engineer writes code implementing a feature governed by invariants, the companion file covenant applies as normal. Additionally:
- If code addresses a specific invariant constraint, the companion entry SHOULD reference it: `[IMPL] Implemented correlation ID header per i_arch_api_standards.md INV-2`
- If code deviates from an invariant: `[DEVIATION]` entries reference the invariant — but since invariants are immutable, this escalates as a harder conflict than regular anchor deviations. The deviation is surfaced to PM as "invariant conflict" rather than "spec deviation."

---

## 6. Design Invariant Workflow

### 6.1 `/pl-design-ingest` Is Eliminated

`/pl-design-ingest` is retired. Its responsibilities are split:

| Old responsibility | New home |
|-------------------|----------|
| Figma connection & setup | `/pl-invariant add-figma` |
| Annotation extraction | `/pl-invariant add-figma` + `sync` (stored as advisory in pointer file) |
| brief.json generation | `/pl-spec` (during Visual Spec authoring for features referencing a Figma invariant) |
| Token Map generation | `/pl-spec` (PM maps tokens when writing the Visual Specification) |
| Visual acceptance checklists | `/pl-spec` (PM authors checklists from brief.json data) |
| Design Anchor declaration | Standard `> Prerequisite:` to `i_design_*.md` invariant |
| Local file ingestion (images, PDFs) | No special command — PM adds files to `features/design/` and references them in local `design_*.md` anchors |
| Web URL references | Same — PM adds references to local `design_*.md` anchors |
| Staleness detection | `/pl-invariant sync` (version check) + scan (brief vs pointer version) |
| Dev Resources linking | Dropped (low-value, Figma-specific ceremony) |

### 6.2 Three-Tier Design Model

| Tier | Source | Local File | Invariant? | Assets? |
|------|--------|-----------|-----------|---------|
| **Git markdown** | External git repo | `i_design_*.md` (full content) | Yes — immutable | No — markdown only |
| **Figma** | Figma document | `i_design_*.md` (thin pointer) | Yes — immutable | No — Figma is authority, `brief.json` caches |
| **Local** | Project team | `design_*.md` (full content) | No — regular anchor | Yes — images, PDFs, web URLs, HTML |

If the design authority is external (git or Figma), it's an invariant. If it uses local assets or is locally authored, it's a regular anchor.

### 6.3 End-to-End Figma Flow

**Step 1: Add Figma invariant** (one-time setup, PM mode)
```
/pl-invariant add-figma <figma-url>
```
- Creates `i_design_<name>.md` pointer file
- Extracts annotations as advisory notes
- Requires Figma MCP — no fallback

**Step 2: Write feature spec with Visual Specification** (PM mode, `/pl-spec`)

When PM authors a feature that references a Figma invariant:
1. PM declares `> Prerequisite: features/i_design_<name>.md`
2. PM specifies which Figma frames/nodes are relevant to this feature's screens
3. `/pl-spec` reads the Figma frames via MCP:
   - Extracts design variables (colors, spacing, typography)
   - Extracts component tree, auto-layout, dimensions
   - Generates `brief.json` at `features/design/<feature_stem>/brief.json`
4. PM reads annotations from the invariant pointer (advisory behavioral notes)
5. PM writes the Visual Specification:
   - Token Map: maps Figma tokens to project tokens (identity tokens auto-detected)
   - Visual acceptance checklists: measurable criteria derived from brief.json
   - Gherkin scenarios informed by (but not dictated by) annotations
6. Commit spec + brief.json together

**Step 3: Build** (Engineer mode, `/pl-build`)

Engineer reads the feature spec + brief.json:
1. **Step 0 preflight:** Compare Token Map against brief.json tokens. Warn if Token Map is stale (brief version newer than spec's Processed date).
2. **Step 2 implementation:** Engineer uses Token Map + brief.json for layout, colors, spacing. No Figma MCP needed.
3. **Step 3 verification:** For features with Visual Specification, spot-check compares implemented CSS/styles against Token Map values. **Colors are strict** — hardcoded hex values that should be tokens are flagged. Layout/spacing are warned.

**Step 4: Figma updates** (ongoing, PM mode)
```
/pl-invariant sync i_design_<name>.md
```
- Bumps pointer version, re-extracts annotations
- Flags all dependent features' briefs as potentially stale
- Cascades features to `[TODO]`
- PM refreshes briefs during next `/pl-spec` touch

### 6.4 Annotation Model

Figma annotations are behavioral notes — empty states, loading behavior, interactions, edge cases. They are extracted from Figma's `get_design_context` API.

**Storage:** In the invariant pointer file's `## Annotations` section. Updated on `add-figma` and `sync`.

**Authority level: Advisory, not binding.** Annotations are like user stories in a `prodbrief_` invariant. They inform PM's spec writing but do not dictate it. PM may:
- Adopt an annotation as-is into a QA scenario
- Modify it to fit the project's requirements
- Discard it entirely if outdated or irrelevant

**Why not binding:** Designers often leave annotations that are aspirational, outdated, or refer to components outside the current scope. PM needs judgment authority.

**How PM uses them during `/pl-spec`:**
1. Read the invariant pointer's Annotations section
2. For each relevant annotation, decide: adopt, adapt, or skip
3. Adopted annotations become Gherkin scenarios or acceptance criteria in the feature spec
4. No automatic scenario generation — PM authors explicitly

### 6.5 Design Enforcement Weight

Not all aspects of a Figma invariant are enforced equally:

| Aspect | Enforcement | Where | Rationale |
|--------|-------------|-------|-----------|
| **Colors / design tokens** | Strict — build warns, audit flags as HIGH | `/pl-build` Step 0+3, `/pl-spec-code-audit` | Objective, machine-verifiable. Figma variables map directly to CSS tokens. Hardcoded hex = FORBIDDEN. |
| **Typography** | Strict — build warns, audit flags as HIGH | `/pl-build` Step 3, `/pl-spec-code-audit` | Font families, weights, and sizes are measurable from brief.json. |
| **Spacing / layout** | Moderate — build warns, audit flags as MEDIUM | `/pl-build` Step 3, `/pl-spec-code-audit` | Measurable but may have legitimate variance (responsive, content-dependent). |
| **Annotations (behavioral)** | Advisory — informs spec only | `/pl-spec` (PM reads and decides) | Like prodbrief user stories. Not machine-checkable. |

### 6.6 Staleness and Conflict Detection

| When | What | How | Blocks? |
|------|------|-----|---------|
| `/pl-build` Step 0 | Brief version vs invariant pointer version | Local comparison | Warn only |
| `/pl-build` Step 3 | Implemented styles vs Token Map | CSS/style comparison | Warn (colors strict) |
| `/pl-design-audit` | Brief vs current Figma state | Figma MCP when available | No (PM audit) |
| `/pl-invariant check-feature` | Token Map consistency with brief | Local comparison | No (report) |
| `/pl-verify` (QA) | Triangulated: Figma vs Spec vs App | Figma MCP + Playwright | No (QA finding) |

### 6.7 Briefs Are Still Needed

Briefs (`features/design/<feature_stem>/brief.json`) are the per-feature structured cache:
- Created during `/pl-spec` when PM specifies Figma frames for a feature
- Read by Engineer during `/pl-build` (no Figma MCP needed)
- Staleness checked against invariant pointer version
- NOT invariants — mutable local caches, updated by PM

---

## 7. Reporting

### 7.1 Invariant Audit Toolbox Tool

New Purlin-level tool: `purlin.invariant_audit` in `tools/toolbox/purlin_tools.json`

**Report structure:**

```
INVARIANT AUDIT REPORT
======================================================================
Project: <name>   Scanned: <timestamp>
Invariants: <N> (global: <M>, scoped: <K>)
Features governed: <F>

INVARIANT STATUS
----------------------------------------------------------------------

 Invariant                          Source  Version  Scope   Sync
 ---------------------------------  ------  -------  ------  --------
 i_policy_security.md               git     v2.1.0   global  CURRENT
 i_arch_api_standards.md            git     v1.0.0   scoped  CURRENT
 i_design_visual_standards.md       figma   v456     scoped  STALE
 i_ops_monitoring.md                git     v1.2.0   global  CURRENT

FEATURE COMPLIANCE
----------------------------------------------------------------------

 Feature              Invariant                     Status     Issue
 ------------------   ----------------------------  ---------  ----------------------
 my_feature.md        i_policy_security.md (INV-3)  VIOLATION  eval() at tools/x.py:42
 dashboard.md         i_design_visual_standards.md  STALE      brief v123 != invariant v456
 settings.md          i_arch_api_standards.md       COMPLIANT  --
 auth.md              i_policy_security.md          COMPLIANT  --

VIOLATIONS (<N> total)
----------------------------------------------------------------------

V1. [HIGH] my_feature.md -- FORBIDDEN pattern violation
    Invariant: i_policy_security.md, INV-3
    Constraint: No eval() in user-facing code
    Evidence: tools/my_feature/handler.py:42 -- eval(user_input)
    Fix: Replace with ast.literal_eval() or json.loads()
    Owner: Engineer

V2. [MEDIUM] dashboard.md -- Design invariant stale
    Invariant: i_design_visual_standards.md
    Constraint: Token Map must reflect current Figma version
    Evidence: brief.json version v123, invariant synced to v456
    Fix: PM run /pl-invariant sync i_design_visual_standards.md
    Owner: PM
```

The tool's `agent_instructions` direct the agent to:
1. Run scan, read all `i_*` files from `features/`
2. Build transitive constraint map (global + scoped per feature)
3. For each feature: grep FORBIDDEN patterns, check token compliance, check brief versions
4. Produce the structured report with per-violation remediation and owner

### 7.2 `/pl-spec-code-audit` Integration

No new phase. Existing phases absorb invariants:
- **Phase 0.3:** Constraint collection auto-includes global invariants
- **Phase 1:** Subagents validate against the full constraint set (including invariant FORBIDDEN patterns and coverage)
- **Phase 2:** Gap table includes Dimension 14 (invariant source compliance) with evidence and severity
- **Phase 3:** Remediation suggests concrete fixes for invariant violations

---

## 8. Performance

### 8.1 What's Already Efficient
- **No manifest** — eliminated, zero overhead
- **Lazy loading** — constraint data not loaded at startup, only on first use
- **Immutable files** — cache hit rate approaches 100% (files only change via explicit sync)
- **Scan reuses existing iteration** — no extra pass for invariant files
- **Early-termination regex** — metadata extraction stops at first match per field

### 8.2 Constraint Cache

**File:** `.purlin/cache/invariant_constraints.json` (gitignored)

```json
{
  "generated_at": "2026-03-28T14:30:00Z",
  "source_hashes": {
    "i_policy_security.md": "sha256:abc123"
  },
  "global": ["features/i_policy_security.md"],
  "constraints": {
    "features/i_policy_security.md": {
      "forbidden": [
        {"id": "INV-3", "pattern": "eval\\(", "scope": "**/*.{py,js}", "description": "No eval() in user-facing code"}
      ],
      "invariants": [
        {"id": "INV-1", "text": "All user input must be sanitized", "type": "behavioral"},
        {"id": "INV-5", "text": "User data access must be logged", "type": "behavioral"}
      ]
    }
  }
}
```

**Invalidation:** SHA-256 comparison. The scan's integrity check and the constraint cache share the same hashes — computed once, used for both tamper detection and cache invalidation.

### 8.3 Hotspots and Mitigations

**P1: FORBIDDEN grep amplification in `/pl-build` Step 0**

Problem: 5 global invariants × 3-5 FORBIDDEN patterns each = 15-25 separate grep passes per build.

Fix: **Compile all FORBIDDEN patterns into a single combined regex per file-scope glob.** Group patterns by their `Scope:` field (e.g., all `**/*.py` patterns become one regex). Run ONE grep pass per scope group. Typical result: 2-3 grep passes instead of 15-25.

**P2: Build Step 3 — CSS/style comparison scope**

Problem: Comparing implemented styles against Token Map could scan the entire codebase for every token.

Fix: **Scope to files changed in this build session only.** Use `git diff --name-only` against the pre-build state. Limits comparison to typically 3-10 files.

**P3: Global invariant cascade on minor version bumps**

Problem: PATCH bump (v2.1.0 → v2.1.1) on a global invariant resets ALL 50+ features to `[TODO]`.

Fix: **Cascade scope follows semver:**
- MAJOR bump → full cascade (all dependents reset)
- MINOR bump → cascade with warning
- PATCH bump → **no cascade** — log the update, surface in scan as informational. Rationale: PATCH = corrections/clarifications, not new constraints.

**P4: `/pl-spec-code-audit` subagent payload bloat**

Problem: Global invariants auto-injected into every subagent = 100+ extra statements per subagent.

Fix: **Split by checkability:**
- FORBIDDEN patterns (grep-able) → ALL subagents
- Behavioral statements → ONLY the feature-specific subagent
- ~80% payload reduction for non-primary subagents.

**P5: `check-feature --all` — combinatorial explosion**

Problem: 73 features × 5 globals × 20 patterns = 7,300 grep operations.

Fix: **Invert the check.** Instead of per-feature-per-pattern, grep each FORBIDDEN pattern ONCE across all files, then attribute `file:line` matches to features via the dependency graph. O(patterns) instead of O(features × patterns).

**P6: Figma MCP latency during `/pl-spec`**

Problem: Figma MCP calls take seconds each. Multiple screens = slow spec authoring.

Fix: **Batch extraction.** Extract all frames for a feature in one MCP session. Generate brief.json once at the end, not incrementally.

**P7: `check-conflicts` scales with invariant count**

Problem: Semantic analysis reads all invariant statements. 20 invariants = large context.

Fix: Already mitigated by type-prefix grouping. Additional: **cache conflict results** keyed by the set of invariant content hashes. Valid until next sync.

---

## 9. Files to Modify

### Existing Files

| File | Change |
|------|--------|
| `tools/cdd/scan.py` | Add `_is_invariant_node()`, extend `_ANCHOR_PREFIXES` with `ops_`, `prodbrief_` and `i_` variants, add `scan_invariant_integrity()`, skip invariants in companion debt, add invariant section to scan output |
| `tools/cdd/graph.py` | Parse `> Scope:` metadata, emit `global_invariants` key in JSON, add `invariant: true` flag to parsed features |
| `instructions/references/file_classification.md` | Add INVARIANT classification (no mode can write `i_*` files) |
| `instructions/references/knowledge_colocation.md` | Extend Anchor Node Taxonomy table with `ops_*`, `prodbrief_*`, and `i_` invariant convention |
| `instructions/references/spec_authoring_guide.md` | Add invariant section (Section 3.5) documenting invariant anchor types and linking |
| `.claude/commands/pl-build.md` | Extend Step 0 with global invariant loading and FORBIDDEN pre-scan |
| `.claude/commands/pl-spec.md` | Add invariant awareness advisory at spec commit time |
| `.claude/commands/pl-spec-code-audit.md` | Extend Phase 0.3 to auto-include global invariants, add Dimension 14 |
| `.claude/commands/pl-anchor.md` | Recognize `i_*` prefix and enforce immutability, recognize `ops_*` and `prodbrief_*` |
| `.claude/commands/pl-design-ingest.md` | **RETIRE** — tombstone the skill, redirect to `/pl-invariant add-figma` and `/pl-spec` |
| `.claude/commands/pl-spec.md` | Add Figma brief.json generation + Token Map authoring when feature references a Figma invariant |
| `features/pl_design_ingest.md` | **RETIRE** — tombstone the feature spec |
| `.claude/commands/pl-design-audit.md` | Add invariant source sync status to report |
| `tools/collab/extract_whats_different.py` | Add `i_*` detection in `categorize_file()` |
| `tools/test_support/harness_runner.py` | Add `i_` variants to anchor skip tuple |
| `tools/smoke/smoke.py` | Add `i_` prefix to anchor detection |
| `tools/toolbox/purlin_tools.json` | Add `purlin.invariant_audit` tool |
| `instructions/PURLIN_BASE.md` | Add invariant immutability to mode guard language, add `/pl-invariant` to skill list |
| `.purlin/PURLIN_OVERRIDES.md` | Add invariant-related PM/Engineer override notes |

### New Files

| File | Purpose |
|------|---------|
| `.claude/commands/pl-invariant.md` | Skill file for `/pl-invariant` command |
| `features/pl_invariant.md` | Feature spec for the invariant system |
| `tools/cdd/invariant.py` | Python module for invariant operations (validate, hash, metadata extraction) |
| `tools/cdd/test_invariant.py` | Unit tests for invariant module |
| `tools/feature_templates/_invariant.md` | Template for invariant files (based on anchor template + invariant metadata) |
| `instructions/references/invariant_format.md` | Canonical invariant format reference (for external authors) |
| `instructions/references/invariant_model.md` | Reference doc for the invariant model (linking, scope, enforcement) |

---

## 10. Implementation Phases

### Phase 1: Foundation — Data Model & Detection
1. Create `features/pl_invariant.md` feature spec
2. Create `instructions/references/invariant_format.md` (canonical format)
3. Create `instructions/references/invariant_model.md` (model reference)
4. Create `tools/feature_templates/_invariant.md` (template)
5. Update `instructions/references/file_classification.md` (INVARIANT classification)
6. Update `instructions/references/knowledge_colocation.md` (extended taxonomy)
7. Update `instructions/references/spec_authoring_guide.md` (invariant section)

### Phase 2: Scanner & Graph Integration
8. Update `tools/cdd/scan.py` — invariant detection, integrity check, extended anchor prefixes
9. Update `tools/cdd/graph.py` — `global_invariants` key, `> Scope:` parsing
10. Create `tools/cdd/invariant.py` — core operations module
11. Create `tools/cdd/test_invariant.py` — unit tests
12. Update `tools/collab/extract_whats_different.py`, `tools/test_support/harness_runner.py`, `tools/smoke/smoke.py` — `i_` prefix handling

### Phase 3: Command & Enforcement
13. Create `.claude/commands/pl-invariant.md` — full skill with all subcommands
14. Update `.claude/commands/pl-build.md` — Step 0 invariant preflight
15. Update `.claude/commands/pl-spec.md` — invariant advisory
16. Update `.claude/commands/pl-anchor.md` — `ops_*`, `prodbrief_*` types, `i_*` immutability
17. Update `instructions/PURLIN_BASE.md` — mode guard, skill list

### Phase 4: Figma & Design Integration
18. Update `.claude/commands/pl-design-ingest.md` — handle `i_design_*` anchors
19. Update `.claude/commands/pl-design-audit.md` — invariant sync status
20. Implement `add-figma` and Figma sync in `/pl-invariant`

### Phase 5: Audit & Reporting
21. Update `.claude/commands/pl-spec-code-audit.md` — Dimension 14, global invariant injection
22. Add `purlin.invariant_audit` to `tools/toolbox/purlin_tools.json`

### Phase 6: Overrides & Polish
23. Update `.purlin/PURLIN_OVERRIDES.md` — invariant-specific notes per mode
24. Update `purlin-config-sample/` if applicable (sample sync prompt)

---

## 11. Verification Plan

### Unit Tests (`tools/cdd/test_invariant.py`)
- Invariant file detection (`_is_invariant_node()` with all type prefixes)
- Metadata extraction (all required fields including Format-Version)
- Content hash computation and comparison
- Format validation (missing fields, missing sections, type-specific section checks)
- Prodbrief section detection (User Stories + Success Criteria instead of Invariants)

### Integration Tests
- Scan correctly identifies invariant files alongside regular anchors
- Graph includes `global_invariants` key
- Cascade resets work for both global and scoped invariants
- Companion debt scan skips invariant files
- `extract_whats_different` categorizes invariants correctly

### Manual Verification
- `/pl-invariant add` from a test git repo
- `/pl-invariant add-figma` upgrade path with prerequisite link migration
- `/pl-invariant sync` with version bump and cascade
- `/pl-invariant check-conflicts` between two invariants with contradictory statements
- `/pl-invariant check-feature <feature>` with a FORBIDDEN pattern violation
- `/pl-build` blocking on FORBIDDEN pattern from an invariant
- `/pl-spec` showing invariant advisory
- Mode guard blocking write to `i_*` file
- `purlin.invariant_audit` toolbox tool producing full report
