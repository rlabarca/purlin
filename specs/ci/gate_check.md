# Feature: gate_check

> Description: The gate a tag run ends with. It reads the structured
>   payload, which has already worked out every rule's cells, and groups the
>   rules that fall short by the one cell that blocks each of them. The
>   project's gate decides how far the chain is read: `passed`, `strong` or
>   `signed`. `--verify` adds one section over the evidence already
>   committed: every signature and hold must still bind what it names, and
>   every file under `.purlin/evidence/ci/` must have been committed by the runner
>   itself: on GitHub as git reads the commit's signature and committer, on
>   Azure DevOps as the host records who pushed it. It writes nothing, prints
>   every line under the `gate:` prefix, and fails closed, so a project it
>   cannot read never passes.
> Scope: scripts/ci/gate_check.py, scripts/mcp/purlin/provenance.py, templates/purlin.azure-pipelines.yml
> Stack: python/stdlib (argparse, json, urllib), Azure DevOps REST API

## Rules

- RULE-1: The gate reads the structured payload and never a rendered table, and a caller may hand it a payload it already built
- RULE-2: A rule is counted once, under the feature that owns it, and it is met when the payload reads `meets_gate` true
- RULE-3: A rule blocked at the passed cell is named under `Not passed` with the blocking word and its reasons, a rule no proof line names reading `no test (no proof written)`, except where the passed cell's word is `partial`, which has its own section between `Not passed` and `Weak`
- RULE-4: A rule blocked at the strong cell is named with the cell's word and its reasons, under `Weak` where that word is `weak`, under `Not audited` where it is `not audited` and under `To review` where it is `manual test`, `unsettled` or `held`, because no build moves those three
- RULE-5: A rule blocked at the signed cell is named under `Not signed` with the cell's word and its reasons
- RULE-6: Under `passed` no minimum test strength is printed and no section but `Not passed` can appear, because no cell above the first one exists
- RULE-7: A section names at most 20 rules and counts the rest, pointing at `--json` for every one [level: passed]
- RULE-8: Under `signed` the gate grades every rule whether or not the config names anyone, because no list says who may sign
- RULE-9: The gate exits 0 when it is met, 1 when it is not, and 2 when it cannot read the evidence, so an unreadable project never passes
- RULE-10: `gate_check.py` needs `--check` and a directory that exists; either missing exits 2 [level: passed]
- RULE-11: `--json` prints the gate, the minimum, the commit, the rule counts, every section under its own key, the result and the exit code
- RULE-12: The gate creates and changes no file at any gate value
- RULE-13: Every line the gate prints either carries the `gate:` prefix or is an indented finding under a section heading [level: passed]
- RULE-14: The report's sections are `Not passed`, `Partial`, `Weak`, `Not audited`, `To review`, `To sign` and `Evidence`, in that order, and a section with no line in it is not printed
- RULE-15: `--verify` names under `Evidence` every signature and every hold that no longer binds the rule, proof, test and audit it names, so a tag cannot stand over code that changed after it was signed, and a file naming a rule the project no longer declares is named too
- RULE-16: `--verify` names under `Evidence` every file under `.purlin/evidence/ci/` whose last commit is not the runner's own, read on GitHub, and on a project whose runner variables and `origin` name no Azure DevOps, as `provenance.committed_by` reads it; without `--verify` neither check runs at all
- RULE-17: On Azure DevOps the tag run reads its own identity as `authenticatedUser.id` from `{SYSTEM_TEAMFOUNDATIONCOLLECTIONURI}_apis/connectionData?api-version=7.0`, finds the commit that last changed each `ci/` file with git, reads that commit's `push.pushedBy.id` from `{collection}{SYSTEM_TEAMPROJECT}/_apis/git/repositories/{BUILD_REPOSITORY_ID}/commits/{sha}?api-version=7.0`, and passes the file only when the two ids are the same; the committer's name is never read
- RULE-18: On an Azure DevOps runner the check fails closed: a `pushedBy` id that is not the run's own, a commit answer with no `push`, HTTP 401 or 403 or any other refusal on either request, no answer within 30 seconds, a file no commit changed, and a run with no `SYSTEM_ACCESSTOKEN` each name the file under `Evidence` with the reason in one plain sentence, and the gate exits 1
- RULE-19: Off a runner, where no `SYSTEM_TEAMFOUNDATIONCOLLECTIONURI` is set and `origin` is an Azure DevOps URL, the check sends no request, prints `ci/ provenance is checked by the tag run; this machine has no token.` and the count of files not checked, lists them under `not_checked` in `--json`, and neither names them under `Evidence` nor changes the exit code
- RULE-20: Every request to Azure DevOps carries a 30-second timeout and the token from `SYSTEM_ACCESSTOKEN` in its `Authorization` header and nowhere else, and the token appears in no line the gate prints and in no field of its JSON
- RULE-21: The rendered Azure DevOps pipeline's `Check the gate` step hands the run's token to the gate as `SYSTEM_ACCESSTOKEN: $(System.AccessToken)`

