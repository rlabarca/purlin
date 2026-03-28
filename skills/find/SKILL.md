---
name: find
description: Available to all agents and modes
---

**Purlin command: shared (all roles)**
**Purlin mode: shared**

Available to all agents and modes.

Given the topic or concern provided as an argument, search the spec system and report findings.

## Search Protocol

1. **Feature specs:** Grep `features/*.md` (exclude `features/tombstones/`) for topic keywords. If found, read the matching file and identify the specific section and scenario.
2. **Anchor nodes:** Grep `features/arch_*.md`, `features/design_*.md`, `features/policy_*.md` for the topic. Anchor hits indicate governance-level coverage.
3. **Instruction files:** Grep `instructions/` and `.purlin/PURLIN_OVERRIDES.md` for the topic. Instruction-only hits mean the topic is a process/workflow rule without a feature spec.
4. **Companion files:** Grep `features/*.impl.md` for the topic. Companion hits may reveal implementation decisions or deviations related to the topic.

## Report Format

For each search result, report:
- **File** and **section** where the topic appears
- **Coverage type:** feature spec, anchor node, instruction, or companion

## Recommendation

Based on results, recommend one of:
- **Already covered** — feature spec + scenarios exist; no action needed
- **Spec refinement needed** — coverage exists but is incomplete or vague
- **Anchor node update** — the concern crosses features and belongs in an anchor
- **New spec needed** — no coverage found; suggest creating a feature spec via `purlin:spec`
