# Feature: skill_audit

> Description: What `skills/audit/SKILL.md` must name. The audit is run by hand: it runs the
>   tests, the heuristic spot tests, one planted bug per proof and the model's reading, writes
>   what it found into the evidence and reports the share of rules it found strong. The skill
>   names the commands and the files a reader needs to run it and to act on what it found,
>   within its line ceiling, with no emoji.
> Scope: skills/audit/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 28
> Highest-Proof: 58

## Rules

- RULE-4: The whole of `skills/audit/SKILL.md` is at most 105 lines
- RULE-26: `skills/audit/SKILL.md` names the commands `purlin:audit`, `purlin:audit --all` and `purlin:build`
- RULE-27: `skills/audit/SKILL.md` names the paths `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, `.purlin/evidence/local/<feature>.json` and `references/review_criteria.md`
- RULE-28: `skills/audit/SKILL.md` holds no emoji

## Proof

- PROOF-4 (RULE-4): The audit skill, its lines counted, is at most 105 lines long
- PROOF-31 (RULE-4): A copy of the audit skill made exactly 105 lines long is not reported
- PROOF-32 (RULE-4): A copy of the audit skill made 106 lines long is reported as 106 lines long against a ceiling of 105
- PROOF-53 (RULE-26): A reader of the audit skill finds each of `purlin:audit`, `purlin:audit --all` and `purlin:build` named in it
- PROOF-54 (RULE-26): A copy of the audit skill with every `purlin:build` taken out is reported as `audit does not name purlin:build`
- PROOF-55 (RULE-27): A reader of the audit skill finds each of `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, `.purlin/evidence/local/<feature>.json` and `references/review_criteria.md` named in it
- PROOF-56 (RULE-27): A copy of the audit skill with every `references/review_criteria.md` taken out is reported as `audit does not name references/review_criteria.md`
- PROOF-57 (RULE-28): A reader of the audit skill finds no emoji in it
- PROOF-58 (RULE-28): A copy of the audit skill with one emoji added to its first line is reported, naming line `1`
