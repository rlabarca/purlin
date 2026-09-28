> Criteria-Version: 8

# Drift criteria

What the `drift` tool measures, what each of the three role views reports and from which git
facts, and which config field belongs to which command. The tool reports facts and judges
nothing; the `purlin:drift` skill prints the lines and names the next step.

## Where the range starts

Drift is for a person who has just brought someone else's changes into their checkout. The range
runs from where HEAD stood before the last git action that brought changes in, to HEAD.

The tool reads git's own log of HEAD, `git reflog show HEAD`, and takes the newest entry whose
action is one of these:

| Action | The entry git writes | Where the range starts |
|--------|----------------------|------------------------|
| pull | `pull: ...` | Where HEAD stood before the pull |
| merge | `merge <branch>: ...` | Where HEAD stood before the merge |
| rebase | `rebase (finish): ...` | Where HEAD stood before the rebase's first step, `rebase (start)` |
| checkout | `checkout: moving from <a> to <b>` | The commit HEAD left |
| reset | `reset: moving to <ref>` | Where HEAD stood before the reset |
| clone | `clone: from <url>` | No commit before it: the last 20 commits |

A pull that rebases is logged as several steps, `pull --rebase (start)` to `pull --rebase
(finish)`, and is measured from before its first step, like a rebase. With no such entry at
all, the range is the last 20 commits. With fewer than 20 commits, it is every commit.

`--since <N>` measures the last N commits and `--since <YYYY-MM-DD>` every commit made on or after
that date. Either overrides the log. Any other value is refused before git runs.

The first line of every view names the range in words a person recognises:

```
Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).
```

## The three role views

Each view is a list of lines, the first naming the range, beside the facts each line was built
from. Every view ends with `<n> spec files have changes that are not committed.` when a spec file
under `specs/` differs from HEAD or is not tracked, read from `git status --porcelain -- specs/`.

### `pm`

Every spec file the range changed is read at both ends with `git show <sha>:<path>`, and its map
of rule id to rule text at the start is compared with the one at HEAD. A spec that moved folder
and kept its rules changed nothing.

| Key | Line |
|-----|------|
| `rules_added` | `3 rules added: login RULE-7, RULE-8; export RULE-2.` |
| `rules_changed` | `2 rules changed: login RULE-3, billing RULE-1.` |
| `rules_removed` | `1 rule removed: cart RULE-4.` |
| none of the three | `No rule was added, changed or removed since your last pull.` |

### `eng`

| Key | From | Line |
|-----|------|------|
| `code_changed` | The changed files, `git diff --name-only`, matched to each spec's `> Scope:` expanded to the files git tracks; `src/api/` reaches every file under it | `4 files changed under login's scope: RULE-1, RULE-2, RULE-5 are behind them.` |
| `unscoped` | The changed files no scope reaches, leaving out spec files, `.purlin/` and test files that carry a marker | `2 changed files are under no spec's scope: src/x.py, src/y.py.` |
| `rules_without_test` | Rules whose passed cell reads `no test` | `5 rules have no test: login RULE-1, RULE-2.` |
| `anchors_behind` | One `git ls-remote` per anchor source, below | `anchor proof_common is behind its source (now 3c4d5e6). Run: purlin:anchor sync proof_common.` |
| `out_of_date` | Features that have evidence and whose evidence is not current | `3 features are out of date: login, export, cart.` |

A file deleted in the range is not on disk and is in neither list.

### `qa`

| Key | From | Line |
|-----|------|------|
| `tests_changed` | The changed test files that carry a marker, and the features those markers name | `6 test files changed, covering export, login.` |
| `signatures_stale` | Signatures that do not bind the current rule, with which of the rule text, the proofs, the tests or the audit findings changed | `2 signatures are stale: login RULE-2 (audit findings changed), billing RULE-1 (rule text changed).` |
| `queue` | The queue, counted by what each rule needs | `Queue: 5 rules. 2 hand checks, 3 signatures.` |
| `not_audited` | Rules whose level is `strong` or `signed` that no audit has read, as `<feature>/<RULE-N>` | No line |

