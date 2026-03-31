# Operational Invariant Spec (`i_ops_*`)

> Canonical definition for `i_ops_*.md` invariant files.
> Spec-Version: 1.0

## Purpose

Operational invariants enforce infrastructure and deployment standards from an external authority — SRE team requirements, platform mandates, observability standards. They originate from an external git repo and cannot be edited locally.

## When to Use

- Observability mandates (structured logging format, metric naming, tracing requirements)
- Deployment constraints (health check endpoints, graceful shutdown, readiness probes)
- Infrastructure patterns (container resource limits, network policies, secret management)
- Incident response requirements (runbook format, alert routing, escalation paths)

If the operational standard is locally authored by your project team, use an `ops_*.md` anchor instead.

## Required Sections

| Section | Required | Description |
|---------|----------|-------------|
| `## Purpose` | Yes | What operational domain this covers and the authority behind it |
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
# Operations: Observability Standards

> Label: "Operations: Observability"
> Category: "Operations"
> Format-Version: 1.1
> Invariant: true
> Version: 1.2.0
> Source: https://github.com/acme-org/platform-standards
> Source-Path: ops/observability.md
> Source-SHA: b7c8d9e
> Synced-At: 2026-03-28T12:00:00Z
> Scope: global

## Purpose

Enforces ACME's observability standards for all services. Mandated by the SRE team. Required for production deployment approval.

## Observability Invariants

### Logging

- INV-1: All log output MUST use structured JSON format with `timestamp`, `level`, `message`, and `correlation_id` fields.
- INV-2: Log levels MUST follow: DEBUG (development only), INFO (request lifecycle), WARN (recoverable), ERROR (requires attention).

### Health Checks

- INV-3: Every service MUST expose `/healthz` (liveness) and `/readyz` (readiness) endpoints.
- INV-4: Health endpoints MUST respond within 200ms and return HTTP 200 when healthy.

## FORBIDDEN Patterns

* No print() for logging (INV-1).
    * **Pattern:** `print\(`
    * **Scope:** `src/**/*.py`
    * **Exemption:** CLI tools and test output
```

## Scope Guidance

Use `global` for platform-wide operational standards. Use `scoped` for domain-specific ops requirements (e.g., real-time processing SLAs that only apply to streaming features).
