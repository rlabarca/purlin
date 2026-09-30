# Feature: skill_audit

> Description: What `skills/audit/SKILL.md` must say. An audit runs the tests, the deliberate
>   breaks where mutation testing is on and the AI audit, reports how good the tests are and
>   writes the audit into the evidence, so its text decides what a reader expects of it and
>   which file the audit they are waiting for lands in.
> Scope: skills/audit/SKILL.md
> Stack: markdown, Claude Code skill definition
> Highest-Rule: 24
> Highest-Proof: 51

## Rules

- RULE-1: `skills/audit/SKILL.md` opens with a frontmatter block whose `name` is `audit` and whose `description` is one non-empty line
- RULE-2: The skill tells the agent to run the run script by its path under the plugin root, `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, with `--audit` on the same line
- RULE-3: The last section of `skills/audit/SKILL.md` tells the agent to name the next step as the first line of `Left to do`, with a `→` directive to run the command it names, and lets `Nothing left to do.` through as the one outcome that gives no `→` directive
- RULE-4: The whole of `skills/audit/SKILL.md` is at most 105 lines
- RULE-5: The skill tells the agent that a `ci` file and a `local` file each count under `passed`, `strong` and `signed`
- RULE-6: The skill tells the agent that under `passed` the run reads the rules with the AI audit and measures no strength, that under `strong` and `signed` it runs the breaks where mutation testing is on, and that evidence either source wrote counts at `signed`
- RULE-7: The skill tells the agent that the run writes the audit into `.purlin/evidence/local/<feature>.json`
- RULE-8: The skill tells the agent that the run prints one line of its own, `AI audit: <n> rules read, <s> strong, <w> weak.`, and ends on the status table, the summary and `Left to do`, and that with `--commit` it ends on the evidence commit `purlin: evidence at <sha7>`
- RULE-9: The skill tells the agent that an audit cannot make a signature appear, so a rule waiting on one does not set its exit code
- RULE-10: The skill tells the agent that `purlin:audit --arm-timeout <seconds>` gives the breaking tool longer per feature, and to pass `--arm-timeout <seconds>` on to the run script when the person gave it
- RULE-11: `references/purlin_commands.md` carries a row for `purlin:audit` that states its purpose
- RULE-12: The skill tells the agent that a remote runner runs the same script in an arm of its own that nobody runs by hand
- RULE-13: The skill tells the agent the two evidence folders, `.purlin/evidence/ci/` and `.purlin/evidence/local/`
- RULE-14: The skill tells the agent that a file keeps the newest section per operating system and the newest audit entry per rule
- RULE-15: The skill tells the agent that `--remote` belongs to `purlin:test`
- RULE-24: The skill tells the agent to call `sync_status` with `project_root` set to the project root, the top folder of the git checkout

## Proof

- PROOF-1 (RULE-1): A reader of the audit skill finds it opens with a frontmatter block between two `---` lines, carrying `name: audit` and a `description:` whose value sits whole on that same line, neither empty nor opening a `>` or `|` block
- PROOF-17 (RULE-11): A reader of the command reference, `references/purlin_commands.md`, finds a table headed `Command` and `Purpose` with a row whose first cell is the `purlin:audit` command and whose second cell states its purpose
- PROOF-2 (RULE-2): A reader of the audit skill finds one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--audit`
- PROOF-26 (RULE-12): A reader of the audit skill finds one sentence, its line wrapping ignored, carrying both `A remote runner runs the same script in an arm of its own` and `you never run it by hand`
- PROOF-3 (RULE-3): A reader of the audit skill finds its last section headed as the next step, naming ``the first line of `Left to do` ``, with two outcomes: `Left to do:`, which gives a `→` directive, and `Nothing left to do.`, the one outcome that gives none
- PROOF-4 (RULE-4): The audit skill, its lines counted, is at most 105 lines long
- PROOF-31 (RULE-4): A copy of the audit skill made exactly 105 lines long is not reported
- PROOF-32 (RULE-4): A copy of the audit skill made 106 lines long is reported as 106 lines long against a ceiling of 105
- PROOF-5 (RULE-5): A reader of the audit skill finds a table headed `Source` with a `ci` row and a `local` row, the last cell of each naming `passed`, `strong` and `signed`
- PROOF-33 (RULE-13): A reader of the audit skill finds both evidence folders named, `.purlin/evidence/ci/` and `.purlin/evidence/local/`
- PROOF-6 (RULE-6): A reader of the audit skill finds a table headed `Gate` whose `passed` row names `the AI audit` and says test strength is `not measured`
- PROOF-37 (RULE-6): A reader of the audit skill finds, in the table headed `Gate`, a `strong` row that names the `breaks` and the `minimum` a rule's strength is held to
- PROOF-38 (RULE-6): A reader of the audit skill finds, in the table headed `Gate`, a `signed` row reading "The same as `strong`" and saying evidence either source wrote `counts here too`
- PROOF-11 (RULE-8): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying `AI audit: <n> rules read, <s> strong, <w> weak.` and ``ends on the status table, the summary and `Left to do` ``
- PROOF-12 (RULE-8): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying ``you add `--commit` `` and ``the subject `purlin: evidence at <sha7>` ``
- PROOF-39 (RULE-9): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying `An audit cannot make a signature appear` and `a rule waiting on one does not set the code`
- PROOF-50 (RULE-10): A reader of the audit skill finds `purlin:audit --arm-timeout <seconds>  Give the breaking tool longer per feature` as a line of its usage block, and, in the step that runs the script, `--arm-timeout <seconds>` followed by `when the person gave it`
- PROOF-7 (RULE-7): A reader of the audit skill finds, its line wrapping ignored, the words ``into `.purlin/evidence/local/<feature>.json` ``
- PROOF-44 (RULE-14): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying both `A file keeps the newest section per operating system` and `the newest audit entry per rule`
- PROOF-45 (RULE-15): A reader of the audit skill finds, its line wrapping ignored, the words ``` `--remote` belongs to `purlin:test --remote` ```
- PROOF-51 (RULE-24): A reader of the audit skill finds the first `sync_status` followed, its line wrapping ignored, by ``with `project_root` set to the project root, the top folder of the git checkout``
