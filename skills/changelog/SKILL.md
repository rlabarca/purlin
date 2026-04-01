---
name: changelog
description: Plain-English summary of changes since last verification, cross-referenced with specs
---

Read-only skill. Calls the `changelog` MCP tool for structured data, then interprets and formats the results into a PM/QA-readable report with actionable directives.

## Usage

```
purlin:changelog                        Summarize changes since last verification
purlin:changelog pm                     Summarize with PM priorities only
purlin:changelog eng                    Summarize with engineer priorities only
purlin:changelog qa                     Summarize with QA priorities only
purlin:changelog --since <N>            Last N commits
purlin:changelog --since <date>         Since a date (YYYY-MM-DD)
```

The role can be passed as a bare positional argument (`purlin:changelog pm`) or as a flag (`purlin:changelog --role pm`). Both are equivalent. If no role is given, show all three priority sections.

## Step 1 — Call the changelog MCP tool

```
changelog(since: <from --since arg if given>, role: <from role arg if given, default "all">)
```

The tool returns structured JSON containing:
- `since` — human-readable description of the anchor point
- `commits` — list of one-line commit summaries
- `files` — each changed file with `path`, `category` (CHANGED_SPECS, CHANGED_BEHAVIOR, TESTS_ADDED, NEW_BEHAVIOR, NO_IMPACT), `spec` (matched spec name or null), and `diff_stat`
- `spec_changes` — for each changed spec: `new_rules` and `removed_rules`
- `proof_status` — per-feature: `proved`, `total`, `status` (READY/FAILING/partial), `failing_rules`

Deleted files are already filtered out by the tool — only files that exist on disk are included.

## Step 2 — Interpret and Refine

Read the JSON and apply judgment in one pass:

1. **Refine NEW_BEHAVIOR entries.** The tool mechanically flags all unscoped code files as NEW_BEHAVIOR. Review the file paths and diff_stats — reclassify internal helpers, utilities, build scripts, or trivial files as NO_IMPACT. Only keep genuinely new user-facing functionality as NEW_BEHAVIOR.

2. **Group related files.** Multiple files that belong to the same logical change should be grouped under a single summary line. Use commit messages from the `commits` list for context.

3. **Write for the reader, not the coder.** The changelog is for PMs and QA, not engineers. Translate implementation details into user-visible impact:
   - "Refactored the authentication middleware to use a strategy pattern" → "Changed how login works internally (no user-facing changes)"
   - "Added rate limiting to /api/v2/users endpoint" → "Users who make too many API requests will now be temporarily blocked"
   - "Fixed N+1 query in user list resolver" → "User list page loads faster"

   Technical details go in NO IMPACT. Behavioral changes in CHANGED BEHAVIOR must describe what the USER sees, not what the CODE does.

## Step 3 — Format Output

Print the report using the 5 categories. Omit empty sections.

```
Since <since field from JSON>:

NEW BEHAVIOR:
  <plain English summary>
  Files: <file1>, <file2>
  No spec exists.
  → Run: purlin:spec <suggested_name>

CHANGED BEHAVIOR:
  <spec_name> — <plain English description>
  Files: <file1>, <file2>
  Spec exists: specs/<category>/<name>.md (RULE-N may need updating)
  → Review: purlin:find <spec_name>

CHANGED SPECS:
  <spec_name> — <what changed: new_rules/removed_rules from spec_changes>
  Files: specs/<category>/<name>.md
  → Run: purlin:unit-test

TESTS ADDED:
  <spec_name> — <summary from proof_status>
  Files: <test_file1>, <test_file2>

NO IMPACT:
  <description>
  Files: <file1>, <file2>
```

### Directives per category

| Category | Directive |
|----------|-----------|
| NEW BEHAVIOR | `→ Run: purlin:spec <suggested_name>` |
| CHANGED BEHAVIOR | `→ Review: purlin:find <spec_name>` |
| CHANGED SPECS | `→ Run: purlin:unit-test` |
| TESTS ADDED | Show pass/fail from `proof_status`, or `→ Run: purlin:unit-test` |
| NO IMPACT | No directive |

## Step 4 — TOP PRIORITIES

After all category sections, print a `---` separator and role-aware priorities. Use the `proof_status` and `files` data from the JSON. If a role was specified, show only that role. Otherwise show all three.

### PM priorities (ordered)

1. **Missing specs** — NEW BEHAVIOR items with no spec → `purlin:spec <name>`
2. **Spec drift** — CHANGED BEHAVIOR where spec may be outdated → `purlin:find <name>`
3. **Unproved new rules** — CHANGED SPECS with `new_rules` that lack proofs → `purlin:unit-test`

### Engineer priorities (ordered)

1. **Failing tests** — features with `status: "FAILING"` in `proof_status` → fix code or tests
2. **Unproved rules** — features with `status: "partial"` → `purlin:unit-test`
3. **New unspecced code** — NEW BEHAVIOR items → `purlin:spec <name>`

### QA priorities (ordered)

1. **Stale manual proofs** — features with stale manual stamps → `purlin:verify --manual`
2. **Features ready for verification** — features with `status: "READY"` → `purlin:verify`
3. **Coverage gaps** — features with `status: "partial"` → `purlin:unit-test`

### Format

```
---
TOP PRIORITIES (PM):
  1. <description> — <action>
  2. <description> — <action>

TOP PRIORITIES (Engineer):
  1. <description> — <action>

TOP PRIORITIES (QA):
  1. <description> — <action>
```

Omit any role section with no priorities. Limit to 5 items per role.

## Guidelines

- **This is one LLM pass over structured data.** Do not make additional tool calls. The `changelog` MCP tool already did all the mechanical work.
- **Write for a PM, not a developer.** Summarize behavior, not implementation details.
- **One line per logical change.** Group related files under a single summary.
- **Be conservative with NEW BEHAVIOR.** Reclassify helpers and internals to NO IMPACT.
- **No writes.** This skill reads and reports. It does not modify anything.
