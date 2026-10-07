# Feature: purlin_docs

> Description: The docs under `docs/`. Every relative link on them resolves. The audit page
>   says what to do with a finding and links to the page of research behind the audit, which
>   cites each paper by a link it lists again under its sources. The index lists every page,
>   and the two pages on AI proofs, `docs/testing-ai.md` and `docs/graded-by-ai.md`, are
>   linked from each other and from each page that folds an AI proof in.
> Scope: docs/*.md
> Highest-Rule: 22
> Highest-Proof: 30

## Rules

- RULE-12: Every relative link on the pages under `docs/` names a file in the repository, and every `#` part names a heading of that file
- RULE-15: `docs/audit-research.md` cites the papers behind the audit, each by a link, and lists every source it cites under its heading `Sources`; `docs/audit.md` links to that page and names 3 or 4 of those sources, each by a link
- RULE-16: `docs/working-together.md` holds one paragraph on working in more than one checkout: each checkout has its own results and dashboard, and merging the work and running `purlin:status` in the main checkout brings the main one up to date
- RULE-17: `docs/audit.md` says what to do with a finding under its heading `What to do with a finding`, which stands straight after `How it works`: run `purlin:build`, and the rule ends `strong` or `spot-checked`
- RULE-18: The example on `docs/running-and-evidence.md` that fetches Purlin for a run on another system clones it at the tag a sign-off of this version writes, `signed/<version>`, the version being the `VERSION` file's
- RULE-19: `docs/index.md` lists every other page under `docs/` once in its table of guides, and the line under its title says how many guides that is
- RULE-20: `docs/testing-ai.md` and `docs/graded-by-ai.md` link to each other, and each page that folds an AI proof in links to both
- RULE-21: `docs/testing-ai.md` and `docs/graded-by-ai.md` each hold one flow diagram in plain mermaid, with each box's name in bold
- RULE-22: `docs/audit.md` and `docs/audit-research.md` count the heuristic spot tests as `references/review_criteria.md` does

## Proof

- PROOF-17 (RULE-12): Each relative link on the Markdown pages under `docs/` is followed from the page's own folder; each names a file the repository holds, and each `#` part matches a heading of that file as the git host spells its anchor
- PROOF-21 (RULE-15): The text of `docs/audit-research.md` cites Inozemtseva and Holmes, ICSE 2014; Just et al., FSE 2014; Petrović et al., TSE 2021; Foster et al., FSE 2025; and LLMorpheus, each as a link starting `https://`
- PROOF-22 (RULE-15): Every link the text of `docs/audit-research.md` gives before its heading `Sources` appears again in the list under `Sources`; `docs/audit.md` holds a link to `audit-research.md` and 3 or 4 links starting `https://`, and each of those is in that list
- PROOF-24 (RULE-16): Exactly 1 paragraph of `docs/working-together.md` names a worktree; one sentence of it opens `Each checkout` and says, with no word of denial before `has`, that it has its own results and its own dashboard, and the paragraph names merging and the whole command `purlin:status`
- PROOF-25 (RULE-17): In `docs/audit.md` the heading `What to do with a finding` is the next heading after `How it works`; the part under it holds exactly 6 bullets and names `purlin:build`, `strong` and `spot-checked`
- PROOF-26 (RULE-18): `docs/running-and-evidence.md` holds exactly 1 `git clone` of the purlin repository that names a branch, and the branch it names is `signed/` followed by the content of the `VERSION` file
- PROOF-27 (RULE-19): Under the heading `Guides` of `docs/index.md`, the first cell of each table row links one page by its file name; the pages linked are every Markdown page under `docs/` but `index.md`, each exactly 1 time, 13 in all, and the first line under the page's title reads `Thirteen guides, and the references behind them.`
- PROOF-28 (RULE-20): `docs/testing-ai.md` holds a link to `graded-by-ai.md` and `docs/graded-by-ai.md` holds a link to `testing-ai.md`; each of `how-purlin-works.md`, `specs-and-anchors.md`, `running-and-evidence.md`, `audit.md`, `sign-off.md` and `regulated.md` under `docs/` holds a link to `testing-ai.md` and a link to `graded-by-ai.md`
- PROOF-29 (RULE-21): Each of `docs/testing-ai.md` and `docs/graded-by-ai.md` holds exactly 1 fenced `mermaid` block; its first line reads `flowchart LR`, it holds 5 boxes or more, and the label of every box opens `<b>`
- PROOF-30 (RULE-22): The reference's heading reads `### The seven checks`, and each of `docs/audit.md` and `docs/audit-research.md` holds the words `The seven checks are in` exactly 1 time and no other count of checks
