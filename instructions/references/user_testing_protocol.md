# User Testing Protocol

> **Reference file.** Loaded on demand when recording, routing, or pruning discoveries.
> Stub location: HOW_WE_WORK_BASE Section 7.

## Discovery Lifecycle

Status progression: `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`

**Shortcut -- No Spec Change Needed:** When the Architect (for DISCOVERY/INTENT_DRIFT/SPEC_DISPUTE) or Builder (for BUG) reviews an OPEN entry and confirms no specification or implementation change is required, the entry moves directly to `RESOLVED` with a resolution note explaining why no change was needed. The SPEC_UPDATED step is skipped. QA prunes it normally.

*   **OPEN:** Any agent records the finding.
*   **SPEC_UPDATED:** Architect or PM updates the spec (Gherkin scenarios or Visual Specification) to address it.
*   **RESOLVED:** The fix is complete (or no fix was needed). QA prunes the entry -- this is unconditional regardless of the `Action Required` field value.
*   **PRUNED:** QA removes entry from Discoveries, adds one-liner to Implementation Notes. Git history preserves full record. **Format:** Pruned one-liners MUST use unbracketed type labels (e.g., `BUG --`, `DISCOVERY --`), never bracket-style tags (`[BUG]`, `[DISCOVERY]`). Bracket tags in Implementation Notes are reserved for Builder Decisions (see policy_critic.md Section 2.3).

## Queue Hygiene

*   The sidecar file only contains OPEN and SPEC_UPDATED entries (active work).
*   RESOLVED entries are pruned by the QA Agent.
*   An empty or absent `<name>.discoveries.md` file means the feature is clean.

## Feedback Routing

**From User Testing Discoveries (any agent may record, routed by type):**
*   **BUG** -> Builder must fix implementation. **Exception:** when the BUG is in instruction-file-driven agent behavior (startup protocol ordering, role compliance, slash command gating), the recorder MUST set `Action Required: Architect` in the discovery entry. The Architect fixes it by strengthening the relevant instruction file. The Critic routes BUG action items by reading the `Action Required` field -- the default is Builder, but `Action Required: Architect` overrides this for instruction-level bugs.
*   **DISCOVERY** -> Architect must add missing scenarios, then Builder re-implements.
*   **INTENT_DRIFT** -> Architect must refine scenario intent, then Builder re-implements.
*   **SPEC_DISPUTE** -> Architect must review the disputed scenario with the user and revise or reaffirm it. The scenario is **suspended** (QA skips it) until the Architect resolves the dispute. For SPEC_DISPUTEs concerning visual design, the resolution may require updating the Figma design first, then re-ingesting via `/pl-design-ingest` to update the Visual Specification. When a PM agent is active, design disputes route through the PM for Figma iteration before the Architect finalizes. **Triage override:** When the Architect determines a SPEC_DISPUTE is design-related (involving visual properties, Figma designs, or Token Map entries) but the feature is not PM-owned and the title lacks the `Visual:` prefix, the Architect sets `- **Action Required:** PM` in the discovery entry and commits. The next Critic run routes the dispute to PM. The Architect does not resolve design disputes directly -- design authority belongs to the PM.

**Builder-to-Architect (from Implementation):**
*   **INFEASIBLE** -> The feature cannot be implemented as specified (technical constraints, contradictory requirements, or dependency issues). Builder halts work on the feature, records a detailed rationale in Implementation Notes, and skips to the next feature. Architect must revise the spec before the Builder can resume.
