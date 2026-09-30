> Criteria-Version: 10

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
| merge with conflicts | `commit (merge): ...`, the commit that finishes a merge once its conflicts are resolved | Where HEAD stood before that commit |
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
| `code_changed` | The changed files, `git diff --name-only`, matched to each spec's `> Scope:` expanded to the files git tracks; `src/api/` reaches every file under it | `4 files changed under login's scope: RULE-1, RULE-2, RULE-5 are behind them. Run purlin:test login.` |
| `unscoped` | The changed files no scope reaches, leaving out spec files, `.purlin/` and test files that carry a marker | `2 changed files are under no spec's scope: src/x.py, src/y.py. Add each to a spec's > Scope: line with purlin:spec.` |
| `rules_without_test` | Rules whose passed cell reads `no test` | `5 rules have no test: login RULE-1, RULE-2. Run purlin:build.` |
| `anchors_behind` | One `git ls-remote` per anchor source, below | `anchor proof_common: the pin 1a2b3c4 is behind its source, now 3c4d5e6. Run purlin:anchor sync proof_common.` |
| `out_of_date` | Features that have evidence and whose evidence is not current | `3 features are out of date: login, export, cart. Run purlin:test.` |

A file deleted in the range counts as changed. It joins `code_changed` under every spec whose
`> Scope:` entry covers it: a file entry equal to its path, a folder entry it lies under, or a
glob that matches it. A deleted file no entry covers joins `unscoped`, with that list's
exclusions.

### `qa`

| Key | From | Line |
|-----|------|------|
| `tests_changed` | The changed test files that carry a marker, and the features those markers name | `6 test files changed, covering export, login.` |
| `left` | The status's own items of `Left to do` of the kinds `to_test_by_hand` and `to_sign` | The lines below |

After those lines the view prints the two lines of `Left to do` that wait for a person, in the
words the status prints them:
`2 rules to test by hand: purlin:sign` and `5 rules to sign: purlin:sign`. Either is left out at
zero, and no other line of `Left to do` is printed. At the gate `passed` only a rule to test by
hand can wait for a person.

## Anchors behind

For every anchor carrying a `> Source:`, drift runs one cached `git ls-remote` against that
source and compares its `> Pinned:` sha. A source that begins with `-`, names an `ext::` or an
`fd::` transport, or carries a NUL byte or a newline is refused before any process starts. A
source that names no repository, a description in words or a file on disk, is reported without
one: no process is handed it. An anchor with no `> Source:` is a local anchor and is not checked.

| Condition | Line |
|-----------|------|
| The pin equals the source head | Nothing |
| The pin is behind | `anchor <name>: the pin <old7> is behind its source, now <new7>. Run purlin:anchor sync <name>.` |
| A `> Source:` with no `> Pinned:` | `anchor <name>: names a source and no pin. Run purlin:anchor sync <name>.` |
| The source cannot be read | `anchor <name>: the source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.` |
| The source names no repository: words, or a file on disk | `anchor <name>: its source, <source>, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec <name> to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.` |

Drift never advances a pin on its own. A change that came from somewhere else gets read before
it is adopted.

## Config field ownership

`.purlin/config.json`, and which command owns each field.

| Field | Written by | Read by | Default |
|-------|-----------|---------|---------|
| `version` | `purlin:init`, `purlin:init --update` | `purlin:init --update`, which compares it with the plugin's `VERSION` file to find an upgrade | From the plugin's `VERSION` file |
| `gate` | `purlin:init`, `purlin:init --gate` | `sync_status`, every skill that names a next step | `passed` |
| `mutation_engine` | `purlin:init`, which asks at the gates `strong` and `signed` whether to break the code on purpose | `scripts/run/purlin_run.py`, `sync_status` | `none` from init, and a yes writes `auto`; `none` where the key is absent. `none` turns mutation testing off, so no breaks run and `min_strength` is not applied |
| `min_strength` | `purlin:init` | `purlin:audit` | `null` while mutation testing is off; with it on, `null` under `passed`, 70 under `strong`, 80 under `signed` |
| `audit_parallel` | `purlin:init`, with no question | `scripts/run/purlin_run.py`, which makes that many AI audit calls at once | `4`; any value that is not a whole number from 1 to 16 is read as 4 with one warning |
| `tests` | `purlin:test`, at the first run, once you confirm the command it suggests | `scripts/run/purlin_run.py`, which runs each suite's own command and reads its report; the fingerprint, which reads markers only from the files a suite names | `[]` in the template; see `references/formats/marker_format.md` |
| `ci` | `purlin:init`, from the remote URL | `purlin:test --remote`, the workflow `purlin:init` writes | Detected: `github` or `azure`, and `none` with no remote or another host |

`purlin:init` is the only command that writes config unprompted. `purlin:test` writes `tests`
once you confirm it, and every other command reads. A field that is absent or set to `auto`
leaves the reader to its own fallback. This table must name every field `templates/config.json`
carries: a field written into new projects but absent here has no owner on this page.

## Project root ownership

No config field names the project root, because the root is what the reader of the config had to
find first. `PURLIN_PROJECT_ROOT` owns that question: it is read before anything else, and a
directory it names that exists wins over the `.purlin/` marker a climb from the working
directory would otherwise find. With the variable unset the climb answers, and with no marker
anywhere above the working directory the working directory itself is returned, which is a guess
and is reported as one. Set the variable in the project's `.claude/settings.json` under `env`
when the project root is not at the repository root; the tools also take a `project_root` argument
that overrides it for one call. A tool that finds no `.purlin/config.json` at the root it chose
says which directory it looked at and which mechanism chose it, and names the fix.
