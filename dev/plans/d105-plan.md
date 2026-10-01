# Decisions 104 and 105: a team's collaboration is a rule, and the answers to the second check

Written by the planning agent on 2026-10-01, against `main` at `d7b61f266`. It builds decision 104
(one rule, one scripted proof that three people reach a signed release through git) and decision
105 (the answers to `sanity-qa-product-2.md`, N1 to N12) and nothing else. Nine lanes run at once
on this Mac, each in a worktree `/Users/richlabarca/LocalCode/purlin-wt/d105-<lane>` on branch
`lane/d105-<lane>` made from `main` at the stubs commit of section 1, each owning files no other
lane writes. One integration agent then merges them into `main` in the order of section 5.
Section 2 is the contract: every lane builds to it and none chooses. Section 7 holds the three
questions decisions 104 and 105 leave open; the plan is written to each recommended answer, and
section 7 says what changes under the others.

What decision 105 asks, and where it is built:

| Decision 105 says | Contract | Lanes |
|---|---|---|
| The release run writes fresh results for every rule at the release commit and keeps nothing from earlier runs; the package records the run; the walk opens by naming it and refuses when the branch moved past it or a result is not its own | C1, C2, C3, C4 | run, release, signoff |
| A test comment whose proof's wording changed since the test last changed is caught by the status and every test run as a test comment to correct, and clears once the test changes; `purlin:build` checks each marked test still shows its proof | C5 | drift, counting, run, words |
| The audit keeps a rule's result until that rule's own test changes | C6 | counting, run (format) |
| `.purlin/tests.md` is rendered on every run and never conflicts: setup writes a git attribute | C7 | settings, run |
| N1 a weak test under a hand check is shown and counted as weak | C8, C4 | counting, signoff |
| N2 the first sign-off names pushing the branch and the tag; a later one is refused until it holds the tagged commit | C4 | signoff |
| N5 the package's project name comes from the project's own files; setup writes it | C9 | settings, counting, release |
| N6 the release run tells the developer to push the branch for the signer | C2 | release |
| N9 drift's wording line clears once the test changed; N10 a number written twice is a collision, not a change | C5, C10 | drift |
| N11 `purlin:sign --show` needs no key | C4 | signoff |
| N12's smaller items | C10, C4, C8 | drift, signoff, counting, settings, words, docs |
| Decision 104's scripted three-person test, with a test left on a moved proof and a second signer | C11 | team |

## 1. Rules for every lane

`d103-plan.md` section 1 applies as written, with these names and changes.

- **Before the lanes: the shared stubs, one commit on `main`.** The agent that starts the lanes
  commits, alone and first, `chore: the shared interfaces of decisions 104 and 105, as stubs`,
  and every lane branches from that commit. It holds, each with the docstring section 2 gives
  and the neutral answer, so every lane imports what it calls from the first minute:
  `scripts/mcp/purlin/project.py` (`project_name` answers the folder's name;
  `ensure_table_driver` answers False and writes nothing; the two constants of C7);
  `scripts/mcp/purlin/wording.py` (`stale_comments` answers `[]`; the three constants of C5);
  in `scripts/export/release.py`, `before_run` (None), `only_records_between` (False),
  `current_branch` (''), `time_words` (the string as given), `run_lines` ([]), the constants of
  C2, and `run_release(..., run=None)` passing `run` on; in `scripts/export/package.py`,
  `build(..., run=None)` ignoring it. Nothing else changes in that commit, and the sweep is
  unchanged by it. Each stub's owner (section 3) replaces it.
- **Worktree and scratch.** Lane `<lane>` runs
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/d105-<lane> -b lane/d105-<lane> main`
  (with `main` at the stubs commit)
  and works there alone, with its own scratch folder `/private/tmp/d105-<lane>/` that no other
  agent reads or writes. It writes only the files section 3 gives it. It cannot see the other
  lanes: where it calls what another lane builds, it calls it exactly as section 2 names it, and
  the tests that need it fail until that lane merges (each lane's section lists them).
- **Environment (this Mac).** Before any test:
  `export PATH=/opt/homebrew/opt/dotnet@8/bin:/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH`.
  The worktree has no `.venv` of its own; the main checkout's is used. A lane runs its own test
  files whole with `python -m pytest <files> -q`, then `bash dev/run_tests.sh --fast` once at the
  end. It never runs the full sweep. Nine lanes share the machine: run one pytest process at a
  time, never `-n`.
- **Frozen:** `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
  `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`. A
  lane that needs a helper writes it in its own test file.
