# Hard Gates

Purlin has exactly 1 hard gate. Everything else is optional guidance.

## Gate 1: Proof Coverage

`purlin:verify` refuses to issue a verification receipt for any feature where a RULE lacks a passing PROOF.

**What triggers it:** Running `purlin:verify` when a feature has rules without passing proof markers.

**How to resolve:** Write tests with proof markers covering every rule, then re-run `purlin:verify`.

**Implementation:** The verify skill reads `sync_status` output. Features reported as
**PASSING** — every rule has a passing proof — receive a receipt. Note that VERIFIED is the
state *after* a receipt exists: `_determine_status` returns VERIFIED only when a matching
receipt is already on disk, so requiring VERIFIED before issuing one would mean no feature
could ever get its first receipt. This is enforced in the skill logic, not a hook.

## What Is NOT a Gate

- Writing code without invoking a skill — allowed.
- Writing tests without proof markers — allowed (but `sync_status` won't count them).
- Writing specs in any format — allowed (but unnumbered rules get a WARNING from `sync_status`).
- Editing anchor files (even those with external references) — allowed.
- A low **Proof Design** or **Proof Integrity** score — allowed. Both gauges are advisory and
  neither blocks a commit, a push, or a receipt. They measure quality; the gate measures
  coverage.
- Committing without running verify — allowed.

Skills are optional tools, not gatekeepers.
