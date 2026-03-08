# Builder Decision Protocol

> **Reference file.** Loaded on demand when making a non-trivial implementation decision.
> Stub location: BUILDER_BASE Section 2b.

## Decision Categories

*   **`[CLARIFICATION]`** (Severity: INFO) -- Interpreted ambiguous spec language. The spec was unclear; you chose a reasonable interpretation.
*   **`[AUTONOMOUS]`** (Severity: WARN) -- Spec was silent on this topic. You made a judgment call to fill the gap.
*   **`[DEVIATION]`** (Severity: HIGH) -- Intentionally diverged from what the spec says. Requires Architect acknowledgment before COMPLETE.
*   **`[DISCOVERY]`** (Severity: HIGH) -- Found an unstated requirement during implementation. Requires Architect acknowledgment before COMPLETE.
*   **`[INFEASIBLE]`** (Severity: CRITICAL) -- The feature cannot be implemented as specified due to technical constraints, contradictory requirements, or dependency issues. Requires Architect to revise the spec before work can continue.

## Format

`**[TAG]** <description> (Severity: <level>)`

## Location

All tagged decisions MUST be written in the companion file (`features/<name>.impl.md`), never inline in the feature `.md` file. If no companion file exists, create it (see BUILDER_BASE Section 5.2 Knowledge Colocation).

## Rules

*   `[CLARIFICATION]` and `[AUTONOMOUS]` are informational. They do not block completion but are audited by the Critic tool.
*   `[DEVIATION]` and `[DISCOVERY]` MUST be acknowledged by the Architect (via spec update or explicit approval) before the feature can transition to `[Complete]`. Architect appends `Acknowledged.` to the tag line; the bracket tag stays in place -- do NOT convert to unbracketed format (unbracketed labels are reserved for pruned QA records).
*   `[INFEASIBLE]` **halts work on the feature.** Record the tag with a detailed rationale in Implementation Notes, commit the note, then **skip to the next feature** in the work plan. The Architect must revise the spec before the Builder can resume. Do NOT attempt workarounds or partial implementations.
*   When in doubt between CLARIFICATION and AUTONOMOUS, use AUTONOMOUS. Transparency is preferred over underreporting.

## Cross-Feature Discovery Routing

When a `[DISCOVERY]` identifies a bug or gap in a *different* feature (not the one currently being implemented), file the `[DISCOVERY]` in the **target feature's** `## Implementation Notes` -- not the originating feature. The Critic flags Architect action items per-feature; a discovery filed in the wrong file leaves the broken feature invisible to the Critic. A `[CLARIFICATION]` note in the originating feature's Implementation Notes is appropriate if the trigger context is useful, but the actionable tag belongs in the target feature.

## Bracket-Tag Exclusivity

The bracket-tag syntax (`[DISCOVERY]`, `[DEVIATION]`, etc.) in Implementation Notes is for Builder Decisions (active and acknowledged). The Architect may append acknowledgment markers to existing tag lines; the tags themselves are Builder-authored. Pruned User Testing records use unbracketed labels (`DISCOVERY --`, `BUG --`). If you encounter a pruned record that uses bracket tags, the Critic will miscount it as an active decision -- reformat it to unbracketed style.

## Chat Is Not a Communication Channel

Never surface spec corrections, stale path references, or other Architect-directed findings via chat output. Chat output is ephemeral and not monitored by the Architect between sessions. Use `/pl-propose` to record the finding in Implementation Notes and commit it. The Critic will route it to the Architect's action items at their next session.
