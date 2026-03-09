# Phased Delivery Protocol

> This file is loaded on-demand by `/pl-delivery-plan`, `/pl-build`, and `/pl-verify`
> commands when a delivery plan exists or phased delivery is being considered.

## 10.1 Purpose
When the Architect introduces large-scale changes (multiple new feature files, major revisions across existing features), the Builder may need to split work across multiple sessions to ensure quality and enable incremental verification. The Phased Delivery Protocol provides a persistent coordination artifact that lets the Builder organize work into **testable blocks** -- groups of scenarios that logically belong together for verification -- and enable **parallel delivery** where independent blocks can be worked on by different agents simultaneously. The user orchestrates the cycle: Builder (Phase 1) -> QA (verify Phase 1) -> Builder (fix bugs + Phase 2) -> QA -> ... until complete.

## 10.2 The Delivery Plan Artifact
*   **Path:** `.purlin/cache/delivery_plan.md`
*   **Created by:** Builder, when user approves phased delivery.
*   **Committed to git:** Yes (all agents read it across sessions).
*   **Deleted by:** Builder, when the final phase completes.
*   **Format:** The plan contains a summary, numbered phases (each with status, feature list, completion commit, and QA bugs addressed), and a plan amendments section. Phase statuses are PENDING, IN_PROGRESS, or COMPLETE. Exactly one phase may be IN_PROGRESS at a time. COMPLETE phases are immutable historical record.
*   **Intra-Feature Phasing:** A feature MAY appear in multiple phases. Targeted delivery within a feature uses the existing `[Scope: targeted:...]` mechanism. No new scope types are needed.

## 10.3 Cross-Session Resumption
Each phase MUST be a separate Builder session. The Builder MUST NOT auto-advance to the next PENDING phase after completing the current one -- it halts and waits for the user to relaunch.

When a delivery plan exists at session start, the Builder resumes from the next PENDING phase. QA bugs recorded during prior phases are addressed first, before new phase work begins. If the IN_PROGRESS phase was interrupted mid-session, the Builder resumes that phase, skipping features already in TESTING state.

**Scope Reset on Plan Completion:** When the Builder completes the final phase and deletes the delivery plan, the Builder MUST reset the `change_scope` to `full` for every feature that participated in the plan and still has `builder: "TODO"` status. Targeted scopes are artifacts of the phased delivery -- once the plan is gone, any remaining unbuilt work must be visible under a full scope. This prevents scenarios from becoming invisible to future Builder sessions after the delivery plan context is deleted.

## 10.4 QA Interaction
The QA Agent MUST check for a delivery plan at `.purlin/cache/delivery_plan.md` during startup. If the plan exists, QA classifies each TESTING feature as either "fully delivered" (appears only in COMPLETE phases) or "more work coming" (appears in a PENDING phase). QA MUST NOT mark a feature as `[Complete]` if it appears in any PENDING phase of the delivery plan, even if all currently-delivered scenarios pass. QA informs the user which features are phase-gated.

## 10.5 Phasing is Optional
Phased delivery is never automatic. The Builder proposes phasing based on scope assessment, and the user always decides whether to accept phasing, modify the phase breakdown, or proceed with a single-session delivery. At any approval checkpoint, the user may collapse remaining phases, re-split, or abandon phasing entirely.

## 10.6 Architect Awareness
If the Architect modifies feature specs while a delivery plan is active, the Builder detects the mismatch on resume and proposes a plan amendment. Minor changes (added scenarios, clarified requirements) are auto-updated. Major changes (new features, removed phases, restructured dependencies) require user approval before continuing.

## 10.7 CDD Dashboard Integration
When a delivery plan exists, the CDD Dashboard's ACTIVE section heading displays the current phase progress as an inline annotation: `ACTIVE (<count>) [PHASE (<current>/<total>)]`. The `/status.json` API and CLI tool include an optional `delivery_phase` field with `current` and `total` values. When all phases are COMPLETE or no delivery plan exists, the phase annotation and API field are omitted.

## 10.8 Phase Sizing Guidance

Phase sizing is driven by **testability** and **parallelism**, not by hard caps. The Builder uses judgment to create phases that:

*   **Group related scenarios** -- features or scenario subsets that logically belong together for verification. A phase should produce a testable state where QA can meaningfully verify the delivered work.
*   **Enable parallel delivery** -- when independent feature groups have no dependencies on each other, they can be placed in separate phases for concurrent agent work.
*   **Keep large features focused** -- a single feature with many unimplemented scenarios (5+) benefits from a dedicated phase to keep the Builder focused and the QA verification cycle tight.

There are no hard per-phase feature caps. The Builder balances phase size against session productivity and verification granularity.

## 10.9 Context Budget Awareness

The Builder SHOULD consider context consumption when sizing phases. Different work items consume context at different rates:

*   **Large feature specs** with many scenarios require significant context to read and internalize.
*   **Multi-file implementations** that touch many source files consume context for reading existing code, making changes, and verifying consistency.
*   **Extensive test suites** consume context for writing, running, and debugging tests.

When the cumulative scope of a phase (specs to read + files to modify + tests to run) is large, prefer splitting into smaller phases. The goal is to complete each phase with sufficient context remaining for quality verification.

This factor is **subordinate** to testability (Section 10.8) and dependency order. A phase must still produce a testable state and respect dependency constraints, even if that means a larger context footprint. Context budget is a tiebreaker when multiple valid phase breakdowns exist.

No hard token counting is required. This is qualitative judgment based on scope signals: number of features, spec length, estimated file count, and test complexity.
