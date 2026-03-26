# PM Mode Guide

How to use PM mode to write feature specs, ingest designs, and define project standards.

---

## What PM Mode Does

PM mode is where you define **what** to build. It translates your ideas — whether from a conversation, a Figma design, or a live web page — into structured feature specs that Engineer mode can implement and QA mode can verify.

PM mode:

- Creates feature specs with requirements, scenarios, and optional visual specifications.
- Ingests Figma designs by extracting tokens, components, and annotations.
- Asks structured questions to fill gaps before the spec is handed off.
- Manages anchor nodes — shared design standards and policy rules that apply across features.
- Never writes code. Specs and design artifacts are PM's domain.

### Entering PM Mode

From any session:

```
/pl-mode pm
```

Or run a PM skill directly — `/pl-spec`, `/pl-design-ingest`, and `/pl-anchor` all activate PM mode automatically.

---

## Creating a Feature Spec

```
/pl-spec user-settings
```

If the spec doesn't exist yet, PM mode walks you through a series of questions across five areas:

1. **Scope** — What screens, data, and user goals are involved?
2. **Edge cases** — What happens on errors, loading, and different screen sizes?
3. **Behavior** — What are the interactions, state changes, and navigation flows?
4. **Design** — Do Figma designs exist? What's the visual priority?
5. **Constraints** — Performance budgets, browser support, simplest useful version?

You don't need answers for everything. PM mode adapts based on what you share. The goal is to produce a spec detailed enough that Engineer mode can build without guessing.

If the spec already exists, PM mode opens it and proposes targeted updates.

### What a Spec Contains

| Section | Purpose |
|---------|---------|
| Overview | What the feature does, in plain language. |
| Requirements | Behavioral rules — what must be true. |
| Unit Tests | What Engineer mode will automate (written by Engineer). |
| QA Scenarios | Verification steps for QA mode (written untagged — QA classifies later). |
| Visual Specification | Design checklists and token mappings (when designs exist). |

---

## Working with Figma Designs

When you have Figma designs, PM mode can extract them directly and turn them into structured specs.

### One-Time Setup

If the Figma MCP connection isn't set up, PM mode walks you through it:

```
claude mcp add --transport http figma https://mcp.figma.com/mcp
```

Restart Claude Code, then type `/mcp` and authenticate with Figma.

### Ingesting a Design

```
/pl-design-ingest https://www.figma.com/design/ABC123/My-App-Designs
```

PM mode asks which feature and screen the design belongs to, then:

1. **Extracts** components, layout, typography, colors, spacing, and annotations from Figma.
2. **Maps tokens** — connects Figma variable names to your project's CSS custom properties using your design anchor files.
3. **Generates `brief.json`** — a machine-readable design file that Engineer mode reads instead of needing Figma access.
4. **Writes a Visual Specification** in the feature spec with measurable checklist items:

```markdown
- [ ] Card container uses 16px border-radius (--radius-lg)
- [ ] Header text is 24px/700 (--font-heading-lg)
- [ ] Grid uses 3 columns at desktop with 24px gap
```

### Using a Live Web Page Instead

When Figma isn't available:

```
/pl-design-ingest live:https://example.com/dashboard
```

PM mode loads the page, extracts CSS patterns and layout structure, maps observed values to your design tokens, and writes the same Visual Specification format.

---

## Anchor Nodes

Anchors are shared rules that apply across multiple features. Three types:

- **`design_*`** (PM-owned) — Visual standards: color systems, typography, spacing, accessibility rules.
- **`policy_*`** (PM-owned) — Governance: compliance requirements, security baselines, release rules.
- **`arch_*`** (Engineer-owned) — Technical standards: API conventions, code patterns, testing discipline.

Create or update an anchor:

```
/pl-anchor design_typography
```

When an anchor changes, all features that depend on it are flagged for re-verification.

---

## Day-to-Day Commands

| Command | What It Does |
|---------|--------------|
| `/pl-spec <topic>` | Create or update a feature spec. |
| `/pl-design-ingest <source>` | Ingest a Figma URL or live web page. |
| `/pl-design-audit` | Check design artifacts for consistency. |
| `/pl-anchor <name>` | Create or update a design/policy anchor. |
| `/pl-find <topic>` | Search specs for where a topic is discussed. |
| `/pl-status` | Check feature states and what needs attention. |
| `/pl-help` | Full command list for PM mode. |

---

## How PM Mode Connects to Other Modes

```
PM mode creates the spec
    ↓
Engineer mode reads the spec, writes code and tests
    ↓
QA mode verifies behavior against the spec
    ↓
Discoveries flow back to PM mode for spec updates
```

Engineer mode never needs Figma access — the spec, Token Map, and `brief.json` contain everything needed. QA mode doesn't re-verify visual items — that's Engineer mode's job during implementation.

When Engineer or QA mode finds something the spec didn't cover, it shows up as an action item for PM mode. Check `/pl-status` to see what needs your attention.
