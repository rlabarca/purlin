# Hard Gates

Purlin has exactly 2 hard gates. Everything else is optional guidance.

## Gate 1: Invariant Protection

Files in `specs/_invariants/i_*` are **read-only**. The gate hook (`scripts/gate.sh`) blocks all Write/Edit calls targeting these files unless a bypass lock exists at `.purlin/runtime/invariant_write_lock`.

**What triggers it:** Any attempt to write or edit a file matching `specs/_invariants/i_*`.

**How to resolve:** Use `purlin:invariant sync` to update from the external source. The invariant skill creates the bypass lock, writes the file, then removes the lock.

**Implementation:** `hooks/hooks.json` registers a `PreToolUse` hook on `Write|Edit|NotebookEdit` that runs `scripts/gate.sh`. The script checks for the lock file and allows writes only when the lock target matches the file being written.

## Gate 2: Proof Coverage

`purlin:verify` refuses to issue a verification receipt for any feature where a RULE lacks a passing PROOF.

**What triggers it:** Running `purlin:verify` when a feature has rules without passing proof markers.

**How to resolve:** Write tests with proof markers covering every rule, then re-run `purlin:verify`.

**Implementation:** The verify skill reads `sync_status` output. Only features reported as READY (all rules have passing proofs) receive a receipt. This is enforced in the skill logic, not a hook.

## What Is NOT a Gate

- Writing code without invoking a skill — allowed.
- Writing tests without proof markers — allowed (but `sync_status` won't count them).
- Writing specs in any format — allowed (but unnumbered rules get a WARNING from `sync_status`).
- Committing without running verify — allowed.

Skills are optional tools, not gatekeepers.
