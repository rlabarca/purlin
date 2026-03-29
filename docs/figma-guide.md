# Figma Integration Guide

Purlin turns Figma designs into verified implementations. The PM reads your Figma file, writes a spec with a Token Map, the Engineer builds from it, and QA verifies the result against the original design. When the Figma file changes, Purlin tells you what's stale.

For the full design workflow including local anchors and non-Figma assets, see the [Design Guide](design-guide.md).

---

## Setup

Figma integration requires the Figma MCP server. Add it once:

```bash
claude mcp add figma -- npx figma-developer-mcp --stdio
```

Restart your session after adding. PM mode is the primary interface for Figma — it has full read access via MCP and can write to Figma with your approval.

Without Figma MCP, PM mode falls back to manual: you paste a Figma URL and describe the design yourself. Everything else still works — Token Maps, visual specs, verification — you just lose the automated extraction.

---

## The Workflow

### 1. Import the Figma Design (One-Time)

For org-wide or shared design systems, create a design invariant:

```
purlin:invariant add-figma https://www.figma.com/design/ABC123/Design-System
```

This creates `features/i_design_<name>.md` — an immutable pointer to the Figma document. Purlin extracts annotations and metadata via MCP. If the design applies to all features, set its scope to global.

Skip this step if you're referencing Figma URLs directly in individual feature specs rather than using a shared design system.

### 2. PM Writes the Spec from Figma

```
purlin:spec dashboard_feature
```

When PM asks about visual design, provide the Figma URL for the relevant screen. PM reads the design via MCP — extracting components, colors, fonts, spacing, and layout — then writes a **Visual Specification** section in the feature spec:

```markdown
## Visual Specification

> **Design Anchor:** features/design_visual_standards.md

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

**The Token Map** is the critical piece. It maps Figma's design tokens to your project's CSS variables. This is what prevents hardcoded hex values in code.

### 3. PM Generates a Brief (Optional, Recommended)

When Figma MCP is available, PM also generates `features/_design/<feature>/brief.json` — a machine-readable cache of the design data:

```json
{
  "figma_url": "https://figma.com/file/...",
  "figma_version_id": "v123",
  "screens": {
    "Dashboard Layout": {
      "node_id": "123:456",
      "dimensions": {"width": 1440, "height": 900},
      "components": [
        {"name": "Card", "width": 320, "height": 200, "gap": 24}
      ]
    }
  },
  "tokens": {
    "surface": "#162531",
    "primary": "#38BDF8"
  }
}
```

Engineers read the brief locally instead of hitting Figma MCP during implementation. It's faster and works offline.

### 4. Engineer Builds from the Spec

```
purlin:build dashboard_feature
```

Engineer reads the Token Map and brief, then implements using token references:

```css
/* Good — uses tokens from the Token Map */
.dashboard { background: var(--purlin-surface); }

/* Bad — hardcoded hex bypasses the design system */
.dashboard { background: #162531; }
```

The build preflight checks that Token Maps are valid and briefs are current before implementation starts.

### 5. QA Verifies Against Figma

```
purlin:web-test dashboard_feature
```

QA performs **three-source triangulation** — comparing what Figma says, what the spec says, and what the app actually renders:

| Figma | Spec | App | Verdict |
|-------|------|-----|---------|
| Matches | Matches | Matches | **PASS** |
| Changed | Not updated | Matches old design | **STALE** — PM syncs invariant and updates spec |
| Matches | Matches | Different | **BUG** — Engineer fix needed |

QA reads Figma via MCP, reads the spec's Token Map and checklist, and uses Playwright to inspect the running app's computed styles and layout.

### 6. PM Audits Design Health

```
purlin:design-audit
```

This scans all features with visual specs and reports:
- **Staleness** — Has the Figma file changed since the spec was written?
- **Brief status** — Is the cached brief.json still current?
- **Token conflicts** — Do Token Map values contradict the design anchor?
- **Invariant sync** — Are Figma-sourced invariants up to date?

---

## Design Invariants (Org-Level Design Systems)

If your Figma file represents an organization-wide design system (not just one feature's mockup), make it an invariant:

```
purlin:invariant add-figma https://figma.com/file/abc123/Design-System
```

This creates `features/i_design_system.md` — an immutable pointer to the Figma document. With `> Scope: global`, it applies to every feature automatically.

When the design system updates in Figma:

```
purlin:invariant sync i_design_system.md
```

Major version changes cascade: dependent features reset to `[TODO]` and engineers re-verify against the new tokens. See the [Invariants Guide](invariants-guide.md) for enforcement details and the [Design Guide](design-guide.md) for the full design workflow.

---

## Design Anchors vs Invariants

| | Design Anchor | Design Invariant |
|---|---|---|
| **File** | `design_*.md` | `i_design_*.md` |
| **Editable locally?** | Yes (PM mode) | No — sync from source only |
| **Use when** | Project-specific design decisions | Org-wide design system from Figma |
| **Example** | Your app's color palette choices | Company brand guidelines |

Most projects have one design anchor (your local decisions) and optionally one design invariant (the org's system).

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

## Who Does What

| Role | Figma access | Primary actions |
|------|-------------|----------------|
| **PM** | Full read + write (with approval) | Create Token Maps, generate briefs, sync invariants, audit design health |
| **Engineer** | Read-only (brief first, MCP fallback) | Implement from Token Map and brief; no direct Figma changes |
| **QA** | Read-only (for verification) | Triangulated verification via `purlin:web-test` |

---

## Tips

- **Always use token references, never hardcoded values.** The Token Map exists to enforce this. `var(--purlin-accent)` not `#38BDF8`.
- **Generate briefs when you can.** Engineers work faster with a local `brief.json` than waiting for Figma MCP calls.
- **Run `purlin:design-audit` before releases.** It catches stale specs from Figma updates you might have missed.
- **Start with a design anchor, upgrade to invariant later.** You can promote a `design_*.md` anchor to `i_design_*.md` invariant with `purlin:invariant add-figma <url> <existing-anchor>`.
