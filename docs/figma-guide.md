# Figma Integration Guide

Purlin turns Figma designs into verified implementations. The PM reads your Figma file, writes a spec with a Token Map, the Engineer builds from it, and QA verifies the result against the original design. When the Figma file changes, Purlin tells you what's stale.

For the full design workflow including local anchors and non-Figma assets, see the [Design Guide](design-guide.md).

---

## Setup

Figma integration requires the Figma MCP server. Add it once:

```bash
claude mcp add --transport http figma https://mcp.figma.com/mcp
```

Restart your session, then run `/mcp`, select Figma, and complete OAuth in the browser.

PM mode is the primary interface for Figma — it has full read access via MCP and can write to Figma with your approval. The key MCP tools Purlin uses:

| Tool | Purpose |
|------|---------|
| `get_design_context` | Primary tool — returns design tokens as CSS variables, component data, layout hints, Code Connect snippets, annotations, and a screenshot |
| `get_metadata` | Version tracking — file version ID, last modified timestamp |
| `get_variable_defs` | Full design variable vocabulary — names, types, collections, resolved values |
| `get_screenshot` | Visual snapshot of a Figma frame — used for visual drift detection |
| `get_code_connect_map` | Code Connect component-to-code mappings (when configured) |

Without Figma MCP, PM mode falls back to manual: you paste a Figma URL and describe the design yourself. Everything else still works — Token Maps, visual specs, verification — you just lose the automated extraction and auto-seeding.

---

## The Workflow

### 1. Import the Figma Design (One-Time)

For org-wide or shared design systems, create a design invariant:

```
purlin:invariant add-figma https://www.figma.com/design/ABC123/Design-System
```

This creates `features/_invariants/i_design_<name>.md` — an immutable pointer to the Figma document. Purlin extracts annotations and design variable definitions via MCP (`get_design_context` + `get_variable_defs`). If Code Connect is configured, the pointer notes that component-to-code mappings are available. If the design applies to all features, set its scope to global.

Skip this step if you're referencing Figma URLs directly in individual feature specs rather than using a shared design system.

### 2. PM Writes the Spec from Figma

```
purlin:spec dashboard_feature
```

When PM asks about visual design, provide the Figma URL for the relevant screen. PM calls `get_design_context` (for structure, tokens, and annotations) and `get_variable_defs` (for the full variable vocabulary), then **auto-seeds a Token Map** by matching Figma variables against your project's design tokens. PM presents the auto-generated mappings for your review, then writes the **Visual Specification** section:

```markdown
## Visual Specification

> **Design Anchor:** features/_invariants/i_design_system.md

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

**The Token Map** is the critical piece. It maps Figma's design tokens to your project's CSS variables. This is what prevents hardcoded hex values in code. With Figma MCP, Token Maps are auto-seeded — PM reviews and confirms rather than writing from scratch.

### 3. PM Generates a Brief (Optional, Recommended)

When Figma MCP is available, PM also generates `features/_design/<feature>/brief.json` — a machine-readable cache built from `get_design_context`, `get_variable_defs`, and `get_metadata`:

```json
{
  "figma_url": "https://figma.com/file/...",
  "figma_version_id": "v123",
  "figma_last_modified": "2026-03-28T09:00:00Z",
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
  },
  "code_connect": {
    "Card": {
      "source_file": "src/components/Card.tsx",
      "props": {"variant": "outlined"}
    }
  }
}
```

The `code_connect` key is only present when Code Connect is configured in your Figma org. Engineers read the brief locally instead of hitting Figma MCP during implementation. It's faster and works offline.

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

QA reads Figma via `get_design_context` and `get_variable_defs`, reads the spec's Token Map and checklist, and uses Playwright to inspect the running app's computed styles and layout. For visual judgment items, `get_screenshot` provides a Figma frame snapshot for vision comparison.

### 6. PM Audits Design Health

```
purlin:design-audit
```

This scans all features with visual specs and reports:
- **Staleness** — Has the Figma file changed since the spec was written?
- **Brief status** — Is the cached brief.json still current?
- **Token conflicts** — Do Token Map values contradict the design anchor? (Uses `get_variable_defs` to detect renamed/added/removed variables)
- **Invariant sync** — Are Figma-sourced invariants up to date? (Uses `get_metadata` for version comparison)
- **Visual drift** — Does the running app match the Figma design? (Uses `get_screenshot` + Playwright screenshots when both MCP servers are available)

---

## Design Invariants (Org-Level Design Systems)

If your Figma file represents an organization-wide design system (not just one feature's mockup), make it an invariant:

```
purlin:invariant add-figma https://figma.com/file/abc123/Design-System
```

This creates `features/_invariants/i_design_system.md` — an immutable pointer to the Figma document. The pointer captures design variable definitions (from `get_variable_defs`), annotations (from `get_design_context`), and Code Connect availability. With `> Scope: global`, it applies to every feature automatically.

When the design system updates in Figma:

```
purlin:invariant sync i_design_system.md
```

Sync fetches the new version via `get_metadata`, re-extracts annotations and variable definitions, and updates the pointer. Major version changes cascade: dependent features reset to `[TODO]` and engineers re-verify against the new tokens. See the [Invariants Guide](invariants-guide.md) for enforcement details and the [Design Guide](design-guide.md) for the full design workflow.

---

## Design Anchors vs Invariants

| | Design Anchor | Design Invariant |
|---|---|---|
| **File** | `design_*.md` | `i_design_*.md` |
| **Source** | Local (PM-authored) | External (Figma or git) |
| **Editable locally?** | Yes (PM mode) | No — sync from source only |
| **Use when** | Project-specific decisions, no Figma | Figma-sourced design system |
| **Example** | App color palette, layout conventions | Company brand guidelines in Figma |

Figma designs are always invariants. If your design source is a Figma file, use `purlin:invariant add-figma` — don't create a local anchor. Design anchors are for project-specific decisions that aren't governed by an external Figma document.

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
| **PM** | Full read + write (with approval) | Auto-seed Token Maps (via `get_design_context` + `get_variable_defs`), generate briefs, sync invariants, audit design health |
| **Engineer** | Read-only (brief first, MCP fallback) | Implement from Token Map and brief; no direct Figma changes |
| **QA** | Read-only (for verification) | Triangulated verification via `purlin:web-test` |

---

## Tips

- **Always use token references, never hardcoded values.** The Token Map exists to enforce this. `var(--purlin-accent)` not `#38BDF8`.
- **Generate briefs when you can.** Engineers work faster with a local `brief.json` than waiting for Figma MCP calls.
- **Run `purlin:design-audit` before releases.** It catches stale specs from Figma updates you might have missed.
- **If you have Figma, start with an invariant.** Use `purlin:invariant add-figma <url>` — don't create a local anchor first. If you already have a local `design_*.md` anchor and want to replace it with a Figma source, use `purlin:invariant add-figma <url> <existing-anchor>` to upgrade and rewire all prerequisite links.
