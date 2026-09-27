# Feature: gate_check

> Description: The gate a tag run ends with. It reads the structured
>   payload, which has already worked out every rule's cells, and groups the
>   rules that fall short by the one cell that blocks each of them. The
>   project's gate decides how far the chain is read: `passed`, `strong` or
>   `signed`. `--verify` adds one section over the evidence already
>   committed: every signature and hold must still bind what it names, and
>   every file under a `ci/` folder must have been committed by the runner
>   itself. It writes nothing, prints every line under the `gate:` prefix,
>   and fails closed, so a project it cannot read never passes.
> Scope: scripts/ci/gate_check.py
> Stack: python/stdlib (argparse, json)

## Rules

- RULE-1: The gate reads the structured payload and never a rendered table, and a caller may hand it a payload it already built [bar: strong] [origin: eng]
- RULE-2: A rule is counted once, under the feature that owns it, and it is met when the payload reads `meets_gate` true [bar: strong] [origin: eng]
- RULE-3: A rule blocked at the spec status or at the passed cell is named under `Not passed` with the blocking word and its reasons, the spec status reading `no proof names this rule`, except where the passed cell's word is `partial`, which has its own section between `Not passed` and `Weak` [bar: strong] [origin: eng]
- RULE-4: A rule blocked at the strong cell is named with the cell's word and its reasons, under `Weak` where that word is `weak`, under `Not audited` where it is `not audited` and under `To review` where it is `manual test`, `unsettled` or `held`, because no build moves those three [bar: strong] [origin: eng]
- RULE-5: A rule blocked at the signed cell is named under `Not signed` with the cell's word and its reasons [bar: strong] [origin: eng]
- RULE-6: Under `passed` no minimum test strength is printed and no section but `Not passed` can appear, because no cell above the first one exists [bar: strong] [origin: eng]
- RULE-7: A section names at most 20 rules and counts the rest, pointing at `--json` for every one [bar: passed] [origin: eng]
- RULE-8: Under `signed` the gate grades every rule whether or not the config names anyone, because no list says who may sign; the key an older release named its signers under is not read [bar: strong] [origin: eng]
- RULE-9: The gate exits 0 when it is met, 1 when it is not, and 2 when it cannot read the evidence, so an unreadable project never passes [bar: strong] [origin: eng]
- RULE-10: `gate_check.py` needs `--check` and a directory that exists; either missing exits 2 [bar: passed] [origin: eng]
- RULE-11: `--json` prints the gate, the minimum, the commit, the rule counts, every section under its own key, the result and the exit code [bar: strong] [origin: eng]
- RULE-12: The gate creates and changes no file at any gate value [bar: strong] [origin: eng]
- RULE-13: Every line the gate prints either carries the `gate:` prefix or is an indented finding under a section heading [bar: passed] [origin: eng]
- RULE-14: The report's sections are `Not passed`, `Partial`, `Weak`, `Not audited`, `To review`, `To sign` and `Evidence`, in that order, and a section with no line in it is not printed [bar: strong] [origin: eng]
- RULE-15: `--verify` names under `Evidence` every signature and every hold that no longer binds the rule, proof, test, bar and audit it names, so a tag cannot stand over code that changed after it was signed, and a file naming a rule the project no longer declares is named too [bar: strong] [origin: eng]
- RULE-16: `--verify` names under `Evidence` every file under `.purlin/records/ci/` or `.purlin/briefs/ci/` whose commit is not the runner's own, and without `--verify` neither check runs at all [bar: strong] [origin: eng]

## Proof

