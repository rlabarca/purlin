# Lane `signoff` of decision 103: report

Branch `lane/d103-signoff`, made from `origin/d103/base` at `e5f82d0`. Builds C6, C8, C9 and
signature format 14; rewrites `sign.py` around the sign-off walk and the sign skill to it.

## Highest lines after the work

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/review/signatures.md` | 111 | 222 |
| `specs/skills/skill_sign.md` | 31 | 62 |

## Tests before and after

| File | Before | After |
|---|---|---|
| `dev/test_signatures.py` | 114 tests | 51 tests |
| `dev/test_skill_sign.py` | 33 tests | 16 tests |

Both files pass whole, 67 of 67, when run with a scratch stand-in for lane `release`'s
`scripts/export/release.py` helpers (C5) and for the two things lane `counting` changes
(`summary.BLOCKING`, and the payload no longer calling the deleted signature readers). The
stand-in lives only in the lane's scratch folder and is not committed. Without it, on this
branch alone, `dev/test_signatures.py` cannot be collected (`import release` fails), which C6
and section 6 expect until lane `release` merges.

`bash dev/run_tests.sh --fast` on this branch: collection stops on 6 errors, every one an import
of something another lane moves or deletes (listed below). The same sweep run with the stand-in
and those 3 uncollectable files held out: 104 failed, 1895 passed, 9 skipped, 12 errors; every
failure is one listed below. `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`
errors at setup on `d103/base` too, before any change.

## Rules and proofs deleted or reworded

`specs/review/signatures.md`:
- Rules deleted, with their proofs and tests: 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 18, 19,
  23, 42, 43, 45, 46, 49, 53, 54, 55, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66, 68, 69, 70, 71, 72,
  73, 74, 75, 76, 78, 80, 82, 85, 86, 87, 88, 90, 91, 92, 93, 94, 95, 96, 98, 99, 100.
- Proofs deleted: 1, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 20, 23, 24, 29, 30, 31, 32,
  33, 63, 64, 65, 67, 68, 70, 74, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93,
  94, 99 to 113, 119 to 131, 134 to 151, 154, 156, 159, 160, 161, 163, 165, 172 to 177, 179 to
  191, 194 to 199.
- Rules kept and reworded to a sign-off: 17, 20, 21, 22, 50, 60, 67, 77 (no feature any more),
  79 (`NOT_MADE`'s new words), 81, 83, 84, 89, 97, 101.
- Proofs kept and reworded: 21, 22, 25, 27, 28, 75, 95, 96, 97, 98, 115 to 118, 132, 133, 152,
  153, 155, 157, 158, 162, 164, 166 to 171, 178, 192, 193, 200, 201. PROOF-170 and PROOF-171
  now read a weak `login RULE-2` that is not a hand check, since a hand check's stop shows no
  audit. PROOF-201 reads a package that lists no test for a proof: a rule whose proof has no
  test is `no_test`, which blocks a release, so the walk reaches `tied to no test` only where
  the package lists none.
- New: RULE-102 to RULE-111, PROOF-202 to PROOF-222, as section 4 numbers them.

`specs/skills/skill_sign.md`:
- Rules deleted: 2, 6, 7, 8, 9, 12, 14, 17, 18, 19, 21, 22, 24, 26, 27, 28. Proofs deleted: 2, 6,
  7, 8, 19, 30, 31, 40, 41, 44, 45, 46, 47, 49, 50, 52, 53, 55, 56, 57, 58.
- Kept and reworded: RULE-3 (every outcome now carries a directive), RULE-5 (the two conditions
  of a sign-off), RULE-13, RULE-25; RULE-1, 4, 10, 11, 15, 16, 20, 23 kept as they were, their
  proofs pointed at the section that now holds the words.
- New: RULE-29 (PROOF-59, PROOF-60), RULE-30 (PROOF-61), RULE-31 (PROOF-62).

Signature format 13 to 14, in the same commit as the code.

## Deliberate break

`package_hash` written from the package's `commit` in place of its `fingerprint`: PROOF-217's
test failed (and PROOF-214's), then `git checkout -- scripts/review/sign.py` restored it and the
test passed. The first attempt at this break ran before the rewrite was committed, so the
checkout restored the old file; the rewrite was written again from the same text and committed
before the break was run a second time.

## Calls left or made

- **The order of `NO_VERSION`.** C8 lists it after the seven refusals, but the package refusal
  names the version, so the version is read third: gate, uncommitted work, version, package,
  moved, failing, behind, already signed, key.
- **"The package's commit" and the sha in `NO_SIGNOFF_MOVED` and `OVERVIEW`** are the commit that
  added the package file (where `passed/<version>` would sit), matching C8's examples, which
  name `3c9d2e1`, the tagged commit. The sign-off file's `commit` and the tag's `Commit:` line
  are the package's own `commit` field, as C6 and C5 say.
- **`release.only_signoffs_since(root, commit)`** is called with the commit that added the
  package and read as covering the commits after it (`commit..HEAD`), since that commit itself
  touches the package. Lane `release` should build it so.
- **A later sign-off** writes the tag when `signed/<version>` does not exist yet, not only when no
  sign-off exists, so a first sign-off whose tag git refused is tagged by the next.
- **`ALREADY_SIGNED`** reads HEAD's file for the signer's slug and compares its `package_hash`
  with the package's fingerprint; a sign-off over an earlier package of the same version is
  written over.
- **The overview counts** `passing` and the audit's three numbers over the rules that are not
  hand checks, so `38 + 2 = 40` and `30 + 2 + 6 = 38` as in C8's example.
- **One `Results` line per system** takes a current section before one that is not, and `ci`
  before `local` on a tie; the machine falls back to the runner, then `an unnamed machine`.
- **A stop's answers**: an empty or unknown line asks again; the end of input stops the walk.
  At the strong list an empty line is `go on`. `note` with an empty line records nothing.
- **`--show` prints the strong list** under `STRONG_ASK` with its trailing space cut, so the agent
  relays C8's exact question; it prints no stop's question.
- **`--answers` with no `strong` key** reads as `go on`; a hand check answered `continue`, or
  `note` with no line, counts as no answer.
- **`--show` checks the key** like the walk, since the key is among C8's refusals.
- **A sign-off commit git refuses** leaves no file behind: the file is unstaged and removed, or
  put back as HEAD held it.

## Words chosen that section 7 does not give

- `OTHER_PACKAGE = 'it signs another evidence package than the one committed'`, the reason a
  sign-off does not count when its `package_hash` is not the committed fingerprint.
- `NO_SOURCE = "      the test's source was not found"` is C8's; the machine fallback
  `an unnamed machine` is chosen.
- The command-line errors: `--answers needs the file that holds them.`,
  `--release needs the version to sign.`, `unexpected argument <x>`,
  `--show and --answers are two steps; name one.`, and the usage line
  `Usage: sign.py [--show | --answers FILE] [--release NAME] [--project-root DIR]`.
- `--help`'s first line: `Sign a release's evidence package, as a signed commit.`
- The skill's closing table: `→ Run: purlin:build <feature>, then purlin:test --release` after a
  stop; `→ Run: purlin:sign when the person is ready` after `Nothing was signed.`;
  `→ Ask the person about that stop, then run: purlin:sign --answers <file>`;
  `→ Ask another person to run: purlin:sign`; `→ Fix what git named, then run: purlin:sign`;
  `→ Fix what git named, then write the tag: git tag -s signed/<version>`.
