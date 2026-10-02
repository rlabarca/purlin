# Decision 122, lane `signoff`: the report

Branch `lane/d122-signoff`, cut from `main` at `e02c9b4f5`. Nothing was pushed, tagged or signed
outside a temporary project, no real `claude` was started and no audit was run against this
repository.

## What was built

| File | Change |
|---|---|
| `scripts/mcp/purlin/signatures.py` | `signed_with(project_root, sha)` reads the key from the commit's own signature; `_verifies` is built on the same `ssh-keygen -Y check-novalidate` call. `hand_notes` fills `changed` (K2). `standing_by_files(project_root, version)` and `signed_versions(project_root)` are new |
| `scripts/mcp/purlin/facts.py` | `signoff_fact` reads the versions of the tags on `HEAD` and of the `.signoffs` folders `HEAD` holds, newest first; `TAG_NOT_HERE` |
| `scripts/review/sign.py` | `_sign` compares the key that signed with `key_fingerprint` and takes the commit back on a difference (`WRONG_KEY`, `KEY_ENDING`, `NO_SSH_KEY`); the answers file is asked `SIGN_ASK_TYPED` and ends on `NOT_SIGNED_ANSWERS`; `NO_TEST_RUNS`; `NOTE_CHANGED`; the overview leaves a rule checked by hand alone out of the rules that pass |
| `scripts/export/package.py` | `_results` writes `checked at sign-off` for a rule whose every proof is `@manual`; `audit_counts` counts as `summary.audit_counts` does (K4) |
| `references/formats/package_format.md` | version 11 to 12, in the commit of its code |
| `references/formats/signature_format.md` | wording only, version 16 stays |
| `dev/sign_project.py` | `signing_key` sets `gpg.ssh.program ssh-keygen`, as the two test files' own key helpers do |
| `dev/test_signatures.py`, `dev/test_export.py` | 9 tests added, 4 changed |

## Test numbers

`python -m pytest dev/test_signatures.py dev/test_export.py -q`

| | Passed | Skipped | Failed |
|---|---|---|---|
| Before, on `main` | 111 | 1 | 0 |
| After | 120 | 1 | 0 |

9 tests added: 7 for `signatures` (PROOF-269 to 275), 2 for `package` (PROOF-82, 83). None
deleted. The skipped test is `package` PROOF-39, tagged `@env(windows)`.

| Spec | Rules before, after | Proofs before, after | `Highest-Rule` before, after | `Highest-Proof` before, after |
|---|---|---|---|---|
| `signatures` | 30, 31 | 69, 76 | 135, 136 | 268, 275 |
| `package` | 23, 23 | 43, 45 | 37, 37 | 81, 83 |

The numbers the plan assumed were the tree's.

## Seen failing first

Each test was written and run against `main`'s code before any code changed.

| Proof | What `main`'s code gave |
|---|---|
| `signatures` PROOF-269 | the walk's last line was `Push the branch and the tag: git push origin main signed/2.1.0`: it signed with the other key, exit 0 |
| `signatures` PROOF-270 | the same run: exit 0, not 1 |
| `signatures` PROOF-272 | under `Last note` the first line was the note's, with no line above it |
| `signatures` PROOF-273 | the same |
| `signatures` PROOF-274 | `not signed` |
| `signatures` PROOF-275 | failed on its first step, `not signed` before the note was changed; its last step, `not signed`, holds on `main` too, as the refusing direction of RULE-130 |
| `signatures` PROOF-264, PROOF-271 | the last line was `Nothing was signed.` |
| `signatures` PROOF-232 | `  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.` and `  The audit: 17 strong, 1 weak, 1 not audited.` |
| `signatures` PROOF-251 | `  Linux/Unix: passed on dana-laptop` |
| `signatures` PROOF-220's test | `  2 rules on Linux/Unix: 2 pass their tests, 1 has a hand check.` |
| `package` PROOF-82 | `not_audited` 2 |
| `package` PROOF-83 | `['passed']` |

PROOF-221's test already held the signer's address from the base commit.

## Rules and proofs, word for word

### `signatures`: reworded rules

