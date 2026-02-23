# Feature: Critic Consistency Check & README Update

> Label: "Release Step: Critic Consistency Check & README Update"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md
> Prerequisite: features/policy_critic.md

## 1. Overview

This feature defines the `critic_consistency_check` local release step: a Purlin-repository-specific two-phase audit that (1) cross-references all Critic-related specification and instruction files for inconsistencies in terminology, routing rules, and responsibilities, and (2) writes or updates the `## The Critic` section in README.md. This step is defined in Purlin's `.purlin/release/local_steps.json` and does not appear in consumer project checklists.

## 2. Requirements

### 2.1 Phase 1: Audit Scope

The Architect reads the following files:

- `features/critic_tool.md`
- `features/policy_critic.md`
- `instructions/HOW_WE_WORK_BASE.md` — Section 8
- `instructions/ARCHITECT_BASE.md`
- `instructions/BUILDER_BASE.md`
- `instructions/QA_BASE.md`

### 2.2 Phase 1: Audit Checks

The Architect checks for:

1. **Deprecated terminology.** All files MUST use "coordination engine" — not "quality gate" — when describing the Critic's role.
2. **Routing rule consistency.** Discovery type routing (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE) MUST be consistent across `policy_critic.md`, HOW_WE_WORK_BASE Section 7.5, and `QA_BASE`.
3. **Role status enumeration consistency.** Status labels used in Critic output MUST match those described in HOW_WE_WORK_BASE and role-specific files.
4. **`critic_gate_blocking` described as no-op.** Every file that references `critic_gate_blocking` MUST describe it as a no-op when `false`.
5. **Startup mandate.** All three role files MUST mandate `tools/cdd/status.sh` at session start.
6. **CLI-only agent interface.** All files MUST describe the agent interface as CLI-only (never HTTP).

The Architect produces a findings table with severity: CRITICAL, WARNING, or OK. CRITICAL findings halt the step and the release.

### 2.3 Phase 2: README Update

After a clean Phase 1 (zero CRITICAL findings), the Architect writes or updates the `## The Critic` section in README.md. The section is placed immediately after `## The Agents` and before `## Setup & Configuration`.

The Architect commits with message `docs(readme): update Role of the Critic section`.

### 2.4 Step Metadata

| Field | Value |
|-------|-------|
| ID | `critic_consistency_check` |
| Friendly Name | `Critic Consistency Check & README Update` |
| Scope | Purlin-local (not a global step) |
| Code | null |
| Agent Instructions | See Sections 2.1–2.3 above (two-phase execution). |

## 3. Scenarios

### Automated Scenarios
None. All verification is manual (Architect-executed release step).

### Manual Scenarios (Architect Execution)

#### Scenario: Clean audit — README updated
Given all Critic-related files are consistent with no deprecated terminology, routing conflicts, or missing mandates,
When the Architect executes the `critic_consistency_check` step,
Then the Architect produces a findings table with all items at OK,
And writes or updates the `## The Critic` section in README.md,
And commits with message `docs(readme): update Role of the Critic section`.

#### Scenario: Deprecated "quality gate" terminology found
Given one or more files still use "quality gate" instead of "coordination engine",
When the Architect executes Phase 1 of the `critic_consistency_check` step,
Then the Architect reports the finding as CRITICAL with the specific file and location,
And halts without proceeding to Phase 2 or the next release step.

#### Scenario: Routing rule inconsistency found
Given the SPEC_DISPUTE routing rule differs between `policy_critic.md` and HOW_WE_WORK_BASE Section 7.5,
When the Architect executes Phase 1 of the `critic_consistency_check` step,
Then the Architect reports the specific discrepancy as a CRITICAL finding,
And halts until the inconsistency is resolved and the step is re-run.

#### Scenario: WARNING-level finding does not halt
Given a finding is classified as WARNING (non-critical inconsistency),
When the Architect completes Phase 1,
Then the Architect proceeds to Phase 2 (README update) after reporting the warning,
And notes the warning in the README update commit message.

## Implementation Notes

This step is positioned immediately after `doc_consistency_framework` in Purlin's release config. The broader instruction-file consistency check runs first; this step then focuses narrowly on the Critic subsystem.

Phase 2 (README update) runs only after Phase 1 produces zero CRITICAL findings. A clean audit is a prerequisite for README publication.
