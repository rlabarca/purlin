---
name: drift
description: Detect spec drift and summarize changes since last verification, cross-referenced with specs
---

This skill writes nothing. It calls the `drift` MCP tool for structured data, then interprets and formats the results into a PM/QA-readable report with actionable directives.

Classification criteria: see `references/drift_criteria.md` (Criteria-Version: N).

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

**Paths in this skill:** every `references/`, `templates/`, `hooks/`, `scripts/` and `agents/` path below is relative to the plugin root; see `${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:drift                            Summarize changes since last verification
purlin:drift [pm|eng|qa]                Summarize with that role's priorities only
purlin:drift --since <N>                Last N commits
purlin:drift --since <date>             Since a date (YYYY-MM-DD)
```

The role is a bare positional argument and there is one spelling of it: `purlin:drift pm`, `purlin:drift eng` or `purlin:drift qa`. Those three tokens are the only ones. The `drift` MCP tool takes no role argument at all; this skill filters its own output by role. If no role is given, show all three priority sections.

### Note on uncommitted changes

Drift detection compares committed git history. Uncommitted changes to specs, code, or proof files are invisible to drift. If sync_status warns about uncommitted changes, commit them first for accurate drift reporting.

## Step 1: Call the drift MCP tool

```
drift(since: <from --since arg if given>)
```

If the tool returns a JSON object with a `recommendation` field instead of the normal drift data, the project has no verification history and too many commits for drift tracking to be useful. Display:

```
No verification anchor found. This project has <commits_since_init> commits without verification history.

→ Use purlin:spec-from-code to generate initial specs from the existing codebase.
→ After specs exist and purlin:verify has run, purlin:drift will track ongoing changes.
```

Do not attempt to process the response as normal drift data. Return immediately after displaying this message.

Otherwise, the tool returns structured JSON containing:
- `since`: human-readable description of the anchor point
- `commits`: list of one-line commit summaries
- `files`: each changed file with `path`, `category` (CHANGED_SPECS, CHANGED_BEHAVIOR, TESTS_ADDED, NEW_BEHAVIOR, NO_IMPACT), `spec` (matched spec name or null), and `diff_stat`
- `spec_changes`: for each changed spec: `new_rules` and `removed_rules`
- `proof_status`: per-feature: `proved`, `total`, `status` (VERIFIED/PASSING/PARTIAL/FAILING/UNTESTED), `failing_rules`
- `drift_flags`: precomputed drift indicators: features with structural-only coverage that have changed files. Each entry has `spec`, `reason`, and `files`.
- `broken_scopes`: specs whose `> Scope:` references files or directories that no longer exist on disk. Each entry has `spec`, `missing_paths`, and `existing_paths`.
- `rule_details`: for each spec with changed behavior files, its `spec_path`, the `changed_files` that landed in its scope, `total_rules`, `proved_rules`, the `unproved` and `failing` rule ids, and `rules`, each a `rule_id` and a `description` cut to 200 characters on a word boundary and suffixed ` ...` when cut. Step 2d reads it.
- `external_anchor_drift`: one entry per anchor carrying a `> Source:`, with `anchor`, `source_url`, `pinned`, `status` (stale, unpinned or error), and `remote_sha` or `error`. The Anchor External Reference Drift step reads it.

The payload is serialized compact, with no indentation and no space after any separator: nobody reads it directly, and this skill is what formats it for a person. Parse it as JSON; never read it line by line.

Deleted files are already filtered out by the tool: only files that exist on disk are included.

## Step 2: Analyze and Classify Each Change

For each file in the drift MCP output, the agent must perform the following analysis. Do not summarize multiple files into one paragraph: analyze each change individually, then group by logical change.

### 2a: Read the actual diff

The MCP tool tells you WHICH files changed. You need to understand WHAT the changes mean. For every file categorized as CHANGED_BEHAVIOR or NEW_BEHAVIOR, read the git diff for that file:

```bash
git diff <since_ref> -- <file_path>
```

Use the `since` field from the MCP output to determine the ref. Do not skip this step: the MCP tool's `category` and `diff_stat` are mechanical classifications, not semantic understanding.

### 2b: Classify the significance

For each changed file, assign a significance level based on the diff content (not just the MCP category).

**CHANGED_SPECS does not imply the code is out of sync.** Every edit under `specs/` classifies
as CHANGED_SPECS, so a project being authored spec-first: where proof descriptions are
iterated deliberately before anything is built: produces that category on every run. Before
describing spec changes as drift, check whether the files named in the spec's `> Scope:` exist.
If they do not, there is no implementation to have drifted from: report the spec work as
progress and point at `purlin:build`, not at a mismatch.

The five levels, what each means, which MCP category it comes from and who cares about it are
listed once, in `references/drift_criteria.md` § Significance Classification. Read that table
rather than a second copy here.

