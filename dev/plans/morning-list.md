# The morning list

What was done on 2026-09-27 and overnight into 2026-09-28, under decision 54. Nothing here was
audited, signed, tagged or pushed. `main` is local only.

## Where things stand

- Every piece is merged into `main` by fast-forward. The full sweep on `main` after the last
  of them: **1036 passed across 7 suites, 0 failed.**
- This repository's own tests run through the new path tie **947 of 947** markers, and **553 of
  555** rules meet the gate. The two that do not are tagged for Linux and this machine is a Mac.
- The repository holds 374 tracked files, down from 1,350.
- `purlin:init --update` found one thing here, an old git hook, and removed it with a backup.
  Plain `purlin:init` then replaced this repository's runner file and rewrote the settings file
  in its own key order, with no value changed.

## What to review, in this order

1. **What differs between 0.9.5 and 0.10.0**: `RELEASE_NOTES.md`, the 0.10.0 section. Five
   headings, and the upgrade listed step by step.
2. **The first pages**: `README.md`, then `docs/getting-started.md`. They lead with how little
   Purlin touches and the ten-minute path.
3. **The regulated page**: `docs/regulated-workflow.md`. Eight headings, ending in "No claim of
   compliance".
4. **The rest of the docs**, from `docs/index.md`.
5. **The slides**: https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is, six of them. Pictures of
   each are in `dev/plans/deck/`, with the script that builds them.
6. **The diagrams**: four, in light and dark, in `dev/plans/diagrams/`.
7. **The proof guideline**: `references/spec_quality_guide.md`, "Writing proofs", and the three
   specs rewritten to it: `specs/mcp/drift.md`, `specs/anchor/upstream.md`,
   `specs/mcp/config_engine.md`.

## Decided on the morning of 2026-09-28

Six choices were put to you; decision 56 records the answers. Two stay as they were (a hand
check without a note; a spec that names no files at `signed`). Four change, and one more piece
applies them: a merge with conflicts counts for drift; a marker that names nothing fails the
run; the tag and its package are written only at the gate `signed`; the remote runner gets a
diagram.

## What is not proven here

- **Go.** Not installed on this machine. Its report reader was tested against a sample written
  from Go's documentation. The docs say so.
- **Vitest 4.** It would not install here. Version 3 is proven.
- **Azure DevOps against the real service.** Two scripts for the work machine:
  `dev/manual/check_azure_remote.py` and `dev/manual/check_azure_provenance.py`. Each prints ok
  or FAIL per fact; the second names two fallbacks in its header, neither built.
- **The two rules tagged for Linux.** They need one `purlin:test --remote`, which pushes a
  temporary branch.

## Test gaps still open

From writing proofs to the guideline. The proof claims only what the test shows.

- `upstream` PROOF-6: the second refused source is not shown to write no copy.
- `upstream` PROOF-7: rewording the source is not shown to move the pin.

The rest of this repository's proofs, outside the three rewritten specs, are still in the
test's own words. An audit will find fault with many of them.

## Yours to delete

Local branches git would not delete for me:

- `lane/13`, `lane/14`: one commit each that is not on `main`, with their worktrees.
- `worktree-agent-*` (5, with worktrees under `.claude/worktrees/`, 199 MB): not ancestors of
  `main`, though every patch in them is on `main`.
- `lane/1B`, `lane/2B`, `lane/3`, `lane/5B`, `lane/6A`, `lane/7A`, `three-levels`,
  `two-gauges-remote-verification`, `evidence-workflow`: merged into `main`, and different from
  their copies on the remote.

On the remote, none touched: `origin/lane/*` (13), `origin/three-levels`,
`origin/evidence-workflow`, `origin/two-gauges-remote-verification`, two
`origin/worktree-agent-*`, and the tag `pre-instruction-optimization`. The local tag
`validated/1.0` is a name no longer in use. A backup of the removed git hook sits at
`.git/hooks/pre-push.local-3ed9f685.bak`.

`dev/plans/` itself stays until you have finished reviewing, then goes.

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
| P9 the marker comment, no plugins | 51 | merged | 967 passed, 0 failed |
| S2 the prose | 45, 52, 53 | merged | 968 passed, 0 failed |
| The diagrams | 45 | merged | 968 passed, 0 failed |
| The clean-release sweep, with 16 code fixes | 44, 50 | merged | 964 passed, 0 failed |
| The follow-up: pages re-quoted, the board at passed | 50, 51 | merged | 964 passed, 0 failed |
| Setup applied to this repository | 49 | committed | full sweep 1036 passed, 0 failed |

The count falls where tests of removed things were deleted and rises where new tests were
added. No count was edited.

## Every choice made on your behalf

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

### P9

- Every test command goes through bash, so an environment prefix works.
- A marker is read only from files a suite's globs match, and needs a space after `purlin:`.
- A marker ties to the next test declared after it, even with a helper between.
- In a shell or SQL suite a marker anywhere in the file counts.
- With no `tests` setting the run prints one line and runs nothing; it detects nothing.
- One shell suite was split in two, because two proofs each needed their own result.

### S2

- The solo page was merged into getting started; `running-and-records.md` became
  `running-and-evidence.md`.
- "Protected branches" is written as "branch protection", and "decides who may approve" as
  "decides who may sign the version off", because the word guard forbade the literals.
- The release notes keep the header "Unreleased — 0.10.0".

### The diagrams

- `<version>` is written with codes in place of the angle brackets inside a diagram. It
  renders correctly; the raw text shows the codes.
- The diagram in `docs/specs-and-anchors.md` was deleted: it restated the paragraphs under it.

### The sweep

- It removed one rule from a spec the prose piece owned, because a rebase conflict forced it
  and you had decided the rule goes.
- The word guard now forbids only machine spellings and no ordinary English word.
- At `passed`, a rule with neither proof nor test is sent to `purlin:build`.
- The dashboard upgrade step replaces the page only when it is a link or differs from the
  shipped one.

### The follow-up

- At `passed` with no proofs, the rule screen drops its proofs section.
- The test of the five words builds its own sample without proofs and leaves the shared
  sample as it was.

