# Feature: purlin_docs

> Description: The docs are the pages `docs/index.md` lists: how Purlin works, getting started,
>   specs and anchors, running and evidence, working together, the sign-off, upgrading, the
>   audit and the dashboard. Every relative link on them resolves. The audit page says why the
>   audit works as it does and cites the research behind it, each paper by a link the page
>   lists again under its sources.
> Scope: docs/*.md
> Highest-Rule: 15
> Highest-Proof: 23

## Rules

- RULE-12: Every relative link on the pages under `docs/` names a file in the repository, and every `#` part names a heading of that file
- RULE-14: The docs are exactly `docs/index.md` and the nine pages it links to
- RULE-15: `docs/audit.md` cites the papers behind the audit, each by a link, and lists every source it cites under its heading `Sources`

## Proof

- PROOF-17 (RULE-12): Each relative link on the Markdown pages under `docs/` is followed from the page's own folder; each names a file the repository holds, and each `#` part matches a heading of that file as the git host spells its anchor
- PROOF-19 (RULE-14): `docs/index.md` links to each of `how-purlin-works.md`, `getting-started.md`, `specs-and-anchors.md`, `running-and-evidence.md`, `working-together.md`, `sign-off.md`, `upgrading.md`, `audit.md` and `dashboard.md`, and each names a file under `docs/`
- PROOF-20 (RULE-14): Every Markdown file directly under `docs/` is either `index.md` or one of the nine pages `docs/index.md` links to
- PROOF-21 (RULE-15): The text of `docs/audit.md` cites Inozemtseva and Holmes, ICSE 2014; Just et al., FSE 2014; Petrović et al., TSE 2021; Foster et al., FSE 2025; and LLMorpheus, each as a link starting `https://`
- PROOF-22 (RULE-15): Every link the text of `docs/audit.md` gives before its heading `Sources` appears again in the list under `Sources`
- PROOF-23 (RULE-15): Each entry of the list under `Sources` in `docs/audit.md` carries a title that is a link starting `https://`
