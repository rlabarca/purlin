# Architecture Invariant Spec (`i_arch_*`)

> Canonical definition for `i_arch_*.md` invariant files.
> Spec-Version: 1.0

## Purpose

Architecture invariants enforce technical standards from an external authority — API conventions, service boundaries, data modeling rules, coding patterns. They originate from an architecture team's git repo and cannot be edited locally.

## When to Use

- Org-wide API standards (endpoint naming, error response format, versioning scheme)
- Service architecture constraints (allowed communication patterns, data ownership)
- Code quality mandates (no eval, no raw SQL, required error handling)
- Infrastructure patterns (logging format, health check requirements)

If the standard is locally authored by your project team, use an `arch_*.md` anchor instead.

## Required Sections

| Section | Required | Description |
|---------|----------|-------------|
| `## Purpose` | Yes | What constraints this enforces and the organizational authority behind them |
| `## <Domain> Invariants` | Yes | Numbered invariant statements (INV-1, INV-2, ...) — specific, testable |
| `## FORBIDDEN Patterns` | Optional | Regex patterns that block builds when matched |
| `## Verification Scenarios` | Optional | Given/When/Then scenarios demonstrating compliance |

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

| Where | What | Blocks? |
|-------|------|---------|
| `purlin:build` Step 0 | FORBIDDEN pattern grep against feature code files | Yes |
| `purlin:build` Step 0 | Behavioral invariant statements shown as reminders | No |
| `purlin:spec-code-audit` | Dimension 14 compliance check | No — audit finding |

## Example

```markdown
# Architecture: API Standards

> Label: "Architecture: API Standards"
> Category: "Architecture"
> Format-Version: 1.1
> Invariant: true
> Version: 2.1.0
> Source: https://github.com/acme-org/standards
> Source-Path: features/arch_api_standards.md
> Source-SHA: a1b2c3d
> Synced-At: 2026-03-28T12:00:00Z
> Scope: global

## Purpose

Enforces ACME's API design standards across all services. Mandated by the Architecture Review Board.

## API Invariants

### Endpoint Design

- INV-1: All endpoints MUST return structured error responses with `code`, `message`, and `request_id` fields.
- INV-2: Version prefix MUST be `/api/v{N}/` where N is a positive integer.

### Data Handling

- INV-3: No `eval()` in user-facing code paths.
- INV-4: All user data access MUST be logged with correlation ID.

## FORBIDDEN Patterns

* No eval() in user-facing code (INV-3).
    * **Pattern:** `eval\(`
    * **Scope:** `src/**/*.py`
    * **Exemption:** Test fixtures only
```

## Scope Guidance

Use `global` for org-wide API standards that apply to every feature. Use `scoped` for domain-specific architecture rules (e.g., database access patterns that only apply to data-layer features).
