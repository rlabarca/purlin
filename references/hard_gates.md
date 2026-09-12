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

## No Claude Code Hook Enforces Anything

`hooks/hooks.json` registers no Claude Code hooks: its `hooks` object is empty and the plugin
installs no `PreToolUse`, `PostToolUse` or `Stop` handler. So every **NEVER** in `agents/purlin.md`
is an instruction to the agent, not a mechanism that stops it. An agent that ignores one is not
blocked by anything inside this repository.

The controls that survive an agent ignoring an instruction run outside the agent's turn: the
proof-coverage gate inside `purlin:verify`, the pre-push hook, the CI gate job
(`scripts/ci/verify_gate.py --check`), and Branch protection making that job required. Read the
**NEVER** list as the agent's contract and "Enforcement Layers" below as what holds when the
contract is broken.

## Enforcement Layers

This is the project's only enforcement-layer table. `docs/regulated-environments.md`,
`docs/lifecycle-guide.md` and `docs/testing-workflow-guide.md` link here instead of carrying a
copy, because three copies drifted into three different answers about what blocks a push.

| Layer | Where it runs | What it blocks |
|---|---|---|
| **Layer 0: skill logic** | inside `purlin:verify`, in the developer's session | a receipt for any feature with a rule that has no passing proof. This is Gate 1 above, the framework's one gate, and nobody can turn it off: it is how the skill works. Every layer below it is something a project configures for itself |
| **Layer 1: git pre-push hook** | `git push`, on the developer's machine | in `warn`, a FAILING proof; in `strict`, anything not VERIFIED; in `off`, nothing at all, and it prints one line saying so. The developer sets the mode with `purlin:init --pre-push` and can bypass any mode with `--no-verify`. Caveat worth knowing before you rely on it: when the hook cannot resolve the plugin root it has no evidence to read, so it prints a WARNING and allows the push in `warn` and exits 1 in `strict`, rather than reporting a pass it did not earn |
| **Layer 2: your CI test run** | the forge, on the triggers your workflow declares | whatever your own test job blocks on. Purlin ships no pipeline config; you write it. Running every tier here regenerates the proof files from the code as pushed, which is what makes Layer 3 a clean-room reading rather than a re-read of what the developer committed |
| **Layer 3: `scripts/ci/verify_gate.py --check`** | the forge, as a job branch protection marks required | a merge while any feature is not VERIFIED or is awaiting a runner. `.purlin/config.json`'s `remote_verification` field **declares** which bar the project holds itself to; branch protection is what **enforces** it, because the field is a file in the tree the agent can edit |
| **Not a layer: `purlin:verify --recheck`** | a Claude Code session, on a developer's machine | nothing. It is a local clean-room re-run that re-executes the tests and compares the recomputed vhash against the committed receipts. No workflow can invoke a skill, so it is a check you choose to run, never a gate that runs on you |

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
