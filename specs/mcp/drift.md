# Feature: drift

> Description: What changed since your last pull, by role. Drift reads git's
>   own log of HEAD for the last action that brought changes in, and reports
>   what changed between where HEAD stood before it and HEAD: rules added,
>   changed and removed for the PM; code changed, rules with no test, anchors
>   behind and evidence out of date for the engineer; tests changed, and the
>   rules waiting for someone to test by hand or to sign, for QA. It reports
>   facts and judges nothing.
> Scope: scripts/mcp/purlin/drift.py
> Stack: python/stdlib, json, re, subprocess (list-only)

## Rules

- RULE-1: A `since` argument is accepted only as a commit count of digits or a `YYYY-MM-DD` date; any other value is refused with the error `rejected since` and a reason naming both accepted forms, and no subprocess starts
- RULE-2: With no `since`, the range runs from where HEAD stood before the newest entry of git's log of HEAD whose action is a pull, a merge, a merge committed after its conflicts were resolved, a finished rebase, a checkout or a reset, to HEAD; a pull or a rebase that git logged as several steps is measured from where HEAD stood before its first step
- RULE-3: When the newest such entry is the clone, or there is none, the range is the last 20 commits, or every commit when there are fewer
- RULE-4: `since` overrides the log: a count of N gives the last N commits, and a date gives every commit made on or after it
- RULE-5: When the range starts where HEAD stood before an action, the first line of every view is the same line, naming the action, how long ago it ran, the range as two 7-character shas and the number of commits, as in `Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).`
- RULE-6: The PM view compares, for each spec file the range changed, the spec's rule ids and texts at the start of the range with those at HEAD, matching a spec by its name wherever its file lies, and prints `<n> rules added: `, `<n> rules changed: ` and `<n> rules removed: ` lines naming each feature and its rule ids, or, when there is none, `No rule was added, changed or removed` followed by the range, as in `No rule was added, changed or removed since your last pull.`
- RULE-7: The engineer view names, per spec whose scope reaches a changed file, how many of its files changed and the spec's own rules behind them, as `2 files changed under login's scope: RULE-1, RULE-2 are behind them.`; a scope entry ending in `/` reaches every file under that directory, and a file deleted in the range counts under every spec whose scope entry names it, holds it in its folder or matches it as a glob
- RULE-8: The engineer view names every changed file no spec's scope reaches, a file deleted in the range included, leaving out files under `specs/`, files under `.purlin/` and files that carry a proof marker, as `2 changed files are under no spec's scope: src/x.py, src/y.py.`
- RULE-9: The engineer view names every rule whose passed cell reads `no test`, as `2 rules have no test: login RULE-1, RULE-2.`
- RULE-10: The engineer view names every pinned anchor that is not current: one whose source has moved past its pin is `behind` with the source's 7-character sha, one naming a source and no pin is `unpinned`, one whose source cannot be read is `error` with the reason, and one still at its pin is not named at all
- RULE-11: A `> Source:` value is refused before any process starts when it begins with `-`, names an `ext::` or an `fd::` transport, or carries a NUL byte or a newline, and the refusal names which of those it was
- RULE-12: One remote listing per source per run: an anchor repository serving six anchors is reached once
- RULE-13: An anchor's row and its line name the anchor by its own spec name, never by the repository path and never by the file inside it
- RULE-14: The engineer view names every feature that has evidence and whose evidence is out of date, as `1 feature is out of date: login.`
- RULE-15: The QA view counts the changed files that carry a proof marker and names the features those markers name, in alphabetical order, as `2 test files changed, covering export, login.`
- RULE-17: Every view ends with `<n> spec files have changes that are not committed.` when a spec file under `specs/` differs from HEAD or is not tracked, and prints no such line when none does
- RULE-18: The report carries exactly `since` and `roles`, and the roles are exactly `pm`, `eng` and `qa`
- RULE-19: The report is serialized with no indentation and no space after a separator, because its only reader is a model paying by the token
- RULE-20: The engineer view reports an anchor whose `> Source:` names no repository, words or a file on disk, as `error` with the line that names `purlin:spec`, and no process is handed the source
- RULE-21: When `.purlin/config.json` exists and cannot be read, drift's answer is the sentence `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.` alone, in place of the report, and it reads nothing else
- RULE-22: The QA view prints the `to test by hand` and `to sign` lines of `Left to do` in the words the status prints them, as `1 rule to test by hand: purlin:sign`, and no other line of `Left to do`
- RULE-23: Each view carries its lines and the facts they were built from under fixed keys
- RULE-24: The QA view's `left` holds the status's own items of `Left to do` of the kinds `to_test_by_hand` and `to_sign`, the items its lines of `Left to do` are built from
- RULE-25: A role argument narrows the answer to exactly `since`, `role` and `view`

