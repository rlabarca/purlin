# Implementation Notes: pl_infeasible

## Summary

The `/pl-infeasible` skill is an agent instruction file (`.claude/commands/pl-infeasible.md`) that guides Engineer mode through the INFEASIBLE escalation workflow. Since it is a Markdown skill (not executable code), tests verify structural properties of the file content.

## Bug Fix: CRITICAL Priority Designation

**[CLARIFICATION]** The spec (Section 1 Overview and Scenario 4) requires that `status.sh` surfaces the INFEASIBLE entry as a "CRITICAL-priority PM action item." The skill file originally said only "surface the INFEASIBLE entry in the Critic report for PM mode" without mentioning CRITICAL priority. Updated step 4 to explicitly include "CRITICAL-priority" in the instruction text. Added a corresponding structural test (`test_critical_priority_designation`) to prevent regression. (Severity: INFO)

## Test Coverage

- 14 structural tests across 4 scenario classes (up from 13)
- New test `test_critical_priority_designation` verifies the CRITICAL keyword is present in the skill file
