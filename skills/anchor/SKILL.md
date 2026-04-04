---
name: anchor
description: Create and manage anchor specs — cross-cutting constraints with optional external references
---

# purlin:anchor

Create, sync, and manage anchor specs. Anchors define cross-cutting constraints that other features reference via `> Requires:`.

See `references/formats/anchor_format.md` for the full format.

## Usage

```
purlin:anchor create <name>                    # Create a local anchor
purlin:anchor create <name> --source <url>     # Create with external reference
purlin:anchor add-figma <figma-url>            # Create from Figma design
purlin:anchor sync <name>                      # Pull latest from external source
purlin:anchor sync --check-only                # CI: exit non-zero if any anchor is stale
```

## create

Create a new anchor spec in `specs/_anchors/`.

1. Ask the user what cross-cutting concern this anchor defines.
2. Extract rules from the user's description (same rule-writing process as `purlin:spec`).
3. Write the spec using the anchor format from `references/formats/anchor_format.md`.
4. If `--source <url>` is provided, add `> Source:` and `> Pinned:` metadata and read the external content to inform the rules.
5. Validate all references exist before committing.
6. Commit the anchor spec per `references/commit_conventions.md`.

## add-figma

Create an anchor from a Figma design URL. Read `references/figma_extraction_criteria.md` for the full extraction criteria.

1. Parse the Figma URL to get file key and node ID.
2. Call `get_metadata` MCP tool to get the file info.
3. Call `get_design_context` MCP tool to read the design.
4. Call `get_screenshot` MCP tool to capture the visual reference.
5. Save screenshot to `specs/_anchors/screenshots/`.
6. **Check for responsive variants** — if the design contains multiple frames at different widths (desktop, tablet, mobile), create one visual match rule per viewport and capture one screenshot per variant.
7. **Check for annotations** — look for spec frames, text nodes with behavioral descriptions, component descriptions, and Figma comments. List them in the anchor's "What it does" section as context, and note: "Behavioral requirements from annotations should be added to feature specs that require this anchor."
8. Create a thin anchor with:
   - `> Source:` pointing to the Figma URL
   - `> Visual-Reference: figma://<fileKey>/<nodeId>`
   - `> Pinned:` set to the file's `lastModified` timestamp
   - `> Type: design`
   - One visual match rule per viewport
   - One screenshot comparison proof (using the project's test framework) per rule, all tagged `@e2e`
9. For responsive designs: one rule + proof per viewport size.
10. For theme variants: one rule + proof per theme.
11. Commit per `references/commit_conventions.md`.

Do NOT extract granular CSS/typography/spacing rules. The LLM reads Figma directly during build for full visual fidelity.

## sync

Compare `> Pinned:` value to the upstream source. Pull if different.

### Git-sourced

1. Read `> Source:` to get repo URL and `> Path:` to get file path.
2. Read `> Pinned:` to get the current SHA.
3. Fetch the remote HEAD SHA: `git ls-remote <repo> HEAD`.
4. If SHAs differ:
   a. Fetch the new content and update the anchor file's external reference data.
   b. Update `> Pinned:` with the new SHA.
   c. If the anchor has local rules (rules not from the original sync), flag: "External reference changed. This anchor has N local rules — review for conflicts via purlin:drift."
   d. Commit per `references/commit_conventions.md`: `anchor(<name>): sync from upstream (<new-sha>[:7])`

### Figma-sourced

1. Read `> Source:` to get the Figma URL.
2. Read `> Pinned:` to get the current timestamp.
3. Call `get_metadata` MCP tool with the Figma file key to get `lastModified`.
4. If timestamps differ:
   a. Call `get_design_context` to fetch the current design data.
   b. Update the anchor file with refreshed visual data.
   c. Update `> Pinned:` with the new timestamp.
   d. If `> Visual-Reference:` exists, call `get_screenshot` to recapture the reference screenshot.
   e. If local rules exist, flag for drift review.
   f. Commit.

### Error handling

If any fetch command fails (auth error, network timeout, repo not found, Figma MCP error):
1. Report the exact error to the user.
2. Do NOT update `> Pinned:` or the anchor content.
3. Suggest: "Check your credentials and network, then retry `purlin:anchor sync <name>`."

If the fetched content is empty or unparseable:
1. Report the issue.
2. Do NOT overwrite the existing anchor content.
3. Suggest: "The upstream file may have been reformatted. Check the source."

### --check-only

For CI pipelines without Claude Code:
1. For each anchor with `> Source:`, compare `> Pinned:` to the remote HEAD.
2. If any are stale, exit non-zero with a list of stale anchors.
3. If all are current, exit 0.

CI scripting example (without Claude Code):
```bash
# Check if anchor's external ref is stale
PINNED=$(grep '> Pinned:' specs/_anchors/api_contract.md | awk '{print $3}')
REMOTE=$(git ls-remote git@github.com:acme/api-spec.git HEAD | cut -f1)
if [ "$PINNED" != "$REMOTE" ]; then echo "Anchor stale"; exit 1; fi
```
