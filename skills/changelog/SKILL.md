---
name: changelog
description: Plain-English summary of changes since last verification, cross-referenced with specs
---

Read-only skill. No writes, no markers, no state. Reads git log + code diffs + specs and produces a PM/QA-readable summary with actionable directives.

## Usage

```
purlin:changelog                   Summarize changes since last verification
purlin:changelog --since <N>       Last N commits
purlin:changelog --since <date>    Since a date (YYYY-MM-DD)
```

## Step 1 — Determine the "Since" Anchor

Find the starting point for the changelog, in order of precedence:

1. **`--since N`** (integer) — use `HEAD~N`
2. **`--since YYYY-MM-DD`** (date) — use `git log --since=<date>`
3. **Most recent `verify:` commit** — `git log --oneline --grep="^verify:" -1`
4. **Most recent tag** — `git describe --tags --abbrev=0 2>/dev/null`
5. **Fallback** — `HEAD~20` (last 20 commits)

Store the resolved anchor as `SINCE_REF` (a commit SHA or ref). Print the anchor context:

```
Since last verification (<ref>, <relative time>):
```

or if using fallback:

```
Since <ref> (<relative time>, no verification receipt found):
```

## Step 2 — Gather Changes

Run these git commands to collect raw data:

```bash
# All commits since anchor
git log --oneline $SINCE_REF..HEAD

# All changed files since anchor
git diff --name-only $SINCE_REF..HEAD

# Full diff for classification (read selectively, not all at once)
git diff $SINCE_REF..HEAD -- <file>
```

## Step 3 — Read Specs for Cross-Reference

Scan all specs to build a scope map:

1. Read all `specs/**/*.md` files.
2. For each spec, extract `> Scope:` file patterns.
3. Build a reverse map: `source_file → [spec_names]`.
4. Also note which specs have changed in the diff.

## Step 4 — Classify Each Changed File

For each file in the diff, classify it into exactly one category:

| File matches... | Category |
|-----------------|----------|
| `specs/**/*.md` (new/modified rules) | CHANGED SPECS |
| `> Scope:` of an existing spec (code change) | CHANGED BEHAVIOR |
| Test file with proof markers (`*.proofs-*.json`, or test files) | TESTS ADDED |
| Code file not in any spec's scope | NEW BEHAVIOR or NO IMPACT |
| Docs, config, formatting, README, comments-only | NO IMPACT |

For files that match no spec scope and are not obviously docs/config, read the diff to determine:
- **NEW BEHAVIOR**: The diff adds observable functionality (new routes, new exports, new CLI commands, new user-facing logic).
- **NO IMPACT**: Internal refactors, renames, comment changes, dependency bumps, formatting.

## Step 5 — Group and Summarize

Group classified files by category, then by feature/topic. For each group, write a **plain-English one-line summary** of what changed — not file paths, not commit hashes. Include the files list indented below.

## Step 6 — Add Directives

Each category has a standard directive:

| Category | Directive |
|----------|-----------|
| NEW BEHAVIOR | `→ Run: purlin:spec <suggested_name>` |
| CHANGED BEHAVIOR | `→ Review: purlin:find <spec_name>` (spec may need rule updates) |
| CHANGED SPECS | `→ Run: purlin:unit-test` (proofs may be missing/stale) |
| TESTS ADDED | Show pass/fail count if known, otherwise `→ Run: purlin:unit-test` to verify |
| NO IMPACT | No directive (informational only) |

## Step 7 — Output

Print the full report in this exact format:

```
Since last verification (<anchor_description>):

NEW BEHAVIOR:
  <summary> — <plain English description>
  Files: <file1>, <file2>
  No spec exists.
  → Run: purlin:spec <suggested_name>

CHANGED BEHAVIOR:
  <spec_name> — <plain English description of change>
  Files: <file1>, <file2>
  Spec exists: specs/<category>/<name>.md (RULE-N may need updating)
  → Review: purlin:find <spec_name>

CHANGED SPECS:
  <spec_name> — <what changed in the spec>
  Files: specs/<category>/<name>.md
  → Run: purlin:unit-test

TESTS ADDED:
  <spec_name> — <N> new tests, <pass/fail summary>
  Files: <test_file1>, <test_file2>

NO IMPACT:
  <description>
  Files: <file1>, <file2>
```

Omit any category section that has no entries. Do not print empty sections.

## Guidelines

- **Write for a PM, not a developer.** Summarize behavior, not implementation. "Login now rate-limits after 10 attempts" not "changed RATE_LIMIT constant in auth.js".
- **One line per logical change.** Group related files under a single summary line.
- **Always cross-reference specs.** If a code change touches a specced scope, name the spec.
- **Be conservative with NEW BEHAVIOR.** Only flag genuinely new user-facing functionality. Internal helpers, utilities, and refactors are NO IMPACT.
- **No writes.** This skill reads git and specs. It does not modify anything.
