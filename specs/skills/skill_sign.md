# Feature: skill_sign

> Description: What `skills/sign/SKILL.md` must say. Sign builds the evidence package from the
>   committed evidence, walks it with a person, stopping only at hand checks, and adds their
>   sign-off over the package in a signed commit, in any project and at any time. The skill
>   names the commands and the files the agent runs and reads.
> Scope: skills/sign/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 36
> Highest-Proof: 67

## Rules

- RULE-35: The skill names the commands and files the agent runs, reads or hands on: `purlin:sign`, `--show`, `--answers`, `--check`, `--version`, `purlin:test --all --commit`, `git push origin`, `scripts/review/sign.py`, `.purlin/runtime/signoff-answers.json`, `.purlin/evidence/package/<version>.json` and `VERSION`
- RULE-36: The sign skill shows the lines the walk and `--check` print about AI proofs, as they are printed: the models they ran on, the proofs an AI graded, the AI outputs kept, the findings that count graded proofs, one graded run, and the AI outputs that match

## Proof

- PROOF-63 (RULE-35): The sign skill's text holds each of `purlin:sign`, `--show`, `--answers`, `--check`, `--version`, `purlin:test --all --commit` and `git push origin`, and the check of the commands it must name lists no problem
- PROOF-64 (RULE-35): The sign skill's text holds each of `scripts/review/sign.py`, `.purlin/runtime/signoff-answers.json`, `.purlin/evidence/package/<version>.json` and `VERSION`, and the check of the paths it must name lists no problem
- PROOF-66 (RULE-36): One fenced block of the sign skill holds these four whole lines in this order, the second and third indented two spaces and the others not: `AI proofs run on claude-opus-5-5: 12 proofs, 5 runs each.`, `Graded by an AI: 6 proofs, by claude-haiku-4-5-20251001.`, `AI outputs kept with the package: 60 of 60.` and `To read before you sign: 1 weak, 6 proofs graded by an AI.`
- PROOF-67 (RULE-36): The sign skill holds, each as a whole line of a fenced block, `AI outputs beside the package that match their sha256: 59 of 60.` with no indent and, indented two spaces, `refund_skill RULE-3: PROOF-6 on claude-opus-5-5, run 1 of 5, accepted by claude-haiku-4-5-20251001: The reply refuses, gives the limit as the reason and blames nobody.`; each is what `sign.py`'s own line for it gives with those values
