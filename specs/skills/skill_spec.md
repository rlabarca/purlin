# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must say. The spec skill turns a requirement in any
>   form into rules and proofs, so its text decides how ids are allocated, how each proof is
>   shaped, which the guide `references/spec_quality_guide.md` sets, and how the skill hands
>   over to the build.
> Scope: skills/spec/SKILL.md, references/spec_quality_guide.md, references/purlin_commands.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/spec/SKILL.md` opens with a frontmatter block whose `name` is `spec` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:spec`
- RULE-2: The skill allocates rule and proof ids against `origin/main`, read with `git show origin/main:<spec>`, and not against the working tree alone: the next id is one past the highest in either copy of the spec
- RULE-3: The skill closes by naming `purlin:build` in one fixed line, `Spec saved: <name>. Next: purlin:build <name>`, with nothing printed after it, and never starts building itself
- RULE-4: The whole of `skills/spec/SKILL.md` is at most 210 lines
- RULE-5: The skill writes `> Scope:` on every spec it creates, naming the files the requirement touches or the paths `purlin:build` will create, and says that a spec naming no files has its tests run on every `purlin:test` and that, at the gate `signed`, its rules cannot be signed and no tag is written
- RULE-6: Before it saves, the skill prints each rule with its proofs under it and asks whether to change any, saves the spec only once the person is satisfied, and drafts every proof against the guideline for a good proof
- RULE-7: The skill writes each proof as one case, one starting situation and one action in at most 60 words, with a refusal or a boundary as a proof of its own, and sends the reader to the guide's `One proof, one case`, which says the same

## Proof

- PROOF-1 (RULE-1): The spec skill opens with a block between two `---` lines in which `name` reads `spec` and `description` holds its value on its own line: not empty, not a `>` or `|` block, and not continued on the next line
- PROOF-14 (RULE-1): The command reference has a row, in a table headed `Command` and `Purpose`, whose first cell reads `purlin:spec <name>` and whose second cell is not empty
- PROOF-15 (RULE-1): A copy of the spec skill with its `name:` line deleted is refused, and the report says the name was expected to read `spec`
- PROOF-16 (RULE-1): A copy of the spec skill whose `description:` line holds no value is refused as carrying no one-line description
- PROOF-17 (RULE-1): A copy of the spec skill whose description sits on the next line, indented under an empty `description:`, is refused as carrying no one-line description
- PROOF-18 (RULE-1): A copy of the spec skill whose description is written as a `|` block is refused as carrying no one-line description
- PROOF-19 (RULE-1): A copy of the spec skill whose description runs on to a second, indented line is refused as carrying no one-line description
- PROOF-20 (RULE-1): A copy of the command reference without its `purlin:spec <name>` row, its `purlin:spec-from-code` row kept, is refused as carrying no row for `purlin:spec`
- PROOF-2 (RULE-2): The spec skill shows the command `git show origin/main:`, says ids are "allocated against `origin/main`, not against the working tree", and says the next id is "one past the highest in either copy of the spec"
- PROOF-21 (RULE-2): A copy of the spec skill with the fenced block holding `git show origin/main:` deleted is refused, and the report names `git show origin/main:` as missing
- PROOF-3 (RULE-3): The spec skill's last section, headed `When you are done`, sets the line `Spec saved: <name>. Next: purlin:build <name>` alone inside a fenced block, says to "end with exactly this and nothing after it", says "Never start the build yourself", and has an edited spec's changes said "before the offer"
- PROOF-22 (RULE-3): A copy of the spec skill whose closing line reads `Spec written. Shall I build it?` is refused, and the report names the missing line `Spec saved: <name>. Next: purlin:build <name>`
- PROOF-23 (RULE-3): A copy of the spec skill with the fence around its closing line removed is refused as not setting the line in a fenced block
- PROOF-24 (RULE-3): A copy of the spec skill without the words "and nothing after it" is refused as not saying that nothing follows the closing line
- PROOF-25 (RULE-3): A copy of the spec skill reading "Then build it" in place of "Never start the build yourself" is refused as not saying it never starts the build
- PROOF-26 (RULE-3): A copy of the spec skill with a section `## Notes` added after `When you are done` is refused as closing on `Notes`
- PROOF-27 (RULE-3): A copy of the spec skill that has an edited spec's changes said "after the offer" is refused as putting text after the closing line
- PROOF-4 (RULE-4): The spec skill, counted line by line, is at most 210 lines
- PROOF-28 (RULE-4): A copy of the spec skill lengthened with prose to exactly 210 lines is accepted, with nothing reported
- PROOF-29 (RULE-4): A copy of the spec skill lengthened with prose to 211 lines is refused, and the report gives the count 211 beside the ceiling 210
- PROOF-5 (RULE-5): The spec skill says, in one sentence, "Write `> Scope:` on every spec you create", naming "the files the requirement touches" and "the paths `purlin:build` will create", and its numbered step that writes the metadata names `> Scope:`
- PROOF-30 (RULE-5): The spec skill says, in one sentence, that of "A spec that names no files" "every run includes it", and "at the gate `signed` its rules cannot be signed and no tag is written"
- PROOF-31 (RULE-5): A copy of the spec skill with the sentence that opens "Write `> Scope:` on every spec you create" deleted is refused, and the report names that sentence as missing
- PROOF-32 (RULE-5): A copy of the spec skill without "the files the requirement touches" is refused as having no sentence that says what the scope names
- PROOF-33 (RULE-5): A copy of the spec skill whose sentence on a spec that names no files drops "at the gate `signed`" is refused as having no sentence that carries all of it
- PROOF-34 (RULE-5): A copy of the spec skill whose sentence on a spec that names no files drops "and no tag is written" is refused as having no sentence that carries all of it
- PROOF-35 (RULE-5): A copy of the spec skill whose numbered metadata step no longer names `> Scope:` is refused as having a metadata step without it
- PROOF-6 (RULE-6): In the spec skill's numbered procedure, the step "Print each rule with its proofs under it and ask whether to change any" comes before the step "Save the spec when the person is satisfied"
- PROOF-36 (RULE-6): The spec skill says, in one sentence, to draft every proof against `references/spec_quality_guide.md`, "Writing proofs", and that a good proof holds "at least one failure case"
- PROOF-37 (RULE-6): A copy of the spec skill with the step that prints the rules deleted is refused, and the report names that step as missing
- PROOF-38 (RULE-6): A copy of the spec skill with the print step and the save step swapped is refused as saving the spec before it prints the rules
- PROOF-39 (RULE-6): A copy of the spec skill that drafts proofs against "the guide" in place of `references/spec_quality_guide.md`, "Writing proofs" is refused, and the report names the missing instruction
- PROOF-7 (RULE-7): The spec skill says, in one sentence, "Write each proof as one case", "one starting situation and one action", "in at most 60 words", "a refusal or a boundary as a proof of its own" and the guide's "One proof, one case"
- PROOF-40 (RULE-7): The quality guide has a section headed `One proof, one case` that says "one starting situation, one action", "at most 60 words" and "A refusal or a boundary is a case of its own"
- PROOF-8 (RULE-7): A copy of the spec skill with ", and a refusal or a boundary as a proof of its own" deleted is refused as having no sentence that carries all of it
- PROOF-9 (RULE-7): A copy of the quality guide whose section `One proof, one case` no longer says "at most 60 words" is refused as not stating the limit
- PROOF-41 (RULE-7): A copy of the quality guide whose section `One proof, one case` no longer says "A refusal or a boundary is a case of its own" is refused as not saying it