## Proof

- PROOF-1 (RULE-2): Run the gate over a project at gate `passed` whose evidence a person committed; verify it exits 0 and prints `gate: gate = passed` and `PASS. Every rule meets passed.`
- PROOF-2 (RULE-3): Run the gate over a project at gate `passed` with no evidence at all; verify it exits 1, opens a section `Not passed (2):`, reads `login RULE-1: no test` and `login RULE-2: no test`, and closes with `gate: FAIL. 2 of 2 rules do not meet passed.`
- PROOF-3 (RULE-3): Write a section whose `PROOF-1` failed and run the gate at gate `passed`; verify it exits 1 and reads `login RULE-1: failed` with a reason opening `failing:`
- PROOF-4 (RULE-3): Delete the proof line naming `RULE-1` and run the gate at gate `passed`; verify it exits 1, opens `Not passed (1):` and reads `login RULE-1: no test (no proof written)`
- PROOF-5 (RULE-6): Run the gate at gate `passed` over a project naming a minimum of 80 and evidence measuring 10; verify it exits 0, prints no line holding `minimum test strength`, and opens neither `Weak` nor `Not signed`
- PROOF-6 (RULE-2): Run the gate at gate `strong` over a section CI committed, a strength of 90 and an audit entry for the unmarked `RULE-2`; verify it exits 0 and prints `gate: gate = strong` and `minimum test strength 50.`
- PROOF-7 (RULE-3): Run the gate at gate `strong` over a section written under `.purlin/evidence/local/`; verify it exits 0 and passes. Run the same project at gate `signed`; verify it opens no `Not passed` section, because a local section counts there too, and opens `To sign (1):` instead
- PROOF-33 (RULE-3): Run the gate over a project whose rule passed on one operating system and failed on another; verify it exits 1, opens a section `Partial (1):` rather than `Not passed`, and names the platform that failed
- PROOF-8 (RULE-4): Run the gate at gate `strong` with a minimum of 70 over evidence measuring 40; verify it exits 1, opens `Weak (2):` and reads `strength 40% under 70%`
- PROOF-9 (RULE-4): Run the gate at gate `strong` with no audit entry written for the unmarked `RULE-2`; verify it exits 1, opens `Not audited (1):`, reads `login RULE-2: not audited` and names `no audit has run on this code`
- PROOF-10 (RULE-4): Write an audit entry that settled and found `PROOF-2 asserts the status but never the body the rule names.` and run the gate at gate `strong`; verify it exits 1, opens `Weak (1):`, reads `login RULE-2: weak` and prints that sentence
- PROOF-11 (RULE-5): Sign the unmarked `RULE-2` with a signed commit by the listed signer, then run the gate at gate `signed`; verify it exits 0 and prints `gate: gate = signed`
- PROOF-12 (RULE-5): Sign only the unmarked `RULE-2` and run the gate at gate `signed`; verify it exits 0 and never names `login RULE-1`, which is marked `[level: passed]`
- PROOF-13 (RULE-5): Run the gate at gate `signed` with no signature written; verify it exits 1, opens `Not signed (1):` and reads `login RULE-2: unsigned`
- PROOF-14 (RULE-5): Write a signature and commit it without a signature on the commit, then run the gate at gate `signed`; verify it exits 1 and reads `the signing commit is not signed`
- PROOF-15 (RULE-5): Sign the unmarked `RULE-2` as `dev@example.com`, the author of the last commit to the test file, in a signed commit, and run the gate at gate `signed`; verify it exits 0 and never reads `last touched`
- PROOF-16 (RULE-5): At gate `signed`, with both rules at the level `signed`, sign every rule, then change `200` to `signed 200` in `RULE-1`, run its tests and its audit again, and run the gate; verify it exits 1, reads `login RULE-1: stale` and gives the reason `hashes changed after the signature`
- PROOF-17 (RULE-5): Point `origin/HEAD` at `main`, sign the unmarked `RULE-2` in a signed commit on a branch called `side`, and run the gate at gate `signed` there; verify it exits 0 and never reads `not on main`
- PROOF-18 (RULE-8): Run the gate at gate `signed` over a project whose config names nobody and whose rule at the level `signed` is unsigned; verify it exits 1, opens `To sign (1):` naming `login RULE-2: unsigned`, and never prints `purlin:init --gate signed`. Sign that rule in a signed commit and run it again; verify it exits 0
- PROOF-19 (RULE-7): Run the gate at gate `strong` over a spec carrying 30 rules and no evidence; verify it opens `Not passed (30):` and closes the section with `and 10 more; --json prints every one.`
- PROOF-20 (RULE-2): Declare an anchor holding 1 rule, require it from a feature holding 2, and run the gate with `--json` at gate `passed`; verify it counts 3 rules and names `policy RULE-1` exactly once
- PROOF-21 (RULE-9): Run the gate over a passing project, then a failing one, then a directory holding no project; verify the exit codes are 0, 1 and 2 and that the last prints `failing closed`
- PROOF-22 (RULE-9): Run the gate over a directory that does not exist; verify it exits 2 and prints `cannot read a Purlin project`
- PROOF-23 (RULE-10): Run the gate with no argument, and with `--check --project-root /no/such/directory`; verify both exit 2
- PROOF-24 (RULE-13): Run `gate_check.py` as a command in a separate process over a passing project; verify it exits 0 and its output opens `gate: gate = passed`
- PROOF-25 (RULE-11): Run the gate with `--json` over a project at gate `passed` with no evidence; verify the JSON reads gate `passed`, result `fail`, exit 1, 2 rules, 0 met, 2 entries under `not_passed`, empty `weak`, `waiting` and `not_signed`, and the commit the payload named
- PROOF-26 (RULE-11): Run the gate with `--json` over a passing project; verify the result is `pass`, that met equals 2 of 2 rules and `not_passed` is empty
- PROOF-27 (RULE-11): Run the gate with `--json` at gate `strong` with a minimum of 70 over evidence measuring 40; verify `weak` holds 2 entries, `not_passed` is empty and the minimum reads 70
- PROOF-28 (RULE-8): Run the gate with `--json` at gate `signed` over a project whose config names nobody; verify it exits 1, that `to_sign` holds exactly 1 row, and that the JSON carries no key naming who may sign
- PROOF-29 (RULE-12): Snapshot every file of a project, run the gate at `passed`, `strong` and `signed`, and snapshot again; verify the two snapshots are equal and `git status --porcelain` prints nothing
- PROOF-30 (RULE-1): Read the gate's own source; verify it builds the payload, reads `meets_gate`, and that none of the box-drawing glyphs a rendered table uses appears in it
- PROOF-31 (RULE-1): Build the payload, hand it to the gate and run it; verify it exits 0 and prints `PASS`
- PROOF-32 (RULE-13): Run the gate over a project with no evidence; verify every line that is not indented either opens with `gate:` or ends with a colon
- PROOF-34 (RULE-14): Run the gate with `--json` at gate `signed` over a project holding one rule short at each section; verify the JSON carries the keys `not_passed`, `partial`, `weak`, `not_audited`, `to_review`, `to_sign` and `evidence`, and that the section titles read `Not passed`, `Partial`, `Weak`, `Not audited`, `To review`, `To sign` and `Evidence` in that order
- PROOF-35 (RULE-15): Sign a rule at gate `signed`, then edit the rule text and run the gate with `--check --verify`; verify it exits 1, opens `Evidence (1):`, names the signature file and reads `what it binds is not this code`. Run the same project with `--check` alone and verify no `Evidence` section is printed
- PROOF-36 (RULE-15): Write a hold for a rule, delete that rule from the spec and run the gate with `--check --verify`; verify the hold file is named under `Evidence` with `no rule login RULE-2 is in this project`
- PROOF-37 (RULE-15): Re-audit a signed rule so the audit finds something it did not before, then run the gate with `--check --verify`; verify the signature is named under `Evidence`, because the audit hash a signature binds moved
- PROOF-38 (RULE-16): Commit a file under `.purlin/evidence/ci/` as a person and run the gate with `--check --verify`; verify it exits 1 and names that path under `Evidence` with `the commit that added it is not the runner's`. Commit the same file as the build identity and verify it is not named
- PROOF-39 (RULE-17): Commit a `ci/` file, set the Azure DevOps variables and a token, and stand a fake opener in for the network answering `connectionData` with the id `build-1` and the commit with `push.pushedBy.id` `build-1`; run the check; verify the file is not named, that the first request is the `connectionData` URL and the second the `commits/<sha>` URL for the sha `git log -1` names for the file. Commit it under the committer name `Project Collection Build Service` and have the commit answer `jane-1`; verify it is named
- PROOF-40 (RULE-17): Commit a `ci/` file twice, the first commit answering `pushedBy.id` `build-1` and the second `jane-1`; verify it is named and that only the second sha was asked about. Swap the two answers; verify it is not named
- PROOF-41 (RULE-18): Answer a commit with `pushedBy` `jane-1`, `jane@acme.com`, and run the gate with `--check --verify`; verify it exits 1, opens `Evidence (1):` and names the file with `was pushed by jane@acme.com, not by the identity this run holds`
- PROOF-42 (RULE-18): Answer a commit with no `push` key; verify the file is named with `Azure DevOps names no push for commit`
- PROOF-43 (RULE-18): Answer the commit request with HTTP 401, then with HTTP 403; verify the file is named each time with `refused the token with HTTP 401` and `refused the token with HTTP 403`. Answer `connectionData` with HTTP 401; verify every `ci/` file is named and no commit was asked about
- PROOF-44 (RULE-18): Have the opener raise a timeout; verify the file is named with `did not answer within 30 seconds`. Commit nothing under a `ci/` file that exists; verify it is named with `no commit has changed it`
- PROOF-45 (RULE-18): Set the collection, project and repository but no token; verify every `ci/` file is named with `the run has no SYSTEM_ACCESSTOKEN` and no request was sent
- PROOF-46 (RULE-19): Point `origin` at `https://dev.azure.com/acme/demo/_git/demo`, set no Azure DevOps variable, and run the gate with `--check --verify --json` over a project that otherwise meets the gate with two `ci/` files; verify it exits 0, prints `gate: ci/ provenance is checked by the tag run; this machine has no token.` and `gate: 2 files under .purlin/evidence/ci/ are not checked.`, opens no `Evidence` section, lists both files under `not_checked`, and sent no request
- PROOF-47 (RULE-20): Run the match, the mismatch, the 401 and the timeout cases through the gate with `--json` and the token `s3cret-token-value`; verify every request carried the timeout 30 and `Authorization: Bearer s3cret-token-value`, and that the token appears nowhere in what the gate printed
- PROOF-48 (RULE-21): Render the Azure DevOps pipeline; verify the step whose `displayName` is `Check the gate` carries `env:` with `SYSTEM_ACCESSTOKEN: $(System.AccessToken)`
