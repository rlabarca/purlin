# Feature: drift

> Description: What changed since your last pull, by role. Drift reads git's
>   own log of HEAD for the last action that brought changes in, and reports
>   what changed between where HEAD stood before it and HEAD: rules added,
>   changed and removed for the PM; code changed, rules with no test, anchors
>   behind and evidence out of date for the engineer; tests changed,
>   signatures gone stale and the size of the queue for QA. It reports facts
>   and judges nothing.
> Scope: scripts/mcp/purlin/drift.py
> Stack: python/stdlib, json, re, subprocess (list-only)

## Rules

- RULE-1: A `since` argument is accepted only as a commit count of digits or a `YYYY-MM-DD` date; any other value is refused with the error `rejected since` and a reason naming both accepted forms, and no subprocess starts
- RULE-2: With no `since`, the range runs from where HEAD stood before the newest entry of git's log of HEAD whose action is a pull, a merge, a finished rebase, a checkout or a reset, to HEAD; a pull or a rebase that git logged as several steps is measured from where HEAD stood before its first step
- RULE-3: When the newest such entry is the clone, or there is none, the range is the last 20 commits, or every commit when there are fewer
- RULE-4: `since` overrides the log: a count of N gives the last N commits, and a date gives every commit made on or after it
- RULE-5: The first line of every view names the action it measured from, how long ago it ran, the range as two 7-character shas and the number of commits, as in `Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).`
- RULE-6: The PM view compares each spec's map of rule id to rule text at the start of the range with the one at HEAD, and prints `<n> rules added: `, `<n> rules changed: ` and `<n> rules removed: ` lines naming each feature and its rule ids, or `No rule was added, changed or removed since <the action>.` when there is none
- RULE-7: The engineer view names, per spec whose scope reaches a changed file, how many of its files changed and the spec's own rules behind them, as `2 files changed under login's scope: RULE-1, RULE-2 are behind them.`; a scope entry ending in `/` reaches every file under that directory
- RULE-8: The engineer view names every changed file no spec's scope reaches, leaving out spec files, files under `.purlin/` and files that carry a proof marker, as `2 changed files are under no spec's scope: src/x.py, src/y.py.`
- RULE-9: The engineer view names every rule whose passed cell reads `no test`, as `2 rules have no test: login RULE-1, RULE-2.`
- RULE-10: The engineer view names every pinned anchor that is not current: one whose source has moved past its pin is `behind` with the source's 7-character sha, one naming a source and no pin is `unpinned`, one whose source cannot be read is `error` with the reason, and one still at its pin is not named at all
- RULE-11: A `> Source:` value is refused before any process starts when it begins with `-`, names an `ext::` or an `fd::` transport, or carries a NUL byte or a newline, and the refusal names which of those it was
- RULE-12: One remote listing per source per run: an anchor repository serving six anchors is reached once
- RULE-13: An anchor row names the anchor's own spec name, never the repository path and never the file inside it
- RULE-14: The engineer view names every feature that has evidence and whose evidence is out of date, as `1 feature is out of date: login.`
- RULE-15: The QA view names the changed files that carry a proof marker and the features those markers name, as `2 test files changed, covering login, export.`
- RULE-16: Under the gate `strong` or `signed` the QA view names every stale signature with what changed since it was made, as `1 signature is stale: login RULE-1 (rule text changed).`, and the size of the queue, as `Queue: 1 rule. 1 hand check, 0 signatures.`; under the gate `passed` it prints neither line
- RULE-17: Every view ends with `<n> spec files have changes that are not committed.` when a spec file under `specs/` differs from HEAD or is not tracked, and prints no such line when none does
- RULE-18: The report carries exactly `since` and `roles`; the roles are exactly `pm`, `eng` and `qa`, each view carrying its lines and the facts they were built from under fixed keys; a role argument narrows the answer to exactly `since`, `role` and `view`
- RULE-19: The report is serialized with no indentation and no space after a separator, because its only reader is a model paying by the token

## Proof

