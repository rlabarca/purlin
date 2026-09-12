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
- A proof declared `@on(<platform>)` with no result there — allowed. It reports
  `AWAITING RUNNER`, which warns and never blocks (`specs/mcp/sync_status.md` RULE-47).

Skills are optional tools, not gatekeepers.

## Project Policy Is Not a Framework Gate

A project can add gates of its own, and one ships as a template: `scripts/ci/verify_gate.py
--check` exits `1` when a feature is not VERIFIED or is awaiting a runner, and branch protection
marking that job a required check is what makes the exit code matter.

That is **project policy layered on top of the framework's single gate**, not a second gate. The
distinction is not cosmetic:

| | Purlin's gate | A project's CI gate |
|---|---|---|
| Where it lives | skill logic, in the framework | the project's own workflow files and forge settings |
| Who can turn it off | nobody; it is how `purlin:verify` works | the project, by changing its own config or branch rules |
| What it asks | does every rule have a passing proof? | whatever the project decided, e.g. is every feature VERIFIED on every platform? |

`.purlin/config.json`'s `remote_verification` field **declares** whether a project holds itself to
the remote bar. It does not enforce it: the field is a file in the tree the agent can edit, so
enforcement has to live outside the repository (`docs/regulated-environments.md`, "Policy lives
outside the repo"). See `references/remote_verification.md`.

So the count stands. Purlin has exactly 1 hard gate; a project may have as many as it configures,
and none of them are Purlin's.