- PROOF-1 (RULE-2): Run the gate over a project at gate `passed` whose record a person committed; verify it exits 0 and prints `gate: gate = passed` and `PASS. Every rule meets passed.` @integration
- PROOF-2 (RULE-3): Run the gate over a project at gate `passed` with no record at all; verify it exits 1, opens a section `Not passed (2):`, reads `login RULE-1: no test` and `login RULE-2: no test`, and closes with `gate: FAIL. 2 of 2 rules do not meet passed.` @integration
- PROOF-3 (RULE-3): Write a record whose `PROOF-1` failed and run the gate at gate `passed`; verify it exits 1 and reads `login RULE-1: failed` with a reason opening `failing:` @integration
- PROOF-4 (RULE-3): Delete the proof line naming `RULE-1` and run the gate at gate `passed`; verify it exits 1, reads `login RULE-1: drafted` and gives the reason `no proof names this rule` @integration
- PROOF-5 (RULE-6): Run the gate at gate `passed` over a project naming a minimum of 80 and a record measuring 10; verify it exits 0, prints no line holding `minimum test strength`, and opens neither `Weak` nor `Not signed` @integration
- PROOF-6 (RULE-2): Run the gate at gate `strong` over a record CI committed, a strength of 90 and a settled brief for the `[bar: strong]` rule; verify it exits 0 and prints `gate: gate = strong` and `minimum test strength 50.` @integration
- PROOF-7 (RULE-3): Run the gate at gate `strong` over a record written under `.purlin/records/local/`; verify it exits 0 and passes. Run the same project at gate `signed`; verify it opens no `Not passed` section, because a local record counts there too, and opens `To sign (1):` instead @integration
- PROOF-33 (RULE-3): Run the gate over a project whose rule passed on one operating system and failed on another; verify it exits 1, opens a section `Partial (1):` rather than `Not passed`, and names the platform that failed @integration
- PROOF-8 (RULE-4): Run the gate at gate `strong` with a minimum of 70 over a record measuring 40; verify it exits 1, opens `Weak (2):` and reads `strength 40% under 70%` @integration
- PROOF-9 (RULE-4): Run the gate at gate `strong` with no brief written for the `[bar: strong]` rule; verify it exits 1, opens `Not audited (1):`, reads `login RULE-2: not audited` and names `no audit has run on this code` @integration
- PROOF-10 (RULE-4): Write a settled brief whose observation reads `PROOF-2 asserts the status but never the body the rule names.` and run the gate at gate `strong`; verify it exits 1, opens `Weak (1):`, reads `login RULE-2: weak` and prints that sentence @integration
- PROOF-11 (RULE-5): Sign the `[bar: strong]` rule with a signed commit by the listed signer, then run the gate at gate `signed`; verify it exits 0 and prints `gate: gate = signed` @integration
- PROOF-12 (RULE-5): Sign only the `[bar: strong]` rule and run the gate at gate `signed` with `sign_at` at `strong`; verify it exits 0 and never names `login RULE-1`, whose bar is `passed` @integration
- PROOF-13 (RULE-5): Run the gate at gate `signed` with no signature written; verify it exits 1, opens `Not signed (1):` and reads `login RULE-2: unsigned` @integration
- PROOF-14 (RULE-5): Write a signature and commit it without a signature on the commit, then run the gate at gate `signed`; verify it exits 1 and reads `the signing commit is not signed` @integration
- PROOF-15 (RULE-5): Sign the `[bar: strong]` rule as `dev@example.com`, the author of the commit that last touched the test, in a signed commit, and run the gate at gate `signed`; verify it exits 0 and never reads `last touched` @integration
- PROOF-16 (RULE-5): Sign every rule at gate `signed` with `sign_at` `all`, then change `200` to `signed 200` in the `[bar: passed]` rule and run the gate; verify it exits 1, reads `login RULE-1: stale` and gives the reason `hashes changed after the signature` @integration
- PROOF-17 (RULE-5): Point `origin/HEAD` at `main`, sign the `[bar: strong]` rule in a signed commit on a branch called `side`, and run the gate at gate `signed` there; verify it exits 0 and never reads `not on main` @integration
- PROOF-18 (RULE-8): Run the gate at gate `signed` over a project whose config names nobody and whose `[bar: strong]` rule is unsigned; verify it exits 1, opens `To sign (1):` naming `login RULE-2: unsigned`, and never prints `purlin:init --gate signed`. Sign that rule in a signed commit and run it again; verify it exits 0 @integration
- PROOF-19 (RULE-7): Run the gate at gate `strong` over a spec carrying 30 rules and no record; verify it opens `Not passed (30):` and closes the section with `and 10 more; --json prints every one.` @integration
- PROOF-20 (RULE-2): Declare an anchor holding 1 rule, require it from a feature holding 2, and run the gate with `--json` at gate `passed`; verify it counts 3 rules and names `policy RULE-1` exactly once @integration
- PROOF-21 (RULE-9): Run the gate over a passing project, then a failing one, then a directory holding no project; verify the exit codes are 0, 1 and 2 and that the last prints `failing closed` @integration
- PROOF-22 (RULE-9): Run the gate over a directory that does not exist; verify it exits 2 and prints `cannot read a Purlin project` @integration
- PROOF-23 (RULE-10): Run the gate with no argument, and with `--check --project-root /no/such/directory`; verify both exit 2
- PROOF-24 (RULE-13): Run `gate_check.py` as a command in a separate process over a passing project; verify it exits 0 and its output opens `gate: gate = passed` @integration
- PROOF-25 (RULE-11): Run the gate with `--json` over a project at gate `passed` with no record; verify the JSON reads gate `passed`, result `fail`, exit 1, 2 rules, 0 met, 2 entries under `not_passed`, empty `weak`, `waiting` and `not_signed`, and the commit the payload named @integration
- PROOF-26 (RULE-11): Run the gate with `--json` over a passing project; verify the result is `pass`, that met equals 2 of 2 rules and `not_passed` is empty @integration
- PROOF-27 (RULE-11): Run the gate with `--json` at gate `strong` with a minimum of 70 over a record measuring 40; verify `weak` holds 2 entries, `not_passed` is empty and the minimum reads 70 @integration
- PROOF-28 (RULE-8): Run the gate with `--json` at gate `signed` over a project whose config names nobody; verify it exits 1, that `to_sign` holds exactly 1 row, and that the JSON carries no key about a list of signers @integration
- PROOF-29 (RULE-12): Snapshot every file of a project, run the gate at `passed`, `strong` and `signed`, and snapshot again; verify the two snapshots are equal and `git status --porcelain` prints nothing @integration
- PROOF-30 (RULE-1): Read the gate's own source; verify it builds the payload, reads `meets_gate`, and that none of the box-drawing glyphs a rendered table uses appears in it
- PROOF-31 (RULE-1): Build the payload, hand it to the gate and run it; verify it exits 0 and prints `PASS` @integration
- PROOF-32 (RULE-13): Run the gate over a project with no record; verify every line that is not indented either opens with `gate:` or ends with a colon @integration
- PROOF-34 (RULE-14): Run the gate with `--json` at gate `signed` over a project holding one rule short at each section; verify the JSON carries the keys `not_passed`, `partial`, `weak`, `not_audited`, `to_review`, `to_sign` and `evidence`, and that the section titles read `Not passed`, `Partial`, `Weak`, `Not audited`, `To review`, `To sign` and `Evidence` in that order @integration
- PROOF-35 (RULE-15): Sign a rule at gate `signed`, then edit the rule text and run the gate with `--check --verify`; verify it exits 1, opens `Evidence (1):`, names the signature file and reads `what it binds is not this code`. Run the same project with `--check` alone and verify no `Evidence` section is printed @integration
- PROOF-36 (RULE-15): Write a hold for a rule, delete that rule from the spec and run the gate with `--check --verify`; verify the hold file is named under `Evidence` with `no rule login RULE-2 is in this project` @integration
- PROOF-37 (RULE-15): Re-audit a signed rule so the brief observes something it did not before, then run the gate with `--check --verify`; verify the signature is named under `Evidence`, because the audit hash a signature binds moved @integration
- PROOF-38 (RULE-16): Commit a record under `.purlin/records/ci/` as a person and run the gate with `--check --verify`; verify it exits 1 and names that path under `Evidence` with `the commit that added it is not the runner's`. Commit the same file as the build identity and verify it is not named @integration
