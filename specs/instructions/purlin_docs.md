# Feature: purlin_docs

> Description: The docs under `docs/`. Every relative link on them resolves. The audit page
>   says what to do with a finding and cites the research behind the audit, each paper by a link
>   the page lists again under its sources.
> Scope: docs/*.md
> Highest-Rule: 18
> Highest-Proof: 26

## Rules

- RULE-12: Every relative link on the pages under `docs/` names a file in the repository, and every `#` part names a heading of that file
- RULE-15: `docs/audit.md` cites the papers behind the audit, each by a link, and lists every source it cites under its heading `Sources`
- RULE-16: `docs/working-together.md` holds one paragraph on working in more than one checkout: each checkout has its own results and dashboard, and merging the work and running `purlin:status` in the main checkout brings the main one up to date
- RULE-17: `docs/audit.md` says what to do with a finding under its heading `What to do with a finding`, which stands straight after `How it works`: run `purlin:build`, and the rule ends `strong` or `spot-checked`
- RULE-18: The example on `docs/running-and-evidence.md` that fetches Purlin for a run on another system clones it at the tag a sign-off of this version writes, `signed/<version>`, the version being the `VERSION` file's

## Proof

- PROOF-17 (RULE-12): Each relative link on the Markdown pages under `docs/` is followed from the page's own folder; each names a file the repository holds, and each `#` part matches a heading of that file as the git host spells its anchor
- PROOF-21 (RULE-15): The text of `docs/audit.md` cites Inozemtseva and Holmes, ICSE 2014; Just et al., FSE 2014; Petrović et al., TSE 2021; Foster et al., FSE 2025; and LLMorpheus, each as a link starting `https://`
- PROOF-22 (RULE-15): Every link the text of `docs/audit.md` gives before its heading `Sources` appears again in the list under `Sources`
- PROOF-24 (RULE-16): Exactly 1 paragraph of `docs/working-together.md` names a worktree; it says each checkout has its own results and its own dashboard, and names merging and `purlin:status`
- PROOF-25 (RULE-17): In `docs/audit.md` the heading `What to do with a finding` is the next heading after `How it works`; the part under it holds exactly 6 bullets and names `purlin:build`, `strong` and `spot-checked`
- PROOF-26 (RULE-18): `docs/running-and-evidence.md` holds exactly 1 `git clone` of the purlin repository that names a branch, and the branch it names is `signed/` followed by the content of the `VERSION` file
