> Criteria-Version: 14

# Drift criteria

What the `drift` tool measures, what its one view reports and from which git facts, and which
setting belongs to which command. The tool reports facts and judges nothing; the `purlin:drift`
skill prints the lines and names the next step.

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
| checkout | `checkout: moving from <a> to <b>`, where HEAD moved to another commit | The commit HEAD left |
| reset | `reset: moving to <ref>` | Where HEAD stood before the reset |
| clone | `clone: from <url>` | No commit before it: the last 20 commits |

A pull that rebases is logged as several steps, `pull --rebase (start)` to `pull --rebase
(finish)`, and is measured from before its first step, like a rebase. A checkout that leaves
HEAD at the commit it stood at, as `git checkout -b topic` does, brought nothing in: drift passes
over it to the entry before. With no such entry at all, the range is the last 20 commits. With
fewer than 20 commits, it is every commit.

`--since <N>` measures the last N commits and `--since <YYYY-MM-DD>` every commit made on or after
that date. Either overrides the log. Any other value is refused before git runs.

The view's first line names the range in words a person recognises:

```
Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).
```

## The view

The report carries exactly two keys, `since` and `view`.

- `since` is the range: `action`, `commits`, `from`, `line`, `to` and `when`. `line` is the
  sentence that names the range.
- `view` carries exactly twelve keys. `lines` holds every sentence to print: first the one naming
  the range, then the rest in the order of the table below. The other eleven are the keys of the table, each
  holding the facts its lines were built from.

Lines the status already prints, such as the work left to do or the spec files not committed,
are not repeated here.

| Key | Line |
|-----|------|
| `merge_in_progress` | `MERGE_HEAD: merge in progress. The range above stops before it. Commit the merge, then run purlin:drift.` |
| `rules_added` | `3 rules added: login RULE-7, RULE-8; export RULE-2.` |
| `rules_changed` | `2 rules changed: login RULE-3, billing RULE-1.` |
| `rules_removed` | `1 rule removed: cart RULE-4.` |
| none of the three | `No rule was added, changed or removed since your last pull.` |
| `proofs_added` | `2 proofs added: sample_age PROOF-5, PROOF-6; stability PROOF-3.` |
| `proofs_changed` | `sample_age PROOF-1 (RULE-1): changed. "72 hours" became "96 hours".`, or `It was reworded.` where the change is too large to show |
| `proofs_moved` | `sample_age PROOF-4 moved to PROOF-6.` |
| `numbers_twice` | `sample_age PROOF-4: number written twice. The line on origin/main keeps it. Renumber the other to PROOF-7 and move its test comments with it. It reads "<its first 8 words>".` |
| `comments_changed` | `sample_age PROOF-4 (RULE-2): test comment to correct. "<old words>" became "<new words>" after tests/test_age.py:14 last changed (a1b2c3d). Run purlin:build sample_age.` |
| `default_branch` | `origin/main: last fetch. It was 3 days ago, and drift does not fetch. Run git fetch, then purlin:drift.`, printed only after a `numbers_twice` line |
| `anchors_behind` | `proof_common: anchor pin behind. The pin 1a2b3c4 is behind its source, now 3c4d5e6. Run purlin:anchor sync proof_common.` |

### A merge in progress

`merge_in_progress` is true where `git rev-parse -q --verify MERGE_HEAD` answers: a merge
stopped on conflicts and is not committed. Its line is then the view's second, right after the
one naming the range. The range reads git's log of HEAD, which holds the merge only once it is
committed.

### Rules and proofs

Every spec file the range changed is read at both ends with `git show <sha>:<path>`, and its map
of rule id to rule text at the start is compared with the one at HEAD. A spec is matched by its
name wherever its file lies, so a spec that moved folder and kept its rules changed nothing.

The proof lines follow the rule lines, and read the same two ends of each spec file. A proof
**moved** when its text at the range's start is, unchanged, under another id of the same spec at
HEAD, an id that did not hold that text at the start. An id whose text differs between the two
ends is **changed**, and one absent at the start and not a move is **added**. Texts are quoted
whole, without their tags. A proof removed is not listed. A number a spec writes twice at either
end is named as written twice, below, and never as added, changed or moved.

### Numbers written twice, and the default branch

Drift reads only this checkout: it never fetches, pulls or reaches the host. It reads every spec
of the checkout for a number written twice, compared with the spec on the default branch.

**The default branch** is the one `git symbolic-ref --quiet refs/remotes/origin/HEAD` names, else
the first of `origin/main` and `origin/master` that exists, else none. **Its age** is now less
the time of the newest entry of that ref's own log,
`git reflog show -1 --date=unix refs/remotes/<ref>`, else less the time `FETCH_HEAD` was
written, else unknown. It reads
`under a minute`, then whole minutes, hours or days, rounded down. Unknown reads
`origin/main: last fetch. None is on record, and drift does not fetch. Run git fetch, then purlin:drift.`

