# Feature: approvals

> Description: The attestation that a rule, its proof and its test belong
>   together, and the gate that reads it. One approval is one file, so two
>   approvals never conflict, and it binds the hashes of the rule text, the
>   proof text and the test body, plus the pinned design a design rule rests on.
>   CI writes the auto-approvals a low-risk rule may have; a person writes the
>   rest as one signed commit. `scripts/ci/verify_gate.py --check` reads the
>   structured payload and decides whether the branch may merge under the
>   project's gate: `tested`, `recorded` or `approved`.
> Scope: scripts/review/approve.py, scripts/ci/verify_gate.py
> Stack: python/stdlib (argparse, json, subprocess), git signed commits

## Rules

- RULE-1: The three hashes an approval binds come back together with the kind of the test hash and the pinned design hash of a design rule [risk: medium] [origin: eng]
- RULE-2: A rule the project does not declare has no hashes at all [risk: low] [origin: eng]
- RULE-3: Reflowing a rule's whitespace or changing its tags leaves the triple where it was, so re-tagging never stales an approval [risk: high] [origin: eng]
- RULE-4: Editing the rule text, the proof text or the test body moves the triple [risk: high] [origin: eng]
- RULE-5: A rule proved only by a `@manual` proof records `manual` as the kind of its test hash instead of naming a test file [risk: high] [origin: eng]
- RULE-6: An approval stays current only while the rule text, the proof text, the test body and the risk still hash to what it bound [risk: high] [origin: eng]
- RULE-7: A rule whose only approval has gone stale is reported Stale, never Approved [risk: high] [origin: eng]
- RULE-8: An approval file is named for the rule, the first eight characters of the triple and the approver's slug, the email local part lowercased with every character that is not a letter or a digit replaced by a hyphen [risk: medium] [origin: eng]
- RULE-9: An approval carries schema `purlin-approval/1` and exactly the fields the format names: the triple, the three hashes and their kind, the design hash, the risk, the approver, the timestamp, the gate, the brief and the record [risk: medium] [origin: eng]
- RULE-10: The approval reader finds an approval beside its spec and never reads a brief written in the same directory as one [risk: high] [origin: eng]
- RULE-11: CI auto-approves a low-risk rule whose record passes and whose test strength is at or above the minimum, writing a file whose approver is `ci` and which names the record it rests on [risk: high] [origin: eng]
- RULE-12: CI never auto-approves a rule tagged `[risk: high]` or `[risk: medium]` [risk: high] [origin: eng]
- RULE-13: CI writes nothing while the test strength is below the minimum, and auto-approves once a record at or above it exists [risk: high] [origin: eng]
- RULE-14: CI never auto-approves a rule whose record carries a failing proof [risk: high] [origin: eng]
- RULE-15: CI never auto-approves a rule proved by a `@manual` proof, because that evidence is a person's note [risk: high] [origin: eng]
- RULE-16: CI leaves a rule that already carries a current approval alone rather than writing a second one [risk: medium] [origin: eng]
- RULE-17: With no signing configured the command writes no approval, exits 1 and prints the three git config commands that set signing up [risk: medium] [origin: eng]
- RULE-18: One invocation is one signed commit, whatever number of rules it carries, and its subject names the feature and every rule approved [risk: high] [origin: eng]
- RULE-19: A batch spanning more than one feature names each feature with its own rules in the subject [risk: low] [origin: eng]
- RULE-20: An approval counts only when the commit that added it is signed and its author is on the approver list [risk: high] [origin: eng]
- RULE-21: Someone off the approver list is refused by name, and at gate `approved` with no list at all the command names `purlin:init --gate approved` and exits 1 [risk: medium] [origin: eng]
- RULE-22: `approve.py --help` exits 0 and an unknown option or no feature at all exits 2 [risk: low] [origin: eng]
- RULE-23: An approval committed on a side branch is not on the protected branch until that branch merges [risk: high] [origin: eng]
- RULE-24: At gate `tested` a record a person committed counts and the test strength is never read [risk: medium] [origin: eng]
- RULE-25: At gate `tested` a rule with no record, and a rule whose record carries a failing proof, fail the gate and are named [risk: high] [origin: eng]
- RULE-26: At gate `recorded` only a record CI committed counts, and a record a person committed is reported as no record at all [risk: high] [origin: eng]
- RULE-27: At gate `recorded` a test strength below the minimum fails and names both numbers, while no engine at all leaves the rule alone [risk: high] [origin: eng]
- RULE-28: A report section names at most 20 rules and counts the rest, pointing at `--json` for every one [risk: low] [origin: eng]
- RULE-29: At gate `approved` a current approval signed by someone on the approver list passes its rule, and a low-risk rule needs no human approval at all [risk: high] [origin: eng]
- RULE-30: At gate `approved` a high-risk rule fails when it has no approval, when its only approval is a CI auto-approval, when the approval commit is unsigned, or when the approver last touched the test, and the report says which [risk: high] [origin: eng]
- RULE-31: At gate `approved` a stale approval fails as Stale, and an approval that has not reached the protected branch fails naming that branch [risk: high] [origin: eng]
- RULE-32: At gate `approved` with no approver list the gate prints the missing-list directive and fails without grading a rule [risk: high] [origin: eng]
- RULE-33: The gate exits 0 when it is met, 1 when it is not, and 2 when it cannot read the evidence, so an unreadable project never passes [risk: high] [origin: eng]
- RULE-34: `verify_gate.py` needs `--check` and a directory that exists; either missing exits 2 [risk: low] [origin: eng]
- RULE-35: `--json` prints the gate, the verdict, the exit code, the rule counts and every rule that fell short [risk: medium] [origin: eng]
- RULE-36: The gate creates and changes no file at any gate level [risk: high] [origin: eng]
- RULE-37: The gate reads the structured payload and never a rendered table, and a caller may hand it a payload it already built [risk: medium] [origin: eng]
- RULE-38: Every line the gate prints either carries the `verify-gate:` prefix or is an indented finding under a section heading [risk: low] [origin: eng]
- RULE-39: CI never auto-approves a low-risk rule when a free check found anything in the body of a test backing it [risk: high] [origin: eng]
- RULE-40: `approve.py <feature> RULE-N --hold "<the missing case>"` writes `<RULE-N>.<hash8>.<holder-slug>.hold.json` binding the rule's hashes, with schema `purlin-hold/1`, the holder's email and the missing case as `reason`, and commits it signed as `hold(<feature>): RULE-N`; `--hold` with no reason, or with no rule named, exits 2 and writes nothing [risk: medium] [origin: eng]
- RULE-41: CI never auto-approves a rule a current hold names, and a hold whose rule, proof or test has since changed no longer stops it [risk: high] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read the hashes of `login RULE-1` in a recorded project; verify the rule, proof and test hashes are each 64 characters, the kind is `file` and the design hash is `none` @integration
- PROOF-2 (RULE-2): Read the hashes of `login RULE-99`, which the spec does not declare; verify all five values are `none` @integration
- PROOF-3 (RULE-3): Read the triple, rewrite the rule line with doubled spaces and an added `[origin: pm]` tag, and read it again; verify the two values are equal @integration
- PROOF-4 (RULE-4): Read the triple, then change `200` to `201` in the rule, then extend the proof text, then add a comment to the test; verify each of the three values differs from the first @integration
- PROOF-5 (RULE-5): Retag `PROOF-2` as `@manual` and read the hashes of `RULE-2`; verify the kind of the test hash is `manual` @integration
- PROOF-6 (RULE-6): Write an approval, then load the approvals back; verify exactly 1 is current @integration
- PROOF-7 (RULE-6): Write an approval, then edit the rule text; verify zero approvals are current @integration
- PROOF-8 (RULE-6): Write an approval, then edit the proof text; verify zero approvals are current @integration
- PROOF-9 (RULE-6): Write an approval, then edit the test so its assertion reads `== 200 or True`; verify zero approvals are current @integration
- PROOF-10 (RULE-6): Write an approval, then raise the rule from `[risk: low]` to `[risk: high]`; verify zero approvals are current @integration
- PROOF-11 (RULE-7): Write an approval and verify the rule reads `Approved`; then edit the rule text and verify it reads `Stale` @integration
- PROOF-12 (RULE-8): Write an approval for the address `Rich.LaBarca+purlin@example.com`; verify the only file in the approvals directory is named `RULE-1.<hash8>.rich-labarca-purlin.json` for that rule's triple @integration
- PROOF-13 (RULE-9): Write an approval naming a brief and a record; verify its schema is `purlin-approval/1`, its field names are exactly the 16 the format lists, its triple is the first 16 characters of the rule's triple, and its timestamp ends `Z` @integration
- PROOF-14 (RULE-10): Write an approval and a brief for the same rule into one approvals directory, then load the approvals; verify exactly 1 comes back and its approver is `jane@acme.com` @integration
- PROOF-15 (RULE-11): Run the auto-approval over a recorded project; verify exactly 1 file is written, that it ends `.ci.json`, that its approver is `ci` and its risk `low`, and that its record path opens with `.purlin/records/login/` @integration
- PROOF-16 (RULE-12): Run the auto-approval over the same project; verify no path written names `RULE-2`, the high-risk rule @integration
- PROOF-17 (RULE-13): Set the minimum to 70 and record 30, then run the auto-approval and verify nothing is written; record 95 and run it again and verify exactly 1 file is written @integration
- PROOF-18 (RULE-14): Record `PROOF-1` as failing and run the auto-approval; verify nothing is written @integration
- PROOF-19 (RULE-15): Retag `PROOF-1` as `@manual`, record the project and run the auto-approval; verify nothing is written @integration
- PROOF-20 (RULE-16): Write a person's approval for `RULE-1`, then run the auto-approval; verify nothing is written @integration
- PROOF-21 (RULE-17): Run the command in a checkout with no signing key; verify it exits 1, prints `git config gpg.format ssh`, `git config user.signingkey ~/.ssh/id_ed25519.pub` and `git config commit.gpgsign true`, and that the approvals directory is empty @integration
- PROOF-22 (RULE-17): Run `approve.py` as a command in a separate process against a checkout with no signing key; verify it exits 1 and prints `git config gpg.format ssh` @integration
- PROOF-23 (RULE-18): Configure a throwaway signing key and run the command for the whole feature; verify it exits 0, writes 2 approvals, and that the one commit it made reports signature `G` with the subject `approve(login): RULE-2 RULE-1` @integration
- PROOF-24 (RULE-19): Build the subject for `login RULE-1` with `login RULE-2`, then for `login RULE-1` with `billing RULE-3`; verify they read `approve(login): RULE-1 RULE-2` and `approve(batch): login RULE-1, billing RULE-3`
- PROOF-25 (RULE-20): Run the command to approve `RULE-1` as `jane@acme.com` with signing configured, then count the approval against that list and against `someone@else.com`; verify the first counts and the second is refused with a reason naming the approver list @integration
- PROOF-26 (RULE-21): Set the approver list to `someone@else.com` and run the command; verify it exits 1 and prints `not on the approver list` @integration
- PROOF-27 (RULE-21): Run the command in a recorded project at gate `approved` with no approver list; verify it exits 1 and prints `approver list missing: run purlin:init --gate approved` @integration
- PROOF-28 (RULE-22): Run the command with `--help`, with `login --nope` and with no argument; verify the exit codes are 0, 2 and 2
- PROOF-29 (RULE-23): Run the command to approve `RULE-1` on a branch called `side`; verify the approval is not an ancestor of `main`, then fast-forward `main` onto `side` and verify it is @integration
- PROOF-30 (RULE-24): Run the gate over a project at gate `tested` whose record a person committed; verify it exits 0 and prints `gate = tested` and `PASS. Every rule meets tested.` @integration
- PROOF-31 (RULE-24): Run the gate at gate `tested` with a minimum of 80 over a record measuring 10; verify it exits 0 and prints no line about the minimum test strength @integration
- PROOF-32 (RULE-25): Run the gate over a project at gate `tested` with no record at all; verify it exits 1, opens a section `Not tested (2):`, names `login RULE-1` and `login RULE-2`, and closes with `FAIL. 2 of 2 rules do not meet tested.` @integration
- PROOF-33 (RULE-25): Record `PROOF-1` as failing and run the gate at gate `tested`; verify it exits 1 and names `login RULE-1` @integration
- PROOF-34 (RULE-26): Run the gate at gate `recorded` over a record committed under the build identity; verify it exits 0 and prints `gate = recorded` @integration
- PROOF-35 (RULE-26): Run the gate at gate `recorded` over a record a person committed; verify it exits 1, opens `Not recorded (2):` and gives the reason `no record CI wrote covers this commit` @integration
- PROOF-36 (RULE-27): Run the gate at gate `recorded` with a minimum of 70 over a record measuring 40; verify it exits 1, opens `Below the minimum test strength (2):` and reads `test strength 40 percent, below 70` @integration
- PROOF-37 (RULE-27): Run the gate at gate `recorded` with a minimum of 70 over a record with no test strength; verify it exits 0 and prints no line about the minimum @integration
- PROOF-38 (RULE-28): Run the gate over a spec carrying 30 rules and no record; verify it opens `Not recorded (30):` and closes the section with `and 10 more; --json prints every one.` @integration
- PROOF-39 (RULE-29): Run the command to approve the high-risk rule with a signed commit by the listed approver, then run the gate at gate `approved`; verify it exits 0 and prints `gate = approved` @integration
- PROOF-40 (RULE-29): Run the command to approve only the high-risk rule, then run the gate at gate `approved`; verify it exits 0 and never names `login RULE-1`, the low-risk rule CI auto-approves @integration
- PROOF-41 (RULE-30): Run the gate at gate `approved` with no approval written; verify it exits 1, opens `Not approved (1):` and reads `login RULE-2: no approval` @integration
- PROOF-42 (RULE-30): Write a CI auto-approval for the high-risk rule and run the gate at gate `approved`; verify it exits 1 and the reason names the CI auto-approval @integration
- PROOF-43 (RULE-30): Write an approval and commit it without a signature, then run the gate at gate `approved`; verify it exits 1 and reads `the approval commit is not signed` @integration
- PROOF-44 (RULE-30): Put the author of the test on the approver list, approve with that identity and run the gate at gate `approved`; verify it exits 1 and reads `the approver last touched the test` @integration
- PROOF-45 (RULE-31): Run the command to approve the high-risk rule, then change `401` to `403` in it and run the gate at gate `approved`; verify it exits 1 and the report says Stale @integration
- PROOF-46 (RULE-31): Run the command to approve the high-risk rule on a branch called `side`, then run the gate at gate `approved`; verify it exits 1 and reads `is not on main yet` @integration
- PROOF-47 (RULE-32): Run the gate at gate `approved` over a project with no approver list; verify it exits 1, prints `approver list missing: run purlin:init --gate approved` and never prints `PASS` @integration
- PROOF-48 (RULE-33): Run the gate over a passing project, then a failing one, then a directory holding no project; verify the exit codes are 0, 1 and 2 and that the last prints `failing closed` @integration
- PROOF-49 (RULE-33): Run the gate over a directory that does not exist; verify it exits 2 and prints `cannot read a Purlin project` @integration
- PROOF-50 (RULE-34): Run the gate with no argument, and with `--check --project-root /no/such/directory`; verify both exit 2
- PROOF-51 (RULE-38): Run `verify_gate.py` as a command in a separate process over a passing project; verify it exits 0 and its output opens `verify-gate: gate = tested` @integration
- PROOF-52 (RULE-35): Run the gate with `--json` over a project with no record; verify the JSON reads gate `tested`, verdict `fail`, exit 1, 2 rules, 0 met and 2 entries under the state list @integration
- PROOF-53 (RULE-35): Run the gate with `--json` over a passing project; verify the verdict is `pass`, that met equals 2 of 2 rules and the state list is empty @integration
- PROOF-54 (RULE-32): Run the gate with `--json` at gate `approved` with no approver list; verify it exits 1 and the JSON reports the approver list `missing` @integration
- PROOF-55 (RULE-36): Snapshot every file of a project, run the gate at `tested`, `recorded` and `approved`, and snapshot again; verify the two snapshots are equal and `git status --porcelain` prints nothing @integration
- PROOF-56 (RULE-37): Read the gate's own source; verify it builds the payload and that none of the box-drawing glyphs a rendered table uses appears in it
- PROOF-57 (RULE-37): Build the payload, hand it to the gate and run it; verify it exits 0 and prints `PASS` @integration
- PROOF-58 (RULE-38): Run the gate over a project with no record; verify every line that is not indented either opens with `verify-gate:` or ends with a colon @integration
- PROOF-59 (RULE-39): Edit the low-risk rule's test to call `login("ada", "secret")` and assert nothing, record the project and run the auto-approval; verify nothing is written. Restore `assert login("ada", "secret") == 200`, record again, run it again and verify exactly 1 file is written and it names `RULE-1` @integration
- PROOF-60 (RULE-40): In a checkout signing as `jane@acme.com`, run `login RULE-1 --hold "no case for an expired token"`; verify it exits 0, the last commit is signed `G` with the subject `hold(login): RULE-1`, and it adds `specs/auth/login.approvals/RULE-1.<hash8>.jane.hold.json` for the rule's own triple, whose schema is `purlin-hold/1`, holder `jane@acme.com` and reason `no case for an expired token` @integration
- PROOF-61 (RULE-40): Run `login RULE-1 --hold` with no reason, `login RULE-1 --hold --batch`, and `login --hold "a case"` with no rule; verify each exits 2 and no `.hold.json` exists @integration
- PROOF-62 (RULE-41): Write a hold on the low-risk `RULE-1` for its current text and run the auto-approval; verify nothing is written. Add the comment `# the fixture's password` above the test's assertion, commit, record again and run it again; verify exactly 1 file is written and it names `RULE-1` @integration
