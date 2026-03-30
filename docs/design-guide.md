# Design Guide

How Purlin manages design artifacts — from local anchors to Figma invariants — across all three modes.

---

## The Three-Tier Design Model

Purlin supports three ways to bring design context into your project. Each tier has different ownership, mutability, and enforcement rules.

| Tier | Source | Local File | Editable? | How to Set Up |
|------|--------|-----------|-----------|---------------|
| **Local anchor** | Your project team | `design_*.md` | Yes (PM mode) | `purlin:anchor design_<name>` |
| **Figma invariant** | Figma document | `i_design_*.md` (thin pointer) | No — sync only | `purlin:invariant add-figma <url>` |
| **Git invariant** | External git repo | `i_design_*.md` (full content) | No — sync only | `purlin:invariant add <repo-url>` |

Most projects start with a **local design anchor** for project-specific decisions (your color palette, spacing scale, typography). If your organization has a shared design system in Figma, add it as a **Figma invariant**. If design standards live in a separate git repo, use a **git invariant**.

You can use all three tiers in the same project. A feature might reference both a local anchor (your app's layout conventions) and a Figma invariant (the org's design system).

---

## Local Design Anchors

Design anchors are PM-owned files in `features/` that define shared visual standards. They apply to any feature that declares them as a prerequisite.

### Creating an Anchor

In PM mode:

```
purlin:anchor design_typography
```

PM mode walks you through defining the anchor's purpose and constraints. A typical design anchor includes token definitions, usage rules, and optionally FORBIDDEN patterns:

```markdown
# Design Anchor: Typography

## Purpose
Defines the project's type scale and font usage rules.

## Design Standards
- **Heading tokens:** `--font-heading-sm`, `--font-heading-md`, `--font-heading-lg`
- **Body tokens:** `--font-body`, `--font-body-sm`
- **Font family:** Inter for UI, JetBrains Mono for code

## FORBIDDEN Patterns
- No hardcoded font-family declarations outside the design system
- No px-based font sizes — use rem via tokens
```

### Linking Features to Anchors

Features reference anchors via prerequisites:

```markdown
> Prerequisite: features/design_typography.md
```

When the anchor changes, all dependent features are flagged for re-verification.

### When to Use Local Anchors vs Invariants

- **Local anchor** — Rules your team owns and can change. Your app's color palette, spacing decisions, component conventions.
- **Invariant** — Rules from outside your team that you must follow. The org's Figma design system, brand guidelines from a shared repo.

---

## Design Invariants

Invariants are externally-sourced design rules that can't be edited locally. They're enforced automatically — builds block on violations, audits flag drift.

### Importing from Figma

