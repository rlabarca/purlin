# Feature: skill_audit

> Description: What `skills/audit/SKILL.md` must name. The audit is run by hand: it runs the
>   tests, the heuristic spot tests, one model call per rule and one planted bug per proof, writes
>   what it found into the evidence and reports the share of rules it found strong. The skill
>   names the commands and the files a reader needs to run it and to act on what it found.
> Scope: skills/audit/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 29
> Highest-Proof: 59

## Rules

- RULE-29: `skills/audit/SKILL.md` names the commands `purlin:audit`, `purlin:audit --all` and `purlin:build`, and the paths `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, `.purlin/evidence/local/<feature>.json` and `references/review_criteria.md`

## Proof

- PROOF-59 (RULE-29): A reader of the audit skill finds each of `purlin:audit`, `purlin:audit --all`, `purlin:build`, `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, `.purlin/evidence/local/<feature>.json` and `references/review_criteria.md` named in it
- PROOF-56 (RULE-29): A copy of the audit skill with every `references/review_criteria.md` taken out is reported as `audit does not name references/review_criteria.md`
