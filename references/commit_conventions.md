# Commit Conventions

> Referenced by PURLIN_BASE.md commit discipline and by skills that create commits.

## Mode Attribution Prefixes

| Mode | Prefixes | Example |
|------|----------|---------|
| Engineer | `feat(scope):`, `fix(scope):`, `test(scope):` | `feat(auth): implement login flow` |
| PM | `spec(scope):`, `design(scope):` | `spec(notifications): add edge scenarios` |
| QA | `qa(scope):`, `status(scope):` | `qa(auth): record [BUG] timeout` |
| Shared | `chore(scope):`, `docs(scope):` | `chore: update dependency graph` |

## Mode Trailer

All commits MUST include a `Purlin-Mode:` trailer identifying the active mode:

```
feat(auth): implement login flow

Purlin-Mode: Engineer
```

## Status Tag Commits

Status tag commits use a separate format and MUST be standalone (not combined with code changes):

```
status(scope): [Complete features/FILENAME.md] [Scope: full]
status(scope): [Ready for Verification features/FILENAME.md] [Scope: targeted:A,B]
```

QA completions add `[Verified]`:
```
status(scope): [Complete features/FILENAME.md] [Verified]
```

### Scope Types

| Scope | When |
|-------|------|
| `full` | Behavioral change, new scenarios. Default. |
| `targeted:A,B` | Only specific scenarios affected. |
| `cosmetic` | Non-functional change (formatting, logging). |
| `dependency-only` | Prerequisite update, no direct code changes. |

## Lifecycle Reset Exemption Tags

Include these trailer tags in commit messages to prevent lifecycle resets when modifying feature spec files:

| Tag | Meaning | When to Use |
|-----|---------|-------------|
| `[QA-Tags]` | Only modifies `@auto`/`@manual` tag suffixes | QA classifying scenarios |
| `[Spec-FMT]` | Only formatting changes, no behavioral content change | PM fixing formatting |
| `[Migration]` | Batch role/terminology renames during framework migration | pl-update-purlin migration |

If ALL commits to a feature spec since the last status commit contain exempt tags, the lifecycle is preserved. If ANY commit lacks an exempt tag, the normal reset applies.

## Commit Discipline

- Commit at logical milestones — never defer all commits until session end.
- Status tag commits MUST be separate, standalone commits.
- Implementation work on a single feature MAY be batched into one or a small number of logical commits.
