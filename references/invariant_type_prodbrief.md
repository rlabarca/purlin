# Product Brief Invariant Spec (`i_prodbrief_*`)

> Canonical definition for `i_prodbrief_*.md` invariant files.
> Spec-Version: 1.0

## Purpose

Product brief invariants capture product goals, user stories, and success criteria from an external authority — product leadership, a product management tool, or a strategy repo. They express what the product should achieve, not how to build it. They originate from an external git repo and cannot be edited locally.

## When to Use

- Product goals from leadership (quarterly OKRs, product vision)
- User stories from a product management system exported to git
- Success criteria and KPIs that features must contribute toward
- Strategic mandates that scope what gets built

If the product goals are locally authored by your project team, use a `prodbrief_*.md` anchor instead.

## Required Sections

| Section | Required | Description |
|---------|----------|-------------|
| `## Purpose` | Yes | The product goal this brief defines |
| `## User Stories` | Yes | Grouped by epic/theme, in standard story format |
| `## Success Criteria` | Yes | Measurable outcomes with targets (KPIs) |
| `## Acceptance Scenarios` | Optional | Given/When/Then for product behavior validation |

## Required Metadata

```markdown
> Format-Version: 1.1
> Invariant: true
> Version: <semver>
> Source: <git-repo-url>
> Source-Path: <path-within-repo>
> Source-SHA: <git-commit-sha>
> Synced-At: <ISO-8601-timestamp>
> Scope: <global | scoped>
```

## Enforcement

Product brief invariants are advisory — they don't have FORBIDDEN patterns or build blocks. They inform spec writing and audit findings.

| Where | What | Blocks? |
|-------|------|---------|
| `purlin:spec` | PM sees applicable user stories as context | No |
| `purlin:spec-code-audit` | Dimension 14 checks story coverage | No — audit finding |

## Example

```markdown
# Product Brief: Onboarding Redesign

> Label: "Product: Onboarding Redesign"
> Category: "Product"
> Format-Version: 1.1
> Invariant: true
> Version: 1.0.0
> Source: https://github.com/acme-org/product-briefs
> Source-Path: briefs/onboarding_redesign.md
> Source-SHA: e1f2a3b
> Synced-At: 2026-03-28T12:00:00Z
> Scope: scoped

## Purpose

Defines the product goals for the Q2 onboarding redesign initiative. Approved by VP Product.

## User Stories

### First-Time Setup

- As a new user, I want to complete setup in under 3 minutes, so that I can start using the product immediately.
- As a new user, I want to import my existing data during onboarding, so that I don't start from scratch.

### Activation

- As a new user, I want to see a personalized dashboard after onboarding, so that I understand what the product can do for me.

## Success Criteria

- KPI-1: 90% of new users complete onboarding within 3 minutes (up from 60%)
- KPI-2: 70% of users who complete onboarding return within 7 days (up from 45%)
- KPI-3: Support tickets related to setup drop by 50%

## Acceptance Scenarios

Scenario: Fast onboarding completion
  Given a new user with no prior account
  When they follow the onboarding flow
  Then they reach the dashboard in under 3 minutes
```

## Scope Guidance

Use `scoped` for initiative-specific briefs (only features in the initiative reference it). Use `global` sparingly — only for product-wide mandates like "all features must support mobile viewport."
