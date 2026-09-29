# Feature: skill_audit

> Description: What `skills/audit/SKILL.md` must say. An audit runs the tests, the deliberate
>   breaks where mutation testing is on and the AI audit, reports how good the tests are and
>   writes the audit into the evidence, so its text decides what a reader expects of it and
>   which file the audit they are waiting for lands in.
> Scope: skills/audit/SKILL.md
> Stack: markdown, Claude Code skill definition

## Rules

- RULE-1: `skills/audit/SKILL.md` opens with a frontmatter block whose `name` is `audit` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:audit`
- RULE-2: The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--audit`, and states that a remote runner runs the same script in an arm of its own that nobody runs by hand
- RULE-3: The last section of `skills/audit/SKILL.md` names the next step as the first line of `Left to do`, with a `→` directive to run the command it names, and lets `Nothing left to do.` through as the one outcome that names no command
- RULE-4: The whole of `skills/audit/SKILL.md` is at most 105 lines
- RULE-5: The skill states which evidence counts under which gate, naming both folders: a `ci` file and a `local` file each count under `passed`, `strong` and `signed`
- RULE-6: The skill states that under `passed` the run reads the rules with the AI audit and measures no strength, that under `strong` and `signed` it runs the breaks where mutation testing is on, that with `--commit` it ends on the evidence commit `purlin: evidence at <sha7>`, that it prints one line of its own, `AI audit: <n> rules read, <s> strong, <w> weak.`, and ends on the summary and `Left to do`, that an audit cannot make a signature appear, so a rule waiting on one does not set its exit code, and that evidence either source wrote counts at every gate
- RULE-7: The skill states that the run writes the audit into `.purlin/evidence/local/<feature>.json`, that a file keeps the newest section per operating system and the newest audit entry per rule, and that `--remote` belongs to `purlin:test`

## Proof

- PROOF-1 (RULE-1): A reader of the audit skill finds that it opens with a frontmatter block between two `---` lines, carrying `name: audit` and a `description:` whose value sits whole on that same line, not empty and not opening a `>` or `|` block; the command reference, `references/purlin_commands.md`, carries a table row whose first cell is the `purlin:audit` command. With the `name:` line deleted, the check reports that it found no name where `audit` is expected; with the description left empty, left empty with text on the next line, written as a `|` block, or run onto a second line, it reports that the frontmatter carries no one-line description; with the `purlin:audit` row removed from the command reference, it reports that the reference carries no row for `purlin:audit`
- PROOF-2 (RULE-2): A reader of the audit skill finds one line that runs `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"` with `--audit`, and one sentence, its line wrapping ignored, that carries both `A remote runner runs the same script in an arm of its own` and `you never run it by hand`. With `--audit` moved off the line that runs the script, the check reports that no single line carries both; with `you never run it by hand` deleted, or split off into a sentence of its own, it reports that no sentence carries both phrases
- PROOF-3 (RULE-3): A reader of the audit skill finds its last section headed as the next step, holding two outcomes: `Left to do:`, whose `→ Run:` directive runs the command on the first line of `Left to do`, and `Nothing left to do.`, which names no command
- PROOF-4 (RULE-4): Read `skills/audit/SKILL.md` and count its lines; verify the count is at most 105. Appending prose until the file passes 105 lines fails, and the failure reports the count it found beside the ceiling
- PROOF-5 (RULE-5): A reader of the audit skill finds a table headed `Source` with a `ci` row and a `local` row, the last cell of each naming `passed`, `strong` and `signed`, and finds both folders named, `.purlin/evidence/ci/` and `.purlin/evidence/local/`. With `strong` dropped from the `local` row, the check reports that the local row does not count under `strong`; with the `ci` row removed, it reports that the source table has no `ci` row
- PROOF-6 (RULE-6): A reader of the audit skill finds a table headed `Gate` whose `passed` row names `the AI audit` and `not measured`, whose `strong` row names the `breaks` and the `minimum`, and whose `signed` row reads "The same as `strong`" and `counts here too`
- PROOF-7 (RULE-7): A reader of the audit skill finds, with its line wrapping ignored, the words ``into `.purlin/evidence/local/<feature>.json` ``, one sentence keeping both `the newest section per operating system` and `the newest audit entry per rule`, and the words ``` `--remote` belongs to `purlin:test --remote` ```. With the retention sentence deleted, the check reports `the newest section per operating system` missing; with `the newest audit entry per rule` deleted, it reports no sentence carrying both; with the file the run writes the audit into changed to `.purlin/evidence/ci/<feature>.json`, it reports the words naming the local file missing; with the `--remote` sentence reworded so it no longer gives `--remote` to `purlin:test`, it reports those words missing
- PROOF-8 (RULE-3): A copy of the audit skill with its closing section deleted is reported as closing with the section before it, `Step 5: retention`, which does not name the next step
- PROOF-9 (RULE-3): A copy of the audit skill with the `→` taken out of the `Left to do:` outcome is reported as having a closing outcome that gives no `→` directive
- PROOF-10 (RULE-3): A copy of the audit skill with the `Nothing left to do.` outcome deleted is reported as not naming `Nothing left to do.` in its closing section
- PROOF-11 (RULE-6): A reader of the audit skill finds, its line wrapping ignored, one sentence carrying `AI audit: <n> rules read, <s> strong, <w> weak.` and ``ends on the status table, the summary and `Left to do` ``
- PROOF-12 (RULE-6): A reader of the audit skill finds one sentence naming `--commit` and the subject `purlin: evidence at <sha7>`, and one saying `An audit cannot make a signature appear` and `a rule waiting on one does not set the code`
- PROOF-13 (RULE-6): A copy of the audit skill whose `passed` row reads `Runs the tests, and no breaks` is reported as a row that does not say the run reads the rules with the AI audit
- PROOF-14 (RULE-6): A copy of the audit skill whose `signed` row reads `Runs the tests.` is reported as a row that does not run what the `strong` row runs
- PROOF-15 (RULE-6): A copy of the audit skill with the words ``and ends on the status table, the summary and `Left to do` `` deleted is reported as having no sentence carrying the audit's line and its ending
- PROOF-16 (RULE-6): A copy of the audit skill with `, so a rule waiting on one does not set the code` deleted is reported as having no sentence saying an audit cannot make a signature appear
