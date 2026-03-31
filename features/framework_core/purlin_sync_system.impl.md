# Companion: Purlin Sync System

> Format-Version: 1
> Feature: purlin_sync_system.md

## Implementation Notes

**[IMPL]** Expanded `agents/purlin.md` §2.0 Vocabulary from 5 definitions to a structured glossary covering ~30 core Purlin concepts organized by domain: file buckets, write enforcement, feature anatomy, companion/sidecar files, deviation tags, QA discovery tags, constraint files, sync tracking, testing, pipeline delivery, and key directories. A fresh agent now has all critical vocabulary loaded at startup without needing to read docs/.

**[IMPL]** Folded sub-agent constraint table into `agents/purlin.md` §9 Pipeline Delivery Protocol. Constraints (which steps to run, what not to write, commit format) previously only lived in individual agent files. Now the authoritative rules are in the main agent definition.

**[IMPL]** Removed duplicated content from `agents/purlin.md`: §3.1 (sync how-it-works), §3.2 (file classification/write guard), §3.3 (companion convention) were all restating §2.0 Vocabulary definitions. Collapsed §3 to a 2-line pointer. Merged §7+§8 (lifecycle + testing) into one section. Merged §9+§10+§11 (layered instructions, toolbox, visual specs) into §8 "Other Conventions". Renumbered §9-§12. Net reduction: ~39 lines (280 → 241).

**[IMPL]** Slimmed `engineer-worker.md`, `pm-worker.md`, `qa-worker.md`, and `verification-runner.md` to frontmatter stubs referencing §12. Frontmatter preserved for Agent tool registry. Body text reduced from ~30 lines to 1 line each, pointing to the single source of truth.

**[IMPL]** Rewrote `agents/purlin.md` §2.0 Vocabulary → Constraint Files subsection. Previously 4 terse one-liners that didn't explain how to find anchors or that builds must read them. Now: explains five anchor prefixes with glob pattern, distinguishes anchors (local) from invariants (external/immutable with `i_` prefix), adds explicit "Build mandate" bullet requiring agents to walk the full prerequisite tree and read every connected anchor/invariant during Step 0. Kept net addition to ~4 lines.

## Code Files
- agents/purlin.md
- agents/engineer-worker.md
- agents/pm-worker.md
- agents/qa-worker.md
- agents/verification-runner.md
