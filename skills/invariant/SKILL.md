---
name: invariant
description: Sync read-only constraint files from external sources
---

Manage invariant specs — read-only constraint files sourced from git repos or Figma. Invariants live in `specs/_invariants/i_<prefix>_<name>.md`.

**Invariants require an external source.** If the user provides a local image (screenshot, mockup) and asks for an invariant, refuse: "Images are locally owned — use `purlin:spec --anchor` to create a design anchor instead. Invariants sync from external sources (Figma URLs, git repos)."

## Usage

```
purlin:invariant sync [name]        Sync one or all invariants from upstream
purlin:invariant add <repo-url>     Import a git-sourced invariant
purlin:invariant add-figma <url>    Import a Figma-sourced design invariant
purlin:invariant list               List all invariants and their status
purlin:invariant --check-only       CI mode: fail if any invariant is stale (exit 1)
```

## Invariant Format

See `references/formats/invariant_format.md` for the full spec. Key metadata:

```markdown
# Invariant: i_design_tokens

> Source: git@github.com:org/design-system.git#tokens.md
> Path: docs/tokens.md
> Pinned: abc1234 (git SHA) or 2026-03-31T12:00:00Z (Figma timestamp)

## Rules
- RULE-1: All colors must use design token CSS variables
- RULE-2: Font sizes must use rem units
```

Type prefixes: `i_design_`, `i_api_`, `i_security_`, `i_brand_`, `i_platform_`, `i_schema_`, `i_legal_`, `i_prodbrief_`.

## sync

Compare `> Pinned:` value to the upstream source. Pull if different.

### Git-sourced

1. Read `> Source:` to get repo URL and file path.
2. Read `> Pinned:` to get the current SHA.
3. Fetch the remote HEAD SHA for the file: `git ls-remote <repo> HEAD`.
4. If SHAs differ:
   a. Create bypass lock: write `{"target": "i_<name>.md"}` to `.purlin/runtime/invariant_write_lock`.
   b. Fetch the new content and update the invariant file.
   c. Update `> Pinned:` with the new SHA.
   d. Delete the bypass lock.
   e. Commit: `git commit -m "invariant(i_<name>): sync from upstream (<new-sha>[:7])"`

### Figma-sourced

1. Read `> Source:` to get the Figma URL.
2. Read `> Pinned:` to get the current timestamp.
3. Call `get_metadata` MCP tool with the Figma file key to get `lastModified`.
4. If timestamps differ:
   a. Create bypass lock.
   b. Call `get_design_context` to fetch the current design data.
   c. Update the invariant file with new rules extracted from the design.
   d. Update `> Pinned:` with the new timestamp.
   e. If `> Visual-Reference:` exists, call `get_screenshot` to recapture the reference screenshot to `specs/_invariants/screenshots/`.
   f. Delete the bypass lock.
   g. Commit.

## add

Import a new git-sourced invariant.

1. Clone/fetch the repo, read the target file.
2. Extract rules from the content.
3. Create `specs/_invariants/i_<prefix>_<name>.md` with `> Source:`, `> Path:`, `> Pinned:`.
4. Commit.

## add-figma

Import a new Figma-sourced design invariant. Read `references/figma_extraction_criteria.md` for the full extraction criteria.

1. Parse the Figma URL to get file key and node ID.
2. Call `get_metadata` to get frame dimensions and node structure.
3. Call `get_screenshot` to capture the reference screenshot, save to `specs/_invariants/screenshots/i_design_<name>.png`.
4. **Check for responsive variants** — if the design contains multiple frames at different widths (desktop, tablet, mobile), create one visual match rule per viewport and capture one screenshot per variant.
5. **Check for annotations** — look for spec frames, text nodes with behavioral descriptions, component descriptions, and Figma comments. List them in the invariant's "What it does" section as context, and note: "Behavioral requirements from annotations should be added to feature specs that require this invariant."
6. Write the invariant with:
   - `> Visual-Reference: figma://fileKey/nodeId`
   - One visual match rule (or N rules for N viewports)
   - One screenshot comparison proof per rule, all tagged `@e2e`
7. Create `specs/_invariants/i_design_<name>.md` with `> Type: design`, `> Source:`, `> Pinned:`, `> Visual-Reference:`.
8. Commit.

Do NOT extract granular CSS/typography/spacing rules. The LLM reads Figma directly during build for full visual fidelity.

## list

List all invariants with their sync status:

```
Invariants:
  i_design_tokens: pinned=abc1234 (git, 3d ago)
  i_api_contracts: pinned=def5678 (git, 1h ago)
  i_design_nav: pinned=2026-03-30T12:00:00Z (figma)
```

## --check-only (CI)

Run `sync` in dry-run mode. If any invariant has a newer upstream version than its `> Pinned:` value, print the stale invariants and exit 1. Does not modify any files.

## Write Protection

Invariant files (`specs/_invariants/i_*`) are protected by the gate hook (`hooks/hooks.json` → `scripts/gate.sh`). Direct writes are blocked unless a bypass lock exists at `.purlin/runtime/invariant_write_lock` with a matching target. Only this skill creates and removes the bypass lock.
