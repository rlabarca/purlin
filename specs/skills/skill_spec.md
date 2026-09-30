# Feature: skill_spec

> Description: What `skills/spec/SKILL.md` must say. The spec skill turns a requirement in any
>   form into rules and proofs, so its text decides how ids are allocated, how each proof is
>   shaped, which the guide `references/spec_quality_guide.md` sets, and how the skill hands
>   over to the build.
> Scope: skills/spec/SKILL.md, references/spec_quality_guide.md, references/purlin_commands.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 22

## Rules

- RULE-1: `skills/spec/SKILL.md` opens with a frontmatter block whose `name` is `spec` and whose `description` is one non-empty line
- RULE-2: The skill tells the agent that a new rule takes one more than the highest of `> Highest-Rule:` and every rule number in the working copy and in `origin/main`'s copy, read with `git show origin/main:<spec>`, and that proof ids are allocated the same way
- RULE-3: The skill tells the agent to close on one fixed line, `Spec saved: <name>. Next: purlin:build <name>`, with nothing printed after it, and never to start building itself
- RULE-4: The whole of `skills/spec/SKILL.md` is at most 210 lines
- RULE-5: The skill tells the agent to write `> Scope:` on every spec it creates, naming the files the requirement touches or the paths `purlin:build` will create
- RULE-6: The skill tells the agent to print each rule with its proofs under it and ask whether to change any before it saves, and to save the spec only once the person is satisfied
- RULE-7: The skill tells the agent to write each proof as one case, one starting situation and one action in at most 60 words, with a refusal or a boundary as a proof of its own, and points it at the guide's `One proof, one case`
- RULE-8: `references/purlin_commands.md` carries a row for `purlin:spec`
- RULE-9: The skill tells the agent that a spec naming no files has its tests run on every `purlin:test` and that, at the gate `signed`, its rules cannot be signed and no tag is written
- RULE-10: The skill tells the agent to draft every proof against the guideline for a good proof in `references/spec_quality_guide.md`
- RULE-11: The guide's section `One proof, one case` says a proof holds one starting situation and one action in at most 60 words, and that a refusal or a boundary is a case of its own
- RULE-13: The skill tells the agent to write the number a new rule takes into `> Highest-Rule:`, adding the line after the spec's other `>` lines where it is missing
- RULE-14: The skill tells the agent to call `sync_status` with `project_root` set to the project root, the top folder of the git checkout
- RULE-15: The skill's intake table says what to do with each kind of input: one sentence, a product description or a ticket, pasted acceptance criteria, and a screenshot
- RULE-16: The skill tells the agent to edit an existing spec in place when given a change, and never to renumber
- RULE-17: After a merge that leaves one id twice in a spec, the skill tells the agent to keep both rules and give the incoming one the next free number, moving its test markers and signature filenames with it
- RULE-18: The skill tells the agent that two branches that advanced the same anchor pin resolve to the newer sha
- RULE-19: The guide's section `Written for a person who cannot read code` says that for a library a proof may name a function or class the library exports and an error type a caller gets back, and that a name from inside the code stays out
- RULE-20: The guide's section `One proof, one case` says one proof may name a list of like inputs that share one action and one kind of result
- RULE-21: The guide's table `When a rule is stuck` gives, for a proof tagged for a system that has not run, the word `not run` with `<System>: no run yet`, and names `purlin:test --remote` and the runner file
- RULE-22: The skill tells the agent to commit the spec it writes, with the `spec(<name>):` prefix, before it ends on its closing line

## Proof

