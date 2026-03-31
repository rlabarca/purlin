# Companion: Purlin Sync System

> Format-Version: 1
> Feature: purlin_sync_system.md

## Implementation Notes

**[IMPL]** Expanded `agents/purlin.md` §2.0 Vocabulary from 5 definitions to a structured glossary covering ~30 core Purlin concepts organized by domain: file buckets, write enforcement, feature anatomy, companion/sidecar files, deviation tags, QA discovery tags, constraint files, sync tracking, testing, pipeline delivery, and key directories. A fresh agent now has all critical vocabulary loaded at startup without needing to read docs/.

**[IMPL]** Folded sub-agent constraint table into `agents/purlin.md` §12 Pipeline Delivery Protocol. Constraints (which steps to run, what not to write, commit format) previously only lived in individual agent files. Now the authoritative rules are in the main agent definition.

**[IMPL]** Slimmed `engineer-worker.md`, `pm-worker.md`, `qa-worker.md`, and `verification-runner.md` to frontmatter stubs referencing §12. Frontmatter preserved for Agent tool registry. Body text reduced from ~30 lines to 1 line each, pointing to the single source of truth.

## Code Files
- agents/purlin.md
- agents/engineer-worker.md
- agents/pm-worker.md
- agents/qa-worker.md
- agents/verification-runner.md
