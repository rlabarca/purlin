# Feature: skill_anchor

> Scope: skills/anchor/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:anchor` skill creates, syncs, and manages anchor specs — cross-cutting constraints with optional external references. Anchors define shared rules that other features reference via `> Requires:`.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `anchor`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: An anchor written with only Part 1 (authoring) fields — no `> Source:`, `> Path:`, or `> Pinned:` — is parsed as a local anchor: `source_url` is None, no staleness checks run, and sync_status output contains no Source/Pinned lines for that anchor
- RULE-6: An anchor with Part 2 tracking fields (`> Source:`, `> Path:`, `> Pinned:`) added is parsed as externally-referenced: `source_url`, `pinned`, and `source_path` are all populated, and sync_status output shows Source/Path/Pinned lines for that anchor
- RULE-7: Adding Part 2 tracking fields to a Part 1-only anchor transitions it from local to externally-referenced — the same anchor file, before and after adding `> Source:` and `> Pinned:`, produces different `_scan_specs` results for `source_url` and `pinned`

## Proof

- PROOF-1 (RULE-1): Grep `skills/anchor/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/anchor/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `anchor`
- PROOF-4 (RULE-4): Grep `skills/anchor/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): e2e: Create anchor with only Part 1 fields (Description, Type, rules, proofs — no Source/Path/Pinned); call _scan_specs; verify source_url is None and pinned is None. Run sync_status; verify output does NOT contain "Source:" or "Pinned:" for that anchor @e2e
- PROOF-6 (RULE-6): e2e: Create anchor with Part 1 fields plus Part 2 tracking fields (Source, Path, Pinned pointing to a local bare git repo); call _scan_specs; verify source_url, pinned, and source_path are all populated with correct values. Run sync_status; verify output contains "Source:", "Path:", and "Pinned:" lines @e2e
- PROOF-7 (RULE-7): e2e: Create a Part 1-only anchor; call _scan_specs and capture source_url (None). Then add Part 2 fields to the same file; call _scan_specs again; verify source_url is now populated and pinned matches the written value @e2e