- PROOF-1 (RULE-1): The spec skill opens with a block between two `---` lines in which `name` reads `spec` and `description` holds its value on its own line: not empty, not a `>` or `|` block, and not continued on the next line
- PROOF-14 (RULE-8): The command reference has a row, in a table headed `Command` and `Purpose`, whose first cell reads `purlin:spec <name>` and whose second cell is not empty
- PROOF-2 (RULE-2): The spec skill's section `Ids` says a new rule takes "one more than the highest of `> Highest-Rule:` and every rule number in either copy of the spec", names `git show origin/main:<spec>`, and says proof ids are allocated the same way; procedure step 5 points at `Ids`
- PROOF-3 (RULE-3): The spec skill's last section, headed `When you are done`, sets the line `Spec saved: <name>. Next: purlin:build <name>` alone inside a fenced block, says to "end with exactly this and nothing after it", says "Never start the build yourself", and has an edited spec's changes said "before the offer"
- PROOF-4 (RULE-4): The spec skill, counted line by line, is at most 210 lines
- PROOF-28 (RULE-4): A copy of the spec skill lengthened with prose to exactly 210 lines is accepted, with nothing reported
- PROOF-5 (RULE-5): The spec skill says, in one sentence, "Write `> Scope:` on every spec you create", naming "the files the requirement touches" and "the paths `purlin:build` will create", and its numbered step that writes the metadata names `> Scope:`
- PROOF-30 (RULE-9): The spec skill says, in one sentence, that of "A spec that names no files" "every run includes it", and "at the gate `signed` its rules cannot be signed and no tag is written"
- PROOF-6 (RULE-6): In the spec skill's numbered procedure, the step "Print each rule with its proofs under it and ask whether to change any" comes before the step "Save the spec when the person is satisfied"
- PROOF-36 (RULE-10): The spec skill says, in one sentence, to draft every proof against `references/spec_quality_guide.md`, "Writing proofs", and that a good proof holds "at least one failure case"
- PROOF-7 (RULE-7): The spec skill says, in one sentence, "Write each proof as one case", "one starting situation and one action", "in at most 60 words", "a refusal or a boundary as a proof of its own" and the guide's "One proof, one case"
- PROOF-40 (RULE-11): The quality guide has a section headed `One proof, one case` that says "one starting situation, one action", "at most 60 words" and "A refusal or a boundary is a case of its own"
- PROOF-42 (RULE-13): The spec skill's section `Ids` says ``Write that number into `> Highest-Rule:`, adding the line after the spec's other `>` lines where it is missing``
- PROOF-43 (RULE-14): The spec skill's first procedure step says ``Call `sync_status` with `project_root` set to the project root, the top folder of the git checkout``
- PROOF-44 (RULE-15): The spec skill's intake table has a row, each saying what to do, for each of `One sentence`, `A product description or a ticket`, `Pasted acceptance criteria` and `A screenshot`
- PROOF-45 (RULE-16): The spec skill's intake table has the row `An existing spec plus a change`, whose second cell reads `Edit in place. Never renumber`
- PROOF-46 (RULE-17): The spec skill's section `After a merge conflict` says to keep both rules, give the incoming one the next free number, and move its test markers and its signature filenames with it
- PROOF-47 (RULE-18): The spec skill's section `After a merge conflict` says `Two branches that advanced the same anchor pin resolve to the newer sha.`
- PROOF-48 (RULE-19): The guide's section `Written for a person who cannot read code` says a proof may name a function or class the library exports and an error type a caller gets back, with the poor example `_split_fields` and the good example `parse_line` raising `LineTooShort`
- PROOF-49 (RULE-20): The guide's section `One proof, one case` says `One proof may name a list of like inputs that share one action and one kind of result`, with the example of `0`, `-1` and `-0.5` refused with `Amount must be positive`
- PROOF-50 (RULE-21): The guide's `When a rule is stuck` table has a row whose word cell holds `not run` and `<System>: no run yet`, and whose fix says ``Run `purlin:test --remote`, whose runner file names that system``
- PROOF-51 (RULE-22): The spec skill's section `When you are done`, read across its line breaks, says to commit the file with the `spec(<name>):` prefix and then to end with the closing line `Spec saved: <name>. Next: purlin:build <name>`