- RULE-50: A sign-off records the signer's email as git holds it, git's `user.name` as the signer's name, and the fingerprint of the key that signed its commit
- RULE-111: `--answers FILE` walks with the answers the file gives, printing each after its question, refuses with nothing written when a stop has no answer, and signs only where the file's `sign` holds the signer's email address, as the last question names it
- RULE-126: A hand check's stop shows the rule, each proof with its tag and the tests tied to it, the results on each system with any proof that found nothing to check and its reason, or `No test runs for this rule: you check it here.` where its every proof is `@manual`, the audit's findings where it found the rule weak, and asks what the person saw
- RULE-127: The walk opens with one line per run of the counted results, naming who ran it, on which machine, when, on which commit and how many rules, then `Signing <version> at <sha7>.`, then an overview counting per system the rules that pass their tests, a rule checked by hand alone not among them, and the hand checks, and what the audit found, as the status counts it: strong, weak, spot-checked, out of date and not audited, a count of zero left out but strong
- RULE-129: A hand check's stop shows, under `Last note`, each note of the newest sign-off that holds one for the rule, worded as the dashboard words it: `noted at the sign-off of <version> by <signer>, <at this commit | 1 commit since | <n> commits since>: <note>`; where the rule's or the proof's wording changed since that note, one line saying so stands above it; where no sign-off has noted the rule the stop shows neither
- RULE-130: The sign-off reads `signed <version>` only where a sign-off of that version counts and either `signed/<version>` names a commit holding its package, or this checkout holds no tag of that name, where it is read at the commit that added the sign-off, with one line naming `git fetch --tags`; a tag that names no such commit is passed over, with one warning naming the tag and why

### `signatures`: added rule

- RULE-136: After the sign-off's commit is made the command reads the key that signed it, and where that is not the key `user.signingkey` names it takes the commit back, writes no tag, exits 1 and prints one line naming both keys and the usual cause

### `signatures`: reworded proofs

- PROOF-221 (RULE-111): With `login RULE-2` a hand check and an answers file giving it `note` with `the lockout page read 401` and `sign` holding `jane@acme.com`, the signer's address, `--answers` prints that note after the stop's question, exits 0, and the sign-off carries that note
- PROOF-232 (RULE-127): Over 19 rules on Linux/Unix, 18 that pass their tests and 1 checked by hand alone, with 17 audited strong and 1 weak, the overview prints `  19 rules on Linux/Unix: 18 pass their tests, 1 has a hand check.` and `  The audit: 17 strong, 1 weak.`
- PROOF-251 (RULE-129): Before any sign-off, `--show` ends the stop of `login RULE-2`, whose one proof is `@manual`, on `Results` and `  No test runs for this rule: you check it here.`, with no line `Last note`
- PROOF-264 (RULE-111): An answers file gives `login RULE-2` a note and holds `"sign": true`; `--answers .purlin/runtime/signoff-answers.json` ends `Nothing was signed: "sign" in .purlin/runtime/signoff-answers.json must hold jane@acme.com, typed by the person signing.`, exits 0 and adds no commit and no file

### `signatures`: added proofs

- PROOF-269 (RULE-136): `user.signingkey` names Quinn's key, and `gpg.ssh.program` names a program that signs with another key; the walk answered yes prints one line beginning `No sign-off: the commit was signed with the key ending ...` and naming the last 4 characters of both keys, exits 1, `HEAD` names the commit it named before, and no `signed/2.1.0` exists
- PROOF-270 (RULE-136): After that refusal the checkout holds no sign-off file and no package file for `2.1.0`, and `git status --porcelain` prints nothing
- PROOF-271 (RULE-111): An answers file holds `"sign": "quinn@acme.com"` where the signer is `jane@acme.com`; `--answers` ends on the `Nothing was signed:` line naming `jane@acme.com`, and adds no commit and no file
- PROOF-272 (RULE-129): Quinn signs `0.1.0` with a note at the hand check `login RULE-2`; `RULE-2`'s text is then reworded and committed with new results; `--show --version 0.2.0` prints under `Last note` first `  The rule's wording changed since this note.`, then the note's line
- PROOF-273 (RULE-129): After the same sign-off the `@manual` proof of `login RULE-2` is reworded, the rule left as it was, and new results committed; the stop prints under `Last note` first `  The proof's wording changed since this note.`
- PROOF-274 (RULE-130): Quinn signs `0.1.0`, and the tag `signed/0.1.0` is then deleted from the checkout, as a pull that fetched no tag leaves it; the sign-off reads `signed 0.1.0 at <sha7>`, the sign-off's commit, and the warnings hold one line starting `signed/0.1.0 is not in this checkout:` and ending `Run git fetch --tags, or purlin:sign if no one wrote the tag.`
- PROOF-275 (RULE-130): With that tag deleted, a commit made with no signature then changes the sign-off file's note; the sign-off reads `not signed`

### `package`: reworded rules

- RULE-11: Each rule carries each result with its operating system, source, time, commit, runner and machine, and a rule whose every proof is `@manual` reads `checked at sign-off` there, never `passed`
- RULE-29: The package carries `audit`, the five counts `strong`, `weak`, `spot_checked`, `out_of_date` and `not_audited` as `purlin:status` gives them, over the rules that pass their tests and have a tested proof, and `hand_checks`, one entry per rule with a `@manual` proof naming its feature, rule and proofs

### `package`: added proofs

- PROOF-82 (RULE-29): 3 rules pass their tests, 2 found `strong` by the audit and 1 never read, and a fourth rule's one proof is `@manual`; the package's `audit` reads `{"strong": 2, "weak": 0, "spot_checked": 0, "out_of_date": 0, "not_audited": 1}`
- PROOF-83 (RULE-11): `login RULE-2`'s one proof is `@manual`, and its feature's committed section reads `RULE-2` `passed`; in the package each result of `RULE-2` reads `checked at sign-off`

