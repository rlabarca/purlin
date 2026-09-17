# Held rules, 0.10.0 review

These are the cases a reviewer named as missing during the 0.10.0 review, before the
three-level model. The signatures and holds of that review were dropped with the old layout, so
none of these is a current hold. Each line still names the case a test is missing, and a signer
who agrees writes it again with `purlin:sign <feature> RULE-N --hold "<case>"`.

## proof_common (10)

- `RULE-1` [high]: vitest, sql and xUnit plugins never run
- `RULE-2` [high]: second specs/ or .purlin/ beside the run not checked; no-marker fallback not covered
- `RULE-3` [medium]: zero-backslash test and subdirectory-run test lack the RULE-3 marker
- `RULE-4` [medium]: only the shell entry is checked for seven keys
- `RULE-6` [high]: replace-own-entry leg is in an unmarked test
- `RULE-8` [medium]: temp-name construction checked loosely; no-leftover test unmarked
- `RULE-11` [high]: stderr naming the offending marker never asserted
- `RULE-12` [medium]: skip-exempt check is a text search only
- `RULE-13` [medium]: only jest and vitest imports checked
- `RULE-14` [medium]: tier default file/top-level tier/e2e absence unchecked; proof names a test file without the marker

## server (10)

- `RULE-1` [high]: capabilities tools not asserted
- `RULE-2` [high]: project_root optional not checked
- `RULE-5` [high]: the startup line is never checked for the version and the root
- `RULE-6` [high]: no later call showing the per-call root does not persist
- `RULE-7` [high]: root/how-chosen not checked
- `RULE-9` [high]: merged config / config.local.json not read
- `RULE-11` [high]: only producer hook exercised
- `RULE-12` [medium]: no data file written not asserted
- `RULE-14` [high]: spec/record input triggers not exercised
- `RULE-15` [medium]: behavioural half touches a proof file, not specs/

## mutation (9)

- `RULE-3` [high]: no case lands exactly on a half (e.g. (1, 7) → 13), so half-up is never told apart from banker's rounding
- `RULE-5` [high]: only one feature is run, so nothing shows one run per feature over its own scope files
- `RULE-7` [medium]: never asserts the reason names @stryker-mutator/core
- `RULE-9` [high]: "counts missed for this one" is never exercised
- `RULE-13` [medium]: find_report is exercised one directory down, not two as the proof says
- `RULE-18` [medium]: available False not asserted
- `RULE-19` [medium]: one rule not two; score None not asserted
- `RULE-20` [high]: unknown engine: no-import and the reason naming the engine are not checked
- `RULE-21` [high]: no test shows a directory entry winning over a glob; proof needs a directory case

## records (8)

- `RULE-1` [medium]: conflicting runner/os/timestamp untested
- `RULE-5` [high]: mode compared with module constant, not literal 100644
- `RULE-6` [medium]: retries compared with module constant, not literal 3
- `RULE-7` [high]: unset GITHUB_REPOSITORY untested
- `RULE-8` [medium]: newContent not asserted; Azure push ref head branch not checked
- `RULE-14` [medium]: project name/timestamp not asserted; literals differ from proof
- `RULE-15` [medium]: unknown rollup text not asserted
- `RULE-22` [medium]: counts compared with module constant

## scaffold (7)

- `RULE-11` [high]: command writing signer list not asserted
- `RULE-26` [medium]: hook-manager line to add not asserted
- `RULE-29` [high]: root precedence chain partially exercised
- `RULE-33` [medium]: dry-run accepts 0/1/3, nothing-applied unchecked
- `RULE-36` [high]: typescript walk passes when npm/vitest missing
- `RULE-37` [high]: ts/xunit pass when tools missing; jest/sql/shell not wired
- `RULE-39` [medium]: lib, app and test preferences named by the rule are untested; only src and tests

## static_checks (6)

- `RULE-1` [high]: stress test body `or True`
- `RULE-2` [high]: stress test asserts pass, opposite of proof; no two-constants python case
- `RULE-8` [high]: PROOF-20 asserts only the result count, so the condition deciding the result is untested
- `RULE-16` [medium]: shell/C# result shape not checked
- `RULE-21` [high]: .py .sh .js .ts extensions not in loop
- `RULE-31` [medium]: js/ts/cs/sql bodies unchecked

## drift (5)

