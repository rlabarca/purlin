# Feature: skill_audit

> Description: What `skills/audit/SKILL.md` must say. An audit runs the tests, the deliberate
>   breaks where mutation testing is on and the AI audit, reports how good the tests are and
>   writes the audit into the evidence, so its text decides what a reader expects of it and
>   which file the audit they are waiting for lands in.
> Scope: skills/audit/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/audit/SKILL.md` opens with a frontmatter block whose `name` is `audit` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:audit` that states its purpose
- RULE-2: The skill runs the run script by its path under the plugin root, `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, with `--audit` on the same line, and states that a remote runner runs the same script in an arm of its own that nobody runs by hand
- RULE-3: The last section of `skills/audit/SKILL.md` names the next step as the first line of `Left to do`, with a `→` directive to run the command it names, and lets `Nothing left to do.` through as the one outcome that gives no `→` directive
- RULE-4: The whole of `skills/audit/SKILL.md` is at most 105 lines
- RULE-5: The skill states which evidence counts under which gate, naming both folders: a `ci` file and a `local` file each count under `passed`, `strong` and `signed`
- RULE-6: The skill states that under `passed` the run reads the rules with the AI audit and measures no strength, that under `strong` and `signed` it runs the breaks where mutation testing is on, that with `--commit` it ends on the evidence commit `purlin: evidence at <sha7>`, that it prints one line of its own, `AI audit: <n> rules read, <s> strong, <w> weak.`, and ends on the summary and `Left to do`, that an audit cannot make a signature appear, so a rule waiting on one does not set its exit code, and that evidence either source wrote counts at every gate
- RULE-7: The skill states that the run writes the audit into `.purlin/evidence/local/<feature>.json`, that a file keeps the newest section per operating system and the newest audit entry per rule, and that `--remote` belongs to `purlin:test`

## Proof

- PROOF-1 (RULE-1): A reader of the audit skill finds it opens with a frontmatter block between two `---` lines, carrying `name: audit` and a `description:` whose value sits whole on that same line, neither empty nor opening a `>` or `|` block
- PROOF-17 (RULE-1): A reader of the command reference, `references/purlin_commands.md`, finds a table headed `Command` and `Purpose` with a row whose first cell is the `purlin:audit` command and whose second cell states its purpose
- PROOF-18 (RULE-1): A copy of the audit skill with its `name: audit` line deleted is reported as naming no skill where `audit` is expected
- PROOF-19 (RULE-1): A copy of the audit skill whose `description:` line is left empty is reported as carrying no one-line description
- PROOF-20 (RULE-1): A copy of the audit skill whose `description:` line is left empty, with its text moved to an indented line below it, is reported as carrying no one-line description
- PROOF-21 (RULE-1): A copy of the audit skill whose description is written as a `|` block, its text on the indented line below, is reported as carrying no one-line description
- PROOF-22 (RULE-1): A copy of the audit skill whose description is written as a `>-` block, its text on the indented line below, is reported as carrying no one-line description
- PROOF-23 (RULE-1): A copy of the audit skill whose description runs on to a second, indented line reading `and a second line` is reported as carrying no one-line description
- PROOF-24 (RULE-1): A copy of the command reference with its `purlin:audit` row deleted is reported as carrying no row for `purlin:audit`
- PROOF-25 (RULE-1): A copy of the command reference whose `purlin:audit` row has its purpose cell emptied is reported as carrying no row for `purlin:audit`
- PROOF-2 (RULE-2): A reader of the audit skill finds one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--audit`
- PROOF-26 (RULE-2): A reader of the audit skill finds one sentence, its line wrapping ignored, carrying both `A remote runner runs the same script in an arm of its own` and `you never run it by hand`
- PROOF-27 (RULE-2): A copy of the audit skill with `--audit` moved to the line below the script's path is reported as having no single line that carries both
- PROOF-28 (RULE-2): A copy of the audit skill with `; you never run it by hand` deleted is reported as having no sentence carrying both runner phrases
- PROOF-29 (RULE-2): A copy of the audit skill with `you never run it by hand` split off into a sentence of its own, `Then you never run it by hand.`, is reported as having no sentence carrying both runner phrases
- PROOF-3 (RULE-3): A reader of the audit skill finds its last section headed as the next step, naming ``the first line of `Left to do` ``, with two outcomes: `Left to do:`, which gives a `→` directive, and `Nothing left to do.`, the one outcome that gives none
- PROOF-8 (RULE-3): A copy of the audit skill with its closing section deleted is reported as closing with the section before it, `Step 5: retention`, which does not name the next step
- PROOF-9 (RULE-3): A copy of the audit skill with the `→` taken out of the `Left to do:` outcome is reported as having a closing outcome that gives no `→` directive
- PROOF-10 (RULE-3): A copy of the audit skill with the `Nothing left to do.` outcome deleted is reported as not naming `Nothing left to do.` in its closing section
- PROOF-30 (RULE-3): A copy of the audit skill whose closing section no longer says ``the first line of `Left to do` `` is the next step is reported as a closing section that does not name those words
- PROOF-4 (RULE-4): The audit skill, its lines counted, is at most 105 lines long
- PROOF-31 (RULE-4): A copy of the audit skill made exactly 105 lines long is not reported
- PROOF-32 (RULE-4): A copy of the audit skill made 106 lines long is reported as 106 lines long against a ceiling of 105
- PROOF-5 (RULE-5): A reader of the audit skill finds a table headed `Source` with a `ci` row and a `local` row, the last cell of each naming `passed`, `strong` and `signed`
- PROOF-33 (RULE-5): A reader of the audit skill finds both evidence folders named, `.purlin/evidence/ci/` and `.purlin/evidence/local/`
- PROOF-34 (RULE-5): A copy of the audit skill with `strong` dropped from the `local` row is reported as a local row that does not count under `strong`
- PROOF-35 (RULE-5): A copy of the audit skill with the `ci` row deleted is reported as a source table with no `ci` row
- PROOF-36 (RULE-5): A copy of the audit skill with every `.purlin/evidence/ci/` changed to `.purlin/evidence/remote/` is reported as not naming `.purlin/evidence/ci/`
- PROOF-6 (RULE-6): A reader of the audit skill finds a table headed `Gate` whose `passed` row names `the AI audit` and says test strength is `not measured`
- PROOF-37 (RULE-6): A reader of the audit skill finds, in the table headed `Gate`, a `strong` row that names the `breaks` and the `minimum` a rule's strength is held to
- PROOF-38 (RULE-6): A reader of the audit skill finds, in the table headed `Gate`, a `signed` row reading "The same as `strong`" and saying evidence either source wrote `counts here too`
- PROOF-11 (RULE-6): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying `AI audit: <n> rules read, <s> strong, <w> weak.` and ``ends on the status table, the summary and `Left to do` ``
- PROOF-12 (RULE-6): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying ``you add `--commit` `` and ``the subject `purlin: evidence at <sha7>` ``
- PROOF-39 (RULE-6): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying `An audit cannot make a signature appear` and `a rule waiting on one does not set the code`
- PROOF-13 (RULE-6): A copy of the audit skill whose `passed` row reads `Runs the tests, and no breaks` is reported as a row that does not say the run reads the rules with the AI audit
- PROOF-40 (RULE-6): A copy of the audit skill whose `passed` row has `test strength is not measured, and ` deleted is reported as a row that does not name `not measured`
- PROOF-41 (RULE-6): A copy of the audit skill whose `strong` row has `Runs the breaks too where mutation testing is on; ` deleted is reported as a row that does not name `breaks`
- PROOF-14 (RULE-6): A copy of the audit skill whose `signed` row reads `Runs the tests.` is reported as a row that does not run what the `strong` row runs
- PROOF-42 (RULE-6): A copy of the audit skill whose `signed` row has `Evidence either source wrote counts here too` deleted is reported as a row that does not say `counts here too`
- PROOF-15 (RULE-6): A copy of the audit skill with ``and ends on the status table, the summary and `Left to do` `` deleted is reported as having no sentence carrying the audit's line and its ending
- PROOF-43 (RULE-6): A copy of the audit skill whose `--commit` sentence gives the subject as `purlin: evidence for <sha7>` is reported as having no sentence carrying `--commit` and ``the subject `purlin: evidence at <sha7>` ``
- PROOF-16 (RULE-6): A copy of the audit skill with `, so a rule waiting on one does not set the code` deleted is reported as having no sentence saying an audit cannot make a signature appear
- PROOF-7 (RULE-7): A reader of the audit skill finds, its line wrapping ignored, the words ``into `.purlin/evidence/local/<feature>.json` ``
- PROOF-44 (RULE-7): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying both `A file keeps the newest section per operating system` and `the newest audit entry per rule`
- PROOF-45 (RULE-7): A reader of the audit skill finds, its line wrapping ignored, the words ``` `--remote` belongs to `purlin:test --remote` ```
- PROOF-46 (RULE-7): A copy of the audit skill with its retention sentence deleted is reported as not carrying `the newest section per operating system`
- PROOF-47 (RULE-7): A copy of the audit skill with ` and the newest audit entry per rule` deleted is reported as having no sentence carrying both retention phrases
- PROOF-48 (RULE-7): A copy of the audit skill that writes the audit into `.purlin/evidence/ci/<feature>.json` is reported as not carrying the words naming `.purlin/evidence/local/<feature>.json`
- PROOF-49 (RULE-7): A copy of the audit skill reading ``so use `purlin:test --remote` `` in place of ``so `--remote` belongs to `purlin:test --remote` `` is reported as not carrying the words that give `--remote` to `purlin:test`
