# Feature: drift

> Description: What changed since your last pull, in one view. Drift reads git's
>   own log of HEAD for the last action that brought changes in, and reports
>   what changed between where HEAD stood before it and HEAD: rules added,
>   changed and removed; proofs added, changed and moved; each number a spec
>   writes twice, with the line that moves and how old the copy of the default
>   branch is; each test comment whose proof's wording changed after its test
>   was last changed; and each anchor behind its source, checked without
>   pulling. It reads only this checkout, reports facts and judges nothing.
> Scope: scripts/mcp/purlin/drift.py, scripts/mcp/purlin/wording.py
> Stack: python/stdlib, json, re, subprocess (list-only)
> Highest-Rule: 43
> Highest-Proof: 88

## Rules

- RULE-1: A `since` argument is accepted only as a commit count of digits or a `YYYY-MM-DD` date; any other value is refused with the error `rejected since` and a reason naming both accepted forms, and no subprocess starts
- RULE-2: With no `since`, the range runs from where HEAD stood before the newest entry of git's log of HEAD whose action is a pull, a merge, a merge committed after its conflicts were resolved, a finished rebase, a checkout or a reset, to HEAD; a pull or a rebase that git logged as several steps is measured from where HEAD stood before its first step, and a checkout that leaves HEAD at the commit it stood at starts no range
- RULE-3: When the newest such entry is the clone, or there is none, the range is the last 20 commits, or every commit when there are fewer
- RULE-4: `since` overrides the log: a count of N gives the last N commits, and a date gives every commit made on or after it
- RULE-6: The view compares, for each spec file the range changed, the spec's rule ids and texts at the start of the range with those at HEAD, matching a spec by its name wherever its file lies, and prints `<n> rules added: `, `<n> rules changed: ` and `<n> rules removed: ` lines naming each feature and its rule ids, or, when there is none, `No rule was added, changed or removed` followed by the range, as in `No rule was added, changed or removed since your last pull.`
- RULE-10: The view names every remote anchor that is not current, by its own spec name and with the command that fixes it: one whose source has moved past its pin is `behind` with the source's 7-character sha, one naming a source and no pin is `unpinned`, one whose source cannot be read is `error` with the reason, and one still at its pin is not named at all
- RULE-11: A `> Source:` value is refused before any process starts when it begins with `-`, names an `ext::` or an `fd::` transport, or carries a NUL byte or a newline, and the refusal names which of those it was
- RULE-20: The view reports an anchor whose `> Source:` names no repository, words or a file on disk, as `error` with the line that names `purlin:spec`, and no process is handed the source
- RULE-31: The view names each number a spec of this checkout writes twice, and never as a proof changed: the line whose text is the one on the default branch keeps it, and the other is renumbered to the next free number
- RULE-32: Where the view names a number written twice, it says how long ago this checkout last fetched the default branch
- RULE-33: The view names each test comment whose proof's wording changed after its test was last changed, where the range changed that proof or that test's file, quoting both wordings
- RULE-35: A test is last changed at the newest commit that changed its lines below its marker comment, or any line of its file when the file is run whole; a test with a line not committed is never named
- RULE-40: When drift cannot read the project, because `.purlin/config.json` cannot be read or HEAD names no commit, its whole answer names what is wrong and how to fix it, in place of the report, and no process starts beyond reading git
- RULE-41: Drift changes nothing: it writes no file, leaves HEAD and the working tree as they were, fetches nothing from the remote, and checks an anchor's source without pulling it, so the anchor's file, its pin and this checkout's git objects stay as they were
- RULE-42: The report carries exactly `since` and `view`, and the view carries its lines and the facts they were built from under fixed keys
- RULE-43: The view names the proofs the range added, in one count line by feature; each proof whose wording the range changed, quoting its text at both ends; and each proof whose text the range moved, unchanged, to another id of the same spec

## Proof

