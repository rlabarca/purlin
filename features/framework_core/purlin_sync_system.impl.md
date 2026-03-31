# Companion: Purlin Sync System

> Format-Version: 1
> Feature: purlin_sync_system.md

## Implementation Notes

**[IMPL]** Expanded `agents/purlin.md` §2.0 Vocabulary from 5 definitions to a structured glossary covering ~30 core Purlin concepts organized by domain: file buckets, write enforcement, feature anatomy, companion/sidecar files, deviation tags, QA discovery tags, constraint files, sync tracking, testing, pipeline delivery, and key directories. A fresh agent now has all critical vocabulary loaded at startup without needing to read docs/.

**[IMPL]** Folded sub-agent constraint table into `agents/purlin.md` §9 Pipeline Delivery Protocol. Constraints (which steps to run, what not to write, commit format) previously only lived in individual agent files. Now the authoritative rules are in the main agent definition.

**[IMPL]** Removed duplicated content from `agents/purlin.md`: §3.1 (sync how-it-works), §3.2 (file classification/write guard), §3.3 (companion convention) were all restating §2.0 Vocabulary definitions. Collapsed §3 to a 2-line pointer. Merged §7+§8 (lifecycle + testing) into one section. Merged §9+§10+§11 (layered instructions, toolbox, visual specs) into §8 "Other Conventions". Renumbered §9-§12. Net reduction: ~39 lines (280 → 241).

**[IMPL]** Slimmed `engineer-worker.md`, `pm-worker.md`, `qa-worker.md`, and `verification-runner.md` to frontmatter stubs referencing §12. Frontmatter preserved for Agent tool registry. Body text reduced from ~30 lines to 1 line each, pointing to the single source of truth.

**[IMPL]** Restructured constraint file documentation. Created `docs/constraints-guide.md` as the single reference for how constraints flow through the build process (purlin_constraints tool, enforcement points, cascade behavior, FORBIDDEN patterns). Slimmed purlin.md §2.0 Constraint Files from 9 lines to 4 — definitions only, detail deferred to constraints guide. Updated `knowledge_colocation.md` spec to require 5 anchor prefixes (was 3) and invariant mention.

**[IMPL]** Added `get_feature_constraints()` to `graph_engine.py` — walks the transitive prerequisite tree via BFS and returns all connected ancestors, anchors, scoped invariants, and global invariants in one call. Exposed as `purlin_constraints` MCP tool in `purlin_server.py`. CLI: `python3 scripts/mcp/graph_engine.py constraints <feature_stem>`.

**[IMPL]** Refactored build SKILL.md Step 0: replaced manual "Constraint File Mandate" + separate "Anchor Review" + "Invariant Preflight" (steps 1-2) with single "Constraint Collection (MANDATORY)" bullet that calls `purlin_constraints`. FORBIDDEN pre-scan, behavioral reminders, and Figma staleness checks remain as separate bullets consuming the collection output. Prerequisite Stability simplified to reference ancestors from the collection.

**[IMPL]** User-in-the-loop reclassification: closed the escape hatch where agents could self-reclassify files as OTHER to bypass `purlin:build`. Three-layer defense: (1) write-guard error messages no longer suggest `purlin:classify add` as an alternative, (2) agent protocol explicitly prohibits self-reclassification, (3) `purlin:classify add` now requires explicit user confirmation via `AskUserQuestion` (which cannot be auto-approved even in YOLO mode). Added `assert_blocked_without_message` test helper to verify the escape hatch is removed. Tests remain classified as CODE — intentional friction ensures test changes are tracked against features. (Severity: INFO)

**[IMPL]** Hardened reclassification bypass prevention. Added hard gate to `purlin:classify add` that structurally refuses to reclassify CODE, SPEC, or INVARIANT files as OTHER — no user override path exists. Updated write-guard block messages for CODE, SPEC, and INVARIANT files to explicitly warn "Do NOT reclassify this file via purlin:classify — TYPE files cannot be added to write_exceptions." Added bypass prevention test assertions (Section 3 now verifies anti-reclassify warnings are present, not just that classify isn't suggested). Added `self-reclassify-after-block` adversarial scenario to agent skill routing tests covering the exact failure mode where an agent autonomously pivots to reclassification after being blocked. Updated regression JSON with new assertions. This closes the loophole where the prior defense (user confirmation + message omission) was insufficient because agents have independent knowledge of the classify skill from system context.

## Code Files
- agents/purlin.md
- agents/engineer-worker.md
- agents/pm-worker.md
- agents/qa-worker.md
- agents/verification-runner.md
- scripts/mcp/graph_engine.py
- scripts/mcp/purlin_server.py
- skills/build/SKILL.md
- skills/classify/SKILL.md
- hooks/scripts/write-guard.sh
- tests/purlin_sync_system/test_write_guard.sh
- tests/purlin_sync_system/test_write_guard_bypass_prevention.sh
- tests/purlin_sync_system/test_agent_skill_routing.sh
- tests/qa/scenarios/purlin_sync_system.json
- references/file_classification.md
