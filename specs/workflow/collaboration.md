# Feature: collaboration

> Description: Product, QA and dev work at once through git, in three clones of one repository,
>   and reach a signed version. A script plays the three people, forces collisions, merges in
>   both orders, and checks the run completes with no step stuck, no command failing
>   unexpectedly and nothing corrupted. The run with real AI sessions is the owner's sanity
>   check, not this proof.
> Scope: scripts/init/scaffold.py, scripts/run/purlin_run.py, scripts/run/evidence.py, scripts/export, scripts/review/sign.py, scripts/spec/renumber.py, scripts/mcp/purlin
> Stack: python/stdlib (subprocess), git, ssh-keygen, pytest
> Highest-Rule: 1
> Highest-Proof: 1

## Rules

- RULE-1: Three people working at once through git reach a signed version: `signed/<version>` exists, and the evidence package it holds describes the code under it and matches its fingerprint; no step needs a command that Purlin's output, skills and docs do not give; no command fails unexpectedly, and every warning raised along the way is resolved by the end; no spec holds a number twice or a merge-conflict line; every test comment is tied and names a proof with the wording it was marked against; each spec's highest-number lines cover its numbers; and the package lists every rule

## Proof

- PROOF-1 (RULE-1): Pat, Quinn and Dana work in three clones of one bare repository; two pairs of branches take the same numbers, one merged QA first and one dev first; a test stays marked on a proof whose number moved; Dana runs and commits; Quinn signs `0.1.0`, then Pat; every check of RULE-1 holds @slow