Every rule and proof above is the plan's, section 3, word for word. None was deleted. PROOF-252
and PROOF-253 stand as they were.

## Lines a person reads

Every printed line is contract K9's, word for word: `SIGN_ASK_TYPED`, `NOT_SIGNED_ANSWERS`,
`WRONG_KEY`, `KEY_ENDING`, `NO_SSH_KEY`, `NO_TEST_RUNS`, `NOTE_CHANGED` and `TAG_NOT_HERE`.

Chosen by this lane, none of them printed by any command today:

- `signatures.standing_by_files`' three reasons, which it returns and `signoff_fact` does not
  print: `this checkout holds <tag>`, `HEAD holds no evidence package for <version>` and
  `no sign-off of <version> counts: <reason>`.
- What the answers walk prints after the last question: what the file's `sign` holds, a string
  as it is, any other value as JSON writes it (`true`), nothing where the file has no `sign`.
- In `signature_format.md`: the paragraph on the key that signed, under "The commit and the
  tag"; the two cases and the `TAG_NOT_HERE` line under "Where the status reads `signed`"; and
  `passing` in `shown.overview`, `counting the rules that pass their tests, a rule checked by
  hand alone not among them`.
- In `package_format.md`: `steps` reads `the rules whose passed status reads passed`; `audit`,
  `result` and `statuses` say what RULE-29 and RULE-11 say; the example's `steps` and `audit`
  now sum to 41 of its 42 rules, one being its hand check.

## Calls the plan did not make

1. **A version with files and no counting sign-off, and no tag, adds no warning.** RULE-130's
   warning names a tag, and here there is none to name. The status reads `not signed`, as
   PROOF-275 holds. `standing_by_files` returns the reason, so a surface can print it later.
2. **A tag that exists in the checkout and is not on `HEAD` or an ancestor is passed over in
   silence, as before**, also where `HEAD` holds that version's sign-off files. The files answer
   only where the checkout holds no tag of that name at all, as contract 4.4 says.
3. **`package.audit_counts` checks both halves of K4**: the `passed` status reads `passed`, and
   the `strong` status's word is one of the five. Section 4.4 names only the second; K4 names
   both, and `summary.audit_counts` checks both.
4. **`sign.plan` leaves a rule checked by hand alone out of `passing` itself**, as well as
   reading the package's `checked at sign-off`, so a package committed by an earlier sign-off
   of the same version gives the same overview.
5. **A commit whose signature names no SSH key** (`signed_with` gives None) is taken back too,
   printed with `NO_SSH_KEY` as K9 gives it.
6. **`signature_format.md` says more than the `key_fingerprint` cell**: its section on where
   the status reads `signed` was RULE-130's old wording. No field changed, so the version stays
   16, as section 7 says.
7. **`dev/sign_project.py`'s `signing_key` sets `gpg.ssh.program ssh-keygen`.** Four test files
   of other lanes sign through it. On a machine whose global `gpg.ssh.program` signs with a key
   of its own, RULE-136 would now take those sign-offs back.
8. **Two commits, the package first.** At the first commit two tests of
   `dev/test_signatures.py` still expect the old overview; the second commit brings them in
   line. The package's counts and the walk's overview could not be split further without a
   third state of `sign.py`.
9. **The program of PROOF-269 is a `#!/bin/sh` script** named as `gpg.ssh.program`. Git for
   Windows runs such a script through its own shell; this was not run on Windows here. If
   `python3 dev/windows_run.py` shows otherwise, the two tests of RULE-136 need a program
   Windows can start.

## Left, or waiting on another lane

- **`surfaces`**: `states._passed_cell` still reads `passed` for a rule checked by hand alone,
  so the package's `statuses.passed.word` reads `passed` there until that lane merges.
  `package_format.md` already says what it will read. `payload._feature_entry` already hands
  `changed` on as `hand_changed`; `states.rule_cells` takes it in that lane.
- **`run`**: `scripts/run/evidence.py` still writes `passed` as the section's word for such a
  rule. The package reads `checked at sign-off` whatever the section holds, so nothing here
  waits on it.
- **`words`**: `skills/sign/SKILL.md`, `docs/sign-off.md` and
  `references/evidence_and_signoff.md` quote K9 and section 6.5. Not touched here.
- **The coordinator**: decision 123's two fields in `package_format.md`, one version above 12.

## The sweep

`bash dev/run_tests.sh --fast`, in the worktree, on the final tree: `844 passed, 9 skipped`,
`Suites: 1 passed, 0 failed`. No failure waits on another lane. `git rebase main` changed
nothing: `main` was still at `e02c9b4f5`, so the sweep is the acceptance after the rebase.
