# Feature: skill_drift

> Description: What `skills/drift/SKILL.md` must say. Drift reports what changed since your last
>   pull, in one view, and it writes nothing.
> Scope: skills/drift/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 15
> Highest-Proof: 46

## Rules

- RULE-15: The skill names the commands `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:anchor sync` and `git fetch`, and the files `references/drift_criteria.md` and `scripts/run/purlin_drift.py`

## Proof

- PROOF-46 (RULE-15): The drift skill names `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:anchor sync`, `git fetch`, `references/drift_criteria.md` and `scripts/run/purlin_drift.py`
- PROOF-43 (RULE-15): A copy of the drift skill with every `purlin:spec` taken out is reported as `drift does not name purlin:spec`