- The skill's description: `Sign a release's evidence package after walking what a person has to
  look at, as a signed commit`.

## Failures in files this lane does not own

- `scripts/review/ai_audit.py` (lane `run`) imports `not_a_rule` from `sign`, which C12 deletes;
  so does `dev/test_ai_audit_tests_named.py`. Every audit run and `dev/test_ai_audit.py` fail to
  import. The helper and its line `<feature> <RULE-N> is not a rule any spec has. Run
  purlin:status <feature> to see its rules.` belong in `ai_audit.py` now.
- `dev/test_tag.py` (lane `release`) imports `DOUBLED_SPEC` from `dev/test_signatures.py`, which
  no longer holds it.
- `dev/test_export.py` and `scripts/export/package.py` (lane `release`) call `sign.tag_if_met`,
  `sign.write_signature`, `signatures.load_signatures`, `is_current`, `commit_date` and
  `signed_hash`, all deleted by C6 and C12.
- `scripts/mcp/purlin/payload.py` and `states.py` (lane `counting`) call
  `signatures.load_signatures`, `test_hash_kind`, `audit_hash`, `commit_date` and `is_current`;
  every payload build fails until that lane's C4 lands. That one cause accounts for the failures
  in `dev/test_run_script.py`, `dev/test_evidence_writer.py`, `dev/test_mutation_adapters.py`,
  `dev/test_schema_spec_format.py`, `dev/test_mcp_server.py` (the tool calls),
  `dev/test_purlin_docs.py` (the two quoted runs) and every other test that builds a payload.
- `dev/test_init_scaffold.py` (lane `settings`), `TestTheThreeGates`: four tests call
  `sign.sign_and_commit` and the old tag.
- `dev/test_report_refresh.py` (lane `dashboard`): two tests sign a rule with the old command.
- `dev/mcp_project.py` and `dev/sign_project.py` (frozen) still read `signatures.signed_hash` and
  `load_signatures` in `Project.signature`, `Project.load` and `Project.signatures`; section 6
  step 2 deletes them. This lane's tests call none of them.

## Tests that fail only because another lane has not merged

Every test in `dev/test_signatures.py`: the module imports `release` (lane `release`), and the
walk reads the payload's `left` against `summary.BLOCKING` and builds the payload without the
signature readers (lane `counting`). Among them the ones that also need lane `release`'s own
behaviour: PROOF-178, PROOF-215 and PROOF-216 (`release.write_tag`, `tag_name`, `tag_exists`),
PROOF-203 (`uncommitted_work`), PROOF-204 (`package_at_head`), PROOF-205
(`only_signoffs_since`), PROOF-207 (`behind_host`, `behind_words`). PROOF-206 needs lane
`counting`'s `BLOCKING`. `dev/test_skill_sign.py` passes on this branch alone.

Two notes on the environment, for integration: the cloud container's global git settings sign
with a program of its own (`gpg.ssh.program`) and negotiate pushes (`push.negotiate`), so the
test key helper sets `gpg.ssh.program ssh-keygen` in each throwaway checkout and PROOF-207's
pushes pass `-c push.negotiate=false`. Neither changes what is tested.
