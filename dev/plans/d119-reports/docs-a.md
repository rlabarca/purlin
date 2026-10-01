# Lane `docs-a`, decision 119

Branch `lane/d119-docs-a`. Files changed: `README.md` and the eight pages of `docs/` the lane
owns. `dev/test_purlin_docs.py` is unchanged. Nothing under `specs/` changed.

## Tests

`python3 -m pytest dev/test_purlin_docs.py dev/test_install.py -q`

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before | 9 | 0 | 0 |
| After | 8 | 1 | 0 |

The one failure waits on lane `words`: `purlin_docs PROOF-17` reports exactly
`docs/running-and-evidence.md: ../references/evidence_and_signoff.md#a-run-on-another-system`.
The heading `## A run on another system` is the one plan section 4 gives that file, and it
replaces `## Where a runner runs` there. No other link is broken. `install PROOF-1`,
`purlin_docs PROOF-21`, `22` and `24` pass.

No test was deleted, rewritten or added.

Broken on purpose once: the heading `## Testing on another system` renamed in
`docs/running-and-evidence.md`. The link check then named three more links (from
`how-purlin-works.md`, `specs-and-anchors.md` and the page itself). Restored.

Plan section 8's first two greps find nothing in the nine files.

## Each page

Words are `wc -w`. Sentence length is the mean over prose, outside code blocks, tables and
headings; "long" counts sentences over 30 words.

| Page | Words before | Words after | Mean sentence before | after | Long before | after |
|---|---|---|---|---|---|---|
| `README.md` | 1101 | 1106 | 14.3 | 10.5 | 2 | 0 |
| `docs/running-and-evidence.md` | 4037 | 3911 | 16.0 | 13.0 | 11 | 5 |
| `docs/getting-started.md` | 1643 | 1616 | 14.2 | 11.3 | 6 | 0 |
| `docs/how-purlin-works.md` | 1499 | 1490 | 15.7 | 12.8 | 6 | 2 |
| `docs/index.md` | 505 | 520 | 12.7 | 8.8 | 0 | 0 |
| `docs/specs-and-anchors.md` | 3338 | 3537 | 16.7 | 11.9 | 13 | 1 |
| `docs/sign-off.md` | 2628 | 2693 | 17.6 | 12.0 | 11 | 5 |
| `docs/working-together.md` | 1424 | 1435 | 15.0 | 11.1 | 5 | 1 |
| `docs/upgrading.md` | 875 | 852 | 14.5 | 11.4 | 1 | 0 |
| Total | 17050 | 17160 | | | 55 | 14 |

The word total did not fall. The pass split sentences and turned stacked clauses into lists,
which costs words, and the new content added about 600: the GitHub example, judgment calls,
the two kinds of anchor, the slide tables on the sign-off and regulated work. The long
sentences left are mostly the plan's own word-for-word lines (`What that run does`) and
sentences carrying a long quoted line.

## What was done

1. **The removal.** `## Testing on another system` in `docs/running-and-evidence.md` is plan
   section 4's block, word for word, with its three subsections. Every other line the plan
   names is as the plan has it, on all nine pages.
2. **New content, in the slides' words.** `### Judgment calls` in `docs/specs-and-anchors.md`
   (it replaces `### Manual proofs`), and `docs/sign-off.md` points to it. `### Slow proofs`
   opens with the slide's lead and four rows and closes on `Nothing to remember.` The anchors
   section opens with the slide's lead and the two kinds, then `### An anchor in this project`
   and `### A remote anchor`, the second with `#### Kept in step` and `#### Read-only`.
3. **Remote anchor.** 9 places: `specs-and-anchors.md` 5, `working-together.md` 3,
   `index.md` 1. `Your copy is pinned to one version of its source.` stands once, in
   `docs/specs-and-anchors.md`.
4. **The plain-language pass**, on every page.

## Lines chosen here, not given by the plan

- `docs/specs-and-anchors.md`: the headings `### An anchor in this project` and
  `### A remote anchor`; `A remote anchor is owned elsewhere. The team that owns the rules keeps
  them in its own repository, and your project keeps a copy of the ones it must follow.`; in the
  table's second row, the added sentence `This kind is a remote anchor.`
- `docs/specs-and-anchors.md`, under `### Judgment calls`: `A proof a test settles carries no
  @manual, whatever that test needs to run. A test may ask a model a question with one right
  answer, such as which commands it offers after an install.` The second sentence is the plan's
  line for the quality guide.
- `docs/sign-off.md`: the opening table uses the sign-off slide's rows, and `## Beside a
  regulated system` opens with the regulated slide's rows, with `such as Veeva` added to the
  third.
- `docs/sign-off.md`: `A judgment call takes a proof tagged @manual. It is a hand check, and the
  walk stops at it.` then the link to `specs-and-anchors.md#judgment-calls`.
- `docs/running-and-evidence.md`: `[Testing on another system](#testing-on-another-system) says
  how a project gets that run.`; the exit codes as a table; `A result stops counting when the
  rule, the test or the code changes, until the tests are run again.` (the `why` slide).
- `docs/index.md`: the `Specs and anchors` row reads `The spec format, judgment calls, slow
  tests, operating systems, ids across branches, and the two kinds of anchor`.

## Differences from the plan

- The plan's last sentence of the Azure DevOps subsection links
  `../references/evidence_and_signoff.md` with no heading. The lane's task asked for the link by
  heading, so it reads `evidence_and_signoff.md#a-run-on-another-system`. That is the one link
  that depends on another lane's file, and why PROOF-17 waits.
- The plan calls `## Testing on another system` in `docs/how-purlin-works.md` four sentences.
  The slide's lead is two sentences and its closing two, so with the plan's own sentence the
  section holds five.
- `docs/sign-off.md` no longer says `look and feel is not a rule`. The plan has the sign-off
  page repeat none of the judgment-calls words, and `specs-and-anchors.md` says it.

## Statements the pages made that the specs do not hold, and fixes

- `docs/running-and-evidence.md`, the `Left to do` table, said it names each kind of work in
  order and left out `1 slow proof to run` / `purlin:test --all`. The row is added, between
  `1 rule to test` and `1 rule to test on Windows`, the order `references/evidence_and_signoff.md`
  gives.
- `docs/how-purlin-works.md`, "What keeps the tests from reading `met`?", left out a slow test
  that has not passed. Added.
- `docs/specs-and-anchors.md`, "Ids across branches", said the same thing twice in two
  sentences. One is kept.

## Open, for integration or the owner

- The pages describe what sibling lanes are building: no `--remote`, `--ci --commit`, the lines
  `Run purlin:test on Windows.` and `run purlin:test on Windows`, a `ci` section with the
  machine's name and the git email. They are true once `run`, `surfaces` and `words` merge.
- The example workflow clones Purlin with `--branch v0.10.0`, as the plan has it. The
  repository's tags run to `v0.9.5` today, so the example works once the release pushes
  `v0.10.0`.
- `README.md`'s command table still gives `purlin:sign [--version <version>]` and one purpose
  sentence per command, as `references/purlin_commands.md` has them now. If lane `words` rewords
  a purpose sentence, the reading pass brings the README in line.
- No failure was found in a file the lane does not own.
