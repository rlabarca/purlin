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
| P4 one queue, no holds | 37, 48, 50, 52 | merged | 939 passed, 0 failed |
| P6 drift by role | 42 | merged | 948 passed, 0 failed |
| P5 the audit calls the model | 35, 50, 52 | merged | 980 passed, 0 failed |
| P8 init and the upgrade from 0.9.5 | 35, 36, 39, 40, 45 | merged | 1007 passed, 0 failed |
| A fix of mine: an empty pass mark warns of nothing | 35 | merged | 1008 passed, 0 failed |
| P7 a run covers what the change touched | 39 | merged | 1036 passed, 0 failed |
| S1 the dashboard, the hook removed | 36, 37, 45, 50 | merged | 1032 passed, 0 failed |
| P10 the evidence package | 52, 55 | merged | 1057 passed, 0 failed |

The count falls where tests of removed things were deleted and rises where new tests were
added. No count was edited.

## Red on main, outside the fast sweep

Nothing, as of P5. Two things were red for a while and are fixed:

| Test | Red from | Fixed by |
|---|---|---|
| `dev/test_purlin_report.py`, two hover tests | P2 | P5 |
| `dev/test_e2e_required_rules.sh`, 6 checks | P2 | P4 |

One test failed once on a clock boundary and passed on every later run:
`dev/test_drift.py::TestReportShape::test_the_report_the_views_and_the_narrowed_answer`.
P7 makes it independent of the clock.

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

### P4

- A rule whose level is `passed` is never in the queue, even when it needs a hand check.
- **A hand check signed without a note is still accepted.** The walk asks for the note and does
  not require it. You may want it required: a hand check with no note says a person checked and
  not what they saw.
- The refusal over uncommitted evidence reads the rule's own feature; the tag reads every feature.
- The walk shows each rule in a fixed shape and no longer prints the test's code.

### P6

- A rebase is measured from before it started.
- **A merge that needed conflicts resolved is not counted as a merge**, because git logs it as
  `commit (merge)` and your list named `merge`. It is a one-line change to count it.
- A checkout that does not move HEAD gives an empty range.
- "The rules behind" changed code are all of that spec's own rules.
- A file deleted in the range is in neither the covered nor the uncovered list.

### P5

- Why a rule could not be audited is kept in a file that is never committed, so the status can
  say why; nothing about a failure goes into the evidence.
- With mutation testing on, the breaks still do not run at the gate `passed`.
- Only an answer that gave no decision is tried again; a timeout or a failure is not.
- The model's name is what the model's own output reports, or `unknown`.
- A repeated audit entry is kept only when the model and the instructions also match.
- `signature_format.md` was reworded and not bumped, since no field changed.
- The evidence file's `schema` string stays `purlin-evidence/1` while its format version is 2.

### P8

- `--yes` answers no to mutation testing; `--mutation` turns it on without asking.
- The upgrade names every setting the old file carried that the new one lacks, not a fixed
  list, so six are named.
- Removing a Figma source also removes the pin that went with it.
- A yes to mutation testing during an upgrade writes the setting and says to run `purlin:init`
  to wire the tool, instead of wiring it inside the upgrade.

### P7

- At `signed`, a rule whose spec names no files leaves the queue, since nobody could clear it.
- **At `signed`, the gate check fails while any spec names no files, even if every rule in it
  is marked below `signed`.** This is stricter than you may have meant.
- The remote runner runs every feature when none is named.
- On a partial run, C# projects still run their whole suite; the other kinds run only the
  selected files.
- "Nothing to run" with `--commit` still commits evidence an earlier run wrote.

### S1

- `purlin:test` and `purlin:audit` refresh the page's data through the status they already end
  on, so setup and the remote runner, which also print the status, refresh it too.
- The top bar shows the release label from `strong` up, because one can be written at `strong`.
- The sample data names a model from 2025 (`claude-opus-4-1-20250805`), which the rule
  screenshot shows. Sample data only.

### P10

- The package is built from a temporary checkout of the commit the evidence was taken at, so a
  second clone gives the same bytes.
- `purlin:sign` also commits the package before the label at the gate `strong`; its state reads
  `gate strong met` and still not for approval.
- A package lists only the signatures that are still current; a stale one shows through the
  signed status's reason.
- The phrase "for approval" is allowed by the word guard, because your own wording needs it.

## Test gaps the proof guideline exposed

Each is a place where a test shows less than a good proof would claim. The proof now claims
only what the test shows. The five in `drift` were closed by P6; the two in `upstream` are open.

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
