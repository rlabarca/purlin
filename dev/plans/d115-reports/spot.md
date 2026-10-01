# Lane `spot`, round 1

Branch `lane/d115-spot`, from `d115/base` at `e2c3023d4`. Specs: `plain_checks` (20 proofs),
`planted_bug` (13 proofs). Files written: `scripts/review/plain_checks.py`,
`scripts/review/targeted_break.py`, `dev/test_plain_checks.py`, `dev/test_planted_bug.py`, this
report. No file under `specs/` changed; no format file is this lane's in K14.

## Tests

`python -m pytest dev/test_plain_checks.py dev/test_planted_bug.py -q`

| When | Passed | Failed | Skipped |
|---|---|---|---|
| Before the first change | 0 | 0 | 0 (neither file existed) |
| After the last change | 33 | 0 | 0 |

- Skipped for a missing tool: none. The tests need only `git` and `python3`.
- Waiting on another lane: none.
- The deliberate break: `_all_pass` in `targeted_break.py` was made to answer `True`, so every
  planted bug reads `survived`. 4 tests failed (`planted_bug PROOF-3`, `PROOF-13`, `PROOF-8`,
  `PROOF-12`). It was restored with `git checkout -- scripts/review/targeted_break.py`, and the
  33 tests pass again.

## Section 4's row

| | Gone | Reworded | To add |
|---|---|---|---|
| As found | 0 | 0 | 33 |
| As left | 0 | 0 | 0: 33 added, one marked test per proof |

Appendix A's script over both files, last line: `0 gone, 0 reworded, 33 right as they stand.`
The proof ids in the tests match the spec's ids exactly: 20 of `plain_checks`, 13 of
`planted_bug`.

Reworded comments: none, since both files are new. Tests deleted: none.

K15's greps over the four files find nothing. One near miss was fixed: `surrogateescape`
matched `gate`, so paths are now decoded with `os.fsdecode`. No character above ASCII in any
of the four files.

## Lines a person reads that this lane chose

**`plain_checks`, the language in `NOT_READ`:** `Python`, `JavaScript`, `TypeScript`, `C#`,
`Go`, `shell`. A file of any other language is named by its extension without the dot, as in
`The test checks nothing is not read in rb tests.` Printed by `check_project`, once per check
and language.

**`targeted_break`, the `why` of a `not made` result.** The audit prints these. `audit`'s line
`PROOF-1: no bug was planted: <why>.` carries them.