Under the gate `passed` there is no signature and no queue, so the `qa` view prints neither line
and reports only the tests that changed.

## Anchors behind

For every anchor carrying a `> Source:`, drift runs one cached `git ls-remote` against that
source and compares its `> Pinned:` sha. A source that begins with `-`, names an `ext::` or an
`fd::` transport, or carries a NUL byte or a newline is refused before any process starts.

| Condition | Line |
|-----------|------|
| The pin equals the source head | Nothing |
| The pin is behind | `anchor <name> is behind its source (now <sha7>). Run: purlin:anchor sync <name>.` |
| A `> Source:` with no `> Pinned:` | `anchor <name> names a source and no pin. Run: purlin:anchor sync <name>.` |
| The source cannot be read | `anchor <name>: its source could not be read (<reason>).` |

Drift never advances a pin on its own. A change that came from somewhere else gets read before
it is adopted.

## Config field ownership

`.purlin/config.json`, and which command owns each field.

| Field | Written by | Read by | Default |
|-------|-----------|---------|---------|
| `version` | `purlin:init` | The dashboard header; `purlin:sign` and `purlin:export` where the project has no `VERSION` file of its own | From the plugin's `VERSION` file |
| `gate` | `purlin:init`, `purlin:init --gate` | `sync_status`, `scripts/ci/gate_check.py`, every skill that names a next step | `passed` |
| `mutation_engine` | `purlin:init`, which asks `Measure test strength by breaking the code on purpose?` where an engine exists | `scripts/run/purlin_run.py`, `sync_status` | `none` from init, and a yes writes `auto`; `auto` where the key is absent. `none` turns mutation testing off, so no breaks run and `min_strength` is not applied |
| `min_strength` | `purlin:init` | `purlin:audit`, `scripts/ci/gate_check.py` | `null` while mutation testing is off; with it on, `null` under `passed`, 70 under `strong`, 80 under `signed` |
| `audit_parallel` | `purlin:init`, with no question | `scripts/run/purlin_run.py`, which makes that many AI audit calls at once | `4`; any value that is not a whole number from 1 to 16 is read as 4 with one warning |
| `tests` | `purlin:init`, one entry per framework it detects, or the command and report it asks for | `scripts/run/purlin_run.py`, which runs each suite's own command and reads its report; the fingerprint, which reads markers only from the files a suite names | `[]` in the template; see `references/formats/marker_format.md` |
| `ci` | `purlin:init`, from the remote URL | `purlin:test --remote`, the workflow `purlin:init` writes | Detected: `github` or `azure` |
| `trust` | `purlin:init`, which asks `Do you trust your own machine for the tests and the signing?`, or `Do you trust your own machine for the tests?` at the gate `passed` | `scripts/review/sign.py`, `scripts/run/workflow.py` | `local`; the only other value is `remote` |

`purlin:init` is the only command that writes config unprompted. Every other command reads. A
field that is absent or set to `auto` leaves the reader to its own fallback. This table must
name every field `templates/config.json` carries: a field written into new projects but absent
here has no owner on this page.

## Project root ownership

No config field names the project root, because the root is what the reader of the config had to
find first. `PURLIN_PROJECT_ROOT` owns that question: it is read before anything else, and a
directory it names that exists wins over the `.purlin/` marker a climb from the working
directory would otherwise find. With the variable unset the climb answers, and with no marker
anywhere above the working directory the working directory itself is returned, which is a guess
and is reported as one. Set the variable in the project's `.claude/settings.json` under `env`
when the workspace is not at the repository root; the tools also take a `project_root` argument
that overrides it for one call. A tool that finds no `.purlin/config.json` at the root it chose
says which directory it looked at and which mechanism chose it, and names the fix.