**A number written twice.** The line whose text equals that id's text on the default branch
keeps the number; the other moves to the next free number, one above the spec's
`> Highest-Rule:` or `> Highest-Proof:` and above every number of that kind the spec holds.
Where one spec writes several numbers twice, each takes the next number after the one before.
`purlin:spec` makes the edit, and moves the test comments, when you say yes to its plan.

**A proof that follows a moved rule.** An entry for a rule holds `follows`, each proof naming
that rule that is not on the default branch's copy, with its line. For each, drift prints one
line after the entry's own: `login: PROOF-3 will name RULE-3.`

| Case | Line |
|------|------|
| One line is on the default branch | `sample_age PROOF-4: number written twice. The line on origin/main keeps it. Renumber the other to PROOF-7 and move its test comments with it. It reads "<its first 8 words>".` |
| Neither line is on the default branch | `sample_age PROOF-7: number written twice. Neither line is on origin/main, and the one that reaches it first keeps the number. Renumber the other to PROOF-8 and move its test comments with it.` |
| The default branch writes it twice too | `sample_age PROOF-4: number written twice. origin/main itself writes it twice. Renumber the second to PROOF-7 and move its test comments with it. It reads "<its first 8 words>".` |
| No default branch | `sample_age PROOF-4: number written twice. This checkout has no copy of a default branch to say which line keeps it. Renumber the one not yet merged to PROOF-7 and move its test comments with it.` |

### Test comments to correct

A test comment is named where its proof's wording, at the commit that last changed the test,
differs from its wording now, and where the range changed that proof or that test's file. A
test is last changed at the newest commit `git blame` names for the lines below its comment down
to the test's last line, or for any line of its file when the file is run whole. A test with a
line not yet committed is never named, and the line clears once the test itself changes. The
check is `scripts/mcp/purlin/wording.py`'s, the same the status and every test run make.

The line ends `Move the comment to PROOF-6, which holds the old wording.` in place of the build,
where a proof of the same spec now holds the old wording exactly.

## Anchors behind

For every anchor carrying a `> Source:`, drift runs one cached `git ls-remote` against that
source and compares its `> Pinned:` sha. It reads the source's head and pulls nothing: the
anchor's file, its pin and this checkout's git objects stay as they were. A source that begins with `-`, names an `ext::` or an
`fd::` transport, or carries a NUL byte or a newline is refused before any process starts. A
source that names no repository, a description in words or a file on disk, is reported without
one: no process is handed it. An anchor with no `> Source:` is a local anchor and is not checked.

| Condition | Line |
|-----------|------|
| The pin equals the source head | Nothing |
| The pin is behind | `<name>: anchor pin behind. The pin <old7> is behind its source, now <new7>. Run purlin:anchor sync <name>.` |
| A `> Source:` with no `> Pinned:` | `<name>: anchor with no pin. It names a source and no pin. Run purlin:anchor sync <name>.` |
| The source cannot be read | `<name>: anchor source not read. Its source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.` |
| The source names no repository: words, or a file on disk | `<name>: anchor source not a spec. <source> is not a spec in Purlin's format kept in a git repository. Run purlin:spec <name> to take out its > Source: and > Pinned: lines.` |

Drift never advances a pin on its own; only `purlin:anchor sync` pulls. A change that came from
somewhere else gets read before it is adopted.

## Config field ownership

`.purlin/config.json` holds two settings, and which command owns each.

| Field | Written by | Read by | Default |
|-------|-----------|---------|---------|
| `version` | `purlin:init`, `purlin:init --update` | `purlin:init --update`, which compares it with the plugin's `VERSION` file to find an upgrade | From the plugin's `VERSION` file |
| `tests` | `purlin:test`, at the first run, once you answer yes to its question, or with `--write-tests` | `scripts/run/purlin_run.py`, which runs each suite's own command and reads its report; the fingerprint, which reads markers only from the files a suite names | `[]` in the template; see `references/formats/marker_format.md` |

`purlin:init` is the only command that writes the settings unprompted. `purlin:test` writes
`tests` once you confirm it, and every other command reads. The project's name is read from the
project's own files each time; it is not a setting. Any
other key is not read, and the status names it with its fix. This table must name every field
`templates/config.json` carries: a field written into new projects but absent here has no owner
on this page.

## Project root ownership

No setting names the project root, because the root is what the reader of the settings had to
find first. Every Purlin tool call names it: `project_root` is the top folder of the git
checkout you are working in, and a call that names none is refused with that fix, so one
checkout's state is never read as another's. A script run on the command line takes
`--project-root`, and without it reads the working directory. A tool that finds no
`.purlin/config.json` at the root it was given says which folder it looked at and names the fix.
Purlin's own folder is refused as a project root; `references/purlin_commands.md`, "The tools
and their scripts", gives both lines.
