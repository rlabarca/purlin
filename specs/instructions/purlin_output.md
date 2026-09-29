# Feature: purlin_output

> Description: The one check of what Purlin prints. The files under `scripts/` print Purlin's
>   terminal lines and build its dashboard, and setup writes a project's files from
>   `templates/`, so no emoji and no pictograph in those two folders means none in what they
>   print or write.
> Scope: scripts/**, templates/**

## Rules

- RULE-1: No file under `scripts/` or `templates/` carries an emoji or a pictograph other than `▶`

## Proof

- PROOF-1 (RULE-1): Every tracked file under `scripts/` and `templates/` is read; none holds a character with the Unicode property `Extended_Pictographic`, or U+FE0F, other than `▶`
