---
name: spec-catch-up
description: Update existing specs to match code that was built ahead of spec. Reads sync state, proposes targeted spec changes, auto-creates companion files
---

## Active Skill Marker

Before any file writes, set the active skill marker:

```bash
mkdir -p .purlin/runtime && echo "spec-catch-up" > .purlin/runtime/active_skill
```

After all writes are complete (final commit), clear it:

```bash
rm -f .purlin/runtime/active_skill
```

---

## Required Reading

Before catching up specs, read `${CLAUDE_PLUGIN_ROOT}/references/spec_authoring_guide.md` for shared authoring principles, role focus, and anchor classification guidance. This guide applies to PM.

---

## Purpose

Lightweight spec reconciliation for features where code landed ahead of spec updates. Bridges the gap between `purlin:spec` (forward authoring) and `purlin:spec-from-code` (heavy brownfield import). Reads sync tracking data, identifies what changed in code, proposes targeted spec additions/revisions, and applies them after PM approval.

**This skill writes SPEC and IMPL files only.** It does not modify code or tests.

---

## Argument Parsing

Parse `$ARGUMENTS`:
- **Feature name provided:** `purlin:spec-catch-up <feature_name>` — catch up a specific feature.
- **No argument:** `purlin:spec-catch-up` — discover all `code_ahead` features and offer to catch up each.

---

## Step 0 — Discovery

### 0.1 — Load Sync State

1. Read `.purlin/sync_ledger.json` — persistent per-feature sync status (committed to git).
2. Read `.purlin/runtime/sync_state.json` — session-scoped write tracker (gitignored).
3. Merge: for each feature, session writes overlay ledger. Session changes upgrade `synced` → `code_ahead` if only code changed this session.

### 0.2 — Identify Targets

**If a feature name was provided:**
1. Resolve the feature file via `features/**/<feature_name>.md`.
2. If the file does not exist: abort with `"No spec exists for '<feature_name>'. Use purlin:spec to author a new spec, or purlin:spec-from-code to reverse-engineer from existing code."`
3. Look up the feature in the merged sync state. If the feature is `synced` or `spec_ahead`: warn `"Feature '<feature_name>' is not code-ahead (status: <status>). Proceed anyway?"` — continue only if the user confirms.
4. If the feature has no ledger entry: warn `"Feature '<feature_name>' has no sync tracking data. Proceed with code analysis?"` — continue only if the user confirms.

**If no argument was provided:**
1. Filter the merged sync state for all features with `sync_status: "code_ahead"` or `session_pending: "code_ahead"`.
2. If none found: report `"All features are in sync. No spec catch-up needed."` and exit.
3. Present the list with context:
   ```
   Features with code ahead of spec:

     1. auth_middleware — code 1d ago, spec 8d ago, no impl
     2. webhook_delivery — code 3h ago, spec 2d ago, impl exists
     3. notification_system — code 1d ago, spec 5d ago, no impl

   Catch up all? Or enter a number to catch up one at a time.
   ```
4. Accept: "all", a number, or a feature name. Process selected features sequentially.

---

## Step 1 — Gather Context (per feature)

### 1.1 — Read the Existing Spec

Read `features/<category>/<feature_name>.md`. Extract:
- All requirements (§2 subsections)
- All scenarios (§3 `#### Scenario:` entries with Given/When/Then)
- Metadata (`> Label:`, `> Category:`, `> Prerequisite:`)

### 1.2 — Identify Changed Code Files

Build the list of code files that changed since the spec was last updated:

1. **Session state** (`.purlin/runtime/sync_state.json`): Check `features[stem].code_files` and `features[stem].test_files` for files written this session.
2. **Sync ledger** (`.purlin/sync_ledger.json`): Compare `last_code_commit` vs `last_spec_commit` timestamps. If `last_spec_date` exists, find code files changed after that date:
   ```bash
   git log --name-only --format="" --since="<last_spec_date>" -- <known_code_paths>
   ```
