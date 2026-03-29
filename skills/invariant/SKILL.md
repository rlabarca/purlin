---
name: invariant
description: This skill activates PM mode for write operations (add, add-figma, sync, remove). Read-only subcommands (check-update...
---

> **Invariant format:** See `${CLAUDE_PLUGIN_ROOT}/references/invariant_format.md` for the canonical format.
> **Invariant model:** See `${CLAUDE_PLUGIN_ROOT}/references/invariant_model.md` for identification, scope, and cascade rules.

## Usage

```
purlin:invariant <subcommand> [args]
```

| Subcommand | Mode | Description |
|------------|------|-------------|
| `add <repo-url> [file-path]` | PM | Import an invariant from an external git repo |
| `add-figma <figma-url> [existing-anchor]` | PM | Create a Figma-sourced design invariant |
| `sync [file-name \| --all]` | PM | Pull latest version from source (git or Figma) |
| `check-updates` | Any | Check all invariants for new versions (fast, no clone) |
| `check-conflicts` | Any | Detect invariant-to-invariant and invariant-to-anchor conflicts |
| `check-feature <feature> [--all]` | Any | Check feature adherence to applicable invariants |
| `validate` | Any | Validate all invariant files for correct format and metadata |
| `list` | Any | List all active invariants with version, scope, sync status |
| `remove <file-name>` | PM | Remove an invariant from the project |

If no subcommand is provided, print the usage table above and stop.

---

## Mode Enforcement

- **Write subcommands** (`add`, `add-figma`, `sync`, `remove`): Require PM mode. If the current mode is not PM, prompt: `"This subcommand modifies invariant files. Switch to PM mode?"` Do not proceed without PM mode active.
- **Read-only subcommands** (`check-updates`, `check-conflicts`, `check-feature`, `validate`, `list`): Run in any active mode. No mode switch required.

---

## Subcommand: `add <repo-url> [file-path]`

Import an invariant from an external git repo.

1. **Shallow clone** the external repo to a temp directory (depth 1).
2. **Locate the target file:**
   - If `file-path` is provided, use that path within the clone.
   - If not, scan the clone's `features/` directory for anchor files and present a list for the user to choose.
3. **Validate format:** Check for required sections (`## Purpose`, `## * Invariants` or prodbrief sections) and `> Version:` metadata. If validation fails, report issues and stop.
4. **Scope prompt:** If `> Scope:` is missing, ask PM to choose:
   ```
   Scope for this invariant?
     1. global — auto-applies to every non-anchor feature
     2. scoped — features must explicitly declare Prerequisite
   ```
5. **Inject/verify metadata:** Ensure these metadata lines are present (inject if missing, verify if present):
   - `> Invariant: true`
   - `> Source: <repo-url>`
   - `> Source-Path: <path-within-repo>`
   - `> Source-SHA: <git-commit-sha>`
   - `> Synced-At: <ISO-8601-timestamp>`
   - `> Format-Version: 1.0` (if not already present)
6. **Copy to `features/_invariants/`** with `i_` prefix prepended to the filename. If the source file is `policy_security.md`, the local file becomes `features/_invariants/i_policy_security.md`. Create the `_invariants/` folder if it doesn't exist. If `features/_invariants/i_<name>.md` already exists, stop with: "Invariant file already exists at `features/_invariants/i_<name>.md`. Use `purlin:invariant sync` to update an existing invariant."
7. **Commit** with tag: `invariant-add(features/_invariants/i_<type>_<name>.md): v<version> from <repo>`.
8. **Run scan:** Run `purlin_scan` to integrate into dependency graph and trigger cascade if global.
9. **Clean up** the shallow clone.

---

## Subcommand: `add-figma <figma-url> [existing-anchor]`

Create a Figma-sourced design invariant. **Requires Figma MCP** -- no fallback.

1. **Verify Figma MCP** is available (check for `get_design_context` or Figma-related tools in available tool list). If not available:
   ```
   Figma MCP is not available. To set up:
   1. Run: claude mcp add figma -- npx figma-developer-mcp --stdio
   2. Restart the session
   ```
   Stop -- do not proceed without MCP.
2. **Fetch Figma metadata** via MCP: version ID, last modified, design variables.
3. **Extract annotations** via `get_design_context`: behavioral notes, interaction descriptions, edge cases.
4. **Prompt PM** for the invariant name and Purpose section content.
5. **Create pointer file** `features/_invariants/i_design_<name>.md` with:
   ```markdown
   # Design: <Name>

   > Label: "Design: <Name>"
   > Category: "<Category>"
   > Format-Version: 1.0
   > Invariant: true
   > Version: <figma-version-id>
   > Source: figma
   > Figma-URL: <figma-url>
   > Synced-At: <ISO-8601-timestamp>
   > Scope: <global | scoped>

   ## Purpose

   <PM-provided purpose text>

   ## Figma Source

   This invariant is governed by the Figma document linked above.
   Design tokens, constraints, and visual standards are defined in Figma
   and cached locally in per-feature `brief.json` files during spec authoring.

   ## Annotations

   <Extracted behavioral notes, marked as advisory>
   ```
6. **Anchor upgrade** (if `existing-anchor` provided):
   - Resolve the existing anchor via `features/**/<existing-anchor>` and verify it is a `design_*.md` file.
   - Find all feature files with `> Prerequisite: <existing-anchor>` or `> **Design Anchor:** <existing-anchor>`.
   - Update those references to point to `i_design_<name>.md`.
   - Delete the old anchor file.
7. **Commit** with tag: `invariant-add(features/_invariants/i_design_<name>.md): Figma-sourced`.
8. **Run scan:** Run `purlin_scan` to cascade-reset dependent features.

---

## Subcommand: `sync [file-name | --all]`

Pull latest version from source.

- If `file-name` is provided, sync that single invariant.
- If `--all`, sync all `i_*` files in `features/_invariants/`.
- If neither, list invariants and ask which to sync.

### Git-sourced invariants

1. **Read local metadata:** Extract `> Source:`, `> Source-Path:`, `> Source-SHA:`, `> Version:` from the local file.
2. **Shallow clone** the source repo (depth 1).
3. **Compare:** Read the source file, compare version and content against local.
4. **If unchanged:** Report `"<file> is already current (v<version>)."` and stop.
5. **If changed:**
   - Show the diff between local and source.
   - Report version delta: PATCH (informational), MINOR (cascade with warning), MAJOR (full cascade -- flag prominently).
   - Present cascade impact: list features that will reset to `[TODO]`.
6. **On confirmation:** Overwrite local file, update embedded metadata (`> Version:`, `> Source-SHA:`, `> Synced-At:`).
7. **Commit** with tag: `invariant-sync(features/_invariants/i_<name>.md): v<old> -> v<new>`.
8. **Run scan:** Run `purlin_scan` to trigger cascade (semver-gated per `${CLAUDE_PLUGIN_ROOT}/references/invariant_model.md`):
   - MAJOR bump: full cascade.
   - MINOR bump: cascade with warning.
   - PATCH bump: no cascade (informational only).

### Figma-sourced invariants

1. **Verify Figma MCP** is available. If not, report and stop.
2. **Fetch current** Figma file metadata via MCP.
3. **Compare** `figma_version_id` against stored `> Version:`.
4. **If unchanged:** Report already current and stop.
5. **If changed:**
   - Update `> Version:` and `> Synced-At:` in the pointer file.
   - Re-extract annotations, update the `## Annotations` section.
   - Flag affected features' `brief.json` as potentially stale.
6. **Commit and cascade** same as git-sourced.

---

## Subcommand: `check-updates`

Check all invariants for new versions. Fast -- no clone.

For each `i_*` file in `features/_invariants/`:
- **Git-sourced:** Run `git ls-remote <source-url> HEAD` to get remote HEAD SHA. Compare against local `> Source-SHA:`. If different: `"Update may be available: <file> (local: <sha-short>, remote: <sha-short>)"`.
- **Figma-sourced:** If Figma MCP available, fetch file version ID. Compare against stored `> Version:`. If different: `"Figma updated: <file>"`. If MCP not available: `"Skipped (no Figma MCP): <file>"`.
- **Report summary:** `N invariants checked, M have updates available.`

---

## Subcommand: `check-conflicts`

Agent-driven semantic analysis of invariant statements.

1. **Group** all invariants by anchor type prefix (after stripping `i_`).
2. **Extract statements:** For each invariant, extract bullets under `## * Invariants` sections. For prodbrief invariants, extract user stories and success criteria.
3. **Extract local anchors:** Also read local anchors of matching types for comparison.
4. **Analyze** for contradictions:
   - **Invariant-to-invariant:** Two invariants of the same type making contradictory claims.
   - **Invariant-to-anchor:** A local anchor's constraints contradicting an imported invariant.
5. **Report** conflicts with severity and specific contradicting statements:
   ```
   CONFLICT: i_arch_api_standards.md INV-3 vs i_arch_data_contracts.md INV-7
     Severity: HIGH
     Statement A: "All API responses MUST use camelCase keys"
     Statement B: "Database-backed endpoints MUST use snake_case in response bodies"
     Resolution: Clarify scope boundaries or update one invariant at source
   ```
   If no conflicts found: `"No conflicts detected across N invariants and M local anchors."`

---

## Subcommand: `check-feature <feature> [--all]`

Check feature adherence to applicable invariants.

- If `<feature>` is provided, check that single feature.
- If `--all`, check all non-anchor features.

### Per-feature check

1. **Determine applicable invariants:**
   - All global invariants (from `dependency_graph.json` -> `global_invariants`).
   - All scoped invariants in the feature's transitive prerequisite chain.
2. **For each applicable invariant:**
   - **FORBIDDEN patterns:** Grep the feature's code files for pattern matches. Report violations with file:line evidence.
   - **Invariant statement coverage:** Check if the feature's spec and implementation address each constraint. Report gaps.
   - **Token Map validation** (design invariants): Verify Token Map values match the invariant's token definitions.
3. **Report** per-feature, per-invariant, per-constraint compliance:
   ```
   Feature: user_auth.md
     i_policy_security.md (global):
       INV-1 (session tokens encrypted): PASS — covered by scenario "Verify token encryption"
       INV-3 (no eval in user code): VIOLATION — tools/auth/handler.py:42 matches eval\(
     i_arch_api_standards.md (scoped):
       INV-2 (structured error responses): PASS — implemented in error_handler.py
   ```

### Performance (P5)

When `--all` is used, invert the check: iterate over patterns (O(patterns)) rather than features x patterns. Compile FORBIDDEN patterns into combined regex per scope glob (P1).

---

## Subcommand: `validate`

Validate all `i_*` files in `features/_invariants/` for format compliance.

For each `i_*` file in `features/_invariants/`:
1. **Required metadata:** Check for `> Format-Version:`, `> Invariant: true`, `> Version:`, `> Source:`, `> Scope:`.
2. **Format version compatibility:** Warn if file's format version exceeds Purlin's supported version (currently `1.0`).
3. **Required sections per type:**
   - arch/policy/ops/design: `## Purpose` + `## * Invariants`
   - prodbrief: `## Purpose` + `## User Stories` + `## Success Criteria`
4. **Type prefix:** After stripping `i_`, verify the remaining prefix is one of: `arch_`, `design_`, `policy_`, `ops_`, `prodbrief_`.
5. **Report** issues per file:
   ```
   Validating 5 invariant files...

   i_policy_security.md: PASS
   i_arch_api_standards.md: FAIL
     - Missing required metadata: > Scope:
   i_prodbrief_q2.md: PASS
   i_design_visual.md: WARN
     - Format-Version 2.0 exceeds supported version 1.0

   Result: 3 passed, 1 failed, 1 warning
   ```

---

## Subcommand: `list`

List all active invariants.

Glob `features/_invariants/i_*.md` and read metadata from each file. Display:

```
INVARIANTS (N total: M global, K scoped)

File                               Type       Version  Scope   Source
-----------------------------------  ---------  -------  ------  ------
i_policy_security.md               policy     v2.1.0   global  git
i_arch_api_standards.md            arch       v1.0.0   scoped  git
i_design_visual_standards.md       design     v456     scoped  figma
i_ops_monitoring.md                ops        v1.2.0   global  git
i_prodbrief_q2_goals.md            prodbrief  v1.0.0   scoped  git
```

---

## Subcommand: `remove <file-name>`

Remove an invariant from the project. Requires PM mode.

1. **Verify** `features/_invariants/<file-name>` exists and starts with `i_`.
2. **Find dependents:** Grep all feature files for `> Prerequisite: features/_invariants/<file-name>`.
3. **Show impact:** List dependent features and ask for confirmation.
4. **On confirmation:**
   - Remove the `> Prerequisite:` lines from dependent feature files.
   - Delete `features/_invariants/<file-name>`.
5. **Commit** with message: `pm(invariant): remove <file-name>`.
6. **Run scan:** Run `purlin_scan` to update dependency graph.
