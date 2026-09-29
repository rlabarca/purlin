# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must say. The spec skill turns a requirement in any
>   form into rules and proofs, so its text decides how ids are allocated, how each proof is
>   shaped, which the guide `references/spec_quality_guide.md` sets, and how the skill hands
>   over to the build.
> Scope: skills/spec/SKILL.md, references/spec_quality_guide.md, references/purlin_commands.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec/SKILL.md` opens with a frontmatter block whose `name` is `spec` and whose `description` is one non-empty line
- RULE-2: The skill tells the agent to allocate rule and proof ids against `origin/main`, read with `git show origin/main:<spec>`, and not against the working tree alone: the next id is one past the highest in either copy of the spec
- RULE-3: The skill tells the agent to close on one fixed line, `Spec saved: <name>. Next: purlin:build <name>`, with nothing printed after it, and never to start building itself
- RULE-4: The whole of `skills/spec/SKILL.md` is at most 210 lines
- RULE-5: The skill tells the agent to write `> Scope:` on every spec it creates, naming the files the requirement touches or the paths `purlin:build` will create
- RULE-6: The skill tells the agent to print each rule with its proofs under it and ask whether to change any before it saves, and to save the spec only once the person is satisfied
- RULE-7: The skill tells the agent to write each proof as one case, one starting situation and one action in at most 60 words, with a refusal or a boundary as a proof of its own, and points it at the guide's `One proof, one case`
- RULE-8: `references/purlin_commands.md` carries a row for `purlin:spec`
- RULE-9: The skill tells the agent that a spec naming no files has its tests run on every `purlin:test` and that, at the gate `signed`, its rules cannot be signed and no tag is written
- RULE-10: The skill tells the agent to draft every proof against the guideline for a good proof in `references/spec_quality_guide.md`
- RULE-11: The guide's section `One proof, one case` says a proof holds one starting situation and one action in at most 60 words, and that a refusal or a boundary is a case of its own

## Proof

- PROOF-1 (RULE-1): The spec skill opens with a block between two `---` lines in which `name` reads `spec` and `description` holds its value on its own line: not empty, not a `>` or `|` block, and not continued on the next line
- PROOF-14 (RULE-8): The command reference has a row, in a table headed `Command` and `Purpose`, whose first cell reads `purlin:spec <name>` and whose second cell is not empty
- PROOF-2 (RULE-2): The spec skill shows the command `git show origin/main:`, says ids are "allocated against `origin/main`, not against the working tree", and says the next id is "one past the highest in either copy of the spec"
- PROOF-3 (RULE-3): The spec skill's last section, headed `When you are done`, sets the line `Spec saved: <name>. Next: purlin:build <name>` alone inside a fenced block, says to "end with exactly this and nothing after it", says "Never start the build yourself", and has an edited spec's changes said "before the offer"
- PROOF-4 (RULE-4): The spec skill, counted line by line, is at most 210 lines
- PROOF-28 (RULE-4): A copy of the spec skill lengthened with prose to exactly 210 lines is accepted, with nothing reported
- PROOF-5 (RULE-5): The spec skill says, in one sentence, "Write `> Scope:` on every spec you create", naming "the files the requirement touches" and "the paths `purlin:build` will create", and its numbered step that writes the metadata names `> Scope:`
- PROOF-30 (RULE-9): The spec skill says, in one sentence, that of "A spec that names no files" "every run includes it", and "at the gate `signed` its rules cannot be signed and no tag is written"
- PROOF-6 (RULE-6): In the spec skill's numbered procedure, the step "Print each rule with its proofs under it and ask whether to change any" comes before the step "Save the spec when the person is satisfied"
- PROOF-36 (RULE-10): The spec skill says, in one sentence, to draft every proof against `references/spec_quality_guide.md`, "Writing proofs", and that a good proof holds "at least one failure case"
- PROOF-7 (RULE-7): The spec skill says, in one sentence, "Write each proof as one case", "one starting situation and one action", "in at most 60 words", "a refusal or a boundary as a proof of its own" and the guide's "One proof, one case"
- PROOF-40 (RULE-11): The quality guide has a section headed `One proof, one case` that says "one starting situation, one action", "at most 60 words" and "A refusal or a boundary is a case of its own"