3. **Companion file source mapping**: If `<feature_name>.impl.md` exists, check for `### Source Mapping` entries to identify known implementation files.
4. **Skill-to-feature mapping**: For features matching `purlin_<name>`, also check `skills/<name>/SKILL.md`.

Deduplicate the file list. Cap at 10 primary files (prioritize by recency). If more than 10 files changed, summarize the rest.

### 1.3 — Read the Changed Code

Read each identified code file (up to 10). Extract:
- Public functions, classes, and entry points
- Behavioral changes (new handlers, modified logic, added parameters)
- Error handling and edge cases
- Configuration or environment dependencies

### 1.4 — Read the Companion File (if exists)

If `features/<category>/<feature_name>.impl.md` exists, read it for:
- `[IMPL]` entries documenting what was built
- `[DEVIATION]`, `[AUTONOMOUS]`, `[DISCOVERY]` tags indicating spec divergence
- `### Source Mapping` sections

Companion entries are curated signal — prioritize them over raw code reading.

### 1.5 — Load Applicable Constraints

Call `purlin_constraints` with the feature stem. Read every file listed in `anchors`, `scoped_invariants`, and `global_invariants`. Surface these as advisory context during the proposal (Step 3) — if the code being caught up violates a FORBIDDEN pattern or contradicts a constraint statement, the proposal MUST flag it so PM can decide whether to accept the code as-is, request a code fix, or escalate an invariant conflict.

---

## Step 2 — Analyze Gaps

Compare the existing spec against the code to identify:

### 2.1 — New Requirements

Behavior present in code but absent from the spec's §2 Requirements section:
- New functions or endpoints not covered by any requirement
- New parameters, configuration options, or environment variables
- New error handling paths or validation rules

### 2.2 — Changed Behavior

Existing requirements that no longer match the code:
- Modified function signatures or return values
- Changed validation rules or thresholds
- Updated error messages or status codes

### 2.3 — New Scenarios

Test cases or behavioral paths that exist in code/tests but have no corresponding `#### Scenario:` entry:
- New test functions in `tests/<feature_stem>/`
- Edge cases handled in code with no scenario coverage
- Error paths with explicit handling but no scenario

### 2.4 — Metadata Gaps

- Missing `> Prerequisite:` links for new dependencies introduced in code
- Category or label that no longer fits after code evolution

---

## Step 3 — Propose Changes

Present a structured proposal for PM review. **Do NOT apply any changes yet.**

### Proposal Format

```
## Spec Catch-Up Proposal: <feature_name>

**Sync status:** code_ahead (code: <date>, spec: <date>)
**Code files analyzed:** N files
**Companion entries reviewed:** N entries

---

### New Requirements (additions to §2)

1. **<Subsection>: <Requirement text>**
   Source: `<file>:<function>` — <brief rationale>

### Changed Requirements (revisions to §2)

1. **§2.N <Existing requirement>**
   Current: "<current text>"
   Proposed: "<revised text>"
   Reason: <why the code diverged>

### New Scenarios (additions to §3)

1. **Scenario: <Title>**

       Given <precondition>
       When <action>
       Then <expected outcome>

   Source: `tests/<stem>/test_<name>.sh`

### Metadata Updates

- Add `> Prerequisite: <anchor>.md` (new dependency on <anchor>)

### No Changes Needed

<If any area has no gaps, state explicitly: "Requirements are current — no additions needed.">

---

**Apply these changes?** (yes / edit / skip)
```

### User Response Handling

- **yes**: Proceed to Step 4 (apply all proposed changes).
- **edit**: Ask user which items to modify, remove, or revise. Re-present the updated proposal.
- **skip**: Skip this feature. If processing multiple features, continue to the next.
- **partial**: User specifies which numbered items to apply.

---

## Step 4 — Apply Changes

### 4.1 — Update the Spec

