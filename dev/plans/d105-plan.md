# Decisions 104 to 110: one plan

Written by the planning agent on 2026-10-01 against `main` at `1ded32dd1`. It builds, as one
round: decision 104 (a team's collaboration is a rule with a scripted proof), 105 (the second
check's answers), 106 (Purlin keeps the evidence and the sign-off and tracks no release), 107 (an
anchor rule with nothing to check passes and says so), 108 (no gate: two facts, the tests and the
sign-off), 109 (the scope review's answers, `scope-review.md`) and 110 (plain checks and one
targeted break per proof). Where they differ, the later
decision holds. Everything a decision cuts is a clean release (decision 44): deleted outright
with its rules, proofs, tests, docs lines and settings; `RELEASE_NOTES.md` alone keeps history;
only the upgrade from 0.9.5 keeps what it needs.

Twenty lanes run at once on this Mac, each in a worktree
`/Users/richlabarca/LocalCode/purlin-wt/d105-<lane>` on branch `lane/d105-<lane>` made from
`main` at the stubs commit of section 1, each owning files no other lane writes. One integration
agent merges them in the order of section 5. Section 2 is the contract; no lane chooses. Section 7
holds what the decisions leave open.

**The owner's answers, built to as written:**

- The table `.purlin/tests.md` goes entirely (106).
- A result counts for a sign-off only when taken on the same version of the code; no release
  branch is needed (106). Only the sign-off requires it; the status keeps counting a result while
  nothing its feature covers changed (the earlier plan's Q1, answered (a)).
- The ~198 test comments whose proof was reworded after the test last changed are read and fixed
  in this round (106).
- A skip whose reason starts `nothing to check:` counts as met for an anchor's rule only; on a
  project's own rule it reads `not run`, its reason kept (the earlier plan's Q2, answered (a)).