In PM mode (requires [Figma MCP setup](figma-guide.md#setup)):

```
purlin:invariant add-figma https://www.figma.com/design/ABC123/Design-System
```

This creates `features/_invariants/i_design_<name>.md` — a thin pointer file. The Figma document stays the authority. Purlin reads it via MCP when needed — extracting annotations and design variable definitions via `get_design_context` and `get_variable_defs`, and noting Code Connect availability when configured.

**Upgrading a local anchor:** If you already have a `design_*.md` anchor and want to promote it to a Figma invariant:

```
purlin:invariant add-figma https://www.figma.com/design/ABC123/Design-System design_visual_standards.md
```

This replaces the old anchor file, updates all prerequisite links in dependent features, and cascade-resets those features to `[TODO]`.

### Importing from a Git Repo

```
purlin:invariant add https://github.com/your-org/design-standards features/design_tokens.md
```

This clones the file into your project with an `i_` prefix and injects sync metadata.

### Keeping Invariants Current

When the source changes:

```
purlin:invariant sync i_design_system.md
```

Or check all invariants at once:

```
purlin:invariant check-updates
```

Version bumps trigger cascades: MAJOR resets all dependent features, MINOR resets with a warning, PATCH is informational only. See the [Invariants Guide](invariants-guide.md) for details.

---

## Visual Specifications

A Visual Specification is a section inside a feature spec that connects design intent to implementation. It contains a Token Map, an optional `brief.json`, and a verification checklist.

### How PM Creates a Visual Spec

During spec authoring:

```
purlin:spec dashboard-overview
```

When PM encounters a feature with design requirements, it:

1. **Reads the design source** — calls `get_design_context` (for structure, tokens, annotations) and `get_variable_defs` (for the full variable vocabulary) when Figma MCP is available, or reads local anchor files.
2. **Auto-seeds a Token Map** — Matches Figma variable names against project design tokens automatically. PM reviews and confirms the mappings. Without MCP, PM creates Token Maps manually.
3. **Generates `brief.json`** (optional, Figma only) — A machine-readable cache at `features/_design/<feature>/brief.json` containing dimensions, components, token values, and Code Connect mappings (when configured). Engineers read this instead of needing Figma access.
4. **Writes a verification checklist** — Measurable items that QA and web tests can check.

```markdown
## Visual Specification

> Prerequisite: features/i_design_system.md

### Screen: Dashboard Layout

- **Reference:** [Figma](https://figma.com/file/.../node-id=...)
- **Processed:** 2026-03-28
- **Token Map:**
  - `surface` -> `var(--purlin-surface)`
  - `on-surface` -> `var(--purlin-primary)`
  - `primary` -> `var(--purlin-accent)`
  - `spacing-md` -> `var(--purlin-spacing-md)`

- [ ] Dashboard grid shows 4 columns with equal spacing
- [ ] Card title uses `heading-lg` typography
- [ ] Accent color applied to primary action button
```

### How Engineer Uses the Visual Spec

During `purlin:build`, Engineer mode:

1. **Reads the Token Map** in the build preflight (Step 0) — loads token mappings and checks brief staleness.
2. **Implements using token references** — `var(--purlin-accent)` not `#38BDF8`. Hardcoded values are flagged by the design-audit and invariant enforcement.
3. **Runs `purlin:web-test`** (Step 3) — Playwright checks each checklist item against the running app's computed styles and layout.

### How QA Verifies Visual Work

During `purlin:web-test`, QA performs **three-source triangulation**:

| Figma (source) | Spec (contract) | App (output) | Verdict |
|------|------|-----|---------|
| Matches | Matches | Matches | **PASS** |
| Changed | Not updated | Matches old | **STALE** — PM re-syncs invariant, updates spec |
| Matches | Matches | Different | **BUG** — Engineer fix needed |

---

## Design Audit

`purlin:design-audit` is a PM-mode command that checks design health across the entire project. Run it before releases or during design reviews.

### What It Checks

| Check | What It Catches |
|-------|----------------|
| **Reference integrity** | Missing local files (CRITICAL), malformed URLs |
| **Staleness** | Local artifacts newer than the spec's Processed date |
| **Brief staleness** | `brief.json` out of sync with Figma version |
| **Invariant sync status** | Figma or git source has a newer version |
| **Anchor consistency** | Token Map values that don't match any anchor token, hardcoded hex values |
| **Invariant compliance** | FORBIDDEN pattern violations, color/typography enforcement |
| **Figma drift** (MCP) | Design variables renamed, added, or values changed since the spec was written (via `get_variable_defs`) |
| **Visual drift** (MCP) | Figma screenshot vs browser screenshot comparison (via `get_screenshot` + Playwright) |
| **Dev status** (MCP) | Figma frame status doesn't match spec metadata (via `get_metadata`) |

### Running It

```
purlin:design-audit
```

The output is a per-feature table followed by an invariant summary. Remediation routes to the right command:

| Issue | Fix With |
|-------|----------|
| Stale invariant | `purlin:invariant sync <file>` |
| Stale brief | `purlin:spec <feature>` (regenerates brief from Figma) |
| Stale local artifact | `purlin:spec <feature>` (re-processes the artifact) |
| Token Map inconsistency | `purlin:spec <feature>` (update Token Map) |
| FORBIDDEN violation | Engineer fixes the code |

---

## Which Skill Does What

| Skill | Mode | Design role |
|-------|------|-------------|
| `purlin:anchor design_*` | PM | Create or update local design anchors |
| `purlin:invariant add-figma` | PM | Import a Figma design as an immutable invariant |
| `purlin:invariant add` | PM | Import a design standard from a git repo |
| `purlin:invariant sync` | PM | Pull latest version from Figma or git source |
| `purlin:invariant check-updates` | Any | Check if design invariants have newer versions |
| `purlin:invariant check-feature` | Any | Check a feature's compliance with design constraints |
| `purlin:spec` | PM | Write the Visual Specification — auto-seed Token Map, generate brief, write checklist |
| `purlin:design-audit` | PM | Audit design health across the project |
| `purlin:build` | Engineer | Implement from Token Map; preflight checks invariant compliance |
| `purlin:web-test` | Engineer/QA | Verify visual checklist items via Playwright |
| `purlin:spec-code-audit` | Engineer | Dimension 14 checks invariant compliance in code |

---

## Enforcement Levels

Not all design properties are enforced equally:

| Aspect | Enforcement | What happens on violation |
|--------|------------|--------------------------|
| Colors / tokens | **Strict** | Hardcoded hex values flagged as FORBIDDEN |
| Typography | **Strict** | Wrong font/weight/size flagged in audit |
| Spacing / layout | **Moderate** | Warned but not blocked |
| Annotations | **Advisory** | PM reads during spec authoring, decides what to adopt |

---

## End-to-End Example

**Starting from scratch with Figma:**

1. **Set up Figma MCP** (one-time): `claude mcp add --transport http figma https://mcp.figma.com/mcp`
2. **Create a local design anchor** for project-specific rules: `purlin:anchor design_tokens`
3. **Import the org's Figma design system** as an invariant: `purlin:invariant add-figma <figma-url>`
4. **Write a feature spec** referencing the design: `purlin:spec user-settings` — PM reads Figma via MCP, writes Token Map and checklist
5. **Build the feature**: `purlin:build user-settings` — Engineer implements using token references
6. **Verify visual output**: `purlin:web-test user-settings` — Playwright checks against the checklist
7. **Audit design health** before release: `purlin:design-audit`

**Starting from scratch without Figma:**

1. **Create a local design anchor**: `purlin:anchor design_visual_standards`
2. **Add local assets** to `features/_design/<feature>/` (screenshots, PDFs)
3. **Write a feature spec**: `purlin:spec dashboard` — PM references the anchor and assets, writes Token Map and checklist
4. **Build and verify** as above
