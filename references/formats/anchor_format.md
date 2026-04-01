# Anchor Spec Format

Anchors are regular specs with type-prefixed names that define cross-cutting constraints. They live in `specs/<category>/` alongside other specs and use the same 3-section format.

## Type Prefixes

| Prefix | Domain | Example |
|--------|--------|---------|
| `design_` | Visual/UX standards | `design_typography.md` |
| `api_` | API contracts | `api_rest_conventions.md` |
| `security_` | Security requirements | `security_auth_policy.md` |
| `brand_` | Brand guidelines | `brand_voice.md` |
| `platform_` | Platform constraints | `platform_browser_support.md` |
| `schema_` | Data schemas | `schema_user_model.md` |
| `legal_` | Legal/compliance | `legal_gdpr.md` |
| `prodbrief_` | Product brief requirements | `prodbrief_launch.md` |

## Template

```markdown
# Anchor: <type_prefix><name>

> Scope: <file patterns or modules this anchor governs>

## What it does

<One paragraph: what cross-cutting concern this anchor defines.>

## Rules

- RULE-1: <Constraint that applies to all features requiring this anchor>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <How to verify compliance>
- PROOF-2 (RULE-2): <How to verify compliance>
```

## How Anchors Work

1. An anchor defines rules in the same format as a regular spec.
2. Other specs reference the anchor via `> Requires: design_typography`.
3. `sync_status` includes the anchor's rules in the requiring spec's coverage.
4. Tests in the requiring feature use proof markers to prove the anchor's rules.

## Anchors vs Invariants

| | Anchor | Invariant |
|---|--------|-----------|
| Location | `specs/<category>/` | `specs/_invariants/` |
| Prefix | `design_`, `api_`, etc. | `i_design_`, `i_api_`, etc. |
| Source | Written locally | Synced from external source |
| Editable | Yes | No (read-only, gate-protected) |
| Has `> Source:`/`> Pinned:` | No | Yes |

Use anchors for constraints you define. Use invariants for constraints imported from external sources.
