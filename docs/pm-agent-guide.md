# PM Agent Guide

A practical guide for product managers using the PM agent in Purlin.

---

## 1. Overview

The PM agent is Purlin's design and specification agent. It helps product managers translate ideas, Figma designs, and live web pages into structured feature specs that the rest of the team (Architect, Builder, QA) can act on.

The PM agent:

- **Creates feature specs** with requirements, scenarios, and visual specifications.
- **Ingests Figma designs** by extracting design tokens, component structure, and annotations -- then generates a machine-readable brief for the Builder.
- **Ingests live web pages** as design references when Figma is not available.
- **Asks structured questions** to refine vague ideas into precise, testable specs.
- **Never writes code.** The PM owns specs and design artifacts. Code is the Builder's job.

By default, the PM agent uses Claude Sonnet 4.6 for fast, conversational iteration. You can change this in your project's [CDD Dashboard](status-grid-guide.md) configuration.

---

## 2. Getting Started

### Launching a PM Session

From your project root, run:

```bash
./pl-run-pm.sh
```

This launches a Claude Code session with the PM agent's instructions, tools, and permissions pre-loaded.

### First-Time Guided Onboarding

If your project has zero feature specs (a brand-new project), the PM enters **Guided Onboarding Mode** automatically. Instead of showing a wall of commands, it starts a conversation:

1. The PM greets you and explains that this is a new project.
2. It asks what you are building. A single sentence is enough -- the PM will probe for details.
3. It asks if you have Figma designs. If you do, paste a URL. If not, the PM works from your text description.
4. The PM creates your first feature spec and at least one [anchor node](critic-and-cdd-guide.md) (a shared design standard document).
5. It commits the files and tells you what to do next.

After onboarding, you will see something like:

```
Your first spec is ready at features/dashboard_overview.md.
Run ./pl-run-builder.sh in another terminal to start building from the spec.
Run ./pl-cdd-start.sh to see the status dashboard.
The Builder reads your spec and writes the code and tests to match it.
```

### Returning to an Existing Project

When features already exist, the PM shows a command table and any Critic action items waiting for your attention:

```
Purlin PM -- Ready
---

  Specification & Design
  ------
  /pl-spec <topic>           Shape a feature spec (guided)
  /pl-design-ingest          Ingest Figma design into visual spec
  /pl-design-audit           Audit design-spec consistency

  Navigation
  ------
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-status                 Check CDD status
  /pl-help                   Re-display this command list
```

---

## 3. Example 1: Working with Figma Designs

This walkthrough shows how to bring a Figma design into a Purlin feature spec.

### Step 1: Set Up Figma MCP (One-Time)

The PM checks for Figma MCP availability every time it starts. If the Figma connection is missing and either (a) the project has features with Visual Specification sections or (b) you mention a Figma URL, the PM walks you through setup:

1. Add the Figma MCP server:
   ```
   claude mcp add --transport http figma https://mcp.figma.com/mcp
   ```
2. Restart Claude to pick up the new MCP server.
3. Type `/mcp` in the terminal.
4. Select "figma" from the list to begin authentication.
5. Complete the authentication in the browser window that opens.
6. Return to the terminal -- Figma MCP tools are now available.

Once configured, this step is not needed again.

### Step 2: Run the Design Ingest Command

With a Figma URL in hand, run:

```
/pl-design-ingest https://www.figma.com/design/ABC123/My-App-Designs
```

The PM asks which feature file and screen this design belongs to. If the feature spec does not exist yet, the PM creates one.

### Step 3: What the PM Extracts

When Figma MCP is available, the PM calls `get_design_context` and extracts:

- **Component tree structure** -- layout hierarchy, auto-layout properties, nesting.
- **Design variables** -- colors, spacing values, typography scales.
- **Component variants and states** -- hover, active, disabled, error states.
- **Annotations** -- behavioral notes left by designers in the Figma file.
- **Dev status** -- whether the frame is marked "Ready for Dev" or "Completed" in Figma.

The PM presents behavioral annotations to you for review:

```
I found these behavioral notes in the Figma annotations:
- Clicking the header row sorts the table by that column
- Empty state shows an illustration with a CTA button
- Error banner auto-dismisses after 5 seconds

I'll use these to draft scenarios -- let me know if any are outdated.
```

### Step 4: Token Map Generation

The PM reads your project's design anchor files (`features/design_*.md`) to understand your token system. It then maps Figma variable names to your project's CSS custom properties:

