> Criteria-Version: 1

# Drift Detection Criteria

This document defines how the `drift` MCP tool and `purlin:drift` skill classify changed files and detect spec drift. The MCP tool implements deterministic classification. The skill applies semantic analysis on top.

## File Classification (MCP Tool — Deterministic)

The tool classifies each changed file in strict order. First match wins.

| Order | Category | Match condition |
|-------|----------|----------------|
| 1 | CHANGED_SPECS | Path starts with `specs/` and ends with `.md` |
| 2 | TESTS_ADDED | Path matches a test pattern (see below) |
| 3 | CHANGED_BEHAVIOR | Path is in any spec's `> Scope:` (exact or prefix match) |
| 4 | NO_IMPACT | Path matches a documentation/config pattern AND is not in a behavioral directory |
| 5 | NEW_BEHAVIOR | Everything else — unscoped code or behavioral files without a spec |

### Test Patterns

A file is TESTS_ADDED if its path contains any of: `.proofs-`, `test_`, `_test.`, `.test.`, `tests/`, `dev/test_`.

### NO_IMPACT Patterns

Files matching these path prefixes/suffixes are documentation or config with no behavioral impact:

- `docs/`, `assets/`, `templates/`, `references/`
- `.gitignore`, `LICENSE`, `CLAUDE.md`, `README.md`, `RELEASE_NOTES.md`
- `.mcp.json`, `settings.json`
- Any `.md` file not in a behavioral directory

### Behavioral Directory Exclusions

These directories contain behavioral definitions even when files end in `.md`. They are **excluded** from the `.md` catch-all in NO_IMPACT:

- `skills/` — skill instructions control what the agent does
- `agents/` and `.claude/agents/` — agent definitions control agent behavior

Files in these directories that are not in any spec's `> Scope:` are classified as NEW_BEHAVIOR, not NO_IMPACT. This ensures that changing a skill definition triggers a "no spec exists" or "spec drift" flag rather than being silently ignored.

Note: `specs/` files are already caught by the CHANGED_SPECS rule (order 1) and never reach the NO_IMPACT check.

### Scope Matching

The tool builds a scope-to-spec map from all `> Scope:` metadata. Matching supports two modes:

- **Exact match** — `> Scope: scripts/mcp/purlin_server.py` matches only that exact path
- **Prefix match** — `> Scope: src/api/` (trailing slash) matches any file whose path starts with `src/api/`

Prefix match enables directory-scoped specs without listing every file.

## Significance Classification (Skill — Semantic)

The skill re-classifies MCP categories by reading the actual `git diff`. The MCP category is a starting point; the diff tells you the real significance.

| Significance | Meaning | Source |
|-------------|---------|--------|
| BEHAVIORAL | Changes what the software does | CHANGED_BEHAVIOR or NEW_BEHAVIOR files where the diff adds/removes logic |
| STRUCTURAL | Changes organization without changing behavior | CHANGED_BEHAVIOR files where the diff is a rename/refactor |
| OPERATIONAL | Changes how the software runs (CI, deploy, env) | Makefiles, Dockerfiles, CI configs, env vars |
| DOCUMENTATION | Changes to docs, comments, guides | NO_IMPACT files, or CHANGED_BEHAVIOR files where only comments changed |
| TRIVIAL | Formatting, whitespace, typos | Any file where the diff is cosmetic |

## Behavioral Gap Drift Detection

When a feature has no behavioral proofs (only structural checks) AND has changed files, the proofs don't actually test the changed behavior — they only verify that instruction text exists.

The MCP tool precomputes this. Each file entry classified as CHANGED_BEHAVIOR includes:

- `behavioral_gap: true` — when the file's spec has no behavioral proofs (only structural checks)

The top-level result includes a `drift_flags` array summarizing all features with no behavioral proofs that have changed files:

```json
{
  "drift_flags": [
    {
      "spec": "purlin_agent",
      "reason": "behavioral_gap_with_code_change",
      "files": ["agents/purlin.md"]
    }
  ]
}
```