- PROOF-1 (RULE-1): Drift is asked for the changes since `--output=/tmp/x`; the answer is the error `rejected since` with the reason `since must be a number of commits (digits only) or a YYYY-MM-DD date; refusing to pass "--output=/tmp/x" to git`, and no process was started
- PROOF-3 (RULE-2): A checkout pulls 2 new commits from a second repository, then commits once more on its own; the range runs from the commit it stood at before the pull to HEAD, 3 commits, and names the action `pull`
- PROOF-29 (RULE-2): A branch of 2 commits and `main` change the same line of one file, the merge stops on the conflict, and the file is resolved and the merge committed by hand; the range runs from `main` as it stood before the merge to HEAD, 3 commits, and names the action `merge`
- PROOF-86 (RULE-2): A pull brings in 2 commits, then `git checkout -b topic` makes a branch at HEAD; the range still runs from where HEAD stood before the pull, 2 commits, and names the action `pull`
- PROOF-8 (RULE-3): A clone is made of a repository of 25 commits; the range is its last 20 commits, from the 21st commit back to HEAD, and names the action `clone`
- PROOF-9 (RULE-4): After a pull that brought in 1 commit, drift is asked for the changes since `3`; the range is the last 3 commits, not the pull's 1, and the first line begins `The last 3 commits (`
- PROOF-10 (RULE-4): In a project whose three commits are dated 2026-01-01, 2026-03-01 and 2026-04-01, drift is asked for the changes since `2026-02-15`; the range is the last 2 commits, from the first commit to HEAD, and the first line begins `Since 2026-02-15 (`
- PROOF-12 (RULE-6): One pull brings in spec changes that add `RULE-3` to `login`, reword `RULE-1` of `login` and remove `RULE-2` of `cart`; after its first line the view reads exactly `1 rule added: login RULE-3.`, `1 rule changed: login RULE-1.` and `1 rule removed: cart RULE-2.`
- PROOF-38 (RULE-6): A pull brings in one change, a spec moved to another folder with its rules unchanged; after its first line the view reads exactly `No rule was added, changed or removed since your last pull.`
- PROOF-17 (RULE-10): An anchor is pinned to its source's first commit, and the source gains a second; the view holds one row for it, reading `behind` with the first 7 characters of the new commit's sha, and the line `anchor external_anchor: the pin <first sha7> is behind its source, now <new sha7>. Run purlin:anchor sync external_anchor.`
- PROOF-19 (RULE-10): The anchor `policy` names the source `https://github.com/acme/p.git` and no pin; its row reads `unpinned` with no sha, the view reads `anchor policy: names a source and no pin. Run purlin:anchor sync policy.`, and no process is handed that source
- PROOF-40 (RULE-10): The anchor `policy` is pinned to a source path where no repository exists; its row reads `error` with no sha and a reason naming that path, and the view reads `anchor policy: the source could not be read (<the reason>). Check its > Source: line, then run purlin:anchor sync policy.`
- PROOF-20 (RULE-11): The anchor `policy` is pinned to the source `--upload-pack=/bin/echo`; its row reads `error` with the reason `begins with "-"`, the view reads `anchor policy: the source could not be read (begins with "-"). Check its > Source: line, then run purlin:anchor sync policy.`, and no process is handed that source
- PROOF-42 (RULE-11): An anchor pinned to the source `ext::sh -c id` reads `error` with the reason `names an ext:: transport`, and no process is handed that source
- PROOF-44 (RULE-11): An anchor pinned to a source carrying a NUL byte, `/srv/anchors<NUL>.git`, reads `error` with the reason `contains a NUL byte`, and no process is handed that source
- PROOF-56 (RULE-20): The anchor `refunds` is pinned to the source `policy.txt`, a text file in the project; its row reads `error`, its line begins `anchor refunds: its source, policy.txt, is not a spec in Purlin's format kept in a git repository` and names `purlin:spec refunds`, and no process is handed `policy.txt`
- PROOF-70 (RULE-31): After a merge, `login` writes `PROOF-4` twice, its line on `origin/main` reading `A` and the branch's `B`; the view holds `login: PROOF-4 is written twice. The line on origin/main keeps PROOF-4; renumber the other to PROOF-5 and move its test comments with it: "B".`
- PROOF-71 (RULE-31): `login` writes `PROOF-7` twice and `origin/main` holds neither line; the view holds `login: PROOF-7 is written twice, and neither line is on origin/main. The one that reaches origin/main first keeps PROOF-7; renumber the other to PROOF-8 and move its test comments with it.`
- PROOF-85 (RULE-31): After a merge, `login` writes `PROOF-4` twice, `A` from `origin/main` and `B` from the branch; the view names `PROOF-4` as written twice and holds no line beginning `login PROOF-4 changed`
- PROOF-73 (RULE-32): `login` writes `PROOF-4` twice and `origin/main` was last updated three days ago; the view holds `origin/main was last fetched 3 days ago, and drift does not fetch. Run git fetch, then purlin:drift again.`
- PROOF-75 (RULE-33): A test marked `login PROOF-4` is committed while `PROOF-4` reads `A`, and a pull rewords it `B`; the view holds `tests/test_login.py:1 names login PROOF-4, whose wording changed after the test was last changed in <sha7>: it read "A" and now reads "B". Run purlin:build login to make the test show it; the line clears once the test changes.`
- PROOF-76 (RULE-33): A test marked `login PROOF-4` is committed while `PROOF-4` reads `A`, and a pull rewords it `B` and puts `A` under `PROOF-6`; the comment's line ends `it read "A" and now reads "B". Its old wording is now PROOF-6: move the comment there.`
- PROOF-82 (RULE-35): A test marked `login PROOF-4` is committed while it reads `A`; a pull rewords it `B`, and a commit after the pull changes an assertion in the test; the view holds no line naming `tests/test_login.py:1`
- PROOF-83 (RULE-35): A test marked `login PROOF-4` is committed while it reads `A`; a pull rewords it `B`, and an assertion in the test is then changed and not committed; the view holds no line naming `tests/test_login.py:1`
- PROOF-84 (RULE-35): A test marked `login PROOF-4` is committed while it reads `A`; a pull rewords it `B`, and a commit then rewrites only the comment line, still naming `login PROOF-4`; the view still holds a line naming `tests/test_login.py:1`
- PROOF-58 (RULE-40): A project's `.purlin/config.json` holds a comma after its last setting; drift's whole answer is `.purlin/config.json cannot be read: <the JSON reader's message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and no process starts
- PROOF-61 (RULE-40): In a repository made with `git init` and no commit, drift is asked for its report; the answer is the error `no commits` with the reason `drift reads git, and HEAD names no commit here`
- PROOF-66 (RULE-41): In a checkout that has just pulled a change to a spec and a source file, drift is asked for its report twice; HEAD, `git status --porcelain` and the bytes of every file outside `.git` read the same after as before
- PROOF-74 (RULE-41): Another clone pushes a commit to the bare repository this checkout was cloned from; after drift runs here, `origin/main` names the commit it named before
- PROOF-88 (RULE-41): An anchor is pinned to its source's first commit and the source gains a second; after the view names it `behind`, the anchor's file reads byte for byte as before, and this checkout holds no object of the source's second commit
- PROOF-27 (RULE-42): After a pull, the report carries exactly `since` and `view`, and `since` carries exactly `action`, `commits`, `from`, `line`, `to` and `when`
- PROOF-49 (RULE-42): After a pull, the view carries exactly `anchors_behind`, `comments_changed`, `default_branch`, `lines`, `numbers_twice`, `proofs_added`, `proofs_changed`, `proofs_moved`, `rules_added`, `rules_changed` and `rules_removed`
- PROOF-67 (RULE-43): A pull adds `PROOF-5` and `PROOF-6` to `login`; the view holds `2 proofs added: login PROOF-5, PROOF-6.`
- PROOF-68 (RULE-43): A pull changes `login`'s `PROOF-1` from `An age of 150 minutes` to `An age of 90 minutes`; the view holds `login PROOF-1 changed: it read "An age of 150 minutes" and now reads "An age of 90 minutes".`
- PROOF-69 (RULE-43): A pull moves the text of `login`'s `PROOF-4` to `PROOF-6` and gives `PROOF-4` a new text; the view holds `login PROOF-4 moved to PROOF-6.`
