# The morning list

What was done overnight on 2026-09-27 to 28, under decision 54. Read top to bottom. Nothing
here was audited, signed, tagged or pushed.

## Pieces

| Piece | Decision | State | Fast sweep after it |
|---|---|---|---|
| Signing is logged, not policed | 32 | merged | 1001 passed, 0 failed |
| The free scans are removed | 33 | merged | 1001 passed, 0 failed |
| Three cleanups | 34 | merged | 1001 passed, 0 failed |
| The periphery is removed | 41 | merged | 928 passed, 0 failed |
| Brand kit, wording page, leftovers | 45 | merged | 926 passed, 0 failed |
| A proof says less | 38 | merged | 906 passed, 0 failed |
| P1 fingerprint and evidence reader | 40 | merged | 930 passed, 0 failed |
| G1 the Azure remote run waits | 43 | merged | 925 passed, 0 failed |
| P2 evidence written and read | 40, 50 | merged | 916 passed, 0 failed |
| P9a the guideline for a good proof | 51 | merged | 916 passed, 0 failed |
| G2 the Azure check of who committed | 43 | merged | 937 passed, 0 failed |
| P3 levels | 36 | merged | 937 passed, 0 failed |

The count falls where tests of removed things were deleted and rises where new tests were
added. No count was edited.

## Red on main, outside the fast sweep

| Test | Since | Cause | Owner |
|---|---|---|---|
| `dev/test_purlin_report.py`, two hover tests | P2 | The page cannot say when the audit ran until the audit piece records it | S1, after P5 |
| `dev/test_e2e_required_rules.sh`, 6 checks | P2 | The suite writes runtime proof files; the status now reads evidence | P4 |

## Choices made on your behalf

One line each, with the piece that made it. Each took the smaller option.

### Mine

- The audit's checklist stays as what the AI audit looks for, in plain sentences (decision 33).
- `--quick` became `--test` with no alias (decision 34).
- A rule marked `[level: passed]` is the way one rule is exempted from needing a proof at
  `strong` (my reading of "we can still override individual rules as we can now").
- The evidence package names the commit its evidence was taken at, which is the parent of the
  commit that carries the package, because a file cannot name the commit that contains it
  (decision 55).
- The audit runs `audit_parallel` calls at once, default 4, written by init without a question.
- Drift measures from where HEAD stood before the last pull, merge, rebase, checkout, clone or
  reset, read from git's own log of HEAD; with no such entry, the last 20 commits.
- Two generated files, `.purlin/plugin-root` and `.purlin/report-stamp.js`, and five untracked
  leftover folders were removed from this checkout.

### P1

- A file named directly in `> Scope:` that git does not track counts as unmatched and is reported.
- With no git, a scope reaches nothing; the walk of the disk is gone.
- Reordering rule or proof lines does not change the spec part of the fingerprint.

### G1

- A remote that is not an Azure DevOps URL is refused before the push, so no run branch is left.
- At the 90-minute limit the run branch is kept, because the run is still going.
- An unreadable answer while polling counts as not completed.

### P2

- An audit that asks no model records `strong` with no findings, so the strong cell reads as it
  did; P5 replaces this.
- `--commit` with `--ci` or `--remote` exits 2.
- The remote runner commits its evidence files and not `.purlin/tests.md`; the next local run
  renders the table.
- A run that repeats the stored result over the same fingerprint leaves the file untouched.
- The hash of a test's screenshot and of the run log went with the record; the evidence format
  has no field for either.

### P9a

- The three specs rewritten as examples are `drift`, `upstream` and `config_engine`.
- A path the software itself writes, reads or prints counts as output a caller sees, so a proof
  may name it.

### G2

- On an Azure runner with no token, every `ci/` file fails, because a run that cannot ask has
  checked nothing.
- Files not checked on your own machine are listed under `not_checked` and do not change the
  exit code.

### P3

- The payload's schema number stays 9; the fields changed inside a schema nobody has received.
- A `[level: x]` whose value is not one of the three words is read as unmarked.
- Re-marking a rule's level puts its evidence out of date until the tests run again, as
  re-marking the bar did.
- `purlin:spec` writes no level tag; `purlin:spec-from-code` writes `[level: passed]`.

## Test gaps the proof guideline exposed

Each is a place where a test shows less than a good proof would claim. The proof now claims
only what the test shows.

- `drift` PROOF-13: no refusal of a NUL byte or a newline is shown.
- `drift` PROOF-16: the PM view's keys are shown by no proof.
- `drift` PROOF-17: the narrowed answer's top-level keys are not checked.
- `drift` PROOF-19: 7 of the report's 10 keys are checked after reading it back.
- `drift` PROOF-20: the reason on an error row is checked only for being non-empty.
- `upstream` PROOF-6: the second refused source is not shown to write no copy.
- `upstream` PROOF-7: rewording the source is not shown to move the pin.

## For the work machine

- `dev/manual/check_azure_remote.py`: four facts about the remote run on the real service.
- `dev/manual/check_azure_provenance.py`: three facts about who pushed a commit, with two
  fallbacks named in its header, neither built.

## Yours to delete

Local branches git would not delete for me, with why:

- `lane/13`, `lane/14`: one commit each that is not on `main`.
- `worktree-agent-*` (5, with worktrees under `.claude/worktrees/`, 199 MB): not ancestors of
  `main`, though every patch in them is on `main`.
- `lane/1B`, `lane/2B`, `lane/3`, `lane/5B`, `lane/6A`, `lane/7A`, `three-levels`,
  `two-gauges-remote-verification`, `evidence-workflow`: merged into `main`, and different from
  their copies on the remote.

On the remote, none touched: `origin/lane/*` (13), `origin/three-levels`,
`origin/evidence-workflow`, `origin/two-gauges-remote-verification`, two
`origin/worktree-agent-*`, and the tag `pre-instruction-optimization`. The local tag
`validated/1.0` is a retired name.
