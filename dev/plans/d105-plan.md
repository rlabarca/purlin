# Decisions 104 to 107: collaboration as a rule, the second check's answers, no release step, nothing to check

Written by the planning agent on 2026-10-01, revised the same day for decision 106, against `main`
at `b4a235e39`. It builds decision 104 (one rule, one scripted proof that three people reach a
signed version through git), decision 105 (the answers to `sanity-qa-product-2.md`, N1 to N12)
as decision 106 amends it, and decision 106 (Purlin keeps the evidence and the sign-off and
tracks no release), and decision 107 (an anchor rule with nothing to check passes, and says so).
The later decision holds: where 105 names the release run, its package or
its push line, 106's committed evidence and sign-off replace them.

Eleven lanes run at once on this Mac, each in a worktree
`/Users/richlabarca/LocalCode/purlin-wt/d105-<lane>` on branch `lane/d105-<lane>` made from
`main` at the stubs commit of section 1, each owning files no other lane writes. One integration
agent then merges them into `main` in the order of section 5. Section 2 is the contract: every
lane builds to it and none chooses. Section 7 holds the two questions decisions 104 to 107 leave
open; the plan is written to each recommended answer.

The owner's answers to the first version of this plan, built to as written:

- **The table's merge (old Q1):** moot; `.purlin/tests.md` goes entirely (106).
- **Remote results (old Q2):** a remote result counts only when taken on the same version of the
  code as the rest, with no release branch required (106).
- **Reworded proofs (old Q3):** the tests change; the roughly 198 tests of this repository whose
  proof was reworded after the test last changed are read and fixed in this round (106).

What the three decisions ask, and where it is built:

| Asked | Contract | Lanes |
|---|---|---|
| 106: no release step, no `passed/<version>`; `purlin:test --release` and its package commit go | C1, C13 | run, package, counting, every words lane |
| 106: at `passed` the status and the dashboard say met or not met, on the committed evidence | C8 | counting, dashboard |
| 106: the hand-off is run (here, and `purlin:test --remote` for other systems) and commit | C1 | run |
| 106: a result counts for the sign-off only when taken on this exact version of the code | C2 | package, signoff |
| 106: `purlin:sign` reads the committed evidence, refuses and names what to run again, opens by naming who ran the tests, where and when, builds the package, walks, one signature, the first writes `signed/<version>` | C3, C4 | package, signoff |
| 106: a hand check's note is asked for, not required; empty is `no note` | C4 | signoff |
| 106: `.purlin/tests.md` goes | C1, C13 | run, settings, words, docs |
| 105 and 106: a test comment whose proof was reworded after the test last changed is a test comment to correct; the ~198 here are fixed now | C5, C14 | drift, counting, run, words, every lane owning a test file, tests |
| 105: the audit keeps a rule's result until that rule's own test changes | C6 | counting, run (format) |
| 105 N1: a weak test under a hand check is shown and counted as weak | C8, C4 | counting, signoff |
| 105 N2: the first sign-off names pushing the branch and the tag; a later one waits for the tagged commit | C4 | signoff |
| 105 N5: the package names the project from its own files; setup writes it | C9 | settings, counting |
| 105 N9, N10: drift's wording line clears once the test changed; a number written twice is not a change | C5, C10 | drift |
| 105 N11: `purlin:sign --show` needs no key | C4 | signoff |
| 105 N12: the smaller items | C4, C8, C10, C9 | signoff, counting, drift, settings, docs |
| 104: the scripted three-person test, with a test left on a moved proof and a second signer | C11 | team |
| 107: a rule whose test finds nothing to check skips with a reason through the test tool's own skip; Purlin reads the reason from the reports, counts the rule as met, shows the reason on the status, the dashboard and in the package; the quality guide teaches "for every X in the project, Y holds"; no project-side way to say a pulled rule does not apply | C15 | run, counting, package, dashboard, words, docs |

## 1. Rules for every lane

`d103-plan.md` section 1 applies as written, with these names and changes.

