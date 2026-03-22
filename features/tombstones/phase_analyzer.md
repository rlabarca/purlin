# TOMBSTONE: phase_analyzer

**Retired:** 2026-03-22
**Reason:** phase_analyzer.py is replaced by agent-native execution group logic in `/pl-build` and `/pl-delivery-plan` skills. The interactive Builder reads `dependency_graph.json` directly -- the external Python tool is unnecessary indirection.

## Files to Delete

- `tools/delivery/phase_analyzer.py` -- entire file (838 lines)
- `tools/delivery/test_phase_analyzer.py` -- test file for the retired tool
- `tests/phase_analyzer/tests.json` -- test results for the retired tool

## Dependencies to Check

- `features/subagent_parallel_builder.md` -- had `> Prerequisite: features/phase_analyzer.md` (already removed by Architect)
- `.claude/commands/pl-build.md` -- referenced `phase_analyzer.py --intra-phase` (already updated by Architect)
- `.claude/commands/pl-delivery-plan.md` -- referenced `phase_analyzer.py` for validation (already updated by Architect)
- `instructions/references/phased_delivery.md` -- referenced `phase_analyzer.py` (already updated by Architect)

## Context

The phase analyzer was built for the now-deprecated `--continuous` bash orchestration mode. That mode needed an external Python tool because the bash script couldn't reason about dependencies. The interactive Builder agent can read `dependency_graph.json` directly and reason about feature independence. The analysis logic has been folded into the `/pl-build` and `/pl-delivery-plan` skills as "execution groups" -- a combined phasing + parallelization model that replaces both inter-phase grouping and intra-phase independence analysis with agent-native reasoning.
