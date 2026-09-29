# Feature: purlin_output

> Description: The one check of what Purlin prints. Every line a person reads from Purlin, in
>   the terminal, the dashboard or a file setup writes, comes from a file under `scripts/` or
>   `templates/`, so no emoji and no pictograph in those files means none in what Purlin prints.
> Scope: scripts/**, templates/**

## Rules

- RULE-1: No file under `scripts/` or `templates/` carries an emoji or a pictograph other than `▶`

## Proof

- PROOF-1 (RULE-1): Every tracked file under `scripts/` and `templates/` is read; none holds a character with the Unicode property `Extended_Pictographic`, or U+FE0F, other than `▶`
