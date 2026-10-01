# Feature: purlin_docs

> Description: The docs under `docs/`. Every relative link on them resolves. The audit page
>   cites the research behind the audit, each paper by a link the page lists again under its
>   sources.
> Scope: docs/*.md
> Highest-Rule: 15
> Highest-Proof: 23

## Rules

- RULE-12: Every relative link on the pages under `docs/` names a file in the repository, and every `#` part names a heading of that file
- RULE-15: `docs/audit.md` cites the papers behind the audit, each by a link, and lists every source it cites under its heading `Sources`

## Proof

- PROOF-17 (RULE-12): Each relative link on the Markdown pages under `docs/` is followed from the page's own folder; each names a file the repository holds, and each `#` part matches a heading of that file as the git host spells its anchor
- PROOF-21 (RULE-15): The text of `docs/audit.md` cites Inozemtseva and Holmes, ICSE 2014; Just et al., FSE 2014; Petrović et al., TSE 2021; Foster et al., FSE 2025; and LLMorpheus, each as a link starting `https://`
- PROOF-22 (RULE-15): Every link the text of `docs/audit.md` gives before its heading `Sources` appears again in the list under `Sources`