```markdown
- **Token Map:**
  - `surface` -> `var(--project-bg)`
  - `primary` -> `var(--project-accent)`
  - `text/secondary` -> `var(--project-text-muted)`
  - `spacing/md` -> `var(--project-space-4)`
```

Identity mappings (where the Figma name already matches a project token) are auto-generated. The PM reports how many were automatic vs. how many needed manual resolution.

### Step 5: brief.json Generation

The PM generates `features/design/<feature_stem>/brief.json`, a machine-readable file containing:

- The source Figma URL and last-modified timestamp.
- Per-screen structured data: node IDs, dimensions, components, layout.
- Resolved design token values.
- Code Connect mappings (if present in the Figma file).
- Figma dev status and version ID.

This file is what the **Builder reads instead of needing Figma access**. The Builder never opens Figma -- it works entirely from the spec and brief.json.

### Step 6: What Gets Added to Your Feature Spec

The PM updates the feature file with a `## Visual Specification` section containing:

- A design anchor declaration linking to the relevant `design_*.md` file.
- A `### Screen:` subsection with the Figma reference URL, processing date, Token Map, and a visual acceptance checklist.

The checklist contains measurable items derived from the design:

```markdown
- [ ] Card container uses 16px border-radius (--radius-lg)
- [ ] Header text is 24px/700 (--font-heading-lg)
- [ ] Grid uses 3 columns at desktop breakpoint with 24px gap
- [ ] Empty state illustration is centered with 48px top margin
```

### Step 7: Commit

The PM commits the design artifacts and spec update together:

```
spec(dashboard_overview): ingest design artifact for main_screen
```

---

## 4. Example 2: Using a Live Web Page as Reference

When you do not have Figma designs -- for example, when reverse-engineering from an existing app or studying a competitor -- you can use a live web page as the design source.

### Step 1: Run Design Ingest with the "live:" Prefix

```
/pl-design-ingest live:https://example.com/dashboard
```

The `live:` prefix tells the PM to treat this URL as a web page to analyze, not a Figma file.

### Step 2: What the PM Extracts

The PM uses WebFetch to load the page and extracts:

- **CSS patterns** -- colors, font sizes, spacing, border radii, shadows.
- **Component structure** -- the DOM hierarchy, repeated patterns, layout approach.
- **Computed styles** -- actual rendered values for key elements.

### Step 3: Token Map from Observed Values

The PM maps the CSS values it observes to your project's design anchor tokens, just like the Figma flow:

```markdown
- **Token Map:**
  - `observed: #1976D2` -> `var(--project-accent)`
  - `observed: 14px` -> `var(--project-text-sm)`
  - `observed: 8px 16px` -> `var(--project-space-2) var(--project-space-4)`
```

If no design anchor exists yet, the PM uses literal values and notes that you should create a `design_*.md` anchor to enable proper token mapping.

### Step 4: Visual Specification

The PM creates the same `## Visual Specification` section with Token Map and acceptance checklists, following the same format as the Figma flow. The only difference is the reference line points to the live URL instead of a Figma URL.

---

## 5. The Probing Question Protocol

When you ask the PM to create a new feature spec (via `/pl-spec` or during onboarding), it does not just take your description and run. It asks five rounds of structured questions to surface requirements you might not have considered.

### Round 1: Scope

The PM asks about screens, data, and user goals.

- What screens or views does this feature involve?
- What data does it display or manipulate?
- What is the user trying to accomplish?

### Round 2: Edge Cases

The PM probes error states, loading behavior, responsive layout, and accessibility.

- What happens when the data fails to load?
- What does the loading state look like?
- How does this behave on mobile vs. desktop?
- Are there accessibility requirements (keyboard navigation, screen reader support)?

### Round 3: Behavior

The PM asks about interactions, state management, and navigation.

- What happens when the user clicks, hovers, or drags?
- Does this feature maintain state across page navigations?
- How does the user get to this screen, and where do they go next?

### Round 4: Design

The PM asks about Figma designs and visual hierarchy.

- Do Figma designs exist for this feature?
- What is the visual priority -- what should the user see first?

### Round 5: Constraints

The PM asks about performance, platform limitations, and simplicity.

- Are there performance budgets (load time, bundle size)?
- Are there platform constraints (browser support, device targets)?
- What is the simplest version of this feature that would be useful?

You do not need to have answers to every question. The PM adapts based on what you tell it. The goal is to produce a spec with enough detail that the Builder can implement without guessing.

---

## 6. What Gets Created