### 2c: Write individual change descriptions

For BEHAVIORAL and OPERATIONAL changes, write one entry per **logical change**: not one entry per file, and not one paragraph for all files.

A "logical change" is a set of related files that implement one thing:
- 3 skill files all adding the same guardrail pattern → one entry describing the guardrail
- A Makefile + Dockerfile + CI config all changing the build → one entry describing the build change
- One skill adding a completely new workflow step → its own entry

Each entry must include:
- **What changed** in plain English (PM-readable)
- **Why it matters**: what's different for the user/developer/QA
- **Which specs are affected**: and whether existing rules still cover the change or new rules are needed
- **The directive**: what to do about it

### 2d: Flag spec drift (rule-level analysis)

For each BEHAVIORAL change, perform **rule-level** analysis using the `rule_details` field from the MCP tool. This field provides, for each spec with changed behavior files: every rule with its description, the `unproved` and `failing` rule ids, the `spec_path` holding the full text, and which scope files changed.

**Step 1: Read the diff and identify changed behavior:**
For each spec in `rule_details`, read the diffs for its `changed_files`. A description ending ` ...` was cut at 200 characters: when the head of it is not enough to judge the rule, open the spec at `spec_path` and read the rule whole. Identify what behavioral aspects changed: new functions, modified conditionals, changed return values, added/removed error handling, new UI sections, changed responsive behavior, etc.

**Step 2: Cross-reference changes against individual rules:**
For each rule in the spec's `rules` array, ask: does this rule's description relate to any of the changed behavior? Classify each rule:

- **Covered**: the rule describes behavior that was NOT changed, or was changed in a way that the rule still holds → `✓ RULE-N: <description>`
- **Potentially stale**: the rule describes behavior that WAS changed and may no longer be accurate → `⚠ RULE-N: <description> (<what changed>)`
- **Unproved**: the rule id is in the spec's `unproved` list regardless of changes → `✗ RULE-N: <description> (no proof)`
- **Missing**: the diff reveals new behavior that NO existing rule covers → `+ Suggested RULE: <description of uncovered behavior>`

**Step 3: Format rule-level findings per spec:**

```
Spec: <name> (<total_rules> rules, <proved_rules> proved)
Changed files: <file1>, <file2>

  ✓ RULE-1: Parse config and return defaults
  ⚠ RULE-2: Return 400 on invalid input (new validation path added for empty arrays)
  ✓ RULE-3: Log warning on retry
  ✗ RULE-4: Rate limit to 100 req/s (no proof exists)
  + Suggested: Batch endpoint accepts up to 50 items (new behavior, no rule)

→ Update spec: purlin:spec <name> (address ⚠ and + items)
→ Write tests: test <name> (address ✗ items)
```

If no rule is potentially stale and no new behavior is uncovered → `Spec up to date ✓`

If no spec exists → `No spec exists → Run: purlin:spec <name>`

**Behavioral gap drift:** Check the `drift_flags` array in the MCP tool output. Each entry identifies a feature with no behavioral proofs whose code changed. For each:

```
Spec: purlin_agent (8 rules, 0 behavioral proofs)
⚠ All proofs are structural checks. Code changed but no behavioral test verifies the new behavior.
→ Run: purlin:spec purlin_agent (add behavioral rules)
```

Also check individual file entries for `behavioral_gap: true`: these are CHANGED_BEHAVIOR files whose spec has only structural checks (no behavioral proofs).

**Broken scopes:** Check the `broken_scopes` array in the MCP tool output. Each entry identifies a spec whose `> Scope:` references a path that no longer exists on disk. For each:

```
Spec: login
⚠ Broken scope: src/auth/old_login.py no longer exists
→ Was it renamed? Run: purlin:rename login (to update scope and references)
→ Was it deleted? Run: purlin:spec login (to update or remove the spec)
```

### Anchor External Reference Drift

Check the `external_anchor_drift` array in the MCP tool output. Each entry has:
- `anchor`: the anchor name
- `source_url`: the external reference URL
- `pinned`: the stored SHA or timestamp
- `status`: one of: `stale` (pinned behind remote HEAD), `unpinned` (no Pinned field), `error` (source unreachable)
- `remote_sha`: the current remote HEAD (when available)
- `error`: error message (when status is error)

For each entry, format as:

- **stale:** `⚠ Anchor <name> is stale: pinned at <pinned[:7]> but remote is at <remote_sha>. Run: purlin:anchor sync <name>`
- **unpinned:** `⚠ Anchor <name> has > Source: but no > Pinned: value. Run: purlin:anchor sync <name> to pin`
- **error:** `✗ Anchor <name>: source unreachable: <error>. Verify URL in specs/_anchors/<name>.md`

