# Policy Invariant Spec (`i_policy_*`)

> Canonical definition for `i_policy_*.md` invariant files.
> Spec-Version: 1.0

## Purpose

Policy invariants enforce compliance, security, and governance rules from an external authority — a CISO's security standards, legal/regulatory mandates, or organizational process requirements. They originate from an external git repo and cannot be edited locally.

## When to Use

- Security standards (authentication requirements, input validation, encryption mandates)
- Compliance rules (GDPR data handling, SOC 2 logging, HIPAA access controls)
- Governance processes (change management, approval workflows, audit trail requirements)
- Operational policies (incident response, data retention, access control)

If the policy is locally authored by your project team, use a `policy_*.md` anchor instead.

## Required Sections

| Section | Required | Description |
|---------|----------|-------------|
| `## Purpose` | Yes | What compliance/security domain this covers and the authority behind it |
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
# Policy: Data Security

> Label: "Policy: Data Security"
> Category: "Security"
> Format-Version: 1.1
> Invariant: true
> Version: 3.0.0
> Source: https://github.com/acme-org/security-standards
> Source-Path: policies/data_security.md
> Source-SHA: d4e5f6a
> Synced-At: 2026-03-28T12:00:00Z
> Scope: global

## Purpose

Enforces ACME's data security standards across all services. Mandated by the CISO office. Compliance is audited quarterly.

## Security Invariants

### Authentication

- INV-1: All API endpoints MUST require authentication. No anonymous access to data endpoints.
- INV-2: Session tokens MUST be stored in httpOnly cookies, not localStorage.

### Data Handling

- INV-3: PII MUST NOT appear in log output. Use structured logging with PII redaction.
- INV-4: All database queries MUST use parameterized statements. No string concatenation.

## FORBIDDEN Patterns

* No raw SQL string concatenation (INV-4).
    * **Pattern:** `f"SELECT.*{`
    * **Scope:** `src/**/*.py`
    * **Exemption:** Migration scripts in `migrations/`

* No PII in log statements (INV-3).
    * **Pattern:** `log.*(email|ssn|phone|password)`
    * **Scope:** `src/**/*.py`
    * **Exemption:** Audit log module only
```

## Scope Guidance

Use `global` for security and compliance rules that apply to every feature. Use `scoped` for domain-specific policies (e.g., payment processing rules that only apply to billing features).