## Proof

- PROOF-1 (RULE-1): Drift is asked for the changes since `--output=/tmp/x`; the answer is the error `rejected since`, its reason names both accepted forms, `digits only` and a `YYYY-MM-DD` date, and no process was started
- PROOF-2 (RULE-1): In a project of 3 commits, drift is asked for the changes since `2`; the answer measures 2 commits, and git was run to find them
- PROOF-3 (RULE-2): A checkout pulls 2 new commits from a second repository, then commits once more on its own; the range runs from the commit it stood at before the pull to HEAD, 3 commits, and names the action `pull`
- PROOF-4 (RULE-2): A branch of 2 commits is merged into `main` with a merge commit; the range runs from `main` as it stood before the merge to HEAD, 3 commits, and names the action `merge`
- PROOF-29 (RULE-2): A branch of 2 commits and `main` change the same line of one file, the merge stops on the conflict, and the file is resolved and the merge committed by hand; the range runs from `main` as it stood before the merge to HEAD, 3 commits, and names the action `merge`
- PROOF-35 (RULE-2): After a merge committed by hand once its conflict was resolved, a plain commit is made on `main`; the range still runs from `main` as it stood before the merge to HEAD, now 4 commits, and names the action `merge`
- PROOF-5 (RULE-2): A branch of 1 commit is rebased onto a `main` that gained 2 commits; the range runs from where the branch stood before the rebase to HEAD, 3 commits, and names the action `rebase`
- PROOF-6 (RULE-2): A checkout moves from `main` to a branch 2 commits ahead of it; the range runs from `main` to the branch, 2 commits, and names the action `checkout`
- PROOF-7 (RULE-2): A pull brings in 2 commits, then a reset moves HEAD back 2 commits; the range names the action `reset`, the newer of the two, and runs from where HEAD stood before the reset to HEAD
- PROOF-8 (RULE-3): A clone is made of a repository of 25 commits; the range is its last 20 commits, from the 21st commit back to HEAD, and names the action `clone`
- PROOF-36 (RULE-3): A repository of 25 commits is made in place, with no pull, merge, rebase, checkout, clone or reset; the range is its last 20 commits, from the 21st commit back, and names no action
- PROOF-37 (RULE-3): A repository of 3 commits is made in place; the range is all 3, with no commit before them, and the first line reads `The last 3 commits (up to <sha7>, 3 commits). Git's log of HEAD names no pull, merge, rebase, checkout, clone or reset.`
- PROOF-9 (RULE-4): After a pull that brought in 1 commit, drift is asked for the changes since `3`; the range is the last 3 commits, not the pull's 1, and the first line begins `The last 3 commits (`
- PROOF-10 (RULE-4): In a project whose three commits are dated 2026-01-01, 2026-03-01 and 2026-04-01, drift is asked for the changes since `2026-02-15`; the range is the last 2 commits, from the first commit to HEAD, and the first line begins `Since 2026-02-15 (`
- PROOF-11 (RULE-5): After a pull that brought in 2 commits, the first line of each of the three views is the same line, `Since your last pull, <n> <unit> ago (<sha7>..<sha7>, 2 commits).`, the shas being the start of the range and HEAD, and the report's range carries that line too
- PROOF-30 (RULE-5): After a merge committed by hand once its conflict was resolved, the first line of each of the three views is the same line, `Since your last merge, <n> <unit> ago (<sha7>..<sha7>, 3 commits).`, the shas being the start of the range and HEAD
- PROOF-12 (RULE-6): One pull brings in spec changes that add `RULE-3` to `login`, reword `RULE-1` of `login` and remove `RULE-2` of `cart`; after its first line the PM view reads exactly `1 rule added: login RULE-3.`, `1 rule changed: login RULE-1.` and `1 rule removed: cart RULE-2.`
- PROOF-38 (RULE-6): A pull brings in one change, a spec moved to another folder with its rules unchanged; after its first line the PM view reads exactly `No rule was added, changed or removed since your last pull.`
- PROOF-13 (RULE-6): A pull brings in a change to a source file and to no spec; after its first line the PM view reads exactly `No rule was added, changed or removed since your last pull.`
- PROOF-14 (RULE-7): The spec `login`, of 2 rules, covers the folder `src/auth/`, and a pull changes `src/auth/login.py` and `src/auth/token.py`; the engineer view reads `2 files changed under login's scope: RULE-1, RULE-2 are behind them.` and its facts name both files under `login`
- PROOF-51 (RULE-7): The spec `login`, of 2 rules, names the files `src/auth/login.py` and `src/auth/old.py`, and a pull deletes `src/auth/old.py`; the engineer view reads `1 file changed under login's scope: RULE-1, RULE-2 are behind it.` and its facts name `src/auth/old.py` under `login`
- PROOF-52 (RULE-7): The spec `login`, of 2 rules, covers the folder `src/auth/`, and a pull deletes `src/auth/token.py`; the engineer view reads `1 file changed under login's scope: RULE-1, RULE-2 are behind it.` and its facts name `src/auth/token.py` under `login`
- PROOF-53 (RULE-7): The spec `login`, of 2 rules, covers the glob `src/**/*.py`, and a pull deletes `src/auth/token.py`; the engineer view reads `1 file changed under login's scope: RULE-1, RULE-2 are behind it.` and its facts name `src/auth/token.py` under `login`
- PROOF-15 (RULE-8): A pull changes `src/x.py` and `src/y.py`, which no spec covers, a spec file, a file under `.purlin/` and a test file carrying a proof marker; the engineer view reads `2 changed files are under no spec's scope: src/x.py, src/y.py.`, naming none of the other three there
- PROOF-54 (RULE-8): A pull deletes `src/gone.py` and adds `src/x.py`, which no spec covers; the engineer view reads `2 changed files are under no spec's scope: src/gone.py, src/x.py.` and names no spec whose scope changed
- PROOF-59 (RULE-8): A pull changes `src/auth/login.py`, which the spec `login` covers, and the file is then removed with `git rm` and not committed; the engineer view prints no line of changed files under no spec's scope
- PROOF-16 (RULE-9): The spec `login` has 2 rules and no test has run for either; after a pull, the engineer view reads `2 rules have no test: login RULE-1, RULE-2.`
- PROOF-39 (RULE-9): The spec `login` has 2 rules and a passing run is written for both; after a pull, the engineer view prints no line saying a rule has no test
- PROOF-17 (RULE-10): An anchor is pinned to its source's first commit, and the source gains a second; the engineer view holds one row for it, reading `behind` with the first 7 characters of the new commit's sha, and the line `anchor external_anchor is behind its source (now <sha7>). Run: purlin:anchor sync external_anchor.`
- PROOF-18 (RULE-10): An anchor that carries 2 rules of its own is pinned to its source's first commit, and the source then gains a second commit; exactly 1 row for that anchor reads `behind`
- PROOF-19 (RULE-10): The anchor `policy` names the source `https://github.com/acme/p.git` and no pin; its row reads `unpinned` with no sha, the engineer view reads `anchor policy names a source and no pin. Run: purlin:anchor sync policy.`, and no process is handed that source
- PROOF-40 (RULE-10): The anchor `policy` is pinned to a source path where no repository exists; its row reads `error` with no sha and a reason naming that path, and the engineer view reads `anchor policy: its source could not be read (<the reason>).`
- PROOF-41 (RULE-10): An anchor is pinned to its source's newest commit; the source is read once, and the engineer view holds no row and no line for the anchor
- PROOF-55 (RULE-10): An anchor is pinned to `https://dev.azure.com/acme/p/_git/policies`, which cannot be reached; the source is asked, its row reads `error` with no sha, and the engineer view reads `anchor policy: its source could not be read (<the reason>).`
- PROOF-20 (RULE-11): The anchor `policy` is pinned to the source `--upload-pack=/bin/echo`; its row reads `error` with the reason `begins with "-"`, the engineer view reads `anchor policy: its source could not be read (begins with "-").`, and no process is handed that source
- PROOF-42 (RULE-11): An anchor pinned to the source `ext::sh -c id` reads `error` with the reason `names an ext:: transport`, and no process is handed that source
- PROOF-43 (RULE-11): An anchor pinned to the source `fd::7` reads `error` with the reason `names an fd:: transport`, and no process is handed that source
- PROOF-44 (RULE-11): An anchor pinned to a source carrying a NUL byte, `/srv/anchors<NUL>.git`, reads `error` with the reason `contains a NUL byte`, and no process is handed that source
- PROOF-45 (RULE-11): The check of an anchor's source, given `/srv/anchors.git`, a newline and `--upload-pack=x`, refuses it with the reason `contains a newline`, and no process starts; a spec's `> Source:` line cannot hold a newline, so this is the check alone
- PROOF-46 (RULE-11): An anchor names the source `https://github.com/acme/ext-rules.git`, which holds `ext` and a `-` but neither begins with `-` nor names a transport, and no pin; it is not refused, and its row reads `unpinned` with no reason
- PROOF-21 (RULE-12): Three anchors are pinned to the first commit of one source repository, which then gains a commit; the engineer view holds 3 rows reading `behind`, and the source is listed once
- PROOF-22 (RULE-13): The anchor `local_security`, copied from the file `constraints.md` in another repository, falls behind its source; its row is named `local_security`, and its one line reads `anchor local_security is behind its source (now <sha7>). Run: purlin:anchor sync local_security.`
- PROOF-23 (RULE-14): The spec `login` has a passing run written and `cart` has none, and a pull then changes a file in each one's scope; the engineer view reads `1 feature is out of date: login.` and does not name `cart`
- PROOF-24 (RULE-15): A pull changes one test file carrying markers for `login` and `export`, one carrying a marker for `login` and one carrying no marker; after its first line the QA view reads exactly `2 test files changed, covering export, login.`
- PROOF-31 (RULE-22): Under the gate `passed`, the spec `login` has one rule with an ordinary proof and one whose only proof is checked by hand, and nothing has been run or signed; after its first line the QA view reads exactly `1 rule to test by hand: purlin:sign`
- PROOF-32 (RULE-22): The status leaves `3 rules to audit` and `2 rules to sign`; after its first line the QA view reads exactly `2 rules to sign: purlin:sign`
- PROOF-33 (RULE-22): The status leaves only `3 rules to audit`; the QA view prints nothing after its first line
- PROOF-26 (RULE-17): One spec is edited and not committed; every view ends with `1 spec file has changes that are not committed.`
- PROOF-47 (RULE-17): One spec is edited and a second spec is added and not tracked; every view ends with `2 spec files have changes that are not committed.`
- PROOF-48 (RULE-17): An edited spec and a new one are both committed; no view prints a line about spec files not committed, and each view's count of them reads 0
- PROOF-27 (RULE-18): After a pull, the report carries exactly `since` and `roles`; `since` carries exactly `action`, `commits`, `from`, `line`, `to` and `when`, and `roles` exactly `eng`, `pm` and `qa`
- PROOF-49 (RULE-23): After a pull, the PM view carries exactly `lines`, `rules_added`, `rules_changed`, `rules_removed` and `specs_uncommitted`; the engineer view exactly `anchors_behind`, `code_changed`, `lines`, `out_of_date`, `rules_without_test`, `specs_uncommitted` and `unscoped`; the QA view exactly `left`, `lines`, `specs_uncommitted` and `tests_changed`
- PROOF-50 (RULE-25): After a pull, drift is asked for the `qa` role; the answer carries exactly `since`, `role` and `view`, its role reads `qa`, and its `since` and `view` are those of the whole report
- PROOF-34 (RULE-24): The status leaves `3 rules to audit` and `2 rules to sign`; the QA view's `left` holds exactly the one item `{"kind": "to_sign", "count": 2, "text": "2 rules to sign", "command": "purlin:sign"}`
- PROOF-28 (RULE-19): After one committed change, the report text is indented nowhere, puts no space after the `:` and `,` that separate its keys and values, reads back as a report carrying exactly `since` and `roles`, and is shorter than the same report laid out with an indent of 2
- PROOF-56 (RULE-20): The anchor `refunds` is pinned to the source `policy.txt`, a text file in the project; its row reads `error`, its line begins `anchor refunds: its source, policy.txt, is not a spec in Purlin's format kept in a git repository` and names `purlin:spec refunds`, and no process is handed `policy.txt`
- PROOF-57 (RULE-20): The anchor `refunds` is pinned to the source `the finance team's refund policy`, a description in words; its row reads `error`, its line begins `anchor refunds: its source, the finance team's refund policy, is not a spec in Purlin's format` and names `purlin:spec refunds`, and no process is handed that source
- PROOF-58 (RULE-21): A project's `.purlin/config.json` holds a comma after its last setting; drift's whole answer is `.purlin/config.json cannot be read: <the JSON reader's message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and no process starts
