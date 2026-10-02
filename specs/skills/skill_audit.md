# Feature: skill_audit

> Description: What `skills/audit/SKILL.md` must name. The audit is run by hand: it runs the
>   tests, the heuristic spot tests and one planted bug per proof, aimed past that proof's test,
>   writes what it found into the evidence and reports the share of rules it found strong. The
>   skill names the commands and the files a reader needs to run it and to act on what it found.
> Scope: skills/audit/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 31
> Highest-Proof: 61

## Rules

- RULE-29: `skills/audit/SKILL.md` names the commands `purlin:audit`, `purlin:audit --all`, `purlin:audit <feature> RULE-N --settle` and `purlin:build`, and the paths `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, `.purlin/evidence/local/<feature>.json` and `references/review_criteria.md`
- RULE-30: The audit skill shows the two lines a settle prints, each in the words `references/review_criteria.md` gives under its heading `Settling a finding`
- RULE-31: The audit skill shows the line that refuses a settle for a test that has not changed and the sentence a settle under `--sound` leaves, each in the words `references/review_criteria.md` gives under its heading `Settling a finding`

## Proof

- PROOF-59 (RULE-29): A reader of the audit skill finds each of `purlin:audit`, `purlin:audit --all`, `purlin:audit <feature> RULE-N --settle`, `purlin:build`, `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, `.purlin/evidence/local/<feature>.json` and `references/review_criteria.md` named in it
- PROOF-56 (RULE-29): A copy of the audit skill with every `references/review_criteria.md` taken out is reported as `audit does not name references/review_criteria.md`
- PROOF-60 (RULE-30): The audit skill and the part of `references/review_criteria.md` under the heading `Settling a finding` each hold `the test now catches the bug it missed at` and `did not break what the proof says. A new bug was planted.`
- PROOF-61 (RULE-31): The audit skill and the part of `references/review_criteria.md` under the heading `Settling a finding` each hold `its test is as it was when the bug got past it. Strengthen it with purlin:build, then settle.` and `was settled with its test unchanged: it was judged to assert what the proof names.`
