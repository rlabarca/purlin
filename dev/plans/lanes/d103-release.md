# Decision 103, lane `release`

Built on `lane/d103-release` from `origin/d103/base`: C5 in the new `scripts/export/release.py`,
C7 and package format 7 in `scripts/export/package.py`, evidence format 7's wording, the
`RECORDS` change in `fingerprint.py`, and the export skill's words (88 lines, ceiling 90).

## Highest lines after the work

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/export/release.md` (new) | 12 | 16 |
| `specs/export/package.md` | 31 | 64 |
| `specs/mcp/evidence.md` | 33 (unchanged) | 85 (unchanged) |
| `specs/skills/skill_export.md` | 14 | 36 |

## Tests before and after

The four owned files (`dev/test_export.py`, `dev/test_tag.py`, `dev/test_fingerprint.py`,
`dev/test_skill_export.py`):

- At `d103/base` on this Linux container: 156 tests, 155 passed, 1 failed
  (`test_tag.py::test_the_tag_is_signed_with_the_key_the_settings_name`, which is now deleted).
- After, as committed: 128 tests. 72 pass, 49 fail and 7 error, all because
  `summary.BLOCKING` (lane `counting`) does not exist yet.
- After, with `BLOCKING` stubbed into `summary.py` as C3 gives it (a temporary edit, never
  committed): 125 pass and 3 fail, and those 3 wait on lane `counting` (listed below).
- `bash dev/run_tests.sh --fast`: 2115 passed, 60 failed, 8 errors, 9 skipped. 56 of the failures
  and errors are in owned files and wait on `BLOCKING`. The rest are listed under
  "Failures in files this lane does not own".

## Deliberate break

`blocking = summary_module.BLOCKING + ('to_strengthen',)` in `run_release`'s `blocking_rules`.
The PROOF-12 test (`test_a_weak_or_unaudited_rule_does_not_refuse`) failed with
`No release: 1 rule does not pass at <sha7>: login RULE-1. ...`. The file was then restored with
`git checkout -- scripts/export/release.py`, and the test passed again. The test ran with the
`BLOCKING` stub in place and no model.

## Rules and proofs, by number

- `specs/export/release.md`: new, RULE-1 to RULE-12 and PROOF-1 to PROOF-16, as section 4 lists
  them, with four changes:
  - PROOF-3 uses an uncommitted new file `NOTES.md`. Editing `src/login.py` makes the evidence
    out of date, so the failing-rule check fires first.
  - PROOF-12 runs at `signed` and ends on `READY_TO_SIGN`. At `passed` today's payload has no
    strong cell, so the break could not be seen before lane `counting` merges.
  - In PROOF-13, the test file is edited and its tests run again in one commit.
  - PROOF-15 uses a tag named `passed`, which blocks every tag under `passed/`.
- `specs/export/package.md`:
  - Deleted: RULE-13 (signatures) and RULE-27 (not applying), and PROOF-6, 7, 19, 23, 24, 27,
    28, 31, 58 and 59, each with its test.
  - Reworded rules: RULE-1 (version as `purlin:test --release` reads it), RULE-3 (17 keys,
    `purlin-package/3`), RULE-4 (the count that pass; `not finished` only on a blocking line),
    RULE-5 (the to_tag clause goes), RULE-7 (evidence only) and RULE-14 (two statuses at both
    gates).
  - Reworded proofs: PROOF-1 and PROOF-38 (`State: finished.`), PROOF-3, PROOF-12, PROOF-17 (the
    edit is now `"passed"` to `"failed"`), PROOF-20, PROOF-29 and PROOF-46 (`purlin-package/3`),
    and PROOF-55.
  - "Signed and tagged" becomes "released", meaning released at `passed` as `passed/2.1.0`, in
    PROOF-9, 11, 14, 15, 25, 26, 39 and 56. PROOF-15 no longer counts `committed_at`.
  - New: RULE-29 with PROOF-61 and PROOF-62, RULE-30 with PROOF-63, and RULE-31 with PROOF-64.
- `specs/mcp/evidence.md`: RULE-31 and PROOF-82 are reworded from a `*.signatures/` file to a
  sign-off file under `.purlin/evidence/package/<version>.signoffs/`.
- `specs/skills/skill_export.md`: PROOF-29 is reworded (`git show <the release tag>:...`), and
  RULE-14 with PROOF-36 is new.

Every proof written or rewritten is at most 60 words and has a marked test of its own.

## Calls left

- `only_signoffs_since(project_root, commit)` takes no version. It accepts commits that touch
  only `.purlin/evidence/package/*.json` or `.purlin/evidence/package/*.signoffs/**`.
- `uncommitted_work` now returns a bool, as C5 says. The old copy in `sign.py` returned a list;
  lane `signoff` deletes that copy.
- `TAGGED` names HEAD after the package commit, which is the commit the tag is on. The tag's
  message names the commit the package describes.
- `run_release` treats any gate but `signed` as `passed`, so a project still at `strong` releases
  as `passed` until lane `settings` merges.
- `package.commit()` lost its `signed` argument. A plain `git commit` signs where
  `commit.gpgsign` is on.
- `package.py`'s own `NO_VERSION` still names `purlin:export --release`.
- `hand_checks` entries carry `checked`, as C13 gives it: false at `passed`, `in the sign-offs` at
  `signed`.

## Words chosen that section 7 does not give

- When only test comments block a release, the first slot of `NO_RELEASE_FAILING` reads
  `1 test comment does not count` (`<n> test comments do not count`), and the third reads
  `1 test comment to correct`.
- The export skill: `purlin:export writes the package at any time, at any gate, and releases
  nothing. A version is released by purlin:test --release, which commits the evidence and the
  package and tags passed/<version> at the gate passed; at signed the first purlin:sign tags it.`
- The export skill's state row: `finished`: `No line of left stops a release: every rule's tests
  pass, and a weak rule or one with no proof may still be listed`. Its mismatch directive:
  `→ Run: git show <the release tag>:.purlin/evidence/package/<version>.json`.
- Package format 7's prose on the state, the hand checks and the sign-offs beside the package.

## Failures in files this lane does not own (from `--fast`)

- `dev/test_signatures.py`, 6 failures, and `dev/test_init_scaffold.py`,
  `test_with_the_rule_signed_the_signed_tag_is_written`: `sign.py` still calls
  `package.write_for_tag`, which is deleted here. Lane `signoff` rewrites `sign.py`. Section 6
  expects the walk to be broken between the `release` and `signoff` merges.
- `dev/test_states.py`, 4 failures and 1 error (the does-not-apply anchor tests and the fixtures
  contract): `fingerprint.RECORDS` no longer excludes `specs/**/*.signatures/`, so a
  not-applying signature file now changes the anchor's code part. Lane `counting` deletes these
  tests with decision 101's signature as not applying.

## Tests that fail only because another lane has not merged

- Lane `counting`:
  - Every test in `dev/test_tag.py`, and every test in `dev/test_export.py` that builds a
    package, needs `summary.BLOCKING`.
  - PROOF-61 needs `summary.audit`.
  - PROOF-63 needs `to_sign` deleted from `left`.
  - PROOF-29 needs the strong cell at `passed`.
- Lane `signoff`: the tag at `signed` written by a sign-off is not tested here.