Edit `features/<category>/<feature_name>.md`:
- Insert new requirements into the appropriate §2 subsections. If a new subsection is needed, number it sequentially.
- Revise changed requirements in place, preserving section numbering.
- Append new scenarios to §3 with proper `#### Scenario:` heading and indented Given/When/Then format.
- Update metadata fields as proposed.
- Follow all format rules from `${CLAUDE_PLUGIN_ROOT}/references/formats/feature_format.md`.

### 4.2 — Create or Update Companion File

**If `<feature_name>.impl.md` does not exist**, create it in the same category folder as the spec:

```markdown
# Implementation Notes: <Feature Display Name>

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (none) | (none) | — | — |

### Source Mapping

| Spec Requirement | Source File(s) |
|-----------------|---------------|
| §2.1 <requirement summary> | `<file_path>` |
| §2.2 <requirement summary> | `<file_path>` |

## Notes

**[IMPL]** Spec caught up via purlin:spec-catch-up (<date>). Code files analyzed: <list>.
```

**If the companion file already exists**, append a catch-up summary entry:

```markdown
**[IMPL]** Spec caught up via purlin:spec-catch-up (<date>). Added N requirements, revised M requirements, added K scenarios.
```

Update the Source Mapping section if it exists, or create it if absent.

### 4.3 — Commit and Update Ledger

Commit spec and companion file changes together so the sync ledger records both in the same commit:

```bash
git add features/<category>/<feature_name>.md features/<category>/<feature_name>.impl.md
git commit -m "spec(<feature_stem>): catch up spec to match implementation

Purlin-Mode: PM"
```

After the commit, update the sync ledger explicitly:

```bash
PURLIN_COMMIT_MSG="spec(<feature_stem>): catch up spec to match implementation" bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/sync-ledger-update.sh"
bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/sync-ledger-update.sh" --sha "$(git rev-parse HEAD)"
```

### 4.4 — Verify Sync Resolution

Run `purlin_scan` with `only: "features"` to confirm:
1. The spec passes scan format validation (required sections, scenario format).
2. No new scan findings were introduced.

Then read `.purlin/sync_ledger.json` directly to confirm the feature's sync status resolved to `synced`.

If sync did not resolve, report the remaining drift and suggest follow-up actions.

---

## Step 5 — Summary (multi-feature mode)

When processing multiple features, present a summary:

```
Spec Catch-Up Complete

  Caught up:
    - auth_middleware: +2 requirements, +1 scenario, impl.md created
    - webhook_delivery: +1 requirement, 1 revised, +3 scenarios

  Skipped:
    - notification_system: user skipped

  Sync status:
    - auth_middleware: synced
    - webhook_delivery: synced
    - notification_system: code_ahead (unchanged)
```

---

## Error Cases

| Condition | Behavior |
|-----------|----------|
| Feature not found | Abort, suggest `purlin:spec` or `purlin:spec-from-code` |
| No `code_ahead` features (no-arg mode) | Report "All features in sync" and exit |
| Feature is `synced` or `spec_ahead` | Warn, ask confirmation before proceeding |
| No code files found for feature | Report "No code changes detected. Sync ledger may be stale." and skip |
| Stub spec (no requirements/scenarios) | Warn: "Spec appears to be a stub — consider purlin:spec for full authoring." |
| Companion file exists but has no Source Mapping | Add Source Mapping section during update |
| User declines all proposals | Exit cleanly, no changes made |

---

## Constraints

- **PM-scoped.** Writes spec and companion files only. Does not modify code, tests, or anchor nodes.
- **Always propose first.** Never apply spec changes without explicit approval.
- **Preserve existing spec structure.** New content is additive or surgical revision. Do not reorganize sections, renumber existing requirements, or remove existing scenarios unless the user explicitly approves.
- **Follow scan parser requirements.** All scenarios use `#### Scenario:` headings with indented Given/When/Then. Required sections (Overview, Requirements, Scenarios) must be present.
- **Companion files are Engineer-owned.** This skill creates the structural scaffold (Active Deviations table, Source Mapping, `[IMPL]` entry). Deep implementation documentation is the Engineer's responsibility.
