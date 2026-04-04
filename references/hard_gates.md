# Hard Gates

Purlin has exactly 1 hard gate. Everything else is optional guidance.

## Gate 1: Proof Coverage

`purlin:verify` refuses to issue a verification receipt for any feature where a RULE lacks a passing PROOF.

**What triggers it:** Running `purlin:verify` when a feature has rules without passing proof markers.

**How to resolve:** Write tests with proof markers covering every rule, then re-run `purlin:verify`.

**Implementation:** The verify skill reads `sync_status` output. Only features reported as VERIFIED (all rules have passing proofs) receive a receipt. This is enforced in the skill logic, not a hook.

## What Is NOT a Gate

- Writing code without invoking a skill — allowed.
- Writing tests without proof markers — allowed (but `sync_status` won't count them).
- Writing specs in any format — allowed (but unnumbered rules get a WARNING from `sync_status`).
- Editing anchor files (even those with external references) — allowed.
- Committing without running verify — allowed.

Skills are optional tools, not gatekeepers.