Here is a summary of every artifact the PM agent can produce.

| Artifact | Location | Description |
|---|---|---|
| Feature spec | `features/<name>.md` | The primary specification: overview, requirements, Unit Tests, QA Scenarios, and optional visual specification. This is what the Builder implements against. |
| Anchor node | `features/design_<name>.md` or `features/policy_<name>.md` | Shared design standards or policy constraints that apply across multiple features. |
| Design brief | `features/design/<feature_stem>/brief.json` | Machine-readable Figma data (tokens, screens, components) that the Builder reads instead of accessing Figma. |
| Design artifacts | `features/design/<feature_stem>/` | Local copies of design assets (images, exported screens) stored alongside the brief. |
| Token Map | Inside the feature spec's Visual Specification section | Mapping from Figma design variable names (or observed CSS values) to the project's CSS custom properties. |
| Visual checklist | Inside the feature spec's Visual Specification section | Measurable acceptance criteria derived from design properties (dimensions, spacing, colors, typography). |

### Visual Ownership: Specification vs. Verification

The PM **authors** the Visual Specification -- Token Maps, acceptance checklists, and design briefs. The Builder **verifies** all visual checklist items during implementation (via `/pl-web-test` for web features, manual inspection for non-web features). QA does not re-verify visual items. This separation keeps the PM focused on design intent and the Builder accountable for visual fidelity in the implementation.

### How Artifacts Flow Between Agents

```
PM creates spec + brief.json
    |
    v
Architect validates structure and requirements
    |
    v
Builder reads spec + brief.json, writes code and tests,
  verifies visual checklist items during implementation
    |
    v
QA verifies QA Scenarios (behavioral tests requiring human judgment)
```

The Builder never needs Figma access. The brief.json and Token Map contain everything needed to match the design.

---

## 7. Day-to-Day Tips

### Creating a New Spec

```
/pl-spec user-settings
```

The PM checks if a spec for "user-settings" already exists. If not, it creates one using the probing question protocol. If it exists, the PM opens it and proposes targeted updates.

### When to Re-Ingest a Design

Re-run `/pl-design-ingest` when:

- The Figma design has been updated since the last ingest.
- You want to add a new screen to an existing feature's visual specification.
- The design anchor tokens have changed and you need to refresh the Token Map.

Use the "reprocess" keyword to re-ingest a specific screen:

```
/pl-design-ingest reprocess dashboard_overview main_screen
```

### Handling Design Disputes

When the Builder or QA flags a discrepancy between the spec and the implementation, entries tagged `SPEC_DISPUTE` are routed to the PM. You own the resolution:

1. Check [the Critic](critic-and-cdd-guide.md) report (`/pl-status`) for any SPEC_DISPUTE items.
2. Review the disputed section of the spec.
3. Update the spec if the design intent was misunderstood, or confirm the spec is correct and the implementation needs to change.

### Finding Where a Topic Lives

```
/pl-find authentication
```

This searches across all specs to find where a topic is discussed. Useful when you are unsure if a requirement is already covered somewhere.

### Auditing Design Consistency

```
/pl-design-audit
```

This checks that design artifacts, Token Maps, and visual specifications are consistent with each other and with the current design anchors.

### Checking Project Status

```
/pl-status
```

This runs the CDD status tool and shows the current state of all features -- which are in TODO, which are being built, which are complete, and what the Critic has flagged.

---

## 8. Command Reference

| Command | Description |
|---|---|
| `/pl-spec <topic>` | Create a new feature spec or update an existing one. Launches the probing question protocol for new specs. |
| `/pl-design-ingest <source>` | Ingest a Figma URL, live web page (prefix with `live:`), or local image/PDF into a feature's visual specification. Generates Token Map and brief.json. |
| `/pl-design-audit` | Audit design artifacts for consistency with specs and design anchors. |
| `/pl-find <topic>` | Search across all specs to discover where a topic is discussed. |
| `/pl-status` | Check CDD status: feature states, Critic action items, and overall project health. |
| `/pl-help` | Display the full command list. |
| `/pl-resume [save\|role]` | Save or restore PM session state. |
| `/pl-agent-config` | Modify PM [agent configuration](agent-configuration-guide.md) (model, effort, permissions). |
| `/pl-override-edit` | Edit PM_OVERRIDES.md to customize PM behavior for your project. |
| `/pl-purlin-issue` | Report a Purlin framework issue. |
| `/pl-update-purlin` | Update the Purlin submodule with intelligent conflict handling. |
