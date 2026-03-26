**Purlin mode: QA**

Purlin agent: This skill activates QA mode. If another mode is active, confirm switch first.

---

## Scope

If an argument was provided, record a discovery for `features/<arg>.md`.
If no argument was provided, ask the user which feature the discovery belongs to.

---

## Discovery Classification

Guide the user through classifying the finding:

*   **[BUG]** -- Behavior contradicts an existing scenario. The spec is right, implementation is wrong. Routes to Engineer.
*   **[DISCOVERY]** -- Behavior exists but no scenario covers it. The spec is incomplete. Routes to PM (add scenarios), then Engineer (re-implement).
*   **[INTENT_DRIFT]** -- Behavior matches the spec literally but misses the actual intent. Routes to PM (refine intent), then Engineer.
*   **[SPEC_DISPUTE]** -- The user disagrees with a scenario's expected behavior. The spec itself is wrong or undesirable. Routes to PM or PM (review and revise/reaffirm). Scenario is **suspended** until resolved.

When classifying: if the user says "this shouldn't work this way" or "the scenario is wrong," that's SPEC_DISPUTE. If they say "it doesn't do what the scenario says," that's BUG.

Ask the user to describe the observed behavior and expected behavior.

## Recording Format

Record the entry in `features/<name>.discoveries.md`, creating the file if absent. File heading: `# User Testing Discoveries: <Feature Label>`.

```
### [TYPE] <title> (Discovered: YYYY-MM-DD)
- **Scenario:** <which scenario, or NONE>
- **Observed Behavior:** <what the user described>
- **Expected Behavior:** <from the scenario, or "not specified">
- **Action Required:** <Engineer or PM>
- **Status:** OPEN
```

**Routing the `Action Required` field:**
*   BUG -> `Engineer` (default). Exception: when the BUG is in instruction-file-driven agent behavior (startup protocol, role compliance, slash command gating), set `PM`.
*   DISCOVERY -> `PM`
*   INTENT_DRIFT -> `PM`
*   SPEC_DISPUTE -> `PM` (default). For design disputes (visual properties, Figma, Token Map), PM will triage by setting `Action Required: PM`.

Commit: `git commit -m "qa(<scope>): [TYPE] - <brief title>"`.

If SPEC_DISPUTE: inform user the scenario is suspended for future sessions until resolution.

## Discovery Lifecycle

Status progression: `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`

*   **OPEN:** Just recorded.
*   **SPEC_UPDATED:** PM updated the spec to address it.
*   **RESOLVED:** Fix complete or no fix needed. (Shortcut: PM/Engineer confirms no change needed -> skip to RESOLVED with resolution note.)
*   **PRUNED:** QA removes entry from sidecar, adds one-liner to companion file (`features/<name>.impl.md`). Format: `<TYPE> -- <summary>` (NO bracket tags -- brackets are reserved for Engineer Decisions).

## Pruning Protocol

When an entry reaches RESOLVED:
1.  Remove from `features/<name>.discoveries.md`. If file becomes empty (heading only), delete it.
2.  Add one-liner to companion file: `<TYPE> -- <summary>`.
3.  Git commit the pruning.