When an anchor with `> Source:` has been synced (Pinned changed) and also has local rules, flag as a PM action item:
- "**<anchor_name>**: external reference updated: N local rules may conflict. Review and update or confirm."

### 2e: Format by audience

Group the entries by significance, not by MCP category:

```
NEEDS ATTENTION:
  <logical change title>
    What: <plain English description of the change>
    Files: <file1>, <file2>, <file3>
    Spec: <spec_name> (<N> rules): <spec drift status from 2d>
    → <directive>

  <logical change title>
    What: <plain English description>
    Files: <file1>
    Spec: none: <reason no spec needed, or directive to create one>
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

**NEEDS ATTENTION** carries every BEHAVIORAL and OPERATIONAL change, which is anything that affects what the software does or how it runs. **FOR AWARENESS** carries STRUCTURAL and DOCUMENTATION changes. **TRIVIAL** carries formatting and whitespace. Omit empty sections.

## Step 3: Format Output

Print `Since <since field from JSON>:`, then the grouped entries exactly as Step 2e shapes them. Nothing here reformats or re-derives that block; the shape above is the whole report body.

## Step 4: ACTION ITEMS

After all sections, print a `---` separator and role-aware action items. These MUST reference the actual analysis from Step 2, not just the raw proof counts from the MCP tool. List ALL actionable items for each role: do not truncate. When the agent sees "handle PM items" it needs the complete list.

### PM action items (ordered)

List every item that applies, in this order:

1. **Assumed values**: features with rules tagged `(assumed)` that need PM confirmation → `→ Run: purlin:spec <name>`
2. **Missing specs**: BEHAVIORAL changes with no spec → `→ Run: purlin:spec <name>`
3. **Spec drift**: BEHAVIORAL changes where existing spec rules don't cover the new behavior → `→ Run: purlin:spec <name>`
4. **Unproved new rules**: changed specs with `new_rules` that lack proofs → `→ Run: test <name>`

### Engineer action items (ordered)

List every item that applies, in this order:

1. **Failing tests**: features with `status: "FAILING"` in `proof_status` → `→ Run: test <name>`
2. **Unproved rules**: features with `status: "PARTIAL"` or `"UNTESTED"` → `→ Run: test <name>` (PARTIAL means more tests needed to reach PASSING)
3. **New unspecced code**: BEHAVIORAL changes with no spec → `→ Run: purlin:spec <name>`

### QA action items (ordered)

List every item that applies, in this order:

1. **Stale manual proofs**: features with stale manual stamps → `→ Run: purlin:verify --manual <feature> <PROOF-N>`
2. **Features ready for verification**: features with `status: "PASSING"` (all rules proved, no receipt yet) → `→ Run: purlin:verify`
3. **Coverage gaps**: features with `status: "PARTIAL"` or `"UNTESTED"` → `→ Run: test <name>`

### Consistency check

Before emitting ACTION ITEMS, cross-reference against the NEEDS ATTENTION entries:
- If any entry in NEEDS ATTENTION flagged spec drift → that spec MUST appear in PM action items, even if `proof_status` shows all rules proved (the proofs were from before the change)
- If NEEDS ATTENTION says "no missing specs" → PM action items should not list missing specs
- **Rule-level drift:** Every spec with `⚠` (potentially stale) or `+` (missing) rules from rule_details analysis must appear in PM action items with the specific rules listed: `Spec drift: <name>: RULE-2 may be stale (new validation path), 1 new behavior uncovered → Run: purlin:spec <name>`
- **Behavioral gap drift:** Every entry in `drift_flags` must appear in PM action items: `Spec drift: <name>: code changed, no behavioral proofs (only structural checks) → Run: purlin:spec <name>`
- **Broken scopes:** Every entry in `broken_scopes` must appear in PM action items: `Broken scope: <name>: <path> no longer exists → Run: purlin:rename <name> or purlin:spec <name>`
- Do not contradict the detailed analysis with the summary

### Format

```
---
ACTION ITEMS (PM):
  1. <description>: <action>
  2. <description>: <action>
  ...

ACTION ITEMS (Engineer):
  1. <description>: <action>
  ...

ACTION ITEMS (QA):
  1. <description>: <action>
  ...
```

Omit any role section with no action items.

## Guidelines

- **Read the diffs (Step 2a).** The MCP tool gives the file list and a mechanical category; the `git diff` is what says whether a CHANGED_BEHAVIOR file is really STRUCTURAL or OPERATIONAL. This is the only tool call this skill makes beyond the initial `drift` call.
- **Write for a PM, not a developer.** Summarize behavior, not implementation details.
- **One entry per logical change.** Group related files under a single entry, but never collapse unrelated changes into one paragraph.
- **No writes.** This skill reads and reports. It does not modify anything.
