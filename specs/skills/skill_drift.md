# Feature: skill_drift

> Description: What `skills/drift/SKILL.md` must say. Drift reports what changed since your last
>   pull, in one view, and it writes nothing.
> Scope: skills/drift/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 14
> Highest-Proof: 45

## Rules

- RULE-2: The skill names the file `references/drift_criteria.md`
- RULE-4: The whole of `skills/drift/SKILL.md` is at most 150 lines
- RULE-13: The skill names the commands `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:anchor sync` and `git fetch`
- RULE-14: The skill holds no emoji

## Proof

- PROOF-40 (RULE-2): The drift skill names `references/drift_criteria.md`
- PROOF-41 (RULE-2): A copy of the drift skill with every `references/drift_criteria.md` taken out is reported as `drift does not name references/drift_criteria.md`
- PROOF-4 (RULE-4): The drift skill, counted line by line, is at most 150 lines long
- PROOF-34 (RULE-4): A copy of the drift skill lengthened with lines of prose to exactly 150 lines is reported as having no problem
- PROOF-35 (RULE-4): A copy of the drift skill lengthened with lines of prose to 151 lines is reported as being 151 lines against its ceiling of 150
- PROOF-42 (RULE-13): The drift skill names `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:anchor sync` and `git fetch`
- PROOF-43 (RULE-13): A copy of the drift skill with every `purlin:spec` taken out is reported as `drift does not name purlin:spec`
- PROOF-44 (RULE-14): The drift skill holds no character from the Unicode emoji blocks
- PROOF-45 (RULE-14): A copy of the drift skill with the character U+2705 added to one line is reported as having one problem
