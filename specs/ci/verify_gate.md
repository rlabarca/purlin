# Feature: verify_gate

> Requires: security_no_dangerous_patterns
> Scope: scripts/ci/verify_gate.py, .github/workflows/verify-gate.yml, .github/workflows/windows-proofs.yml
> Stack: python/stdlib (argparse, json), GitHub Actions
> Description: Purlin's CI side of remote verification. `scripts/ci/verify_gate.py --check` is a
>   deterministic gate that reads the structured status payload and decides whether the branch may
>   merge; the runner workflows prove runner-gated tiers and commit their proof files back with
>   recorded provenance. The gate reads the project's declared `remote_verification` mode, but the
>   mode is a declaration the agent can edit, not the enforcement: enforcement is branch protection
>   marking this job a required check.

## Rules

- RULE-1: `verify_gate.py --check` reads its input from the structured payload `_build_report_data` produces, never from the rendered Unicode summary table. The table's glyphs and column order are presentation and change with the dashboard; a gate that parses them is coupled to a layout and breaks silently when the layout moves
- RULE-2: Exit codes are `0` when the gate passes, `1` when it fails, and `2` for a bad invocation (unreadable project, unknown mode, missing payload), matching `dev/bump_version.sh`. A gate must fail closed: an error reading the payload exits non-zero, never `0`
- RULE-3: The gate's verdict is keyed off the project's `remote_verification` mode. Under `"required"` an unverified feature or a feature awaiting a runner fails the gate. Under `"optional"` the same findings are reported and the gate exits `0`. Under `"off"` the gate exits `0` and reports only that it is disabled, so a project that has not opted in is never blocked by a job it did not ask for
- RULE-4: Under `"required"`, a feature with runner-gated proofs that have no result at their tier fails the gate, even when it is VERIFIED. The gate reads the payload's live `awaiting_runner` list rather than the receipt's, because the receipt records what was true when it was issued and the gate is deciding about now; the receipt's own `awaiting_runner` (`skill_verify` RULE-9) is the record of the same gap, not the gate's input. A VERIFIED feature awaiting a runner is a verified-here claim, not a verified-everywhere one, and `"required"` is the declaration that verified-everywhere is the bar. Locally this state warns and never blocks (`sync_status` RULE-47): the gate is where it becomes fatal, because the gate is the only layer that runs on every platform
- RULE-5: The gate never writes. It reads the payload, prints a verdict, and exits: no file is created or modified, no commit is made, no proof or receipt is touched. It is the CI counterpart of `purlin:verify`'s read-only contract, and the same reason applies: a gate that can edit the evidence it grades is not a gate
- RULE-6: The `remote_verification` mode the gate reports is named as a declaration and not as the enforcement, in the gate's own output and in its source header. Enforcement is branch protection marking the job a required check, which lives outside the repository where the agent cannot reach it (`docs/regulated-environments.md`, "Policy lives outside the repo")
- RULE-7: Every workflow that commits a proof file back to the branch stamps the commit with a `Purlin-Runner: <runner-identity>` trailer, because that trailer is the only place the identity of the proving runner is recorded. Proof entries carry no such field, by design (`sync_status` RULE-48). A commit-back with no trailer reports as `runner not recorded`, which is a gap, not a valid state
- RULE-8: Every workflow that commits a proof file back to the branch carries a loop guard, so its own commit cannot retrigger it: a `paths-ignore` entry for the proof files it writes, and `[skip ci]` in the commit subject. Both, because either alone fails on a different trigger path

## Proof

- PROOF-1 (RULE-1): Grep `scripts/ci/verify_gate.py` for the box-drawing glyphs the summary table is built from (`│`, `┌`, `─`); verify none appears, and that the gate obtains its features by calling the report-data builder rather than by splitting text
- PROOF-2 (RULE-2): Run the gate against a fully verified project and assert exit `0`; against a project with an unverified feature under `"required"` and assert exit `1`; against a directory that is not a Purlin project and assert exit `2`. Assert the non-project case is not `0`, so a gate that cannot read the evidence cannot pass the branch @integration
- PROOF-3 (RULE-3): Build one temp project with an unverified feature and run the gate three times, changing only `remote_verification`: assert exit `1` under `"required"`, exit `0` under `"optional"` with the same feature still named in the output, and exit `0` under `"off"` with the output stating the gate is disabled. The finding is identical in all three; only the verdict differs @integration
- PROOF-4 (RULE-4): Build two temp projects whose specs differ only in one extra `@windows` proof line covering a rule that a `@unit` proof already proves, so both have the same rules, the same executed proofs, the same vhash and a valid receipt reading VERIFIED. Run the gate under `"required"` on each: assert the one with the awaited proof exits `1` naming that proof id and tier, and the other exits `0`. Since the two differ in nothing else, the awaited runner is provably what failed it @integration
- PROOF-5 (RULE-5): Snapshot every path under a temp project (name, size, mtime) plus `git status --porcelain`, run the gate under each of the three modes, and assert the snapshot is byte-identical afterwards: no file added, removed, or modified, and no commit created
- PROOF-6 (RULE-6): Run the gate under `"required"` and grep its output for the declaration/enforcement split; verify it names branch protection as the enforcement and does not describe the config field as the gate. Grep `scripts/ci/verify_gate.py`'s header for the same split @integration
- PROOF-7 (RULE-7): Parse every workflow under `.github/workflows/`; for each one that runs `git commit` on a `*.proofs-*.json` path, verify its commit command includes a `Purlin-Runner:` trailer. Assert at least one such workflow was found, so the proof cannot pass by matching nothing
- PROOF-8 (RULE-8): For each workflow that commits a proof file back, verify it declares a `paths-ignore` entry matching the proof files it writes and that its commit subject contains `[skip ci]`. Assert at least one such workflow was found