- `RULE-3` [high]: a file listed twice still passes; nothing asserts 6 files
- `RULE-9` [medium]: removed rule ids not proved
- `RULE-11` [high]: NUL-byte/newline sources untested; no process count
- `RULE-14` [high]: per-role key sets not asserted
- `RULE-15` [medium]: top-level keys not shown exact

## run_script (5)

- `RULE-1` [medium]: --ci/--tag without --record not covered
- `RULE-13` [high]: no record case with a failing proof → result fail
- `RULE-18` [medium]: record still written is not checked
- `RULE-19` [medium]: only node_modules skipped is exercised
- `RULE-38` [medium]: double purlin_proof / one finish writing both entries untested

## specs (5)

- `RULE-3` [high]: proof text hash never exercised
- `RULE-7` [medium]: bare @windows tier and Visual-Hash not covered
- `RULE-11` [medium]: neither anchor condition shown alone
- `RULE-12` [high]: directory expansion and unhashable path untested
- `RULE-13` [high]: transitive requires untested

## states (5)

- `RULE-4` [high]: record at another commit and scope-tree match untested
- `RULE-5` [high]: signed gate and ci-labelled record not exercised
- `RULE-8` [high]: current signature with failing/absent record untested
- `RULE-11` [high]: low-risk under minimum and medium not shown
- `RULE-15` [high]: one feature only, so a double count cannot occur; needs two features proving the global anchor

## brief (4)

- `RULE-5` [high]: only 2 of 5 proof-text checks exercised
- `RULE-6` [high]: only no_assertion of the test-body checks exercised
- `RULE-9` [medium]: one record only; latest-of-several unproved
- `RULE-20` [high]: only rule-text edit exercised, not proof text or test body

## signatures (3)

- `RULE-9` [medium]: proof says 16 fields, format and test have 15
- `RULE-12` [high]: medium-risk never-auto-signed case missing
- `RULE-31` [high]: proof literal `is not on main yet`, test asserts `is not on origin/main yet`

## purlin_report (3)

- `RULE-9` [medium]: solo leg never checks STRENGTH and CODE CHANGED absent
- `RULE-17` [high]: no case where the OS has a record and the notice is absent
- `RULE-18` [high]: one-line cut and state pill not proved

## schema_spec_format (3)

- `RULE-3` [medium]: multi-rule PROOF (RULE-A, RULE-B) not proved
- `RULE-5` [medium]: comma-separated Requires list (2+) not proved
- `RULE-6` [high]: overlap not asserted; no boundary case

## upstream (3)

- `RULE-6` [high]: ext:: case never checks no file written / no process
- `RULE-7` [medium]: reworded source moving the pin untested
- `RULE-22` [high]: propose writing the patch not exercised

## config_engine (2)

- `RULE-2` [high]: only one .purlin/ marker, so nothing shows the climb stops at the nearest one
- `RULE-6` [high]: warning never checked to name the malformed file

## pm_anchor_userstories (2)

- `RULE-2` [high]: no assertion that the skill says changes land as a pull request
- `RULE-3` [high]: never checks for "pull request comment"

## skill_sign (2)

- `RULE-3` [medium]: → one line only
- `RULE-5` [high]: nothing checks that the skill says the signature commit is signed

## skill_init (2)

- `RULE-3` [medium]: → one line only
- `RULE-5` [high]: three answers not bounded; CI requirement per gate unchecked

## update (2)

- `RULE-3` [high]: exit-0 Nothing is pending only asserted under RULE-5
- `RULE-10` [high]: digest/test_framework presence not asserted; retired list read from module

## proofs (1)

- `RULE-6` [high]: only pass-then-fail order exercised

## skill_anchor (1)

- `RULE-3` [medium]: → required on one line only, not one per outcome

## skill_build (1)

- `RULE-3` [medium]: → one line only

## skill_drift (1)

- `RULE-3` [medium]: → one line only

## skill_find (1)

- `RULE-3` [medium]: → one line only

## skill_rename (1)

- `RULE-3` [medium]: → one line only

## skill_review (1)

The spec was deleted.

## skill_spec (1)

- `RULE-3` [medium]: fenced block / nothing after not asserted

## skill_spec_from_code (1)

- `RULE-3` [medium]: → one line only

## skill_status (1)

- `RULE-3` [medium]: → one line only

## skill_test (1)

- `RULE-3` [medium]: → one line only

## skill_audit (1)

- `RULE-3` [medium]: → one line only
