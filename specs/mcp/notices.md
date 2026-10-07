# Feature: notices

> Description: The one shape of every warning and every line of information Purlin prints,
>   in the terminal and on the dashboard: what the line is about, what kind of line it is,
>   what is wrong in a few words, and what to run. A reader learns the shape once. A proof that
>   was reworded is shown by the words that changed, never whole.
> Scope: scripts/mcp/purlin/notices.py, scripts/mcp/purlin/wording.py
> Stack: python/stdlib
> Highest-Rule: 8
> Highest-Proof: 18

## Rules

- RULE-1: A warning, and a line of information, is one line reading `<what it is about>: <kind>. <what is wrong> <what to do>`, where what to do is `Run <command>.` wherever a command clears it
- RULE-2: Every kind has words of its own, the same in every line of that kind: a kind the status counts under `Left to do` uses the words it uses there, `test comment to correct`, `spec to repair`, `rule to fix` and `rule to write a test for`, and every other kind has 2 to 5 words
- RULE-3: A line about a proof names it `<spec> PROOF-N (RULE-N)`, with the rule the spec gives the proof, and `<spec> PROOF-N` where no spec gives it one
- RULE-4: A test comment whose proof was reworded is named by the words that changed alone, `"<old words>" became "<new words>"`, the shortest run of words that differs, followed by the test's file and line and the commit that last changed the test; neither wording is printed whole
- RULE-5: A word added or taken out is shown with the word on each side of it; a side of more than 8 words is cut to its first 8, followed by ` ...`; and where the two wordings share no word at either end, or the words that differ are more than 8 on both sides, the line says `was reworded` and quotes neither
- RULE-6: The data the dashboard reads carries each line as an entry of `notices`: its tone, `warn` or `neutral`, its kind and the kind's words, what it is about, the spec and the rule it names, the rest of the line, and the line whole
- RULE-7: Where the status would print three or more lines of one kind that each name a spec, it prints one line in their place, the dashboard's own: the kind, how many specs, the first two and how many more, ending `Run purlin:status for each.`, or, where they name one spec, that spec, how many places and `Run purlin:status <name>.`; one or two lines of a kind are printed whole, and `purlin:status <name>` prints every line of that spec whole
- RULE-8: Where a line quotes another tool's own message, as git's for a source it cannot read, it quotes the message's first sentence, cut at 80 characters and followed by `...` where it is longer

## Proof

- PROOF-1 (RULE-1): A spec `login` carries `> Requires: api` and writes `RULE-2` twice; the status prints `login RULE-2: spec to repair. It is written twice, and the second is read. Run purlin:spec login.` and `login: line not read. Every anchor covers the whole project, so > Requires: is not read. Run purlin:spec login.`, each on a line of its own
- PROOF-2 (RULE-1): A spec `login` whose scope names `src/gone.py`, a file git does not have, gives one line of information, `login: spec ahead of its code. src/gone.py is not written yet. Run purlin:build login, or purlin:spec login to correct the path.`
- PROOF-17 (RULE-1): A line of the kind `model_not_reached` about `claude-opus-5-5`, with `The login expired.` wrong and `purlin:test --all` to run, reads `claude-opus-5-5: model not reached. The login expired. Run purlin:test --all.`
- PROOF-3 (RULE-2): No two kinds share their words; the kinds `to_correct`, `to_repair`, `to_fix` and `no_test` print `test comment to correct`, `spec to repair`, `rule to fix` and `rule to write a test for`, the words `Left to do` prints for one of each, and every other kind's words hold 2 to 5 words
- PROOF-4 (RULE-3): A test comment at `tests/test_login.py:1` names `login PROOF-9`, which the spec `login` does not have; the one comment named as naming nothing reads `login PROOF-9: test comment to correct. tests/test_login.py:1 names it, and no spec has it. Run purlin:build.`
- PROOF-5 (RULE-4): In a git project, `login`'s `PROOF-1 (RULE-1)` reads `The package holds exactly the sixteen keys the rule names` when the test under the comment at `tests/test_login.py:1` is committed, and a later commit changes `sixteen` to `seventeen`; the command that lists the test comments to correct prints `login PROOF-1 (RULE-1): test comment to correct. "sixteen" became "seventeen" after tests/test_login.py:1 last changed (<sha7>). Run purlin:build login.`, `<sha7>` the test's commit, then `1 test comment to correct.`
- PROOF-6 (RULE-4): In that project the line holds neither `The package holds` nor `keys the rule names`, and holds no line break
- PROOF-7 (RULE-5): A proof reading `A sample taken 90 minutes ago reads 90` gains ` minutes` at its end; the change reads `"90" became "90 minutes"`
- PROOF-8 (RULE-5): A proof reading `The export holds a header line and then one line per row` loses the word `header`; the change reads `"a header line" became "a line"`
- PROOF-9 (RULE-5): Between `Open the page and read one two three four five six seven eight nine ten words then stop` and `Open the page and read nothing then stop`, the change reads `"one two three four five six seven eight ..." became "nothing"`
- PROOF-10 (RULE-5): A proof reading `A` reworded to `B` reads `was reworded`, and so does a proof whose 9 middle words all change to 9 others between a first and a last word that stay
- PROOF-11 (RULE-6): In the project of PROOF-5 the payload's `notices` is exactly one entry: `tone` `warn`, `kind` `to_correct`, `label` `test comment to correct`, `about` `login PROOF-1 (RULE-1)`, `feature` `login`, `rule` `RULE-1`, `rest` `"sixteen" became "seventeen" after tests/test_login.py:1 last changed (<sha7>). Run purlin:build login.`, and `text` the line whole
- PROOF-12 (RULE-6): A line that carries no kind, handed to the same data, is an entry whose `text` and `rest` are the line and whose `kind`, `label`, `about`, `feature` and `rule` are null
- PROOF-13 (RULE-7): The specs `alpha`, `beta`, `delta` and `gamma` each carry `> Requires: api`; the status prints `line not read: 4 specs, alpha, beta and 2 more. Run purlin:status for each.` once and no line holding `: line not read.`, and `purlin_status.py --spec alpha` prints first `alpha: line not read. Every anchor covers the whole project, so > Requires: is not read. Run purlin:spec alpha.`
- PROOF-14 (RULE-7): With only `alpha` and `beta` carrying that line, the status's lines holding `line not read` are exactly the two whole lines, `alpha`'s then `beta`'s
- PROOF-15 (RULE-7): Three `rule to fix` lines naming `a RULE-1`, `a RULE-2` and `a RULE-3`, after one `rule to write a test for` line naming `b RULE-1` and before a line of no kind, fold to exactly `b RULE-1: rule to write a test for. Run purlin:build b.`, `rule to fix: a, in 3 places. Run purlin:status a.` and the line of no kind
- PROOF-16 (RULE-8): The message `fatal: repository not found. Check the address.` is quoted as `fatal: repository not found`; `fatal: ` followed by 100 `x` and then `. More.` is quoted as its first 80 characters and `...`, 83 characters in all
- PROOF-18 (RULE-7): Three lines `notices.model_not_reached` gives, for `model-a`, `model-b` and `model-c`, each with `The login expired.`, name no spec; the first is the line `notices.line` gives for the kind `model_not_reached`, and folded they are exactly the three whole lines, `model-a: model not reached. The login expired. Run purlin:test --all.` and the same for `model-b` and `model-c`, in the terminal's fold and in the dashboard's
