# Phased Delivery Protocol

> This file is loaded on-demand by `/pl-delivery-plan`, `/pl-build`, and `/pl-verify`
> commands when a delivery plan exists or phased delivery is being considered.

## 10.1 Purpose
When the Architect introduces large-scale changes (multiple new feature files, major revisions across existing features), the Builder may need to split work across multiple sessions to manage context window limits and ensure quality. The Phased Delivery Protocol provides a persistent coordination artifact that lets the Builder propose splitting work into numbered phases, each producing a testable state. The user orchestrates the cycle: Builder (Phase 1) -> QA (verify Phase 1) -> Builder (fix bugs + Phase 2) -> QA -> ... until complete.

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
Phased delivery is never automatic. The Builder proposes phasing based on scope assessment heuristics, and the user always decides whether to accept phasing, modify the phase breakdown, or proceed with a single-session delivery. At any approval checkpoint, the user may collapse remaining phases, re-split, or abandon phasing entirely.

## 10.6 Architect Awareness
If the Architect modifies feature specs while a delivery plan is active, the Builder detects the mismatch on resume and proposes a plan amendment. Minor changes (added scenarios, clarified requirements) are auto-updated. Major changes (new features, removed phases, restructured dependencies) require user approval before continuing.

## 10.7 CDD Dashboard Integration
When a delivery plan exists, the CDD Dashboard's ACTIVE section heading displays the current phase progress as an inline annotation: `ACTIVE (<count>) [PHASE (<current>/<total>)]`. The `/status.json` API and CLI tool include an optional `delivery_phase` field with `current` and `total` values. When all phases are COMPLETE or no delivery plan exists, the phase annotation and API field are omitted.
