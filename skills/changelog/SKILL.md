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

## Step 2 — Analyze and Classify Each Change

For each file in the changelog MCP output, the agent must perform the following analysis. Do not summarize multiple files into one paragraph — analyze each change individually, then group by logical change.

### 2a — Read the actual diff

The MCP tool tells you WHICH files changed. You need to understand WHAT the changes mean. For every file categorized as CHANGED_BEHAVIOR or NEW_BEHAVIOR, read the git diff for that file:

```bash
git diff <since_ref> -- <file_path>
```

Use the `since` field from the MCP output to determine the ref. Do not skip this step — the MCP tool's `category` and `diff_stat` are mechanical classifications, not semantic understanding.

### 2b — Classify the significance

For each changed file, assign a significance level based on the diff content (not just the MCP category):

| Significance | Meaning | Who cares |
|-------------|---------|-----------|
| **BEHAVIORAL** | Changes what the software does — new features, changed rules, removed capabilities | PM, Engineer, QA |
| **STRUCTURAL** | Changes how the software is organized — refactors, renames, file moves, dependency updates | Engineer |
| **OPERATIONAL** | Changes how the software runs — CI config, deployment, env vars, Dockerfiles, Makefiles | Engineer, QA |
| **DOCUMENTATION** | Changes to docs, comments, READMEs, guides | PM (if user-facing), otherwise no one |
| **TRIVIAL** | Formatting, whitespace, typo fixes, auto-generated files | No one |

The MCP tool's NO_IMPACT category maps roughly to DOCUMENTATION and TRIVIAL, but many files classified as CHANGED_BEHAVIOR might actually be STRUCTURAL (a refactor that doesn't change behavior) or OPERATIONAL (a Makefile change). The diff tells you which.

### 2c — Write individual change descriptions

For BEHAVIORAL and OPERATIONAL changes, write one entry per **logical change** — not one entry per file, and not one paragraph for all files.

A "logical change" is a set of related files that implement one thing:
- 3 skill files all adding the same guardrail pattern → one entry describing the guardrail
- A Makefile + Dockerfile + CI config all changing the build → one entry describing the build change
- One skill adding a completely new workflow step → its own entry

Each entry must include:
- **What changed** in plain English (PM-readable)
- **Why it matters** — what's different for the user/developer/QA
- **Which specs are affected** — and whether existing rules still cover the change or new rules are needed
- **The directive** — what to do about it

### 2d — Flag spec drift

For each BEHAVIORAL change, check: do the existing spec rules cover this new behavior?

- If the spec has rules that still match → `Spec up to date ✓`
- If the spec exists but the new behavior isn't covered by any rule → `⚠ Spec may need new rules → update the spec for <feature>`
- If no spec exists → `No spec exists → Run: purlin:spec <name>`

Do not say "6/6 proved" if the code just added behavior that isn't in any of those 6 rules. The proof count was from BEFORE the change. The spec needs review.

**Structural-only coverage check:** When `proof_status` reports a feature as `structural_only: true`, include that in the spec status line:

```
Spec: purlin_agent (8 rules, READY — structural only)
⚠ All proofs are grep checks. No E2E test verifies the agent actually follows the new behavior.
→ Run: purlin:spec purlin_agent (to add behavioral proofs)
```

A feature that is READY but structural-only AND appeared in NEEDS ATTENTION means the proofs don't actually test the changed behavior — they only verify the instruction text exists.

### 2e — Format by audience

Group the entries by significance, not by MCP category:

```
NEEDS ATTENTION:
  <logical change title>
    What: <plain English description of the change>
    Files: <file1>, <file2>, <file3>
    Spec: <spec_name> (<N> rules) — <spec drift status from 2d>
    → <directive>

  <logical change title>
    What: <plain English description>
    Files: <file1>
    Spec: none — <reason no spec needed, or directive to create one>
    → <directive>

FOR AWARENESS:
  <description>
    Files: <file1>, <file2>
    No spec impact.

  <description>
    Files: <file1>
    No spec impact.

TRIVIAL:
  (nothing this cycle)
```

**NEEDS ATTENTION** includes all BEHAVIORAL and OPERATIONAL changes — anything that affects what the software does or how it runs. **FOR AWARENESS** includes STRUCTURAL and DOCUMENTATION changes. **TRIVIAL** includes formatting and whitespace. Omit empty sections.

## Step 3 — Format Output

Print the report header, then the grouped entries from Step 2e.

```
Since <since field from JSON>:

<NEEDS ATTENTION section from 2e>

<FOR AWARENESS section from 2e>

<TRIVIAL section from 2e>
```

## Step 4 — ACTION ITEMS

After all sections, print a `---` separator and role-aware action items. These MUST reference the actual analysis from Step 2, not just the raw proof counts from the MCP tool. List ALL actionable items for each role — do not truncate. When the agent sees "handle PM items" it needs the complete list.

### PM action items (ordered)

List every item that applies, in this order:

1. **Missing specs** — BEHAVIORAL changes with no spec → `→ Run: purlin:spec <name>`
2. **Spec drift** — BEHAVIORAL changes where existing spec rules don't cover the new behavior → `→ Run: purlin:spec <name>`
3. **Unproved new rules** — changed specs with `new_rules` that lack proofs → `→ Run: test <name>`

### Engineer action items (ordered)

List every item that applies, in this order:

1. **Failing tests** — features with `status: "FAILING"` in `proof_status` → `→ Run: test <name>`
2. **Unproved rules** — features with `status: "partial"` → `→ Run: test <name>`
3. **New unspecced code** — BEHAVIORAL changes with no spec → `→ Run: purlin:spec <name>`

### QA action items (ordered)

List every item that applies, in this order:

1. **Stale manual proofs** — features with stale manual stamps → `→ Run: purlin:verify --manual <feature> <PROOF-N>`
2. **Features ready for verification** — features with `status: "READY"` → `→ Run: purlin:verify`
3. **Coverage gaps** — features with `status: "partial"` → `→ Run: test <name>`

### Consistency check

Before emitting ACTION ITEMS, cross-reference against the NEEDS ATTENTION entries:
- If any entry in NEEDS ATTENTION flagged spec drift → that spec MUST appear in PM action items, even if `proof_status` shows all rules proved (the proofs were from before the change)
- If NEEDS ATTENTION says "no missing specs" → PM action items should not list missing specs
- **Structural-only with code changes:** If a feature is READY but `structural_only: true` AND it appeared in NEEDS ATTENTION (code changed), it must appear in PM action items: `Spec drift: <name> — code changed, all proofs are structural only (no behavioral coverage) → Run: purlin:spec <name>`
- Do not contradict the detailed analysis with the summary

### Format

```
---
ACTION ITEMS (PM):
  1. <description> — <action>
  2. <description> — <action>
  ...

ACTION ITEMS (Engineer):
  1. <description> — <action>
  ...

ACTION ITEMS (QA):
  1. <description> — <action>
  ...
```

Omit any role section with no action items.

## Guidelines

- **Read diffs for behavioral changes.** The MCP tool provides the file list; you must read the actual diffs to understand what changed. This is the only additional tool call this skill makes beyond the initial `changelog` MCP call.
- **Write for a PM, not a developer.** Summarize behavior, not implementation details.
- **One entry per logical change.** Group related files under a single entry, but never collapse unrelated changes into one paragraph.
- **Classify from the diff, not the MCP category.** The MCP tool's mechanical classification is a starting point. The diff tells you whether a CHANGED_BEHAVIOR file is actually STRUCTURAL or OPERATIONAL.
- **No writes.** This skill reads and reports. It does not modify anything.
