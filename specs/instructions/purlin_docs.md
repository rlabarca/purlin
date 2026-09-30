# Feature: purlin_docs

> Description: The four pages a reader meets first, `README.md`, `docs/index.md`,
>   `docs/getting-started.md` and `docs/how-purlin-works.md`, say what the product does now.
>   The README's command table carries the purpose sentences of `references/purlin_commands.md`.
>   Each printed line the four pages quote sits in a fenced block marked `text`, under a
>   comment naming the run of the sample project it was taken from, `<!-- sample: <run> -->`.
>   The sample project is the ten-minute path: a Python project whose `pyproject.toml`
>   configures pytest and that holds no code, set up at the gate `passed` with the commit agreed,
>   then one spec, `cart`, of three rules, with its code and three marked tests. A second project
>   with no test tool Purlin knows gives the line the first run prints for it.
> Scope: README.md, docs/index.md, docs/getting-started.md, docs/how-purlin-works.md
> Highest-Rule: 12

## Rules

- RULE-1: The README's command table gives every command the purpose sentence `references/purlin_commands.md` gives it, word for word
- RULE-2: Every printed line quoted on the four pages is printed, word for word, by a run of the sample project the page describes
- RULE-12: Every relative link on the four pages names a file in the repository, and every `#` part names a heading of that file

## Proof

- PROOF-1 (RULE-1): Each row of the README's command table carries, character for character, the purpose sentence the command reference gives the command in that row
- PROOF-2 (RULE-1): Each of the 11 commands the command reference lists has a row in the README's command table
- PROOF-3 (RULE-2): The sample project is set up at the gate `passed` with the commit agreed; each block of lines the pages take from setup is printed by it, one line after another as the page shows them
- PROOF-4 (RULE-2): In the set-up sample project with the spec, code and tests of `cart` committed, the first test run of `cart` prints each block of lines the pages take from it, one line after another
- PROOF-5 (RULE-2): Once the entry the first run suggested is written into the `tests` setting, the next test run of `cart` prints each block of lines the pages take from it, one line after another
- PROOF-6 (RULE-2): After that run, a test run with `--commit` and no feature named prints each block of lines the pages take from it, one line after another
- PROOF-7 (RULE-2): With the cart's code changed so that the test of `RULE-2` fails, a test run with no feature named prints each block of lines the pages take from it, one line after another
- PROOF-8 (RULE-2): In a set-up project with the spec and tests of `cart` and no test tool Purlin knows, the first test run of `cart` prints each block of lines the pages take from it
- PROOF-9 (RULE-2): Every fenced block on the four pages names its language, and every block marked `text` sits under a comment naming one of the six runs of the sample project
- PROOF-17 (RULE-12): Each relative link on the four pages is followed from the page's own folder; each names a file the repository holds, and each `#` part matches a heading of that file as the git host spells its anchor