- **Before the lanes: the shared stubs, one commit on `main`.** The agent that starts the lanes
  commits, alone and first, `chore: the shared interfaces of decisions 104 to 106, as stubs`, and
  every lane branches from it. It holds, each with the docstring section 2 gives:
  - `scripts/mcp/purlin/project.py`: `project_name` answering the folder's name.
  - `scripts/mcp/purlin/wording.py`: C5's constants and a **working, unoptimized**
    `stale_comments` built to C5's definition (no cost bound yet), and its command line
    `python3 scripts/mcp/purlin/wording.py [--project-root DIR] [--file PATH ...]`, printing
    each entry's `text`, one per line, then `<n> test comments to correct.` (`1 test comment to
    correct.`, `No test comment to correct.`), exit 0. Every lane uses it to find the comments
    in its own test files (C14). Lane `drift` then makes it meet the cost bound.
  - in `scripts/export/package.py`: `project_version` (moved from `release.py`, which stays
    until lane `package` deletes it), `only_records_between` (answering False), `same_code`
    (False), `time_words`, `run_lines` (`[]`), and C3's constants.
  Nothing else changes in that commit, and the sweep is unchanged by it. Each stub's owner
  (section 3) replaces it.
- **Worktree and scratch.** Lane `<lane>` runs
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/d105-<lane> -b lane/d105-<lane> main`
  (with `main` at the stubs commit) and works there alone, with its own scratch folder
  `/private/tmp/d105-<lane>/` no other agent reads or writes. It writes only the files section 3
  gives it. Where it calls what another lane builds, it calls it exactly as section 2 names it,
  and the tests that need it fail until that lane merges (each lane's section lists them).
- **Environment (this Mac).** Before any test:
  `export PATH=/opt/homebrew/opt/dotnet@8/bin:/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH`.
  A lane runs its own test files whole with `python -m pytest <files> -q`, then
  `bash dev/run_tests.sh --fast` once at the end. Never the full sweep. Eleven lanes share the
  machine: one pytest process at a time, never `-n`.
- **Frozen:** `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
  `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`. A lane
  that needs a helper writes it in its own test file.
- **No generated file is staged:** `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/report-data.js`, `docs/images/*.png`, `dev/plans/deck/*.png`,
  and `.purlin/tests.md` while it still exists.
- **Proofs.** Every proof written or rewritten holds one case in at most 60 words and has a marked
  test of its own. New rules and proofs take numbers in order from the next free ones section 3
  gives, which follow each spec's `> Highest-Rule:` / `> Highest-Proof:` at `b4a235e39`, and raise
  those lines. A number is never reused, a deleted one included. A proof names what a person sees
  or a file holds, never a function inside the code (decision 98).
- **Test comments to correct, in every lane's own test files (C14).** Before its last commit,
  each lane runs `python3 scripts/mcp/purlin/wording.py --file <each test file it owns>` and
  leaves none: a proof it reworded, and every comment already listed there.
- **Clean release** (decision 44). What this plan retires is deleted outright: its code, its
  constants, its rules, its proofs and their tests, its lines in skills, references and docs. No
  test that a removed thing is absent, no compatibility reader. `RELEASE_NOTES.md` is the one
  place history is kept. Each lane greps its own files for `--release`, `passed/`,
  `release run`, `tests.md`, `READY_TO_SIGN`, `TO_RELEASE`, `finished` and `released`, and
  leaves none that C13 retires.
- **A rule that survives in part is reworded, not split into an old and a new one.** Its number
  stays. A rule that moves to another spec (C13) is deleted in the old spec and written new in
  the new one, with that spec's next numbers.
- **Formats.** A change to a format's parsing or emission updates its file under
  `references/formats/` in the same commit, with the number C12 gives.
- **Instruction lengths** (`dev/skill_checks.py` `CEILINGS`): status 100, test 120, build 130,
  init 250, audit 105, sign 185, export 90, spec 210, spec-from-code 130, drift 150, anchor 160,
  agent 135. Today: status 99, test 119, build 128, audit 104, export 88, sign 165, spec 192,
  drift 91, init 187, agent 132. Every line added to status, test, build, audit or export cuts one.
- **Deliberate break.** Each lane breaks its most important change on purpose (named in its
  section), sees its own test fail, then restores the file with `git checkout -- <that file>`,
  never `git checkout -- specs/`. No real `claude` on `PATH`, no git host, `gh`, `az` or network:
  every repository a test makes is local, a "host" is a bare repository on disk.
- **A call no decision makes and this plan does not make:** build the rest, leave that thing as
  it is, report it.
- **Commits** on the lane branch with the prefixes of `references/commit_conventions.md`, each
  ending with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01W6UPm3QPtMvgPNfN6W9vBE
  ```
  Push nothing. No `purlin:audit` or `purlin:sign` against this repository, no real `claude`.
- **Do not edit `dev/plans/three-levels.md`**: another agent is writing to it.
- **Report** (in the last message and in `dev/plans/lanes/d105-<lane>.md`, committed on the lane
  branch): each spec's Highest lines after the work; tests before and after; every rule and proof
  deleted, moved or reworded, by number; every test comment to correct it cleared, as C14's
  table; every call left; every word chosen that section 6 does not give; every failure in a file
  it does not own; every test that fails only because another lane has not merged.

## 2. Contracts

What two lanes share, fixed word for word. `<...>` is filled in. Filled examples use the sample
project of `sanity-qa-product-2.md`: `labconnect`, `dana.dev@labconnect.example` on
`dana-laptop`, version `0.1.0`, `HEAD` at `1cf829e`.

### C1. The hand-off: run and commit, lane `run`

`purlin:test --release` goes, with `release.py`'s call, `RELEASE_RUNS_ALL`, the usage lines and
`--release`'s exit code. The developer's hand-off is `purlin:test --all --commit`, and
`purlin:test --remote` for any proof tagged for another system. What changes in a run:

1. **A section names the code it describes.** Its `commit` is `HEAD` after the run's own work
   commit (`purlin: specs, tests and settings ...`), where `--commit` made one, else `HEAD` when
   the run started. `dirty` stays as now.
2. **A section carries who ran it.** A `local` section gains `email`, the runner's
   `git config user.email`, or `unknown`; kept and never compared, like `hostname`.
3. **Retention keeps only the same code.** A run that sees the same thing over the same
   fingerprint on the same machine leaves the section as it is only where
   `package.only_records_between(<its commit>, <the new commit>)` holds; otherwise it writes the
   new `at`, `commit`, `dirty` and `email`. So running twice on one commit commits nothing new,
   and a run on new code moves every section it runs onto that code.
4. **`.purlin/tests.md` goes.** `evidence.write_table`, `render_table`, `newest_sections`,
   `TABLE_*`, `TABLE_PATH`, its place in the evidence commit and every mention go. A checkout
   that still holds the file is left alone; this repository's own copy is deleted by integration.
5. Every `--test`, `--audit` and `--remote` run prints each test comment to correct (C5) after
   the markers lines, with no change to its exit code.

### C2. The same version of the code, lane `package`

In `scripts/export/package.py`:

```python
def only_records_between(project_root, older, newer):
    """True when `older` is `newer`, or an ancestor of it from which every commit up
    to `newer` changes only paths under `.purlin/`."""

def same_code(project_root, section_commit, head=None):
    """only_records_between(section_commit, head or HEAD), and False for an empty commit."""
```

A result counts for a sign-off when its section is current (its fingerprint, as now), not
`dirty`, and `same_code` holds for its `commit`. A `ci` result taken at `X` and pulled home by
`purlin:test --remote` as a commit that changes only `.purlin/` counts. No release branch is
needed. The status and its cells do not use `same_code` (section 7).

### C3. The package, format 8, lane `package`

`release.py` is deleted. `package.build(project_root, version=None)` is what `purlin:export`
and `purlin:sign` call. Schema `purlin-package/4`.

- `TOP_LEVEL = ('schema', 'met', 'rules', 'steps', 'audit', 'left', 'purlin_version',
  'project', 'version', 'tag', 'commit', 'runs', 'gate', 'mutation_engine', 'features',
  'hand_checks', 'warnings', 'fingerprint')`. `state` goes; `met` is true when no kind of `left`
  is in `summary.BLOCKING`. `tag` is `signed/<version>` at `signed`, null at `passed`.
- `runs`: one entry per group of the counted sections, grouped by source, system, `email` (a
  `ci` section: `a remote runner`) and machine, ordered local first then by system:
  ```json
  "runs": [{"by": "dana.dev@labconnect.example", "machine": "dana-laptop", "os": "linux",
            "source": "local", "at": "2026-10-01T12:17:13Z", "commit": "<40 hex>", "rules": 19}]
  ```
  `at` is the group's newest, `commit` its newest section's, `rules` how many rules it answers.
- Each entry of a rule's `results` gains `"same_code": true|false` (C2).
- `project` is the payload's `project` (C9).
- Moved here from `release.py`, kept as they are: `project_version` and its readers,
  `uncommitted_work`, `behind_host`, `behind_words`. New:

```python
def time_words(at):
    """`2026-10-01T12:17:13Z` read as `2026-10-01 12:17 UTC`."""

def run_lines(package):
    """One RUN_LINE per entry of `runs`, or RUN_REMOTE_LINE for a ci entry."""

def off_code(package, project_root):
    """[(system words, source, [features])] for every counted result whose same_code is
    false, by system then feature."""

RUN_LINE = 'Tests run by %s on %s at %s on %s: %s on %s.'
# by, machine, time_words(at), sha7 of commit, '19 rules' / '1 rule', 'Linux/Unix'
RUN_REMOTE_LINE = 'Tests run by a remote runner at %s on %s: %s on %s.'
# time_words(at), sha7, '4 rules', 'Windows'
```

- `references/formats/package_format.md` goes to Format-Version 8: `met`, `runs`, each result's
  `same_code`, `tag` null at `passed`, `project`'s source, and that `purlin:sign` writes the
  package it signs.

### C4. The sign-off, lane `signoff`

`purlin:sign [--version <version>]` (`--release` renamed: nothing is called a release), `--show`,
`--answers FILE`. At `signed` it reads the committed evidence at `HEAD`, builds the package with
`package.build`, and walks.

**Refusals**, in this order, each one line, nothing written, exit 1 (the first exit 0):

```python
AT_PASSED = ('Nothing is signed at the gate passed: the status says whether every rule '
             'passes. To sign, run purlin:init --gate signed.')
NO_SIGNOFF_WORK = ('No sign-off: the working tree holds changes that are not committed. '
                   'Commit them, run purlin:test --all --commit, then purlin:sign.')
NO_SIGNOFF_EVIDENCE = ('No sign-off: the evidence is written and not committed. Run '
                       'purlin:test --commit, then purlin:sign.')
NO_VERSION = ('No version: nothing in this project states one. Run purlin:sign --version '
              '<version>, or write it to a VERSION file.')
NO_SIGNOFF_ELSEWHERE = ('No sign-off: %s is at %s, which this checkout does not hold. '
                        'Pull, then run purlin:sign.')
NO_SIGNOFF_MOVED = ('No sign-off: %s is at %s, and the code has changed since. To sign this '
                    'code, name a new version: purlin:sign --version <version>.')
NO_SIGNOFF_NOT_THIS_CODE = ('No sign-off: these results were not taken on this version of '
                            'the code, %s: %s. Run %s, then purlin:sign.')
# HEAD sha7; 'sample_age, stability on Linux/Unix; visit_window on Windows';
# 'purlin:test --all --commit' / 'purlin:test --remote' / both joined ' and '
NO_SIGNOFF_FAILING = ('No sign-off: %s at %s: %s. Run purlin:status to see what is left, '
                      'then purlin:sign.')
NO_SIGNOFF_BEHIND = ('No sign-off: %s holds %s that %s does not, as this checkout last '
                     'fetched it. Pull, then run purlin:sign.')
ALREADY_SIGNED = '%s has already signed %s over this package; nothing was written.'
```

`NO_SIGNOFF_ELSEWHERE` fires where `signed/<version>` exists here and its commit is not an
ancestor of `HEAD`; `NO_SIGNOFF_MOVED` where it is, and a commit after it changes anything but
the package folder. `NO_SIGNOFF_PACKAGE`, `NO_SIGNOFF_MOVED`'s old words and every release word
go.

**The key** (N11): `--show` never asks for or names one. The terminal walk and `--answers` check
it after the refusals, before their first line, printing today's `NO_KEY` block, exit 1.

**The opening** (105, from the evidence): the walk, `--show` and `--answers` print
`package.run_lines(package)` first, then `OVERVIEW`:

```
Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.
Signing 0.1.0 at 1cf829e.
  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.
  The audit: 17 strong, 1 weak, 0 not audited.
  2 stops: 1 hand check, 1 weak, 0 not audited.
```

`OVERVIEW = 'Signing %s at %s.'` (version, the package's `commit` sha7);
`OVERVIEW_RULES = '  %s on %s: %s, %s.'` with `19 pass their tests` from `steps.passed` and
`1 has a hand check` / `2 have a hand check`; `OVERVIEW_STOPS = '  %s: %s, %s, %s.'` with
`1 hand check` / `2 hand checks` (N12).

**A hand check** (106, N1): it stops once. Its stop shows `Rule`, `Proof`, and, where the audit
reads `weak` or `undecided`, `Results` and `What the audit found`. It asks
`HAND_ASK = '%s %s   what did you see, in one line, or Enter for no note, or stop: '`. An empty
line records the note `no note` (`kind` `hand check`). In `--answers`, a hand check takes
`continue` (recorded `no note`), `note` with a line, or `stop`.

**Signing:** on yes, `purlin:sign` writes the package (`.purlin/evidence/package/<version>.json`,
only for the first sign-off of a version; a later one signs the package the tagged commit holds,
which it does not rewrite) and the sign-off file, and makes one signed commit of both,
`sign(<version>): <email>`. The first sign-off writes `signed/<version>` on that commit, its
message `Signed <version> at the gate signed.\n\nCommit: <the package's commit>\n`.

```python
SIGNED_PUSH = 'Push the branch and the tag: git push origin %s %s'   # after TAGGED; the branch, the tag
TAG_STAYS = '%s stays at %s; this sign-off is added after it. Push it: git push origin %s'
```

On a detached `HEAD` the branch is left out: `git push origin signed/0.1.0`, `Push it: git push`.
Moved here from `release.py`: `tag_name` (now `signed/<version>` alone), `tag_exists`,
`write_tag`, `current_branch`.

**The sign-off file**, signature format 15: `shown` gains `runs` (the package's) and
`shown.overview.passing` is `steps.passed`; a note may read `no note`; `package_hash` is the
fingerprint of the package in the same commit.

### C5. A test comment to correct, lane `drift` (read by `counting`, `run`, `drift`, every lane)

`scripts/mcp/purlin/wording.py`, the one home of the check:

```python
STALE = ('%s:%d names %s %s, whose wording changed after the test was last changed in %s: '
         'it read "%s" and now reads "%s". ')
STALE_BUILD = ('Run purlin:build %s to make the test show it; the line clears once the test '
               'changes.')
STALE_MOVE = 'Its old wording is now %s: move the comment there.'

def stale_comments(project_root, features, scanned=None):
    """One entry per test comment naming a proof whose wording, at the commit that
    last changed the test, differs from its wording now. By file, then line.

    The test is the lines from the comment to the test's last line (`markers.Test`
    `line` and `end`; a file run whole is the whole file). Its last change is the
    newest commit `git blame` names for those lines; a test with an uncommitted line
    has changed now and is never named. `scanned` is markers.scan's answer, read with
    tracked_only=True where not given.

    Each entry: {'file', 'line', 'feature', 'id', 'commit' (sha7), 'old', 'new',
    'now_under' (the other proof id of the spec holding `old` exactly, or None), 'text'}.
    `text` is STALE filled, then STALE_MOVE where now_under, else STALE_BUILD."""
```

- **Cost** (lane `drift`): one `git blame --porcelain` per test file holding a marker and one per
  spec, cached for the call; a proof whose spec line was last written in the test's last-change
  commit or an ancestor of it is not compared further; one `git show` per distinct (commit,
  spec) compared. On this repository `sync_status` takes at most 3 seconds longer than at
  `b4a235e39`; the lane reports both times.
- **Readers:** the payload (C8) adds each `text` to `warnings` and counts it under `to_correct`;
  `purlin_run.py` prints them (C1); drift (C10) prints those whose proof changed in its range or
  whose file it changed; `renumber.py` moves a comment to `now_under`.
- `drift.comment_reworded`, `COMMENT_CHANGED` and `COMMENT_CHECK` are deleted; `COMMENT_MOVE`
  becomes `STALE_MOVE`.

### C6. The audit's per-test key, lane `counting` (format text by lane `run`)

A rule's `test_hash` is the sha256 of the sorted lines `<file> <test name> <sha256 of the
test's source>`, one per test tied to the rule's proofs (as `_backing_tests` names them). The
source is the test's declaration as `markers` bounds it, line ends read as `\n`. A test of an
`exit` suite, and a test whose declaration is not found by its name, gives
`<file> <test name> <blob id of the file>`. `test_hash_kind` is `test` where every part read a
declaration, `file` where any read the file; `TEST_HASH_KINDS = ('manual', 'file', 'test')`.
Every audit entry written before stops answering once; none is migrated.

### C7. The project's name, lane `settings`

`scripts/mcp/purlin/project.py`:

```python
def project_name(project_root, config=None):
    """The first that names one, stripped: `project_name` in .purlin/config.json;
    `[project]` then `[tool.poetry]` `name` in pyproject.toml; `name` in package.json;
    the first root *.csproj file's name without `.csproj`, in name order; the last
    path segment of `git remote get-url origin` without `.git`; the folder's name."""
```

- `templates/config.json` gains `"project_name": ""` as its first key; setup writes
  `project_name` over the folder it sets up, keeping a value already there; seven keys.
- `purlin:init --update` adds it where missing:
  `added to .purlin/config.json: project_name "labconnect"`.
- The settings tool accepts it as `a name of 1 to 100 characters`:
  `"" is not accepted for project_name; it takes a name of 1 to 100 characters. Nothing was saved.`
- This repository's `.purlin/config.json` gains `"project_name": "purlin"`.

### C8. The payload, the status and the gate, lane `counting`

`SCHEMA_VERSION = 14`.

- `finished` becomes `met`; `tag` becomes `signed_tag`: `{name, commit}` for the newest
  `signed/*` tag whose commit `package.only_records_between(<it>, HEAD)` reaches, else null.
  `release_tag` and every `passed/*` reading go.
- A new kind, blocking: `('to_commit', 'feature whose results are not committed',
  'features whose results are not committed', 'purlin:test --commit')`, counting the features
  whose `local/` evidence file is written and not committed.
- `met`: no blocking kind left, and at `signed` a `signed_tag` too.
- **The last line**, replacing `TO_RELEASE`, `TO_RELEASE_SIGNED`, `RELEASE` and the use of
  `NOTHING_LEFT` as one:

```python
MET_PASSED = 'The gate passed is met: every rule passes its tests on the committed evidence.'
READY_TO_SIGN = ('Every rule passes its tests on the committed evidence. The gate signed is '
                 'met once a person signs: purlin:sign')
MET_SIGNED = 'The gate signed is met: %s.'           # signed/0.1.0
NOT_MET = 'The gate %s is not met.'                  # after Left to do, while a blocking kind is left
```

  `Left to do:` and its lines stay as now above it, a rule to strengthen or to write a proof for
  included, which do not stop `met`.
- The stale lines (C5): `warnings` and `to_correct`, as C5 says.
- **N1:** a rule with a `@manual` proof whose audit reads `weak` or `undecided` reads `weak`,
  reasons the findings then `manual proof`, `left` `to_strengthen`; any other audit or none,
  `manual test` as now.
- **N12, the vanished finding:** a strong cell reading `waiting` or `not audited`, whose
  evidence holds an entry that no longer answers and read `weak`, gains per finding
  `EARLIER_WEAK = 'the last audit, before the rule or its tests changed, found it weak: %s'`,
  counted nowhere.
- **N12, no code:** `status._holds_code` counts a file only where it holds a byte.
- `project` is `project.project_name(project_root, config)`.

```
Left to do:
  1 test comment to correct: purlin:build
The gate passed is not met.
```

### C9. Setup and the upgrade, lane `settings`

C7, and `UNKNOWN_HOST` reads
`origin is not on GitHub or Azure DevOps, so every test runs on this machine and purlin:test --remote is not set up.`
`templates/gitignore.purlin` loses its `.purlin/tests.md` words. No `.gitattributes` line.

### C10. Drift and the helper, lane `drift`

- N9: the comment lines are C5's. N10: an id the range's end writes twice is left out of
  `proofs_changed`. N12: a `checkout` reflog entry whose old and new sha are the same is not an
  action; the engineer view's no-test line is one per rule:
  `NO_TEST_FOR = '%s %s has no test for %s. Run purlin:build %s.'` or
  `NO_TEST = '%s %s has no test. Run purlin:build %s.'`.
- The helper writes a moved rule line after the spec's last `- RULE-` line and a moved proof
  line after its last `- PROOF-` line.
- `references/drift_criteria.md` goes to Criteria-Version 13.

### C11. The three-person test, lane `team`

`specs/team/collaboration.md`, new:

```
# Feature: collaboration

> Description: Product, QA and dev work at once through git, in three clones of one repository,
>   and reach a version signed at the gate `signed`. A script plays the three people, forces
>   collisions, merges in both orders, and checks the run completes with no step stuck, no
>   command failing unexpectedly and nothing corrupted. The run with real AI sessions is the
>   owner's sanity check, not this proof.
> Scope: scripts/init/scaffold.py, scripts/run/purlin_run.py, scripts/run/evidence.py, scripts/export, scripts/review/sign.py, scripts/spec/renumber.py, scripts/mcp/purlin
> Stack: python/stdlib (subprocess), git, ssh-keygen, pytest
> Highest-Rule: 1
> Highest-Proof: 1

## Rules

- RULE-1: Three people working at once through git reach a signed version: `signed/<version>` exists, and the evidence package it holds describes the code under it and matches its fingerprint; no step needs a command that Purlin's output, skills and docs do not give; no command fails unexpectedly, and every warning raised along the way is resolved by the end; no spec holds a number twice or a merge-conflict line; every test comment is tied and names a proof with the wording it was marked against; each spec's highest-number lines cover its numbers; and the package lists every rule

## Proofs

- PROOF-1 (RULE-1): Pat, Quinn and Dana work in three clones of one bare repository at the gate `signed`; two pairs of branches take the same numbers, one merged QA first and one dev first; a test stays marked on a proof whose number moved; Dana runs and commits; Quinn signs `0.1.0`, then Pat; every check of RULE-1 holds
```

`dev/test_collaboration.py`, one test marked `# purlin: collaboration PROOF-1`, section 3's
scenario. It writes its sample project from text in the test file, gives each person a `HOME`
under `tmp_path`, makes every key with `ssh-keygen` inside the test, sets
`GIT_CONFIG_NOSYSTEM=1`, uses a bare repository on disk as the host, runs no audit and calls no
model, and finishes in under 120 seconds on this Mac.

### C12. Format and schema numbers

| File | Now | After | Why |
|---|---|---|---|
| `references/formats/package_format.md` | 7 | 8 | each result's `nothing_to_check` reason (C15); `state` becomes `met`; `runs` added; each result's `same_code`; `tag` null at `passed`; schema `purlin-package/4`; written by `purlin:sign` |
| `references/formats/signature_format.md` | 14 | 15 | `shown.runs` added; `passing` counts every rule that passes; `no note`; the package in the same commit |
| `references/formats/evidence_format.md` | 7 | 8 | a section's `commit` is the code it describes; `email` added; retention only over the same code; `test_hash` per test; the table section goes; a proof entry's `result` may be `nothing to check`, with `reason` (C15) |
| `references/formats/marker_format.md` | 3 | 4 | each report format's skip message is read as the case's reason, and `nothing to check:` named (C15) |
| `references/formats/anchor_format.md` | 11 | 12 | `.purlin/tests.md` leaves the records list; an anchor's rule is written "for every X in the project, Y holds" and its test skips with `nothing to check: <why>` where there is no X (C15) |
| `references/formats/spec_format.md` | 21 | 21 | unchanged |
| payload `schema_version` | 13 | 14 | `finished` becomes `met`, `tag` becomes `signed_tag`, `to_commit` |
| `references/drift_criteria.md` Criteria-Version | 12 | 13 | C5's basis, the collision out of `changed`, the checkout that moves nothing |

### C13. Deleted outright

`scripts/export/release.py`, `specs/export/release.md`, `dev/test_tag.py`; `purlin:test
--release` and every line naming it; the `passed/<version>` tag and every reading of it
(`release_tag`, `REFUSED`, `NO_RELEASE_*`, `PACKAGE_COMMITTED`, `TAGGED` as the release's,
`READY_TO_SIGN` as the release's, `HAND_CHECKS`'s release line); the package's `state`; the
words `release`, `released` and `finished` wherever they name a step Purlin takes;
`.purlin/tests.md`, its writer, its rules, proofs and tests. What survives of `release.md` moves
as a new rule in `specs/review/signatures.md` (the version read from the project, uncommitted
work, the branch's copy on the host ahead, git refusing the tag) or `specs/export/package.md`
(the version), with that spec's next numbers.

### C14. The ~198 test comments to correct

At `b4a235e39` C5's check names 198 comments in 30 test files. Each is cleared by the lane that
owns its file, in that lane, plus lane `tests` for the files no other lane owns:

| Lane | Files (comments at `b4a235e39`) |
|---|---|
| `dashboard` | `test_purlin_report.py` (34), `test_purlin_report_board_layout.py` (4), `test_report_refresh.py` (4) |
| `run` | `test_run_script.py` (33), `test_evidence_writer.py` (3), `test_fingerprint.py` (1), `test_evidence_reader.py` (3), `test_reports.py` (5), `test_skill_audit.py` (2) |
| `counting` | `test_states.py` (20) |
| `settings` | `test_init_scaffold.py` (16), `test_init_update.py` (3), `test_skill_init.py` (1), `test_specs_reader.py` (1) |
| `drift` | `test_drift.py` (11), `test_skill_drift.py` (1) |
| `package` | `test_export.py` (9), `test_skill_export.py` (1) |
| `signoff` | `test_signatures.py` (5) |
| `words` | `test_skill_spec.py` (1) |
| `tests` | `test_host.py` (11), `test_ai_audit.py` (9), `test_remote.py` (4), `test_consumer_ci.py` (3), `test_purlin_version.py` (3), `test_security.py` (3), `test_ai_audit_tests_named.py` (2), `test_host_pathspec.py` (2), `test_mutation_adapters.py` (2), `test_upstream_notes.py` (1) |

For each comment: read the test against the proof as written now. Where the test shows it,
change the test so it states it (its name, its docstring or an assertion); where it does not,
fix the test to show it; where the old wording is now another id, move the comment. Never reword
a proof to match a test. Each lane's report lists every one as `<file>:<line> <feature>
<PROOF-N> stated | fixed | moved`, with one line on what changed for each `fixed`.

**How it is checked:** (1) each lane: `wording.py --file` on its files prints `No test comment
to correct.`, and its test files pass; (2) integration: `wording.py` over the whole repository
prints `No test comment to correct.`; (3) integration: `git diff b4a235e39 -- specs/` touches no
proof line for a commit whose subject begins `test:`; (4) a reviewer agent, not one of the
fixers, reads every `fixed` entry's diff against its proof and every tenth `stated`, and lists
each it disagrees with; integration fixes those before the sweep.

### C15. Nothing to check, lanes `run`, `counting`, `package`, `dashboard`, `words`

- **The skip.** A test that finds nothing to check skips through its tool's own skip with a
  reason that begins exactly `nothing to check:`, as `nothing to check: this project has no
  screens`. Any other skip reads as today (`missing`).
- **Reading it** (lane `run`, `scripts/run/reports.py`, marker format 4): each `Case` gains
  `reason`, the skip's message, or `''`. `junit`: the `<skipped>` child's `message` attribute,
  else its text. `trx`: a `NotExecuted` (or other skipped) result's `Output/ErrorInfo/Message`,
  else `Output/StdOut`'s last line. `gotest`: the last `output` event of that test before its
  `skip` event, with its leading `<file>:<line>: ` cut. `exit`: carries none, so an `exit` test
  cannot skip. Where a tool writes no message (Jest's `test.skip`), the rule cannot skip and the
  quality guide says so.
- **The evidence** (lane `run`, evidence format 8): a proof entry whose every tied case skipped
  with a `nothing to check:` reason reads `"result": "nothing to check"` with
  `"reason": "nothing to check: this project has no screens"`. In an anchor's section (Q2) such
  a proof counts as passed in `rule_word`; in any other spec's section it reads `not run`, as a
  skip does today, and keeps its `reason`.
- **The cell** (lane `counting`): an anchor's rule whose proofs passed, one or more of them as
  `nothing to check`, reads `passed`, with one reason per such proof:
  `NOTHING_TO_CHECK = '%s: %s'` (`PROOF-3`, the reason). It counts under `steps.passed`. The
  strong cell reads `not audited` with no change; the audit reads the test as it reads any.
- **The status** (lane `counting`), after the table, one line per such rule:
  `NOTHING_LINE = '%s %s passes with nothing to check here: %s.'`
  (`security_no_dangerous_patterns RULE-3`, the reason without its `nothing to check: `).
- **The package** (lane `package`): each `results` entry carries `nothing_to_check`, the list of
  `{proof, reason}` read from its section, `[]` where none; a rule's `statuses.passed.reasons`
  carry the cell's reasons. The walk (lane `signoff`) shows each in `Results` as
  `  Linux/Unix: passed on dana-laptop; nothing to check for PROOF-3: this project has no screens`.
- **The dashboard** (lane `dashboard`): the rule's page shows the reason under the proof, and the
  board's passed cell carries a `nothing to check` hover; fixtures gain one such anchor rule.
- **No project-side `does not apply`.** Nothing of decision 101's survives in code; lanes `words`
  and `docs` grep for `does not apply`, `--does-not-apply` and `not applying` and delete what
  they find outside `RELEASE_NOTES.md`.

## 3. The lanes

| Lane | Owns |
|---|---|
| L1 `settings` | `scripts/mcp/purlin/project.py`; `scripts/init/{scaffold,update}.py`; `templates/{config.json,gitignore.purlin}`; `scripts/mcp/purlin/server.py`; `scripts/run/workflow.py` (`UNKNOWN_HOST`); `.purlin/config.json`; `specs/mcp/{config_engine,server,specs}.md`; `specs/init/{scaffold,update}.md`; `dev/test_{config_engine,mcp_server,init_scaffold,init_update,specs_reader}.py`; `dev/fixtures/upgrade-0.9.5/**`; `skills/init/SKILL.md`; `specs/skills/skill_init.md`; `dev/test_skill_init.py` |
| L2 `drift` | `scripts/mcp/purlin/{wording,drift}.py`; `scripts/spec/renumber.py`; `specs/mcp/drift.md`; `specs/spec/renumber.md`; `dev/test_{drift,renumber,wording}.py`; `references/drift_criteria.md`; `skills/drift/SKILL.md`; `specs/skills/skill_drift.md`; `dev/test_skill_drift.py` |
| L3 `counting` | `scripts/mcp/purlin/{payload,states,status,summary,board}.py`; `specs/mcp/{states,summary}.md`; `dev/test_{states,summary,backing_tests,failing,purlin_output}.py`; `specs/instructions/purlin_output.md`; `skills/status/SKILL.md`; `specs/skills/skill_status.md`; `dev/test_skill_status.py` |
| L4 `package` | `scripts/export/{package,release}.py`; `specs/export/{package,release}.md`; `dev/test_export.py`; `dev/test_tag.py`; `references/formats/package_format.md`; `skills/export/SKILL.md`; `specs/skills/skill_export.md`; `dev/test_skill_export.py` |
| L5 `signoff` | `scripts/review/sign.py`; `scripts/mcp/purlin/signatures.py`; `specs/review/signatures.md`; `dev/test_signatures.py`; `references/formats/signature_format.md`; `skills/sign/SKILL.md`; `specs/skills/skill_sign.md`; `dev/test_skill_sign.py` |
| L6 `run` | `scripts/run/{purlin_run,evidence,reports}.py`; `scripts/mcp/purlin/{fingerprint,evidence}.py`; `references/formats/{evidence_format,marker_format}.md`; `specs/run/{run_script,evidence_writer,reports}.md`; `specs/mcp/evidence.md`; `dev/test_{run_script,evidence_writer,fingerprint,evidence_reader,reports}.py`; `skills/{test,audit}/SKILL.md`; `specs/skills/{skill_test,skill_audit}.md`; `dev/test_skill_{test,audit}.py` |
| L7 `dashboard` | `scripts/report/src/**`; `scripts/mcp/purlin/report_data.py`; `dev/build_report.py`; `dev/capture_doc_screenshots.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report.py`; `dev/test_purlin_report_board_layout.py`; `dev/test_report_refresh.py`; `dev/fixtures/report/*.json`; `docs/dashboard.md` |
| L8 `words` | `skills/{spec,build,anchor,spec-from-code}/SKILL.md`; `specs/skills/{skill_spec,skill_build,skill_anchor,skill_spec_from_code}.md`; `dev/test_skill_{spec,build,anchor,spec_from_code}.py`; `references/{glossary,purlin_commands,hard_gates,commit_conventions,spec_quality_guide}.md`; `references/formats/anchor_format.md`; `agents/purlin.md`; `specs/instructions/purlin_agent.md`; `dev/test_purlin_agent.py`; `README.md`; `RELEASE_NOTES.md`; `CLAUDE.md` (the step naming `purlin:test --release` and the `package_format.md` row alone) |
| L9 `docs` | `docs/{index,getting-started,how-purlin-works,raising-the-gate-and-upgrading,regulated-workflow,review-and-signing,running-and-evidence,spec-from-code,specs-and-anchors,team-workflow,working-together,qa-guide}.md`; `specs/instructions/purlin_docs.md`; `dev/test_purlin_docs.py`; `dev/plans/deck/build_deck.py`; `dev/plans/deck/check_deck.py` |
| L10 `tests` | the ten files of C14's last row |
| L11 `team` | `specs/team/collaboration.md`; `dev/test_collaboration.py` |

No lane: `scripts/mcp/purlin/{markers,specs,gate}.py`, `scripts/review/{ai_audit,marked_tests}.py`,
`scripts/run/{ci,host,remote}.py`, `templates/purlin*.yml`, `dev/test_vocabulary.py`,
`dev/plans/three-levels.md`. A failure the sweep finds there is integration's.

### L1 `settings`

C7, C9. The init skill names seven keys, no `tests.md` and no release step, within 250.

- `specs/mcp/config_engine.md` (R18 P44; next RULE-19, PROOF-45), `> Scope:` adds
  `scripts/mcp/purlin/project.py`: RULE-19, the name is the first C7 source that names one
  (PROOF-45 config over `pyproject.toml`; PROOF-46 `[project] name`; PROOF-47 `package.json`;
  PROOF-48 `Intake.csproj`; PROOF-49 the origin `/srv/git/labconnect.git`; PROOF-50 the folder).
- `specs/init/scaffold.md` (R78 P170; next RULE-79, PROOF-171): RULE-79, setup writes
  `project_name` (PROOF-171). Proofs quoting `UNKNOWN_HOST`, six keys, `tests.md` or
  `purlin:test --release` are reworded or deleted.
- `specs/init/update.md` (R49 P161; next RULE-50, PROOF-162): RULE-50, the upgrade adds
  `project_name` with its line (PROOF-162); proofs quoting the old words reworded.
- `specs/mcp/server.md` (R32 P163; next RULE-33, PROOF-164): RULE-33 (PROOF-164 written;
  PROOF-165 empty refused).
- `specs/skills/skill_init.md` (R85 P96; next RULE-86, PROOF-97): RULE-86, seven keys (PROOF-97).

Break: drop `pyproject.toml` from the chain; PROOF-46 fails. Waits on: none.

### L2 `drift`

C5 (the stub made fast, its cost bound), C10. The drift skill says the wording line clears once
the test changes, through `purlin:build`, within 150.

- `specs/mcp/drift.md` (R34 P80; next RULE-35, PROOF-81), `> Scope:` adds
  `scripts/mcp/purlin/wording.py`: proofs quoting `COMMENT_CHANGED`/`COMMENT_CHECK` reworded.
  RULE-35, named when the proof changed after the test last changed (PROOF-81 named with
  `STALE`; PROOF-82 the test edited after, not named; PROOF-83 an uncommitted test edit, not
  named; PROOF-84 only the comment line rewritten, still named). RULE-36, an id written twice is
  no proof changed (PROOF-85). RULE-37, a checkout that moves nothing does not start the range
  (PROOF-86). RULE-38, the engineer view names a rule's untested proofs (PROOF-87).
- `specs/spec/renumber.md` (R9 P12; next RULE-10, PROOF-13): RULE-6 reworded to C5's basis.
  RULE-10, a moved line goes after the last of its kind (PROOF-13 rule; PROOF-14 proof).
- `specs/skills/skill_drift.md` (R13 P39; next RULE-14, PROOF-40): RULE-14 (PROOF-40).

Break: blame the comment line alone; PROOF-82 fails. Waits on: drift tests reading the `qa`
view's `Left to do` (lane `counting`).

### L3 `counting`

C6, C8. The status skill: the last lines by gate, `to_commit`, a test comment to correct goes to
`purlin:build`; no release row; within 100.

- `specs/mcp/states.md` (R109 P264; next RULE-110, PROOF-265): RULE-110, the test hash per test
  (PROOF-265 another test of the file edited, unchanged; PROOF-266 the rule's test edited,
  changed; PROOF-267 a shell test run whole, kind `file`). RULE-111, weak wins over a hand check
  (PROOF-268). RULE-112, a test comment to correct is warned and counted (PROOF-269; PROOF-270
  cleared after the test changes). RULE-113, the head names the project from its files
  (PROOF-271). RULE-114, the earlier weak finding (PROOF-272). RULE-39 reworded: a file of code
  that holds something (PROOF-273). RULE-115, an anchor rule with nothing to check reads `passed`
  with the reason, and the status prints `NOTHING_LINE` (PROOF-274 the cell; PROOF-275 the line). Every rule naming a release, `passed/` or `finished` is
  reworded to C8 or deleted.
- `specs/mcp/summary.md` (R19 P47; next RULE-20, PROOF-48): RULE-18 reworded to C8's last lines
  (its proofs rewritten: PROOF-44 `MET_PASSED`, PROOF-45 `READY_TO_SIGN`, PROOF-46 `MET_SIGNED`).
  RULE-20, `NOT_MET` follows `Left to do` while a blocking kind is left (PROOF-48). RULE-21,
  `to_commit` (PROOF-49).
- `specs/skills/skill_status.md` (R12 P36; next RULE-13, PROOF-37): RULE-13 (PROOF-37).

Break: count `to_commit` outside `BLOCKING`; PROOF-49 fails. Waits on: PROOF-269/270 (lane
`drift` for the fast check is not needed; the stub works), PROOF-271 (lane `settings`), the
`signed_tag` proofs (lane `package`'s `only_records_between`).

### L4 `package`

C2, C3, C13's `release.py` half. The export skill: the package at any time, `met`, `runs`, no
release; within 90.

- `specs/export/release.md`, `dev/test_tag.py`, `scripts/export/release.py`: deleted.
- `specs/export/package.md` (R31 P64; next RULE-32, PROOF-65): RULE-3, PROOF-3, PROOF-46 reworded
  to C3's keys; RULE-30 reworded to `met`. RULE-32, `runs` (PROOF-65 one local group; PROOF-66 a
  local and a `ci` group). RULE-33, `same_code` (PROOF-67 true after a commit changing only
  `.purlin/`; PROOF-68 false after a code commit). RULE-34, `project` (PROOF-69). RULE-35, the
  version read from the project, moved from `release.md` (PROOF-70 `VERSION`; PROOF-71
  `pyproject.toml`). RULE-36, `tag` null at `passed` (PROOF-72). RULE-37, a result carries
  `nothing_to_check` (PROOF-73).
- `specs/skills/skill_export.md` (R14 P36; next RULE-15, PROOF-37): RULE-14 reworded (no release);
  RULE-15 (PROOF-37).

Break: let `same_code` ignore a code commit; PROOF-68 fails. Waits on: PROOF-69 (`settings`).

### L5 `signoff`

C4, signature format 15. Its own package helper in `dev/test_signatures.py` builds through
`package.build` where lane `package` has merged, and writes C3's shape itself until then. The
sign skill: `--show` first, no key needed; the refusals and what to run; the note optional; the
push lines; a later signer pulls first; `--version`; within 185.

- `specs/review/signatures.md` (R111 P222; next RULE-112, PROOF-223): RULE-102's refusals
  rewritten to C4's list, one proof each that is new (PROOF-223 `NO_SIGNOFF_EVIDENCE`; PROOF-224
  `NO_SIGNOFF_ELSEWHERE`; PROOF-225 `NO_SIGNOFF_MOVED`; PROOF-226 `NO_SIGNOFF_NOT_THIS_CODE`
  naming `purlin:test --remote` for a Windows result), the deleted refusals' proofs deleted.
  RULE-112, the opening run lines (PROOF-227). RULE-113, `--show` needs no key (PROOF-228);
  `--answers` with none prints the key block first (PROOF-229). RULE-114, a weak hand check
  shows what the audit found (PROOF-230). RULE-115, the overview's counts (PROOF-231). RULE-116,
  the push lines (PROOF-232 first; PROOF-233 later). RULE-117, an empty hand-check answer is
  `no note` (PROOF-234). RULE-118, the first sign-off commits the package and the sign-off in
  one signed commit and tags it (PROOF-235); a later one adds its file alone (PROOF-236).
  RULE-119, moved from `release.md`: the branch's copy on the host ahead refuses (PROOF-237);
  git refusing the tag prints `NO_TAG_GIT` (PROOF-238). RULE-120, the sign-off records `runs`
  (PROOF-239). RULE-121, `Results` names each proof with nothing to check and its reason
  (PROOF-240).
- `specs/skills/skill_sign.md` (R31 P62; next RULE-32, PROOF-63): RULE-32, `--show` before any key
  question (PROOF-63); RULE-33, the note is optional (PROOF-64).

Break: drop the ancestor check behind `NO_SIGNOFF_ELSEWHERE`; PROOF-224 fails. Waits on: every
test building a real package (lane `package`).

### L6 `run`

C1, C5's printing, evidence format 8 (C6's text included), C13's run half. `fingerprint.py`'s
records list loses `.purlin/tests.md`. The test skill: the hand-off is `purlin:test --all
--commit` and `purlin:test --remote`; no `--release`, no table; the audit skill: a rule is read
again only when its own test changed; within 120 and 105.

- `specs/run/run_script.md` (R94 P269; next RULE-95, PROOF-270): RULE-90, RULE-91 and every rule
  of `--release` deleted with their proofs and tests. RULE-95, a section names the commit its
  work commit made (PROOF-270). RULE-96, a section carries the runner's email (PROOF-271).
  RULE-97, a run on new code moves an unchanged section onto it (PROOF-272); on the same code
  leaves it (PROOF-273). RULE-98, every run prints the test comments to correct and exits as its
  tests do (PROOF-274).
- `specs/run/evidence_writer.md` (R26 P89): every rule and proof of the table deleted; next
  RULE-27, PROOF-90 if one is needed.
- `specs/mcp/evidence.md` (R33 P85): a proof naming `.purlin/tests.md` among the records
  reworded.
- `specs/skills/skill_test.md` (R21 P50; next RULE-22, PROOF-51): RULE-21 deleted; RULE-22, the
  hand-off (PROOF-51). `specs/skills/skill_audit.md` (R25 P52; next RULE-26, PROOF-53): RULE-26
  (PROOF-53).

- `specs/run/reports.md` (R31 P114; next RULE-32, PROOF-115): RULE-32, each format's skip
  message is the case's reason (PROOF-115 `junit`; PROOF-116 `trx`; PROOF-117 `gotest`; PROOF-118
  an `exit` test has none). RULE-33, a `nothing to check:` skip in an anchor's section reads
  `nothing to check` and its rule `passed` (PROOF-119); in another spec's section, `not run`
  with the reason kept (PROOF-120); any other skip reads `missing` as today (PROOF-121).

Break: keep a section on old code; PROOF-272 fails. Waits on: PROOF-272/273 (lane `package`'s
`only_records_between`).

### L7 `dashboard`

Schema 14 fixtures: `met`, `signed_tag`, `last_line` in C8's words; the line shows in both
states; the tag chip reads `signed_tag`; a `@manual` proof at `signed` reads
`Checked by hand when a person signs, in the walk of purlin:sign.` and at `passed`
`Checked by hand. The gate passed records no hand check.`; no `release` and no
`purlin:test --release` in any hover. `docs/dashboard.md` the same.

- `specs/dashboard/purlin_report.md` (R71 P222; next RULE-72, PROOF-223): RULE-72, the page shows
  the gate's line, met or not met (PROOF-223 met at `passed`; PROOF-224 not met). RULE-73, a
  rule with nothing to check shows its reason (PROOF-225). Rules naming a
  release reworded.

Break: hide the line when not met; PROOF-224 fails. Waits on: none (fixed fixtures).

### L8 `words`

- `skills/build/SKILL.md`: before adding any marker, read each test already marked for the spec
  against its proof as written now; where one no longer shows it, fix it, or move the comment as
  "Renumbering" says; where it shows it but its comment is to correct, change the test so it
  states the new wording. The closing rows: no release; the hand-off. Within 130.
- `skills/spec/SKILL.md` "After a merge conflict": section 6's sentence. `skills/anchor` and
  `skills/spec-from-code`: release lines go.
- `references/glossary.md` (`release`, `release run` go; `hand-off`, `met`, `test comment to
  correct` as section 6), `purlin_commands.md` (`purlin:test --release` goes; `purlin:sign
  --version`; `--show` needs no key), `hard_gates.md` (the two gates as met or not met on the
  committed evidence; when a result counts for a sign-off, C2; what `signed/<version>` means;
  no `passed/`), `commit_conventions.md` (`sign(<version>)` commits the package too; the
  release row goes), `spec_quality_guide.md` (a reworded proof needs its test changed; C15's section on writing an
  anchor's rule as "for every X in the project, Y holds" and skipping with `nothing to check:
  <why>` where there is no X, with the skip in pytest, Jest/Vitest, xUnit and Go and the tools
  that carry no message), `formats/anchor_format.md` (C12, Format-Version 12). The anchor skill
  points an author at that section in one line; no `does not apply` anywhere.
- `agents/purlin.md`: the loop ends on run and commit, then at `signed` `purlin:sign`; within
  135. `CLAUDE.md`: "Releasing a new version" step 3 reads `Run purlin:test --all --commit (and
  purlin:test --remote for other systems), then purlin:sign at the gate signed. The first
  sign-off writes the signed tag signed/<version>.`; the `package_format.md` row reads `The
  evidence package purlin:export and purlin:sign write, handed to a regulated sign-off system as
  evidence`.
- `README.md`, `RELEASE_NOTES.md` 0.10.0: section 6; decision 103's and 105's release entries
  replaced, not kept beside.
- `specs/skills/skill_build.md` (R19 P48; next RULE-20, PROOF-49): RULE-20, the check before a
  marker (PROOF-49); RULE-21, clearing by changing the test (PROOF-50). `skill_spec.md` (R30 P60;
  next RULE-31, PROOF-61): RULE-31 (PROOF-61). `purlin_agent.md` (R17 P48; next RULE-18,
  PROOF-49): RULE-18 (PROOF-49). `skill_anchor` (R16 P38), `skill_spec_from_code` (R51 P165):
  reworded only.

Break: drop the check from the build skill; PROOF-49 fails. Waits on: none.

### L9 `docs`

Every page in section 6's words, with no release step: `review-and-signing.md` becomes the
sign-off page (the hand-off; the refusals and what to rerun; the opening lines; the note
optional; the package written by the sign-off; the push lines; a later signer pulls first;
verifying a signed commit with `gpg.ssh.allowedSignersFile`, the commands given);
`qa-guide.md` (QA runs no tests; signs on the branch the developer committed; `--show` needs no
key); `team-workflow.md` (the hand-off; remote results on the same code; no table; the merge
recipe without `tests.md`); `running-and-evidence.md` (sections name their code; retention over
the same code; a test comment to correct; the per-test audit key; no table);
`working-together.md` (the wording line clears when the test changes; a collision is not a
change); `regulated-workflow.md` (its flow ends run, commit, `purlin:sign`, `signed/<version>`;
the sample package at `purlin-package/4`); `getting-started.md`, `how-purlin-works.md`,
`raising-the-gate-and-upgrading.md` (met or not met; `project_name`), `specs-and-anchors.md`,
`spec-from-code.md`, `index.md` where a line changed. `specs-and-anchors.md` says how a pulled
  rule with nothing to check reads, and that a pulled rule that fails here is raised with its
  authors. The deck drops the release slide text.

`specs/instructions/purlin_docs.md` (R13 P18; next RULE-14, PROOF-19): RULE-13 reworded to the
one tag; RULE-14, the sign-off page names the hand-off and the refusal naming what to rerun
(PROOF-19).

Break: none in code; greps of its files for `--release`, `passed/`, `tests.md`,
`purlin-package/3`, `release run` are empty.

### L10 `tests`

C14 for its eleven files, nothing else. Waits on: none (the stub's check works).

### L11 `team`

C11. Every command as its skill runs it (the table of `sanity-qa-product-2.md` section 1, with
`purlin:test --all --commit` as the hand-off and no release step):

1. Pat: `pyproject.toml` naming `labconnect`, version `0.1.0`; setup at `--gate signed --yes`;
   push `main`.
2. Pat on `product/specs`: `sample_age` and `stability`, two rules and three proofs each; merged
   to `main`, pushed.
3. Dana on `dev/build`: code and marked tests; the suggested `tests` entry written through the
   settings tool; `--test --commit`; merged, pushed.
4. **Collision one, QA first:** Quinn on `qa/frozen` and Dana on `dev/tube-case` each add
   `stability` RULE-3 and PROOF-4 from the same `main`, Dana's test marked `stability PROOF-4`.
   Quinn merges first. Dana pulls, keeps both lines, reads the status and drift, runs
   `renumber.py stability --dry-run` then without, commits, `--test --commit`, merges, pushes.
5. **Collision two, dev first:** both add `sample_age` PROOF-4; Dana merges first; Quinn pulls,
   resolves, renumbers, merges.
6. **A test left on a moved proof:** Dana, on a branch from Quinn's commit before the renumber,
   marks a test `sample_age PROOF-4` for Quinn's proof; after the merge the status prints C5's
   line naming where the old wording is now and `1 test comment to correct: purlin:build`, then
   `The gate signed is not met.`; `renumber.py sample_age` moves it; the line is gone.
7. **The hand-off:** Dana on `main`: `purlin_run.py --test --all --commit`; the status reads
   `READY_TO_SIGN`; push `main`.
8. Quinn: pull; `sign.py --show` with no key set shows the walk; `sign.py --answers` prints the
   key block, whose commands the test runs as printed with Quinn's `HOME`; answers file (the
   hand check left empty); `--answers`; runs the push line it prints.
9. **A second signer:** Pat, on `main` as it stood before Quinn signed, runs `git fetch` (the tag
   comes with it) and `sign.py --answers`: refused with `NO_SIGNOFF_ELSEWHERE`; pulls as it says,
   signs, runs `TAG_STAYS`'s push line.
10. **End checks**, in a fresh clone of the bare repository, each its own assertion naming the
    check: `signed/0.1.0` exists on the host; the package at the tag passes `package.py --check`;
    `git diff --name-only <package commit> signed/0.1.0` lists only `.purlin/evidence/package/`
    paths; both sign-off files on `origin/main` count; every exit code was the expected one (the
    refusal of step 9, and the not-met states of steps 4 to 6, the only planned ones); every
    warning any status or run printed is absent from the final status, which ends on
    `MET_SIGNED`; no spec has broken reasons; `Markers: <n> tied to a test, 0 not tied.`;
    `wording.stale_comments` empty; each spec's Highest lines cover its numbers; the package's
    `rules` equals the rules the specs write at its commit, each listed; the hand check's note
    reads `no note`. **No step needs a command Purlin does not give:** every command after step 1
    that is not a plain git step a person takes anyway (commit, branch, switch, merge, pull,
    fetch, push of a branch, conflict edit) is extracted from the output before it (a `Run:` or
    `→ Run:` command, a push line, the key block) or from the skill the table maps it to, and
    the test fails where it is absent.

Break: point step 7 at base `main`'s `purlin_run.py` (sections keep old commits): step 8 is
refused with `NO_SIGNOFF_NOT_THIS_CODE`. Waits on: every other lane; integration runs it last.

## 4. Frozen files

None is expected to change. If the sweep shows one must, integration's own commit
(`chore: the frozen helpers follow decision 106`) may change only: in `dev/sign_project.py`, a
docstring naming a release, and `signing_project`'s evidence given an `email` and a `commit` of
`HEAD`; in `dev/mcp_project.py`, `evidence(...)` writing `commit` as `HEAD`. Anything else goes
to the owner.

## 5. Merge order and integration

### Merge order

`settings`, `drift`, `counting`, `package`, `signoff`, `run`, `dashboard`, `words`, `docs`,
`tests`, `team`. Each by fast-forward: integration rebases the lane branch on the merged line,
reruns its files, then fast-forwards `main`.

Why: `project.py` and `wording.py` are read by the payload; the payload by everything after;
`package.py` by the walk and by the run's retention; the dashboard reads fixed fixtures; words
and docs describe the rest; `tests` touches only test files; the three-person test needs all.

Expected red between merges, and only: each lane's listed waits; from the `package` merge until
`signoff` and `run` merge, `sign.py` and `purlin_run.py` importing from the deleted `release.py`;
skill and docs tests quoting a line their lane has not yet rewritten; `dev/test_collaboration.py`
until the last merge.

### Integration's job (alone, on the Mac, after every lane merged)

1. Merge in order; resolve each failure a lane reported in a file it does not own, to the
   contracts.
2. Frozen files, only as section 4 allows.
3. `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH`. `git rm .purlin/tests.md`
   (`chore: the committed test table goes`).
4. C14's checks 2 to 4: `wording.py` over the repository, the `specs/` diff, the reviewer agent's
   read; fix what it lists.
5. `bash dev/run_tests.sh`: 0 failed. Never edit a number to make it pass.
6. `python3 dev/build_report.py`; commit `scripts/report/purlin-report.html` once. Retake the two
   docs screenshots with `dev/capture_doc_screenshots.py` and commit them if they differ. Look at
   the dashboard with playwright, headless, dark and light, at 1500, 1280, 1024, 768 and 390
   pixels, on the three fixtures: the gate's line met and not met, never wrapped inside a value,
   neutral text at least 7 to 1; no `release` word anywhere.
7. Greps over `scripts/`, `skills/`, `agents/`, `references/`, `docs/`, `templates/`,
   `README.md`, `CLAUDE.md` and `dev/test_*.py`, each empty outside `RELEASE_NOTES.md`:
   `--release` (as `purlin:test`'s), `passed/`, `tests.md`, `release run`, `READY_TO_SIGN`
   (the release's), `TO_RELEASE`, `release_tag`, `purlin-package/3`, `schema_version.: 13`.
8. `python3 scripts/run/purlin_run.py --test --all`: `Markers: <n> tied to a test, 0 not
   tied.`, no rule `failed`, `partial` or `no test`, no spec to repair, no test comment to
   correct, no warning, `<n> rules. <n> pass their tests.`, only `rules to test on Windows`
   left. Then `--commit`. Do not sign.
9. `dev/plans/d105-interfaces.md`: differences from the contracts, every word a lane chose, the
   ids, test counts, `dev/test_collaboration.py`'s time, C14's final table (count per lane,
   `stated` / `fixed` / `moved`, the reviewer's disagreements), and section 6 under "Words
   chosen for the owner to read".
10. `dev/plans/handoff.md`: "Where the tree is" (decisions 104 to 106 built), "What is left" (the
    owner's sanity check with real AI sessions; the remote run on Windows, not run since decision
    100; the owner's first `purlin:sign` of 0.10.0 after `purlin:test --all --commit` and
    `purlin:test --remote`), and section 6 under "Words for the owner to read".

## 6. Lines a person reads, chosen

The owner reads these and says which to change.

| Where | What it says |
|---|---|
| The status, the gate (C8) | `The gate passed is met: every rule passes its tests on the committed evidence.`; `Every rule passes its tests on the committed evidence. The gate signed is met once a person signs: purlin:sign`; `The gate signed is met: signed/0.1.0.`; `The gate passed is not met.`; under `Left to do:` `2 features whose results are not committed: purlin:test --commit` |
| The walk's opening (C3, C4) | `Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.`; `Tests run by a remote runner at 2026-10-01 11:58 UTC on 1cf829e: 4 rules on Windows.`; `Signing 0.1.0 at 1cf829e.` |
| The walk's refusals (C4) | `Nothing is signed at the gate passed: the status says whether every rule passes. To sign, run purlin:init --gate signed.`; `No sign-off: the working tree holds changes that are not committed. Commit them, run purlin:test --all --commit, then purlin:sign.`; `No sign-off: the evidence is written and not committed. Run purlin:test --commit, then purlin:sign.`; `No sign-off: signed/0.1.0 is at e0deb2e, which this checkout does not hold. Pull, then run purlin:sign.`; `No sign-off: signed/0.1.0 is at e0deb2e, and the code has changed since. To sign this code, name a new version: purlin:sign --version <version>.`; `No sign-off: these results were not taken on this version of the code, 1cf829e: sample_age, stability on Linux/Unix; visit_window on Windows. Run purlin:test --all --commit and purlin:test --remote, then purlin:sign.` |
| The overview (C4, N12) | `  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.`; `  2 stops: 1 hand check, 1 weak, 0 not audited.` |
| A hand check (C4) | `critical_screen RULE-2   what did you see, in one line, or Enter for no note, or stop: `; the note recorded `no note` |
| After a sign-off (C4, N2) | `Tagged signed/0.1.0 at e0deb2e.`; `Push the branch and the tag: git push origin main signed/0.1.0`; `signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push origin main` |
| A test comment to correct (C5) | `tests/test_age.py:33 names sample_age PROOF-5, whose wording changed after the test was last changed in 495698f: it read "<old>" and now reads "<new>". Run purlin:build sample_age to make the test show it; the line clears once the test changes.`; or the ending `Its old wording is now PROOF-7: move the comment there.`; `1 test comment to correct: purlin:build` |
| The strong cell (C8) | `the last audit, before the rule or its tests changed, found it weak: <finding>` |
| Drift (C10) | `visit_window RULE-1 has no test for PROOF-3. Run purlin:build visit_window.`; `sample_age RULE-9 has no test. Run purlin:build sample_age.` |
| Setup and the upgrade (C7, C9) | `added to .purlin/config.json: project_name "labconnect"`; `"" is not accepted for project_name; it takes a name of 1 to 100 characters. Nothing was saved.`; `origin is not on GitHub or Azure DevOps, so every test runs on this machine and purlin:test --remote is not set up.` |
| Nothing to check (C15) | `security_no_dangerous_patterns RULE-3 passes with nothing to check here: this project has no screens.`; the walk's `  Linux/Unix: passed on dana-laptop; nothing to check for PROOF-3: this project has no screens` |
| The dashboard (L7) | `Checked by hand when a person signs, in the walk of purlin:sign.`; `Checked by hand. The gate passed records no hand check.` |
| The glossary (words) | `**hand-off**: what the developer does when the work is ready: purlin:test --all --commit, and purlin:test --remote for any proof tagged for another system. That commit is ready for sign-off; QA runs no tests.`; `**met**: at passed, every rule passes its tests on the committed evidence; at signed, the same, and a person has signed it, written as signed/<version>.`; `**test comment to correct**: a comment above a test that names nothing a spec has, or names a proof whose wording changed after the test last changed. It clears once the comment or the test is corrected.` |
| The build skill (words) | `Before adding any marker, read each test already marked for this spec against its proof as written now. Where one no longer shows it, fix the test, or move the comment as purlin:spec's Renumbering says. Where it shows it but its comment is to correct, change the test so it states the new wording: its name, its docstring or an assertion.` |
| The spec skill (words) | `When the conflict is two different texts of the same id, show both and ask which survives. Two ids that say different things are both kept, and the one not yet on the default branch is renumbered.` |
| `RELEASE_NOTES.md` 0.10.0 (words) | `**Purlin keeps the evidence and the sign-off.** At passed the status says whether every rule passes on the committed evidence: met or not met. There is no release step and no passed tag.`; `**The hand-off is run and commit.** purlin:test --all --commit, and purlin:test --remote for other systems.`; `**purlin:sign builds the evidence package and signs it.** It refuses, naming what to run again, when a result was not taken on this version of the code, and opens by naming who ran the tests, where and when. The first sign-off writes signed/<version>; a hand check's note is optional.`; `**A test comment whose proof was reworded is caught** until the test changes.`; `**The audit reads a rule again only when its own test changes.**`; `**.purlin/tests.md is gone**; the status and the dashboard show the results.`; `**The package names the project** from its own files, and setup writes project_name.`; `**An anchor rule with nothing to check passes, and says so.** Its test skips with a reason beginning nothing to check:, and the status, the dashboard and the package show the reason.`; the format numbers of C12 |

## 7. Questions for the owner

**Q1. Should the status call a rule passing when its results were taken on older code?**

Root: a test run reruns only the features whose own spec, code or tests changed, so after an
unrelated change elsewhere a feature's results still come from an older commit. Today the
status counts those as passing, since nothing the feature covers changed. Decision 106 says a
result counts for the sign-off only when taken on this exact version of the code; this plan
applies that at `purlin:sign` alone.

- **(a) Only the sign-off asks for this exact code, recommended.** The status keeps counting a
  feature's results while nothing it covers changed, and `purlin:sign` refuses with one line
  naming `purlin:test --all --commit` when any result is older. Consequence: day-to-day runs stay
  short; the developer's hand-off before a sign-off is a full run.
- **(b) The status asks for it too.** Every commit of code makes every rule read "to test" until
  a full run. Consequence: met always means "on this exact code", but every run is a full run
  and `purlin:test` with no feature named loses its point.

The plan is written to (a): C2's last sentence. Under (b) lane `counting` makes the passed cell
read `out of date` with the reason `taken on <sha7>, before this code` wherever `same_code` fails,
and lane `run` makes `--test` with no feature named run every feature.

**Q2. Is "nothing to check" for anchors only, or for any spec's rule?**

Root: decision 107 lets an anchor's rule, written by another team to hold across any project,
pass with a reason when this project has nothing it covers ("this project has no screens"). A
project's own spec could use the same skip for its own rules.

- **(a) Anchors only, recommended, as decision 107 is worded.** A project's own rule describes
  its own code, so a test that finds nothing to check there means the rule or the test is wrong;
  such a skip reads `not run` and keeps its reason. Consequence: one narrow door, used by
  authors who cannot know every project.
- **(b) Any spec's rule.** Consequence: a team may write its own rules "for every X" too, but a
  developer can make a rule pass by having its test skip, visible only as a reason on the
  status and in the package.

The plan is written to (a): C15's "in an anchor's section". Under (b) lane `run` drops that
condition and lane `counting`'s PROOF-274 holds for any spec.

## 8. Calls this plan makes

Not questions: each follows from decisions 104 to 106 or the code, and the owner may reverse any.

- **`purlin:sign --release` becomes `--version`**: nothing is called a release.
- **The first sign-off commits the package with its sign-off**, in one signed commit, and the tag
  sits on it; a later sign-off signs the package the tagged commit holds.
- **A test comment to correct does not fail a test run**; the status counts it, so the gate is
  not met, and the sign-off refuses it as a failing kind.
- **Times read UTC with the date**, `2026-10-01 12:17 UTC`.
- **A section's `commit` is the commit its run's work commit made**, so a run that commits specs
  or tests names the code it measured.
- **Running twice on the same code commits nothing new**; on new code every section run moves.
- **N12's vanished finding stays out of the counts**, shown as a reason on the rule.
- **Every audit written before C6 stops answering once**; none is migrated.
- **Signature verification for a reader** is taught in the docs; `purlin:sign`'s key block is
  unchanged.
- **Only a skip whose reason begins `nothing to check:` counts** (C15), so a test skipped for
  another reason (a missing tool, another system) never passes a rule.
- **The 198 test comments are cleared by the lane that owns each file**, so no two agents edit
  one file; lane `tests` takes the files no other lane owns.