| Constant | Words |
|---|---|
| `NO_CHANGE` | `the answer named no change` (from K9) |
| `OUTSIDE` | `../outside.py is outside the copy of the project` |
| `NOT_IN_SCOPE` | `README.md is not a file the feature's scope names` |
| `NO_FILE` | `src/gone.py is not in the project` |
| `NOT_FOUND` | `the lines before the change are not in src/age.py` |
| `FOUND_MORE` | `the lines before the change are in src/age.py 2 times, not once` |
| `NO_DIFFERENCE` | `the change leaves src/age.py as it was` |
| (the model not reached) | the reason `ModelUnreachable` carries, passed through unchanged (`claude is not on PATH` and the rest of section 6 are `audit`'s to raise) |

Every finding line is the spec's, word for word.

## Differences from section 3's contracts

1. **`plain_checks.check_project(project_root, features=None, out=None)` is added.** It reads
   every marked test of the project, or of `features`, against its proofs. It prints `NOT_READ`
   once per check and language, and answers one entry per finding:
   `{'feature', 'proof', 'file', 'name', 'check', 'finding'}`. `plain_checks PROOF-28` ("the
   audit prints … exactly once") and `PROOF-30` (the spot tests over a project of three features)
   need a whole-project pass, and no lane's contract held one. `audit_run.run` can call it
   rather than repeat the dedup. Within one call it caches each file's text and syntax tree. Over
   this repository's 2,185 marked tests it takes 3 seconds.
2. **`targeted_break.break_proofs(project_root, jobs, ask, out=None, timeout=None)` is added,
   answering `(results, exit code)`.** On `ProjectChanged` it prints `STOPPED`, runs no later
   job and answers 1. Otherwise it answers 0. `planted_bug PROOF-7` and `PROOF-13` say "the
   audit prints … and exits", and `audit_run` is a stub until `audit` lands, so these two proofs
   are shown through `break_proofs`. `audit_run.run` should call it rather than reimplement it.
3. **`break_proof` gains `timeout=None`**, the seconds the proof's tests may run, as
   `--arm-timeout` sets them. `planted_bug PROOF-14` needs it. It defaults to
   `purlin_run.ARM_TIMEOUT_DEFAULT`.
4. **The shape of `proof` in `break_proof`:** `{'id', 'text', 'rule', 'rule_text'}`, which fills
   the request's `proof`, `proof_text`, `rule` and `rule_text`. A bare `'PROOF-N'` string is also
   accepted.
5. **`ProjectChanged.path`** carries the path. It is the first path, sorted, whose status or bytes
   differ.
6. **`ModelUnreachable` is caught by its class name.** `ai_audit.py` at the base does not define
   it yet, and importing `ai_audit` here would tie the two modules together. Any other exception
   from `ask` is raised again.
7. **`parse_answer(text)` is public.** It removes a fence of three backticks around the answer
   before reading it. An answer with no `file:` line, no `before:` lines or no `after:` line
   reads `not made` with `the answer named no change`.
8. **A `not made` result** still carries `file`, `before` and `after` where the answer named them.
   Its `line` is `None` and its `finding` is `None`. `why` is `''` for `caught` and `survived`, as
   K2's example has it.

## Calls this lane made that no decision or spec makes, left for the owner

- **Which checks each language is read for.** Python, JavaScript, TypeScript and C# are read for
  all six. Go is not read for 3 (no `try`) or 5 (no mocking pattern read). Shell is read for 1,
  2 and 6 only. Any other language is read for 6 only.
- **Check 6 names the first backticked value** when the file holds none of several. The spec's
  finding has room for one `<value>`.
- **The checks were narrowed after one read-only pass over this repository's own tests.** The
  pass called no model and wrote nothing.
  - Check 4 fires only where both sides are the same call with the same arguments, and no call
    stands between the binding and the assertion. Before this, 61 tests of the
    "snapshot, act, compare" kind were flagged, such as `before = _files(); …;
    assert _files() == before`.
  - Check 2's "a value compared with itself" holds no call. A compared call is check 4's, so
    `assert days == days` reads check 2 alone.
  - Check 3's "does nothing" is `pass`, an empty block, or a lone constant. A handler that
    `continue`s is a deliberate skip, which removed 4 false alarms.
  - Check 1 counts `raise AssertionError(...)` as an assertion. One false alarm went.
  - A helper "defined in another file" stops check 1 only where that file is of the same
    language and holds an assertion.

  What is left on this repository: 18 findings, all from check 6. Nobody has read them yet;
  that is integration's step 9.
- **The copy holds no `.git`.** A proof's test that needs git inside the copy fails there and
  reads `caught`.
- **The guard runs `git status --porcelain -z` as K9 gives it, without `-uall`.** An untracked
  folder is listed once and hashed whole.

## Left unbuilt, open, or failing elsewhere

- Every proof of both specs is built as worded. `planted_bug PROOF-7` and `PROOF-13`, and
  `plain_checks PROOF-28`, are shown through this lane's own functions, which stand in for
  "the audit": `break_proofs` and `check_project`. Once `audit` lands, integration may want them
  shown through `audit_run.run` as well.
- `plain_checks RULE-7` asks for a skipped check to be named "once per check and language".
  `check_project` does this within one call. Nothing stops `audit_run` from printing it again in
  a second call.
- No failure seen in a file this lane does not own. Nothing outside `scripts/review/` imports
  either module yet.

## Cost

This session cannot read its own cost.