The skill should surface these prominently:

```
Spec: purlin_agent (8 rules, 0 behavioral proofs)
⚠ All proofs are structural checks. Code changed but no behavioral test verifies the new behavior.
→ Run: purlin:spec purlin_agent (add behavioral rules)
```

## Broken Scope Detection

When a spec's `> Scope:` references a file or directory that no longer exists on disk, the file was likely deleted or renamed without updating the spec. The `drift` MCP tool checks every scope path in every spec against the filesystem:

- **Exact paths** — checked via `os.path.exists()`
- **Prefix paths** (trailing `/`) — checked via `os.path.isdir()`

Any spec with at least one missing scope path is included in the `broken_scopes` array in the result JSON:

```json
{
  "broken_scopes": [
    {
      "spec": "login",
      "missing_paths": ["src/auth/old_login.py"],
      "existing_paths": ["src/auth/session.js"]
    }
  ]
}
```

This is surfaced as an action item in drift reports. If the file was renamed, `purlin:rename` updates the scope and references. If the file was intentionally deleted, `purlin:spec` should be used to update or remove the spec.

## External Reference Drift (Anchors with `> Source:`)

Anchors with `> Source:` metadata point to an external origin (git repo, URL). When the external source changes, the anchor may be stale. The skill detects this by comparing the `> Pinned:` SHA or timestamp against the current state of the source.

| Condition | Classification | Action |
|-----------|---------------|--------|
| `> Pinned:` SHA matches current source HEAD | No drift | No action needed |
| `> Pinned:` SHA is behind current source HEAD | External drift | `⚠ Anchor may be stale → Run: purlin:anchor sync <name>` |
| `> Source:` URL is unreachable | Broken reference | `✗ Source unreachable → Verify URL in anchor` |
| No `> Pinned:` field on a `> Source:` anchor | Unpinned | `⚠ Unpinned anchor — Run: purlin:anchor sync <name> to pin` |

External drift does not automatically update the anchor. The `purlin:anchor sync` command fetches the latest source, updates the anchor content, and bumps the `> Pinned:` value. This is intentionally manual — external changes require review before adoption.

## Spec Drift Rules

For each BEHAVIORAL change, the skill checks existing rules:

- Rules still match → `Spec up to date ✓`
- Spec exists but new behavior isn't covered → `⚠ Spec may need new rules`
- No spec exists → `No spec exists → Run: purlin:spec <name>`
- Feature is VERIFIED but structural-only with code changes → flag as above

The proof count from `proof_status` reflects the state BEFORE the current changes. A feature showing "6/6 proved" after behavioral code changes still needs spec review — those 6 proofs were for the old behavior.

## Config Field Ownership

`.purlin/config.json` fields and which skill owns each:

| Field | Written by | Read by | Default |
|-------|-----------|---------|---------|
| `version` | `purlin:init` | — | `"0.9.0"` |
| `test_framework` | `purlin:init` (Step 3) | `purlin:unit-test` (Step 1) | `"auto"` |
| `spec_dir` | `purlin:init` | `sync_status` MCP tool | `"specs"` |
| `pre_push` | `purlin:init` | pre-push hook | `"warn"` |
| `audit_criteria` | `purlin:init --sync-audit-criteria` | `purlin:audit` (Step 1) | not set (uses built-in) |
| `audit_criteria_pinned` | `purlin:init --sync-audit-criteria` | `purlin:audit` (Step 1) | not set |
| `audit_llm` | `purlin:init --audit-llm` | `purlin:audit` (External LLM Mode) | not set (uses Claude) |
| `audit_llm_name` | `purlin:init --audit-llm` | `purlin:audit` (report header) | not set |
| `report` | `purlin:init --report` | `sync_status` (report-data.js side effect) | `true` |

`purlin:init` is the only skill that writes config. All other skills read their relevant fields. When a field is missing or set to `"auto"`, the reading skill applies its own fallback logic (e.g., `unit-test` auto-detects the framework).