- Every cut, keep and change of decision 109, as section 2 gives them.
- A hand check always shows its last note, with the version it was signed at and how many
  commits have come since (this plan's earlier Q1, answered (b); decision 110).

## 1. Rules for every lane

`d103-plan.md` section 1 applies, with these names and changes.

- **Before the lanes: the shared stubs, one commit on `main`.** The agent that starts the lanes
  commits, alone and first, `chore: the shared interfaces of decisions 104 to 109, as stubs`, and
  every lane branches from it. It holds, each with the docstring section 2 gives:
  - `scripts/mcp/purlin/project.py`: `project_name` answering the folder's name (C7).
  - `scripts/mcp/purlin/wording.py`: C5's constants and a **working, unoptimized**
    `stale_comments` built to C5's definition, with its command line
    `python3 scripts/mcp/purlin/wording.py [--project-root DIR] [--file PATH ...]` printing each
    entry's `text`, one per line, then `<n> test comments to correct.` (`1 test comment to
    correct.`, `No test comment to correct.`), exit 0. Lane `drift` then makes it fast.
  - `scripts/mcp/purlin/facts.py`: C8's constants and `tests_fact` / `signoff_fact` answering
    `not met` / `not signed`.
  - in `scripts/export/package.py`: `project_version` (copied from `release.py`, which stays
    until lane `package` deletes it), `only_records_between` (False), `same_code` (False),
    `time_words`, `run_lines` (`[]`) and C3's constants.
  Nothing else changes in that commit, and the sweep is unchanged by it. Each stub's owner
  (section 3) replaces it.
- **Worktree and scratch.** `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/d105-<lane> -b lane/d105-<lane> main` (with `main` at
  the stubs commit); scratch `/private/tmp/d105-<lane>/`, no other agent's. A lane writes only the
  files section 3 gives it; where it calls another lane's work, it calls it as section 2 names it,
  and lists the tests that wait.
- **Environment.** `export PATH=/opt/homebrew/opt/dotnet@8/bin:/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH`.
  Its own test files whole with `python -m pytest <files> -q`, then `bash dev/run_tests.sh --fast`
  once at the end. Never the full sweep. One pytest process at a time, never `-n`.
- **Frozen:** `dev/mcp_project.py`, `dev/sign_project.py`, `dev/run_project.py`,
  `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`. `dev/skill_checks.py` is
  lane `checks`'s this round. A lane that needs a helper writes it in its own test file.
- **No generated file is staged:** `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/report-data.js`, `docs/images/*.png`, `dev/plans/deck/*.png`,
  and `.purlin/tests.md` while it exists.
- **Proofs.** One case in at most 60 words, a marked test of its own. New numbers in order from
  the next free ones section 3 gives (each spec's `> Highest-` lines at `1ded32dd1`), raising
  those lines; a number is never reused. A proof names what a person sees or a file holds.
- **A rule that survives in part is reworded**, its number kept. A rule moving to another spec is
  deleted in the old and written new in the new, with that spec's next numbers. A spec deleted
  whole takes its test file with it.
- **Test comments to correct (C14).** Before its last commit, each lane runs
  `python3 scripts/mcp/purlin/wording.py --file <each test file it owns>` and leaves none: those
  listed at the start and those its own rewordings make.
- **Clean release greps.** Each lane greps its own files for every word C13 retires and leaves
  none outside `RELEASE_NOTES.md`.
- **Formats.** A change to parsing or emission updates its `references/formats/` file in the same
  commit, with C12's number.
- **Instruction lengths:** each skill keeps today's ceiling in `dev/skill_checks.py` unless lane
  `checks` lowers it; agent 135.
- **Deliberate break.** Each lane breaks its most important change on purpose (named in its
  section), sees its test fail, restores with `git checkout -- <that file>`, never
  `git checkout -- specs/`. No real `claude`, no git host, no network: a host is a bare
  repository on disk.
- **A call no decision or contract makes:** build the rest, leave it, report it.
- **Commits** with `references/commit_conventions.md`'s prefixes, each ending:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01W6UPm3QPtMvgPNfN6W9vBE
  ```
  Push nothing. No `purlin:audit` or `purlin:sign` against this repository.
- **Do not edit `dev/plans/three-levels.md`.**
- **Report** in the last message and in `dev/plans/lanes/d105-<lane>.md` on the lane branch: each
  spec's Highest lines; tests before and after; rules and proofs deleted, moved or reworded, by
  number; C14's table for its files; calls left; words chosen beyond section 6; failures in files
  it does not own; tests waiting on another lane.

## 2. Contracts

Filled examples use `labconnect`, `dana.dev@labconnect.example` on `dana-laptop`, version
`0.1.0`, `HEAD` at `1cf829e`.

### C1. Running and committing, lanes `run` and `evidence`

The hand-off is `purlin:test --all --commit`, and `purlin:test --remote` for any proof tagged for
another system. `purlin:test --release` goes (C13).

1. **A section names the code it describes**: its `commit` is `HEAD` after the run's own work
   commit (`purlin: specs, tests and settings ...`) where `--commit` made one, else `HEAD` when
   the run started.
2. **A `local` section gains `email`**, `git config user.email` or `unknown`; kept, never
   compared.
3. **Retention keeps only the same code**: a section that saw the same thing over the same
   fingerprint on the same machine is left as it is only where
   `package.only_records_between(<its commit>, <the new commit>)` holds; otherwise `at`,
   `commit`, `dirty` and `email` are written new.
4. **`.purlin/tests.md` goes**: its writer and every mention. This repository's copy is deleted
   by integration.
5. Every `--test`, `--audit` and `--remote` run prints each test comment to correct (C5) after
   the markers lines; its exit code does not change.
6. **No mutation testing**: `--arm-timeout` stays (it bounds every suite); nothing else of the
   breaks remains.

### C2. The same version of the code, lane `package`

```python
def only_records_between(project_root, older, newer):
    """True when `older` is `newer`, or an ancestor of it from which every commit up
    to `newer` changes only paths under `.purlin/`."""

def same_code(project_root, section_commit, head=None):
    """only_records_between(section_commit, head or HEAD); False for an empty commit."""
```

A result counts for a sign-off when its section is current, not `dirty`, and `same_code` holds. A
`ci` result pulled home by `purlin:test --remote` in a commit that changes only `.purlin/` counts.

### C3. The package, format 8, lane `package`

`scripts/export/release.py` and `purlin:export` go. `package.build(project_root, version)` is
called by `purlin:sign` alone; `package.check_file(path)` by `purlin:sign --check FILE`.
`package.py` keeps no command line of its own. Schema `purlin-package/4`.

- `TOP_LEVEL = ('schema', 'met', 'rules', 'steps', 'audit', 'left', 'purlin_version',
  'project', 'version', 'tag', 'commit', 'runs', 'features', 'hand_checks', 'warnings',
  'fingerprint')`. Gone: `state`, `gate`, `mutation_engine`. `met`: no kind of `left` is in
  `summary.BLOCKING`. `tag` is `signed/<version>`.
- `runs`, one per group of counted sections by source, system, `email` (a `ci` section:
  `a remote runner`) and machine, local first then by system:
  ```json
  "runs": [{"by": "dana.dev@labconnect.example", "machine": "dana-laptop", "os": "linux",
            "source": "local", "at": "2026-10-01T12:17:13Z", "commit": "<40 hex>", "rules": 19}]
  ```
- Each `results` entry gains `"same_code": true|false` and `"nothing_to_check": [{"proof",
  "reason"}]` (C15). A rule's audit carries no `strength`. `hand_checks[].checked` is
  `"in the sign-offs"`.
- `project` is `project.project_name(project_root)`.
- **Who did what, from git (110):** each rule entry gains `authors`:
  ```json
  "authors": {"rule": {"written_by": "pat.product@labconnect.example", "commit": "<40 hex>"},
              "proofs": [{"id": "PROOF-1", "written_by": "...", "written_commit": "...",
                          "changed_by": "...", "changed_commit": "..."}],
              "tests": [{"file": "tests/test_age.py", "name": "test_age", "changed_by": "...",
                          "changed_commit": "..."}]}
  ```
  `written` is the oldest commit whose diff adds a line `- <id>` to that spec
  (`git log --reverse -G` on the spec, first match); `changed` is the commit `git blame` names for
  the id's line now; a test's `changed` is `wording.test_last_change` (C5). Emails are git's
  author emails. Nobody does anything extra.
- Moved here from `release.py`: `project_version` and its readers, `uncommitted_work`,
  `behind_host`, `behind_words`. New: `time_words(at)` (`2026-10-01 12:17 UTC`), `run_lines`,
  `off_code(package, project_root)` → `[(system words, source, [features])]`.

```python
RUN_LINE = 'Tests run by %s on %s at %s on %s: %s on %s.'
# by, machine, time_words(at), sha7, '19 rules' / '1 rule', 'Linux/Unix'
RUN_REMOTE_LINE = 'Tests run by a remote runner at %s on %s: %s on %s.'
```

### C4. The sign-off, lane `signoff`

`purlin:sign [--version <version>]`, `--show`, `--answers FILE`, `--check FILE`. Any project may
sign whenever it chooses (108). It reads the committed evidence at `HEAD`, builds the package,
walks, takes one signature.

**Refusals**, in order, one line each, nothing written, exit 1:

```python
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
NO_SIGNOFF_FAILING = ('No sign-off: %s at %s: %s. Run purlin:status to see what is left, '
                      'then purlin:sign.')
NO_SIGNOFF_BEHIND = ('No sign-off: %s holds %s that %s does not, as this checkout last '
                     'fetched it. Pull, then run purlin:sign.')
ALREADY_SIGNED = '%s has already signed %s over this package; nothing was written.'
```

`NO_SIGNOFF_ELSEWHERE`: `signed/<version>` exists and its commit is not an ancestor of `HEAD`.
`NO_SIGNOFF_MOVED`: it is, and a commit after it changes anything outside the package folder.
`NO_SIGNOFF_NOT_THIS_CODE` fills `HEAD`'s sha7, `sample_age, stability on Linux/Unix;
visit_window on Windows`, and `purlin:test --all --commit`, `purlin:test --remote` or both joined
` and `. `AT_PASSED` and every gate line go.

**The key** (N11): `--show` names none. The walk and `--answers` check it after the refusals,
before their first line, printing today's `NO_KEY` block.

**The walk** (109: stops only at hand checks):

```
Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.
Signing 0.1.0 at 1cf829e.
  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.
  The audit: 17 strong, 1 weak, 1 not audited.
The audit's findings: 1 weak. list / go on:
```

```python
OVERVIEW = 'Signing %s at %s.'
OVERVIEW_RULES = '  %s on %s: %s, %s.'   # '19 pass their tests' from steps.passed; '1 has a hand check' / '2 have a hand check' / 'no hand check'
OVERVIEW_AUDIT = '  The audit: %d strong, %d weak, %d not audited.'   # left out where no rule was audited
AUDIT_ASK = "The audit's findings: %s. list / go on: "               # '1 weak' / '2 weak'; asked only where a rule reads weak
AUDIT_LIST = '  %s %s   %s'                                           # feature, RULE-N, one finding per line
HAND_ASK = '%s %s   what did you see, in one line, or Enter for no note, or stop: '
```

`list` prints every weak rule with its findings, then asks `go on: `. Then one stop per hand check,
by feature then number: `Rule`, `Proof`, `Results` (each with `nothing to check` where C15
applies), and `What the audit found` where its audit reads weak or undecided (N1). An empty
answer records `no note`. `--answers` takes `{"audit": "list" | "go on", "stops": {"<feature>
RULE-N": {"answer": "note", "note": "..."} | {"answer": "continue"} | {"answer": "stop"}},
"sign": true}`. `STRONG_*`, the weak and not-audited stops and `walk` go.

**Signing:** the first sign-off of a version writes the package and the sign-off file in one
signed commit `sign(<version>): <email>` and tags `signed/<version>` on it, message
`Signed <version>.\n\nCommit: <the package's commit>\n`; a later one adds its file alone.

```python
SIGNED_PUSH = 'Push the branch and the tag: git push origin %s %s'
TAG_STAYS = '%s stays at %s; this sign-off is added after it. Push it: git push origin %s'
```

On a detached `HEAD` the branch is left out. `--check FILE` prints
`The package matches its fingerprint.` or `The package does not match its fingerprint: <why>.`
Moved in from `release.py`: `tag_exists`, `write_tag`, `current_branch`, `NO_TAG_GIT`.

**The sign-off file**, signature format 15: `shown` holds `overview`, `runs`, `hand_checks`
(each stop walked) and `audit_list_opened`; `notes` may read `no note`; `package_hash` is the
fingerprint of the package in the same commit. `one_by_one` and `in_list` go.

### C5. A test comment to correct, lane `drift`

`scripts/mcp/purlin/wording.py`:

```python
STALE = ('%s:%d names %s %s, whose wording changed after the test was last changed in %s: '
         'it read "%s" and now reads "%s". ')
STALE_BUILD = ('Run purlin:build %s to make the test show it; the line clears once the test '
               'changes.')
STALE_MOVE = 'Its old wording is now %s: move the comment there.'

def stale_comments(project_root, features, scanned=None):
    """One entry per test comment naming a proof whose wording, at the commit that last
    changed the test (the lines from the comment to the test's last line; a file run whole
    is the whole file; the newest commit git blame names for them), differs from its
    wording now. A test with an uncommitted line is never named. By file, then line.
    Each: {'file','line','feature','id','commit' (sha7),'old','new','now_under','text'}."""
```

Cost: one `git blame --porcelain` per marked test file and per spec, cached; one `git show` per
(commit, spec) compared; `sync_status` here at most 3 seconds slower than at `1ded32dd1`.
`wording.test_last_change(project_root, path, marker_line, end_line)` → `(sha, author email)` or
None is the one home of "the commit that last changed a test", read by C3's `authors` too.
Readers: the payload (`warnings`, counted under `to_correct`), the run (C1.5), drift, the
renumber helper (moves a comment to `now_under`).

### C6. The audit's per-test key, lane `counting`

`test_hash` is the sha256 of the sorted lines `<file> <test name> <sha256 of the test's
source>`, one per test tied to the rule's proofs, the source as `markers` bounds it with line ends
read as `\n`; a test of an `exit` suite, or one not found by its name, gives
`<file> <test name> <blob id>`. `test_hash_kind` `test`, `file`, `manual` or `none`. Earlier audit
entries stop answering once.

### C7. Settings and the project's name, lanes `settings`, `setup`, `upgrade`

- `.purlin/config.json` holds `version` and `tests` alone. `scripts/mcp/purlin/gate.py` is
  deleted. `config_engine.KNOWN_KEYS = ('version', 'tests')`; any other key in the file is named
  once: `.purlin/config.json carries %s, which this version does not read. Run purlin:init --update.`
  (keys joined `, `), where the upgrade has a step for it, else `Remove it from
  .purlin/config.json.`.
- The settings tool reads and writes `version` and `tests`; any other key:
  `%s is not a setting; .purlin/config.json holds version and tests. Nothing was saved.`
- `project.project_name(project_root)`: `[project]` then `[tool.poetry]` `name` in
  `pyproject.toml`; `name` in `package.json`; the first root `*.csproj` file's name without
  `.csproj`; the last segment of `git remote get-url origin` without `.git`; the folder's name.
  Read each time; never written.
- The git host is read from the remote each time (`workflow.host_of`).
- **Setup** asks one question, its existing `Commit the files setup wrote? [y/N]`, and writes
  the settings file, `specs/`, the evidence folder, the gitignore block and the dashboard copy;
  no runner file, no mutation config. `--gate` and `--mutation` go. Its last lines are the
  status's (C8).
- **The upgrade** is from 0.9.5 only: every step for a 0.10 build goes. On a 0.9.5 project it
  writes `version` and `tests` and removes every other key, printing today's
  `removed from .purlin/config.json: <keys>`. This repository's own `.purlin/config.json` is set
  to `version` and `tests` by hand (lane `settings`).

### C8. The two facts, lane `counting` (shown by `dashboard`)

New `scripts/mcp/purlin/facts.py`:

```python
TESTS_MET = 'met'
TESTS_NOT_MET = 'not met'
SIGNED_AT = 'signed %s at %s'                 # version, sha7 of the tagged commit
SIGNED_SINCE = 'signed %s, %d commits since'  # '1 commit since' for one
NOT_SIGNED = 'not signed'

def tests_fact(payload):
    """`met` when no kind of `left` is in summary.BLOCKING, else `not met`."""

def signoff_fact(project_root):
    """{'word', 'version', 'commit', 'since'} for the newest signed/* tag whose commit is
    HEAD's ancestor: SIGNED_AT where only_records_between(tag, HEAD), else SIGNED_SINCE with
    the count of commits tag..HEAD; NOT_SIGNED where none."""
```

**The status's opening lines**, replacing `Purlin status: <p>, plugin <v>, gate <g>`:

```
Purlin status: labconnect, plugin 0.10.0
Tests: not met
Sign-off: signed 0.1.0, 4 commits since
```

- After the table and `Left to do`, the last line: `Every rule passes its tests on the
  committed evidence. To sign it: purlin:sign` where tests are `met` and the sign-off is not
  `signed <v> at <sha>`; else none. `TO_RELEASE`, `TO_RELEASE_SIGNED`, `RELEASE`, `NOT_MET`
  and every gate line go.
- A new blocking kind `('to_commit', 'feature whose results are not committed', 'features whose
  results are not committed', 'purlin:test --commit')`.
- `no_proof` (`rule to write a proof for`) is listed for every project, not blocking.
- **A hand check** reads `checked at sign-off` in the strong cell (in place of `manual test`), with
  one reason per note of the newest sign-off that holds one, whatever code it was taken on:
  `HAND_NOTE = 'noted at the sign-off of %s by %s, %s: %s'` (version, signer, `at this commit`,
  `1 commit since` or `4 commits since`, the note); none before any sign-off.
- **N1:** a hand check whose audit reads weak or undecided reads `weak`, reasons the findings then
  `checked at sign-off`, `left` `to_strengthen`.
- **No strength:** the strong cell's `strength`, `STRENGTH`, `NOT_MEASURED` and every mutation
  reason go.
- **N12:** `EARLIER_WEAK = 'the last audit, before the rule or its tests changed, found it weak: %s'`
  on a `waiting` or `not audited` cell; `_holds_code` counts a file holding a byte.
- **Payload schema 14:** `gate` goes; `met` (replacing `finished`) and `signoff` (`signoff_fact`'s
  dict) are added; `tag` and `release_tag` go; `project` from `project.py`; the stale lines ride
  in `warnings`.

### C9. Remote runner set up on first need, lane `remote`

Setup writes no runner file. The status keeps naming proofs tagged for a system this machine is
not (`84 proofs need Windows; this machine is macOS. Run purlin:test --remote.`). The first
`purlin:test --remote` with no runner file for the host:

```python
RUNNER_WRITTEN = 'Purlin wrote %s, the runner for %s, to run the proofs tagged for %s:'
RUNNER_NEXT = 'Commit it and run: purlin:test --remote --commit-runner'
RUNNER_COMMITTED = 'Committed %s, the runner for %s.'
```

It writes the file, prints `RUNNER_WRITTEN`, the file, `RUNNER_NEXT`, exits 0 having run nothing.
`--commit-runner` commits it (`ci: the Purlin runner for <GitHub|Azure DevOps>`), prints
`RUNNER_COMMITTED`, then runs as `--remote` does. `remote.ensure_runner(project_root,
commit=False, out=None)` → `(path, written)` is what `purlin_run.py` calls. Both templates lose
the run on a pushed `signed/*` tag; so does this repository's `.github/workflows/purlin.yml`.
GitHub and Azure DevOps both stay.

### C10. Drift: one view, lane `drift`

`purlin:drift` takes no role. One `lines` list: the range line; rules added, changed and removed;
proofs added, changed (an id written twice left out, N10) and moved; each number written twice
with which line moves and the default branch's age; the renumbering offer; stale test comments
(C5, those whose proof changed in range or whose file did); anchors behind their source. No line
the status prints (no-test, out of date, `Left to do`, scope). Drift checks an anchor's source with
`git ls-remote` and never pulls (109). A `checkout` reflog entry whose old and new sha are the
same is not an action (N12). The helper writes a moved rule after the spec's last `- RULE-` line
and a moved proof after its last `- PROOF-` line. `references/drift_criteria.md`: Criteria-Version
13, one view. The MCP `drift` tool loses its `role` argument.

### C11. The three-person test, lane `team`

`specs/team/collaboration.md`:

```
# Feature: collaboration

> Description: Product, QA and dev work at once through git, in three clones of one repository,
>   and reach a signed version. A script plays the three people, forces collisions, merges in
>   both orders, and checks the run completes with no step stuck, no command failing
>   unexpectedly and nothing corrupted. The run with real AI sessions is the owner's sanity
>   check, not this proof.
> Scope: scripts/init/scaffold.py, scripts/run/purlin_run.py, scripts/run/evidence.py, scripts/export, scripts/review/sign.py, scripts/spec/renumber.py, scripts/mcp/purlin
> Stack: python/stdlib (subprocess), git, ssh-keygen, pytest
> Highest-Rule: 1
> Highest-Proof: 1

## Rules

- RULE-1: Three people working at once through git reach a signed version: `signed/<version>` exists, and the evidence package it holds describes the code under it and matches its fingerprint; no step needs a command that Purlin's output, skills and docs do not give; no command fails unexpectedly, and every warning raised along the way is resolved by the end; no spec holds a number twice or a merge-conflict line; every test comment is tied and names a proof with the wording it was marked against; each spec's highest-number lines cover its numbers; and the package lists every rule

## Proofs

- PROOF-1 (RULE-1): Pat, Quinn and Dana work in three clones of one bare repository; two pairs of branches take the same numbers, one merged QA first and one dev first; a test stays marked on a proof whose number moved; Dana runs and commits; Quinn signs `0.1.0`, then Pat; every check of RULE-1 holds
```

`dev/test_collaboration.py`, one test marked `# purlin: collaboration PROOF-1`: its sample
project written from text in the test, a `HOME` per person under `tmp_path`, keys made by
`ssh-keygen` inside it, `GIT_CONFIG_NOSYSTEM=1`, a bare repository as the host, no audit, no
model, under 120 seconds.

### C12. Format and schema numbers

| File | Now | After | Why |
|---|---|---|---|
| `package_format.md` | 7 | 8 | `met` for `state`; `gate`, `mutation_engine`, `strength` gone; `runs`; each result's `same_code` and `nothing_to_check`; each rule's `authors`; written and checked by `purlin:sign` |
| `signature_format.md` | 14 | 15 | `shown` holds `overview`, `runs`, `hand_checks`, `audit_list_opened`; `no note`; the package in the same commit |
| `evidence_format.md` | 7 | 8 | a section's `commit` is its code; `email`; retention over the same code; `test_hash` per test; `audit.mutation` gone; the table gone; a proof's `nothing to check` result and `reason`; an audit entry's `breaks` and `explanation`, `undecided` gone (C17) |
| `marker_format.md` | 3 | 4 | each report format's skip message read as the case's reason; `nothing to check:` |
| `anchor_format.md` | 11 | 12 | "for every X in the project, Y holds"; the `nothing to check:` skip; drift and the status check the source and do not pull; the table leaves the records |
| `spec_format.md` | 21 | 22 | `> Scope:` and every proof rule stated without a gate; `@manual` reads `checked at sign-off` |
| payload `schema_version` | 13 | 14 | C8 |
| `drift_criteria.md` | 12 | 13 | one view (C10) |

### C13. Deleted outright

- **The gate (108):** `gate.py`, the `gate` setting, `--gate`, setup's gate question, `GATE_*`,
  `NOT_A_GATE*`, `STRONG_RETIRED`, `AT_PASSED`, every gate-conditional display and line, the
  dashboard's `gate:` chip, `references/hard_gates.md` (renamed `references/evidence_and_signoff.md`,
  C16).
- **The release step (106):** `scripts/export/release.py`, `specs/export/release.md`,
  `dev/test_tag.py`, `--release` on `purlin:test`, `passed/<version>`, the package's `state`.
- **`.purlin/tests.md` (106).**
- **Mutation testing (109):** `scripts/run/mutation/**`, `specs/run/mutation.md`,
  `dev/test_mutation_adapters.py`, `dev/fixtures/mutation/**`, `mutation_engine`, the setup
  question, the mutmut config setup writes, every strength line and reason, `audit.mutation`.
- **`purlin:export` (109):** `skills/export/`, `specs/skills/skill_export.md`,
  `dev/test_skill_export.py`, `package.py`'s command line.
- **Settings `audit_parallel`, `ci`, `project_name`** (109); `AUDIT_PARALLEL = 4` lives in
  `ai_audit.py`.
- **Drift's roles** (`pm`, `eng`, `qa`), their views and every duplicated status line (109).
- **The sign-off walk's stops** for weak and unaudited rules and the strong list (109).
- **Setup's runner file** and the runner's run on a pushed `signed/*` tag (109).
- **The upgrade's steps for 0.10 builds** (109).
- **Dashboard extras (109):** the filter buttons, the live age and the reload (a static
  `Data from <time>` stays), the links to the git host, unfolding a rule under its row, the tabs.
- **About 220 self-check rules (109)**, as lane `checks` and each skill's lane say.
- **Docs pages** folded into eight (C16); `docs/spec-from-code.md`.
- **Empty folders** `scripts/ci`, `scripts/hooks`, `scripts/proof` (untracked; integration
  deletes them).
- **Decision 101's `does not apply`**: whatever is left of it.

### C14. The test comments to correct

At `1ded32dd1` C5's check names 198 in 30 files. Each lane clears those in its own files; files
this round deletes are skipped; no other file is left, so no separate `tests` lane is needed.

| Lane | Files (count) |
|---|---|
| `dashboard` | `test_purlin_report.py` (34), `test_purlin_report_board_layout.py` (4), `test_report_refresh.py` (4) |
| `run` | `test_run_script.py` (33) |
| `evidence` | `test_evidence_writer.py` (3), `test_fingerprint.py` (1), `test_evidence_reader.py` (3), `test_reports.py` (5) |
| `counting` | `test_states.py` (20) |
| `setup` | `test_init_scaffold.py` (16), `test_skill_init.py` (1) |
| `upgrade` | `test_init_update.py` (3) |
| `settings` | `test_specs_reader.py` (1) |
| `drift` | `test_drift.py` (11), `test_skill_drift.py` (1) |
| `package` | `test_export.py` (9) |
| `signoff` | `test_signatures.py` (5) |
| `skills` | `test_skill_spec.py` (1) |
| `remote` | `test_host.py` (11), `test_remote.py` (4), `test_consumer_ci.py` (3), `test_host_pathspec.py` (2) |
| `audit` | `test_ai_audit.py` (9), `test_ai_audit_tests_named.py` (2), `test_skill_audit.py` (2) |
| `checks` | `test_purlin_version.py` (3), `test_security.py` (3) |
| `anchors` | `test_upstream_notes.py` (1) |
| deleted | `test_mutation_adapters.py` (2), `test_skill_export.py` (1) |

For each: read the test against the proof as written now. Where it shows it, change the test so
it states it (its name, its docstring or an assertion); where it does not, fix the test; where
the old wording is now another id, move the comment. Never reword a proof to match a test. Each
lane lists every one as `<file>:<line> <feature> <PROOF-N> stated | fixed | moved`, with a line on
what changed for each `fixed`.

**Checked by:** (1) each lane: `wording.py --file` on its files prints `No test comment to
correct.` and its tests pass; (2) integration: `wording.py` over the repository prints the same;
(3) integration: no commit whose subject starts `test:` changes a proof line; (4) a reviewer
agent, not a fixer, reads every `fixed` diff against its proof and every tenth `stated`, listing
each it disagrees with, fixed before the sweep.

### C15. Nothing to check, lanes `evidence`, `counting`, `package`, `signoff`, `dashboard`, `skills`

- A test that finds nothing to check skips through its tool's own skip with a reason starting
  exactly `nothing to check:`. Any other skip reads as today.
- `reports.py`: each case's `reason`: `junit` the `<skipped>` child's `message`, else its text;
  `trx` a skipped result's `Output/ErrorInfo/Message`, else `Output/StdOut`'s last line; `gotest`
  the test's last `output` event before `skip`, its `<file>:<line>: ` cut; `exit` none.
- Evidence: a proof whose every tied case skipped so reads `"result": "nothing to check"` with
  `"reason"`. In an anchor's section it counts as passed; in any other spec's section it reads
  `not run`, its reason kept.
- The cell: the anchor rule reads `passed`, one reason per such proof
  `NOTHING_TO_CHECK = '%s: %s'`; the status prints after the table
  `NOTHING_LINE = '%s %s passes with nothing to check here: %s.'`.
- The package's `nothing_to_check`; the walk's `Results` line
  `  Linux/Unix: passed on dana-laptop; nothing to check for PROOF-3: this project has no screens`;
  the dashboard's rule page shows the reason.
- The quality guide teaches anchor authors "for every X in the project, Y holds" and the skip,
  per tool, naming tools that carry no message (Jest's `test.skip`).

### C16. The docs, eight pages, lane `docs`

`docs/how-purlin-works.md`, `getting-started.md`, `specs-and-anchors.md`,
`running-and-evidence.md`, `working-together.md`, `sign-off.md` (new: the sign-off with QA and
regulated use; from `review-and-signing.md`, `qa-guide.md`, `regulated-workflow.md`),
`upgrading.md` (renamed from `raising-the-gate-and-upgrading.md`, 0.9.5 only), `audit.md` (new,
110: what the audit checks, why, the research and the reasoning, with the sources of section 2's
C18), `dashboard.md`
(lane `dashboard`), and `index.md` as the list of them. Deleted: `review-and-signing.md`,
`qa-guide.md`, `regulated-workflow.md`, `team-workflow.md`, `spec-from-code.md`,
`raising-the-gate-and-upgrading.md`. `spec-from-code` is named on no core page; its skill teaches
itself. `references/hard_gates.md` becomes `references/evidence_and_signoff.md` (lane `skills`):
the one home of the two facts, which evidence counts for a sign-off, when a sign-off counts, what
`signed/<version>` means; `CLAUDE.md`'s table row follows.

### C18. The audit page's sources, lane `docs`

`docs/audit.md` cites, each by title and link, and says in one sentence what each shows:
Inozemtseva and Holmes, ICSE 2014, coverage and test suite effectiveness
(https://cs.uwaterloo.ca/news/professor-reid-holmes-and-graduate-student-laura-inozemtseva);
Just et al., FSE 2014, mutants as a valid substitute for real faults
(https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014-abstract.html);
Petrovic et al., Google, TSE 2021, mutation testing in practice at scale, on changed code
(https://arxiv.org/pdf/2102.11378); Meta's ACH, FSE 2025, mutation-guided test generation
(https://arxiv.org/pdf/2501.12862); LLMorpheus, model-written mutants
(https://arxiv.org/abs/2404.09952v2); https://arxiv.org/pdf/1807.05030;
https://arxiv.org/html/2606.19544v1; tautological tests
(https://specstory.com/learning/test-quality/tautological-test); https://arxiv.org/html/2602.00409v1.
The lane reads each source before writing its sentence and names in its report any it could not
read; it fetches nothing at test time, and no test reaches the network.

### C17. The audit, lanes `audit`, `plain`, `break` (110)

`purlin:audit` runs only when a person asks; nothing blocks on it. `purlin_run.py --audit` runs
the tests as now, then calls, in the new `scripts/review/audit_run.py` (lane `audit`):

```python
def run(project_root, features, selected, out=None):
    """For each rule read: the plain checks, the targeted breaks, then the model's
    reading as the explanation. Writes audit.rules entries; prints the findings and
    the share. Returns 0 always (1 only for a bad command line)."""
```

**Plain checks** (lane `plain`, new `scripts/review/plain_checks.py`, no model):

```python
CHECKS = ('no assertion', 'cannot fail', 'error swallowed', 'expected value computed by the code',
          'mocks what the rule is about', 'proof value missing')
def check(project_root, feature, proof, test):
    """[(check, sentence)] for one tied test, from its source and the proof's text."""
```

Each sentence names the test and what it lacks, as
`tests/test_age.py::test_age: no assertion.`,
`tests/test_age.py::test_age: the proof names 90 and the test does not hold it.`.
Python by `ast`; JavaScript, TypeScript, C#, Go and shell by the token reading `markers` already
does; a check a language cannot read is skipped and named once:
`<check> is not read in <language> tests.`

**The targeted break** (lane `break`, new `scripts/review/targeted_break.py`):

```python
def break_proof(project_root, feature, proof, test, scope_files, ask=None):
    """One break: the model is asked for the smallest change to one scoped file that
    would violate the proof; it is applied in a copy of the project; the proof's own
    test runs there; the copy is deleted. Returns {'proof', 'file', 'before', 'after',
    'result': 'caught' | 'survived' | 'not made', 'why'}."""
```

- **The user's code is never changed.** The copy is made with `git ls-files -co
  --exclude-standard -z` into `tempfile.mkdtemp(prefix='purlin-break-')`; the change is applied
  there alone, by an exact replacement of `before` with `after` that must match once; the test
  runs with that copy as its working directory, through the suite's own `run` command; the copy
  is removed in a `finally`. Every write goes through one function that refuses a path not under
  the copy. Before and after each break the module takes `git status --porcelain -z` and the
  hash of every file it lists in the project; a difference stops the audit with
  `The audit stopped: <path> changed while a break ran. Nothing in the project was written by the audit.`
  and exit 1, and the lane's test proves both lines never fire in a normal run.
- **The model's answer** is exactly:
  ```
  file: src/age.py
  before:
  <the exact lines>
  after:
  <the lines>
  ```
  or `no break: <why>` (`result` `not made`). Anything else is `not made` with
  `the answer named no change`.
- **Which proofs:** one break per proof whose test or covered code changed since the audit last
  read it: the audit entry keeps, per proof, `break_key` = sha256 of the test's source hash and
  the feature's `code` fingerprint part; a proof whose key is unchanged keeps its break.
- **No real model in a test:** every test of `break`, `plain` and `audit` runs with
  `dev/conftest.py`'s fake first on `PATH`, installs its own `dev/fake_claude.py` with the
  answers it needs, and asserts `shutil.which('claude')` resolves under its own `tmp_path` before
  the first call. The deliberate break of each lane runs only that way.

**The verdict:** a rule reads `weak` when any plain check fires on one of its tests or any break
`survived`; `strong` when none fires and every break was `caught` or `not made`; the model's
reading, asked once per rule as now, becomes the explanation under each finding and decides
nothing (`undecided` goes). Evidence format 8: each `audit.rules` entry holds `verdict`,
`findings` (the plain checks' sentences and each survived break as
`PROOF-1: the test still passes when src/age.py:12 reads "return 0"`), `breaks`
(`{PROOF-N: {file, before, after, result, break_key}}`), `explanation` (the model's sentences),
`model`, `criteria`, `at`, `commit`, and the three hashes.

**The share:** the audit's last line, and the status sentence's audit clause:
`AUDIT_SHARE = 'The audit found %d of %d rules strong (%d%%).'` over the rules that pass their
tests, a hand check counted where it has a tested proof. Nothing compares it with a target.

## 3. The lanes

| Lane | Owns |
|---|---|
| L1 `settings` | `scripts/mcp/config_engine.py`; `scripts/mcp/purlin/{gate,project,server,specs}.py`; `.purlin/config.json`; `templates/config.json`; `specs/mcp/{config_engine,server,specs,schema_spec_format}.md`; `dev/test_{config_engine,mcp_server,specs_reader,schema_spec_format}.py` |
| L2 `setup` | `scripts/init/scaffold.py`; `templates/{gitignore.purlin,evidence-readme.md}`; `specs/init/scaffold.md`; `dev/test_init_scaffold.py`; `dev/test_init_e2e_wiring.sh`; `skills/init/SKILL.md`; `specs/skills/skill_init.md`; `dev/test_skill_init.py` |
| L3 `upgrade` | `scripts/init/update.py`; `specs/init/update.md`; `dev/test_init_update.py`; `dev/fixtures/upgrade-0.9.5/**` |
| L4 `drift` | `scripts/mcp/purlin/{wording,drift}.py`; `scripts/spec/renumber.py`; `specs/mcp/drift.md`; `specs/spec/renumber.md`; `dev/test_{drift,renumber,wording}.py`; `references/drift_criteria.md`; `skills/drift/SKILL.md`; `specs/skills/skill_drift.md`; `dev/test_skill_drift.py` |
| L5 `counting` | `scripts/mcp/purlin/{facts,payload,states,status,summary,board}.py`; `specs/mcp/{states,summary}.md`; `dev/test_{states,summary,backing_tests,failing,purlin_output}.py`; `specs/instructions/purlin_output.md`; `skills/status/SKILL.md`; `specs/skills/skill_status.md`; `dev/test_skill_status.py` |
| L6 `package` | `scripts/export/{package,release}.py`; `specs/export/{package,release}.md`; `dev/test_export.py`; `dev/test_tag.py`; `references/formats/package_format.md`; `skills/export/`; `specs/skills/skill_export.md`; `dev/test_skill_export.py` |
| L7 `signoff` | `scripts/review/sign.py`; `scripts/mcp/purlin/signatures.py`; `specs/review/signatures.md`; `dev/test_signatures.py`; `references/formats/signature_format.md`; `skills/sign/SKILL.md`; `specs/skills/skill_sign.md`; `dev/test_skill_sign.py` |
| L8 `run` | `scripts/run/purlin_run.py`; `scripts/mcp/purlin/frameworks.py`; `references/supported_frameworks.md`; `specs/run/run_script.md`; `dev/test_run_script.py`; `skills/test/SKILL.md`; `specs/skills/skill_test.md`; `dev/test_skill_test.py`; `dev/fixtures/reports/**` |
| L9 `evidence` | `scripts/run/{evidence,reports}.py`; `scripts/mcp/purlin/{evidence,fingerprint,markers}.py`; `references/formats/{evidence_format,marker_format}.md`; `specs/run/{evidence_writer,reports}.md`; `specs/mcp/evidence.md`; `dev/test_{evidence_writer,evidence_reader,fingerprint,reports}.py` |
| L10 `audit` | new `scripts/review/audit_run.py`; `scripts/review/{ai_audit,marked_tests}.py`; `scripts/run/mutation/**`; `references/review_criteria.md`; `specs/review/ai_audit.md`; `specs/run/mutation.md`; `dev/test_{ai_audit,ai_audit_tests_named,mutation_adapters}.py`; `dev/fixtures/mutation/**`; `skills/audit/SKILL.md`; `specs/skills/skill_audit.md`; `dev/test_skill_audit.py` |
| L10b `plain` | new `scripts/review/plain_checks.py`; new `specs/review/plain_checks.md`; new `dev/test_plain_checks.py` |
| L10c `break` | new `scripts/review/targeted_break.py`; new `specs/review/targeted_break.md`; new `dev/test_targeted_break.py` |
| L11 `remote` | `scripts/run/{host,remote,workflow,ci}.py`; `templates/purlin.yml`; `templates/purlin.azure-pipelines.yml`; `.github/workflows/purlin.yml`; `specs/run/host.md`; `dev/test_{host,remote,host_pathspec,consumer_ci}.py`; `dev/fixtures/consumer-ci/**` |
| L12 `anchors` | `scripts/anchor/upstream.py`; `specs/anchor/upstream.md`; `dev/test_{upstream,upstream_notes}.py`; `dev/test_e2e_anchor_{authority,rules}.sh`; `dev/test_e2e_external_refs.sh`; `dev/setup-external-refs.sh`; `skills/anchor/SKILL.md`; `specs/skills/skill_anchor.md`; `dev/test_skill_anchor.py`; `references/formats/anchor_format.md` |
| L13 `dashboard` | `scripts/report/src/**`; `scripts/mcp/purlin/report_data.py`; `dev/build_report.py`; `dev/capture_doc_screenshots.py`; `dev/browser_launch.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report.py`; `dev/test_purlin_report_board_layout.py`; `dev/test_report_refresh.py`; `dev/fixtures/report/*.json`; `docs/dashboard.md` |
| L14 `skills` | `skills/{spec,build,spec-from-code}/SKILL.md`; `specs/skills/{skill_spec,skill_build,skill_spec_from_code}.md`; `dev/test_skill_{spec,build,spec_from_code}.py`; `references/{glossary,purlin_commands,hard_gates,commit_conventions,spec_quality_guide,writing_style}.md`; new `references/evidence_and_signoff.md`; `references/formats/spec_format.md`; `agents/purlin.md`; `README.md`; `RELEASE_NOTES.md`; `CLAUDE.md` |
| L15 `checks` | `dev/skill_checks.py`; `dev/test_vocabulary.py`; `specs/instructions/{purlin_agent,purlin_version}.md`; `dev/test_{purlin_agent,purlin_version}.py`; `specs/_anchors/security_no_dangerous_patterns.md`; `dev/test_security.py`; `dev/bump_version.sh`; `.github/workflows/version-check.yml` |
| L16 `docs` | `docs/*.md` but `dashboard.md`; `specs/instructions/purlin_docs.md`; `dev/test_purlin_docs.py` |
| L17 `deck` | `dev/plans/deck/**` but its `*.png` |
| L18 `team` | `specs/team/collaboration.md`; `dev/test_collaboration.py` |

No lane: `dev/run_tests.sh`, `dev/suites.py`, `dev/windows_skip.sh`, the frozen helpers,
`scripts/purlin_python.sh`, `.claude-plugin/*`, `VERSION`. A failure there is integration's.

**The skill specs' trim (109), every lane owning one:** each `specs/skills/skill_*.md` keeps at
most four rules: the commands the skill must name, the files and paths it must name, its line
ceiling, and that it holds no emoji; every other rule and proof goes with its test. Lane `checks`
gives `dev/skill_checks.py` the one helper they use:
`must_name(skill, commands=(), paths=())` → a list of problems, each `<skill> does not name <x>`.
Until `checks` merges, each lane's own test calls `skill_checks.wrapped` as now.

### L1 `settings`

C7's settings half: `gate.py` deleted, `KNOWN_KEYS`, the two refusals, `project.py` (filled from
the stub), the settings tool, this repository's `.purlin/config.json` to `version` and `tests`.

- `specs/mcp/config_engine.md` (R18 P44; next RULE-19, PROOF-45), scope adds `project.py`, drops
  `gate.py`: every gate, mutation and `audit_parallel` rule deleted. RULE-19, the project's name
  (PROOF-45 `[project] name`; PROOF-46 `package.json`; PROOF-47 `Intake.csproj`; PROOF-48 the
  origin `/srv/git/labconnect.git`; PROOF-49 the folder). RULE-20, a key not read is named once
  (PROOF-50 `gate`; PROOF-51 a key the upgrade does not know).
- `specs/mcp/server.md` (R32 P163; next RULE-33, PROOF-164): rules for `gate`, `mutation_engine`,
  `audit_parallel`, `ci` deleted; RULE-33, any other key refused (PROOF-164). The `drift` tool's
  `role` argument goes (PROOF-165, a call with `role` is refused as an unknown argument).
- `specs/mcp/specs.md`, `schema_spec_format.md`: only proofs naming a gate.

Break: let `gate` be written; PROOF-164 fails. Waits on: none.

### L2 `setup`

C7's setup half. The init skill: one question, no gate, no mutation, no runner, no `--update`
steps beyond 0.9.5. Skill spec trimmed.

- `specs/init/scaffold.md` (R78 P170; next RULE-79, PROOF-171): every rule of the gate, the
  mutation question and config, the runner file, `ci`, `audit_parallel`, `tests.md` and the
  release deleted. RULE-79, setup asks one question (PROOF-171, a run with no flags prints exactly
  one `[y/N]`). RULE-80, the settings file it writes holds `version` and `tests` (PROOF-172).
  RULE-81, it writes no runner file under a GitHub remote (PROOF-173). `UNKNOWN_HOST`'s lines go
  with the runner.

Break: write `gate`; PROOF-172 fails. Waits on: none.

### L3 `upgrade`

C7's upgrade half: 0.9.5 only.

- `specs/init/update.md` (R49 P161; next RULE-50, PROOF-162): every step for a 0.10 build
  (`strong` to `passed`, `min_strength`, the gate offer) deleted. RULE-50, a 0.9.5 project's
  settings end as `version` and `tests` (PROOF-162), the rest named in `removed from` (PROOF-163).

Break: keep `gate`; PROOF-162 fails. Waits on: none.

### L4 `drift`

C5 (the stub made fast), C10. Skill and spec trimmed.

- `specs/mcp/drift.md` (R34 P80; next RULE-35, PROOF-81), scope adds `wording.py`: every role
  rule and every line the status prints deleted. RULE-35, a comment is named when its proof
  changed after its test last changed (PROOF-81 named; PROOF-82 test edited after, not named;
  PROOF-83 uncommitted edit, not named; PROOF-84 only the comment line rewritten, named). RULE-36,
  an id written twice is no proof changed (PROOF-85). RULE-37, a checkout that moves nothing
  starts no range (PROOF-86). RULE-38, one view: a call names no role (PROOF-87). RULE-39, drift
  never pulls an anchor (PROOF-88).
- `specs/spec/renumber.md` (R9 P12; next RULE-10, PROOF-13): RULE-6 to C5's basis; RULE-10 a
  moved line goes after its kind's last (PROOF-13 rule; PROOF-14 proof).

Break: blame the comment line alone; PROOF-82 fails. Waits on: none.

### L5 `counting`

C6, C8 (with `facts.py`), C15's cell and status line. Status skill trimmed.

- `specs/mcp/states.md` (R109 P264; next RULE-110, PROOF-265): every gate-conditional rule, every
  strength rule and `manual test` reworded or deleted. RULE-110, the per-test hash (PROOF-265
  another test of the file edited, unchanged; PROOF-266 the rule's test edited, changed;
  PROOF-267 a shell test, `file`). RULE-111, N1 (PROOF-268). RULE-112, a test comment to correct
  is warned and counted (PROOF-269; PROOF-270 cleared). RULE-113, the project from its files
  (PROOF-271). RULE-114, `EARLIER_WEAK` (PROOF-272). RULE-39 reworded (PROOF-273). RULE-115, an
  anchor rule with nothing to check (PROOF-274 cell; PROOF-275 `NOTHING_LINE`). RULE-116, a hand
  check reads `checked at sign-off` (PROOF-276), with its last note and `4 commits since`
  (PROOF-277). RULE-117, the status sentence's audit clause is `AUDIT_SHARE` (PROOF-278).
- `specs/mcp/summary.md` (R19 P47; next RULE-20, PROOF-48): RULE-18 reworded to C8's last line
  (PROOF-44 rewritten; PROOF-45, PROOF-46 deleted). RULE-20, the opening lines (PROOF-48 `Tests:
  met`; PROOF-49 `Sign-off: signed 0.1.0 at <sha7>`; PROOF-50 `signed 0.1.0, 1 commit since`;
  PROOF-51 `not signed`). RULE-21, `to_commit` (PROOF-52).

Break: count `to_commit` outside `BLOCKING`; PROOF-52 fails. Waits on: PROOF-269/270 none (the
stub works); PROOF-271 (`settings`); PROOF-274 (`evidence`); PROOF-49/50 (`package`'s
`only_records_between`).

### L6 `package`

C2, C3; `release.py`, `release.md`, `test_tag.py`, `skills/export/`, `skill_export` deleted.

- `specs/export/package.md` (R31 P64; next RULE-32, PROOF-65): rules of `state`, `gate`,
  `mutation_engine`, `purlin:export`'s command line and `--release` deleted or reworded.
  RULE-32 `runs` (PROOF-65, PROOF-66 with a `ci` group). RULE-33 `same_code` (PROOF-67 true after
  a `.purlin/`-only commit; PROOF-68 false after a code commit). RULE-34 `project` (PROOF-69).
  RULE-35, the version from the project (PROOF-70 `VERSION`; PROOF-71 `pyproject.toml`).
  RULE-36 `nothing_to_check` (PROOF-72). RULE-37, `authors` from git (PROOF-73 the rule's
  writer; PROOF-74 a proof changed by another person; PROOF-75 a test's last change).

Break: let `same_code` pass a code commit; PROOF-68 fails. Waits on: PROOF-69 (`settings`),
PROOF-75 (`drift`'s `test_last_change`).

### L7 `signoff`

C4. The sign skill: any project, any time; `--show` first, no key; hand checks the only stops;
the audit list; the note optional; `--check`; push lines; within 185, its spec trimmed.

- `specs/review/signatures.md` (R111 P222; next RULE-112, PROOF-223): the gate rule, the
  weak / not-audited / strong stops and the strong list deleted. RULE-102 rewritten to C4's
  refusals, new proofs PROOF-223 (`NO_SIGNOFF_EVIDENCE`), PROOF-224 (`ELSEWHERE`), PROOF-225
  (`MOVED`), PROOF-226 (`NOT_THIS_CODE` naming `purlin:test --remote`). RULE-112 the run lines
  (PROOF-227). RULE-113 `--show` needs no key (PROOF-228). RULE-114 only hand checks stop
  (PROOF-229, a project with a weak and an unaudited rule and no hand check walks no stop).
  RULE-115 the audit list (PROOF-230). RULE-116 N1 at a hand check (PROOF-231). RULE-117 the
  overview's counts (PROOF-232). RULE-118 push lines (PROOF-233, PROOF-234). RULE-119 `no note`
  (PROOF-235). RULE-120 package and sign-off in one commit, tagged (PROOF-236); later, file alone
  (PROOF-237). RULE-121 moved from `release.md`: host ahead (PROOF-238), git refusing the tag
  (PROOF-239). RULE-122 `--check` (PROOF-240 matches; PROOF-241 not). RULE-123 `Results` names
  nothing to check (PROOF-242).

Break: drop the ancestor check behind `ELSEWHERE`; PROOF-224 fails. Waits on: real-package tests
(`package`); its own helper writes C3's shape until then.

### L8 `run`

C1 (1, 4, 5, 6), C9's call (`remote.ensure_runner`), `--release` and every mutation flag gone.
`_audit` is replaced by the call to `audit_run.run` (C17); its rules move to lane `audit`'s spec.
The test skill: the hand-off, `--remote` and its first-run runner; trimmed spec.

- `specs/run/run_script.md` (R94 P269; next RULE-95, PROOF-270): every `--release`, mutation,
  gate and table rule deleted. RULE-95, the section names the commit its work commit made
  (PROOF-270). RULE-96, every run prints the test comments to correct and exits as its tests do
  (PROOF-271). RULE-97, `--remote` with no runner file writes it and runs nothing (PROOF-272);
  `--commit-runner` commits it (PROOF-273).

Break: let `--remote` run with no runner file; PROOF-272 fails. Waits on: PROOF-272/273
(`remote`).

### L9 `evidence`

C1 (2, 3, 4), C15's reading and evidence, evidence format 8, marker format 4; `fingerprint.py`'s
records lose the table.

- `specs/run/evidence_writer.md` (R26 P89; next RULE-27, PROOF-90): the table's and mutation's
  rules deleted. RULE-27 `email` (PROOF-90). RULE-28 retention over the same code (PROOF-91 left
  on one commit; PROOF-92 moved on new code). RULE-29 a `nothing to check` proof (PROOF-93
  anchor, passed; PROOF-94 project spec, `not run` with reason).
- `specs/run/reports.md` (R31 P114; next RULE-32, PROOF-115): RULE-32 each format's skip reason
  (PROOF-115 `junit`; PROOF-116 `trx`; PROOF-117 `gotest`; PROOF-118 `exit` none).
- `specs/mcp/evidence.md` (R33 P85): proofs naming the table or `audit.mutation` reworded.

Break: keep a section on old code; PROOF-92 fails. Waits on: PROOF-91/92 (`package`).

### L10 `audit`

Mutation deleted whole (C13). `audit_run.py` (C17): the order, the verdict, the entry, the share;
`ai_audit.py` becomes the model's reading as the explanation and the break's request (its prompt
in `review_criteria.md`, rewritten: the model writes the break in C17's answer shape, and
explains findings; it decides nothing); `AUDIT_PARALLEL = 4`; the audit skill: run by hand, what
it checks, the share and a target such as 80% as the person's own, within 105; trimmed spec.

- `specs/review/ai_audit.md` (R31 P93; next RULE-32, PROOF-94), scope adds `audit_run.py`:
  strength and `undecided` rules deleted. RULE-32, four calls at once (PROOF-94). RULE-33, the
  verdict from checks and breaks alone (PROOF-95 a fired check, weak; PROOF-96 a survived break,
  weak; PROOF-97 all caught, strong, the model's answer `weak` changing nothing). RULE-34, the
  explanation is stored under the finding (PROOF-98). RULE-35, `AUDIT_SHARE` (PROOF-99). RULE-36,
  a proof whose break key is unchanged is not broken again (PROOF-100).

Break: let the model's answer set the verdict; PROOF-97 fails. Waits on: `plain`, `break` (its
tests call them through stubs it writes in its own test file until they merge).

### L10b `plain`

C17's plain checks, one rule each, in a new spec `specs/review/plain_checks.md`
(`> Scope: scripts/review/plain_checks.py`, ids from 1): RULE-1 to RULE-6, one per check, each
with a Python proof and a JavaScript proof where the token reading carries it; RULE-7, a check a
language cannot read is named once; RULE-8, a clean test fires nothing. No model is called.

Break: let `assert True` pass `cannot fail`; that proof fails. Waits on: none.

### L10c `break`

C17's targeted break, in a new spec `specs/review/targeted_break.md`
(`> Scope: scripts/review/targeted_break.py`, ids from 1): RULE-1 the change is made in a copy
(PROOF-1 the project's files hash the same after a break); RULE-2 a surviving test reads
`survived` with the change (PROOF-2); RULE-3 a caught one `caught` (PROOF-3); RULE-4 an answer
that matches nothing, or matches twice, is `not made` (PROOF-4, PROOF-5); RULE-5 a write outside
the copy is refused (PROOF-6); RULE-6 the project changing during a break stops the audit with
its line (PROOF-7, a test that edits the project from its fake's answer hook); RULE-7 the copy is
removed when the test command fails or times out (PROOF-8); RULE-8 no test reaches a real model
(PROOF-9, `claude` resolves under `tmp_path`).

Break: apply the change in the project instead of the copy; PROOF-1 fails. Waits on: none.

### L11 `remote`

C9: `ensure_runner`, the runner words, both templates without the `signed/*` run, this
repository's workflow file the same; `workflow.py`'s gate reasons go; the host read each time.

- `specs/run/host.md` (R45 P139; next RULE-46, PROOF-140): setup's runner rules and the tag run
  deleted. RULE-46, the first `--remote` writes the runner for the remote's host (PROOF-140
  GitHub; PROOF-141 Azure DevOps). RULE-47, no template runs on a `signed/*` push (PROOF-142).

Break: leave the tag trigger; PROOF-142 fails. Waits on: none.

### L12 `anchors`

`upstream.py`: the status and drift check with `git ls-remote` and never pull; only
`purlin:anchor sync` pulls. Anchor format 12 (C12, C15). The anchor skill points at the quality
guide's section; trimmed spec; no `does not apply`.

- `specs/anchor/upstream.md` (R35 P59; next RULE-36, PROOF-60): RULE-36, a check never changes
  the pinned file (PROOF-60).

Break: pull during the check; PROOF-60 fails. Waits on: none.

### L13 `dashboard`

Schema 14 fixtures. The two header boxes: `Tests` reading `met` / `not met`, `Sign-off` reading
C8's words, in place of `gate:` and `no signed tag`. Keeps the board, a rule's page with
`Back to the board`, the count boxes, the theme button, the per-system boxes, specs grouped by
folder with a count and no progress bar, the row badges, the hovers, a static `Data from <time>`.
Cuts C13's list and every strength part. A hand check reads `checked at sign-off`; a rule with
nothing to check shows its reason. `docs/dashboard.md` the same; its first paragraph no longer
names the table.

- `specs/dashboard/purlin_report.md` (R71 P222; next RULE-72, PROOF-223): the rules of every cut
  part deleted with proofs and tests. RULE-72 the two boxes (PROOF-223 `met`; PROOF-224
  `signed 0.1.0, 4 commits since`; PROOF-225 `not signed`). RULE-73 `Data from <time>` (PROOF-226).
  RULE-74 nothing to check (PROOF-227).

Break: show `gate:`; PROOF-223 fails. Waits on: none.

### L14 `skills`

The spec, build and spec-from-code skills (the build skill's check before a marker and clearing a
comment by changing the test; the spec skill's collision sentence; spec-from-code out of the core
path); the references (glossary, commands, conventions, quality guide with C15's section and
"a reworded proof needs its test changed", writing style without gate examples,
`evidence_and_signoff.md` new and `hard_gates.md` deleted); `spec_format.md` 22; the agent
(two facts, the hand-off, `purlin:sign` any time; within 135); README; RELEASE_NOTES (section
6); CLAUDE.md (the format table's rows for package and signature, "Releasing a new version" step
3 `Run purlin:test --all --commit and purlin:test --remote, then purlin:sign. The first sign-off
writes signed/<version>.`, the one-home table's `evidence_and_signoff.md` row). Skill specs
trimmed.

- `specs/skills/skill_build.md` (R19 P48; next RULE-20): the four kept rules carry the check
  before a marker (PROOF-49).

Break: drop the check from the build skill; PROOF-49 fails. Waits on: none.

### L15 `checks`

109's trim of Purlin's checks on itself: `purlin_agent` and `purlin_version` keep the rules that
protect what a user runs (no emoji in output, the version script and its CI check); the security
anchor keeps the languages `scripts/` holds (Python, shell) and drops PHP, TypeScript and C#
forms; `test_vocabulary.py` keeps only no emoji; `skill_checks.must_name`; ceilings kept.

Break: let an emoji through; the kept no-emoji proof fails. Waits on: none.

### L16 `docs`

C16's pages, `docs/audit.md` with C18's sources among them, in section 6's words; each page no longer names a gate, a release, the table,
mutation, export, drift roles or the cut dashboard parts. `specs/instructions/purlin_docs.md`
(R13 P18; next RULE-14, PROOF-19): kept to the eight pages and their links resolving (PROOF-19).

Break: none in code; greps of C13's words over `docs/` empty.

### L17 `deck`

`build_deck.py` rebuilt for the two facts: what Purlin is, spec and proof, run and commit, the
two facts, the sign-off, anchors with nothing to check, working together; `check_deck.py`'s width
check holds. The lane renders the pictures in its scratch folder to check them and commits only
the builder; integration renders and commits the pictures.

### L18 `team`

C11, every command as its skill runs it:

1. Pat: `pyproject.toml` naming `labconnect`, version `0.1.0`; setup `--yes`; push `main`.
2. Pat on `product/specs`: `sample_age`, `stability`; merged, pushed.
3. Dana on `dev/build`: code and marked tests; the suggested `tests` entry written through the
   settings tool; `--test --commit`; merged, pushed.
4. **Collision one, QA first:** both add `stability` RULE-3 and PROOF-4, Dana's test marked
   `stability PROOF-4`; Quinn merges first; Dana pulls, keeps both lines, reads the status and
   drift, renumbers (`--dry-run` then without), commits, `--test --commit`, merges.
5. **Collision two, dev first:** both add `sample_age` PROOF-4; Dana first; Quinn renumbers.
6. **A test left on a moved proof:** Dana, from Quinn's pre-renumber commit, marks a test
   `sample_age PROOF-4`; after the merge the status prints C5's line and `Tests: not met`;
   `renumber.py` moves it; the line is gone.
7. **The hand-off:** Dana on `main`: `--test --all --commit`; the status opens `Tests: met`,
   `Sign-off: not signed`; push.
8. Quinn: pull; `sign.py --show` with no key; `--answers` prints the key block, run as printed
   with Quinn's `HOME`; the hand check answered empty; signs; runs `SIGNED_PUSH`'s command.
9. **Second signer:** Pat, on `main` before Quinn signed, `git fetch`, `--answers`: refused with
   `NO_SIGNOFF_ELSEWHERE`; pulls, signs, runs `TAG_STAYS`'s command.
10. **End checks** in a fresh clone, each its own assertion: `signed/0.1.0` on the host;
    `sign.py --check` on the package at the tag matches; `git diff --name-only <package commit>
    signed/0.1.0` lists only `.purlin/evidence/package/`; both sign-offs count; every exit code
    as expected (step 9's refusal and the `not met` of steps 4 to 6 the only planned ones); every
    warning seen absent from the final status, which opens `Tests: met` and
    `Sign-off: signed 0.1.0 at <sha7>`; no spec broken; `0 not tied`; no stale comment; Highest
    lines cover numbers; the package lists every rule; the hand check's note `no note`. Every
    command after step 1 that is not a plain git step is taken from the output before it or from
    its skill, and the test fails where it is absent.

Break: run step 7 with base `main`'s `purlin_run.py`; step 8 is refused. Waits on: every lane.

## 4. Frozen files

None is expected to change. If one must, integration's commit
`chore: the frozen helpers follow decisions 108 and 109` may only remove a `gate`,
`mutation_engine`, `audit_parallel` or `ci` key a helper writes, a `strength` it passes, or a
docstring naming a gate or a release. Anything else goes to the owner.

## 5. Merge order and integration

### Merge order

`drift`, `evidence`, `package`, `counting`, `signoff`, `plain`, `break`, `audit`, `remote`, `run`, `anchors`,
`setup`, `upgrade`, `settings`, `dashboard`, `skills`, `checks`, `docs`, `deck`, `team`. Each by
fast-forward after a rebase on the merged line and a rerun of its files.

Why: `wording.py` and the evidence shape are read by the payload; `package.py` by the facts, the
walk and retention; `remote.ensure_runner` by the run; `settings` deletes `gate.py`, so it merges
after every lane that stops importing it; the words, checks, docs and deck describe the rest; the
three-person test needs everything.

**Expected red, and only:** each lane's listed waits; until `settings` merges, nothing (the stub
and `gate.py` both exist); from `package` until `signoff` and `run` merge, imports of the deleted
`release.py`; from `audit` until `run` and `setup` merge, their imports of the deleted `mutation`
package; skill tests quoting a line their lane has not
rewritten; `dev/test_collaboration.py` until last.

### Integration's job (alone, after every lane merged)

1. Merge in order; fix each failure reported in a file no lane owns, to the contracts.
2. Frozen files as section 4 allows. Delete `scripts/ci`, `scripts/hooks`, `scripts/proof`.
   `git rm .purlin/tests.md`.
3. `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH`.
4. C14's checks 2 to 4, the reviewer agent included.
5. `bash dev/run_tests.sh`: 0 failed. `dev/run_tests.sh` and `dev/suites.py` drop deleted files.
   Never edit a number to make it pass.
6. `python3 dev/build_report.py`; commit the built page once. Retake the two docs screenshots.
   Look at the dashboard with playwright, headless, dark and light, at 1500, 1280, 1024, 768 and
   390 pixels, on the three fixtures: the two boxes, `Back to the board`, `Data from <time>`, no
   cut part, no value wrapped inside itself, neutral text at least 7 to 1.
7. Render the deck's pictures with lane `deck`'s builder and `check_deck.py`; commit them.
8. Greps over `scripts/`, `skills/`, `agents/`, `references/`, `docs/`, `templates/`,
   `README.md`, `CLAUDE.md`, `dev/test_*`, empty outside `RELEASE_NOTES.md`: `gate`, `--release`,
   `passed/`, `tests.md`, `mutation`, `mutmut`, `stryker`, `min_strength`, `audit_parallel`,
   `purlin:export`, `does not apply`, `role`-named drift views, `purlin-package/3`.
9. `python3 scripts/run/purlin_run.py --test --all`: `0 not tied`, no rule `failed`, `partial`
   or `no test`, no spec to repair, no test comment to correct, no warning, only rules to test
   on Windows left; then `--commit`. Do not sign.
10. `dev/plans/d105-interfaces.md`: differences from the contracts, words chosen, ids, test counts
    before and after (rules, proofs, test lines, against `scope-review.md`'s figures), C14's
    final table and the reviewer's disagreements, the collaboration test's time, section 6 under
    "Words chosen for the owner to read".
11. `dev/plans/handoff.md`: decisions 104 to 109 built; left: the owner's sanity check with real
    AI sessions, the remote run on Windows (not run since decision 100, and now writing its
    runner on first need), the owner's first `purlin:sign` of 0.10.0.

## 6. Lines a person reads, chosen

| Where | What it says |
|---|---|
| The status's opening (C8) | `Purlin status: labconnect, plugin 0.10.0`; `Tests: met`; `Tests: not met`; `Sign-off: signed 0.1.0 at a1b2c3d`; `Sign-off: signed 0.1.0, 4 commits since`; `Sign-off: not signed` |
| The status's last line (C8) | `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`; `2 features whose results are not committed: purlin:test --commit` |
| A hand check (C8, C4) | `checked at sign-off`; `critical_screen RULE-2   what did you see, in one line, or Enter for no note, or stop: `; `no note` |
| The walk (C4) | `Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.`; `Tests run by a remote runner at 2026-10-01 11:58 UTC on 1cf829e: 4 rules on Windows.`; `Signing 0.1.0 at 1cf829e.`; `  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.`; `  The audit: 17 strong, 1 weak, 1 not audited.`; `The audit's findings: 1 weak. list / go on: ` |
| The walk's refusals (C4) | as C4 gives them, filled: `No sign-off: these results were not taken on this version of the code, 1cf829e: sample_age, stability on Linux/Unix; visit_window on Windows. Run purlin:test --all --commit and purlin:test --remote, then purlin:sign.` and the rest |
| After a sign-off (C4) | `Tagged signed/0.1.0 at e0deb2e.`; `Push the branch and the tag: git push origin main signed/0.1.0`; `signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push origin main` |
| A test comment to correct (C5) | `tests/test_age.py:33 names sample_age PROOF-5, whose wording changed after the test was last changed in 495698f: it read "<old>" and now reads "<new>". Run purlin:build sample_age to make the test show it; the line clears once the test changes.` |
| A hand check's note (C8) | `noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red` |
| The audit (C17) | `tests/test_age.py::test_age: no assertion.`; `tests/test_age.py::test_age: the proof names 90 and the test does not hold it.`; `PROOF-1: the test still passes when src/age.py:12 reads "return 0"`; `The audit found 42 of 50 rules strong (84%).`; `The audit stopped: src/age.py changed while a break ran. Nothing in the project was written by the audit.` |
| Nothing to check (C15) | `security_no_dangerous_patterns RULE-3 passes with nothing to check here: this project has no screens.` |
| The runner (C9) | `Purlin wrote .github/workflows/purlin.yml, the runner for GitHub, to run the proofs tagged for Windows:`; `Commit it and run: purlin:test --remote --commit-runner`; `Committed .github/workflows/purlin.yml, the runner for GitHub.` |
| Settings (C7) | `.purlin/config.json carries gate, mutation_engine, which this version does not read. Run purlin:init --update.`; `gate is not a setting; .purlin/config.json holds version and tests. Nothing was saved.` |
| Dashboard (L13) | the boxes `Tests` / `met` and `Sign-off` / `signed 0.1.0 at a1b2c3d`; `Back to the board`; `Data from 2026-10-01 12:17 UTC` |
| `RELEASE_NOTES.md` 0.10.0 | `**Two facts, no gate.** The status and the dashboard say whether the tests are met on the committed evidence, and whether this code is signed.`; `**The hand-off is run and commit**: purlin:test --all --commit, and purlin:test --remote for other systems.`; `**purlin:sign builds the evidence package and signs it**, at any time, in any project; it stops only at hand checks, whose note is optional, and refuses results not taken on this code.`; `**An anchor rule with nothing to check passes, and says so.**`; `**A test comment whose proof was reworded is caught** until the test changes.`; `**The audit checks tests in code and breaks the code once per changed proof**, in a copy of the project: plain checks for hollow tests, then one model-written break the proof's test must catch; it reports the share of rules it found strong. Run it by hand; nothing blocks on it.`; `**The evidence package records who wrote and last changed each rule, proof and test**, from git.`; `**Cut:** mutation testing, purlin:export, the gate, the release step, .purlin/tests.md, drift's role views, setup's questions but one, and most settings.`; the format numbers of C12 |

## 7. Questions for the owner

**Q1 (answered (b)).** A hand check always shows its last note, with its version and how many
commits since: C8's `HAND_NOTE`.

**Q2. What does the targeted break do with code that only one proof's test can reach?**

Root: decision 110 breaks the code once per changed proof and runs that proof's own test. A
test written for another proof of the same rule may also catch the break, which would show the
code is covered, though not by this proof's test.

- **(a) Only the proof's own test counts, recommended.** Consequence: each proof is shown to have
  a test that guards it; a rule whose second test does the work reads weak until the first is
  fixed or the proofs are merged.
- **(b) Any test of the same rule counts.** Consequence: fewer weak findings, but a proof can
  pass the audit with a test that does not show it.

The plan is written to (a): C17's "the proof's own test runs".

**Answered by the owner, 2026-10-01: Q2 (a), only the proof's own test counts when a break is caught; the call on authorship is reversed: the package names the first person to write a rule's or proof's wording, followed through renumbers.**

**Owner's wording and drafts, 2026-10-01, override C17 and section 6 where they differ.**
- The audit's first step is named **Heuristic spot tests** and its second **one planted bug per
  proof**; "targeted break" and "plain checks" appear in nothing a person reads.
- The six spot tests, their exact scope, what each does not flag, and their finding lines are as
  `references/review_criteria.md`, "Heuristic spot tests", gives them, word for word (the owner's
  official text, committed before the build). Lane `plain` implements them to it, one rule each;
  no lane changes that section's checks, scope or findings.
- `docs/audit.md` is `dev/plans/drafts/audit.md`, taken over by lane `docs`, which changes only
  what the build makes untrue and keeps every link to a paper.
- Integration runs the spot tests over this repository's own tests, reads every finding, fixes
  the test or narrows the check, and reports both counts.

## 8. Calls this plan makes

- `references/hard_gates.md` is renamed `references/evidence_and_signoff.md`: its name carried
  the cut word.
- `purlin:sign --release` becomes `--version`; `purlin:export --check` becomes
  `purlin:sign --check`.
- The first `--remote` writes the runner and runs nothing; `--commit-runner` commits and runs, so
  the agent can ask the person between the two.
- The first sign-off commits the package with its sign-off in one signed commit, tagged there.
- A test comment to correct does not fail a test run; it makes `Tests: not met`.
- `--arm-timeout` stays: it bounds every suite, not only mutation.
- gotest stays (decision 109 cut nothing of the report formats).
- The audit runs four calls at once, fixed.
- The break runs in a copy of the project, never in the checkout, and a check before and after
  each break stops the audit if the project changed.
- Who wrote a rule or proof is the oldest commit adding its line; renumbering moves that line, so
  the helper's commit becomes the writer of a moved id.
- Times read UTC with the date.
- Every audit entry written before C6 stops answering once.