- **No generated file is staged:** `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, `docs/images/*.png`,
  `dev/plans/deck/*.png`.
- **Proofs.** Every proof written or rewritten holds one case in at most 60 words and has a marked
  test of its own. New rules and proofs take numbers in order from the next free ones section 3
  gives, which follow each spec's `> Highest-Rule:` / `> Highest-Proof:` at `d7b61f266`, and raise
  those lines. A number is never reused, a deleted one included. A proof names what a person sees
  or a file holds, never a function inside the code (decision 98).
- **A proof reworded by this plan clears its own test comment.** C5 makes a test comment whose
  proof's wording changed after the test last changed a test comment to correct. Every proof a
  lane rewords, the lane's own test for it changes in the same commit (at least its name, its
  docstring or an assertion, so the test states the new wording).
- **Clean release** (decision 44). What this plan retires is deleted outright: its code, its
  constants, its rules, its proofs and their tests, its lines in skills, references and docs. No
  test that a removed thing is absent, no compatibility reader. `RELEASE_NOTES.md` is the one
  place history is kept.
- **A rule that survives in part is reworded, not split into an old and a new one.** Its number
  stays; each proof that no longer holds is deleted or rewritten to one case of the new contract.
- **Formats.** A change to a format's parsing or emission updates its file under
  `references/formats/` in the same commit, with the number C12 gives.
- **Instruction lengths** (`dev/skill_checks.py` `CEILINGS`): status 100, test 120, build 130,
  init 250, audit 105, sign 185, export 90, spec 210, spec-from-code 130, drift 150, anchor 160,
  agent 135. Today: status 99, test 119, build 128, audit 104, export 88, sign 165, spec 192,
  drift 91, init 187, agent 132. Every line added to status, test, build, audit or export cuts
  one.
- **Deliberate break.** Each lane breaks its most important change on purpose (named in its
  section), sees its own test fail, then restores the file with `git checkout -- <that file>`,
  never `git checkout -- specs/`. The break runs only under a test that uses `dev/fake_claude.py`
  or no model, with no real `claude` on `PATH`, and reaches no git host, `gh`, `az` or network
  service: every repository a test makes is local, and a "host" is a bare repository on disk.
- **A call no decision makes and this plan does not make:** build the rest, leave that thing as
  it is, report it.
- **Commits** on the lane branch with the prefixes of `references/commit_conventions.md`, each
  ending with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01W6UPm3QPtMvgPNfN6W9vBE
  ```
  Push nothing: no branch, no tag, no pull request. No `purlin:audit`, `purlin:sign` or
  `purlin:test --release` against this repository, and no real `claude`.
- **Report** (in the last message and in `dev/plans/lanes/d105-<lane>.md`, committed on the lane
  branch): each spec's `> Highest-Rule:` and `> Highest-Proof:` after the work; tests before and
  after; every rule and proof deleted or reworded, by number; every call left; every word chosen
  that section 6 does not give; every failure in a file it does not own; every test that fails
  only because another lane has not merged.

## 2. Contracts

What two lanes share, fixed word for word. `<...>` is filled in. Filled examples use the sample
project of `sanity-qa-product-2.md`: `labconnect`, `dana.dev@labconnect.example` on `dana-laptop`,
a release branch `release/0.1.0` whose release run tested `1cf829e`.

### C1. The release run, lane `run` (calls lane `release`)

`purlin:test --release [<version>]` is still `purlin_run.py --release [VERSION]`, which implies
`--test --all --commit`. What changes:

1. **Before any test runs**, `purlin_run.py` calls `release.before_run(project_root, version)`
   (C2). On a refusal it exits 1 having started no suite and written nothing.
2. **Every section is written fresh.** Every suite runs; every feature's section for this
   operating system is built with one `at`, the time the last suite finished, and one `commit`,
   the full sha of `HEAD` when the run started, and is written with `fresh=True`
   (`evidence.merge_section(..., fresh=True)`, lane `run`): the section replaces the one there
   even when it saw the same thing, and every other operating system's section in that
   `local/<feature>.json` is removed, since it is an earlier run's. `ci/` files are not touched
   (Q2). Audit entries are not touched: they are not results.
3. The evidence is committed as now (`purlin: evidence at <sha7>`), `.purlin/tests.md` with it.
4. `purlin_run.py` then calls `release.run_release(project_root, version, run=run)` with

   ```python
   run = {'by': '<git config user.email, or "unknown">',
          'machine': evidence.local_machine(),
          'os': '<this host: windows, macos or linux>',
          'at': '<the one at every section carries>',
          'commit': '<the full sha of HEAD when the tests started>'}
   ```

A test run without `--release` keeps the retention rule of `evidence_format.md` as it is.

### C2. The release, lane `release`

In `scripts/export/release.py`, beside what is there:

```python
def before_run(project_root, version=None, out=None):
    """The checks a release makes before any test runs. Prints the refusal's
    line and returns its kind, or returns None. In this order: NO_RELEASE_WORK,
    NO_RELEASE_BEHIND, NO_VERSION, NO_RELEASE_EXISTS. Nothing is fetched."""

def run_release(project_root, version=None, out=None, run=None):
    """As now, and `run` (C1) goes to package.build. Returns (tag or None, refused or None)."""

def only_records_between(project_root, older, newer):
    """True when `older` is `newer`, or an ancestor of it, and every commit in
    older..newer changes only paths under `.purlin/`."""

def current_branch(project_root):
    """The checked-out branch's short name, or '' on a detached HEAD."""

def time_words(at):
    """`2026-10-01T12:17:13Z` read as `2026-10-01 12:17 UTC`."""

def run_lines(package):
    """The lines that name the release run: RUN_LINE filled from
    package['release_run'], then one RUN_REMOTE_LINE per operating system whose
    results came from a remote runner and count (Q2). [] where release_run is null."""

RUN_LINE = 'Tests run by %s on %s at %s on %s: %s, all passed.'
# by, machine, time_words(at), sha7 of commit, '19 rules' / '1 rule'
RUN_REMOTE_LINE = 'Tests on %s run by a remote runner at %s on %s.'
# 'Windows' (states.systems_text of one system), time_words(section at), sha7 of section commit
PUSH_FOR_SIGNER = 'Push it for the signer: git push -u origin %s'
NO_RELEASE_REMOTE = ('No release: the results on %s were not taken at %s: %s. Run '
                     'purlin:test --remote on this branch, then purlin:test --release.')
# 'Windows', sha7 of run commit, 'sample_age RULE-6; stability RULE-2'
REFUSED = ('spec', 'failing', 'remote', 'work', 'behind', 'version', 'exists', 'package', 'git')
```

- `run_release` keeps its checks and order, and adds `remote` after `failing`: a rule whose
  passed cell counts a `ci` section (Q2) whose `commit` is not one from which
  `only_records_between(section commit, run['commit'])` holds refuses with `NO_RELEASE_REMOTE`,
  one line per system.
- At the gate `signed`, after `PACKAGE_COMMITTED`: `run_lines(package)`, then `READY_TO_SIGN`,
  then `PUSH_FOR_SIGNER` filled with `current_branch`, left out on a detached HEAD.
- At the gate `passed`, after `PACKAGE_COMMITTED`: `run_lines(package)`, then `TAGGED` and
  `summary.RELEASE` as now.

```
Evidence package committed: .purlin/evidence/package/0.1.0.json.
Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules, all passed.
Run purlin:sign to sign it; the first signature writes signed/0.1.0.
Push it for the signer: git push -u origin release/0.1.0
```

### C3. The package, format 8, lane `release`

`.purlin/evidence/package/<version>.json`, schema `purlin-package/4`.

- `TOP_LEVEL = ('schema', 'state', 'rules', 'steps', 'audit', 'left', 'purlin_version',
  'project', 'version', 'tag', 'commit', 'release_run', 'gate', 'mutation_engine', 'features',
  'hand_checks', 'warnings', 'fingerprint')`.
- `package.build(project_root, release=None, run=None)`. `release_run` is null where `run` is
  None (`purlin:export`), else:

  ```json
  "release_run": {"by": "dana.dev@labconnect.example", "machine": "dana-laptop", "os": "linux",
                  "at": "2026-10-01T12:17:13Z", "commit": "<40 hex>", "rules": 19, "passed": 19}
  ```

  `rules` and `passed` are the package's own `rules` and `steps.passed`.
- Each entry of a rule's `results` gains `"release_run": true|false`: true for a `local` result
  whose `os`, `machine`, `at` and `commit` equal the run's, and for a `ci` result whose section
  `commit` satisfies `release.only_records_between(<that commit>, run['commit'])` (Q2); false
  otherwise, and always false where `release_run` is null.
- `project` is the payload's `project` (C9).
- `references/formats/package_format.md` goes to Format-Version 8 and says what `release_run` and
  each result's `release_run` mean, that a release run writes every local result afresh, and
  where `project` comes from.

### C4. The sign-off walk, lane `signoff`

**Refusals**, in this order, each one line, nothing written, exit 1 (the first exit 0):
`AT_PASSED`, `NO_SIGNOFF_WORK`, `NO_VERSION`, `NO_SIGNOFF_ELSEWHERE`, `NO_SIGNOFF_PACKAGE`,
`NO_SIGNOFF_NO_RUN`, `NO_SIGNOFF_MOVED`, `NO_SIGNOFF_NOT_RUN`, `NO_SIGNOFF_FAILING`,
`NO_SIGNOFF_BEHIND`, `ALREADY_SIGNED`. The new and changed ones:

```python
NO_SIGNOFF_ELSEWHERE = ('No sign-off: %s is at %s, which this checkout does not hold. '
                        'Pull, then run purlin:sign.')
# fires when the tag signed/<version> exists here and its commit is not an ancestor of HEAD
NO_SIGNOFF_NO_RUN = ('No sign-off: the evidence package for %s was not written by a release '
                     'run. Run purlin:test --release.')
NO_SIGNOFF_MOVED = ('No sign-off: the release run tested %s, and %s has moved past it to %s. '
                    'Run purlin:test --release.')
# release_run commit sha7, current_branch or 'HEAD', HEAD sha7; fires as today's check does
NO_SIGNOFF_NOT_RUN = ("No sign-off: the evidence package for %s holds results that are not "
                      "the release run's: %s. Run purlin:test --release.")
# any result with current true and release_run false; 'sample_age RULE-1, RULE-2; stability RULE-1'
```

**The key** (N11): `refusal()` no longer checks it. `--show` never asks for or names a key. The
terminal walk and `--answers` check it after the refusals and before the first line they print;
with none they print today's `NO_KEY` block and exit 1.

**The opening** (decision 105): the walk, `--show` and `--answers` print `release.run_lines`
first, then `OVERVIEW` as now.

**The overview** (N12, one count for one fact):

```python
OVERVIEW_RULES = '  %s on %s: %s, %s.'
# '19 rules', 'Linux/Unix', '19 pass their tests' (package steps.passed), '1 has a hand check' / '2 have a hand check'
OVERVIEW_STOPS = '  %s: %s, %s, %s.'
# '2 stops', '1 hand check' / '2 hand checks', '1 weak', '0 not audited'
```

The sign-off's `shown.overview.passing` is `steps.passed`.

**A hand check with a weak audit** (N1): it still stops once, as a hand check, and its stop
shows `Rule`, `Proof`, then `Results` and `What the audit found` wherever the rule's `audit`
verdict is `weak` or `undecided`, then asks `HAND_ASK` as now.

**The push lines** (N2):

```python
SIGNED_PUSH = summary.NOTHING_LEFT + ' Push the branch and the tag: git push origin %s %s'
# printed after TAGGED by the first sign-off in place of summary.RELEASE; summary.RELEASE where HEAD names no branch
TAG_STAYS = '%s stays at %s; this sign-off is added after it. Push it: git push origin %s'
# the branch; 'Push it: git push' where HEAD names no branch
```

**The sign-off file**, signature format 15: `shown` gains `release_run`, a copy of the package's;
`shown.overview.passing` is `steps.passed`. Nothing else changes.

```
Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules, all passed.
Signing 0.1.0: .purlin/evidence/package/0.1.0.json, at 5d6ab5b.
  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.
  The audit: 17 strong, 1 weak, 0 not audited.
  2 stops: 1 hand check, 1 weak, 0 not audited.
...
Signed 0.1.0 as quinn.qa@labconnect.example with the key ending ...gNPU.
Tagged signed/0.1.0 at e0deb2e.
Nothing left to do. Push the branch and the tag: git push origin release/0.1.0 signed/0.1.0
Sign-offs of 0.1.0: quinn.qa@labconnect.example.
```

```
No sign-off: signed/0.1.0 is at e0deb2e, which this checkout does not hold. Pull, then run purlin:sign.
signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push origin release/0.1.0
Sign-offs of 0.1.0: quinn.qa@labconnect.example, pat.product@labconnect.example.
```

### C5. A test comment to correct, lane `drift` (read by `counting`, `run`, `drift`)

New `scripts/mcp/purlin/wording.py`, the one home of the check:

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
    has changed now, and is never named. `features` is specs.scan_specs's answer and
    `scanned` markers.scan's, read with tracked_only=True where not given.

    Each entry: {'file', 'line', 'feature', 'id', 'commit' (sha7), 'old', 'new',
    'now_under' (the other proof id of the spec that holds `old` exactly, or None),
    'text'}. `text` is STALE filled, then STALE_MOVE where now_under, else STALE_BUILD."""
```

- **Cost:** at most one `git blame --porcelain` per test file holding a marker and one per spec,
  each cached for the call; a proof whose spec line was last written in the test's last-change
  commit or an ancestor of it is not compared further; one `git show` per distinct
  (commit, spec) compared. On this repository `sync_status` takes no more than 3 seconds longer
  than at `d7b61f266`; the lane reports both times.
- **Who reads it:** the payload (C8) puts each entry's `text` in `warnings` and counts each under
  `to_correct`; `purlin_run.py` prints each `text` after the markers lines of every `--test`,
  `--audit` and `--release` run, with no change to the exit code; drift (C10) prints the entries
  whose proof changed in its range or whose file the range changed; `renumber.py` moves a
  comment to `now_under` (its C10 step 3), and names the others as it names an uncommitted
  comment.
- `drift.comment_reworded`, `COMMENT_CHANGED` and `COMMENT_CHECK` are deleted; `COMMENT_MOVE`
  becomes `wording.STALE_MOVE`.

```
tests/test_age.py:33 names sample_age PROOF-5, whose wording changed after the test was last changed in 495698f: it read "A sample collected 100 minutes before the fall-back change has an age of `100` minutes" and now reads "A sample's age is cut to whole minutes: `1` minute". Its old wording is now PROOF-7: move the comment there.
Left to do:
  1 test comment to correct: purlin:build
```

A release with one left refuses as today: `No release: 1 test comment does not count at
1cf829e: 1 test comment to correct. Run purlin:status to see what is left, then purlin:test
--release.`

### C6. The audit's per-test key, lane `counting` (format text by lane `run`)

A rule's `test_hash` in the payload, which every audit entry carries and is compared on, is the
sha256 of the sorted lines `<file> <test name> <sha256 of the test's source>`, one per test tied
to the rule's proofs (the tests `_backing_tests` names, as now). The source is the test's own
declaration, as `markers` bounds it, line ends read as `\n`. For a test of a suite in the `exit`
format, run whole, and for a test whose declaration cannot be found by its name, the part is
`<file> <test name> <blob id of the file>`, as now. `test_hash_kind` is `test` where every part
read a declaration, `file` where any read the file, `manual` and `none` as now;
`TEST_HASH_KINDS = ('manual', 'file', 'test')`. Every audit entry written before this change
stops answering once, and its rule reads `not audited` until the next audit. No entry is
migrated. Evidence format 8 says what `test_hash` is.

### C7. The table that never conflicts, lanes `settings` and `run`

New `scripts/mcp/purlin/project.py` (lane `settings`):

```python
TABLE_DRIVER = 'purlin-table'
TABLE_DRIVER_NAME = "Purlin's table, rendered again on every run"

def ensure_table_driver(project_root):
    """Set `merge.purlin-table.name` and `merge.purlin-table.driver` (`true`) in this
    clone's own git settings where either is missing. True when it wrote. Never raises."""
```

New `templates/gitattributes.purlin`:

```
# Purlin renders .purlin/tests.md again on every run, so a merge keeps this side's table.
.purlin/tests.md merge=purlin-table
```

- Setup appends it to `.gitattributes` once, guarded by its first line, and calls
  `ensure_table_driver`. `purlin:init --update` does the same where the line is missing. This
  repository's own `.gitattributes` carries it.
- Every `purlin_run.py` run that writes evidence calls `ensure_table_driver` first, so every
  clone that has run the tests once keeps one side on a merge with no conflict.
- `.purlin/tests.md` is rendered on every run that writes evidence: `--test` (with
  `Nothing to run`), `--audit` and `--release`, and committed with the evidence under `--commit`.
  `--ci` leaves it to the next run on a person's machine, as now.

### C8. The payload and the cells, lane `counting`

- `payload.build_payload` calls `wording.stale_comments(project_root, features, scanned)` once,
  appends each entry's `text` to `warnings`, and adds their count to `corrections`, which
  `summary.left` turns into `to_correct` as now. `SCHEMA_VERSION` stays 13: no key is added.
- **N1:** in `states._strong_cell`, a rule with a `@manual` proof whose audit entry reads `weak`
  or `undecided` reads `weak`, its reasons the audit's findings then `manual proof`; its `left`
  is `to_strengthen`. A rule with a `@manual` proof and any other audit, or none, reads
  `manual test` as now.
- **N12, the vanished finding:** a strong cell reading `waiting` or `not audited`, for a rule
  whose evidence still holds an audit entry that no longer answers and read `weak`, gains one
  reason per finding of it: `EARLIER_WEAK = 'the last audit, before the rule or its tests
  changed, found it weak: %s'`. It is counted nowhere.
- **N12, no code:** `status._holds_code` counts a file only where it holds at least one byte, so
  a tree of empty `__init__.py` files ends on `→ Run: purlin:spec <name> to write the first
  spec.`
- `payload.project` is `project.project_name(project_root, config)` (C9).

### C9. The project's name, lane `settings`

In `scripts/mcp/purlin/project.py`:

```python
def project_name(project_root, config=None):
    """The first of these that names one, stripped: `project_name` in
    .purlin/config.json; `[project]` then `[tool.poetry]` `name` in pyproject.toml;
    `name` in package.json; the name of the first root *.csproj file without
    `.csproj`, in name order; the last path segment of `git remote get-url origin`
    without `.git`; the project folder's name."""
```

- `templates/config.json` gains `"project_name": ""` as its first key; setup writes the
  answer of `project_name` over the folder it sets up, keeping a value already there. The config
  now carries seven keys.
- `purlin:init --update` adds it where missing, printing
  `added to .purlin/config.json: project_name "labconnect"`.
- The settings tool accepts `project_name` as `a name of 1 to 100 characters`.
- This repository's `.purlin/config.json` gains `"project_name": "purlin"`.

### C10. Drift and the helper, lane `drift`

- **N9:** drift's comment lines are C5's. **N10:** an id the range's end writes twice is left
  out of `proofs_changed` and its line. **N12:** a `checkout` entry of the reflog whose old and
  new sha are the same is not an action, so `git pull`, `git checkout -b`, then drift measures
  from before the pull; the engineer view's no-test line is one line per rule:
  `NO_TEST_FOR = '%s %s has no test for %s. Run purlin:build %s.'` naming the proofs with no
  test joined `, `, or `NO_TEST = '%s %s has no test. Run purlin:build %s.'` for a rule with no
  proof.
- **N12, the helper's order:** a moved rule line is written after the spec's last `- RULE-`
  line, and a moved proof line after its last `- PROOF-` line, so the numbers read in order.
- `references/drift_criteria.md` goes to Criteria-Version 13.

### C11. The three-person test, lane `team`

`specs/team/collaboration.md`, new:

```
# Feature: collaboration

> Description: Product, QA and dev work at once through git, in three clones of one repository,
>   and reach a release signed at the gate `signed`. A script plays the three people, forces
>   collisions, merges in both orders, and checks the run completes with no step stuck, no
>   command failing unexpectedly and nothing corrupted. The run with real AI sessions is the
>   owner's sanity check, not this proof.
> Scope: scripts/init/scaffold.py, scripts/run/purlin_run.py, scripts/run/evidence.py, scripts/export, scripts/review/sign.py, scripts/spec/renumber.py, scripts/mcp/purlin
> Stack: python/stdlib (subprocess), git, ssh-keygen, pytest
> Highest-Rule: 1
> Highest-Proof: 1

## Rules

- RULE-1: Three people working at once through git reach a signed release: the release carries `signed/<version>`, and its committed evidence package describes the tagged commit and matches its fingerprint; no step needs a command that Purlin's output, skills and docs do not give; no command fails unexpectedly, and every warning raised along the way is resolved by the end; no spec holds a number twice or a merge-conflict line; every test comment is tied and names a proof with the wording it was marked against; each spec's highest-number lines cover its numbers; and the package lists every rule

## Proofs

- PROOF-1 (RULE-1): Pat, Quinn and Dana work in three clones of one bare repository at the gate `signed`; two pairs of branches take the same numbers, one merged QA first and one dev first; a test stays marked on a proof whose number moved; Dana releases `0.1.0`; Quinn signs, then Pat; every check of RULE-1 holds
```

`dev/test_collaboration.py`, one test marked `# purlin: collaboration PROOF-1`, the scenario of
section 3, lane `team`. It writes its sample project from text in the test file (no fixture
folder), gives each person a `HOME` of their own under `tmp_path` (so `~/.ssh` and
`git config --global` are theirs), makes every key inside the test with `ssh-keygen`, sets
`GIT_CONFIG_NOSYSTEM=1`, uses a bare repository on disk as the host, runs no audit and calls no
model, and finishes in under 120 seconds on this Mac.

### C12. Format and schema numbers

| File | Now | After | Why |
|---|---|---|---|
| `references/formats/package_format.md` | 7 | 8 | `release_run` added; each result's `release_run`; schema `purlin-package/4`; `project`'s source |
| `references/formats/signature_format.md` | 14 | 15 | `shown.release_run` added; `shown.overview.passing` counts every rule that passes |
| `references/formats/evidence_format.md` | 7 | 8 | `test_hash` is per test (C6); a release run writes every local section afresh and removes other systems' (C1); the table is rendered on every run and merged by the attribute (C7) |
| `references/formats/spec_format.md` | 21 | 21 | unchanged |
| `references/formats/anchor_format.md` | 11 | 11 | unchanged |
| `references/formats/marker_format.md` | 3 | 3 | unchanged |
| payload `schema_version` | 13 | 13 | no key added or removed: the stale lines ride in `warnings` |
| `references/drift_criteria.md` Criteria-Version | 12 | 13 | the comment check's basis (C5), the collision left out of `changed`, the checkout that moves nothing |

`specs/export/package.md` names `package format 8`; `specs/review/signatures.md` names
`signature format 15`.

## 3. The lanes

Every file that changes has exactly one owner. Ownership follows `d103-plan.md` section 4 where
it fits.

| Lane | Owns |
|---|---|
| L1 `settings` | new `scripts/mcp/purlin/project.py`; new `templates/gitattributes.purlin`; `scripts/init/{scaffold,update}.py`; `templates/config.json`; `scripts/mcp/purlin/server.py`; `scripts/run/workflow.py` (`UNKNOWN_HOST` alone); `.purlin/config.json`; `.gitattributes`; `specs/mcp/{config_engine,server}.md`; `specs/init/{scaffold,update}.md`; `dev/test_{config_engine,mcp_server,init_scaffold,init_update}.py`; `dev/fixtures/upgrade-0.9.5/**`; `skills/init/SKILL.md`; `specs/skills/skill_init.md`; `dev/test_skill_init.py` |
| L2 `drift` | new `scripts/mcp/purlin/wording.py`; `scripts/mcp/purlin/drift.py`; `scripts/spec/renumber.py`; `specs/mcp/drift.md`; `specs/spec/renumber.md`; `dev/test_drift.py`; `dev/test_renumber.py`; new `dev/test_wording.py`; `references/drift_criteria.md`; `skills/drift/SKILL.md`; `specs/skills/skill_drift.md`; `dev/test_skill_drift.py` |
| L3 `counting` | `scripts/mcp/purlin/{payload,states,status,summary,board}.py`; `specs/mcp/{states,summary}.md`; `dev/test_{states,summary,backing_tests,failing,purlin_output}.py`; `specs/instructions/purlin_output.md`; `skills/status/SKILL.md`; `specs/skills/skill_status.md`; `dev/test_skill_status.py` |
| L4 `release` | `scripts/export/{release,package}.py`; `specs/export/{release,package}.md`; `dev/test_export.py`; `dev/test_tag.py`; `references/formats/package_format.md`; `skills/export/SKILL.md`; `specs/skills/skill_export.md`; `dev/test_skill_export.py` |
| L5 `signoff` | `scripts/review/sign.py`; `scripts/mcp/purlin/signatures.py`; `specs/review/signatures.md`; `dev/test_signatures.py`; `references/formats/signature_format.md`; `skills/sign/SKILL.md`; `specs/skills/skill_sign.md`; `dev/test_skill_sign.py` |
| L6 `run` | `scripts/run/purlin_run.py`; `scripts/run/evidence.py`; `references/formats/evidence_format.md`; `specs/run/{run_script,evidence_writer}.md`; `dev/test_{run_script,evidence_writer}.py`; `skills/{test,audit}/SKILL.md`; `specs/skills/{skill_test,skill_audit}.md`; `dev/test_skill_{test,audit}.py` |
| L7 `words` | `skills/{spec,build}/SKILL.md`; `specs/skills/{skill_spec,skill_build}.md`; `dev/test_skill_{spec,build}.py`; `references/{glossary,purlin_commands,hard_gates,spec_quality_guide}.md`; `agents/purlin.md`; `specs/instructions/purlin_agent.md`; `dev/test_purlin_agent.py`; `README.md`; `RELEASE_NOTES.md` |
| L8 `docs` | `docs/{index,getting-started,how-purlin-works,raising-the-gate-and-upgrading,regulated-workflow,review-and-signing,running-and-evidence,team-workflow,working-together,qa-guide}.md`; `specs/instructions/purlin_docs.md`; `dev/test_purlin_docs.py` |
| L9 `team` | new `specs/team/collaboration.md`; new `dev/test_collaboration.py` |

No lane: `scripts/mcp/purlin/{markers,specs,evidence,fingerprint,gate,report_data}.py`,
`scripts/review/{ai_audit,marked_tests}.py`, `scripts/run/{ci,host,remote,reports}.py`, the
dashboard (`scripts/report/src/**`, its fixtures and spec: no word it shows changes), the deck,
`CLAUDE.md`, `dev/test_vocabulary.py`. A failure the sweep finds there is integration's.

### L1 `settings`

Builds C7's `project.py` half and setup's attribute, C9, and `UNKNOWN_HOST`'s words (section 6).
The init skill names the seven keys, the `.gitattributes` line and why, within 250.

Next free ids and the work:
- `specs/mcp/config_engine.md` (R18 P44; next RULE-19, PROOF-45), `> Scope:` adds
  `scripts/mcp/purlin/project.py`: RULE-19, the project's name is the first source C9 lists that
  names one (PROOF-45 the config's value wins over `pyproject.toml`; PROOF-46 `[project] name`;
  PROOF-47 `package.json`'s `name`; PROOF-48 a root `Intake.csproj`; PROOF-49 the origin URL
  `/srv/git/labconnect.git`; PROOF-50 none, the folder's name). RULE-20, the table's merge
  driver is set where missing and left where set (PROOF-51 both keys written; PROOF-52 a driver
  already set is left as it was).
- `specs/init/scaffold.md` (R78 P170; next RULE-79, PROOF-171): RULE-79, setup writes
  `project_name` (PROOF-171, a `pyproject.toml` naming `labconnect`). RULE-80, setup writes the
  attribute once and sets the driver (PROOF-172 the line once after two runs; PROOF-173 the clone's
  git settings hold the driver). RULE-81, in a set-up clone, two branches that each changed
  `.purlin/tests.md` merge with no conflict, keeping the checked-out side's table (PROOF-174). The
  proofs quoting `UNKNOWN_HOST` are reworded to section 6's words.
- `specs/init/update.md` (R49 P161; next RULE-50, PROOF-162): RULE-50, the upgrade adds
  `project_name` with its line (PROOF-162). RULE-51, it adds the attribute line and the driver
  where missing (PROOF-163). The proofs quoting `UNKNOWN_HOST` or `six keys` are reworded.
- `specs/mcp/server.md` (R32 P163; next RULE-33, PROOF-164): RULE-33, the settings tool writes a
  `project_name` of 1 to 100 characters (PROOF-164) and refuses an empty one with
  `"" is not accepted for project_name; it takes a name of 1 to 100 characters. Nothing was saved.`
  (PROOF-165).
- `specs/skills/skill_init.md` (R85 P96; next RULE-86, PROOF-97): RULE-86, the skill names the
  seven keys and the table's attribute (PROOF-97); proofs quoting `six keys` are reworded.

Break on purpose: write the attribute without calling `ensure_table_driver`; PROOF-174's test
fails with a conflict.

Tests that may fail only because another lane has not merged: none; the end-to-end setup tests
that read the status's head line read the folder's name until lane `counting` merges.

### L2 `drift`

Builds C5 (`wording.py`) and C10. `drift.py` calls `wording.stale_comments` and keeps its
range filter. `renumber.py` uses `now_under` for its step 3 and writes moved lines in order. The
drift skill says the wording line clears once the test changes, through `purlin:build`, within
150.

Before building, the lane runs C5's check over this repository and reports the count (the
planning agent's rough pass found 198 markers in 23 specs, `purlin_report` 42, `run_script` 33,
`host` 20, `states` 20 first) and the time, for integration's step 4.

- `specs/mcp/drift.md` (R34 P80; next RULE-35, PROOF-81), `> Scope:` adds
  `scripts/mcp/purlin/wording.py`: the rules and proofs quoting `COMMENT_CHANGED` or
  `COMMENT_CHECK` are reworded to C5's words. RULE-35, a comment is named when its proof's
  wording changed after its test last changed (PROOF-81 a proof edited after the test is named
  with `STALE`; PROOF-82 a test edited after the proof is not named; PROOF-83 a test with an
  uncommitted edit is not named; PROOF-84 only the comment line rewritten, the test body not, is
  still named). RULE-36, an id written twice is no proof changed (PROOF-85). RULE-37, a checkout
  that moves nothing does not start the range (PROOF-86). RULE-38, the engineer view names a
  rule's untested proofs (PROOF-87 `visit_window RULE-1 has no test for PROOF-3. Run
  purlin:build visit_window.`).
- `specs/spec/renumber.md` (R9 P12; next RULE-10, PROOF-13): RULE-6 is reworded to C5's basis,
  its PROOF-8 with it. RULE-10, a moved line is written after the last line of its kind (PROOF-13
  a rule; PROOF-14 a proof).
- `specs/skills/skill_drift.md` (R13 P39; next RULE-14, PROOF-40): RULE-14, the skill sends a
  wording line to `purlin:build` and says it clears once the test changes (PROOF-40).

Break on purpose: blame the comment line alone in `stale_comments`; PROOF-82's test fails.

Tests that may fail only because another lane has not merged: the drift tests that read the
`qa` view's `Left to do` count of test comments (lane `counting`).

### L3 `counting`

Builds C6 and C8. The status skill says a test comment to correct goes to `purlin:build`, which
checks the test still shows its proof, within 100.

- `specs/mcp/states.md` (R109 P264; next RULE-110, PROOF-265): RULE-110, a rule's test hash is
  taken over its own tests (PROOF-265 editing another test of the same file leaves it; PROOF-266
  editing the rule's test changes it; PROOF-267 a shell test run whole hashes the file and reads
  `test_hash_kind` `file`). RULE-111, weak wins over a hand check (PROOF-268: a rule with a
  `@manual` proof and an audit reading weak reads `weak` with the finding and `manual proof`,
  and its `left` is `to_strengthen`). RULE-112, a test comment to correct is a warning and is
  counted (PROOF-269 the status prints C5's line and `1 test comment to correct: purlin:build`;
  PROOF-270 after the test changes, neither). RULE-113, the status head names the project from
  its files (PROOF-271 `Purlin status: labconnect, ...` from `pyproject.toml`, the config naming
  none). RULE-114, the earlier weak finding (PROOF-272). RULE-39 is reworded to "a file of code
  that holds something" (PROOF-273: a tree of empty `__init__.py` files ends on
  `→ Run: purlin:spec <name> to write the first spec.`). RULE-35 and RULE-90's proofs stay; any
  that names the file's blob is reworded to the test's source.
- `specs/mcp/summary.md` (R19 P47): no change unless a proof quotes a line that moved.
- `specs/skills/skill_status.md` (R12 P36; next RULE-13, PROOF-37): RULE-13 (PROOF-37).

Break on purpose: hash the test file's blob again; PROOF-265's test fails.

Tests that may fail only because another lane has not merged: PROOF-269 and PROOF-270 (the
stub of `wording.stale_comments` answers `[]` until lane `drift` merges) and PROOF-271 (the stub
of `project.project_name` answers the folder's name until lane `settings` merges).

### L4 `release`

Builds C2 and C3, package format 8, and the export skill's line that a package `purlin:export`
writes carries no release run and cannot be signed, within 90.

- `specs/export/release.md` (R12 P16; next RULE-13, PROOF-17): RULE-13, the checks before any
  test runs, in C2's order (PROOF-17 uncommitted work; PROOF-18 the tag already written).
  RULE-14, the package records the release run (PROOF-19). RULE-15, a remote result counts only
  over the release run's code (PROOF-20 refused with `NO_RELEASE_REMOTE`; PROOF-21 accepted when
  the commits between changed only `.purlin/`). RULE-16, at `signed` the run ends on the push
  line (PROOF-22) and leaves it out on a detached HEAD (PROOF-23). RULE-17, the run's line
  (PROOF-24).
- `specs/export/package.md` (R31 P64; next RULE-32, PROOF-65): RULE-3 and its PROOF-3 and PROOF-46
  reworded to C3's keys and schema. RULE-32, `release_run` is null from `purlin:export`
  (PROOF-65). RULE-33, a result's `release_run` (PROOF-66 true for the run's own; PROOF-67 false
  for a section another run wrote). RULE-34, `project` is the project's own name (PROOF-68).
- `specs/skills/skill_export.md` (R14 P36; next RULE-15, PROOF-37): RULE-15 (PROOF-37).

Break on purpose: mark every result `release_run` true; PROOF-67's test fails.

Tests that may fail only because another lane has not merged: PROOF-68 (lane `settings`'s
`project.py`, through the payload of lane `counting`).

### L5 `signoff`

Builds C4 and signature format 15. Its own package helper in `dev/test_signatures.py` writes
C3's shape (schema 4, `release_run`, each result's flag), so its tests run before `release`
merges. The sign skill: `--show` runs first and needs no key; the key step comes before
`--answers`; the push lines; the refusal of a later sign-off and its pull; within 185.

- `specs/review/signatures.md` (R111 P222; next RULE-112, PROOF-223): RULE-102's refusals gain
  `NO_SIGNOFF_ELSEWHERE`, `NO_SIGNOFF_NO_RUN` and `NO_SIGNOFF_NOT_RUN` in C4's order and the
  reworded `NO_SIGNOFF_MOVED`, one new proof each (PROOF-223 to PROOF-225), the old moved proof
  reworded. RULE-112, the walk opens with the run's line (PROOF-226). RULE-113, `--show` asks for
  no key (PROOF-227), and `--answers` with no key prints the key block before anything else
  (PROOF-228). RULE-114, a hand check whose audit reads weak shows what the audit found
  (PROOF-229). RULE-115, the overview's counts (PROOF-230). RULE-116, the push lines (PROOF-231
  the first sign-off; PROOF-232 a later one). RULE-117, the sign-off records the release run
  (PROOF-233).
- `specs/skills/skill_sign.md` (R31 P62; next RULE-32, PROOF-63): RULE-32, the skill runs `--show`
  before any key question (PROOF-63) and names both push lines (PROOF-64).

Break on purpose: drop the ancestor check behind `NO_SIGNOFF_ELSEWHERE`; PROOF-223's test fails.

Tests that may fail only because another lane has not merged: none; `release.run_lines`,
`current_branch` and `time_words` are lane `release`'s, so the lane's own tests that reach them
fail until it merges. List them.

### L6 `run`

Builds C1, C7's run half, and C5's printing. `evidence.merge_section` gains `fresh=False`;
`write_table` is called on every path C7 names. Evidence format 8. The test skill names the
release's push line and that the release names its run; the audit skill says a rule is read
again only when its own test changed; within 120 and 105.

- `specs/run/run_script.md` (R94 P269; next RULE-95, PROOF-270): RULE-95, `--release` refuses
  before any test runs (PROOF-270 uncommitted work: exit 1, no suite started). RULE-96,
  `--release` writes every section afresh (PROOF-271 a second release run with the same results
  writes the new `at` and `commit`; PROOF-272 another system's local section is removed).
  RULE-97, the release names the person and the machine (PROOF-273 the package's
  `release_run.by` is the git email). RULE-98, every test run prints each test comment to correct
  and exits as its tests do (PROOF-274). RULE-99, a run sets the table's driver (PROOF-275).
- `specs/run/evidence_writer.md` (R26 P89; next RULE-27, PROOF-90): RULE-27, the table is
  rendered on every run (PROOF-90 `Nothing to run`; PROOF-91 an audit). RULE-28, a fresh write
  replaces a section that saw the same thing (PROOF-92).
- `specs/skills/skill_test.md` (R21 P50; next RULE-22, PROOF-51): RULE-22 (PROOF-51).
  `specs/skills/skill_audit.md` (R25 P52; next RULE-26, PROOF-53): RULE-26 (PROOF-53).

Break on purpose: let `--release` keep a section that saw the same thing; PROOF-271's test fails.

Tests that may fail only because another lane has not merged: PROOF-273 (lane `release`),
PROOF-274 (lane `drift`'s `wording`), PROOF-275 (lane `settings`'s `project`).

### L7 `words`

- `skills/build/SKILL.md`: step 1 of "Writing the code and the tests" opens with: before adding
  any marker, read each test already marked for the spec against its proof as written now; where
  one no longer shows it, fix the test, or move the comment as "Renumbering" says. A test comment
  to correct clears once its test changes: where the test already shows the new wording, change
  the test so it states it (its name, its docstring or an assertion). Within 130.
- `skills/spec/SKILL.md` "After a merge conflict": "When the conflict is two different texts of
  the same id, show both and ask which survives. Two ids that say different things are both
  kept, and the one not yet on the default branch is renumbered." Within 210.
- `references/glossary.md`: `release run` (section 6); `test comment to correct` gains the
  wording case. `references/purlin_commands.md`: `purlin:test --release` names its push line and
  the run in the package; `purlin:sign --show` writes nothing and needs no key.
  `references/hard_gates.md`: the release section says the release run writes every result
  afresh, a remote result counts over the same code (Q2), and a later sign-off needs the tagged
  commit. `references/spec_quality_guide.md`: a reworded proof needs its test changed.
- `agents/purlin.md`: one line in the loop, a test comment to correct goes to `purlin:build`;
  within 135.
- `README.md` and `RELEASE_NOTES.md` 0.10.0: section 6's lines; format numbers of C12.
- `specs/skills/skill_build.md` (R19 P48; next RULE-20, PROOF-49): RULE-20, the check before
  adding a marker (PROOF-49). RULE-21, clearing the line by changing the test (PROOF-50).
  `specs/skills/skill_spec.md` (R30 P60; next RULE-31, PROOF-61): RULE-31, two ids that differ
  are both kept (PROOF-61). `specs/instructions/purlin_agent.md` (R17 P48; next RULE-18,
  PROOF-49): RULE-18 (PROOF-49).

Break on purpose: drop the check from the build skill; PROOF-49's test fails.

Tests that may fail only because another lane has not merged: none.

### L8 `docs`

Every page says what C1 to C10 build, in section 6's words:
`docs/review-and-signing.md` (the release run writes every result afresh and is named at the top
of the walk; `Push it for the signer`; the first sign-off's push of the branch and the tag; a
later signer pulls first; verifying a signed commit with `gpg.ssh.allowedSignersFile`, the
commands given); `docs/qa-guide.md` "The release" (where the signer finds the branch:
`git fetch`, `git switch release/<version>`; `purlin:sign --show` needs no key); 
`docs/team-workflow.md` (the table's attribute and why; the merge recipe names
`.purlin/tests.md`; the package and its sign-offs stay on the release branch and its tag, and
only a fix merges back to the default branch); `docs/running-and-evidence.md` (the release run;
a test comment to correct; the audit reads a rule again only when its own test changed);
`docs/working-together.md` (drift's wording line clears once the test changes; a number written
twice is not a change); `docs/getting-started.md`, `docs/regulated-workflow.md` (the sample
package at `purlin-package/4` with `release_run`), `docs/how-purlin-works.md`,
`docs/raising-the-gate-and-upgrading.md` (the upgrade adds `project_name` and the attribute),
`docs/index.md` where a line changed.

`specs/instructions/purlin_docs.md` (R13 P18; next RULE-14, PROOF-19): RULE-14, the release page
gives the run's line and both push lines (PROOF-19). RULE-15, the team page names the table's
attribute (PROOF-20).

Break on purpose: none in code; the lane runs `dev/test_purlin_docs.py` and greps its files for
`purlin-package/3`, `Push it: git push$`, `whose wording changed since the comment` (each empty).

Tests that may fail only because another lane has not merged: none.

### L9 `team`

Builds C11. The scenario, every command as its skill runs it (the table of
`sanity-qa-product-2.md` section 1), each `purlin_run.py`, `sign.py`, `renumber.py`,
`package.py` and `scaffold.py` call a subprocess with `sys.executable`, `sync_status` and drift
through `scripts/mcp/purlin/server.py` over JSON-RPC as the agent calls them:

1. Pat: a `pyproject.toml` naming `labconnect`, version `0.1.0`, pytest settings; setup at
   `--gate signed --yes`; push `main`.
2. Pat on `product/specs`: `sample_age` and `stability`, two rules and three proofs each, each
   committed `spec(<name>):`; merged to `main`, pushed.
3. Dana on `dev/build`: code and marked tests; the first test run's suggested `tests` entry is
   written through the settings tool; `--test --commit`; merged, pushed.
4. **Collision one, QA first:** Quinn on `qa/frozen` and Dana on `dev/tube-case`, both from the
   same `main`, each add `stability` RULE-3 and PROOF-4; Dana's test is marked
   `stability PROOF-4`. Quinn merges and pushes first. Dana pulls: the conflict is resolved by
   keeping both lines; the status names the number written twice; drift names which line moves;
   `renumber.py stability --dry-run`, then without; committed; `--test --commit`; merged, pushed.
5. **Collision two, dev first:** Dana and Quinn each add `sample_age` PROOF-4 from the same
   `main`; Dana merges first; Quinn pulls, resolves, renumbers (Quinn's becomes PROOF-5),
   merges. Both branches committed evidence for different features, and the merge of
   `.purlin/tests.md` ends with no conflict.
6. **A test left on a moved proof:** Dana, on a branch made from Quinn's commit before the
   renumber, marks a test `sample_age PROOF-4` for Quinn's proof; after the merge the status
   prints C5's line naming `PROOF-5` as where the old wording is now, and `1 test comment to
   correct: purlin:build`; `renumber.py sample_age` moves it; the line is gone.
7. Dana: `release/0.1.0` from `main`; `purlin_run.py --release`; runs the push line it prints.
8. Quinn: fetch, switch to the branch; `sign.py --show` with no key set (it shows the walk); then
   `sign.py --answers` prints the key block, whose commands the test runs as printed with
   Quinn's `HOME`; answers file; `--answers`; runs the push line it prints.
9. **A second signer:** Pat, on the release branch as it stood before Quinn signed, runs
   `git fetch` (which brings the tag) and `sign.py --answers`: refused with
   `NO_SIGNOFF_ELSEWHERE`; pulls as it says, signs, runs the push line `TAG_STAYS` prints.
10. The end checks, in a fresh clone of the bare repository at `signed/0.1.0` and at
    `origin/release/0.1.0`: every one of RULE-1's, each its own assertion with a message naming
    it: the tag exists on the host; `package.py --check` prints `The package matches its
    fingerprint.`; `git diff --name-only <package commit> signed/0.1.0` lists only paths under
    `.purlin/evidence/package/`; both sign-off files are on the branch's tip and each counts;
    every command's exit code was the one expected (the refusal in step 9 and the status reading
    a number twice in steps 4 and 5 the only planned ones); every warning line any status or
    run printed is absent from the final status, which ends on `Nothing left to do.`; no spec's
    broken reasons; `Markers: <n> tied to a test, 0 not tied.`; `wording.stale_comments` empty;
    each spec's `> Highest-Rule:` / `> Highest-Proof:` at least its largest number; the package's
    `rules` equals the number of rules the specs write at its commit and lists each.
    "No step needs a command Purlin does not give": every command the test runs after step 1
    that is not a plain git step a person takes anyway (commit, branch, switch, merge, pull,
    push of a feature branch, conflict edit) is one taken from the output before it (a
    `Run:`/`→ Run:` command, a push line, the key block) or named in the skill the table maps
    it to; the test extracts it from that text and fails when it is absent.

Next free ids: the new spec, `> Highest-Rule: 1`, `> Highest-Proof: 1`.

Break on purpose: run the test against the base `main` copy of `purlin_run.py` (no fresh
sections, no push line): it fails at step 7. Restore.

Tests that may fail only because another lane has not merged: the whole test, until every other
lane has merged. The lane runs it in its worktree, lists each assertion that fails and the
contract it waits on, and makes sure no failure is its own (a step written against a contract
wrongly). Integration runs it after the last merge.

## 4. Frozen files

None is expected to change. `dev/sign_project.py`'s `signing_project` builds evidence a release
run never wrote; no test signs through it (lane `signoff` writes its own packages). If the sweep
shows a frozen helper must change, integration's own commit
(`chore: the frozen helpers follow decision 105`) changes only:

- `dev/sign_project.py` and `dev/mcp_project.py`: an audit entry's `test_hash` taken from
  `Project.rule(...)['test_hash']`, as now, with no other change (they read the payload, so C6
  needs nothing).
- `dev/run_project.py`: `_project` writes no `project_name`; a test that reads the status head
  gets the folder's name. No change.

Anything else is reported to the owner, not edited.

## 5. Merge order and integration

### Merge order

`settings`, `drift`, `counting`, `release`, `signoff`, `run`, `words`, `docs`, `team`. Each by
fast-forward: integration rebases the lane branch on the merged line, reruns its files, then
fast-forwards `main` to it.

Why: `project.py` (settings) and `wording.py` (drift) are imported by the payload (counting),
which every other lane reads. `release.py` and `package.py` are read by the walk (signoff) and the
run (run). The words and the docs describe what the others built. The three-person test needs
all of them.

Expected red between merges, and only these: the tests each lane's section lists as waiting for
another lane, until that lane merges; skill and docs tests that quote a line their lane has not
yet rewritten; `dev/test_collaboration.py` until `team` merges last.

### Integration's job (alone, on the Mac, after every lane merged)

1. Merge in the order above; resolve each failure a lane reported in a file it does not own, to
   the contracts.
2. Frozen files, only as section 4 allows.
3. `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH`.
4. **Test comments to correct in this repository.** Run
   `python3 scripts/run/purlin_run.py --test --all` and read the lines C5 prints (about 198 at
   `d7b61f266`, more after the lanes' rewordings). Fan out by test file, one agent per group of
   files, each with its own scratch folder: for each comment, read the test against the proof as
   written now; where the test shows it, change the test so it states it (its name, its
   docstring or an assertion); where it does not, fix the test to show it; where the old wording
   is now another id, move the comment. Never reword a proof to match a test. Commit
   `test: <n> tests state the wording their proofs carry now` per group. Repeat until none is
   left.
5. `bash dev/run_tests.sh`: 0 failed. Never edit a number to make it pass.
6. `python3 dev/build_report.py`; commit `scripts/report/purlin-report.html` once if it changed.
   The dashboard's words do not change, so the docs screenshots are retaken only if
   `dev/capture_doc_screenshots.py` shows a difference, and the playwright look is skipped
   unless the built page differs from `d7b61f266`'s in more than its data.
7. `python3 scripts/run/purlin_run.py --test --all`: `Markers: <n> tied to a test, 0 not tied.`,
   no rule `failed`, `partial` or `no test`, no spec to repair, no test comment to correct, no
   warning, and the sentence `<n> rules. <n> pass their tests.` with only `rules to test on
   Windows` left. Then the same with `--commit`. Do not run `--release` and do not sign.
8. `dev/plans/d105-interfaces.md`: what was built where it differs from the contracts, every word
   a lane chose that section 6 does not give, the ids, the test counts, the time
   `dev/test_collaboration.py` took, the count of step 4, and section 6 under "Words chosen for
   the owner to read".
9. `dev/plans/handoff.md`: "Where the tree is" (decisions 104 and 105 built), "What is left" (the
   owner's sanity check with real AI sessions; the remote run on Windows, not run since decision
   100; the owner's first `purlin:test --remote` then `purlin:test --release` and `purlin:sign` on
   a release branch for 0.10.0), and section 6 under "Words for the owner to read".

## 6. Lines a person reads, chosen

In the shape of decisions 94 to 103. The owner reads these and says which to change.

| Where | What it says |
|---|---|
| The release run, its line (C2) | `Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules, all passed.`; `Tests on Windows run by a remote runner at 2026-10-01 11:58 UTC on 1cf829e.` |
| The release run, the push (C2, N6) | `Push it for the signer: git push -u origin release/0.1.0` |
| The release run, a remote result (C2, Q2) | `No release: the results on Windows were not taken at 1cf829e: sample_age RULE-6. Run purlin:test --remote on this branch, then purlin:test --release.` |
| The walk's refusals (C4) | `No sign-off: signed/0.1.0 is at e0deb2e, which this checkout does not hold. Pull, then run purlin:sign.`; `No sign-off: the evidence package for 0.1.0 was not written by a release run. Run purlin:test --release.`; `No sign-off: the release run tested 1cf829e, and release/0.1.0 has moved past it to 8de0b6e. Run purlin:test --release.`; `No sign-off: the evidence package for 0.1.0 holds results that are not the release run's: sample_age RULE-1, RULE-2; stability RULE-1. Run purlin:test --release.` |
| The overview (C4, N12) | `  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.`; `  2 stops: 1 hand check, 1 weak, 0 not audited.` |
| After a sign-off (C4, N2) | `Nothing left to do. Push the branch and the tag: git push origin release/0.1.0 signed/0.1.0`; `signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push origin release/0.1.0` |
| A test comment to correct (C5) | `tests/test_age.py:33 names sample_age PROOF-5, whose wording changed after the test was last changed in 495698f: it read "<old>" and now reads "<new>". Run purlin:build sample_age to make the test show it; the line clears once the test changes.`; the ending `Its old wording is now PROOF-7: move the comment there.`; under `Left to do:` `1 test comment to correct: purlin:build` |
| The strong cell, an earlier finding (C8) | `the last audit, before the rule or its tests changed, found it weak: <finding>` |
| Drift (C10) | `visit_window RULE-1 has no test for PROOF-3. Run purlin:build visit_window.`; `sample_age RULE-9 has no test. Run purlin:build sample_age.` |
| Setup and the upgrade (C7, C9) | the attribute's comment `# Purlin renders .purlin/tests.md again on every run, so a merge keeps this side's table.`; `added to .purlin/config.json: project_name "labconnect"`; the settings tool `"" is not accepted for project_name; it takes a name of 1 to 100 characters. Nothing was saved.` |
| Setup, a remote that is neither host (N12) | `origin is not on GitHub or Azure DevOps, so every test runs on this machine and purlin:test --remote is not set up.` |
| The glossary (words) | `**release run**: purlin:test --release on a release branch. It runs every test afresh at the release commit, commits the evidence and the evidence package, and names who ran it, on which machine, when and at which commit; the sign-off walk opens on that line.`; `**test comment to correct**: a comment above a test that names nothing a spec has, or names a proof whose wording changed after the test last changed. It clears once the comment or the test is corrected.` |
| The build skill (words) | `Before adding any marker, read each test already marked for this spec against its proof as written now. Where one no longer shows it, fix the test, or move the comment as purlin:spec's Renumbering says. Where it shows it but its comment is to correct, change the test so it states the new wording: its name, its docstring or an assertion.` |
| The spec skill (words) | `When the conflict is two different texts of the same id, show both and ask which survives. Two ids that say different things are both kept, and the one not yet on the default branch is renumbered.` |
| `RELEASE_NOTES.md` 0.10.0 (words) | `**The release run is what the signer signs.** purlin:test --release writes every result afresh at the release commit and records who ran it, where, when and at which commit; purlin:sign opens on that line and refuses a package any other run wrote.`; `**A test comment whose proof was reworded is caught.** The status and every test run list it as a test comment to correct until the test changes.`; `**The audit reads a rule again only when its own test changes.**`; `**.purlin/tests.md no longer conflicts**: setup writes a merge attribute for it.`; `**The package names the project** from pyproject.toml, package.json, a .csproj or the remote, and setup writes project_name.`; `**Sign-offs travel with the branch.** The first names pushing the branch and the tag; a later one waits until it holds the tagged commit.`; the format numbers of C12 |

## 7. Questions for the owner

**Q1. How does the table of results stop conflicting on a merge?**

Root: `.purlin/tests.md` is a summary table Purlin writes again from the evidence on every test
run, committed so a reader of the repository sees it. When two branches each ran tests, git sees
two edits of the same lines and stops the merge, though either side is thrown away by the next
run anyway. Decision 105 says a git attribute keeps one side. Git keeps one side only when each
clone also carries a one-line setting saying how; the attribute alone, committed, is not enough
in a clone that never had that setting.

- **(a) The attribute, plus the setting written by setup and by every test run, recommended.**
  Consequence: a clone that has run the tests once never conflicts on the table again. A fresh
  clone that merges before it has run anything conflicts once, as today, and the docs say take
  either side.
- **(b) An attribute that keeps both sides' lines.** Consequence: no clone ever stops on it and no
  setting is written, but after a merge the file holds both tables, one below the other, until
  the next run writes it again; pushed in that state, a reader sees two tables.
- **(c) Stop committing the table.** Consequence: never conflicts and nothing to set up, but the
  table is no longer in the repository for someone who did not run the tests; they read the
  dashboard or run the status instead.

The plan is written to (a): C7. Under (b) lane `settings` writes `merge=union` and no driver, and
`ensure_table_driver` is not built. Under (c) the table goes into the ignore list setup writes,
`evidence_format.md` loses "The table is tracked", and no attribute is written.

**Q2. Which results count for a release when some proofs can only be tested on another
operating system?**

Root: a proof tagged for Windows is tested by a remote runner, not on the developer's Mac. The
release run on the Mac writes fresh results for everything it can run, but it cannot run that
proof. Decision 105 says the package keeps nothing from earlier runs.

- **(a) A remote result counts only when taken over the release's own code, recommended.** The
  developer runs `purlin:test --remote` on the release branch first; the release then counts
  those results, names them on their own line in the walk, and refuses with one line naming the
  command when they were taken on other code. Consequence: every result in the package
  describes the released code; a release of a project with such proofs takes one more step and
  one remote run's wait.
- **(b) The release run starts the remote run itself and waits.** Consequence: one command, the
  same evidence as (a), but `purlin:test --release` pushes the branch and waits for the slowest
  runner, and cannot finish without the git host.
- **(c) A remote result counts whenever it still matches the code, as today.** Consequence: no
  extra step, but a Windows result may come from a feature branch's commit, which the package
  names; the "nothing from earlier runs" holds only for this machine's results.

The plan is written to (a): C2's `NO_RELEASE_REMOTE` and `RUN_REMOTE_LINE`, C3's flag. Under (b)
lane `run` makes `--release` push the branch, start the remote run and wait before writing the
package, and `NO_RELEASE_REMOTE` is not built. Under (c) a `ci` result's `release_run` is true
whenever it is current, and `NO_RELEASE_REMOTE` is not built.

**Q3. What clears the warning when a proof was reworded and its test already shows the new
words?**

Root: decision 105 lists a test comment as one to correct when its proof's wording changed after
the test last changed, and clears it once the test changes. Many rewordings change no value (a
clearer sentence, a renamed word), so the test was right all along. This repository alone holds
about 198 such tests today, from the rewordings of decisions 100 to 103.

- **(a) The test changes, recommended, as decision 105 says.** The developer edits the test so it
  states the new wording (its name, its docstring or an assertion). Consequence: every cleared
  line is a test someone read against the new words; integration reads and edits about 198
  tests in this repository before the round ends.
- **(b) Re-typing the comment above the test also clears it.** Consequence: one-line fixes, but a
  person can clear the line without reading the test, which is how N3's wrong test survived.
- **(c) Only rewordings after this release are checked.** Consequence: no backlog here or in a
  consumer's project, but tests that drifted before are never named.

The plan is written to (a): section 5 step 4. Under (b) C5's test span starts at the comment line
and a rewritten comment counts as a change (PROOF-84 inverts). Under (c) `stale_comments` skips a
test whose last change is older than the first commit that carries this release's `VERSION`.

## 8. Calls this plan makes

Not questions: each follows from decisions 104 and 105 or from the code, and the owner may
reverse any.

- **A test comment to correct does not fail a test run.** The tests did pass; the line prints
  and `Left to do` counts it, and a release refuses it, as it refuses every `to_correct`.
- **The payload's schema stays 13.** The lines ride in `warnings`, so the dashboard needs no
  change.
- **Times in the run's line are UTC with the date**, `2026-10-01 12:17 UTC`: a release is signed
  hours or days after it ran, often in another time zone.
- **A release at `passed` keeps its push line**, `git push origin passed/<version>`: nobody else
  signs, so nobody waits for the branch.
- **The package and its sign-offs stay on the release branch and its tag**; the docs say only a
  fix merges back to the default branch.
- **N12's vanished finding stays out of the counts** and shows as a reason on the rule, since the
  finding was on proofs that changed.
- **Every audit written before C6 stops answering once.** No entry is migrated; nothing waits on
  the audit.
- **`ssh` verification for a reader** (`git log --show-signature`) is taught in the docs with the
  commands; the key block `purlin:sign` prints is unchanged, since Purlin's own check needs no
  list of allowed signers.
- **The three-person test drives the scripts the skills name**, as the second check did, and
  plays `purlin:spec` and `purlin:build` by writing what their skills say; it calls no model.
