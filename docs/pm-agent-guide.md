# PM Guide

How to write feature specs, manage designs, and define project standards.

---

## What PM Skills Do

PM is where you define **what** to build. PM skills translate your ideas — whether from a conversation, a Figma design, or a live web page — into structured feature specs that the engineer can implement and QA can verify.

The PM:

- Creates feature specs with requirements, scenarios, and optional visual specifications.
- Imports Figma designs as invariants and extracts tokens, components, and annotations.
- Asks structured questions to fill gaps before the spec is handed off.
- Manages anchor nodes — shared design standards and policy rules that apply across features.
- Never writes code. Specs and design artifacts are PM's domain.

### Getting Started

Run any PM skill directly:

```
purlin:spec user-settings       # Create a spec
purlin:invariant add <url>      # Import an invariant
purlin:anchor design_tokens     # Create a design anchor
```

---

## Creating a Feature Spec

The agent first runs `purlin:find` to check if a spec already exists for the topic. If not:

```
purlin:spec user-settings
```

PM mode walks you through a series of questions across five areas:

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

## Working with Designs

PM mode manages all design artifacts — local anchors, Figma invariants, Token Maps, and visual specifications. For the full design workflow, see the [Design Guide](design-guide.md).

### Figma Designs

When you have Figma designs, PM mode can extract them directly and turn them into structured specs.

### One-Time Setup

If the Figma MCP connection isn't set up, PM mode walks you through it:

```
claude mcp add --transport http figma https://mcp.figma.com/mcp
```

Restart Claude Code, then type `/mcp` and authenticate with Figma.

### Adding a Design Invariant from Figma

For org-wide or shared design systems, create a design invariant:

```
purlin:invariant add-figma https://www.figma.com/design/ABC123/My-App-Designs
```

This creates `features/_invariants/i_design_<name>.md` — an immutable pointer to the Figma document. PM provides the purpose, and Purlin extracts annotations and metadata via Figma MCP. See the [Figma Guide](figma-guide.md) for the full workflow.

To upgrade an existing local design anchor to a Figma invariant:

```
purlin:invariant add-figma https://www.figma.com/design/ABC123/My-App-Designs design_visual_standards.md
```

This replaces the local anchor, updates all prerequisite links, and cascade-resets dependent features.

### Writing a Visual Specification

Once a Figma design is available (as an invariant or referenced by URL), use `purlin:spec` to write the Visual Specification:

```
purlin:spec dashboard-overview
```

PM mode reads the Figma design via MCP, then writes the spec with:

1. **Token Map** — connects Figma variable names to your project's CSS custom properties.
2. **`brief.json`** — a machine-readable design cache that Engineer mode reads instead of needing Figma access.
3. **Visual checklist** — measurable items for verification:

```markdown
- [ ] Card container uses 16px border-radius (--radius-lg)
- [ ] Header text is 24px/700 (--font-heading-lg)
- [ ] Grid uses 3 columns at desktop with 24px gap
```

### Local Design Assets (No Figma)

For local images, PDFs, or web references that don't come from Figma:

1. Copy the file to `features/_design/<feature_stem>/`
2. Reference it in a local design anchor via `purlin:anchor design_<name>`
3. Write the Visual Specification via `purlin:spec`

---

## Anchor Nodes

Anchors are shared rules that apply across multiple features. Five types:

- **`design_*`** (PM-owned) — Visual standards: color systems, typography, spacing, accessibility rules.
- **`policy_*`** (PM-owned) — Governance: compliance requirements, security baselines, release rules.
- **`ops_*`** (PM-owned) — Operational: CI/CD, deployment, monitoring, infrastructure mandates.
- **`prodbrief_*`** (PM-owned) — Product goals: user stories, outcomes, KPIs, success criteria.
- **`arch_*`** (Engineer-owned) — Technical standards: API conventions, code patterns, testing discipline.

Create or update an anchor:

```
purlin:anchor design_typography
```

When an anchor changes, all features that depend on it are flagged for re-verification. For design-specific workflows, see the [Design Guide](design-guide.md). For importing external rules as immutable invariants, see the [Invariants Guide](invariants-guide.md).

---

## Day-to-Day Commands

| Command | What It Does |
|---------|--------------|
| `purlin:spec <topic>` | Create or update a feature spec. |
| `purlin:invariant add <repo-url>` | Import an invariant from an external git repo. |
| `purlin:invariant add-figma <url>` | Import a Figma design as an immutable invariant. |
| `purlin:invariant sync <file>` | Sync an invariant when its source changes. |
| `purlin:invariant remove <file>` | Remove an invariant and clean up prerequisites. |
| `purlin:invariant list` | Show all invariants with sync status. |
| `purlin:invariant check-updates` | Check if any invariants have newer upstream versions. |
| `purlin:invariant check-conflicts` | Find contradictions between invariants (any mode). |
| `purlin:invariant check-feature <name>` | Verify a feature meets its applicable invariants (any mode). |
| `purlin:invariant validate` | Check all invariants for format/metadata (any mode). |
| `purlin:design-audit` | Audit design artifacts for staleness, reference integrity, token conflicts, and invariant sync status. |
| `purlin:anchor <name>` | Create or update a design/policy anchor. `arch_*` anchors are engineer-owned. |
| `purlin:find <topic>` | Search specs for where a topic is discussed. |
| `purlin:status` | Check feature states and what needs attention. |
| `purlin:help` | Full command list. |

---

## How PM Connects to Other Roles

```
PM creates the spec
    ↓
Engineer reads the spec, writes code and tests
    ↓
QA verifies behavior against the spec
    ↓
Discoveries flow back to PM for spec updates
```

The engineer never needs Figma access — the spec, Token Map, and `brief.json` contain everything needed. QA doesn't re-verify visual items — that's the engineer's job during implementation.

When the engineer or QA finds something the spec didn't cover, it shows up as an action item for PM. Check `purlin:status` to see what needs your attention.