- PROOF-1 (RULE-1): Drift is asked for the changes since `--output=/tmp/x`; the answer is the error `rejected since`, its reason names both accepted forms, digits only and a `YYYY-MM-DD` date, and no command was run against the repository
- PROOF-2 (RULE-1): In a project of 3 commits, drift is asked for the changes since `2`; the answer measures 2 commits and runs git to find them
- PROOF-3 (RULE-2): A checkout pulls 2 new commits from a second repository, then commits once more on its own; the range runs from the commit it stood at before the pull to HEAD, 3 commits, and names the action `pull`
- PROOF-4 (RULE-2): A branch of 2 commits is merged into `main` with a merge commit; the range runs from `main` as it stood before the merge to HEAD, 3 commits, and names the action `merge`
- PROOF-5 (RULE-2): A branch of 1 commit is rebased onto a `main` that gained 2 commits; the range runs from the branch as it stood before the rebase to HEAD, naming the action `rebase`, and not from the last step of the rebase, which would be an empty range
- PROOF-6 (RULE-2): A checkout moves from `main` to a branch 2 commits ahead of it; the range runs from `main` to the branch, 2 commits, and names the action `checkout`
- PROOF-7 (RULE-2): After a pull, a reset moves HEAD back 2 commits; the newest action wins, the range runs from where HEAD stood before the reset, and it names the action `reset`
- PROOF-8 (RULE-3): A clone of a repository of 25 commits is measured over its last 20, from the 21st commit back, and names the action `clone`; a repository of 25 commits made in place measures the same 20 with no action named; one of 3 commits measures all 3, with no sha before them
- PROOF-9 (RULE-4): After a pull that brought in 1 commit, drift is asked for the changes since `3`; the range is the last 3 commits, not the pull's 1
- PROOF-10 (RULE-4): In a project whose first commit is dated 2026-01-01 and whose next two are dated 2026-03-01 and 2026-04-01, drift is asked for the changes since `2026-02-15`; the range is the last 2 commits, from the first commit to HEAD
- PROOF-11 (RULE-5): After a pull that brought in 2 commits, the first line of each of the three views reads `Since your last pull, <n> <unit> ago (<sha7>..<sha7>, 2 commits).`, the two shas are the start of the range and HEAD, and the three first lines are the same line
- PROOF-12 (RULE-6): A pull brings in a spec change that adds `RULE-3` to `login`, rewords `RULE-1` of `login`, removes `RULE-2` of `cart` and moves another spec to a new folder with its rules unchanged; the PM view reads exactly `1 rule added: login RULE-3.`, `1 rule changed: login RULE-1.` and `1 rule removed: cart RULE-2.` after its first line, and names the moved spec nowhere
- PROOF-13 (RULE-6): A pull brings in a change to a source file and no spec; the PM view reads, after its first line, exactly `No rule was added, changed or removed since your last pull.`
- PROOF-14 (RULE-7): The spec `login` of 2 rules covers the folder `src/auth/`, and a pull changes `src/auth/login.py` and `src/auth/token.py`; the engineer view reads `2 files changed under login's scope: RULE-1, RULE-2 are behind them.` and its facts name both files under `login`
- PROOF-15 (RULE-8): A pull changes `src/x.py` and `src/y.py`, which no spec covers, a spec file, a file under `.purlin/` and a test file carrying a proof marker; the engineer view reads `2 changed files are under no spec's scope: src/x.py, src/y.py.` and names none of the other three there
- PROOF-16 (RULE-9): The spec `login` has 2 rules and no test has run for either; the engineer view reads `2 rules have no test: login RULE-1, RULE-2.`, and once a passing run is written for both it prints no such line
- PROOF-17 (RULE-10): An anchor is pinned to its source's first commit, and the source then gains a second commit; the engineer view holds exactly one row for that anchor reading `behind`, with a 7-character sha that is the start of the new commit's sha, and the line `anchor external_anchor is behind its source (now <sha7>). Run: purlin:anchor sync external_anchor.`
- PROOF-18 (RULE-10): An anchor that carries rules of its own is pinned to its source's first commit, and the source then gains a second commit; exactly 1 row for that anchor reads `behind`
- PROOF-19 (RULE-10): An anchor that names a source and no pin reads `unpinned` with no remote sha; one whose source is a path where no repository exists reads `error`, and its reason names that path; one whose source has not moved past its pin gets no row at all
- PROOF-20 (RULE-11): The anchor sources `--upload-pack=/bin/echo`, `ext::sh -c id`, `fd::7`, a url carrying a NUL byte and a url carrying a newline are each refused, with the reasons `begins with "-"`, `names an ext:: transport`, `names an fd:: transport`, `contains a NUL byte` and `contains a newline`, and no process starts; `https://github.com/acme/p.git` is accepted with no reason
- PROOF-21 (RULE-12): The same pinned source is checked 3 times in one run; the remote is listed once
- PROOF-22 (RULE-13): The anchor `local_security`, copied from the file `constraints.md` in another repository, falls behind its source; the row reading `behind` names `local_security`, and names neither that repository's path nor `constraints.md`
- PROOF-23 (RULE-14): The spec `login` has a passing run written, and a pull then changes a file in its scope; the engineer view reads `1 feature is out of date: login.`. A feature with no run written at all is not named
- PROOF-24 (RULE-15): A pull changes one test file carrying markers for `login` and `export` and one carrying a marker for `login`; the QA view reads `2 test files changed, covering export, login.` and a changed file carrying no marker is not counted
- PROOF-25 (RULE-16): Under the gate `strong`, `login` RULE-1 carries a signature and its text is then reworded, and `login` RULE-2's only proof is a hand check; the QA view reads `1 signature is stale: login RULE-1 (rule text changed).` and `Queue: 1 rule. 1 hand check, 0 signatures.`. Under the gate `passed` the same project's QA view prints neither line
- PROOF-26 (RULE-17): With one spec edited and not committed, every view ends with `1 spec file has changes that are not committed.`; with a second spec added and not tracked, `2 spec files have changes that are not committed.`; with both committed, no view prints the line
- PROOF-27 (RULE-18): After a pull, the report carries exactly `since` and `roles`; the roles are exactly `eng`, `pm` and `qa`; the PM view carries exactly `lines`, `rules_added`, `rules_changed`, `rules_removed` and `specs_uncommitted`, the engineer view exactly `anchors_behind`, `code_changed`, `lines`, `out_of_date`, `rules_without_test`, `specs_uncommitted` and `unscoped`, and the QA view exactly `lines`, `not_audited`, `queue`, `signatures_stale`, `specs_uncommitted` and `tests_changed`. Asked for the `qa` role, the answer carries exactly `since`, `role` and `view`, its role reads `qa` and its view is the QA view of the whole report
- PROOF-28 (RULE-19): After one committed change, the report text holds no line break followed by two spaces and no colon followed by a space, reads back as a report carrying exactly `since` and `roles`, and is shorter than the same report laid out with an indent of 2
