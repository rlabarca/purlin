# One proof, one case: what the lanes brought back

Run on 2026-09-29. 33 lanes, one per spec or group, each owning its spec and its test files; one agent on CLAUDE.md; one sorting the rules for Windows. All merged into main.

## The counts

| Lane | Proofs before | Proofs after | Over 60 words | Tests before | Tests after |
|---|---|---|---|---|---|
| `group_states` | 145 | 177 | 0 | 131 | 177 |
| `purlin_report` | 103 | 149 | 0 | 106 | 155 |
| `run_script` | 97 | 160 | 0 | 135 | 160 |
| `signatures` | 85 | 105 | 0 | 89 | 105 |
| `scaffold` | 81 | 107 | 0 | 94 | 109 |
| `update` | 62 | 109 | 0 | 97 | 113 |
| `evidence_writer` | 54 | 74 | 0 | 56 | 74 |
| `reports` | 39 | 93 | 0 | 43 | 97 |
| `ai_audit` | 38 | 69 | 0 | 40 | 69 |
| `host` | 35 | 87 | 0 | 92 | 94 |
| `drift` | 33 | 49 | 0 | 33 | 49 |
| `evidence` | 31 | 64 | 0 | 33 | 64 |
| `package` | 29 | 35 | 0 | 30 | 35 |
| `mutation` | 22 | 67 | 0 | 83 | 81 |
| `skill_sign` | 21 | 42 | 0 | 23 | 42 |
| `upstream` | 18 | 31 | 0 | 27 | 31 |
| `skill_test` | 17 | 43 | 0 | 19 | 43 |
| `specs` | 16 | 39 | 0 | 28 | 52 |
| `skill_audit` | 16 | 49 | 0 | 19 | 49 |
| `skill_init` | 15 | 43 | 0 | 17 | 43 |
| `security_no_dangerous_patterns` | 13 | 48 | 0 | 17 | 48 |
| `skill_export` | 13 | 33 | 0 | 15 | 33 |
| `schema_spec_format` | 12 | 44 | 0 | 17 | 44 |
| `purlin_agent` | 12 | 43 | 0 | 17 | 43 |
| `skill_build` | 12 | 34 | 0 | 16 | 34 |
| `skill_spec_from_code` | 12 | 32 | 0 | 15 | 32 |
| `config_engine` | 11 | 27 | 0 | 14 | 28 |
| `server` | 11 | 25 | 0 | 14 | 29 |
| `skill_status` | 11 | 34 | 0 | 10 | 34 |
| `skill_spec` | 9 | 37 | 0 | 14 | 37 |
| `purlin_version` | 8 | 34 | 0 | 9 | 34 |
| `skill_anchor` | 8 | 32 | 0 | 11 | 32 |
| `skill_drift` | 4 | 31 | 0 | 7 | 31 |
| **Total** | 1093 | 2046 | 0 | | |

The dashboard's lane was followed by a second pass for decisions 85 to 93; after it `purlin_report` holds 160 proofs.

## Where the product does not do what its rule says

- **`run_script` Decision 69 (the advice fits the cause) and the spec_quality_guide row for `partial`; the summary belongs to another lane's spec, and no rule of run_script covers the Left to do wording.** The rule says: Decision 69 says the advice fits the cause. The quality guide says that for a rule reading `partial`, you fix the system that failed or run `purlin:test --remote` for the one that has not run. The product does: A spec has PROOF-1 passing here and PROOF-2 tagged @env(windows) on a Mac, with PROOF-2's test either skipped or absent. `--all --test` exits 0 but prints `feat  1  2  0 of 1 · 1 partial`, `1 rule. 0 pass their tests.` and `  1 rule to fix: purlin:build`. It sends you to build, although nothing is broken and the only step left is a Windows run. The run_script section of the evidence also reads `"RULE-1": "not run"`, while the cell for this machine reads `passed`. No assertion of mine touches the summary, so none was taken out.
- **`evidence_writer` evidence_writer RULE-2, read with decision 69 (a run names each rule that fails or has no test, and its advice fits the cause).** The rule says: Decision 69: "A run names each rule that fails or has no test, and its advice fits the cause: a comment to correct, settings to restore, or `purlin:build`." RULE-2 says a rule reads `passed` "where every test tied to every proof that could run here ran and passed" and `no test` "where no test is tied to any of them". It does not cover a rule where some proofs have a test and others do not. The product does: Setup: a rule has two proofs; PROOF-1's test passes and PROOF-2 has no test. A `--all --test` run writes `"rules": {"RULE-1": "not run"}` and names no rule. The status table shows `feat  1  2 · 1 no test  0 of 1`. The ending says `1 rule. 0 pass their tests.` then `Left to do:` and `  1 rule to test: purlin:test`. Running purlin:test again changes nothing; what clears the rule is `purlin:build` writing PROOF-2's test. I changed neither the rule nor the product and added no assertion for this case. See the first question.
- **`reports` reports RULE-8.** The rule says: A `trx` report is read result by result: `Passed` passes, `Failed`, `Error`, `Timeout` and `Aborted` fail, and any other outcome is skipped. references/formats/marker_format.md says the same. The product does: scripts/run/reports.py `_TRX_PASS = ('passed', 'passedbutrunaborted', 'warning', 'completed')` reads the outcomes `PassedButRunAborted`, `Warning` and `Completed` as `pass`, not `skip`. No assertion exposes this (none was in the tests), so nothing was taken out, and neither the rule nor the code was changed.
- **`ai_audit` RULE-8 and RULE-14, against decision 93 (added to main after this branch was cut).** The rule says: Decision 93: `n/a` is printed nowhere, on the dashboard or in the terminal; the audit's report says nothing of strength where none was measured; the model is told `test strength: not measured`, in words. The product does: With no strength measured, `ai_audit.py --feature login --rule RULE-2` prints `Test strength: n/a   minimum 70`, and the prompt sent to the model carries `Test strength: n/a (minimum 70)`. PROOF-63 claims the printed line as the product prints it today. It has to be rewritten when the product change for decision 93 lands.
- **`drift` RULE-10: The engineer view names every pinned anchor that is not current.** The rule says: Every pinned anchor that is not current is named: behind, unpinned or error. The product does: Drift checks an anchor only when its source looks like a git repository: it ends in `.git`, starts with `git@`, holds `github.com` or `gitlab.com`, or is a local path. Any other source gets no row at all, even when it is pinned and behind. Checked directly: the source `https://dev.azure.com/acme/p/_git/policies` pinned to `abc1234` gives no result and an empty engineer list. An anchor kept on Azure DevOps, a host Purlin supports, never shows as behind. No assertion exposes this, so none was taken out.
- **`mutation` mutation RULE-10 (as reworded: 'and by its file, so a test of the same name in a different test file is not that test').** The rule says: A test in the Stryker report is the rule's test only when it is in the same test file. A test of the same name in a different test file is not that test. The product does: The report's file and the rule's file count as the same file when either path ends with the other, compared character by character. So a report's test `locks the account` in `e2e/test/login.test.js` is credited to the rule whose test of that name is in `test/login.test.js` (the rule read 1 caught, 100). A test in `xlogin.test.js` is also taken for one in `login.test.js`. An empty file name on either side matches every file. Today no reader sees a rule's own number (see the first question), so nothing a person reads is wrong yet. No assertion exposing this is in the tests.
- **`upstream` upstream RULE-15.** The rule says: One run reaches each distinct source once, however many anchors are pinned to it The product does: `sync --check` reaches the source once: one `git ls-remote` for two anchors, which PROOF-15 shows. A plain `sync` with two anchors from one repository, both behind, reaches it three times: `git ls-remote` once, then a separate `git clone` for each anchor. My probe recorded [['git', 'ls-remote', '--end-of-options'], ['git', 'clone', '--quiet'], ['git', 'clone', '--quiet']]. The rule and the product were left as they are. The proof and its test claim only the `--check` case, which does hold.
- **`schema_spec_format` No rule covers a reused rule id. The closest is schema_spec_format RULE-2 ('never reuses one'), read together with decision 79 (the summary and Left to do).** The rule says: A spec's rule ids are never reused, and the terminal's summary and its Left to do count the same rules. The product does: In a spec with `RULE-2`, `RULE-1`, `RULE-1`, the status table and summary say `2 rules`, while `Left to do` says `3 rules to write a test for`. The dashboard data lists `RULE-1` twice, both with the second line's text. With a doubled proof id, the later line replaces the earlier one, but the earlier rule still lists that id as its proof. Nothing is reported in either case. No assertion was taken out; nothing tests this today.
- **`skill_build` skill_build RULE-5.** The rule says: The body's Changeset section maps every rule the build addressed as `RULE-N → file:line`, as `references/commit_conventions.md` renders it The product does: The one example of a build commit in references/commit_conventions.md, under "The build commit body", has the subject `feat(auth_login): implement RULE-1, RULE-2, RULE-3`, but its changeset maps only `RULE-1 → src/auth.py:34` and `RULE-2 → src/auth.py:71`. RULE-3 is never mapped, so the rendering the skill tells the agent to follow breaks the rule. The PROOF-37 test checks the example's prefix, the form of each mapped line and its Decisions: and Review: sections. It leaves out the check that every rule the subject names is mapped, because that check would fail on this.
- **`skill_status` Decisions 85 and 92 (no rule of skill_status quotes this line; skills/status/SKILL.md belongs to whoever edits the skill).** The rule says: Decision 85: 'The `Left to do` list leaves the dashboard.' Decision 92: 'The dashboard carries no summary sentence ... The terminal keeps it, since it has no boxes.' The product does: skills/status/SKILL.md, Step 3, line 51, still reads: 'The tool ends on one sentence and `Left to do`, the words every surface ends on:'. The dashboard ends on neither.
- **`skill_drift` Decision 65 ("Every ending of a command names a command to run next, also where the work is complete"), decision 76 (only a finished project's `Nothing left to do.` at the gates `passed` and `strong` names no command) and references/writing_style.md ("A command's ending names the command to run next, except `Nothing left to do.`").** The rule says: Every ending of the drift skill names a command to run next. The product does: The last row of the drift skill's closing table, `| Only the first line, or only `No rule was added, ...` | `→ Nothing changed that the specs, the tests or the signatures need.` |`, names no command. The shared check lets it through because it carries a `→`, and no assertion of mine depends on it. One fix is `→ Run: purlin:status`, which changes skills/drift/SKILL.md, outside this lane.
- **`skill_drift` skill_drift RULE-2 as it stood ("it invents no line the tool does not return") and references/drift_criteria.md, whose anchor line reads `anchor <name> is behind its source (now <sha7>). Run: purlin:anchor sync <name>.`.** The rule says: The lines the skill shows are lines the drift tool returns, and the anchor line carries a 7-character sha. The product does: The skill's example `eng` view shows `anchor proof_common is behind its source (now 3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d). Run: purlin:anchor sync proof_common.`, with a 40-character sha. The tool cuts the sha to its first 7 characters before building the line, so it never prints this form. No test asserts on it. The fix is to change the example in skills/drift/SKILL.md to 7 characters, outside this lane.

## Questions for the owner

### 1. From `group_states`

**What it is for.** Some rules say a behaviour holds whatever the project's gate is set to, for example "a result from a person's own machine counts at every gate". Their proofs show this by repeating the same check at each of the three gates in one proof.

**The question.** Should a proof that repeats the same check at each of the three gates stay one proof, or become three, one per gate? Twelve proofs are like this, including states PROOF-5, 6, 47, 66, 73, 76, 106, 107, 109 and 110.

**Options.** 1) Keep one proof per repeated check. The spec stays shorter, and a failure names the gate in its message. 2) One proof per gate. About 24 more lines, and a failure names the gate by the proof's own number. 3) Keep only the gate where the behaviour could differ, for example `signed` alone for a signature question, and drop the repeats.

### 2. From `group_states`

**What it is for.** Three rules of the states spec all say that a passing test result counts, whether it came from a person's own machine or a remote runner, and whether it is committed or not. RULE-3 says when a rule reads passed, RULE-4 says both sources count at every gate, and RULE-5 says the same again, with the committed-or-not detail and that leftover test reports are not evidence. The quality guide says two rules that always pass or fail together should be one.

**The question.** Should RULE-4 and RULE-5 become one rule?

**Options.** 1) Keep both as they are. Nothing changes for a reader or a signature. 2) Fold RULE-5 into RULE-4 and retire RULE-5. Its proofs move to RULE-4, the spec is one rule shorter, and QA has one fewer rule to read and sign. 3) Keep RULE-5 only for the detail that leftover test reports are not evidence, and move everything else to RULE-4.

### 3. From `purlin_report`

**What it is for.** From the gate strong up, the dashboard has a box counting the rules that have no proof yet. The filter buttons now include one named `To write a proof for`, which carries the same number from the same list of work left.

**The question.** Should the dashboard keep both the `No proof` box and the `To write a proof for` button, when they always show the same number?

**Options.** Keep both: the box sits with the step counts at the top, and the button filters the table (this is how it is built now). Remove the box: the button alone says how many rules need a proof, and the boxes are only the steps reached. Keep the box and make pressing it choose the button: one number, two ways to reach it.

### 4. From `purlin_report`

**What it is for.** When nothing is left to do, the terminal ends on `Nothing left to do.`, and at the gate signed it adds the release step, `Push the tag to release it: git push origin signed/<version>`. The `Left to do` list has left the dashboard, so the page needs somewhere to put that line or nowhere.

**The question.** When nothing is left, should the dashboard show that closing line where the filter buttons would be?

**Options.** Show it where the buttons stand (this is how it is built now): a finished project reads `Nothing left to do.`, and at signed it sees the push command. Show nothing: green boxes say it is finished, and the push command appears only in the terminal. Show it under the summary line instead of above the table.

### 5. From `purlin_report`

**What it is for.** At the gate signed, once every rule is signed and the version has no signed tag yet, the one line left is `the version to tag`, cleared by `purlin:sign`. It counts the version, not a rule, so no rule in the table belongs to it.

**The question.** What should the `To tag` button do, or should there be one?

**Options.** Keep the button; choosing it names `purlin:sign` under the buttons and leaves every rule showing (this is how it is built now). No button for it: show `the version to tag` and its command as a plain line above the table. Treat it like any other button and leave the table empty with a note that no rule is left.

### 6. From `purlin_report`

**What it is for.** Decision 85 gives a rule's row a `FAILED` badge where a test fails. A rule can pass on one operating system and fail on another; the terminal calls that `partial`.

**The question.** Should a rule that passed on one system and failed on another carry `FAILED` on its row?

**Options.** Yes, `FAILED`, because a test did fail somewhere (this is how it is built now). A `PARTIAL` badge instead, so the row says it passed somewhere. No badge, because it has not reached the step; the reason is on the rule's page.

### 7. From `run_script`

**What it is for.** Some rules must also hold on another operating system, such as Windows. On your own machine those proofs cannot run, so the rule waits for a remote run. The list at the end of every run, `Left to do`, is meant to name the next step for each rule.

**The question.** A rule that passes here and only waits for its Windows run is listed today as `1 rule to fix: purlin:build`, as if the code were broken. What should `Left to do` say for it?

**Options.** A) A line of its own, for example `1 rule to run on another system: purlin:test --remote`. The step is named correctly. B) Count it under the existing `to test: purlin:test` line. There is no new wording, but you have to know to add --remote. C) Keep `to fix: purlin:build`. Nothing changes, and the advice stays wrong. D) Count the rule as passed until a remote run shows otherwise, so it leaves `Left to do` altogether. The count is honest only about this machine.

### 8. From `run_script`

**What it is for.** Your rule is that a proof holds one case. Some rules are shown by the same result across many inputs. For example, eight wrong command lines each stop with the same usage line, and seven test tools each get their own suggested command.

**The question.** When several inputs lead to the same kind of result, should each input be its own proof?

**Options.** A) One proof per input. That is what I did: the command-line rule went from 1 proof to 11, the suggested-tool rule from 1 to 7, and the no-model rule from 1 to 6. Each failure names its case, and the specs grow. B) One proof per distinct result. The eight refusals become one proof and the three accepted shapes another. Specs stay short, but a failure names only the group. C) Leave it to whoever writes the proof, with no fixed line. Each lane decides differently.

### 9. From `run_script`

**What it is for.** One rule says the run script's own source carries no emoji, because no Purlin output may show one. Its check looks only at the upper range of characters, where most emoji sit. Symbols like a check mark or a warning sign sit lower and are not caught.

**The question.** What should this rule cover?

**Options.** A) Keep it as it is. It is cheap and catches most emoji, but not all. B) Widen it to every emoji and pictograph symbol, with a stricter check on the same file. C) Widen it to everything Purlin prints, checked across every script. This is closer to your writing rule, and it is a larger test. D) Remove the rule. The writing style already forbids emoji everywhere, and the review of each change holds it.

### 10. From `run_script`

**What it is for.** The setting for how many rules the AI audit reads at once has an allowed range of 1 to 16. When the value is outside it, the run falls back to 4 and prints a warning.

**The question.** The warning prints twice: as the run's first line and again beside the status table. Should it print once?

**Options.** A) Keep both. The first line is seen when the run starts, and the repeat is seen when it ends. B) Print it once, at the start. C) Print it once, beside the status table, where the other settings warnings end up.

### 11. From `signatures`

**What it is for.** Once every rule is signed at the gate signed, running purlin:sign with nothing named writes the release tag. When it cannot, it prints one line saying why and today still reports success (exit 0). The reasons are: changes that are not committed, test results that are not committed, no version stated, a tag of that name already written, or the evidence package could not be committed.

**The question.** When the tag was not written, should purlin:sign still report success?

**Options.** 1) Keep success. The walk finished, and the line is information for the person; a script or CI step cannot tell that no tag was made. 2) Report failure (exit 1) whenever the tag was refused, as decision 85 does for an unknown rule: something expected was not done, and a script can stop on it. 3) Report failure only for reasons the person must fix (uncommitted work or results, no version, package not committed), and success when the tag already exists, since that release is already marked.

### 12. From `signatures`

**What it is for.** When you name a rule that no spec has, purlin:sign prints `login RULE-9 is not a rule any spec has.` It signs the other rules you named and reports failure. Decision 69 says every output should say what to do next. This line names no next step, and it prints before the signing lines rather than at the end.

**The question.** Should the line tell you what to do?

**Options.** 1) Keep it as it is: the rule id you typed is plainly wrong. 2) Add a next step, for example `Check the rule ids with purlin:status.`. 3) List the rules that feature does have, so you can pick the right one. 4) Keep the words but print the line last, just above the summary, so it is not scrolled past.

### 13. From `signatures`

**What it is for.** Two rules cover the same case. One says a rule the spec does not have has nothing a signature could be made over. The other says that naming such a rule to purlin:sign prints that it is not a rule any spec has and signs nothing for it. The first is only visible to a person through the second; its one proof reads an internal answer.

**The question.** Keep both rules, or only the one a person can see?

**Options.** 1) Keep both: the first states where the case is decided, the second what you see. 2) Remove the first and its proof; the second, with its two proofs, covers the case from what you see.

### 14. From `scaffold`

**What it is for.** When you run purlin:init again on a project that is already set up (to raise the gate, for example), it stops before each file it would change and asks `write .purlin/config.json [Y/n]:`. It does this so a second run never quietly overwrites a setting someone already chose. The rule says setup asks the gate question, the mutation question at strong and signed, and nothing else.

**The question.** Should a second run of setup keep asking before it changes each file?

**Options.** 1. Keep asking. The rule is reworded to say that a first run asks only those questions and a later run also asks before each file it changes. 2. Stop asking. A later run changes what it needs without asking, as it already does with --yes, and the rule stays as written. 3. Ask once. A later run lists every file it would change and asks one yes/no question for all of them.

### 15. From `scaffold`

**What it is for.** Two rules make the same promise about a copy of Purlin installed from the marketplace: nothing in the project names the folder the plugin ran from. One checks a project set up at strong; the other checks a new project set up at passed. Both tests pass.

**The question.** Should the promise live in one rule only?

**Options.** 1. Keep both as they are. 2. Remove the clause from the rule about each language being set up the same way, and remove its check at passed; the other rule keeps the promise. 3. Keep the check at passed but file it under the other rule, so that one rule holds both starting situations.

### 16. From `scaffold`

**What it is for.** Every rule about walking the three gates (test and commit, audit, runner runs, sign, tag) is now shown step by step on a Python project. A second, older check walks a TypeScript project and a C# project through the same three gates. It adds about 30 seconds to the full test run, but because it is one check covering everything, no rule is tied to it and a failure does not say which step broke.

**The question.** What should happen to the TypeScript and C# walk through the gates?

**Options.** 1. Keep it as an extra safety check that no rule is tied to. 2. Say in the rule that the walk holds for each language, and give each language's gate steps their own proofs and checks, which is about 16 more proofs. 3. Remove it: the Python walk shows the gates, and TypeScript and C# are already shown to be set up and to run their tests.

### 17. From `update`

**What it is for.** When a project from 0.9.5 is upgraded, its settings file is rewritten. One rule says the rewritten file holds exactly seven settings. A second rule says, on its own, that the old dashboard on/off switch is not carried over. The first rule already guarantees that, because the switch is not one of the seven.

**The question.** Should the dashboard switch keep a rule of its own, or is the seven-settings rule enough?

**Options.** (1) Keep both rules as they are. The switch keeps its own two checks, one for on and one for off, and the second rule repeats what the first already guarantees. (2) Remove the switch's rule and move its two checks under the seven-settings rule. One fewer rule to audit and sign; the same things are still checked. (3) Remove the switch's rule and its two checks. The seven-settings check alone covers it; one fewer rule and two fewer checks.

### 18. From `update`

**What it is for.** Setup and the upgrade both ask how far every rule must go: passed, strong or signed. If you type something that is not one of those, setup says so in one line ("not a gate; reading it as passed") and uses the default. The upgrade uses the default without a word, so you may not notice your answer was not taken.

**The question.** Should the upgrade say, as setup does, when your answer is not a gate?

**Options.** (1) Print the same line setup prints, naming the gate it used instead. You see at once that your answer was not taken. (2) Leave it silent, as now. The gate it used appears later in the line `set the gate to <gate>`. (3) Ask again until one of the three gates is typed. Nothing is ever guessed, but an automated run must use `--yes`.

### 19. From `update`

**What it is for.** The upgrade decides whether a project still looks as 0.9.5 left it, never upgraded. The eight checks for this say only "reads as set up by 0.9.5". What a person actually sees is the effect of that verdict: a test run stops and says to run the upgrade. That behaviour belongs to the test run's own rules.

**The question.** Should these eight checks describe what a person sees (a test run stopping with its message), or stay as the verdict the upgrade reaches?

**Options.** (1) Keep them as the verdict. The checks stay quick and sit beside the upgrade that makes the verdict. (2) Rewrite each to run a test run and see it stop with its message. A reviewer who cannot read code judges them more easily, but each check takes about 2 seconds longer. (3) Move the rule to the test run's feature, where the stop is seen, and keep no such rule under the upgrade. One rule in the place where people see it.

### 20. From `evidence_writer`

**What it is for.** Each rule gets one word in the results a test run records: passed, failed, not run or no test. That word drives what the run reports and what `Left to do` tells you to type next. A rule can have several proofs, and sometimes one proof has a passing test while another has no test yet.

**The question.** When some of a rule's proofs have a passing test and at least one proof has no test at all, which word should the rule read, and what should the run tell you to do?

**Options.** (1) `no test`. The run names the rule as having no test and points to `purlin:build`, which writes the missing test. This matches the advice to the cause. (2) Keep `not run`, but have the run name the proof that has no test and point to `purlin:build`. The word stays as it is today and only the advice changes. (3) Keep it as it is: the rule reads `not run` and `Left to do` says `1 rule to test: purlin:test`. Running that again never clears it, because the missing test still has to be written.

### 21. From `evidence_writer`

**What it is for.** Each set of results records where the tests ran, so a signature can be tied to that machine. A remote runner records its kind, such as `remote runner, Windows`, and keeps the name its host lent it beside that. On your own machine the results record the computer's name twice: once as the machine and once as that host name. The two are always the same, except on a computer with no name, where the machine reads `unknown` and the host name is empty.

**The question.** Should results from your own machine keep the second copy of the computer's name?

**Options.** (1) Keep both, as today. Every set of results has the same two fields wherever it ran. (2) Record the host name only for a remote runner, where it adds something: the name the host lent it. Results from your own machine carry the machine name once. (3) Drop the host name everywhere and keep only the machine. A remote runner's lent name is then no longer recorded.

### 22. From `reports`

**What it is for.** A test is tied to a rule by a one-line comment above it naming the feature and the proof. When that comment names a feature or proof that no spec has, the run prints the file and line with advice to correct it, and the run fails. If every rule otherwise passes, the run's last line still reads `Nothing left to do.` while the run exits with failure. Decision 69 says the terminal and the exit code should say the same thing.

**The question.** When the only problem is a comment naming something no spec has, what should the end of the run say?

**Options.** 1. Keep it as is. The line naming the comment is printed earlier, the summary says `Nothing left to do.`, and the run still fails. The last line and the failure disagree. 2. Add a line to `Left to do`, for example `1 test comment to correct: purlin:build`, so the ending names the work and matches the failure. 3. Stop failing the run for such a comment: print the line as a warning and exit 0, so the ending and the exit agree. A mistyped comment then no longer blocks CI. 4. Remove the check from the test run and leave it to purlin:build, which already finds comments that are nearly right.

### 23. From `reports`

**What it is for.** For .NET projects, Purlin reads the test report that `dotnet test` writes, where each test has an outcome word. The rule says only `Passed` counts as a pass. The product also counts three rarer words as passes: `Warning`, `Completed` and `PassedButRunAborted`.

**The question.** Should those three outcomes count as a pass or as a test that did not run?

**Options.** 1. Count them as passed: the rule and the format description are reworded to match the product. A test the .NET runner reported with a warning, or after the run was cut short, counts toward the rule. 2. Count them as not run: the product is changed to match the rule. Such a rule is then left to test until a clean `Passed` arrives. 3. Count only `Warning` and `Completed` as passed, and treat `PassedButRunAborted` as not run, because the run did not finish.

### 24. From `reports`

**What it is for.** purlin:build looks for comments that are nearly right, such as a misspelled feature name or an id one character off, and suggests the comment that was meant. When the id is a rule id, such as `RULE-30` where the spec has `RULE-3`, it suggests `RULE-3` even when that rule has proofs. A test comment may not name such a rule, so the suggested fix would itself be refused by the next run.

**The question.** Should the suggestion consider only the ids a test comment is allowed to name?

**Options.** 1. Keep it as is: suggest the nearest existing id, and let the next run point out that the rule has proofs. 2. Suggest only ids a comment may name, meaning proofs and rules that have no proof. `RULE-30` then gets no suggestion when `RULE-3` has proofs. 3. When the nearest id is a rule that has proofs, suggest that rule's proof, if it has exactly one.

### 25. From `ai_audit`

**What it is for.** When the audit reads a rule, the model can add a note: a proof longer than 60 words, or one holding two cases. A note never makes the rule weak. It is kept with what the audit found, so someone can tidy the proof later.

**The question.** When you print what the audit found for a rule, should the notes be shown next to the findings? Today the verdict, the model, the time and the findings are printed, and the notes are not.

**Options.** 1) Show the notes under their own heading after the findings. You see which proofs to tidy. 2) Keep them off the printed reading and show them only on the dashboard, or not at all. The reading stays short. 3) Remove notes altogether. The audit then says nothing about a proof's length or its number of cases, and the proof guideline is checked only by the person writing the spec.

### 26. From `ai_audit`

**What it is for.** You can print what the audit reads for one rule by naming the feature and the rule. It is a way to see the rule, its proofs, its tests and the last audit's result in one place.

**The question.** When you name a rule that the feature does not have, for example RULE-99, the command stops with a failure code and prints nothing. Should it say something?

**Options.** 1) Print one line naming the rule that was not found and how to list the feature's rules. This matches the rule that every output says what to do next. 2) Keep it silent with the failure code. Scripts see the failure and a person sees nothing. 3) Print every rule of the feature instead of failing.

### 27. From `host`

**What it is for.** When a remote runner's test suite runs a small sample project inside the job, that sample must not commit its evidence to the real repository. Purlin checks whether the project is the folder the job checked out, and a CI commit from any other folder is refused. Two rules say this today: one says what counts as the job's folder, the other says the commit is refused. They always pass or fail together.

**The question.** Should the rule about which folder is the job's, and the rule about refusing the commit, stay two rules or become one?

**Options.** 1) Merge them into one rule: a CI commit from a folder that is not the one the job checked out is refused, and with no such folder named every project commits. The proofs stay the same and there is one line less to sign. 2) Keep two rules as now: the first has one proof (with no folder named, a commit goes through) and the second has four. 3) Remove the check altogether: a sample project run inside a job could then commit its evidence to the branch under review.

### 28. From `host`

**What it is for.** When a remote run commits its evidence, it needs the name of the branch to commit to. The git host always gives that name on a runner. A fallback exists for when neither the git host nor git can name the branch: it takes the branch the remote's default points at, then the branch you are on, then `main`. It used to matter for deciding whether a signature was on the main branch; signatures now count on any branch, so that reason is gone.

**The question.** Is the fallback for naming the default branch still worth a rule and a signature?

**Options.** 1) Keep it as reworded (origin's default, then the current branch, then `main`). It costs one rule with three proofs and protects a case that rarely happens. 2) Remove the rule and the fallback: when nothing names the branch, the commit is made on the branch you are on, or refused with a line saying no branch could be read. 3) Keep only the `main` guess, with no rule of its own.

### 29. From `host`

**What it is for.** When a runner's run is not one that commits evidence, it prints one line saying why. Today that line always begins `Tag run: nothing is written.`, even when the run was started on an ordinary branch and not by a signed tag. The workflow Purlin writes starts only on run branches and signed tags, so this shows only if someone changes the workflow's triggers or starts a pipeline by hand.

**The question.** What should a runner print when it runs on a branch that is neither a run branch nor a signed tag?

**Options.** 1) Leave it: the line is the same for every run that writes nothing. 2) Print a line of its own, for example `This branch is not a run branch: nothing is written.`, and add a proof for it. 3) Make such a run fail, since the workflow is never meant to start there.

### 30. From `drift`

**What it is for.** Drift tells a developer, after a pull, which features' code changed, so they know which rules may now be behind. Today it counts only files that still exist. A file the pull deleted is never mentioned, whether a spec covers it or not.

**The question.** When a pull deletes a file, should the developer's view mention it?

**Options.** (1) Leave it as it is. Deleting a file never shows, and the rule is reworded to say only files that still exist are counted. (2) Count a deleted file under the feature whose scope covered it, so `2 files changed under login's scope` includes it and login's rules show as behind. (3) Also name deleted files that no spec covered, in the same line as the other files no spec covers.

### 31. From `drift`

**What it is for.** The QA view of drift carries, beside its printed lines, the list of rules that have not yet been audited. No line of the QA view prints this list. The audit is done by a command, not by a person, and the QA view otherwise holds only work waiting for a person: to test by hand and to sign.

**The question.** Should the QA view keep the list of rules not yet audited?

**Options.** (1) Remove it, so the QA view holds only what it prints and what waits for a person. The rule's proof loses the key `not_audited`. (2) Keep it as a fact a model reading drift can use, and reword the rule to say the QA view also carries the rules not yet audited. (3) Print it as a QA line too, `3 rules to audit: purlin:audit`, which goes against the QA view showing only work for a person.

### 32. From `drift`

**What it is for.** An anchor is a set of rules copied from another repository and pinned to one commit there. Drift tells a developer when the source has moved on. It can check only sources that look like a git repository: a GitHub or GitLab address, an address ending in `.git`, an ssh address or a local path. An Azure DevOps address has none of these, so an anchor kept there is never reported, even when it is behind. This is listed as a product fault, but how to fix it is a choice.

**The question.** How should drift decide whether it can check an anchor's source?

**Options.** (1) Try every source that passed the safety check, and report `error` when it cannot be read. Nothing is left out silently. (2) Also recognise Azure DevOps addresses, and keep skipping anything unrecognised. (3) Keep skipping, and reword the rule so it lists the kinds of source drift checks.

### 33. From `evidence`

**What it is for.** A spec's `> Scope:` line names the files the spec covers. When a change touches those files, the rule's test results go out of date and its signature ends. Sometimes an entry on that line finds no file: a typo, a file that was deleted, or a new file not yet added to git. Purlin notices such an entry, but today it tells nobody. The only message a person sees comes when every entry on the line finds nothing: `> Scope: names nothing that exists`.

**The question.** When one entry on a spec's `> Scope:` line finds no file and the others still find some, should Purlin tell the person?

**Options.** (1) Tell them. The test run and the dashboard name the spec and the entry, for example `login: > Scope: names src/gone.py, which finds no file.`, and point to `purlin:spec login` to fix the line. A typo would no longer leave a file silently uncovered. This is new product work, and its proof would read what the run prints. (2) Tell them only in `purlin:drift`'s view for developers, as one more line in the list of what needs attention. The test run and the dashboard stay as they are. (3) Say nothing, and take the idea out. The rule then says only that an entry that finds nothing adds nothing to what the evidence covers, and that the rest of the line still counts. Only the existing message, for a line where every entry finds nothing, stays. A typo in one entry goes unnoticed until someone reads the spec.

### 34. From `package`

**What it is for.** The evidence package is the data file a reviewer reads for one version. One of its promises is that it never records who last edited a test. That promise dates from when a signature did not count if the signer had also last edited the test. That check is gone: anyone with a key can sign, and the system of record decides who was entitled.

**The question.** Should the package keep promising, and checking, that it never names who last edited a test?

**Options.** (1) Remove the promise and its check. The package says only what it carries, and a later version could add the test's editor without breaking a rule. (2) Keep it as it is. A reviewer can rely on the package naming no test editor, and a check guards that. (3) Replace it with a positive promise: the only people the package names are the people who signed. That is stronger and covers every field, and it gets its own check.

### 35. From `package`

**What it is for.** One rule of the evidence package lists everything a single rule carries in the file: its words, proofs, tests, results with the machine, what the audit found, its signatures and its statuses. That is about thirty items in one line, with ten proofs under it. A reviewer or signer reads, audits and signs that line as one unit.

**The question.** Should that one long rule be split into several rules, each about one part of what a rule carries?

**Options.** (1) Keep one rule. There is one line to read, one audit and one signature at the gate `signed`, and the ten proofs stay together. (2) Split it into five rules: the words, proofs and tests; the results and machines; the audit; the signatures; the statuses. Each is judged and signed on its own, so a change to one part ends only that part's signature, and there are four more rules to audit and sign each version.

### 36. From `mutation`

**What it is for.** When Purlin breaks the code on purpose, Stryker and Stryker.NET can say which test caught each break. Purlin uses that to work out a number for each rule from its own tests alone. Today that number is worked out and then dropped: the evidence, the status and the dashboard keep only the feature's one number, and every rule in the feature is judged against it. The docs say a Stryker rule carries its own tests' number.

**The question.** Should a rule be judged on the share of breaks its own tests caught, where the engine can tell?

**Options.** (A) Yes. Keep each rule's own number in the evidence and judge the rule's strength on it; mutmut rules keep the feature's number, since mutmut cannot tell. The fault of matching tests across files must be fixed first. (B) No, remove it. Every engine gives one number per feature and every rule is judged on that. The four mutation rules about ordering rules, crediting each rule's tests, matching test names and choosing between the two ways of crediting go, and the docs line is corrected. (C) Keep it worked out and unused, as today, and correct only the docs line.

### 37. From `mutation`

**What it is for.** With breaking the code on purpose turned on, a rule is strong only when its tests catch at least the minimum share of breaks. Sometimes nothing can be measured: the engine is not installed, it ran past the time limit, or it wrote no report. Then the rule has no number, and today the AI audit alone decides, so the rule can read strong the same as a shell rule that has no engine at all. A whole audit run given a 1-second limit showed exactly this: the rule was counted strong with no strength.

**The question.** When breaking is on but measured nothing for a feature, should its rules still be able to count as strong?

**Options.** (A) Yes, as today: the audit alone decides, and nothing says strength was missing except the line the run prints. (B) No: such a rule reads weak with a reason naming why nothing was measured and the command that fixes it (install the engine, raise the time limit). (C) Stop earlier instead: an audit with breaking on and the engine not installed stops before it starts and names the install command; a run that times out still falls back to the audit alone.

### 38. From `mutation`

**What it is for.** mutmut names each break after the Python module it changed, such as `login.session`, not after the file. Purlin decides which feature a break counts for by matching the end of each `> Scope:` entry against the start of that name. This has two effects. In a project that keeps its code under `src/`, a feature whose scope is the folder `src/` gets no breaks at all, so its strength is never measured. And a feature whose scope names a package's `__init__.py` also gets the breaks of every other file in that package.

**The question.** How should a mutmut break be matched to a feature's scope?

**Options.** (A) By file: turn the break's module name into its file, trying the project root and `src/`, and count it for every feature whose scope reaches that file, the same way a scope reaches files everywhere else in Purlin. (B) Keep the name matching, and state both effects in the rule and the docs, so a Python scope names files or folders below `src/`. (C) Remove the split by feature for mutmut: one number for the whole project, given to every feature.

### 39. From `mutation`

**What it is for.** Stryker.NET writes its report as `mutation-report.json` somewhere under the folder Purlin gives it, and Purlin looks through that folder for it. When no file of that name is there, Purlin today takes the first other JSON file it finds under the folder as the report. The rule does not mention this.

**The question.** Should Purlin read some other JSON file when `mutation-report.json` is missing?

**Options.** (A) No, remove it: only `mutation-report.json` counts; otherwise the feature measures nothing and the log says no report was written. (B) Yes: keep it, and the rule and a proof state it.

### 40. From `skill_sign`

**What it is for.** About half the proofs in this spec (19 of 42) describe a deliberately damaged copy of the sign skill's instructions and say that the check notices the damage. For example: "a copy with the version offer removed is reported as not offering to write the version". They show that the test can fail. They say nothing new about what the sign skill tells a person or an agent.

**The question.** Should a proof that says the check catches a damaged copy stay a proof that QA reads and a person signs, or is showing that a test can fail a job for the audit's deliberate breaks?

**Options.** 1. Keep them as proofs. Every rule carries its own evidence that its check can fail, and QA reads and signs about twice as many lines per spec. 2. Keep the damaged-copy checks as tests, but take them out of the spec. The spec then holds only what the skill says, which is about half the proofs to read and sign, and the tests still guard the checks. 3. Remove them entirely and rely on the audit's deliberate breaks at the gates strong and signed to show the tests can fail. This means the fewest lines to read, but no such evidence at the gate passed.

### 41. From `upstream`

**What it is for.** A project can pull several anchors from one shared policy repository. When you pull new versions, Purlin first asks that repository which version is current, then downloads it to read the new text. The rule promises one trip to each repository per run, so a repository holding many anchors is not contacted over and over.

**The question.** When two or more anchors come from the same repository and all have moved, Purlin checks the repository once but then downloads it once per anchor. Should one pull download each repository only once, or should the promise cover only the check?

**Options.** 1) Download once per repository per run. The promise holds for the check and for the pull, and pulling many anchors from one repository costs one download. This needs a code change. 2) Narrow the promise to the check (`sync --check`, and what drift shows). The pull keeps downloading once per anchor. Nothing changes for the user, and the rule says so plainly. 3) Remove the rule. Purlin makes no promise about how often it contacts a repository, and the check could reach it once per anchor in future.

### 42. From `skill_test`

**What it is for.** The rules of the test skill are there so that the instructions an agent follows when it runs your tests keep saying the right things: which command to run, what each exit code means, what files the run writes and commits, and what to do when no test command is set. Three of these rules each list several separate things, for example one rule names the two files, the two commits, the two result lines, the no-push sentence and how the run ends.

**The question.** Should a rule that lists several separate things the instructions must say be split into one rule per thing?

**Options.** 1. Split them: each thing becomes its own rule with its own proof. There are more rules to audit and sign, but a failing check points at one exact thing, and a change to one item leaves the others' signatures standing. 2. Keep them as they are: fewer rules, and the proofs already name each thing separately, so a failure still says which one broke. 3. Remove the word-for-word rules and keep only the ones about behaviour, such as what to do when no test command is set: fewer rules to keep current when wording changes, but a reworded instruction that says something wrong would go unnoticed.

### 43. From `specs`

**What it is for.** Purlin knows each spec by its file name alone, not by its folder. That short name is what test markers and signatures use, such as `purlin: login PROOF-4`. If two folders each hold a spec with the same file name, for example `specs/auth/login.md` and `specs/admin/login.md`, only one is read. The other's rules vanish from status, tests and signing, and nothing is printed.

**The question.** What should happen when two specs share a file name?

**Options.** 1. Keep it as is: one of the two is read and the other is ignored, without a word. 2. Warn: every run prints one line naming both files and asking you to rename one. The rules of the one not read stay missing until you do. 3. Refuse: a run stops, names both files, and writes nothing until one is renamed. 4. Know specs by folder and name together, so both are read. Every marker and signature would then have to name the folder, a larger change to the marker and signature formats.

### 44. From `specs`

**What it is for.** The spec format anchor, whose rules every spec must meet, says how the `@manual` and `@env` tags on a proof line are read. The feature that reads specs says the same thing again in three rules of its own (the unknown word that stops reading, the three operating systems, and at most one `@env`). Each copy has its own proofs and tests, so one behaviour is proved twice and a change has to be made in two places.

**The question.** Should the tag rules live in one place?

**Options.** 1. Keep both: the anchor says what a spec author may write, the reader says what is read, and each keeps its own proofs. 2. Keep them in the anchor only: the reader feature drops its three tag rules and their proofs. The anchor's rules still count for it, because it requires the anchor. 3. Keep them in the reader only: the anchor keeps just the sentence that the tags exist and points at the reader for how they are read.

### 45. From `skill_audit`

**What it is for.** The audit's instructions tell the reader four kinds of thing: what an audit does at each gate, the one line it prints and how it ends, what it commits, and that it never waits on a signature. Today all of that is one rule, which 16 separate proofs check. A person signs a rule as a whole, and any failing part makes the whole rule fail.

**The question.** Should this stay one rule, or be split so that each part is signed and fails on its own?

**Options.** 1) Keep one rule: one line to sign, but a single wrong sentence in the instructions fails everything the rule covers. 2) Split it into three rules: what each gate runs; the line the audit prints, how it ends and what it commits; and that an audit never waits on a signature. Each is signed and fails on its own, and the proofs move to the new rules unchanged. 3) Split it into one rule per statement, six or seven rules: the finest reporting, and the most to sign. 4) Remove the rule and rely on the audit's own behaviour being checked elsewhere: nothing then checks that the instructions a person or agent reads say these things.

### 46. From `skill_audit`

**What it is for.** A proof's number is never reused, so a past result or signature can never be read as belonging to a different proof. The file that holds the audit skill's spec once held an older version of it, deleted whole in the clean-up, whose proofs were numbered up to 106. Nothing recorded under those old numbers survives.

**The question.** When a spec's history includes an earlier file at the same place that was deleted whole, do its old numbers count as used?

**Options.** 1) No: count only from when the spec was last written anew. The new proofs here run from 17, as done. 2) Yes: any number ever seen at that place is used. The new proofs here are renumbered from 107, leaving a gap of 90 that a reader may find odd. 3) Settle it once for every spec, whichever of the two you choose, so all the lanes number the same way.

### 47. From `skill_init`

**What it is for.** When you set a project up, Purlin records nothing about how its tests run. The first test run recognises one test tool and suggests the command, and you confirm it. A project with tests in two tools, for example Python and JavaScript, needs a second command added. Setup has a flag, `purlin:init --add <tool>`, that adds one more tool's command to the settings. It is listed in the init instructions and a rule says it must be. Nothing in decisions 60 to 85 settles whether it should stay, now that the test run owns how tests are run.

**The question.** Should setup keep a way to add a second test tool's command, or should that belong only to the test run?

**Options.** (a) Keep `purlin:init --add <tool>` as it is. A person with two test tools types one command after setup. (b) Remove it from setup. The first test run suggests one tool, and a second is added by editing the settings through Purlin's settings tool; the rule, its proofs and the flag row go. (c) Remove it from setup and have the first test run suggest a command for every tool it recognises, not only the first, so no second step is needed.

### 48. From `skill_init`

**What it is for.** Each proof has a number, and test results and signatures name a proof by that number. So a number is never given to a different proof: an old result would then seem to speak for the new one. The init spec was once replaced by a completely new file, which started again at 1, and earlier versions of the file had used numbers up to 122.

**The question.** When a spec has been replaced by a new file, should new proof numbers continue from the current file's highest number, or from the highest number the file has ever had?

**Options.** (a) Continue from the current file, which is what this lane did: the new init proofs are 16 to 43. Numbers stay short, and the old ones that are reused belong to proofs from before the replacement. (b) Continue from the highest ever used: the new init proofs become 123 to 150. No number ever means two things, and the numbers look arbitrary. (c) Treat a replaced spec as a new feature under a new name, so its numbers start fresh and cannot collide.

### 49. From `security_no_dangerous_patterns`

**What it is for.** One security rule stops Purlin's own code from handing a whole command line to the computer as text, because text can be bent to run something else. In C#, a program can be started either from a line of text or from a prepared description that lists each argument separately. The check can see a command written out in quotes, but when the code passes a named value it cannot tell which of the two it is.

**The question.** How should the rule treat a C# program start that is passed a named value rather than a command written in quotes?

**Options.** (1) Narrow the rule to a command written out in quotes. It then says exactly what is checked, and a command held in a named value is not covered. (2) Require every C# start to be given a prepared description built in the same place, with its arguments listed one by one. The check can then hold every start, and any C# code that passes a named value fails. (3) Remove the C# part of the rule. Purlin ships no C# code today, so a C# file added later would be checked for none of the C# forms. (4) Leave the rule as it is and accept that the gap stays open.

### 50. From `security_no_dangerous_patterns`

**What it is for.** Another security rule says every program Purlin starts is given its arguments as a list, never as one line of text. For one of Python's ways of starting a program, the check accepts a named value, because Purlin's one use of it, the runner that breaks code on purpose, is passed a list that is built elsewhere. A text check cannot follow that name back to where it is built.

**The question.** Should that one program start be held to a list written in place, like every other start?

**Options.** (1) Change that one start so its list is written where the program is started, and hold that form of start to a list in place. The rule is then checked in full. (2) Narrow the rule to say a named value is accepted for this form of start. It then matches the check, and a string passed by name would go unseen. (3) Leave both as they are, and the gap stays listed as open.

### 51. From `security_no_dangerous_patterns`

**What it is for.** Two of the security rules both name the same two PHP commands, `system(` and `passthru(`: one rule covers running text as code, the other covers handing a command line to the system. A file holding either command therefore fails both rules at once.

**The question.** Should these two PHP commands be named by one rule only?

**Options.** (1) Keep them only under the rule about handing a command line to the system, and take them out of the rule about running text as code. (2) Keep them only under the rule about running text as code, which leaves the other rule covering Python alone. (3) Leave them in both rules, so one mistake shows as two failures.

### 52. From `skill_export`

**What it is for.** Someone can check a package file against the fingerprint it carries, to show nobody changed it after it was exported. When the check finds a difference, the export's instructions tell you what to do next. Today that line is `→ Export the package again at its tag: purlin:export`. But the export always describes the commit you are standing on. Running `purlin:export` from anywhere other than the tagged version writes a different package, and the line does not say how to get to the tag.

**The question.** When a package fails its fingerprint check, what should the next-step line tell you to do?

**Options.** 1. Keep the line as it is. It says 'at its tag' and trusts you to know you must stand on the tagged version first; run from anywhere else, the export describes a different commit. 2. Name the move to the tag, for example `→ Check out signed/<version>, then run: purlin:export`. The step is exact, but it takes you off your branch until you switch back. 3. Point at the copy the tag already carries, for example `→ Take the package committed at signed/<version>`. No new export, and you get the file the signature covers. 4. Remove the line and only report the mismatch. That breaks the promise that every ending names what to do next, so the closing table would lose one of its five outcomes.

### 53. From `schema_spec_format`

**What it is for.** Each rule has a number so that tests and signatures can point at it. Retiring a rule leaves its number unused so that nothing already pointing at it moves.

**The question.** What should Purlin report when a spec uses the same rule number twice, or lists its rules out of order? Today it reports nothing. A doubled number is shown twice with the second line's text, and one screen then says 2 rules while the list of work says 3.

**Options.** (a) Report a doubled number as a warning naming the spec and the number, and leave an out-of-order list alone. (b) Report both, a doubled number and a number lower than the one before it. (c) Report nothing, and change the rule to say the author alone keeps the numbers right. The screens stay inconsistent when an author gets it wrong. (d) Remove the promise that numbers are never reused, so the rule says only that a gap is fine.

### 54. From `schema_spec_format`

**What it is for.** Each line under `## Proof` names the rule it proves. A line Purlin cannot read, such as one with no rule named, is dropped today without a word. To catch this in its own files, this project keeps a check that every proof line in its own specs names exactly one rule. The format itself allows one proof to name several rules.

**The question.** What should happen to a proof line Purlin cannot read, and should this project's own check accept proofs that name several rules?

**Options.** (a) Keep dropping the line silently, and keep the project's check as it is, one rule per proof line. That is stricter than the format. (b) Keep dropping it silently, and widen the project's check to accept several rules, as the format allows. (c) Report such a line as a warning, as a rule line without a number already is, and remove the project's own check, which would then be redundant. (d) Remove the project's check and keep dropping the line silently.

### 55. From `schema_spec_format`

**What it is for.** The first line of a spec reads `# Feature: <name>` or `# Anchor: <name>`. Purlin takes a spec's name from its file name, not from that line. The line matters only when it begins `# Anchor:`, which makes the spec an anchor even outside the anchors folder. A line naming a different name, or neither form, is accepted without a word.

**The question.** Should the rule about this heading stay as it is, or should it say what Purlin actually reads?

**Options.** (a) Keep the rule as a writing convention that only this project's own check enforces, on its own files. (b) Reword the rule to what Purlin reads: the file name is the spec's name, and `# Anchor:` makes a spec an anchor wherever it is kept. Prove it with two small cases and drop the project-only check. (c) Have Purlin warn when the heading is neither form, or names something other than the file name. That is a product change. (d) Remove the rule.

### 56. From `purlin_agent`

**What it is for.** Every Purlin session reads the agent's instructions before doing anything, so their length is paid in every session. A rule caps them at 135 lines, and they are exactly 135 lines today. Any new sentence has to replace an old one.

**The question.** Should the 135-line cap on the agent's instructions stay where it is?

**Options.** (1) Keep 135. Every later change to the agent's wording must cut as much as it adds, and the instructions stay as short as they are now. (2) Raise it, for example to 150. There is room for a few more sentences, such as the one in the next question, and every session reads a little more. (3) Remove the cap and its rule. The instructions can grow freely and nothing warns when they do.

### 57. From `purlin_agent`

**What it is for.** When a person asks about a rule's state, the agent reads the words the product shows and explains them. It explains `no proof written`, the reason shown when no proof names a rule. It says nothing about `No proof`, the word the dashboard's first box and the strong step show when a rule has a test but no proof. Only the glossary explains that word.

**The question.** Should the agent's instructions also say what `No proof` means?

**Options.** (1) Add one sentence saying `No proof` means the rule has a test and no proof, and that `purlin:spec` writes the proof. Because the instructions are at their 135-line cap, another line must be cut or the cap raised. (2) Leave it to the glossary. The agent looks the word up there like every other word. (3) Drop the `no proof written` sentence too, so the agent explains no individual words and relies on the glossary for all of them.

### 58. From `purlin_agent`

**What it is for.** The agent keeps four things it must never do. The fourth is about calling each thing by its one agreed name, and a short line at its end also forbids emoji anywhere, including command output. The project's style guide already forbids emoji everywhere.

**The question.** Where should the agent's ban on emoji live?

**Options.** (1) Keep it inside the fourth never, as it is now. The four nevers stay four, and the naming never carries a second ban. (2) Make it a fifth never of its own. It is easier to see, and the list and its rule become five. (3) Remove it from the agent and rely on the style guide. The agent's list covers only the four acts that could damage the paper trail.

### 59. From `skill_build`

**What it is for.** When you run purlin:build, the build skill is the set of instructions the agent follows. It says how to choose what to build, how to write and mark the tests, and how to write the commit that says which change serves which rule. Its rules are now proved by reading those instructions, so they show what the agent is told. They do not show that an agent, once told, actually writes that commit or fixes the spec's list of files.

**The question.** Is reading the build skill's instructions enough to prove its rules, or should Purlin also run the build skill for real on a small practice project and check the commit it makes?

**Options.** 1. Reading the instructions is enough (as now). Tests are fast and free, and prove what the agent is told, not what it does. 2. Also run it for real. A practice project is built by the agent on every full test run, and its commit and file list are checked. This needs the Claude program, costs model calls each time, and the result can vary from run to run. 3. Run it for real, but only before a release and not in every test run. 4. Drop the rules about the commit and the file list from this spec and leave them to the commit conventions document alone.

### 60. From `skill_build`

**What it is for.** A separate check commits a few hand-written commit messages to a throwaway repository. It shows that a message in the agreed shape comes back from git whole, and that its own rules turn down three broken messages. It reads nothing Purlin itself wrote. It still runs as part of the full test run, but no rule's proof points at it any more.

**The question.** What should happen to the check that commits hand-written messages?

**Options.** 1. Delete it. The build skill's own rules now read the skill and the commit conventions directly. 2. Keep it running in the full test run with no proof pointing at it. 3. Point a proof back at it, which would claim something about git and the check itself rather than about Purlin.

### 61. From `skill_build`

**What it is for.** The commit conventions say a build commit's body has three parts: the changeset (which rule maps to which file and line), Decisions and Review. In the one example they give, Decisions and Review each start with a heading line (`Decisions:` and `Review:`). The changeset has no heading and is just the first lines after the subject. The build skill calls all three "sections", so an agent may or may not write a `Changeset:` heading.

**The question.** Should the changeset in a build commit start with its own heading line, like Decisions and Review?

**Options.** 1. Yes. The example and the skill show a `Changeset:` heading, so every build commit reads the same way. 2. No. The changeset is always the first lines after the subject with no heading, and the skill says so plainly. 3. Either is fine, and the conventions say both are accepted.

### 62. From `skill_build`

**What it is for.** When the build skill finishes, it ends by telling you the next thing to do. At the gate `passed`, once every rule has a passing test, it currently says `→ Run: git push`. Elsewhere, Purlin's rule for a finished project at the gates `passed` and `strong` is to say `Nothing left to do.` and name no command. The build skill's instructions and that rule disagree about what a finished build at `passed` should end on.

**The question.** At the gate `passed`, when every rule has a passing test, what should the build skill tell you at the end?

**Options.** 1. Keep `→ Run: git push`. Pushing is the natural next step after building, and every ending names a command. 2. Say `Nothing left to do.` and name no command, the same as a finished test run. 3. Say `Nothing left to do.` and then mention pushing as a plain sentence, not as a command to run.

### 63. From `skill_spec_from_code`

**What it is for.** purlin:spec-from-code is run once, on a codebase that has no specs. It writes the first rules, ties the tests the project already has, and lists what it could not tie. The spec for it can check only what the skill's instructions say, not what an agent does when it follows them.

**The question.** Should something show that the skill, when it runs, really ties the existing tests, writes no new test, lists the tests and files it left out, and runs no test first?

**Options.** 1. Instructions only (as the branch now stands): the spec checks the skill's wording, and the three trial projects of sanity check 3 are the only check of what it does. Cheapest; a change in the model's behaviour goes unnoticed until the next trial. 2. A check by hand: add proofs marked for a person, who runs the skill on a small sample project (one full test, one partial test, one failing test) and signs what they saw. Needs a person each release. 3. An automated run: the test suite runs the real skill on that sample project and reads what it wrote. Catches changes in behaviour, but calls the model on every run, is slow, costs money and its answers vary. 4. Remove these four rules, so nothing in the spec guards what the skill says about ties, reports or running tests.

### 64. From `skill_spec_from_code`

**What it is for.** Decision 66 says an internal helper gets no rule of its own: it is covered by the rule of the behaviour it serves. The skill says so ("Do not write a rule for a private helper"), but no rule of its spec holds that sentence, so it could be deleted and nothing would fail.

**The question.** Should the spec guard the instruction that no rule is written for an internal helper?

**Options.** 1. Add a rule and its proofs, like the other instructions of the skill: deleting the sentence then fails the tests. 2. Leave it unguarded, as now: the sentence stays in the skill but can be removed without notice. 3. Remove the sentence from the skill and rely on the quality guide's rebuild test, which makes the same point less directly.

### 65. From `config_engine`

**What it is for.** Every command reads the project's settings file for the gate, the test command and the version. The settings file can be edited by hand, and a slip such as a trailing comma leaves it unreadable. Today an unreadable file reads as if it were empty. The next time Purlin saves one setting, it rewrites the file with only that setting, and every other setting is lost.

**The question.** What should happen when the settings file cannot be read?

**Options.** 1. Keep today's behaviour: an unreadable file counts as empty, and the next save replaces it with only the saved setting. Simple, but hand edits and every other setting can disappear without warning.
2. Say so and refuse to save: commands report that the settings file cannot be read and name the line, and saving a setting is refused until the file is fixed. Nothing is lost; you fix the file first.
3. Say so, but still read it as empty: commands warn and carry on, and saving is refused. Commands keep working with defaults, and the file is never overwritten.

### 66. From `config_engine`

**What it is for.** When Purlin saves a setting, for example when setup records the gate, it writes the whole file beside the old one and then swaps it in, so the old file is never left half-written. If the save fails (disk full, a folder you cannot write to), the old file stays as it was. But nothing reports the failure: the settings tool still answers `Set 'gate' = "passed"`, and the setting was not saved.

**The question.** Should a save that fails say so?

**Options.** 1. Yes: the save stops with an error that names the cause, and the tool says the setting was not saved. The answer then matches what is on disk.
2. Keep it quiet, as today: the old file is safe, but you or an agent may believe a setting took effect when it did not.

### 67. From `config_engine`

**What it is for.** Besides the settings tool Purlin gives Claude, there is a small command line that prints the whole settings file, or one setting, for use from a shell script. No skill, agent, hook or shipped script uses it. It sits in the folder a consumer project may depend on, so someone outside might. This lane added five proofs for it (the dump, a missing setting, and three refusals).

**The question.** Should the command line for reading settings stay?

**Options.** 1. Keep it as it is, with its rule and proofs. A shell script in your own project can read a setting without Claude.
2. Remove it: delete the rule, its proofs, its tests and the code, and list the removal in RELEASE_NOTES.md. Settings are read through the settings tool or by opening the file itself.
3. Keep only the dump of the whole file and drop the one-setting form. A shell script uses its own JSON tool to pick out one setting.

### 68. From `server`

**What it is for.** Setup and the first test run use Purlin's settings tool to change one project setting, such as the gate or the test command, without editing the file by hand.

**The question.** What should happen when someone asks the settings tool to change a setting and gives no value? Today the setting is emptied. On a project at the gate `signed`, that silently drops the project to `passed`: the status shows only a warning that the gate is not one of passed, strong or signed, followed by an upgrade suggestion.

**Options.** 1. Refuse it, the way a change naming no setting is already refused. The setting stays as it was and the caller is told a value is required. 2. Keep today's behaviour and write it into the rule, so emptying a setting is a documented way to clear it. 3. Refuse an empty value, and offer a separate, explicit way to remove a setting. 4. Take changing settings out of the tool, so settings change only through setup and the first test run's own questions; the tool would then only read.

### 69. From `server`

**What it is for.** The same settings tool lets an agent write any setting with any value.

**The question.** Should the settings tool refuse a value that Purlin does not accept? Today it accepts a gate of `gold`. Afterwards the status reads the gate as `passed`, prints a warning, and suggests running the upgrade command, which does not describe the real problem.

**Options.** 1. Refuse values Purlin does not accept for the settings it knows, for example a gate other than passed, strong or signed, and name the accepted values. The file stays unchanged. 2. Also refuse setting names Purlin does not know, so a typo cannot add a stray setting. 3. Keep accepting anything; the status warning is enough. 4. Take changing settings out of the tool, as in the previous question.

### 70. From `server`

**What it is for.** An agent reads one setting through the tool to decide what to do next, for example which gate the project uses.

**The question.** What should the tool answer when the setting asked for is not there? Today it answers the sentence `Key 'x' not found in config.` A setting that is found comes back as data instead, so the agent has to tell two shapes apart. A setting stored as empty reads as not found, too. None of this is in a rule.

**Options.** 1. Write today's behaviour into the rule as it is. 2. Answer in the same data shape either way, with the setting shown as empty, so a reader handles one shape. 3. Treat asking for a missing setting as an error with its own code. 4. Leave it unstated, as it is now.

### 71. From `skill_status`

**What it is for.** Some of what the status skill promises is done by the agent, not by the tool: printing the tool's closing lines without changing them, and, when you type a spec's name, printing that spec's rules, listing the choices when several specs match, or showing the whole table when none does. Today the tests can only read the skill's instructions and check the right words are there. They cannot see what an agent actually prints.

**The question.** How should what the agent actually prints for `purlin:status` and `purlin:status <name>` be shown?

**Options.** 1) Keep reading the instructions only. The rules now say the skill 'tells the agent' or 'says', which the tests do show. Nothing more to do; how the agent behaves is left to the AI audit's reading. 2) Add a check done by hand: before each release a person runs `purlin:status` with a name in a sample project and signs what they saw. That adds one `to test by hand` line to every release. 3) Add an automatic run of a real agent against a sample project in the test suite. It calls the model on every run, costs time and money, and its wording can vary from run to run. 4) Drop the promises about the named form's behaviour and keep only that the command reference names `purlin:status [name]`.

### 72. From `skill_status`

**What it is for.** A signature on a rule ends when any file the feature lists changes. The status skill's spec used to list only the skill's own instructions. Two of its proofs now run the status tool itself: one checks that the closing lines printed and the data the dashboard reads carry the same counts, and one checks that every kind of `Left to do` line has a row in the skill's table. So I added the tool's code to the files the spec lists.

**The question.** Should the status skill's rules be re-signed when the status tool's code changes?

**Options.** 1) Yes, keep the tool's three code files in the list. A change to how the tool writes its closing lines ends this spec's signatures, and a person re-checks that the skill still matches. 2) No. List only the skill's instructions, and move the proof that the printed lines and the dashboard data agree to the spec that covers the status tool; the table check stays here. 3) Remove the new proof that the printed lines and the dashboard data agree, and keep only the instruction checks.

### 73. From `skill_spec`

**What it is for.** The spec skill is the set of instructions the agent follows when it turns a requirement into rules and proofs. Its rules say what the skill does: it prints each rule with its proofs and asks before saving, it writes the scope line on every spec, and it writes each proof as one case. The tests read the skill's instructions and confirm those sentences are there. They never run the skill on a real requirement to see the agent do it.

**The question.** Should these rules claim only what the instructions say, or also what the agent actually does when it runs the skill?

**Options.** 1) Reword the rules to say what the skill tells the agent, for example "the skill tells the agent to print each rule with its proofs and ask before it saves". What passes is then exactly what is checked; nothing shows the agent obeys. 2) Keep the wording and add a check that runs the skill on a sample requirement, judged by a person when signing or by the AI audit. That shows real behaviour, but costs a model run, and a person's judgement for each release. 3) Keep things as they are: the spec's description already says it covers what the skill file must say, and each rule is read in that light. Nothing changes, and a reader of one rule alone may think the behaviour itself was proved. The same choice applies to every skill spec, not only this one.

### 74. From `purlin_version`

**What it is for.** Changing the release number is meant to happen in one step, so the version cannot drift between files. The bump script writes the version file and copies the number into the settings template, the plugin manifest and this repository's own settings. The rule also says the bump script is the one way these fields get written. But the upgrade command also rewrites this repository's own settings version, taking the number from the version file.

**The question.** What should the rule claim about who writes the version fields?

**Options.** A) Drop the claim. The rule says what the bump script does and nothing about other writers. Nothing else changes for a user. B) Keep the claim, reading it as: only the bump script sets a new number, and anything else may copy the number from the version file. A test then checks that nothing writes these fields from any other source. C) Keep the claim literally. The upgrade stops writing this repository's settings version and leaves it to the bump script. The upgrade then no longer brings a stale version stamp up to date by itself.

### 75. From `purlin_version`

**What it is for.** The settings template is the starting settings file for a new project, and it carries a version number that the bump script keeps equal to the version file. But setup takes a new project's version from the version file directly, so the template's own number never reaches any project.

**The question.** Should the settings template keep its own version number?

**Options.** A) Keep it. It stays one of the files the bump script updates and the check watches. Nothing changes for a user. B) Remove it. The template holds no version, and the bump script and its check look at one fewer file. New projects still get the right version from the version file. C) Keep it, and have setup take the version from the template. The template then becomes the real source of a new project's version, with the bump script keeping it current.

### 76. From `purlin_version`

**What it is for.** The plugin reports its version to Claude Code when it connects and on the dashboard, and it reads that number from the version file. If the version file is missing, it currently reports 0.0.0 and carries on. I added this behaviour to the wording of rule 2 and rule 4 so the rules describe it.

**The question.** When the version file is missing, should the plugin report 0.0.0 and keep working, or stop?

**Options.** A) Report 0.0.0 and keep working, as now. The rules as reworded describe this. B) Refuse to start and say the version file is missing. A broken install is noticed at once, but the plugin does not run until the file is restored.

### 77. From `skill_anchor`

**What it is for.** The anchor skill tells the agent that a pinned anchor is fixed at one commit and that its rules are never edited in the project that uses it. A change goes upstream, or into a separate local anchor. The checks confirm that the skill says this in the right places, and refuse a copy where one of those sentences is reworded to say the opposite.

**The question.** Should the checks also refuse a skill that keeps those sentences but adds, somewhere else, an instruction that contradicts them, such as 'pin the branch main' or 'edit the pinned copy when the fix is small'?

**Options.** 1. Leave it as it is. The three sentences are checked where they stand, and a contradicting line added elsewhere is caught only by reading the change. 2. Agree a short fixed list of contradicting phrases, for example 'pin the branch', 'edit the pinned copy' and 'edit it in place', and refuse the skill when any sentence carries one. This catches those exact wordings and misses others. 3. Remove the text checks on the pin sentences and rely on reading the skill when it changes. The rule would then have no test behind it.

### 78. From `skill_drift`

**What it is for.** The drift skill shows a sample of each view, product, developer and QA, so the agent and the reader know what the printed lines look like. The samples are written by hand, and one has already drifted from what drift prints: its anchor line carries a 40-character commit id where drift prints 7 characters.

**The question.** Should the sample lines in the drift skill be held to the lines drift actually prints?

**Options.** (1) Yes. Add a rule that every sample line has a form drift prints, and a test that runs drift on a small project and compares. Samples then cannot drift, and changing drift's wording means changing the samples in the same commit. (2) No. Treat the samples as illustration, fix the one wrong line by hand and add no check. Samples can drift again unnoticed. (3) Remove the samples from the skill and point at the drift criteria page, which already shows one line of each kind. The skill gets shorter and nothing can drift, but a reader of the skill no longer sees a whole view at once.

### 79. From `claude-md`

**What it is for.** The release steps for Purlin itself. They tell whoever cuts a release how to set the version number and publish it. This repository now asks every rule to be signed. At that gate the signing command writes its own signed release marker once nothing is left to do, and a person pushes it. Earlier releases used a plain version marker.

**The question.** When Purlin itself is released, which marker marks the release, and who writes and pushes it?

**Options.** (a) The signed marker the signing command writes, pushed by you. The instructions would say: set the version, commit, sign, push the marker, and would drop the plain marker. (b) Both: the signed marker for the evidence, plus the usual plain version marker that people install from. The instructions would name both, and say which comes first. (c) Leave the steps as they are ('Tag and push'). The instructions stay generic, and each release settles it by hand. In every option an agent would be told that only you push.


## Gaps closed

### `group_states`

Section 3 lists one open gap for these specs: states PROOF-45 (RULE-38). RULE-38 no longer exists in the spec, so nothing was left to close. The work below makes the tests look at real behaviour. For each new assertion I broke the source on purpose, saw the test fail, and restored it with git checkout. No test or break reaches the real `claude` program or any service. The tests only build payloads and status text in temporary git projects, and sign with a throwaway ssh key.
- PROOF-58 (RULE-49) used to compare two Python functions. It now compares the real dashboard with the status table. Breaks: the count separator in scripts/report/src/app.js, `·` to `-`, failed with "['3', '2 - 1 ...st', '1 of 3'] == ['3', '2 · 1 ...st', '1 of 3']". board.js writing `(+1 shared)` again failed with "['1 (+1 share...'] == ['1 (+1)', ...]". board.py DOT set to ' - ' failed at "'2 · 1 no test' != '2 - 1 no test'".
- PROOF-42 and PROOF-164 (RULE-35) now compare the test hash as well as the test list. The break made the tests backing a proof come from the first section alone. Both failed: "a local and a ci section did not make up one list", and the list assertion reported "At index 0 diff: 'test_the_windows_lock' != 'test_the_linux_lock'". The first version of PROOF-42 did not catch this break, because the Windows section named every test. It now gives each system a test of its own.
- PROOF-46 (RULE-39) now checks the exact two lines. Adding a third line to the empty-project message failed with "Left contains one more item: 'See the docs.'".
- PROOF-161 (RULE-25) is new: the six bucket counts appear in order at the gate `signed`. Swapping strong and signed failed at "At index 4 diff: 'signed' != 'strong'".
- PROOF-166 (RULE-42) now also checks that an agreeing file raises no warning. A reader that warns on every file failed with "assert not ['.purlin/evidence/ci/login.json was read.']".
- PROOF-103 and PROOF-165 (RULE-36) now check exact cells. Changing `n/a` to `none` failed with "'0 of 2 · none' == '0 of 2 · n/a'".
- PROOF-43 now checks exact cells. Changing `no test` to `without a test` failed.
- PROOF-179 (RULE-72) now checks the exact cell `2`. Writing `(+0 shared)` for a spec with no shared rule failed with "'2 (+0 shared)' == '2'".
- summary PROOF-28 (RULE-10) is new. Dropping the this-machine check failed with "'  2 rules to test on macOS and Windows: purlin:test --remote'".
- PROOF-16 and PROOF-159 (RULE-14) now run through a real project's payload, not straight into the state function.

### `purlin_report`

Section 3 of proofs-rewritten.md lists no gap for purlin_report, and sections 4 and 5 flag nothing for it. Reading the spec against its tests, I found two claims no test showed and closed them:
(1) PROOF-29 said the age recomputes 'with zero reads of the data file in between', and the test did not check it. It now asserts that the page holds exactly one frame, the page reading the data file through one frame per read. Broken on purpose by making the minute tick load the data file again: test_the_age_recomputes_every_minute_from_the_same_payload failed.
(2) PROOF-26 claimed the sentence 'the page shows it once it is committed' while the test checked only the sentence's start. It now asserts the whole sentence.
Every new assertion of decision 85 was broken on purpose in scripts/report/src and restored with git checkout. The page is a local HTML file opened by headless Chromium from a temporary folder, so nothing reaches claude or a service.
- The buttons counted from the rules instead of the payload: PROOF-130 and PROOF-131 failed.
- The FAILED badge removed: PROOF-165 and PROOF-168 failed.
- The hand-check condition removed from 'reached': PROOF-166 and PROOF-167 failed.
- `to_tag` made to filter rules: PROOF-133 failed.
- Choices made to pile up instead of moving: PROOF-14 failed.
- The last line dropped when nothing is left: PROOF-83 failed.
- The label keeping its count: PROOF-35, 86, 46, 130, 131, 14 and 133 and the passed-gate walks failed.
- The command line shown with no button chosen: PROOF-134 and PROOF-87 failed.
- Reasons drawn on the folded row: PROOF-75 and PROOF-112 failed on width.
Two further breaks targeted the unfolded reasons (rows missing, a finding repeated in the reasons). They failed the tests of PROOF-79 and 170 to 172 and 132 at the time. That code was then removed under decision 89.

### `run_script`

PROOF-10 (RULE-10), the case where a foreign proof's test is skipped here: the evidence now has to list PROOF-2 as `not run`, the product does, and the test fails when the product writes `missing`. PROOF-21 was already closed by PROOF-124 (freebsd14 reads linux), following decision 65.

Rule clauses that had no proof now have one:
- RULE-20: evidence that is not committed still reads `passed` (PROOF-162).
- RULE-58: a run over every feature runs the whole suite (PROOF-192).
- RULE-68: the first commit's subject (PROOF-203) and its printed file list (PROOF-204).

Proofs 130 to 133 now read what the run prints instead of the code's own table.

### `signatures`

- **What was open.** The only open item for signatures in section 3 was PROOF-73 (what the walk exits with when it refuses the tag). PROOF-73 no longer exists in the spec. The open part is an owner decision, so it is asked below rather than closed.
- **Section 4 and section 5, closed with tests against real behaviour:**
  - **RULE-6:** PROOF-127 shows a new audit finding ending a signature.
  - **RULE-10:** PROOF-14, 128 and 129 cover where the reader looks: the file beside the spec, copies elsewhere ignored, and copies alone counting as no signature.
  - **RULE-16:** PROOF-30 now runs a bare `login`. PROOF-130 shows `--all` lists its rules in the walk's order. PROOF-131 shows `--all` signs an anchor's rule once.
  - **RULE-45, RULE-46 and RULE-49 to 57:** the proofs run the walk instead of the tag step alone.
  - **RULE-42:** four cases, each read off a written signature.
  - **RULE-43:** six cases, one each.
  - **RULE-22:** three cases, each also checking the printed line.
  - **RULE-23:** two cases: the side branch, and main.
  - **RULE-63:** PROOF-143 adds the bare-feature case.
  - **RULE-64:** PROOF-144 shows the decision 85 change.
- **Breaks tried.** Each break was made in the source, the tests were seen to fail, and the file was restored with git checkout. No test starts the claude program or reaches a network: they start only git, ssh-keygen and Python, in temporary folders.
  - sign.py, unknown rule: stopping everything when one rule is unknown failed PROOF-144 with `assert [] == ['RULE-1']`. Exiting 0 on a mixed call failed it with `assert 0 == 1`.
  - sign.py, what waits: dropping the check that a rule is read once, as its own feature lists it, failed PROOF-131 ('Signed 4 rules', `secure RULE-1` listed 3 times). Skipping hand checks for a bare feature failed PROOF-30 (`['RULE-1'] == ['RULE-1', 'RULE-2']`).
  - sign.py, what `--all` prints and commits: listing the rules after `Signed` in reverse failed PROOF-130. Dropping the feature name from a batch subject failed PROOF-24. Committing each file on its own failed PROOF-90 (`'3' == '1'`).
  - sign.py, the evidence a signature names: reading the ci file first failed PROOF-135. Falling back to the ci path when there is no file failed PROOF-137. Leaving the path off the file failed PROOF-63 and PROOF-136.
  - sign.py, notes and the command line: putting the note on the first rule only failed PROOF-145 (`['I read both by hand.', None]`). Skipping the ending after `Nothing is waiting` for a bare feature failed PROOF-143. Changing the wording of the unknown-option message failed PROOF-132 and PROOF-133.
  - sign.py, the tag: ignoring the work left before tagging failed PROOF-68. The package step refused on its own, so the output differed from the summary ending.
  - signatures.py: making the reader also read `specs/<feature>.signatures` failed PROOF-128 and PROOF-129. Leaving the machines out of the comparison failed PROOF-120. Ignoring a system that has gone failed PROOF-122. Counting a new system failed PROOF-121. Leaving the audit hash out of the signed hash failed PROOF-127.

### `scaffold`

Section 3 listed two open gaps for this spec.
- PROOF-42: the gap asked for a test that the runner's job fails when the gate is not met or the evidence does not match the tag. Decisions 68 and 83 retired that: the separate check at the end of the job was removed, and the job fails only when a test fails or could not run. RULE-42, whose last step is the test run, together with run_script RULE-11, which exits on the tests alone, now covers it. There is nothing left to test in this spec.
- PROOF-44 (1): the unknown-host line now says what still works (decision 65), and PROOF-44 quotes it exactly.
- PROOF-44 (2): RULE-44's "either way" is reworded, and the host tool is now shown on both hosts: PROOF-78 and 79 (gh installed or not) and new PROOF-113 and 114 (az installed or not).

Coverage gaps closed as well:
- RULE-9 was shown for Vitest only. It now has Jest (PROOF-105) and C# (PROOF-106).
- RULE-14 was shown partly by calling an internal function. All four host URLs now go through init and the `ci` setting (PROOF-14, 67, 68, 107).
- RULE-35 checked only characters at or above U+1F000, so ✅ (U+2705) would have passed. It now allows plain ASCII plus the four glyphs → ▶ ▼ ▲ and nothing else.
- RULE-19 now shows that a pyproject block is appended once (PROOF-110).
- RULE-39's package-folder case (PROOF-123) is now shown through the written setup.cfg rather than an internal function.

Each new assertion was broken on purpose in the worktree and restored with `git checkout -- <file>`; every one failed as expected, and `git status` showed scripts clean afterwards. Nothing broken could reach the real `claude` (the fake is first on the path and checked) or a git host (local bare remotes or URLs that are never contacted). The breaks:
- ✅ put in front of the summary line: the emoji test failed.
- jest, then dotnet, dropped from the Stryker note: PROOF-105 and 106 failed.
- az renamed azcli: PROOF-113 failed.
- visualstudio.com no longer read as azure: PROOF-107 failed.
- Only https github URLs read as github: PROOF-14 failed.
- The pyproject block appended on every run: PROOF-110 failed.
- A folder holding only __init__.py not counted as source: PROOF-123 failed.
- The evidence README written as Purlin-owned: PROOF-125 failed.
- The dashboard reported as `wrote`: PROOF-109 failed.
- The gate always written as strong: PROOF-3 failed.
- The evidence subject cut to 8 characters (scripts/run/evidence.py): PROOF-36 failed.
- The audit dropped from the evidence: PROOF-117 failed.
- The tag-run line reworded (scripts/run/host.py): PROOF-91 failed.
- A run branch never read as one: PROOF-118 failed.
- `...` dropped from the signing line (scripts/review/sign.py): PROOF-119 failed.
- The release line reworded (scripts/mcp/purlin/summary.py): PROOF-93 failed.
- `to audit` renamed `to review`: PROOF-90 failed.

### `update`

From section 3, "Left, or closed in part":

update PROOF-8 (left). Decision 65 settled this: the upgrade now deletes the old cache outright. The case the gap named is a committed cache that .gitignore does not name. It is now PROOF-75 (RULE-8). The test takes `.purlin/cache/` out of .gitignore, commits the cache, applies the update, and asserts that nothing under the cache is tracked, the folder is gone and `untracked-files` is not pending. Break: I removed the line that deletes the cache folder. The test failed with "assert not True where True = any(...)": the cache was tracked again.

update PROOF-11 (closed in part). I removed the check that read the update's own source. The behaviour is shown for `report` true (PROOF-11, which now also checks the starting value) and for `report` false (PROOF-44).

From section 5, the flagged rules:
- RULE-5: the claim that `--yes` asks nothing is now observed. PROOF-5 records every prompt and expects none. Break: the confirm question was asked even under --yes; the test failed with "assert ['Apply desig... [y/N] ', ...] == []", 9 prompts. New PROOF-69: --yes at the gate strong with an engine available asks nothing and writes mutation off. Break: --yes returned 'auto'; the test failed with "assert 'auto' == 'none'".
- RULE-2: the rule now says the list is exact. PROOF-68 now asserts the full list with `hooks` in its place. Break: I moved hooks out of the migration list; the test failed with "At index 4 diff: 'config' != 'hooks'".
- RULE-12: already shown by PROOF-48.
- RULE-3: no longer in the spec.

New cases, each with its break:
- PROOF-72, a spec that two migrations rewrite keeps two backups. Break: no backup before the kind-of-test rewrite; the test failed, "Right contains one more item".
- PROOF-78, audit_parallel 8 is kept. Break: the project's value was ignored; "assert 4 == 8".
- PROOF-80, no runner file is offered when no proof names another system. Break: the reason check was skipped; "Left contains one more item: '.github/workflows/purlin.yml'".
- PROOF-97, a tests setting already written is kept. Break: the keep branch was removed; "assert [] == [{'name': 'py...'".
- PROOF-112, an older copy of the page is replaced. Break: stale bytes were written instead; "At index 1 diff: b'h' != b'!'".
- PROOF-18, the commit subject is now exact. Break: ids joined by a space; the assertion diff showed the missing commas.
- PROOF-76, a foreign pre-commit hook beside an old pre-push hook is kept. Break: any hook was taken; FileNotFoundError on pre-commit.
- PROOF-85, the vitest config is exact and its line is printed. Break: the reporter pattern was narrowed to jest; the diff showed the vitest reporter still there.
- PROOF-108 and PROOF-107, each prints its count line. Break: "markers" was always plural; the C# test failed on "rewrote 1 marker".
- PROOF-105, an anchor gets no scope advice. Break: anchors were not exempt; the test failed with the advice in the output.
- PROOF-104, the advice repeats when nothing is pending. Break: the advice was suppressed on that path; the test failed.
- PROOF-81, only the project's own file is left in the plugin folder. Break: .keep was dropped from the shipped names; "assert ['.keep', 'house_purlin.rb'] == ['house_purlin.rb']".

### `evidence_writer`

Section 3 of dev/plans/proofs-rewritten.md lists no open gap for evidence_writer. One more gap was found and closed. PROOF-42 ("a run on a host with no name writes `machine` `unknown`") was carried by a test that built a section directly, but a run works out the machine name itself before the writer sees it. That test could not see the run's own behaviour. It is now a whole `--all --test` run in which the host reports an empty name.

Every new or split test was broken on purpose; each break was restored with `git checkout -- <file>`, and bytecode caching was switched off so no stale compiled file could hide a break. Each break below made every test it names fail:
- The run's fallback name changed from `unknown` to `nameless`: PROOF-42.
- The repeat check also compared `at`: PROOF-59.
- The repeat check ignored the fingerprint: PROOF-61.
- The repeat check ignored rules and proofs: PROOF-60.
- A section already on disk was never replaced: PROOF-55 and PROOF-60.
- The file was written with non-ASCII characters raw: PROOF-4 and PROOF-55.
- The audit comparison read only the model: PROOF-65 to PROOF-70, all six.
- The audit comparison left the model out: PROOF-64.
- An audit entry was always replaced: PROOF-14.
- An audit write kept rules the spec dropped: PROOF-56.
- A section write kept rules the spec dropped: PROOF-5.
- Removal skipped the `local/` folder: PROOF-57 and PROOF-58.
- A rule with no proof and a failing marked test read `not run`: PROOF-71 and PROOF-73.
- A rule with no proof and no marked test read `not run`: PROOF-72.
- Marked tests of a rule with no proof were not listed: PROOF-15, PROOF-71 and PROOF-73.
- The runner slug kept dots: PROOF-74.
- The no-repository line lost its first half: PROOF-11.
- `.purlin/tests.md` was added to the ignore lines setup writes: PROOF-13 and PROOF-63.
- `.purlin/evidence/` was added to this repository's .gitignore: PROOF-62.
No break reached the real `claude` program: every test runs under dev/conftest.py, which puts a fake `claude` first on PATH, and the breaks touched only scripts/run/evidence.py, scripts/run/purlin_run.py, templates/gitignore.purlin and .gitignore.

### `reports`

Section 3 of dev/plans/proofs-rewritten.md had one partly closed gap for this spec: PROOF-5, whose rule said a marker's result is `not run` while the evidence records `missing`. RULE-5 now says `not run`, "which the evidence writes as `missing`". That is what references/formats/marker_format.md specifies and what PROOF-5 asserts.

These gaps were found while reading and are now closed. Each new assertion was broken on purpose in the worktree, seen to fail, and restored with `git checkout -- <file>`:
- PROOF-84, RULE-16 "from the project root", was untested. Broken by changing `cwd=project_root` to `cwd=None` in purlin_run.py's `_run`; the test failed with `assert not True` because where.txt landed in the outside folder.
- PROOF-86, a report folder read file by file, is now shown through a run with two TRX files. Broken by reading only the folder's first file; the run's evidence lost PROOF-2.
- PROOF-78, a test partly skipped and otherwise passing reads `not run`, was untested. Broken by counting pass-or-skip as pass; the test failed with `assert 'pass' == 'missing'`.
- PROOF-79, a test the report holds no case of, now goes through a run with a canned report. Broken by making result_of return pass for no cases: `{'PROOF-2': 'pass'} != {'PROOF-2': 'missing'}`.
- PROOF-13 now marks both declarations and goes through a run. Broken by counting an ambiguous case for its first match; the test failed.
- PROOF-93, RULE-18's `wrote no report in <path>` for an empty folder, was untested. Broken by changing `in` to `at`; the test failed.
- PROOF-90, `purlin` misspelled by one letter, had no RULE-22 proof. Broken by changing the why text; the test failed.
- PROOF-91, a RULE id one character off, was untested. Broken by leaving rules out of the known ids; the comment was no longer listed.
- PROOF-92, a feature one character from two specs, was untested. Broken by taking the first candidate; the comment was listed.
- PROOF-56 now covers the C# attributes the product reads beyond the first five. Broken by removing `TestCaseSource` from the attribute pattern; the test failed.
- PROOF-60, a line that is not JSON, was an unstated part of PROOF-9. Broken by removing both guards around json.loads; JSONDecodeError.
- PROOF-8 now asserts the report's order, so the rows `x: 2` pass and `x: 1` fail are told apart. Broken by sorting the TRX cases; the test failed.
- PROOF-29 now asserts the exact usage line. Broken by changing `--project-root` to `--root` in it; the test failed.

The runs these tests start are pytest, bash, cat, cp, mkdir and printf in temporary projects. None reaches `claude` or any service.

### `ai_audit`

Section 3 of dev/plans/proofs-rewritten.md lists no open gap for ai_audit. I closed these, and broke the source on purpose to see each new test fail:
- **RULE-1, flagged because a stale audit entry was only shown for a text change.** New PROOF-53 covers a changed proof and PROOF-54 a changed test line. Break: I made the audit entry ignore the proof's fingerprint, then the test's. Each test failed with `assert not {'verdict': 'strong', ...}`.
- **RULE-1, which rules are read, now shown on real projects.** New PROOF-48 (a `@manual` proof), PROOF-49 (a required rule), PROOF-50 (the gate `signed`) and PROOF-51 (read again). Breaks:
  - dropping the manual check failed with `assert True is False`
  - dropping the label check failed with `assert [True, True] == [False, False]`
  - skipping a rule that has a signed cell failed PROOF-50
  - ignoring "read again" failed PROOF-51
  - dropping the passed-cell check failed PROOF-2
- **RULE-3, flagged because closing the input was shown only indirectly.** PROOF-13 now claims `claude` reads the whole prompt from its standard input to the end. Break: I started the program with its input left open (limit 5 s). The test failed: the answer was the timeout reason, not `strong` (KeyError 'verdict').
- **RULE-4.** New PROOF-56: two rules, four at a time, both calls run together. Break: one call at a time when there are fewer rules than asked for. It failed.
- **RULE-5.**
  - PROOF-22 is now a finding line with no settled line. Break: such findings read `weak`. It failed.
  - New PROOF-57 is an empty answer. Break: an empty answer reads `strong`. It failed.
- **RULE-6.** The model is now read off the JSON the program prints, not off an internal function.
  - Naming the last model listed failed PROOF-59 (`'claude-haiku-3-5' == 'claude-opus-4-1'`).
  - Naming the first model listed failed PROOF-21.
  - Naming the model that sorts last by name failed PROOF-60.
  - Ignoring a top-level model failed PROOF-61 (`'unknown' == 'claude-x-1'`).
  - Returning '' for no model failed PROOF-58.
- **RULE-7.** New PROOF-62. Break: no second ask. Both PROOF-26 and PROOF-62 failed.
- **RULE-10.** New PROOF-36, 64, 65 and 66 each read a real Python, C# or TypeScript file. Each failed when its separator or its argument stripping was removed. The TypeScript case failed only with both ' > ' and ' ' removed as separators.
- **RULE-11.** The regex and comment cases now hold a `)`, the character that cuts a body in a reader that balances the call's brackets.
  - No character class failed PROOF-68.
  - No escape failed PROOF-69.
  - A line comment read as code failed PROOF-70, and so did a block comment read as code.
  - Counting no nesting failed PROOF-9.
  - A pattern running past its line failed PROOF-10.
  - PROOF-67 (apostrophe) failed only when double-quoted strings were not skipped AND a quoted string ran past its line. With one of the two, it held.
  - PROOF-71 (two one-line divisions) failed only when every `/` started a pattern AND a pattern ran past its line. With one of the two, it held.
- **RULE-12.** The check now compares every file's bytes under `.purlin/`, runtime included, not only the names. Breaks: appending to the runtime file while reading, writing a file while asking, and writing a file from the command. Each failed its test.
- **RULE-13 and RULE-14.** Now shown through the command's own output: the usage line, `ai_audit.py: unexpected argument --nope`, `ai_audit.py: --feature is required.`, `audit: no rule of nothing is in this project.`, exit 1 for an unknown rule, the findings, no emoji, `Nothing yet...`, and every rule printed. Each failed when I broke its message, its exit code or its line, or made the output carry an emoji.

### `host`

- Section 3 listed three host gaps; all three are handled, one in full and two as far as these files allow.
- PROOF-8 (listed as "left", a product fault): the product was fixed under decision 65. PROOF-52 and its test (the push names refs/heads/run/main-4f1c2ab when BUILD_SOURCEBRANCH carries the whole ref) are in place and pass. The case "the last part of the ref alone commits nothing" and the case "the whole ref is read first" are now separate proofs, PROOF-104 and PROOF-105.
- PROOF-30 (closed in part): RULE-26's proof now shows something a caller sees. With no workspace variable set, a CI commit from a project in a temporary folder sends its tree and its commit and prints nothing. Before, the proof only reported an internal yes or no. The refused and allowed cases for each variable are RULE-27's four proofs: 32, 96, 97 and 98. Whether RULE-26 should exist at all is question 1.
- PROOF-26 (closed in part): the Windows path spelling is now shown by the tree the CI commit sends (PROOF-95: the tree holds retired.json alone with no blob id), no longer by a function's answer.
- Two gaps from section 5 were also closed:
  - The GitHub lookup retry is now its own proof, PROOF-69.
  - "Carries nothing of Purlin in its tests" now has its own proof, PROOF-85, and "its own tests pass" is shown by running the fixture's own test file (PROOF-86), not by calling its module.
- The 60-second and 90-minute limits are now shown at their shipped values (PROOF-70, 80, 81), not shortened.

### `drift`

Section 3 of dev/plans/proofs-rewritten.md lists no open gap for drift: it was one of the three example specs left untouched. I tightened what several proofs claim so that each is shown by real behaviour. Each new assertion was checked by breaking scripts/mcp/purlin/drift.py on purpose, running the one test, and restoring the file with git checkout --. Every break made its test fail:

- **PROOF-38** (a moved spec is named nowhere). Break: a spec is matched by its path instead of its name. The test failed with "['1 rule added: specs/b/other.md RULE-1.', '1 rule removed: specs/a/other.md RULE-1.']".
- **PROOF-19** (unpinned, now through the report). Break: the command was cut from the unpinned line. The test failed with "'anchor policy names a source and no pin.'".
- **PROOF-40** (error, now through the report). Break: the line drops git's reason. The test failed with "anchor policy: its source could not be read (None)."
- **PROOF-41** (an anchor at its pin gets no row, now through the report). Break: current anchors are no longer filtered out. The test failed with "assert [{'anchor': ... 'current' ...}] == []".
- **PROOF-20** (a source beginning with a dash). Break: only `-x` is refused. The test failed.
- **PROOF-44** (NUL byte, now through a real spec file). Break: the NUL check looks for byte 1 instead. The test failed with "ValueError: embedded null byte".
- **PROOF-45** (newline). Break: only a carriage return is refused. The test failed, and git then read the local path "/srv/anchors.git --upload-pack=x" and found no repository.
- **PROOF-46** (new case that is not refused, `https://github.com/acme/ext-rules.git`). Break: any source holding `ext` is refused. The test failed with a row reading error.
- **PROOF-21** (one listing per source, now 3 anchors of one real local repository through the report). Break: the listing is not kept for the run. The test failed with 3 listings.
- **PROOF-22** (the row's name; the source now also names the file `constraints.md`). Break: the row is named by the source. The test failed.
- **PROOF-28** (new assertion: no space after the item separator). Break: the separators became (', ', ':'). The test failed with "payload still carries a space after the item separator".
- **PROOF-35** (a plain commit after a merge is not an action). Break: every commit is taken as a merge. The test failed with commits 1.

Before any break I checked what each test starts. Every source a broken path could hand to git is a local path. The two github.com sources are only used where drift stops before any listing, and no break touched that stop or the ext:: and fd:: checks. Nothing reached a remote host or the claude program.

### `evidence`

The report listed one gap for this spec, PROOF-9 (RULE-5), as closed in part. It is still open: see gaps_left. While splitting, I added proofs for parts of rules that had none:
- PROOF-37: the glob `src/**/*.py` reaches `src/login.py`, which sits directly in `src`.
- PROOF-41: scope entries that reach nothing add nothing to the `code` part, which equals the `code` part of a scope naming `src/login.py` alone.
- PROOF-45: a marked file under `node_modules/`, `bin/`, `obj/`, `mutants/` or `.cache/` is not counted.
- PROOF-47: a file git ignores is not listed as untracked, next to one that is.
- PROOF-53 and PROOF-54: a system naming itself `win32` reads `windows`, and `darwin` reads `macos`.
- PROOF-18, PROOF-19, PROOF-51 and PROOF-52: the load warnings are now checked word for word.

Breaks tried in the worktree. Each file was restored with `git checkout -- <file>`, and `git status` showed only my own files after every run. The tests start only `git`, never `claude` and never a service.
0. specs.py, `'is_global': is_anchor and bool(...)` changed to `'is_global': is_anchor`: PROOF-35 failed (and the older PROOF-4 test).
1. fingerprint.py, the glob pathspec given `entry.replace('**/', '*/')`: PROOF-37 failed.
2. `_GLOB_CHARS = ('*', '[')`: PROOF-39 failed.
3. `_GLOB_CHARS = ('*', '?')`: PROOF-40 failed.
4. An unmatched entry added to the scope's files: PROOF-9, PROOF-41 and PROOF-42 failed.
5. The scope read with `--cached --others`: PROOF-42 and PROOF-13 failed.
6. markers.py, `SKIP_DIRS = ()`: PROOF-45 failed.
7. The dot-folder skip removed (`return name in SKIP_DIRS`): PROOF-45 failed.
8. `--exclude-standard` taken off the scope's untracked listing: PROOF-47 failed.
9. The suite check made `return True`: PROOF-44 failed.
10. The not-JSON warning given the not-an-object words: PROOF-18 failed.
11. The schema warning without `not purlin-evidence/2`: PROOF-52 failed.
12. Prefix `win` changed to `windows`: PROOF-53 failed.
13. Prefix `darwin` changed to `macos`: PROOF-54 failed.
14. Every marker file also indexed under `login`: PROOF-43 failed.
15. `'is_global': False`: PROOF-5 failed.
Each break made 1 to 3 tests fail, and the other tests passed.

### `package`

Section 3 of proofs-rewritten.md lists no open gap for `package`. Two gaps turned up while reading the rules, and both are now closed with tests against the real export command:

- **PROOF-30 (RULE-3).** A code change committed after the evidence is the commit the package names. Break: in scripts/export/package.py, the walk that finds the evidence commit was made to step over any commit that does not touch `.purlin/evidence/`. The new test failed with `assert '2dca67c38ebd...' == 'e1976381abe0...'`. Restored with `git checkout -- scripts/export/package.py`.
- **PROOF-31 (RULE-7).** A signature written and not committed is left out of the package and named. Break (a): uncommitted signature files were no longer counted as left out. The test failed because the terminal printed only `Evidence package written to .purlin/evidence/package/2.1.0.json. State: not finished.` and no line for `specs/auth/login.signatures/RULE-2.22d0e163.jane.json`. Break (b): the package was built from the working folder instead of a checkout of the commit. The test failed with `Left contains one more item: {'applies_to': 'login', ... 'committed_at': None ...}`, and PROOF-12's test failed too. Both restored.
- **PROOF-33 (RULE-9), a tighter check.** The test now checks the whole printed line, where it used to check only that the line contained `not in the canonical form`. Break: the message was cut to `the bytes differ`. The test failed with `['The package does not match its fingerprint: the bytes differ.'] != [... 'but the bytes are not in the canonical form.']`. Restored.

The tests start only the package command, git, ssh-keygen and the sign module, all inside temporary folders. I checked that nothing in the export or sign code reaches `claude` or the network before breaking anything.

All three breaks were run with the test file whole, except that one view used -k to read a single failure message. Acceptance was run whole.

### `mutation`

- PROOF-22, which was closed only in part, is now split into PROOF-22 and PROOF-64 to PROOF-67.
- PROOF-67 is the whole run. `purlin_run.py --project-root <p> --all --audit --arm-timeout 1` runs as its own process in a fixture project at the gate `strong`, with `mutation_engine` set to `mutmut`. The project has a spec with `> Scope: src/login/session.py`, a marked test that passes, and the `[tool.mutmut]` block. Its stand-in mutmut sleeps 60 s on `mutmut run`, and the session's fake `claude` is the only model reachable.
- The test checks four things: the run ends within 30 s; mutmut was started once, as `run`, and never asked for results; the output carries the line `purlin: the engine timed out after 1 s, so the breaks it made are partial and measure nothing: raise --arm-timeout to give it longer`; and `.purlin/evidence/local/login.json` holds `audit.mutation` with engine `mutmut` and score null.
- Breaks shown to fail it: dropping `mutation_module.ARM_TIMEOUT = args.arm_timeout` in scripts/run/purlin_run.py; stopping the run script from printing the reason; and making the engine runner return 0 on a timeout.
- The Stryker and Stryker.NET timeouts (PROOF-65, PROOF-66) are no longer stood in by an exit code. The stand-in programs really sleep and are really killed by the shared runner at a 3 s limit. PROOF-22 and PROOF-64 do the same for mutmut at a 1 s limit.
- Section 4 of the report listed proofs that hold several things: 5, 12, 13, 14, 15, 17, 20, 21 and 22. All of them are split, and so are 1, 2, 3, 6, 7, 9, 10, 11 and 16.
- Section 5 flagged rules: RULE-8, 9, 10 and 19 are reworded, and RULE-5's "once per feature" is now shown by PROOF-34, which counts exactly two starts over two features. Separately, RULE-17 and RULE-21 are reworded to what a caller sees.
- New proofs cover mutmut's own statuses (PROOF-39), a break that timed out being credited (PROOF-41) and a folder scope (PROOF-58).

### `skill_sign`

Section 3 of dev/plans/proofs-rewritten.md lists no open gap for skill_sign. I closed these gaps between the spec and its tests:

- **PROOF-4 (RULE-4):** it claimed a file past 185 lines is reported, but no test showed that. It is now split into:
  - PROOF-36: a copy lengthened to exactly 185 lines is let through.
  - PROOF-37: a copy lengthened to 186 lines is reported as 186 lines against the ceiling of 185.
- **PROOF-5 (RULE-5):** it said "exactly two rows", but nothing showed a third row is refused. PROOF-39 now adds a third row and sees it reported.
- **RULE-2, `left`:** the rule names each rule's `left`, but the check never read it. PROOF-2 now requires `left` after the `sync_status()` call.
- **RULE-2, "before it writes anything":** this was proved only by the order of the two script paths. PROOF-30 now checks the sentence `Read what the audit read and found for a rule before anything is written`.
- **PROOF-3 (RULE-3):** it said every outcome carries a `→`, but the check lets `Nothing left to do.` through without one. The proof now says so.

Breaks tried on purpose in the worktree, each restored with `git checkout -- <file>`. The tests only read text; nothing starts `claude` or any service.

| What I broke | What failed |
|---|---|
| Renamed `left` to `state` in the section on what waits | test_what_waits_is_read_from_sync_status (PROOF-2) |
| Cut "before anything is written" | test_it_says_to_read_what_the_audit_found_before_writing (PROOF-30) |
| Removed the purlin:sign row from references/purlin_commands.md | test_the_command_reference_carries_a_row_for_sign (PROOF-23) only |
| Wrote the description as a `\|` block | test_the_frontmatter_names_the_skill_on_one_line (PROOF-1) only |
| Lengthened the skill to 186 lines | PROOF-4, 36 and 37 |
| Changed the ceiling check to `>=`, in dev/skill_checks.py, restored at once | PROOF-36 |
| Changed the ceiling check to `> ceiling + 1` | PROOF-37 |
| Added a third row to the table `A signature counts when` | PROOF-5 |
| Cut `this skill never pushes` | PROOF-42 |
| Cut `offer to write it to a VERSION file at the root` | PROOF-43 and PROOF-20 |
| Swapped `package.json` and `pyproject.toml` | PROOF-19 |
| Swapped the package line and the tag line | PROOF-40 and PROOF-17 |

### `upstream`

Section 3 of proofs-rewritten.md lists no open gap for upstream, and section 4 lists no upstream proof that holds several things. I closed these gaps, found while reading. For each, I broke scripts/anchor/upstream.py on purpose, ran the test and saw it fail, then restored the file with `git checkout -- scripts/anchor/upstream.py`. Each break was confirmed caught:
- PROOF-1: the copy, with its two tracking lines taken out, now has to match the author's file byte for byte. Break: the tracking strip also removed the author's `> Type:` line. The test failed on the byte comparison.
- PROOF-4: the copy's single `> Source:` and `> Pinned:` lines now have to carry this project's source and its full sha. Break: the pin was cut to 7 characters. Failed with `['> Pinned: 03677fa'] == ['> Pinned: 0...dfb82e1caecf']`.
- PROOF-8: every file in the project, not just the copy, has to be unchanged after `sync --check`. Break: the check fetched the source into the project. Failed on the snapshot of the files.
- PROOF-15: the test now counts the real processes that name the repository, instead of spying on an internal call. Break: the per-run cache of a source's head was dropped. Failed with `assert 2 == 1`.
- PROOF-14: no process started by `sync` may name the text file. Break: every anchor with a source, free text included, was queried with ls-remote before the filter. The rows still read right, and the new check failed: `assert not True`.
- PROOF-29: a text file named by its full path gives `no_rules` and starts no process.
  - First break: a readable file no longer won over the repository-address test. Failed with `'error' == 'no_rules'`.
  - Second break: add asked git about the file first. Failed on the list of started processes.
- PROOF-35 and PROOF-12: the copy itself now has to lose `RULE-2`, and its pin has to move. Break: sync reported the changes but did not rewrite the copy. Both tests failed.
- PROOF-34: the whole printed line is now checked. Break: the line named `purlin:anchor create` in place of `purlin:anchor sync`. Failed.

Safety: these tests start only `git` (on local bare repositories in pytest's temporary folder) and the Python interpreter. Nothing reaches the network, the real `claude` program or any service. The refused `ext::` source never reaches git: no break touched the check that refuses it, and git refuses the ext transport by default in any case.

### `skill_test`

Section 3 of dev/plans/proofs-rewritten.md lists no open or partly closed gap for skill_test, so there was no listed gap to close.

While splitting, these checks were made stricter so that each proof claims only what its test shows:
- PROOF-40 now checks the whole line printed when nothing is selected, including its second sentence "purlin:test --all runs them anyway.". This settles the RULE-6 flag in section 5.
- PROOF-32 now checks that the two commit subjects appear in order; PROOF-37 is the refusal when they are swapped.
- PROOF-3 now checks that the closing heading carries "next step". The shared check also accepts "when you are done".
- PROOF-12 and PROOF-44 now check each row of the section on a run that stops, not the section as a whole.
- The old PROOF-4 claimed a refusal no test carried out. PROOF-30 (a copy of exactly 120 lines is not reported) and PROOF-31 (121 lines is reported as "121 lines, ceiling 120") now carry it out.
- PROOF-24 (a `>` block description) and PROOF-29 (the "cannot make an audit or a signature appear" sentence reworded) are new refusals.

Each stricter or new assertion was broken on purpose in the worktree by editing skills/test/SKILL.md, then the file was restored with `git checkout -- skills/test/SKILL.md`. The tests only read text and start no program, so nothing could reach `claude` or any service. Each break and the tests that failed:
1. " purlin:test --all runs them anyway." removed from the nothing line: test_the_shipped_paragraph_carries_the_whole_nothing_line failed.
2. The two commit subjects swapped: test_the_shipped_skill_names_the_two_commits_in_order and test_a_copy_with_the_two_commits_swapped_is_reported failed.
3. "## Step 6: name the next step" renamed "## Step 6: when you are done": test_the_shipped_closing_section_directs_every_outcome failed.
4. "run Step 1 again" taken out of the no-tool row only: test_the_shipped_row_for_no_tool_reads_proposes_and_runs_again failed.
5. "Show the person the command and ask. On yes, write" changed to "Write": test_the_shipped_row_for_a_suggestion_asks_writes_and_runs_again failed.
6. The cannot sentence reworded: test_the_shipped_skill_says_a_run_cannot_make_an_audit_or_signature failed.
7. The skill padded to 121 lines: test_the_shipped_skill_is_at_most_120_lines failed.
8. "there is no settings file, " removed from exit code 1: test_the_shipped_skill_gives_each_exit_code_its_meaning_on_one_line failed.

### `specs`

Section 3 lists one open gap for `specs`: PROOF-17 (RULE-15), what a fourth `[level: ...]` value does. Commit fb2363868 (decision 73) already deleted RULE-15 and the level tag, and PROOF-17 now serves RULE-3, so nothing was left to close.

Section 5 flagged three rules. RULE-15 is deleted. RULE-3 is now shown for both hashes, with spaces and with a line break (PROOF-3, PROOF-4, PROOF-19). RULE-9's clause "rather than split on its first word" now has two examples (PROOF-30, PROOF-31).

Gaps found while reading, closed with new checks against the real reader and the real status report:
(a) RULE-8's limit of five files. PROOF-27: seven carrying specs give one warning that names five and ends `, and 2 more`.
(b) RULE-8's "absent when no spec carries such a tag". PROOF-28 now reads a real project's warnings. The old test built a cleaned-up copy of the reader's output instead.
(c) The other side of RULE-10. PROOF-32: `> Path:` does not replace a path the source line already names.

What I broke on purpose in scripts/mcp/purlin/specs.py, one break at a time, restoring the file with `git checkout --` after each. The tests only read temporary projects and start no `claude` and no service. Every break failed at least one test:
- Five changed to six: PROOF-27 failed.
- No count of the rest: PROOF-27 failed.
- A warning when nothing carries a tag: PROOF-28 failed, `assert ['0 spec file...oes not read'] == []`.
- The path field always wins: PROOF-32 failed.
- `@smoke` listed as an unknown tag: PROOF-21 failed, `['@smoke']`.
- `macos` removed from the systems: PROOF-6 failed.
- The two anchor conditions joined with `and`: PROOF-33, 34 and 38 failed.
- Every spec made an anchor: PROOF-35, 14 and 37 failed.
- No walk into what a required spec requires: PROOF-37 failed.
- An anchor allowed to follow its requires: PROOF-38 failed.
- Only undecodable files skipped: PROOF-41 failed with PermissionError.
- Only unopenable files skipped: PROOF-39 failed with UnicodeDecodeError.
- Specs keyed by title: PROOF-15 failed, `['login']`.
- Line breaks not normalised: PROOF-3 and PROOF-19 failed.
- Spaces not normalised: PROOF-3, 4 and 19 failed.
- A second `@env` merged over the first: PROOF-7 failed.
- `@env(bsd)` not listed: PROOF-23 failed, `[]`.
- `Visual-Hash` forgotten: PROOF-26 failed.
- A stamped `@manual` no longer manual: PROOF-24 failed.
- Any source split on its first word: PROOF-30 and PROOF-31 failed.

### `skill_audit`

Section 3 of dev/plans/proofs-rewritten.md lists no open gap for skill_audit. I still added 12 broken-copy proofs so that each claim a proof makes has a matching refusal:
- a `>-` block description;
- a command row with an empty purpose cell;
- a closing section without "the first line of `Left to do`";
- a copy of exactly 105 lines, not refused, and one of 106 lines, refused with its count;
- no `.purlin/evidence/ci/` named;
- a passed row without `not measured`;
- a strong row without the breaks;
- a signed row without `counts here too`;
- a `--commit` sentence with another subject.

The other new proofs are the old combined proofs split one case to a test.

To check that the tests fail when the product is wrong, I broke the real files and restored each with `git checkout --`. These tests only read files; nothing starts `claude` or any service.
- Description turned into a `>-` block: the frontmatter test and the ceiling test failed.
- ` and the newest audit entry per rule` deleted: PROOF-44 and PROOF-47 failed.
- The signed row set to `Runs the tests`: PROOF-38, 14 and 42 failed.
- `Nothing left to do.` outcome renamed: PROOF-3 and 10 failed.
- `you never run it by hand.` reworded: PROOF-26, 28 and 29 failed.
- The `purlin:audit` purpose cell emptied in references/purlin_commands.md: PROOF-17 failed.
- `strong` dropped from the local row: PROOF-5 and 34 failed.

### `skill_init`

Section 3 of dev/plans/proofs-rewritten.md lists no open gaps for skill_init. The four multi-case proofs section 4 lists are split: PROOF-1, 2, 5 and 6. So are PROOF-3, PROOF-4 and PROOF-7, and every refusal now has a proof and a test of its own. Beyond that, I closed the places where a rule speaks about setup but the old tests read only the skill's text:
- RULE-2's "no flag the script does not take" is now checked against the script's real `--help` output (PROOF-24, PROOF-9), not a hard-coded list.
- RULE-5's "the questions init asks, in order and no others" is now checked against a real setup run:
  - PROOF-32: at `strong`, exactly the 2 questions, worded as the skill quotes them.
  - PROOF-33: at `passed`, only the gate question.
  - PROOF-34: the gates are offered in the order passed, strong, signed.
  - PROOF-35: pressing Enter at the second question leaves mutation off.
- RULE-6's "the settings file init writes" is now checked against the keys a real setup writes (PROOF-38).
Every new assertion was shown to fail when I broke the behaviour it checks (details under for_integration).

### `security_no_dangerous_patterns`

- PROOF-6 (listed as closed in part). The HEAD question and the drift count and date runs were already settled by decision 65 and by PROOF-12 and PROOF-13.
  - This lane made the refusal check meaningful. Each hostile source now ends in `.git`, so it would reach `git ls-remote` if the refusal were missing, and each source is its own proof (PROOF-6, 47, 48).
  - Each proof now requires the exact status line, `<anchor>: (source rejected: <reason>)`.
  - Break, in scripts/mcp/purlin/drift.py: removed the lines that refuse a source beginning with "-". The test printed "AssertionError: '--upload-pack=/bin/echo /tmp/policy.git' reached a command; RULE-6 refuses it before any subprocess starts: [['git', 'ls-remote', '--end-of-options', '--upload-pack=/bin/echo /tmp/policy.git', 'HEAD']]". Run on the old values, the same break was caught only by the status-line assertion.
  - Break, in scripts/mcp/purlin/status.py: changed '%s: (source rejected: %s)' to '%s: (refused: %s)'. PROOF-6, 47 and 48 all failed.
- PROOF-4 (listed as closed in part). A name containing the word, not only ending in it, is already matched on main, and `TOKEN_NAME = "abc"` is planted (PROOF-7), so nothing was left to close.
  - Break: added `API_TOKEN = "abc"` to scripts/mcp/purlin/drift.py. The scan test failed.
- New assertions that each finding names its form (PROOF-14 to 20, 24 to 27, 29, 30) and its file (PROOF-35 to 45). The checks live in the test file, so each was broken there and restored with `git checkout -- dev/test_security.py`:
  - Dropping `passthru(` from the PHP forms failed test_php_forms_are_found.
  - Renaming the `.ts` forms failed test_typescript_forms_are_found.
  - No longer reading the JS and TS `:` field failed test_a_credential_field_in_javascript_or_typescript_is_found.
  - Dropping Popen from the string-argument form failed test_python_popen_given_a_string_is_found.
  - Reading comment lines failed the two comment-boundary tests (PROOF-22, 31).
  - Added `x = eval('1')` to scripts/mcp/purlin/drift.py: the RULE-1 scan test failed.
- Safety. Before each product break I checked what the test starts: only local git, on a temporary project and on `/tmp/policy.git`, which does not exist. The ext:: and fd:: refusals were never broken. Nothing reaches `claude` or any service.

### `skill_export`

Section 3 of proofs-rewritten.md lists no open gap for skill_export. Three places where an old proof claimed more than its test showed are now covered:
- The old PROOF-3 said a copy without the no-claim sentence fails, but no test tried that copy. It is now PROOF-26, with its own test.
- The old PROOF-6 said a skill padded past 90 lines fails, but no test tried it. It is now PROOF-32 (91 lines fails, naming "91 lines, ceiling 90"), with a boundary case, PROOF-33 (exactly 90 lines passes).
- Section 5 noted that the shared closing check also accepts a last heading reading "when you are done". This file now checks for the words `next step` itself. PROOF-31 shows a copy headed "When you are done" fails.

The checks were also tightened past what the shared helpers did:
- The state table must name exactly `finished` then `not finished` (PROOF-4, and PROOF-28 for the refusal).
- The `not finished` row itself must say that `left` holds the lines of `Left to do` (PROOF-27).
- The closing table must have 5 outcome rows, and every line must begin with `→` (PROOF-30).

The frontmatter proof, which held six cases, and the command-reference proof are split. Each description refusal is now its own proof: empty, moved to the line below, a `|` block, run on (PROOF-15 to PROOF-20).

### `schema_spec_format`

PROOF-4 gap (closed in part before): new PROOF-19. At the gate `passed`, a rule with no proof line has one passing test marked `purlin: feat RULE-1`. After a real test run, the rule has no proof and its passed cell reads `passed` with no reason. To check that the test can fail, I changed the no-proof branch of the passed cell in scripts/mcp/purlin/states.py (`if not rule_id or not (...)` became `if True or not (...)`). The test then failed at `assert (cell['word'], cell['reasons']) == ('passed', [])`.

Each split test was also broken on purpose and restored with `git checkout -- <file>`. Every one failed, as follows:
- PROOF-2: changed the warning's closing text in payload.py. It failed on the full warning line.
- PROOF-11: made the stack field read a `> Note:` line. It failed with "the note 'Ask the security lead before the first sync' reached what is read".
- PROOF-21: made a name no spec carries add a `RULE-1`, both in the list of required rules and in the payload. It failed with "Left contains one more item: ('ghost', 'RULE-1', 'required')". Breaking the rule list alone was not caught, because the payload already skips a feature that does not exist, so both places had to be broken.
- PROOF-22: sorted the scope. It failed with "At index 0 diff: 'src/alpha.py' != 'src/zeta.py'".
- PROOF-17: made the rule brackets optional in the proof-line pattern. It failed (AttributeError: 'NoneType' object has no attribute 'split').
- PROOF-35: let a tag be read anywhere in the text, not only at the end. It failed with "assert 'macos' is None".
- PROOF-44: accepted a trailing `s` on a section heading. It failed with "At index 1 diff: {'PROOF-1': ...} != {}".
- PROOF-23: hashed the scope file's folder. It failed with "a file outside the scope changed the fingerprint".
- PROOF-24: hashed no file. It failed with "a file inside the scope did not change the fingerprint".

Every proof that held several cases is split: PROOF-1, 2, 3, 4, 5, 6, 9, 10 and 12, which were all section 4's items and more. Each case now has its own test and marker.

### `purlin_agent`

Section 3 of dev/plans/proofs-rewritten.md lists no open gap for purlin_agent. Three gaps closed while reading:

1. **Too-long agent definition.** PROOF-6 said a file past 135 lines fails, but no test showed that. PROOF-39 now shows a copy of 136 lines is refused with "agents/purlin.md is 136 lines, ceiling 135". PROOF-38 shows the boundary: a copy of exactly 135 lines is not refused.
2. **Reworded first NEVER.** The existing test had a broken copy whose first NEVER was reworded, but no proof claimed it. It is now PROOF-27.
3. **New cases:**
   - PROOF-20: prose above the frontmatter.
   - PROOF-29: the third NEVER without "never write a tag yourself".
   - PROOF-32: the fourth NEVER without "No emoji anywhere".
   - PROOF-37: `no proof written` given another meaning.
   - PROOF-45: "Nothing more to do." in place of "Nothing left to do.".
   - PROOF-46: the summary without "30 are strong.".

The positive NEVER check now also asks for the tag and emoji wording.

**Breaks tried.** Every test only reads text files, so nothing reaches the real claude program or any service. Each break was restored with git checkout, or from a saved copy for the test file:
- The tag clause removed from the third NEVER in agents/purlin.md: PROOF-3's and PROOF-29's tests failed.
- "No emoji anywhere, including command output." removed: PROOF-3's and PROOF-32's tests failed.
- One line added to the agent (136 lines): PROOF-6's test failed.
- A line of prose put above the frontmatter: PROOF-1's test and the four other frontmatter tests failed (the PROOF-6 test also failed, since the file then had 136 lines).
- The meaning of `no proof written` changed: PROOF-5's and PROOF-37's tests failed.
- "Nothing left to do." changed: PROOF-11's and PROOF-45's tests failed.

To show the new refusal tests fail when the check stops refusing, I broke the checks in the test file:
- The frontmatter check no longer asked for an opening block: PROOF-20's test failed.
- The ceiling read as 136: PROOF-39's test failed.
- The Left to do check dropped the summary: PROOF-46's test failed.

### `skill_build`

- **PROOF-3 (RULE-3), listed as left.** Decision 65 has since put a `→` on every one of the build skill's five closing outcomes, and the test now checks every outcome.
  - Break: I deleted ", `→ Run: purlin:test --remote`" from skills/build/SKILL.md and the test failed. I also made the section say where the next step comes from (PROOF-3). Replacing "`purlin:test` ended on the summary and `Left to do`. Name the next step from them:" with "Name the next step:" failed it. PROOF-33 is the refusal for that change.
- **PROOF-6 (RULE-6), listed as left.** The rule described what a build does, which no text check can show. It now says what the skill tells the agent, which is what the test reads. I added PROOF-39, a copy without the delete step, as its refusal.
  - Break: I changed "rewrite the line in the same commit as the code" to "rewrite the line later" and the test failed.
- **PROOF-5 (RULE-5), listed as closed in part.** Of the two parts left:
  - The model-driven part is gone because the rule is now about the skill's text.
  - The "Changeset-only message accepted" part is now read from the product itself. PROOF-36 reads the conventions' table of when Decisions and Review are left out: `When every rule had one obvious implementation` and `When nothing needs a second pass`. PROOF-37 reads the conventions' own example of a build commit.
  - Breaks, each of which failed its test:
    - removed "One commit per build" from the skill (PROOF-5)
    - changed "Changeset is never omitted." to "rarely" (PROOF-35)
    - changed the table's Changeset cell `Never` to `When empty` (PROOF-35)
    - changed the table's Review cell (PROOF-36)
    - changed "omit Review" to "keep Review" (PROOF-36)
    - in the conventions' example: changed `RULE-2 →` to `RULE-2 ->`, removed the `Review:` heading, and removed the `feat(auth_login):` prefix (PROOF-37)
- **Other new tests.** PROOF-34 checks that a copy one line over the ceiling of 130 is refused. The file is exactly 130 lines today.
  - Other breaks, each of which failed its test:
    - PROOF-1: first cell of the purlin:build row changed to `build`
    - PROOF-2: `sync_status` removed from the choosing section
    - PROOF-4: one line added to the skill
    - PROOF-7: the offer-the-marker phrase removed
    - PROOF-40: a blank line put between the marker and `def test_`
    - PROOF-41: "has no proof" changed to "has a proof"
    - PROOF-9: the fix-beside-why sentence removed
    - PROOF-11: "write no entry yourself" changed
  - Every source file was restored with `git checkout -- <file>`. No test in this file starts the claude program or any service; the only thing it starts is the bash lookup inside the frozen shared helper, when it is imported.

### `skill_spec_from_code`

- PROOF-3 was closed only in part: "computed from the state the skill found" was judgement about prose. RULE-3 now says the skill tells the reader to name the next step from the state. The check now needs the sentence `name the next step from the state` in the last section (PROOF-3), and a copy without it is refused (PROOF-140). Break: in the skill I replaced `then name the next step from the state:` with `then name the next step:`, and PROOF-3's test failed. Restored.
- PROOF-4 claimed that a file over 130 lines is refused, but no test showed it. There are now two boundary tests: exactly 130 lines is accepted (PROOF-141) and 131 lines is refused with `is 131 lines, ceiling 130` (PROOF-142). Breaks, each in a local copy of the frozen shared helper and each restored: comparing with `>=` instead of `>` made PROOF-141 fail, and raising this skill's ceiling to 131 made PROOF-142 fail.
- PROOF-6 claimed the marker sits in the paragraph on a test that already shows the proof, but the marker was only checked across the whole file. The paragraph check now includes the marker. Break: in the skill I moved `purlin: <feature> PROOF-<n>` into a new paragraph, and PROOF-6's test failed (the old check passed this). Restored.
- PROOF-7 now also needs `for a person or an agent to decide`, which the rule says. Break: I cut that phrase from the skill, and PROOF-7 failed. Restored.
- PROOF-125, the command reference row, is now its own test. Break: I emptied the purpose cell of the `purlin:spec-from-code [dir]` row. PROOF-125 failed and PROOF-1 still passed. Restored.
- Break: I changed `name: spec-from-code` to `name: spec-from-cod`. PROOF-1 failed. Restored.
- New refusals, each tied to a source break that failed its good-case test: without `Call sync_status.` (PROOF-135; PROOF-2 failed on the break), without `, and write no new test` (PROOF-143; PROOF-6 failed), without `, passing or not` (PROOF-144; PROOF-9 failed).
- PROOF-5 of the report belonged to a rule that no longer exists (RULE-5, removed under decision 73). Nothing is left of it.

### `config_engine`

Section 3 of dev/plans/proofs-rewritten.md lists no gaps for config_engine, because it was one of the three example specs that was not touched. I added these cases where a rule's own words went further than its tests. For each I broke the source on purpose, saw the new test fail, and restored the source with `git checkout -- scripts/mcp/config_engine.py`. The tests start only the config script itself; nothing they run reaches `claude` or any service.
- RULE-1, PROOF-17: `PURLIN_PROJECT_ROOT` names a file, not a folder. Break: accept any path that exists instead of only a folder. The PROOF-17 test failed.
- RULE-1, PROOF-1 made stronger: the variable's folder holds no marker, and the start folder sits under another project's marker. Break: the variable counts only when its folder holds `.purlin/`. The PROOF-1 and PROOF-28 tests failed.
- RULE-2, PROOF-18: two nested markers, and the nearest one wins. Break: keep climbing and return the outermost marker. Only the PROOF-18 test failed.
- RULE-3, PROOF-3 and PROOF-30: the working directory is a known folder, not the start folder. Break: return the start folder. Both tests failed. A second break named the fallback `climb` instead of `cwd`, and the PROOF-30 test failed.
- RULE-4, PROOF-4: the file holds a nested value. Break: drop nested values when reading. The PROOF-4 and PROOF-9 tests failed.
- RULE-5, PROOF-20 to PROOF-23: a key the file does not hold, no argument, `--key` with no name, and an unknown argument. Each was broken one at a time: a missing key printed `None`, no argument exited 0, the usage for `--key` went to standard output, an unknown argument exited 0. Each time only the matching test failed. PROOF-19 (`--dump`, moved out of PROOF-4): a dump printing `{}` failed it.
- RULE-10, PROOF-10: the test now reads the file beside the target at the moment it is moved and checks it holds the whole new contents. Break: write in place. The PROOF-10, PROOF-26 and PROOF-27 tests failed.
- RULE-10, PROOF-27: the write fails partway through writing the new contents, with a disk-full error. Break: remove the clean-up of the file beside the target. The PROOF-26 and PROOF-27 tests failed.
- RULE-13, PROOF-31: all three sentences are checked word for word; before, the test only checked that two words appeared. Break: reword the `cwd` sentence. The PROOF-31 test failed.
- RULE-13, PROOF-28: the root asked for alone. Break: have the root-alone answer ignore the variable. The PROOF-28 and PROOF-1 tests failed.

### `server`

Section 3 of proofs-rewritten.md lists no open gap for server, and section 5 flags none of its rules. Section 4 names PROOF-3, 8, 9 and 10 as holding several cases, and each is now split:
- PROOF-3: the known notification gets no answer. PROOF-125: the line `not json` gets error -32700.
- PROOF-4: an unknown tool gets -32601 and `Unknown tool: nope`. PROOF-127: an unknown method gets -32601 and `Unknown method: nope/at/all`.
- PROOF-6: a named root answers for that workspace. PROOF-128: a later call naming no root answers for the startup folder.
- PROOF-8: a failing tool answers exactly `Error running sync_status: boom` as text, not as an error. PROOF-133: in the same session, the call after the failure is still answered.
- PROOF-9: a read of one key. PROOF-134: a write, which lands on disk, keeps the other keys and reads back. PROOF-135: a read naming no key returns the whole file.
- PROOF-10: a write naming no key is refused and the file is byte for byte unchanged. PROOF-136: an unknown action is refused and the file is byte for byte unchanged.

New cases found while reading the rules:
- PROOF-126: a notification the server does not know gets no answer.
- PROOF-129: `project_root` written as `~/ws` resolves through the home folder.
- PROOF-130: a named root that holds no workspace says `That root came from the project_root argument.`
- PROOF-131: a configuration write where there is no workspace is refused and creates no `.purlin/config.json`.
- PROOF-132: drift where there is no workspace answers `No Purlin workspace at`.
- PROOF-137: the manifest's own command, run as Claude Code runs it, starts a server that answers `initialize`.
- PROOF-138: stdout holds exactly one answer per tool call across sync_status, drift and the configuration read.

PROOF-2 now also checks that `project_root` is not required. PROOF-5 now checks that stdout holds exactly 1 line.

Every test now goes through a running server, as a client does, instead of calling the server's functions directly.

What I broke on purpose to show each new assertion fails. Every break was restored with git checkout, and every test was caught:
- `project_root` put in sync_status's required list (PROOF-2).
- The startup line also printed to stdout (PROOF-5).
- The parse error code changed to -32600 (PROOF-125).
- Every method with no id answered with an error (PROOF-126: got ids [None, 9]).
- `Unknown tool` reworded to `No such tool`, and `Unknown method` to `No such method` (PROOF-4, PROOF-127).
- The named root ignored (PROOF-6).
- The last named root remembered for later calls (PROOF-128: got the login status table).
- The `~` expansion removed (PROOF-129: got `No Purlin workspace at .../empty/~/ws`).
- `is not there` reworded to `is missing` (PROOF-7).
- The argument source described as the working directory (PROOF-130).
- The no-workspace check skipped for the configuration tool (PROOF-131: got `Set 'gate' = "strong"`).
- The same check skipped for drift (PROOF-132: got `{"error":"no commits",...}`).
- A failure answered as a JSON-RPC error, and separately `: ` changed to ` - ` (PROOF-8).
- The read loop stopped after an `Error running` answer (PROOF-133: got [1] instead of [1, 2]).
- A key read made to return the whole file (PROOF-9).
- A write that also changed `project_name`, and separately a write that was never made (PROOF-134).
- A read naming no key made to return the gate alone (PROOF-135).
- A refused write that still wrote a key (PROOF-10).
- An unknown action that cleared the key (PROOF-136).
- The manifest's last argument pointed at a missing file, and separately its resolver argument (PROOF-137).
- A stray print added to the configuration read (PROOF-138).

### `skill_status`

- PROOF-2 gap, closed in part. It said: numbers printed for a fixture project should match the data the dashboard reads. New PROOF-21 runs the real status tool on a throwaway project at the gate strong, with 2 rules: 1 passing and 1 with no test. The status ends on "2 rules. 1 passes its tests. 0 are strong.", "Left to do:", "  1 rule to write a test for: purlin:build" and "  1 rule to audit: purlin:audit". The test then reads back .purlin/report-data.js: 2 rules, steps {passed 1, strong 0}, and the same two lines of work with command and count 1. Breaking the text side (status.py) or the data side (report_data.py, twice) fails it. It compares counts, not the sentence, because under decision 92 the dashboard shows counts and no sentence.
- Not in the report, but found while reading. RULE-3 said "a → directive for each kind of line", and no test checked that every kind of line the tool can print has a row. New PROOF-24 checks it against the tool's own list of 11 kinds: each kind has a row whose directive runs the command the line itself names. PROOF-25 (the wrong command) and PROOF-26 (a kind with no row) are its refused copies.
- Also not in the report. PROOF-4 claimed that a skill of more than 100 lines is refused, and no test showed it. PROOF-28 now shows the 101-line copy refused with "skills/status/SKILL.md is 101 lines, ceiling 100". PROOF-27 shows the boundary: a copy of exactly 100 lines passes.
- Also not in the report. The empty purpose cell in the command reference was checked by hand in stage C and never by a test. PROOF-20 is now a test.
- Also not in the report. The rule says "their cells", and nothing checked the usage line that says it. PROOF-5 now checks that `purlin:status <name>` and `One spec: its rules and their cells` sit on one line.

### `skill_spec`

Section 3 of the rewrite report lists no open gaps for skill_spec. While reading, I found three places where a proof claimed more than its test showed, and closed them:
- The old PROOF-4 said a skill lengthened past 210 lines is refused and the report gives the count, but no test did that. PROOF-28 now shows a copy of exactly 210 lines is accepted, and PROOF-29 shows a copy of 211 lines is refused with 211 against the ceiling of 210.
- The old PROOF-1 said a description "moved to the next line" is refused. The shared broken copy it used actually emptied the description and moved the `name` line below it. PROOF-17 now tests a real next-line description: the value sits indented under an empty `description:`.
- The old PROOF-1 checked the skill's opening block and the command reference row in one test. They are now separate: PROOF-1 for the opening block, PROOF-14 for the row.

Three findings from section 5, now covered by tests:
- RULE-3's "with nothing printed after it" is held by PROOF-24. The reviewer's worry was that the paragraph for an edited spec reads as text printed after the line; PROOF-3 and PROOF-27 now show that paragraph says "before the offer", and a copy that says "after the offer" is refused.
- RULE-1's "row" is held by PROOF-14 and PROOF-20, which read the table row itself, not the text anywhere in the file.
- RULE-6's order is held by PROOF-6 and PROOF-38.

I also added checks the rules ask for that were missing:
- RULE-7 says the guide "says the same". The test now reads the guide's section `One proof, one case` for all three points (PROOF-40, PROOF-41), not only the 60-word limit.
- RULE-6's drafting instruction and "at least one failure case" must now sit in one sentence (PROOF-36).

### `purlin_version`

PROOF-3 of section 3 was "closed in part": nothing showed that a project `purlin:init` creates carries the version. It is closed now. Setup does have a way to run without questions, so the new PROOF-21 runs setup at the gate `passed` into a fresh git repository holding no files. It checks that setup exits 0 and that the new project's `.purlin/config.json` has `version` equal to this checkout's VERSION file. Setting that version to `'0.0.0'` on purpose makes the test fail.

Along the way, I found that setup takes the version from the VERSION file, not from the template. RULE-3 is reworded to say so.

I also closed places where a proof claimed more than its test showed:
- **Old PROOF-6** claimed "a stamp left at 0.9.2 while the file reads 0.10.0 fails naming both", but its test checked only the live file. PROOF-26 and PROOF-27 now show the missing-key and stale-number cases.
- **Old PROOF-8** claimed "restoring a version row at 0.9.0 to skills/init/SKILL.md fails naming that file", which no test showed. PROOF-35 now shows it, and PROOF-36 shows the owner's own row being caught when it restates a number.
- **The check's line for a file with no version key** had no proof. The new PROOF-30 covers it.
- **Section 5's point about RULE-7** was that `--check` matching locations were only looked for by name. PROOF-28, 29 and 33 now read each location's exact `ok <version>` line.

### `skill_anchor`

PROOF-3 in section 3, listed as left: closed. Decision 65 had already given the skill's three endings a → each, and PROOF-6 already refused an ending that lost its arrow. The check the report asked for was the other skills' refusals of the closing section, and the anchor tests had none. There are now three, each its own proof and test:
- PROOF-21: the closing section deleted.
- PROOF-22: every → in it written as ->.
- PROOF-23: the section cut after its first outcome.

Each was shown to fail when its part of the shared closing-section check was disabled on purpose:
- The heading check replaced by `if False:` fails test_a_skill_with_no_closing_section_fails.
- The arrow-in-section check removed fails test_a_closing_section_with_no_arrow_fails.
- The at-least-2-outcomes check removed fails test_a_closing_section_with_one_outcome_fails.

PROOF-4 also claimed a refusal that no test ran ("Appending prose until the file passes 160 lines fails"). That claim is now covered by two new proofs:
- PROOF-24: a copy padded to exactly 160 lines passes.
- PROOF-25: a copy padded to 161 lines fails with "is 161 lines, ceiling 160".

Breaks for PROOF-4, 24 and 25:
- 63 lines added to the real skill (98 to 161) fails PROOF-4.
- The ceiling check changed from > to >= fails PROOF-24.
- The ceiling check changed to > ceiling + 1 fails PROOF-25.

PROOF-5 in section 3, listed as closed in part: closed a little further. Each of the three sentences of RULE-5 now has its own proof, tied to its own section of the skill, and a refusal for a contrary rewording of that sentence:
- PROOF-26: "A pin is a commit or a branch."
- PROOF-28: "Edit a pinned rule in place when the change is small."
- PROOF-30: "a commit to the local copy".

Each positive proof fails when its sentence is changed in the real skill:
- Changing the pin sentence fails PROOF-5 and 26.
- Changing the never-edit sentence fails PROOF-27 and 28.
- Changing the pull-request phrase fails PROOF-29 and 30.

Other new assertions:
- PROOF-9 fails when the purpose cell of the purlin:anchor row in the command reference is emptied.
- PROOF-18 (the script followed by `syncall`) and PROOF-2 fail when the real skill's `sync` subcommand is renamed.
- PROOF-12 now moves the description text to the line below; the old copy dropped it. It fails, together with PROOF-11, when the empty-description check is disabled.

### `skill_drift`

PROOF-2 gap (section 3), first half: the restatement check used to cover only the `From` cells of the eng and qa tables. It now also covers the cells that say where the range starts (7), the anchor conditions (4) and the git commands the criteria name as sources (5). Each kind must have at least 2 entries, so the check cannot pass on a table it failed to read. PROOF-22 is the passing case, and PROOF-24, 25 and 26 each show one kind being caught. RULE-3 flag: PROOF-27 is new. It ties each kind of line the criteria give the three views to its row in the closing table, and checks the table header `What the view shows | The line to print`. PROOF-33 shows a deleted row being caught. PROOF-2 is stricter: the call must stand alone in a fenced block in the "get the data" step, where any occurrence used to count. PROOF-21 is new and reads the print step's instructions. PROOF-34 and PROOF-35 check both sides of the 150-line ceiling. Each check was broken on purpose in the worktree and restored with git checkout; all of them are plain text reads, and none starts claude or any other program:
(1) `git reflog show HEAD` pasted into the skill: test_it_repeats_no_definition_from_the_criteria failed.
(2) "The range starts where HEAD stood before that action" changed to "range starts: Where HEAD stood before the reset": the same test failed.
(3) "The pin is behind" pasted in: the same test failed.
(4) The row `| A test file changed |` deleted: test_every_kind_of_line_has_its_next_step failed.
(5) The fenced `drift(role="eng")` turned into inline text: test_the_data_comes_from_the_drift_tool failed.
(6) "Print `lines` as they come" reworded, and separately "Do not reword a line, do not drop one" reworded: test_it_says_to_print_the_lines_as_they_come failed each time.
(7) A new key row `signatures_ended` added to the criteria's eng table: test_every_kind_of_line_has_its_next_step failed.

### `claude-md`

All three known faults are fixed: the gate_check.py reader named in two rows, the level wording in two reference rows, and the three screenshots. Three more wrong statements were found and fixed: the init wording in the frameworks row, the missing FAIL marker in the version check, and a format rule that covered four of the six format files and left out two script folders. The step 4 grep line was also extended to references/.


## Gaps left

### `group_states`

No gap listed for these two specs is left open. Two smaller things remain:
- Where a proof says the same thing at each of the three gates, one test still loops over the gates (see the question below). Splitting them is mechanical once the owner answers.
- RULE-10's join of three systems with `, ` cannot happen: this machine's system is never on the line, so at most two are named. The rule now says so. The code path for three names stays and no test reaches it. Removing it is a product change outside my files.

### `purlin_report`

None open for this spec. Two claims rest on something indirect.
- PROOF-29's 'read once' is inferred from the page holding one frame, since the page reads the file through one frame per read. Checking it directly would take counting the page's file requests, which I did not try.
- PROOF-23 checks only that both screenshots exist and come from the regulated sample. It cannot tell whether they show today's page; retaking them is a separate step.

### `run_script`

None of the section 3 gaps for run_script remain open. One thing is not proved: RULE-12 says "at every gate", and the proofs cover `strong` (PROOF-12) and `passed` (PROOF-118) but not `signed`. Closing it takes one more small test that uses the existing CI helper with gate='signed', plus one proof.

### `signatures`

None of this spec's gaps stays open as a test gap. The walk's exit code when it refuses the tag (the old PROOF-73 gap) needs the owner's answer to the first question below. After that it is one test: run the command with no argument where the tag is refused, and check the exit code.

### `scaffold`

None left open in this spec. Two things the owner may want, each needing a rule change first:
- (a) If the runner job's result should be a promise in this spec as well as in run_script, RULE-42 needs a clause and two proofs: the last step, run on a project with one failing test, exits 1; and on a project whose rule is only waiting for an audit, it exits 0.
- (b) The typescript and C# walks through all three gates run only inside the untied gates shell file (see the questions).

### `update`

None for this spec.

One observation, not a gap. PROOF-61 is a single proof over five settings keys, each tried alone in its own parametrized run. I kept it as one case, "any one of these five keys", rather than writing five near-identical proofs. If the owner reads each key as its own case, it becomes five proofs, PROOF-114 to PROOF-118, with the parametrized test split into five.

A second limit. PROOF-15 and PROOF-32 rely on the fixture's `@windows` tags naming a system other than the machine's. On a Windows machine the update offers no runner file for them (see RULE-15 and PROOF-80), so those two tests would fail there. This repository has no Windows runner now (decision 83), so nothing runs them there.

### `evidence_writer`

None from section 3. One thing noticed: the writer has its own fallback to `unknown` for a nameless host, but a run never reaches it, because the run passes the machine name in itself. A break of the writer's fallback alone was not caught by the run-level test, and cannot be, since no run uses that code. Removing it or keeping it is a change to scripts/run/evidence.py, outside this lane.

### `reports`

None for this spec.

### `ai_audit`

- **PROOF-14.** The 300-second limit and how the input is handed over are shown by recording the call, not by starting a real program. Showing the real 300 seconds would need a test that waits 5 minutes.
- **PROOF-67 and PROOF-71.** No single break of the JavaScript reader fails them, because a string or a pattern always stops at the end of its line. Two guards have to fail together (see gaps_closed). Making one guard enough would need a different input, and the reader does not seem to have a weaker spot.

### `host`

- PROOF-95 and PROOF-27 (RULE-24): the Windows spelling is simulated on macOS with macOS git. No run on a real Windows machine shows it. Closing this means tagging one of those proofs `@env(windows)` and running `purlin:test --remote`. Decision 82 keeps that choice for the owner, after an agent shows the list of Windows rules, so I tagged nothing.
- RULE-31 as a whole: the real Azure CLI and the real Azure DevOps service are not exercised. That still needs the hand check on the work machine, dev/manual/check_azure_remote.py.
- RULE-30: the product also reads the repository part of the URL, but nothing a caller sees uses it; its only visible effect is that a URL naming no repository is refused (PROOF-75). I reworded the rule so it no longer claims the repository is read. No test could show that reading.
- RULE-17, PROOF-41 to 43: these say "on a macOS machine", but the tests tell the check the machine is macOS and ask whether a workflow is wanted. They do not run `purlin:init` itself. The printed reason is init's, and init belongs to the scaffold lane, so an end-to-end test sits in that lane's files.

### `drift`

None in the list for this spec. One limit is stated in the proof itself. PROOF-45 (a source carrying a newline) is shown only by giving the value to the check of one anchor's source directly, because a spec's `> Source:` line ends at a line break and cannot hold a newline. Showing it through the report is not possible, because a spec file can never reach the check with one.

### `evidence`

PROOF-9 and PROOF-42 (RULE-5), listed as unmatched: nothing in the product shows a person the list of scope entries that reach nothing. The only code outside the fingerprint that expands a scope is drift, and it throws that list away. The whole-spec message `> Scope: names nothing that exists` appears only when every entry reaches nothing. Both proofs therefore read the list the fingerprint produces, not a screen or a line a run prints. Closing the gap needs the owner's answer to the question below. If the list is to be shown, that is product work in the run or the dashboard, which are other lanes' files, followed by a proof through that output. If it is not, RULE-5 drops "is listed as unmatched", and PROOF-9 and PROOF-42 are deleted or rewritten to the `code` part alone, as PROOF-41 already is.

### `package`

None for this spec. The two open questions below may change RULE-6. If the owner removes "nothing names who last changed a test", PROOF-11 and its test are deleted. If the owner splits RULE-6, its ten proofs are re-pointed to the new rules and no test changes.

### `mutation`

None of the report's gaps for this spec are left. Things found while working, and not closed:
(1) PROOF-67 does not check the strong cell of the timed-out rule. Today it reads strong on the audit alone; see the question on unmeasured strength.
(2) There is no test that the first other JSON file is read when `mutation-report.json` is missing, and none that a scope entry `src/` gets no mutmut breaks. Both behaviours wait on the owner's answer; the check is then a few lines in this file.
(3) No assertion shows the test-file matching fault (listed under product faults). Once the product is fixed, the check is one more test with a report whose test is in `e2e/test/login.test.js` and a rule whose test is in `test/login.test.js`, expecting 0 caught.

### `skill_sign`

No gap is open for this spec. Section 3 of the report listed none.

One limit remains for the whole spec: its proofs check what the sign skill's text says. Whether an agent following that text actually does it (reads the audit before signing, offers the key commands, asks for a version) would need an agent run against a fixture project, or a check by hand.

### `upstream`

One gap is left, and it is a product fault rather than a missing test: RULE-15 does not hold for `sync` without `--check`, as described under product_faults. Closing it takes one of two things:
- a change to scripts/anchor/upstream.py so that a sync fetches each source once per run and reads every anchor from that one checkout, plus a test like PROOF-15 for plain `sync` with two anchors behind;
- or the owner narrowing RULE-15 to `sync --check`.
Neither is possible in my own files without a decision from the owner.

### `skill_test`

None for this spec. Section 3 lists none, and every proof is carried by a test that shows exactly its case.

### `specs`

None in my files. Two things wait on the owner and are asked under questions_for_owner:
- What happens when two specs have the same file name. Once the owner decides, closing it is one rule change and a check of two to four lines.
- Rules that appear both here and in the spec format anchor.

### `skill_audit`

No section 3 gap is open for this spec. The rules are about what the audit skill's text says, so a text check is the honest proof. Whether an audit actually behaves as the text says is shown by the run script's own specs, not here.

### `skill_init`

None for this spec. Section 3 lists no open gap for skill_init, and every proof is tied and passing. One claim is still only checked in the skill's text: RULE-7's "installs nothing in a project's tests". Seeing it in real behaviour means setting up a project that has tests and showing nothing lands in them. That belongs to the setup script's own spec (specs/init/scaffold.md), which this lane does not own.

### `security_no_dangerous_patterns`

- PROOF-1, C# (RULE-1). A command held in a variable and passed to `Process.Start(` is not caught. A text scan cannot tell a string variable from a ProcessStartInfo variable. Closing it would take a C# parse, or the narrower rule offered in the first question.
- PROOF-5, Popen (RULE-5). `subprocess.Popen` is held only to a first argument that is not a quoted string; a name is accepted (PROOF-38). The one Popen launch in scripts/, at scripts/run/mutation/__init__.py:121, is passed a name that its callers fill with lists. Closing it would take following that name back to its callers, or changing that launch so its list is written in place; the second is product code outside this lane. It is asked below.

### `skill_export`

None of the proofs has an open gap. One note on coverage: the spec's Description says the export "commits only when asked" and "checks a package against its fingerprint". No rule of this spec covers what the skill says about either. RULE-2 only requires the `--commit` and `--check <file>` forms to be named. What the command does in both cases is covered by the rules of specs/export/package.md (RULE-1, RULE-9, RULE-10). A rule here would only matter if the owner wants the skill's own wording about committing held too.

### `schema_spec_format`

PROOF-2 (RULE-2): ids written out of order, and one id used twice, are still untested. The owner first has to decide what the report should say (question 1). Once decided, each case is a test of about 10 lines in this file.

PROOF-3 (RULE-3): this repository's own check still accepts only one rule per proof line, although the format allows several. It is also undecided whether a proof line Purlin cannot read should be reported (question 2). The work is either a one-line pattern change in this file, or a warning added to the payload, like the one for unnumbered rule lines, followed by removing this check.

RULE-7: Purlin reads nothing from the heading except `# Anchor:`, so PROOF-7 is a check of this repository's own files only (question 3). If the owner chooses to reword the rule, the fix is two proofs and two small tests in this file.

### `purlin_agent`

None for this spec. All the rules are about what the text of the agent definition says. Showing that an agent session actually behaves that way (calls sync_status first, never pushes, routes a plain request to the right command) would take an agent run against a fixture project. A text check cannot show it, and no rule here asks for it.

### `skill_build`

No real run of the build skill is tested. Every proof reads what the skill tells the agent, not what an agent does after reading it. Closing that would need a model-driven purlin:build run against a small practice project, with the resulting commit and `> Scope:` line read back. That needs the claude program and costs model calls on every sweep, so it waits on question 1.

The conventions' example also leaves RULE-3 unmapped. The assertion that would expose it is left out of the tests (see product_faults).

### `skill_spec_from_code`

PROOF-6, closed only in part: nothing shows that an agent following the skill really offers the marker, writes no test, lists the tests it left untied with their reasons and the source files that got no rule, and runs no test first. Closing it needs the real skill run by the model on a small sample project with one full test, one partial test and one failing test, then a look at what it wrote. That means calling the real `claude` program, which this lane may not do and a unit test should not do. I reworded RULE-6 to RULE-9 to what the skill says, which is what the spec's Description says it covers. Whether behaviour should also be proved is the first question for the owner. Sanity check 3 (decision 64) is the run that currently covers this behaviour.

### `config_engine`

One case has no test: a process killed between writing the file beside the target and moving it. It leaves `.purlin/config.json.tmp` on disk. A unit test cannot kill the process at that moment in a reliable way; it would take a child process stopped by a signal at a hook placed between the two steps. RULE-10 was reworded so it no longer claims that case (see rules_sorted). Nothing else is open.

### `server`

None for this spec. The four tests with no marker are unchanged: sync_status answers the table, drift answers JSON, every open passes an encoding, and the package imports only the standard library. The last two check the package's hygiene, which no rule of this spec states. Tying them would take the owner adding rules for the package's hygiene, or moving those tests to the spec that owns them.

### `skill_status`

- PROOF-2's other half. Nothing shows that a skill text holding some other counting instruction is refused, beyond the one sentence replaced in PROOF-6. Closing it needs an agreed list of phrasings that count as "recount", which is a judgement, or the AI audit reading the skill. It also needs an agent run to show that the agent actually prints the tool's lines untouched, which calls the model.
- PROOF-5's gap (the named form's real output: its path, its header, one line per rule with its cells), and what happens when several specs match or none does. The agent composes that output, not the status tool, so only an agent following the skill against a fixture project can show it. That means a real model run, or a hand check signed with purlin:sign. A stand-in agent would be a stand-in for the thing under test. Left open; see the first owner question.

### `skill_spec`

None for this spec. One wider point is not a gap in my files: the rules describe what the agent does, while the tests read the skill's instructions. It is raised in questions_for_owner.

### `purlin_version`

PROOF-7 of section 3, the "one propagation entry point" half of RULE-7, is still not shown. It is now a real choice rather than a missing test.

The upgrade, `purlin:init --update`, also writes the `version` key of `.purlin/config.json`, taking it from the VERSION file. references/drift_criteria.md records this: its `version` row lists `purlin:init` and `purlin:init --update` as the writers. So the bump script is not literally the only thing that writes that file's version.

What it would take depends on the owner's answer (see questions_for_owner):
- If the claim is dropped, nothing more is needed.
- If the claim is kept to mean "the only command that sets a new number", a test would scan the shipped scripts for anything that writes these four version fields from anything other than the VERSION file. That is roughly 30 lines in my test file.

### `skill_anchor`

PROOF-5, the part still open: the tests do not catch a contrary instruction added somewhere else in the skill while the correct sentences stay in place. An example is an extra line telling the reader to pin a branch or to edit the pinned copy. Catching it needs an agreed list of contrary phrasings to refuse.

The obvious search, any sentence pairing "pin" with "branch", already matches a correct sentence in the skill: "A branch moves, and an anchor whose rules changed under a project with no diff to read is exactly what pinning exists to prevent."

This is put to the owner under questions_for_owner.

### `skill_drift`

PROOF-2 gap, second half: whether the agent, when it runs the skill, prints only the tool's lines and invents none. A reading of the skill cannot show that. RULE-2 is now reworded to what the skill tells the agent, which the tests do show. Closing the rest would need a real agent run of purlin:drift against a fixture repository, with its printed lines compared to the tool's `lines`. That reaches the real claude program, which this lane may not start. A paraphrase in the skill's "When to run it" section is not caught either ("The range starts where HEAD stood before that action"). The restatement check compares text word for word, and catching meaning would need an owner decision on what counts as restating, plus a model read.

### `claude-md`

One question is open: how Purlin itself is released. It needs your answer, and then a one-line edit to the release steps.

Three smaller points were noted and not changed, because each reads as meant:
- The version section says that adding a row to the script's header comment makes the check guard it. In fact the check reads a list in the script body. The line mirrors the script's own header, so both would need rewording together.
- "scripts/ is the only directory a consumer may depend on" sits beside "the format files are versioned contracts consumers depend on". Read as paths versus data contracts, the two agree.
- The hard_gates.md row does not name "when a version is finished", which that file is now the one home of. The row lists what the file holds and is not meant to be complete, so I left it.


## Rules sorted

### `group_states`

(a) Wording was loose and the product is right, so the rule is reworded:
- states RULE-4. Before: "...counts at every gate, `signed` included, because what a signature locks is the evidence rather than the machine that produced it". After: "...counts at every gate, `signed` included: a result counts wherever it ran, and its section records where". The old reason contradicted decision 77, under which a signature is made over the machine the tests ran on.
- states RULE-5 (flagged). Before: "the runtime proof files a run leaves under `.purlin/runtime/` are not read". After: "the test reports a run leaves under `.purlin/runtime/reports/` are not read". No run writes a runtime proof file any more; a run does leave reports.
- states RULE-23. Before: "`untested` while no counting run reads as passed, ... `failing` where every platform that ran failed, `partial` where they disagree". After: "`failing` where its passed cell reads `failed`, `partial` where it reads `partial`, `untested` where it reads any other word short of `passed`". This is how the bucket is actually decided.
- states RULE-25 (flagged). Before: "...`manual`, `not_audited`, the test strength, `proofs`, `proofs_without_test` and `proofs_without_test_ids`". After: "...`manual`, `not_audited`, `test_strength`, `proofs`, `proofs_without_test`, `proofs_without_test_ids` and `incomplete`".
- states RULE-35 (flagged). Before, it ended "..., and a runtime proof file this checkout wrote moves nothing". That clause is dropped. PROOF-40, which showed only that this retired file is not read, is deleted. PROOF-42 now checks the hash, not only the list.
- states RULE-36. Before: "a feature with no audit shows `n/a`". After: "with `n/a` in place of the strength where nothing measured one". `n/a` means no mutation score, not no audit.
- states RULE-49 (flagged). Before: "The status table and the dashboard render one spec's row from one module, so a cell reads the same characters wherever it is printed". After: "The status table and the dashboard show one spec's row under the same column headings, and every cell after the spec's name reads the same characters in both, but for the `Rules` cell of a spec that proves shared rules, which reads `<n> (+<k> shared)` in the table and `<n> (+<k>)` on the dashboard". The dashboard really renders from board.js, a copy of board.py, so the rule now states the effect a reader sees. The exception is decision 90's.
- states RULE-57. "a red local section beside a green `ci` one" became "a failing local section beside a passing `ci` one".
- states RULE-59 (flagged). Before: "the newest version wins, read as numbers where the name is numeric". After: "a name whose version starts with a number beats one whose version does not, and numbered versions compare as numbers, so `signed/1.10.0` beats `signed/1.9.0` and `signed/beta`".
- summary RULE-10. Before: "joined by `, ` and ` and `". After: "joined by ` and `; this machine's own system is never among them, since a rule that waits for it is counted `to test`, so the line names one system or two". New PROOF-28 shows it.
Flagged rules already right as they stand:
- states RULE-13: its loose-wording case moved to RULE-14 as PROOF-158.
- RULE-18, RULE-22 and RULE-41 were reworded earlier and are clear.
- RULE-37 and RULE-38 no longer exist.
- RULE-64 and RULE-73 each have a proof for every clause now: PROOF-109, PROOF-110 and PROOF-144.
Retired thing deleted: states PROOF-40, and the runtime-proof-file case of PROOF-7.
Duplicate cases merged into one proof:
- PROOF-16 case (d) is the same as the new PROOF-159.
- PROOF-29 case (b) is the same as PROOF-96.
(b) Product is wrong: none found.
(c) Real choices: see questions_for_owner.

### `purlin_report`

Changed by decision 85, with the product changed to match. Before and after:
- RULE-8. Before, it ended: 'Under the boxes `Left to do` lists the payload's lines of what is left, in the payload's order, each its text and then its command, and where nothing is left the payload's last line stands in the list's place'. After, that sentence is gone; the boxes part is unchanged.
- RULE-13. Before: 'From `strong` up the board offers three filters ... `No proof` ... `Weak` ... `Not audited` ... At `passed` the board offers no filter'. After: 'At every gate the board offers one filter button above the table per line of what is left in the payload, in the payload's order: each is named as its line without the count and the noun it counts, in sentence case, so `4 rules to strengthen` is `To strengthen` and `the version to tag` is `To tag`, and each carries the count the payload gives its line, counted nowhere on the page. A kind the payload does not list has no button, and where it lists none the payload's last line stands in the buttons' place'.
- RULE-14. Before: 'Filters compose: a rule shows only where every set filter accepts it, a combination nothing matches says so in place of the table, and unsetting them restores every row'. After: 'One filter button is chosen at a time: choosing one shows only the rules the payload gives its kind, choosing another moves the choice to it, and choosing the chosen one again shows every rule. `To tag` counts the version and no rule, so choosing it leaves every rule showing'.
- RULE-53. Before: 'Each line of `Left to do` shows the command that clears it in the monospace face ... nothing on the list is a control'. After: 'While a filter button is chosen, one line under the buttons names the command that clears its kind, `Type <command> in Claude Code.`, the command in the monospace face; the line is text, with no button and no checkbox, and pressing it changes nothing on the page. With no button chosen the line is absent'.
- RULE-51. Before, it ended: 'and the `No proof` filter narrows the table to those rules'. After, that clause is gone; the filter is now `To write a proof for`, under RULE-13 and RULE-14.
- RULE-50. Before: 'on the board and on the rule screen'. After: 'on the rule screen', because a row no longer shows a WAITING badge.
- RULE-55, new: 'A rule's row on the board carries a badge for each step the rule has reached, `PASSED`, `STRONG` and `SIGNED`, reached as the step boxes count it, and `FAILED` where a test of the rule failed on any operating system; a step the rule has not reached draws no badge'.
- RULE-56 (the reasons beneath an unfolded rule) was written and then deleted, because decision 89 withdraws that part of decision 85.

Loose wording, product right. Before and after:
- RULE-46. Before: 'a button that opens that rule's proofs beneath the row and closes them again, reading `▶` closed and `▼` open ...; every rule's proofs are closed when the page loads ... Closed, the button reads ... Open, each proof reads ... A filter that hides a rule hides its proofs'. After: 'a button that unfolds the rule beneath the row and folds it again, reading `▶` folded and `▼` unfolded ...; every rule is folded when the page loads and when its spec is opened, and unfolding one rule leaves every other rule as it was. Folded, the button reads ... Unfolded, each proof reads ... A filter that hides a rule hides what it unfolded'.

No rule where the product is wrong: none found. The real choices are under questions_for_owner.

### `run_script`

(a) Reworded because the wording was loose and the product was right:

- RULE-11. Before: "the run exits on the tests alone: 1 where a test failed, evidence is missing or a marker names nothing a spec has, 0 otherwise". After: "`--test` exits on the tests alone: 1 where a test failed, evidence is missing or a marker names nothing a spec has, 0 otherwise, and `--audit` and `--ci` exit as RULE-48 and RULE-12 say". The old wording contradicted RULE-48, because an audit exits 1 on a weak rule, and RULE-12, because the CI run exits 0 on a marker naming nothing.
- RULE-15 (flagged beside RULE-47). Before: "`--audit` and `--ci` write the run's console log to `.purlin/runtime/run.log`". After: the same, plus ", except a `--ci` run on a tag, which writes none".
- RULE-47 (flagged). Before: "On a tag run it runs the tests, writes and commits nothing". After: "writes no evidence and no `.purlin/runtime/run.log`, commits nothing". The suites still write their reports.
- RULE-48 (flagged). Before: "Above the gate `passed`, `--audit` exits 1 when a test it ran failed or did not run, or when a rule it read is weak or could not be audited; ...". After: "`--audit` exits 1 at every gate when a test it ran failed or did not run. Above the gate `passed` it also exits 1 when a rule it read is weak or could not be audited; ...".
- RULE-49 (flagged). Before: "...that is the feature's own, has a proof with a test, ... proof and test." After: the same, plus "; a rule a feature takes from an anchor it requires is read once, as the anchor's, and never as the feature's."
- RULE-51 (flagged). Before: "4 when the setting is absent and 4 with one warning when it is not a whole number from 1 to 16". After: "4 when the setting is absent, and 4 when it is not a whole number from 1 to 16, a fraction or a word included, with the run's first line reading `\"audit_parallel\" is <value>, which is not a whole number from 1 to 16; reading it as 4`". The warning also repeats beside the table; that is question 4.
- RULE-54 (flagged). Before: "`AI audit: <n> rules read, <s> strong, <w> weak.` with the rules it skipped". After: "... and, on the same line, the rules it skipped, `<k> rules skipped; their text, proof and test match their last audit. purlin:audit --all reads them again.`".
- RULE-55 (flagged). Before: "so an anchor edit runs those features". After: "so an anchor edit runs the anchor and those features". The run's line reads "Selected 3 of 4 features: export (spec changed since ...), login (...), shared (spec changed since ...)".
- RULE-68 (found while reading). Before: "first the spec of each feature it ran, the test files carrying their markers and `.purlin/config.json`, then the evidence...". After: "first `purlin: specs, tests and settings for <features>`, holding ... where any changed, printed as `Committed <sha7>, the work these results describe:` and each path on a line of its own; then the evidence...". This follows decision 70 and commit_conventions.md; the product already did it, and PROOF-203 and PROOF-204 now prove it.
- RULE-21 (flagged earlier) needed no change: decision 65 already settled it and PROOF-124 proves it.

(b) Product wrong against a rule of this spec: none. The one fault found, the partial rule listed as `to fix`, sits in the summary, outside this spec's rules; see product_faults.

(c) Real choices for the owner: the four questions above.

### `signatures`

(a) Wording that was loose where the product was right:
- **RULE-13.**
  - Why: the product puts the note on every rule named, whether or not its proof is `@manual`, and decision 75 has Purlin refuse nothing a person does.
  - Before: "`--note` puts one line on the signature, for a `@manual` proof; `--note` with no rule named, with `--all`, or with no line, exits 2".
  - After: "`--note` puts one line on the signature of each rule named, the line a person writes after checking a `@manual` proof by hand; `--note` with no rule named, with `--all`, or with no line, exits 2".
  - Proofs: PROOF-16 now uses a real `@manual` rule, and PROOF-145 shows one note on two rules.

Changed by decision 85:
- **RULE-64.**
  - Before: "A rule named by id that no spec has prints `<feature> <RULE-N> is not a rule any spec has.`, writes no signature and exits 1".
  - After: "A rule named by id that no spec has is named in the line `<feature> <RULE-N> is not a rule any spec has.` and gets no signature; the rules named beside it that a spec has are signed, and the command exits 1".

Flagged in section 5 and now answered by proofs, with the rule text unchanged:
- **RULE-6:** PROOF-127 proves the audit part.
- **RULE-10:** PROOF-14, 128 and 129 prove where the reader looks and what it ignores.
- **RULE-45:** the proofs run the walk ("the walk is run") instead of an unnamed way to ask for the tag. PROOF-101 shows the remote is left as it was.
- **RULE-11:** PROOF-87 looks between stops. The rule stays one sentence, because its six proofs each take one part.
- **RULE-16:** PROOF-30 runs a bare feature. PROOF-130 and PROOF-131 run `--all`.

(b) Product wrong: none found.

(c) Real choices for the owner: the three questions below.

### `scaffold`

Reworded, because the wording was loose and the product was right:
- RULE-31. Before: "A real run outside a git repository exits 2 ..." After: "A run outside a git repository exits 2 ...". "Real" was left over from the rehearsal mode that decision 70 removed.
- RULE-36. Before: "at `passed` a `--test --commit` run exits 0 ...; ... until `--audit --commit` writes an audit ...; a `--ci` run on a tag writes nothing and one on a run branch writes;" After: "at `passed` `purlin:test --all --commit` exits 0 ...; ... until `purlin:audit --all --commit` writes an audit ...; a runner's test run on a `signed/*` tag writes nothing and one on a `run/*` branch writes;". It now names the commands a person types.
- RULE-44. Before: "The host CLI, `gh` or `az`, is reported as present or absent either way". After: "Where both hold, the host's command-line tool, `gh` on GitHub or `az` on Azure DevOps, is reported as installed or not installed, and the workflow is written in both cases". The product checks the tool only after both prerequisites pass.

Flagged in section 5 and already resolved by the current text:
- RULE-15: the workflow no longer always carries an ubuntu job, and PROOF-72 asserts there is none.
- RULE-33: the rehearsal is gone.
- RULE-37: the rule now names purlin:test.
- RULE-46: PROOF-85 shows the gate default under --yes.

Proof claims taken out because they checked that a removed thing is absent:
- PROOF-18: no design folder.
- PROOF-77: no `is not on origin` and no `git push -u`.
- PROOF-5: the test's `at a time` check was replaced by the exact list of questions shown.

Real choices for the owner (see questions_for_owner): whether a second run keeps asking before each write, which RULE-1's "nothing else" does not allow for; the overlap of RULE-37 with RULE-21; and the untied typescript and C# gate walk.

No product fault was found.

### `update`

(a) Loose wording where the product is right. I reworded these, and they are committed in e49212f9f.

- RULE-1. Before: "`pending()` returns one entry per migration a project still needs, each carrying an id, one line saying what it does and the files it touches; it returns nothing for a root with no `.purlin/`". After: "The list of migrations a project still needs holds one entry per migration, each carrying an id, one line saying what it does and the files it touches; the list is empty for a root with no `.purlin/`". Reason: the rule named a function.

- RULE-2 (flagged in section 5). Before: "The detectors read the layout v0.9.5 left, and what that layout leaves behind is what they report; a project that carries a hook v0.9.5 installed has the hook migration reported too". After: "The update, run on the layout v0.9.5 left, lists as pending exactly the migrations that layout needs and no other; a project that also carries a hook v0.9.5 installed has the hook migration listed too". Reason: the old wording did not say the list is exact.

- RULE-5 (flagged). Before: "`--yes` answers yes to every question and applies every pending migration, and a second run finds nothing left to do and changes neither the commit nor the tree". After: "`--yes` asks nothing: it applies every pending migration and takes the default answer to the gate question and to the mutation question; a second run finds nothing left to do and changes neither the commit nor the tree". Reason: under --yes the product answers the mutation question no and the gate question with its default, as setup's --yes does ("takes every default, so mutation testing stays off").

- RULE-10. Before: "...with `audit_parallel` 4 and none of the keys this release stopped reading...". After: "...with `audit_parallel` 4, or the number from 1 to 16 the project already named, and none of the keys...". Reason: the product keeps a value the project already set in that range.

- RULE-15. Before: "...is removed; one runner file is offered in its place, where `purlin:init` writes it...". After: "...is removed; when a proof is tagged `@env` for an operating system other than the one the update runs on, one runner file is offered in its place, where `purlin:init` writes it...; with no such proof none is offered and the output says why; ...". Reason: decisions 75 and 83 give the runner one reason, and the product prints "wrote no workflow: every test runs on this operating system..." when there is none.

- RULE-21. Before: ends "...and `auto`, or no value, writes what detection finds". After: adds "; a config that already carries a `tests` setting keeps it". Reason: the product keeps such a setting unchanged.

- RULE-27. Before: "...naming it, `<n> specs have no > Scope: line: <names>. Run purlin:spec <name> to add one.`, with the line optional below `signed` and required at `signed`; ...". After: "...naming it, `<n> specs have no > Scope: line: <names>. Run purlin:spec <name> to add one.`, followed by `The line is optional below the gate signed and required at signed.`; ...". Reason: the old wording read as if the product enforced the line at signed. It only says so in the advice.

- RULE-12 (flagged): no change. The default taken from the gate the project already named is shown by PROOF-48.
- RULE-3 (flagged): no longer in the spec.

(b) The product does not do what the rule says: none found.

(c) Real choices for the owner:
- RULE-11 overlaps RULE-10 (flagged in section 5).
- The upgrade takes a typed answer that is not a gate without saying so (RULE-12's behaviour, set against setup's).
- Whether the RULE-32 proofs should observe a test run stopping.
All three are under questions_for_owner.

### `evidence_writer`

(a) The wording was loose and the product is right. Three rules were reworded:
- RULE-4, flagged because it read as contradicting RULE-5.
  - Before: "...a section another operating system wrote and the `audit` object stay byte for byte as they were"
  - After: "...a section another operating system wrote and the `audit` object stay byte for byte as they were, apart from the entries of rules the spec no longer carries, which RULE-5 drops"
- RULE-8, flagged because it did not say which commit the table's heading names.
  - Before: "...it opens `# Tests at <sha7>`, carries the columns..."
  - After: "...it opens `# Tests at <sha7>`, naming the commit of the newest section across every feature, carries the columns..."
- RULE-11, flagged because it paraphrased the line the run prints.
  - Before: "...and `--commit` says there is no git repository to commit them to"
  - After: "...and `--commit` prints `Evidence written; there is no git repository to commit it to.`"
  - PROOF-11 and its test now check that whole line.

RULE-9 was flagged because no test showed that an `--audit` run commits nothing. That was already closed by PROOF-37 before this lane, so it needed no change.

(b) The product does not do what a decision says: RULE-2 read with decision 69. A rule with one passing proof and one proof with no test reads `not run`, and the run's advice is `purlin:test`, which does not clear it (see product_faults). RULE-2's own text does not cover that case: read literally, "every test tied to every proof ... ran and passed" would give `passed`. So I left RULE-2 as it is and put the choice of word to the owner.

(c) Real choices for the owner: the word and the advice for a partly tested rule, and whether a person's own results keep the host name beside the machine. Both are under questions_for_owner.

No proof or rule quoted wording that decisions 60 to 85 have since changed. The table's system names read `Windows`, `macOS` and `Linux/Unix`, as decisions 65 and 79 say.

### `reports`

(a) Reworded because the wording was loose and the product is right:
- RULE-5
  - Before: "... is tied to no test` and its result is `not run`"
  - After: "... is tied to no test` and its result is `not run`, which the evidence writes as `missing`"
  - This follows marker_format.md and settles the section 5 flag.
- RULE-6
  - Before: "a C# method carrying `[Fact]`, `[Theory]`, `[Test]`, `[TestCase]` or `[TestMethod]`"
  - After: "a C# method carrying `[Fact]`, `[Theory]`, `[Test]`, `[TestCase]`, `[TestCaseSource]`, `[TestMethod]`, `[DataTestMethod]`, `[SkippableFact]` or `[SkippableTheory]`"
  - These are the attributes the product reads.
- RULE-9
  - Before: "... is that test's result, and every other event is left alone"
  - After: "... is that test's result, and every other event, and every line that is not JSON, is left alone"
- RULE-14
  - Before: "one whose cases were all skipped, or that no case in the report is, reads `not run`"
  - After: "any other, its cases all or partly skipped with none failed, or none of them in the report, reads `not run`, which the evidence writes as `missing`"
  - The product reads a test partly skipped and otherwise passing as `not run`.
- RULE-18
  - Before: "... wrote no report at <path>.` and exit 1"
  - After: "... wrote no report at <path>.`, or `in <path>` where it left a folder with no report in it, and exit 1"

Section 5 flags that needed no rule change:
- RULE-19's plural wording no longer exists; every such line now ends with "Correct the comment, or run purlin:build to repair it."
- RULE-13 and RULE-20 are now shown through a real run and what it prints (PROOF-13, PROOF-20, PROOF-88, PROOF-89).

(b) Where the product is wrong: RULE-8, listed under product_faults.

(c) Real choices, listed under questions_for_owner:
- A run that exits 1 while its last line says `Nothing left to do.` (PROOF-19).
- Which way the TRX mismatch should be fixed.
- A suggested fix that points at a rule that has proofs.

### `ai_audit`

**Reworded because the wording was loose and the product is right:**
- **RULE-4.** Before: "One call is made per rule, and as many calls run at once as the number the caller names". After: "One call is made per rule, and as many calls run at once as the number the caller names, or as there are rules when there are fewer". This answers the proofs-rewritten flag.
- **RULE-11.** Before: "read out of JavaScript and TypeScript by balancing braces, so ...". After: "read out of JavaScript and TypeScript by balancing the brackets of the test's call, with strings, comments and regex literals stepped over, so ...". The reader balances the parentheses of the `it(...)` call on text where strings, comments and patterns are blanked; it does not balance braces.
- **RULE-13.** Before: "a feature with no rule in the project exits 1". After: "a feature with no rule in the project, or a rule the project does not hold, exits 1". The command already exits 1 for `--rule RULE-99`, and its help text says so.
- **RULE-14.** Before: "what the last audit found, with its `verdict`, model and time, and no emoji". After: "what the last audit found, its verdict, model, time and each finding, and no emoji". It prints `Weak`, capitalised, and each finding.

**Flags from proofs-rewritten, settled without a rule change:**
- **RULE-12.** The test now covers `.purlin/runtime/` and compares bytes, and the rule no longer carries the hash part, which main had already removed.
- **RULE-1.** A stale entry is now shown for a changed rule text, proof and test.
- **RULE-3.** PROOF-13 now claims the input is read to its end, and a break shows it.

**Product wrong:** none against its rules. Decision 93 is listed under product_faults.

**A real choice:** two, under questions_for_owner.

### `host`

Reworded, because the wording was loose and the product is right:
- RULE-6.
  - Before: "A ref update refused because the branch moved is retried 3 times and then raised; ..."
  - After: "A ref update refused because the branch moved is sent again, at most 3 times in all, and then raised; ..."
  - Why: the run makes 3 attempts in all, which is what PROOF-58 has always said. "Retried 3 times" reads as 4.
- RULE-12.
  - Before: "... after a red run as after a green one and on both git hosts through the same code; ..."
  - After: "... after a red run as after a green one, on both git hosts; ..."
  - Why: "through the same code" describes how the code is built, and no proof can show it. "At every gate" stays, and PROOF-67 now shows it at the gates passed, strong and signed.
- RULE-20.
  - Before: "... its own tests pass against its own module, ..."
  - After: "... its test of the greeting passes against its own module and its test scoped to Linux passes on Linux alone, ..."
  - Why: run on macOS, the fixture's own test file exits 1 by design.
- RULE-21.
  - Before: "... so a repository whose only branch is `master` is never told its signature is not on the branch"
  - After: "... so a repository whose only branch is `master` is never taken for one on `main`"
  - Why: no reader checks a signature's branch any more; a signature counts on whatever branch carries it. Whether to keep the rule at all is question 2.
- RULE-24.
  - Before: "`deleted_files()` hands git the pathspec `.purlin/evidence` with `/` on every operating system, so a run on Windows still finds the evidence files it removed and ..."
  - After: "When a run looks for the evidence files it removed, it hands git the path `.purlin/evidence` spelled with `/` on every operating system, so a run on Windows still finds them and ..."
  - Why: the old wording named a function.
- RULE-28.
  - Before: "... `commits_here()` is true on a branch under `run/` and true off a runner altogether, where no rule is being spoken for, and false on a tag run, ..."
  - After: "... it commits on a branch under `run/` and off a runner altogether, where no rule is being spoken for, and not on a tag run, ..."
  - Why: the old wording named a function.
- RULE-30.
  - Before: "On Azure DevOps the organisation, project and repository are read from `origin` in three forms, ..."
  - After: "On Azure DevOps the organisation and project the run is looked up in are read from `origin`, which takes one of three forms, ..."
  - Why: nothing a caller sees uses the repository part, apart from refusing a URL that lacks it.
- RULE-31.
  - Before: "...; the intervals and limits are module constants, every `git` and `az` process ..."
  - After: "...; every `git` and `az` process ..."
  - Why: this is a claim about the code. The rule already states the values (3 s, 60 s, 15 s, 90 min), and PROOF-80 and 81 now show the real limits.

Flagged in section 5 and left unchanged:
- RULE-17 names `templates/purlin.yml`. That file ships, and Purlin reads it to write a consumer's workflow, so naming it is allowed, as the guide allows for a file that is itself the product.
- RULE-9: no longer in this spec.

A real choice for the owner:
- RULE-26: its only visible effect is RULE-27's refusal. See question 1.

Product wrong: none found.

### `drift`

(a) Five rules were worded loosely where the product is right, and are reworded (commit 586515c0f):

- **RULE-5**
  - Before: "The first line of every view names the action it measured from, how long ago it ran, the range as two 7-character shas and the number of commits, as in `Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).`"
  - After: "When the range starts where HEAD stood before an action, the first line of every view is the same line, naming the action, how long ago it ran, the range as two 7-character shas and the number of commits, as in `Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).`"
  - Why: a range given by `since`, a clone or no action at all prints other lines, and those are proved under RULE-3 and RULE-4.
- **RULE-6**
  - Before: "The PM view compares each spec's map of rule id to rule text at the start of the range with the one at HEAD, and prints ... or `No rule was added, changed or removed since <the action>.` when there is none"
  - After: "The PM view compares, for each spec file the range changed, the spec's rule ids and texts at the start of the range with those at HEAD, matching a spec by its name wherever its file lies, and prints ... or, when there is none, `No rule was added, changed or removed` followed by the range, as in `No rule was added, changed or removed since your last pull.`"
  - Why: with a count the product prints `in the last 3 commits`, and a moved spec compares with itself because it is matched by name.
- **RULE-8**
  - Before: "leaving out spec files, files under `.purlin/`"
  - After: "leaving out files under `specs/`, files under `.purlin/`"
  - Why: the product leaves out every file under specs/, not only spec files.
- **RULE-13**
  - Before: "An anchor row names the anchor's own spec name, never the repository path and never the file inside it"
  - After: "An anchor's row and its line name the anchor by its own spec name, never by the repository path and never by the file inside it"
  - Why: the row also carries the source as a fact, so the old wording was literally false; what the rule means is the name.
- **RULE-15**
  - Before: "The QA view names the changed files that carry a proof marker and the features those markers name, as `2 test files changed, covering login, export.`"
  - After: "The QA view counts the changed files that carry a proof marker and names the features those markers name, in alphabetical order, as `2 test files changed, covering export, login.`"
  - Why: the product prints a count and sorts the features.

(b) The product is wrong in one place, RULE-10: a source such as Azure DevOps is never checked. See product_faults. Neither the rule nor the product was changed, and no assertion exposed it.

(c) Three real choices are in questions_for_owner:

- Deleted files are not counted in the developer's view (RULE-7 and RULE-8).
- The QA view carries `not_audited`, which no line prints (RULE-18).
- How drift decides which anchor sources to check (RULE-10).

One proof also claimed more than its test showed, and was corrected. PROOF-28 said "no colon followed by a space", but lines such as `1 rule to test by hand: purlin:sign` hold one. It now says no space after the `:` and `,` that separate keys and values, and the test gained the check for the item separator.

### `evidence`

Reworded because the wording was loose and the product is right (type a):

- RULE-3, flagged in section 5.
  Before: "Editing a rule of an anchor changes the `spec` part of every feature that requires the anchor, directly or through another spec, and leaves a feature that does not require it unchanged"
  After: "Editing a rule of an anchor changes the `spec` part of every feature that requires the anchor, directly or through another spec, and, when the anchor carries `> Global: true`, of every feature; a feature that does not require an anchor without `> Global: true` is left unchanged"
  PROOF-5 (global anchor) and PROOF-35 (anchor that is not global) now each read one side.

- RULE-6, flagged in section 5.
  Before: "A spec with no `> Scope:` line is reported as naming no files, and its `code` part is the sha256 of the empty string rather than an error"
  After: "A spec with no `> Scope:` line is reported incomplete with the reason `no > Scope: line`, and its fingerprint is still taken, with a `code` part that is the sha256 of the empty string"

- RULE-7, flagged in section 5.
  Before: "The `tests` part covers every tracked test file, one a suite of the `tests` setting names, carrying a marker for the feature; editing such a file changes `tests` and no other part, and a marker for another feature is not counted"
  After: "The `tests` part covers every tracked test file, one a suite of the `tests` setting names, carrying a marker for the feature; editing such a file changes `tests` and no other part; a marker for another feature, and a file under a folder whose name begins with `.` or is `node_modules`, `bin`, `obj` or `mutants`, are not counted"
  This folder list is the one the marker reader skips and that references/supported_frameworks.md already states.

Product wrong (type b): none. Every rule matched what the product does.

A real choice for the owner (type c): RULE-5, "is listed as unmatched". Nothing a person reads shows that list. See questions_for_owner.

No proof or rule quoted words that decisions 60 to 85 have since changed. `Windows`, `macOS`, `Linux/Unix`, `Win`, `Mac`, `Lin` and `not run` match what the product prints.

### `package`

**Reworded because the wording was loose and the product is right (a):**

- **RULE-3.** Flagged in section 5: it did not say whether a later commit moves `commit`.
  - Before: "... and `commit` is the commit the evidence was taken at"
  - After: "... and `commit` is the commit the evidence was taken at: `HEAD`, stepping back over any commit that changed nothing but files under `.purlin/evidence/package/`"
  - These are the words of the package format and what the product does. The new PROOF-30 shows a code change committed after the evidence moves `commit`.
- **RULE-7.** Found while reading: the product and the format leave out an uncommitted signature as well as uncommitted evidence.
  - Before: "Evidence written and not committed is left out of the package and named, ..."
  - After: "Evidence or a signature written and not committed is left out of the package and named, ..."
  - The new PROOF-31 shows it.

**Proofs rewritten to the standard:**

- PROOF-15, PROOF-16 and PROOF-28 each ended with a clause saying what the test rejects ("... fails"). That clause now states what is seen, or is gone.
- PROOF-9, 25 and 26 now give exact values: `left` null, the machine `remote runner, macOS` as the example, and the model `claude-opus-5-20260901`.
- PROOF-12 was cut to 50 words.

**The product is wrong (b):** none found. The export prints no next command itself; the export skill prints the `→ Run:` line, which covers decision 69.

**A real choice for the owner (c):** RULE-6, twice. First, the clause "nothing names who last changed a test". Second, the rule's length, flagged in section 5. Both are in questions_for_owner.

No quote in the spec conflicts with decisions 60 to 85. In the test file's docstring, a sentence about rules "marked lower" (removed by decision 73) and a comment with no code under it were deleted.

### `mutation`

Test counts are pytest items. The file went from 68 test functions to 67; the item count fell because fewer tests are parametrized. Every proof now has exactly one test.

Reworded (the wording was loose and the product is right):

- RULE-8
  - Before: "A break whose status is `killed` or `timeout` counts caught, one whose status is `survived` or `nocoverage` counts missed, and a break that never reached a test counts for neither"
  - After: "A break whose status is `killed`, `timeout` or, from mutmut, `caught by type check` counts caught; one whose status is `survived`, `nocoverage` or, from mutmut, `no tests` counts missed; and a break with any other status, such as Stryker's `CompileError` or mutmut's `skipped`, counts for neither"
- RULE-9
  - Before: "A rule's number is what its own tests caught: a break only another rule's test caught counts missed for this one, and a rule whose tests the report never lists measures nothing"
  - After: "A rule's number is what its own tests caught: a break its tests reached and did not catch counts missed for it, even when another rule's test caught it; a break that timed out counts caught for every rule whose test reached it; a break its tests never reached counts for neither; and a rule whose tests the report never lists measures nothing"
- RULE-10
  - Before: "... so a name that begins another is not that test, and never across two files of the same name"
  - After: "... so a name that begins another is not that test; and by its file, so a test of the same name in a different test file is not that test". The product does not fully meet this; see product faults.
- RULE-17
  - Before: "A mutmut break is attributed to the scope entry whose last path segments match the most of the break's module name, a break no scope entry covers is left out, and every rule of a feature carries that feature's scope number with `attribution: \"per_scope\"`"
  - After: "A mutmut break counts for a feature when one of the feature's scope entries covers it, the entry's last path segments matching the first segments of the break's module name, so `src/login/session.py` covers `login.session`; a break no scope entry covers counts for no feature; and every rule of a feature carries that feature's scope number with `attribution: \"per_scope\"`"
- RULE-19
  - Before: "... and the reason is a sentence saying why"
  - After: "... and, when no other reason is given, the reason reads `no engine breaks go, shell or sql code, so test strength is not measured for these rules`"
- RULE-21
  - Before: "A mutmut break in a package's `__init__.py` is attributed to the scope entry naming that `__init__.py`, and a scope entry holding `*` is matched as a glob against the file the break changed, losing to any entry that names the file or its directory"
  - After: "A scope entry naming a package's `__init__.py` covers a mutmut break in that file, which mutmut names after the package, and a scope entry holding `*` covers, as a glob, a break in any file it matches"
- Why RULE-17 and RULE-21 changed: which entry "owns" a break cannot be seen, because a feature reports only the sum over its entries.

Product wrong:
- RULE-10 (reworded): a test in a different file with the same name is credited. Details under product faults.

Real choices for the owner (under questions):
- The per-rule number that nothing reads.
- Whether a rule counts strong when breaking was on but measured nothing.
- How mutmut breaks are matched to a scope (a `src/` folder gets nothing; a package's `__init__.py` takes its sibling files).
- The Stryker.NET fallback to any JSON file.

Checked and left as written: RULE-1 to 7, 11 to 16, 18, 20 and 22. RULE-5's "once per feature" is now shown by counting starts.

### `skill_sign`

**Reworded because the wording was loose and the skill was right (case a):**

- **RULE-2.**
  - Before: "The skill reads what waits for a person from `sync_status` as each rule's `left`, `to_test_by_hand` or `to_sign`, shows what the audit read and found with `scripts/review/ai_audit.py` before it writes anything, and writes the signature with `scripts/review/sign.py`, both scripts inside `${CLAUDE_PLUGIN_ROOT}`"
  - After: "The skill reads what waits for a person from `sync_status` as each rule's `left`, `to_test_by_hand` or `to_sign`, says to read what the audit read and found before anything is written, and names `scripts/review/ai_audit.py`, which shows it, ahead of `scripts/review/sign.py`, which writes the signature, both inside `${CLAUDE_PLUGIN_ROOT}`"
  - Why: the report flagged that the order of two script paths was being read as behaviour. The rule now says what the skill text says, and PROOF-30 checks the sentence itself.
- **RULE-3.**
  - Before: "The last section of `skills/sign/SKILL.md` names the next step and computes it from the cells the skill found, giving a `→` directive for each outcome"
  - After: "The last section of `skills/sign/SKILL.md` names the next step for each way the walk can end, pairing what it ended on with a `→` directive, except `Nothing left to do.`, which at the gates `passed` and `strong` names no command"
  - Why: "computes it from the cells" cannot be seen in the text. Also, the skill's `Nothing left to do.` row rightly names no command, as decision 76 settled.

**Flag that no longer applies:**

- **RULE-7:** the report said its test checked a `[level: passed]` sentence. The test now checks the rule's own `signed` clause, `Every rule waits for a signature once its tests pass and its audit is strong`, so rule and test agree. No change.

**Other results:**

- No rule was found where the skill does something other than what the rule says (case b).
- One real choice goes to the owner, under questions_for_owner.

### `upstream`

Section 5 of proofs-rewritten.md flags no upstream rule. I found these while reading.

(a) Loose wording where the product is right. I reworded these in commit 80675c685:
- RULE-5
  - Before: "A `--path` the source does not hold writes no file and reports the path it could not read"
  - After: "A `--path` the source does not hold writes no anchor copy and reports the path it could not read"
  - Why: the fetched checkout under `.purlin/runtime/anchors/` is still written. What the rule means is that no copy is written.
- RULE-10
  - Before: "`--json` prints the whole answer as one JSON object carrying `checked`, `behind` and a row per anchor; without it the lines name the anchor behind and the `purlin:anchor sync <name>` that fixes it"
  - After: "`--json` prints the whole answer as one JSON object carrying `checked`, `behind` and `anchors`, one row per anchor; without it each anchor behind gets a line naming it and the `purlin:anchor sync <name>` that fixes it"
- RULE-22
  - Before: "Every file the module writes lies under the project root it was given"
  - After: "Every file `add` and `sync` write lies under the project root they were given"

(b) The product is wrong: RULE-15, for plain `sync` (see product_faults).

(c) A real choice for the owner: the same RULE-15, whether to fix the product, narrow the rule or remove it (see questions_for_owner).

Decisions 60 to 85 change no word this spec quotes. The printed lines the proofs now quote were checked against the product's output, among them:
- `no_eval: the pin is current.`
- `no_eval: the pin <sha7> is behind its source, now <sha7>. Run purlin:anchor sync no_eval.`
- `no_eval: RULE-2 changed, RULE-3 added. Pin advanced from <sha7> to <sha7>.`
- `no_eval: written to specs/_anchors/no_eval.md, pinned <sha7>`
- `source rejected: begins with "-"`
- `source rejected: names an ext:: transport`

### `skill_test`

Reworded because the wording was loose and the product is right:

RULE-3.
Before: "The last section of `skills/test/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome".
After: "The last section of `skills/test/SKILL.md` names the next step: it lists at least two outcomes the run can end on, and every outcome gives a `→` directive except `Nothing left to do.`, which names no command".
Why: "computes it from the state" cannot be seen in the text. The skill leaves `Nothing left to do.` without a command, as decision 76 settled.

RULE-7.
Before: "...the skill shows the person the suggested entry, asks, writes it with the `purlin_config` tool under the key `tests`, and runs again; ...".
After: "...the skill shows the person the suggested command, asks, and on yes writes the suggested entry with the `purlin_config` tool under the key `tests` and runs again; ...".
Why: the skill says "Show the person the command and ask. On yes, write `[<entry>]`".

Flagged in section 5 and already right, left as they are:
- RULE-1: the check already requires a real row in a table headed Command and Purpose, with a purpose sentence.
- RULE-2: the check already reads each exit code's full meaning.
- RULE-5: the "counts the rules that meet the gate" clause is no longer in the rule; its several parts are now separate proofs.
- RULE-6: the rule's wording is right; the test now checks the whole nothing-selected line.

No rule was found where the product does not do what the rule says.

### `specs`

Reworded, because the wording was loose and the product was right:
- RULE-14. Before: "Every spec is keyed by its filename stem, and a file that cannot be read or decoded is skipped while the rest of the scan still answers". After: "Every spec is keyed by its filename stem, a file that cannot be read or decoded is skipped while the rest of the scan still answers, and a project with no `specs/` folder has no specs". The test already showed the missing-folder case; the rule now says it, as PROOF-40.

Flagged in section 5 and already settled:
- RULE-15 was deleted by decision 73.
- RULE-3's hash of a proof and its line-break case are now each proved.
- RULE-9's "rather than split on its first word" now has examples.

Where the product is wrong: none found.

Real choices for the owner, asked below:
- Two specs with the same file name.
- Tag rules written twice, here as RULE-4, 5 and 6 and in the spec format anchor as RULE-9 and 10.

### `skill_audit`

Reworded because the wording was loose and the product was right:
- **RULE-1**
  - Before: "... and `references/purlin_commands.md` carries a row for `purlin:audit`"
  - After: "... and `references/purlin_commands.md` carries a row for `purlin:audit` that states its purpose"
  - Why: the check has always required the purpose cell.
- **RULE-2** (flagged in section 5: "inside" read as a working directory)
  - Before: "The skill runs `scripts/run/purlin_run.py` inside `${CLAUDE_PLUGIN_ROOT}` with `--audit`, and states ..."
  - After: "The skill runs the run script by its path under the plugin root, `\"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py\"`, with `--audit` on the same line, and states ..."
- **RULE-3**
  - Before: "... and lets `Nothing left to do.` through as the one outcome that names no command"
  - After: "... and lets `Nothing left to do.` through as the one outcome that gives no `→` directive"
  - Why: at the gate `signed` the skill, and the product, go on to name the release step `git push origin signed/<version>`, which is a command, so the old words were untrue there. The section 5 flag, 'computes it from the cells the skill found', no longer appears in the rule.

Left as it is, with a question for the owner:
- **RULE-6** (flagged in section 5 as seven statements in one rule). Each statement now has its own positive proof, and each has at least one broken-copy proof. The old gap ('a rule waiting on one does not set its exit code' had no check) is closed by PROOF-39 and PROOF-16. Whether to split the rule is the owner's call.

Product wrong: none found.

### `skill_init`

Reworded, because the wording was loose and the product is right:
- **RULE-2.** It did not say where a flag had to be named, so a mention in passing prose would have counted (section 5).
  - Before: "The skill runs `scripts/init/scaffold.py` inside `${CLAUDE_PLUGIN_ROOT}`, passing `--project-root` and `--gate`, and names the `--mutation`, `--yes`, `--update` and `--add` forms, and no flag the script does not take"
  - After: "The skill runs `scripts/init/scaffold.py` inside `${CLAUDE_PLUGIN_ROOT}` on one line passing `--project-root` and `--gate`, and its lines that run the script and its flag table name the `--project-root`, `--gate`, `--mutation`, `--yes`, `--update` and `--add` forms, and no flag the script does not take"
- **RULE-3.** "Computes it from the state the skill found" cannot be seen in the text, and it is the script that prints the next step (section 5).
  - Before: "The last section of `skills/init/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome"
  - After: "The last section of `skills/init/SKILL.md`, whose heading names the next step or reads `When you are done`, lists each state the skill may find as an item with its own `→` directive, among them `No specs and no code`, `Code but no specs` and `Specs but no tests`"
- **RULE-5.** The skill and the script both ask the second question only where an engine exists for a framework the project carries; the rule left that out.
  - Before: "...and, at `strong` and `signed` only, whether to measure test strength..."
  - After: "...and, at `strong` and `signed` only, and only where an engine exists for a framework the project carries, whether to measure test strength..."

Flagged, and no change to the rule needed:
- **RULE-6.** Section 5 said the test compared the settings block with the template instead of with the seven names. The test already checks the seven names, and now also checks the keys a real setup writes. The rule reads right as it is.
- **The two held-rules notes.** "RULE-3: → one line only" is answered: every outcome is checked for its own `→`. "RULE-5: three answers not bounded; CI requirement per gate unchecked" is stale: the gate table must be exactly passed, strong, signed, and the CI clause is no longer in the rule.

Where the product is wrong: none found.

A real choice for the owner: whether `purlin:init --add` stays. It is asked below.

### `security_no_dangerous_patterns`

Reworded because the wording was loose and the product is right:

RULE-2
- Before: "No file under `scripts/` opts a subprocess into a shell: no `shell=True` in Python, no `shell: true` in JS or TS, no `UseShellExecute = true` in C#"
- After: "No file under `scripts/` writes the request that opts a subprocess into a shell, not even in a comment: no `shell=True` in Python, no `shell: true` in JS or TS, no `UseShellExecute = true` in C#"
- Why: the check has always read comments too, and the earlier proof already said so.

RULE-4
- Before: "No file under `scripts/` assigns a credential literal: no quoted value assigned to a name containing `password`, `secret`, `api_key` or `token`, in any casing, outside a test file"
- After: "No file under `scripts/` assigns a credential literal: no quoted value of one character or more is given to a name containing `password`, `secret`, `api_key` or `token`, in any casing, with `=`, or with `:` as a field in JS and TS, outside a file whose name begins `test_`"
- Why: this settles the flag that "assigns" left open whether a JS or TS field counts. It also says that an empty value is not counted and exactly which file is exempt. The check is if anything stricter than the old "test file" wording, and scripts/ holds no test_ file.

RULE-6
- Before: "... `--end-of-options` precedes every revision argument that comes from outside Purlin ..."
- After: "... `--end-of-options` precedes an anchor's `> Source:` address and every revision argument that comes from outside Purlin ..."
- Why: the product puts the separator before the Source address in `git ls-remote` and `git clone`, and PROOF-9 shows it. The old wording named only revisions. The rest of the rule is unchanged.

Flagged rules already settled before this lane:
- RULE-1, indented shell `eval`: now caught (PROOF-15).
- RULE-5, Popen: now read (PROOF-37 to 39).
- RULE-6, revisions: shown in drift (PROOF-10, 12, 13).
- RULE-4, a name containing `token`: settled by decision 65.

Real choices for the owner (see questions_for_owner):
- RULE-1: a C# launch given a command held in a name.
- RULE-5: the Python launch given a name.
- RULE-1 and RULE-3: both name PHP `system(` and `passthru(`.

Product wrong: none found.

### `skill_export`

(a) The wording was loose and the product is right, so the rule was reworded:

RULE-1 (section 5: "carries a row" was read as any mention of the command).
- Before: "`skills/export/SKILL.md` opens with a frontmatter block whose `name` is `export` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:export`"
- After: "`skills/export/SKILL.md` opens with a frontmatter block whose `name` is `export` and whose `description` is one non-empty line, and the table of commands in `references/purlin_commands.md` carries a row for `purlin:export` with its purpose"

RULE-2 (section 5: "runs" was not told apart from "mentions").
- Before: "The skill runs `scripts/export/package.py` and names each form of the command: bare, `--release <name>`, `--commit` and `--check <file>`"
- After: "The skill gives the command line that runs `scripts/export/package.py` and names each form of the command on a line of its own: bare, `--release <name>`, `--commit` and `--check <file>`"

RULE-5 (section 5: the heading check also accepted "when you are done", and "each outcome" named no outcomes).
- Before: "The last section of `skills/export/SKILL.md` names the next step, giving a `→` directive for each outcome"
- After: "The last section of `skills/export/SKILL.md` is headed with the words `next step` and gives a `→` directive for each outcome of an export: evidence not committed, no version, `not finished`, `finished` and a `--check` mismatch"

RULE-3, RULE-4 and RULE-6 are unchanged.

(b) Product faults: none. The skill says what each rule asks.

(c) A real choice: the line the skill prints when a package fails its fingerprint check. See questions_for_owner.

### `schema_spec_format`

(a) Loose wording, product right, reworded:

- RULE-2 before: "Rule ids read `RULE-N`, are assigned in increasing order and are never reused, so a retired rule leaves its number vacant ..."
  After: "Rule ids read `RULE-N`; the author assigns them in increasing order and never reuses one, so a retired rule leaves its number vacant ..." (the rest is unchanged).

- RULE-4 before: "A rule that no proof line names carries an empty proof list and reads `no test` in its passed cell with the reason `no proof written`, so a spec cannot claim evidence it does not have"
  After: "A rule that no proof line names carries an empty proof list, and while no test marked with the rule's own id answers it, its passed cell reads `no test` with the reason `no proof written`, so a spec cannot claim evidence it does not have". This matches the format reference and the quality guide. The product honours a rule-marked test at both `passed` and `strong`.

- RULE-6 before: "... parsed into a list in the order written, because the fingerprint hashes exactly those files to tell a code change from a rule change"
  After: "... parsed into a list in the order written, and the code part of the spec's fingerprint hashes exactly those files, so an edit to any other file leaves it unchanged and a code change is told from a rule change".

- RULE-9: added "; a second `@manual` reads as one, and of two `@env` tags the last written is the environment and the earlier is returned in the unknown list". The rest is unchanged.

- RULE-10 before: "any other value, and any tag this release stopped reading, is returned in the unknown list and sets no environment, so a proof is never treated as owned by an operating system the release cannot name"
  After: "any other value, a bare `@windows`, and any other at-word carrying a value in brackets is returned in the unknown list and sets no environment, so a proof is never treated as owned by an operating system the release cannot name; a `@manual` carrying a value still reads as `@manual`". The old wording did not cover `@smoke(x)`, and did not say that a stamped `@manual` still reads manual.

(b) Product wrong: none against a rule as written. The count mismatch for a doubled rule id is listed under product_faults.

(c) Real choices: RULE-2 (a doubled or out-of-order id), RULE-3 (an unreadable proof line, and this project's one-rule-only check) and RULE-7 (what the heading means). All three are listed under questions_for_owner.

### `purlin_agent`

Four rules had loose wording while the agent definition was right. Each is reworded (type a). No rule describes something the product does not do (type b).

**RULE-3**
- Before: "...and they are: evidence or a signature is never written by hand, no signature is ever written on a person's behalf, nothing is pushed and no pull request is opened except the run branch `purlin:test --remote` owns, and nothing is called by a name other than the one `references/glossary.md` gives it"
- After: "...and they are: evidence or a signature is never written by hand; no signature is ever written on a person's behalf; the agent never pushes, never writes a tag itself, never opens a pull request and never deletes or rewrites a remote branch, except the run branch `purlin:test --remote` owns; and nothing is called by a name other than the one `references/glossary.md` gives it, and no emoji is written anywhere"
- Why: the report flagged that the items forbid more than the rule listed (the tag and emoji). The rule now lists exactly what each item forbids, and the test checks the tag and emoji wording.

**RULE-4**
- Before: "...and every `purlin:` command it names is one of the commands `references/purlin_commands.md` lists"
- After: "...and every `purlin:` command it names, read without the words and flags that follow it, is one of the commands `references/purlin_commands.md` lists"
- Why: the report's other point, that the test never read the reference, was already fixed on main.

**RULE-5**
- Before: "...and names the reason `no proof written`, the three steps `passed`, `strong` and `signed`, and the `out of date` word that means the spec, the code or the tests moved since the run"
- After: "...and the paragraph that says so names the three steps `passed`, `strong` and `signed`, says the reason `no proof written` means no proof line names the rule, and says `out of date` means the spec, the code or the tests moved since the run"
- Why: the test already checked the paragraph; the rule now says so.

**RULE-7**
- Before: "The agent says what carries a feature's name and moves together on a rename: ... the evidence files, then `sync_status` to find what was missed"
- After: "The agent says what carries a feature's name and moves together, in one commit, on a rename: ... the evidence files, moved with `git mv`, then `sync_status` to find what was missed"
- Why: the report flagged that the test asked for git mv, one commit and the order, which the rule did not name.

RULE-1, 2, 6 and 8 read right against the product and are unchanged. Two real choices go to the owner as questions: the 135-line ceiling, and whether the agent explains the `no proof` word and keeps the no-emoji line inside the naming NEVER.

### `skill_build`

(a) The wording was loose and the product was right, so the rule is reworded. Section 5 flagged these because they described what the skill does, while the spec is about what the skill's file says.
- RULE-2
  - before: "The skill chooses what to build from `sync_status` and runs the tests through `purlin:test`, never through the test framework directly"
  - after: "The skill tells the agent to choose what to build from `sync_status` and to run the tests through `purlin:test`, never through the test framework directly"
- RULE-3
  - before: "The last section of `skills/build/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome"
  - after: "The last section of `skills/build/SKILL.md` tells the agent to name the next step from the summary and `Left to do` that `purlin:test` ended on, and lists the outcomes, each with its own `→` directive"
  - The flag on this rule (only 2 of 5 outcomes had `→`) no longer applies: decision 65 has since been applied to the skill.
- RULE-5
  - before: "The commit the skill makes carries the `feat(<name>):` subject prefix and a body whose Changeset section maps every rule ..."
  - after: "The skill tells the agent to make one commit per build with the `feat(<name>):` subject prefix and a body whose Changeset section maps every rule ..."
  - The rest of the rule is unchanged.
- RULE-6
  - before: "The skill compares the files the build created, changed or deleted for the feature with its `> Scope:`, adds each new file no entry covers, removes each entry whose file was deleted, and rewrites the line in the same commit as the code"
  - after: "Before it commits, the skill tells the agent to compare the files it created, changed or deleted for the feature with the spec's `> Scope:`, add each new file no entry covers, remove each entry whose file was deleted, and rewrite the line in the same commit as the code"
- RULE-7
  - before: "For each proof with no marked test the skill looks first for an existing test that already shows what the proof asks and offers to add the marker above it, writing nothing new; otherwise it writes an ordinary test ..."
  - after: "For each proof with no marked test the skill tells the agent to look first for an existing test that already shows what the proof asks and offer to add the marker above it, writing nothing new; otherwise to write an ordinary test ..."
- RULE-8
  - before: "Before the tests run, the skill runs `scripts/mcp/purlin/markers.py --near-misses`, shows each comment it returns with its fix and the reason, asks, and makes the edits the person accepts"
  - after: "In a section before the one on running the tests, the skill gives the command `scripts/mcp/purlin/markers.py --near-misses` and tells the agent to show each comment it returns with its fix and the reason, ask, and make the edits the person accepts"
- RULE-9
  - before: "The skill runs the tests through `purlin:test`, which suggests and writes the test command where none is set, and the skill writes no test command itself"
  - after: "The skill tells the agent that `purlin:test` suggests and writes the test command where none is set, and that the agent writes no test command itself"
- RULE-1 is unchanged. Its flag (the row was found anywhere in the file) was already settled: the check requires a table row whose first cell is `purlin:build` and whose second cell gives its purpose.

(b) The product is wrong: RULE-5 against the commit conventions' example. See product_faults.

(c) Real choices: questions 1 to 4.

### `skill_spec_from_code`

Category (a), loose wording, product right; reworded. The spec's Description says it covers what the skill must say, so each rule now says what the skill tells its reader instead of claiming what an agent does.
- RULE-1. Before: "... and `references/purlin_commands.md` carries a row for `purlin:spec-from-code`". After: "... carries a table row for `purlin:spec-from-code` with its purpose beside it". The check already needed a row with a second cell that is not empty; the report had flagged this rule because the rule read as a match of the name anywhere.
- RULE-2. Before: "The skill calls `sync_status` before it surveys anything and sends the reader to `purlin:init` when the project carries no `.purlin/config.json`". After: "Before its procedure, the skill tells the reader to call `sync_status`, and to run `purlin:init` first when the project carries no `.purlin/config.json`". The report's flag, that nothing checked the order, was already fixed on main.
- RULE-3. Before: "The last section of `skills/spec-from-code/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome". After: "The last section of `skills/spec-from-code/SKILL.md` tells the reader to name the next step from the state the skill found, and lists at least two such states, each carrying its own `→` directive".
- RULE-6. Before: "Where an existing test already shows what a proof the skill writes asks, the skill offers to add the marker comment `purlin: <feature> PROOF-<n>` above that test and writes no new test". After: "In its paragraph on an existing test that already shows what a proof asks, the skill tells the reader to offer to add the marker comment `purlin: <feature> PROOF-<n>` above that test and to write no new test".
- RULE-7. Before: "The skill gives every source file a rule where it can, and its report ends by listing the source files that got none, for a person or an agent to decide". After: "The skill tells the reader to give every source file a rule where it can, and to end the report by listing the source files that got none, for a person or an agent to decide".
- RULE-8. Before: "The skill leaves an existing test untied for one of three reasons, and its report lists each such test with its reason: ...". After: "The skill says an existing test is left untied for one of three reasons, and that the report lists each such test with its reason: ..." (the three reasons unchanged).
- RULE-9. Before: "Every rule the skill writes says what its test expects, whether that test passes or not, and the skill runs no test before it writes the rules". After: "The skill says every rule is written from what its test expects, whether that test passes or not, and that no test is run before the rules are written".
- RULE-5, flagged in section 5, was already removed under decision 73.
Category (b): none. Category (c): the two questions below.

### `config_engine`

(a) Loose wording where the product is right. Each rule was reworded to say what the product does.

RULE-5
- Before: "The command line prints the whole config as JSON with `--dump` and one key's value with `--key <name>`"
- After: "The command line prints the whole config as JSON with `--dump`, and with `--key <name>` one key's value, or an empty line when the config holds no such key; any other use prints nothing to standard output, prints its usage or the argument it does not know to standard error, and exits 1"
- Why: the old rule did not say what happens for a missing key or for a refusal, and the product already handles both in a fixed way.

RULE-10
- Before: "A write is atomic: the whole file is written beside the target and then moved onto it, so an interrupted write leaves the previous contents and no temporary file behind"
- After: "A write is atomic: the whole file is written beside the target and then moved onto it, so a write that fails at any point leaves the previous contents whole and removes the file it wrote beside the target"
- Why: a process killed between the two steps leaves `.purlin/config.json.tmp` behind. No code can clean that up, so "no temporary file" holds only for a failure the program sees.

RULE-13
- Before: "`resolve_project_root` returns the root together with the name of how it was found, and is the one implementation of the precedence RULE-1 to RULE-3 describe: the three names are `env`, `climb` and `cwd`, each mapped to the sentence a report prints for it, so the last case is named as the guess it is rather than handed back as a path indistinguishable from a marker that was found. `find_project_root` is the same answer with the name dropped, and nothing recomputes the precedence for itself"
- After: "The project root comes with the name of how it was found, `env`, `climb` or `cwd`, by the precedence RULE-1 to RULE-3 describe, each name with the sentence a report prints for it, so a root that is only the working directory is named as that guess and not handed back as if a marker were found. Asked for alone, without the name, the root is the same answer"
- Why: the rule named two functions. It also claimed "nothing recomputes the precedence for itself", which describes how the code is arranged and cannot be shown by a test. It is true today: only one place in scripts/ climbs for `.purlin/`. The part that can be observed stays: asked for alone, the root is the same answer, and each of the four root proofs now checks it.

(b) Product wrong: none found against the rules as written.

(c) Real choices: three, in questions_for_owner. Also noted, not asked: RULE-8 and RULE-9 overlap. PROOF-8 (adding a key keeps `team`) and PROOF-12 (changing `gate` keeps `version`) already show what RULE-9 claims. They could be merged into one rule.

### `server`

Loose wording where the product is right, reworded in commit 7b8e5952d:

- RULE-6.
  Before: "A call may name its own workspace with `project_root`, which is resolved and used for that call alone; without it the tool uses the root the server resolved at startup"
  After: "A call may name its own workspace with `project_root`, which is resolved, a leading `~` standing for the home folder, and used for that call alone; without it the tool uses the root the server resolved at startup"
  Why: "resolved" did not say what it does; the server expands `~` and makes the path absolute, and PROOF-129 shows the `~` case.

- RULE-7.
  Before: "A root holding no `.purlin/config.json` answers with a line naming that root, how it was chosen and what to run, rather than reporting a project with nothing in it"
  After: "A tool called on a root holding no `.purlin/config.json` answers only with that root, how it was chosen and what to do, rather than reporting or writing a project there"
  Why: the answer is two lines, not one; its second line offers three fixes, not one command to run; and the check covers all three tools, including a write.

- RULE-8.
  Before: "A tool that raises answers with the text `Error running <tool>` and the message, so one bad call never ends the session"
  After: "A tool that raises answers the text `Error running <tool>: <message>`, so one bad call never ends the session"
  Why: it now quotes the exact form the server writes.

Product wrong: none found. Real choices for the owner: three, under questions_for_owner.

### `skill_status`

All four rules flagged in section 5 were loose wording where the product is right (category a). I reworded each; before and after:

RULE-1 (was: unclear whether "row" means the table row).
- Before: "`skills/status/SKILL.md` opens with a frontmatter block whose `name` is `status` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:status`"
- After: "`skills/status/SKILL.md` opens with a frontmatter block whose `name` is `status` and whose `description` is one non-empty line, and the table of commands in `references/purlin_commands.md` carries a row for `purlin:status` whose purpose cell is not empty"

RULE-2 (was: a rule about behaviour, proved only by the text).
- Before: "The skill prints the sentence and the `Left to do` lines `sync_status` returned and never recounts them, so the command line and the dashboard cannot disagree"
- After: "`skills/status/SKILL.md` tells the agent to print the sentence and the `Left to do` lines `sync_status` returned and never to recount them; those lines and the data the dashboard reads come from one computation, so the two cannot disagree"

RULE-3 (was: only one arrow required, and the header row counted as an outcome). The "computes it from the state" wording was already gone, and the shared helper already leaves the header out.
- Before: "The last section of `skills/status/SKILL.md` names the next step, the first line of `Left to do`, and gives a `→` directive for each kind of line but `Nothing left to do.`, which names none"
- After: "The last section of `skills/status/SKILL.md` names the next step, the first line of `Left to do`; its table names every kind of `Left to do` line with a `→` directive to the command that line names, and every row gives a `→` directive but `Nothing left to do.`, which names none"

RULE-5 (was: "shows" describes output the test cannot see).
- Before: "`purlin:status <name>` shows one spec, its rules and their cells, and both `skills/status/SKILL.md` and `references/purlin_commands.md` name that form"
- After: "`skills/status/SKILL.md` says that `purlin:status <name>` shows one spec, its rules and their cells, and what it does when several specs or none match the name, and `references/purlin_commands.md` names that form `purlin:status [name]`"

RULE-4 was not flagged and is unchanged.

Product faults under these rules: none. Real choices: two, asked below.

Separately, the status skill's Step 3 says the tool "ends on one sentence and `Left to do`, the words every surface ends on". Decision 85 took the `Left to do` list off the dashboard, and decision 92 on main took the sentence off, so that phrase is no longer true of the dashboard. No rule of this spec quotes it and I do not own the skill file, so I report it under product_faults and change neither.

### `skill_spec`

Reworded because the wording was loose and the product is right (the change is in commit 669f6e062):

- RULE-2. The skill says ids are "allocated against `origin/main`, not against the working tree", and then that "the next id is one past the highest in either copy of the spec". So the working tree's copy counts too. The rule said "never against the working tree".
  - Before: "The skill allocates rule and proof ids against `origin/main`, read with `git show origin/main:<spec>`, never against the working tree"
  - After: "The skill allocates rule and proof ids against `origin/main`, read with `git show origin/main:<spec>`, and not against the working tree alone: the next id is one past the highest in either copy of the spec"
- RULE-5 (flagged in section 5). The skill says "and no tag is written", and so do references/formats/spec_format.md and references/hard_gates.md. The rule left it out.
  - Before: "...and says that a spec naming no files has its tests run on every `purlin:test` and cannot be signed at the gate `signed`"
  - After: "...and says that a spec naming no files has its tests run on every `purlin:test` and that, at the gate `signed`, its rules cannot be signed and no tag is written"

No change to the wording; the flag is now answered by a test:
- RULE-1: "carries a row" is read as the table row (PROOF-14, PROOF-20).
- RULE-3: "with nothing printed after it" is held by PROOF-24. The skill's paragraph for an edited spec says "before the offer", held by PROOF-3 and PROOF-27.
- RULE-6: "before it saves" is held by the order check (PROOF-6, PROOF-38).

Product faults: none.

Real choice for the owner: whether a rule about what a skill does is proved by reading its instructions. See questions_for_owner.

### `purlin_version`

Reworded because the wording was loose and the product was right (sort a):

RULE-2. It did not mention what happens with no VERSION file, although the old PROOF-2 already claimed it.
- Before: "The `purlin` package reads the version out of the `VERSION` file at import time and assigns it to `PURLIN_VERSION`, and the server reports that value rather than a literal of its own"
- After: "... rather than a literal of its own; with no `VERSION` file, both read `0.0.0`"

RULE-3 (flagged in section 5: is the stamping a description or a claim?). Setup copies the template's other keys but takes `version` from the VERSION file directly, so the old clause described the mechanism wrongly. The stamp is now a claim, and PROOF-21 shows it.
- Before: "The `version` field of `templates/config.json`, which `purlin:init` stamps into a new project, equals the `VERSION` file"
- After: "The `version` field of `templates/config.json`, the settings template `purlin:init` copies into a new project, equals the `VERSION` file, and a project `purlin:init` sets up is stamped with that same version"

RULE-4 (flagged in section 5). "Outside its comments" did not match the check, which sets aside only lines that are wholly comments. The rule also did not name the `0.0.0` exception. The new wording matches the check exactly; the package already passes it.
- Before: "No module of the `purlin` package carries a release version literal outside its comments"
- After: "No module of the `purlin` package carries a quoted release version, three whole numbers joined by dots, on a line that is not wholly a comment; the one exception is `0.0.0`, which the package reports when the `VERSION` file cannot be read"

RULE-7 (flagged in section 5):
- The part about `--check` "still reporting the ones that match" is now shown line by line, so that wording stays unchanged.
- The "one propagation entry point" part is a real choice and goes to the owner. The rule is unchanged.

Product wrong (sort b): none found.

### `skill_anchor`

(a) The wording was loose and the product is right. I reworded three rules:

RULE-1
- Before: "`skills/anchor/SKILL.md` opens with a frontmatter block whose `name` is `anchor` and whose `description` is one non-empty line, and `references/purlin_commands.md` carries a row for `purlin:anchor`"
- After: "`skills/anchor/SKILL.md` opens with a frontmatter block whose `name` is `anchor` and whose `description` is one non-empty line, and the `Command`, `Purpose` table of `references/purlin_commands.md` carries a row for `purlin:anchor` with its purpose"
- Why: section 5 flagged that "a row" was vague. The check already requires a row in that table with the purpose filled in.

RULE-2
- Before: "The skill runs `scripts/anchor/upstream.py` inside `${CLAUDE_PLUGIN_ROOT}` for `add` and `sync`, and names `sync --check` as the read-only form `purlin:drift` runs as well"
- After: "The skill runs `scripts/anchor/upstream.py` inside `${CLAUDE_PLUGIN_ROOT}` for `add` and `sync`, and its `sync` section says that `--check` reports without writing and that `purlin:drift` runs the same check"
- Why: section 5 flagged it as a claim about meaning. The tests check that the `sync` section says those two things.

RULE-3
- Before: "The last section of `skills/anchor/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome"
- After: "The last section of `skills/anchor/SKILL.md` names the next step for each state the skill can end in, at least two, and gives each its own `→` directive"
- Why: nothing a reader can check shows the skill "computing" anything. Section 5's flag, that only one of the endings carried an arrow, was settled by decision 65: all three now carry one, and the tests check every ending.

RULE-4, RULE-5 and RULE-6 were left as written; they read correctly against the skill.

(b) Product wrong: none found.

(c) A real choice: one, the contradicting-instruction question under questions_for_owner.

### `skill_drift`

Reworded, because the wording was loose and the product is right:

RULE-2
- Before: "The skill takes its data from the `drift` tool and points at `references/drift_criteria.md` for what each view's lines mean rather than restating it, and it invents no line the tool does not return"
- After: "The skill takes its data from the `drift` tool, tells the agent to print the lines the tool returns as they come and to invent none, and points at `references/drift_criteria.md` for what each line means and where it comes from rather than restating it"
- Why: "invents no line" was a claim about the agent at run time. The skill does tell the agent this, and the tests show that it does.

RULE-3
- Before: "The last section of `skills/drift/SKILL.md` names the next step and computes it from the state the skill found, giving a `→` directive for each outcome"
- After: "The last section of `skills/drift/SKILL.md` names the next step in a table that gives, for each kind of line the three views print and for a view that shows no change, the `→` directive to print when the view shows it"
- Why: nothing in the test matched "computes it from the state". The table's left column is that link, and PROOF-27 now checks it.

RULE-1
- Before: "... carries a row for `purlin:drift`"
- After: "... carries a row for `purlin:drift` in its command table, with its purpose"
- Why: section 5 flagged that the word "row" was stricter than the check. The shared check now requires a table row with a purpose cell, and PROOF-17 and PROOF-18 show it, so the wording now says so.

Where the product is wrong: two faults, listed under product_faults.

Real choices for the owner: one, listed under questions_for_owner.

### `claude-md`

Corrections made in CLAUDE.md (before -> after):
1. Design and copy: "The three screenshots, the board, the queue and one rule, are taken by" -> "The two screenshots, the board and one rule, are taken by". Rewrapped.
2. Format versioning trigger: "When you change spec, proof, anchor, evidence or signature parsing or emission:" -> "When you change spec, proof, anchor, marker, evidence, signature or package parsing or emission:". The table below it governs six formats, and the old line left out markers and the package.
3. Step 1: "in `scripts/mcp/purlin/`, `scripts/review/`, `scripts/run/` or a skill definition" -> "in `scripts/mcp/purlin/`, `scripts/review/`, `scripts/run/`, `scripts/anchor/`, `scripts/export/` or a skill definition". upstream.py writes the anchor pin lines and package.py writes the package.
4. Step 4: "Grep `docs/`, `skills/` and `agents/purlin.md`" -> "Grep `docs/`, `skills/`, `references/` and `agents/purlin.md`". Four references outside the quality guide cite format files: glossary, hard_gates, drift_criteria and supported_frameworks.
5. signature_format.md row: "read by `sync_status` and `scripts/ci/gate_check.py`" -> "read by `sync_status` and `purlin:export`".
6. evidence_format.md row: "read by `sync_status` and `scripts/ci/gate_check.py`" -> "read by `sync_status` and `purlin:export`".
7. hard_gates.md row: "The gate, the three levels, ..." -> "The gate, the three steps, ...". The glossary word is step, and the section is "The three steps".
8. spec_quality_guide.md row: "Writing a rule, choosing its level, the guideline for a good proof, reading the cell that blocks it" -> "Writing a rule, the guideline for a good proof, reading the cell that blocks it".
9. supported_frameworks.md row: "the `tests` entry init writes for each" -> "the `tests` entry the first test run suggests for each". Setup writes an empty tests setting, and the first run suggests the entry (decisions 70 and 80).
10. Version check: "marked `ok`, `DRIFT` or `absent`" -> "marked `ok`, `DRIFT`, `FAIL` or `absent`". The script prints FAIL for a file with no version key. Rewrapped.
Product faults: none found. Everything CLAUDE.md now says matches the code.


## For integration

### `group_states`

- I rebased the branch onto main twice while working, because main gained decisions 86 to 92 and the dashboard commits for them. The branch now sits on e7286b0bb and fast-forwards.
- Decision 90 is applied. RULE-49 now allows the one difference between the dashboard and the terminal: `1 (+1)` on the dashboard, `1 (+1 shared)` in the table. PROOF-58 now builds the dashboard page in memory from scripts/report/src, using the build() function of dev/build_report.py. It never reads the committed scripts/report/purlin-report.html, which can lag its sources. It opens the page with headless playwright (from dev/browser_launch) over the three sample payloads and compares every cell with the status table's rows. The test is skipped where playwright is missing.
- main currently fails 5 purlin_report rules: RULE-35, 40, 45, 47 and 49. Their tests still expect `(+1 shared)`, the old top bar and the old colours. The purlin_report lane has to update them.
- Decision 92 takes the summary sentence off the dashboard. The summary spec's `> Description:` still lists the dashboard among the surfaces that read "these words". It stays true for the `Left to do` lines, which name the filter buttons. Change it when the dashboard change lands.
- Two frozen helpers still carry the retired runtime proof file. `dev/sign_project.py` has `Project.proofs()`, which writes `.purlin/runtime/proofs/login.json`, and both helpers' docstrings mention it. Nothing in scripts/ reads that file. My tests no longer call `proofs()`, but other lanes' tests do (dev/test_ai_audit.py and the signatures tests). The clean-release sweep should delete it.
- The id order is the file's order by rule, and new ids go up to states PROOF-181 and summary PROOF-28. The next free ids are states PROOF-182 and summary PROOF-29.

### `purlin_report`

MAIN HAS MOVED ON THE DASHBOARD. It is 13 commits past this branch's base, including decisions 86 to 93 and three feat(purlin_report) commits (9476c706b, 57450af75, cd3dd0a19). Those commits change scripts/report/src/app.js and board.js but not the spec or the tests.
- Decision 89, on main, withdraws the last part of decision 85: the reasons and the audit's findings stay on the rule's own page. I applied that (commit f6ba3d5fe). RULE-56 and PROOF-132 and 170 to 172 were written and then deleted; their ids are not reused.
- The merge will conflict in app.js (topBar and ageLine) and board.js (the rulesCell comment).
- After the merge, main's changes break proofs this branch holds:
  - Decision 88 drops the sha from the signed-tag box: PROOF-55 expects `signed/1.4.0 · a1b2c3d`.
  - Decision 90 makes the Rules cell read `1 (+1)` and adds a first hover line: PROOF-71, 72, 113, 142 and 163 and RULE-35, 47 and 49 quote `(+1 shared)` or `(+6 shared)`.
  - Decision 91 moves the refresh words into the age's hover.
- Not done here, and their rules still say the opposite:
  - Decision 87: the `No proof` box first. RULE-51 still says it follows the step boxes.
  - Decision 92: no summary sentence, and the total under `Passing`. RULE-54 and PROOF-121 stay until that is done.
  - Decision 93: no `n/a`, and a hover on the strength. RULE-9 still quotes `n/a`.
- Decision 91 darkens the muted ink on main. That may make my contrast fix (`.kv .tag.plain` drawn in the secondary ink) unnecessary; it is harmless either way.
- Docs out of date, not mine to edit: docs/dashboard.md (the Weak, Not audited and No proof filters table, the Queue and Stale cards, `No rule matches every filter you set.`, and the screenshot alt text at line 40). docs/raising-the-gate-and-upgrading.md:90 says the board 'grows ... a filter' at a higher gate; buttons now appear at every gate.
- The screenshots in docs/images need retaking with dev/capture_doc_screenshots.py once the page settles (decision 63). The script's clicks are unchanged and only its comments were updated. PROOF-23 checks only that both images exist.
- The built page was not staged.

### `run_script`

Only specs/run/run_script.md and dev/test_run_script.py changed. New proof ids are PROOF-144 to PROOF-206; the highest id in the spec's history was 143, so no id is reused. The test file now has 160 tests, one per proof, where it had 135 (collected, parametrized cases included). No frozen helper was touched. Two new fixtures live in the test file: `suggestions` (module scope) runs the real run once for each of the seven tools, and `twelve_features` (module scope) runs the twelve-feature selection once. PROOF-130 to PROOF-133 now check what the run prints in `Suggested entry:` rather than the internal table. A break that shortened the printed globs failed 3 tests; before this change it would have failed only the test of PROOF-126.

Gap check, section 3: PROOF-10 is closed. PROOF-114 now asserts that the skipped foreign proof reads `not run`. When I made the evidence writer always record `missing`, PROOF-10 and PROOF-114 both failed, with "assert [('PROOF-1', ...', 'missing')] == [('PROOF-1', ...', 'not run')]". PROOF-21 was already closed: PROOF-124 shows freebsd14 reads `linux`.

Other breaks I made, each restored with git checkout:
(a) Changed the first commit's subject to 'purlin: work for %s'. PROOF-203 failed with "assert 'purlin: work for feat' == 'purlin: spec...ings for feat'".
(b) Listed only spec paths under the Committed line. PROOF-204 failed.
(c) Made the evidence reader ignore evidence files git does not track. PROOF-162 failed with "assert 'not run' == 'passed'".
(d) Printed the suggested entry with one glob. PROOF-126, 132 and 133 failed.

None of these tests can reach the real claude: the session conftest puts a fake claude first on PATH, and the unreachable-model tests set the claude lookup to None or install their own fake. The git host's commit is faked in-process.

One thing for another lane, which owns the summary: a rule whose only missing run is on another operating system reads `0 of 1 · 1 partial` and is listed as `1 rule to fix: purlin:build`, although nothing needs fixing. This is question 1 below.

### `signatures`

- **Merging.** Main has moved 9 commits (decisions 86 to 90, report and design). None of them touches my 4 files, so the branch needs a rebase or a merge but should not conflict.
- **The decision 85 change** is in scripts/review/sign.py (main() and its docstring). Given `login RULE-1 RULE-9`, the command first prints `login RULE-9 is not a rule any spec has.`. It then signs RULE-1 in one signed commit under `sign(login): RULE-1` and prints the usual `Signed 1 rule as ...` line, the rule list and the summary ending. It exits 1. When every rule named is unknown it prints the line or lines only, writes nothing and exits 1, as before.
- **Docs.** No doc or skill describes the unknown-rule case: I grepped skills/, references/ and docs/, and only dev/plans/phase1-plan.md mentions it. Nothing there is stale.
- **Proof ids.** The highest id in the spec's history was 125. The new ids are 126 to 145.
- **What the tests now go through:**
  - The tag proofs (67, 68, 74, 79, 100, 101, 103, 105, 111) run the walk, which is what the command runs with no argument. They used to call the tag step alone, so each expected output now opens with `Nothing is waiting for someone to test by hand or to sign.`.
  - The machine proofs (119 to 122) record real results instead of hand-built machine maps.
  - The evidence proofs (63, 135 to 137) read the `evidence` field of a signature the command actually wrote.
  - PROOF-24 and PROOF-90 now run `--all` over two features. PROOF-24 no longer builds a subject directly, because the command always sorts the features, so the old unsorted-order case cannot happen through the command.
- **The signatures evidence** changes once the branch lands, since its proofs and tests changed.

### `scaffold`

- The owned test files, whole: 94 tests before (92 pytest + 2 shell files), 109 after (107 pytest + 2 shell files). Proofs: 81 before, 107 after. The new ids are PROOF-99 to PROOF-125. PROOF-57 is deleted and its id is not reused.
- Most of RULE-36 and RULE-37 moved out of the two shell files into dev/test_init_scaffold.py. A shell file counts as one test, so it cannot carry one proof per case. The new last section of test_init_scaffold.py builds a real python, typescript and C# project once per file and runs the commands a person runs. Each step (PROOF-36, 90, 117, 91, 118, 92, 119, 93, 37, 94, 95) has its own test. It uses the session's fake `claude`: a guard checks that the `claude` on the search path is the fake one. It unsets every GITHUB_/SYSTEM_/BUILD_/RUNNER_ variable, and no token is set.
- dev/test_init_e2e_wiring.sh now carries PROOF-96 alone. dev/test_init_e2e_gates.sh carries no marker. It runs `dev/init_e2e_walk.sh all`, so the typescript and C# projects still walk all three gates in the sweep. dev/run_tests.sh still names both files, so neither could be deleted.
- Decision 93 (on main, after my range) rewords setup's Stryker line, which still ends `the test strength reads n/a.`. RULE-9 and PROOF-9, 105 and 106 quote that line exactly. When that product change lands in scripts/init/scaffold.py, those four lines and the helper `_told_about_stryker` in dev/test_init_scaffold.py need the new wording.
- Nothing in the owned files was run through purlin:audit, signed, pushed or tagged.

### `update`

This branch holds two commits on top of 57ebd6168 and touches only specs/init/update.md and dev/test_init_update.py. main has moved on since then (9476c706b and others), so the merge needs a rebase and cannot be a fast-forward. The rebase should be clean because no other lane owns these two files.

Proof ids: the spec's history reached PROOF-66. The new ids run from PROOF-67 to PROOF-113, and the next free id is PROOF-114. PROOF-3, 14, 17 and 22 were deleted earlier and are not reused. Proofs are now grouped by rule, in rule order, and by id within each rule. PROOF-32 in particular moved up to sit with RULE-15.

Test file: the LAYOUTS parametrization is gone (it held one layout). Several tests are renamed or split. Shared setups are now helpers in the file itself: _rewritten, _unwired, _hooks, _with_specs, _with_anchor, _detected_suites, _backed_up and _workflows. No frozen dev helper module was touched.

One assertion was removed: the PROOF-11 test used to count how often 'report' appears in the update script's own source and to check a constant list inside it. The behaviour is now shown with the switch set on (PROOF-11) and set off (PROOF-44). This is the "closed in part" item from section 3.

The test for PROOF-98 now adds the line as `PROOF-14` (the next free id in that fixture anchor) instead of `PROOF-99`, so the example does not read like one of this spec's own ids.

Deliberate breaks: each ran against scripts/init/update.py and was restored with `git checkout -- scripts/init/update.py`. The tests start only the update script, local git and a local bare repository, so nothing reached `claude` or a network service.

No format reference changed. Nothing was signed, audited, pushed or tagged.

### `evidence_writer`

These are three commits on split/evidence_writer that touch only the spec and its test file. The branch was cut at 57ebd6168, and main has moved 10 commits since, none of them to these two files, so a rebase or merge should be clean. The next free proof id is PROOF-75: PROOF-55 to PROOF-74 are now used, and the spec's history had no id above 54. Three rule texts changed (RULE-4, RULE-8, RULE-11), so their rule hashes change, and so do the proof hashes of every rewritten or new proof. Nothing is signed or audited in this lane. One new test (PROOF-42) starts the run with its own PYTHONPATH, which points at a temporary folder holding a sitecustomize.py that makes the host report an empty name. That setting reaches only that one run and the processes it starts. The fake `claude` from dev/conftest.py stays first on PATH for it.

### `reports`

The branch is split/reports, two commits on top of 57ebd6168. It touches only specs/run/reports.md and dev/test_reports.py.

- Proof ids: the new ones are PROOF-40 to PROOF-93. The spec's history never used an id above 39.
- Test helpers: the test file imports only from the frozen dev/reports_project.py and from dev/suites.py. Its new helpers (_spec, _login_run, _captured, _listed, _fix_and_why, and the module fixtures untied_run, five_outcomes and exit_run) live in the test file itself.
- Format file: references/formats/marker_format.md, which this lane does not own, lists 7 C# test attributes. The product reads 9, adding `[SkippableFact]` and `[SkippableTheory]`, and RULE-6 now names all 9. The format file's C# row should get the two Skippable attributes. That is an optional addition, so it bumps Format-Version.
- Near-miss proofs: they now go through `markers.py --near-misses` in a temporary project instead of a hand-built feature list. PROOF-32 uses `# purlin:login PROOF-1`, because a `//` comment in a Python file is not read.
- Tool names: the proofs keep Vitest, Jest, `dotnet test --logger trx` and `go test -json`, because the product reads their output. That is the exception decision 71 allows. The flag in section 5 of dev/plans/proofs-rewritten.md about naming tools needs no further change.

### `ai_audit`

- **Proof ids.** New proofs start at PROOF-48. The feature `ai_audit` went up to PROOF-47 at commit ee69699c4, the rename from brief, so no id is reused. PROOF-28 stays deleted. The proofs are now grouped by rule in rule order, and the file keeps one line per proof. The 69 ids and the 69 markers match one to one, with no id doubled.
- **Clash with decision 93.** This decision was added to main after this branch was cut. PROOF-63 (RULE-8) claims the printed reading shows `Test strength: n/a   minimum 70` when no strength was measured, because that is what the product prints today. When the product change for decision 93 lands, that test fails and PROOF-63 has to be rewritten to what the reading then shows. PROOF-11 quotes the prompt line `Test strength: 90 percent (minimum 70)`, which is the measured case; it changes only if decision 93 rewords that line too.
- **Tests that depend on other code.** They use the frozen helpers sign_project.Project and fake_claude, unchanged. PROOF-49 writes a second spec with `> Requires: login`. PROOF-53 and PROOF-54 depend on the stored audit entry being dropped when a rule's proof or test changes. That check is in scripts/mcp/purlin/evidence.py (`audit_entry`), which another lane may own, so a change there shows up in these tests.
- **Checks I broke on purpose.** 44 deliberate breaks, each restored with `git checkout -- <file>`. `git status scripts` was clean after each set. The real `claude` could not be reached during any of them.

### `host`

- There are three commits on split/host, cut from 57ebd6168. main has 9 newer commits (decisions 86 to 90 and dashboard work), and none of them touches a host file, so the branch should rebase cleanly.
- Proof ids: the new ones are 54 to 105. The highest id this spec ever held was 53, checked through the file's history with --follow; the PROOF-61 that shows up in that history belongs to run_script.
- Proofs are now grouped by rule, in the order the rules appear in the Rules section.
- Five tests were deleted outright because another test now shows the same case through the command itself:
  - the one that asked whether the Azure DevOps build variables are read as Azure DevOps. PROOF-8 now asserts that every request goes to Azure DevOps.
  - the one that read the git host straight from origin. PROOF-24 runs with a GitHub origin and PROOF-37 with an Azure DevOps origin.
  - the parser cases for a github.com URL and an empty string. The command never hands those to the Azure DevOps parser.
  - the check that the four intervals and limits are 3, 60, 15 and 5400. PROOF-70, 80 and 81 now run the real 60-second and 90-minute limits on a stand-in clock.
  - the direct call to the fixture's module. PROOF-86 runs the fixture's own test file.
- Tests changed:
  - Every exact line a proof quotes is now asserted as the whole line: the no-variables line, the workspace line, the detached-head and uncommitted-changes lines, the no-gh line, the no-run line, the tag-run line, the pause line and the workflow reason.
  - The fixtures for the GitHub and Azure DevOps variables now also clear GITHUB_REF. Before this, a run of this suite inside a tag job would have turned the run-branch test red.
  - The run-branch test (PROOF-64) pushes to a bare repository next to the project, so it cannot reach a git host.
- I broke each checked behaviour on purpose 22 times, and every break made its test fail. The source was restored with `git checkout -- <file>` each time, and a check afterwards confirmed scripts/ was clean. The breaks, by source file:
  - scripts/run/host.py:
    - B1: reworded the no-variables line; PROOF-7 and 60 failed.
    - B2: made detect_host answer github for the Azure DevOps variables; PROOF-8 failed on the sha.
    - B3: sent every Azure DevOps change twice; PROOF-8 and 62 failed with `assert 2 == 1`.
    - B4: reworded the workspace line; PROOF-32 and 97 failed.
    - B19: made deleted_files use the os.path.join spelling; PROOF-95 failed with `assert [] == ['.purlin/evi...retired.json']`.
    - B20: reworded the tag line; PROOF-103 failed.
    - B22: reworded the pause line; PROOF-22 failed.
  - scripts/run/ci.py:
    - B5: made "no workspace variable" answer "not the workspace"; PROOF-30 failed.
    - B6: made every project count as the workspace; PROOF-32 and 97 failed.
  - scripts/run/remote.py:
    - B7 and B8: reworded the detached-head and uncommitted-changes lines; PROOF-12 and 63 failed.
    - B9: used sha[:8]; PROOF-64 failed with `Pushing feature-x as run/feature-x-992917eb.`.
    - B10: looked the run up twice; PROOF-66 failed.
    - B11: skipped the pull at the gate `passed`; PROOF-67 failed.
    - B12 and B13: FIND_SECONDS 30 and FIND_EVERY 2; PROOF-70 and 80 failed.
    - B14: poll limit one interval short; PROOF-81 failed.
    - B15: reworded the no-gh line; PROOF-71 failed.
    - B16: kept the user part of the host (netloc); PROOF-73 failed.
    - B17: stopped decoding percent-encoded names; PROOF-74 failed.
    - B18: made the ssh form `v4`; PROOF-36 failed.
  - scripts/run/workflow.py:
    - B21: reworded FOREIGN_OS_REASON; PROOF-42 failed.
- A trap with the breaks, for anyone repeating them: a break that keeps the file the same size and is restored within the same second leaves stale bytecode behind, so the next run uses the broken code. My first pass hit this. I reran all 22 breaks with PYTHONDONTWRITEBYTECODE=1 and scripts/run/__pycache__ cleared before each break, and the results above come from that rerun.

### `drift`

- **Merge:** the branch is 2 commits on top of 57ebd6168. It touches only specs/mcp/drift.md and dev/test_drift.py, so it should rebase or fast-forward cleanly onto the current main.
- **New proof ids:** PROOF-35 to PROOF-50 are new. The spec's history never used an id above 34 on a proof line, so none is reused. The file keeps its order by rule: each new proof sits right after the proof it was split from.
- **Marker ties:** every marker in dev/test_drift.py names an id the spec has, and every proof has exactly one marker. The run printed 0 not tied.
- **Other files:** there are no new helper modules, and none of the frozen dev/ helpers were touched.
- **Rule quotes elsewhere:** docs, skills and references/drift_criteria.md were not checked against the reworded RULE-5, 6, 8, 13 and 15. Those files are not mine. The rewording only narrows each rule to what drift already prints, so no quote should be stale; an integrator may grep for `covering login, export` in case an example somewhere copied the old order.

### `evidence`

The branch is two commits on 57ebd6168, and `main` has moved 10 commits ahead of it. None of those commits touches the three files, so a rebase should apply cleanly. After this branch the spec's proof ids run PROOF-1 to PROOF-64 with none missing; the next free id is PROOF-65. No other file in the repository carries an `evidence` marker. Three rules were reworded: RULE-3, RULE-6 and RULE-7. Another lane that quotes those rules would need the new wording. RULE-6 now quotes the reason `no > Scope: line`, the same words that states RULE-62 already uses.

### `package`

- Two commits, touching only specs/export/package.md and dev/test_export.py. No generated file is staged.
- Spec maxima are RULE-10 and PROOF-35. PROOF ids 30 to 35 are new; the highest id ever used before was 29, checked across the file's whole history.
- There are 35 markers, one per test, and every marker names a proof in the spec.
- The RULE-10 proofs (PROOF-10, 34, 35) now sit at the end of the proof list so it runs in rule order. Their tests moved to a new group, TestCommitting, at the end of the file.
- The tests use only the frozen helper dev/sign_project.py and add no helper outside the test file.
- The branch is behind main, but no file it changes was changed on main, so it should rebase or merge cleanly.

### `mutation`

- The branch is one commit on top of 57ebd6168 and touches two files. Main has moved ahead by about 10 commits (decisions 86 to 93, dashboard work), none of which touch these two files, so it rebases without conflict.
- How the tests run now: every engine run starts a stand-in `stryker`, `dotnet` or `mutmut` program. Each stand-in is a small Python script that records how it was started and writes the captured report it is given. An autouse fixture sets PATH to a temp folder plus `/usr/bin` and `/bin`, and no real engine or `claude` lives in any of them. The one whole-run test adds only the session's fake `claude`, taken from the `no_real_model` fixture in dev/conftest.py.
- This machine does have a real `mutmut` in .venv/bin and a real `dotnet` in /opt/homebrew/bin. The PATH fixture keeps both out of reach.
- The stand-ins use a `#!<python>` first line, so these tests need a system that honours that line. The old test already used a `#!/bin/sh` stand-in, so this is not a new requirement.
- The file now takes about 16 s, up from about 1 s. Real timeouts account for 1+1+3+3 s, and the whole audit run for about 2.5 s.
- 47 deliberate breaks of the engines' source were run, one at a time, each restored with `git checkout -- <file>`, and the scripts folder ended clean. Every break made its expected tests fail. Examples, with what the run printed:
  - Dropping the line in the run script that hands `--arm-timeout` to the engines made the whole-run test fail on time.
  - Making a timed-out engine return exit 0 failed all five timeout tests (`assert 67 is None`).
  - Checking the Stryker on the PATH before the project's own gave `assert 0 == 1`.
  - Dropping `caught by type check` from mutmut's caught statuses gave `{'score': 50,...} == {'score': 60,...}`.
  - Crediting a timed-out break only to a test named as its catcher gave `assert (0, 1) == (1, 0)`.
  - Treating any test file as the same file gave `assert 1 == 0`.
  - Limiting the Stryker.NET report search to one folder down gave `assert None == 60`.
  - Counting every results line as a break printed `3 breaks read`.
  - Letting a break no scope entry covers go to the first entry gave `{'score': 0,...} == {'score': None,...}`.
  - Removing the rule sort gave `['RULE-10', ..., 'RULE-1'] == ['RULE-1', ..., 'RULE-10']`.
  - Rounding a half to even failed the half-rounds-up test.
  My break script is breaks.py in my scratch folder.
- The engine logs print `1 files broken` and `1 breaks read`. I kept those strings out of every proof. The grammar belongs to the product, not these files.
- Rewording RULE-17 and RULE-21 dropped the claims about which scope entry a break "belongs to" (the deepest match wins; a glob loses to a named file or folder). No caller can see which entry a break belongs to, because a feature only reports the sum over its entries. The code for that precedence (the 0.5 weight for a glob) is now tied to no rule. A later simplification of mutmut.py could remove it.

### `skill_sign`

- **Branch state:** split/skill_sign is 2 commits on top of 57ebd6168. Main has moved on to 44b080c34. None of main's new commits touch skills/sign/SKILL.md, references/purlin_commands.md, dev/skill_checks.py or my two files, so a rebase has no conflicts.
- **New proof ids:** PROOF-23 to PROOF-43. PROOF-14 stays unused because it was deleted earlier in the spec's history. The highest id ever used before this work was PROOF-22.
- **Proof counts:** the spec goes from 21 proofs to 42, and the test file from 23 tests to 42, one test per proof.
- **Changed wording:**
  - PROOF-10 now names `left` beside `to_test_by_hand` and `to_sign`, and the check's message changed with it.
  - PROOF-12 now expects the full message for the missing row.
- **Frozen helpers:** dev/skill_checks.py is unchanged. The frontmatter and closing-section refusal cases used to run in shared helpers. Each is now rebuilt as its own test in my file, using the shared `refusals`, `on_copy` and `replace`. The shared `frontmatter_problems` is split in my file by which file each problem names.

### `upstream`

- The spec now goes up to PROOF-37 and RULE-23 (no rule was added or removed). The new proof ids are PROOF-25 to PROOF-37. Before this, the highest id ever used in the file's history was 24.
- Test functions: 27 before (26 in test_upstream.py plus 1 in test_upstream_notes.py), 31 after (30 plus 1).
- dev/test_upstream_notes.py was not changed. It still imports _add, _advance, _copy_text, upstream and workspace from test_upstream.py, and all of those names are still there.
- Three tests were removed because each checked an internal function rather than what a caller sees: the internal free-text check, the internal exit-code helper, and a combined child-process test. Separate tests for each case now cover what they held:
  - the free-text check: PROOF-7 and PROOF-29;
  - the exit codes: PROOF-9, PROOF-30, PROOF-31 and PROOF-32, run through the command line;
  - the combined test: PROOF-10, PROOF-33 and PROOF-34.
- PROOF-30 runs the script as a separate process, so the exit code tested is the one the shell sees.
- The rebase onto the new main should be a plain fast-forward of the two files.

### `skill_test`

- Branch split/skill_test holds 2 commits on 57ebd6168 and changes only specs/skills/skill_test.md and dev/test_skill_test.py.
- Proof ids 19 to 44 are new. PROOF-7 is still vacant: it was deleted earlier in the spec's history and was not reused.
- The spec's two rewordings (RULE-3 and RULE-7) change those rules' text hashes, so the committed evidence for skill_test will read out of date until the next run is committed.
- The frozen helper dev/skill_checks.py was not edited. Every check this spec needs beyond it lives in dev/test_skill_test.py. That includes the per-case frontmatter tests, which replace this file's use of the shared helper that ran six broken copies in one test.
- Nothing was audited, signed, pushed or tagged.

### `specs`

The branch is split/specs with 2 commits on 57ebd6168 and changes only its two owned files. It merges fast-forward onto that base. main is ahead with the decision 86 to 93 commits, so it will need a rebase, and none of those commits touches these files.

What changed:
- The 16 proofs are now 39. Every proof is one case and stays in rule order; PROOF-17 and PROOF-18 moved up beside RULE-3.
- New ids are PROOF-19 to PROOF-41. The highest id ever used in this spec's history was PROOF-18, so no id is reused.
- Every proof has exactly one test, and each test carries one marker.
- The tag, old-field, source and anchor cases now write a spec and read it through the scan. Before, they called the line reader alone.
- The warning cases (PROOF-9, 27, 28) compare the status report's whole warnings list against the exact line the product prints.

Tests in `dev/test_specs_reader.py`: 28 before, 52 after. The unmarked TestFrameworks (5 tests) and TestGate (8 tests) classes are untouched. They carry no `specs` marker and look like they belong to other features' lanes.

One assertion value was dropped as a repeat: the `> Source:` value `--upload-pack=/bin/echo`. It is the same case as PROOF-29 (one word that is not a git URL comes back whole). The option-shaped value `--upload-pack=touch x specs/a.md` is kept as PROOF-31.

Copy seen and not changed, because no rule of mine covers it: with one carrying file, the warning reads `1 spec files carry tags this release does not read (...)`, which has the plural wrong.

### `skill_audit`

- **New proof ids start at PROOF-17.** Main's own history of specs/skills/skill_audit.md, since it was written anew in a18768ceb, uses PROOF-1 to PROOF-16. An older phase 0 spec lived at the same path until 7bd823815 deleted it, and its ids ran up to PROOF-106. Nothing recorded under those old ids survives, so I numbered from 17. If the rule is read to cover the older file too, the ids need moving to 107 and up; see the question below.
- **Proofs are grouped by rule.** Within each rule, the old id comes first and the new ids follow. So PROOF-8, 9 and 10 now sit under RULE-3, and PROOF-11 to 16 sit among the RULE-6 proofs.
- **dev/skill_checks.py is unchanged.** The test file imports `field`, `frontmatter` and `COMMAND_REF` from it and imports the module itself for the ceiling copy. It no longer calls `frontmatter_refusals`: every broken frontmatter copy is its own test here, and there is a new `>-` block case.
- **The skill is exactly at its ceiling.** skills/audit/SKILL.md is 105 lines, the RULE-4 limit, so any lane that adds a line to it fails PROOF-4 and must cut one.
- **Statements with no rule.** Several things the skill says are covered by no rule of this spec. Decision 64's default is a rule, a proof and a test for each, which is outside this lane's proof work:
  - an audit notes a proof over 60 words, or holding two cases, and does not find the rule weak for it (decision 75);
  - the announcement line `AI audit: <n> rules to read, <k> at a time.`;
  - the exit code list;
  - the minimums 70 and 80.

### `skill_init`

- **Proof numbering.** New proof ids start at 16 (PROOF-16 to PROOF-43). This file's history shows ids up to PROOF-122, but all of them are from a different spec that commit 7b81a9b88 replaced wholesale ("one spec per skill"). That rewrite already restarted at PROOF-1, and the next rewrite (2486ead0e) went on from 8. If the owner wants no number that has ever appeared in this file used again, the 28 new ids would have to move to 123-150. It is asked below.
- **Setup is now run for real in 5 tests.** They cover PROOF-24 and PROOF-32 to 35, and PROOF-38 also reads the settings file a run writes. Each run is the setup script started by the Python running the tests, in a new git project in a temporary folder that is deleted afterwards. The script runs git and nothing else: no `claude`, no network. Runs with the same answers are cached, so there are 2 setup runs and 1 usage run per test process, about 0.4 s in total.
- **What I broke on purpose.** Each break was in the worktree, and each file was restored with `git checkout --`.
  - Removed the `--add` argument from scaffold.py: PROOF-24's test failed, and the setup-run tests failed with a traceback.
  - Reworded the mutation question in scaffold.py: PROOF-32 failed, and only it.
  - Removed the line that stops the mutation question at `passed`: PROOF-33 failed, and only it.
  - Swapped the first two gate choices: PROOF-34 failed with `['strong', 'passed', 'signed'] == ['passed', 'strong', 'signed']`.
  - Changed the mutation question's default from `n` to `y`: PROOF-35 failed.
  - Added a `colour` key to templates/config.json: PROOF-38 failed.
  The checks that only read the skill's text are each shown to fail by their own refusal proof, which runs the check on a broken copy of the skill.
- **The template comparison is gone.** The old PROOF-6 compared the skill's settings block with `templates/config.json`. That comparison is replaced by PROOF-38, which compares the block with the settings file a real setup writes.
- **The `--help` check is looser than the old list.** PROOF-9 now checks the skill's flags against the script's own `--help` output, not a hard-coded list. So if the skill named `--plugin-root`, which the script takes, it would not be refused.
- **Nothing is left for `dev/skill_checks.py`.** No new helper went into it; every helper is in dev/test_skill_init.py.

### `security_no_dangerous_patterns`

Branch split/security_no_dangerous_patterns has 2 commits on top of 57ebd6168, touching only the spec and dev/test_security.py.

Proof ids:
- PROOF-1 to PROOF-13 keep their ids.
- PROOF-14 to PROOF-48 are new. The spec's history never went above PROOF-13, so no id is reused.
- The proof list is now ordered by rule.

Changes a reviewer should know about:
- The three hostile anchor sources in the test and in PROOF-6, 47 and 48 now end in `.git`: `--upload-pack=/bin/echo /tmp/policy.git`, `ext::sh -c "touch /tmp/purlin-pwned" /tmp/policy.git`, `fd::7/policy.git`. Without that ending, a source is never handed to git whether or not it is refused, so the old claim that no command carries the value could not fail.
- The old test also carried all three sources in one project. Each now has a project of its own. The test checks every command started, not just git ones, and looks for the value inside any argument, not only as a whole argument.

Nothing in this lane changes product code or a format reference.

### `skill_export`

Two commits on split/skill_export, cut from 57ebd6168. main has moved on since then, so bring them in by rebase or cherry-pick. They touch only specs/skills/skill_export.md and dev/test_skill_export.py.

Proof ids now run to 33. New ids are 14 to 33, and no id was reused: the history's highest was 13. The test file still imports only from dev/skill_checks.py, which was not edited. It now also imports CEILINGS, COMMAND_REF, ceiling_problems, field, frontmatter, on_copy and table_rows from there, which all exist on main at the cut. It no longer uses frontmatter_refusals, undirected_outcome_problems or skill_ceiling_problems.

The positive tests fail when the skill is broken. Each break was made to skills/export/SKILL.md or references/purlin_commands.md in the worktree and restored with git checkout. The tests only read files and start no program.
- Last heading changed to "Step 4: when you are done": test_the_last_heading_names_the_next_step failed.
- `not finished` renamed `unfinished` in the state table: test_the_table_of_states_names_the_two_states failed.
- "`left` holds the lines" changed to "`left` has the lines": test_the_not_finished_row_says_left_holds_left_to_do failed.
- A sixth closing row with no arrow appended: test_every_outcome_row_gives_a_directive failed.
- "The package is evidence for review" changed to "It is evidence for review": test_it_calls_the_package_evidence_for_review failed.
- The --commit usage line changed to "purlin:export --commit: the same": test_each_form_of_the_command_has_a_line failed.
- `name: exported`: test_the_frontmatter_names_the_skill_on_one_line failed.
- 10 lines appended: test_it_stays_under_its_ceiling failed.
- The no-claim sentence reworded: test_it_makes_no_claim_of_compliance failed.
- The purpose cell of the command reference's purlin:export row emptied: test_the_command_reference_has_a_row_for_export failed.

One break was caught by a different proof. Replacing only the first python3 command line left PROOF-21 passing, because the --check line still runs the script. PROOF-24 replaces both lines and fails, as its proof says.

### `schema_spec_format`

Branch split/schema_spec_format has 2 commits on top of 57ebd6168. main has since gained 5 commits touching other files, so the branch needs a rebase before a fast-forward. The two sides share no files.

The proof ids now run from PROOF-1 to PROOF-44. In the spec's history the highest id ever used was PROOF-12, so no id is reused. Each rule's proofs stay together, with new ids after the first.

Removed on purpose:
(1) Old PROOF-6 claimed "beside an anchor whose scope is `scripts/`, the status report names both the spec and the anchor". No rule claims that, and it showed nothing about RULE-6, so the claim and its assertion are gone.
(2) The old PROOF-9 test read this repository's own PROOF-9 text and checked that it ended with "identical tuples". That self-reference is replaced by a spec written in a temporary project (PROOF-35), so rewording a proof can no longer break a test.

Strengthened:
- PROOF-2 now asserts the whole warning line, including "; a rule is `- RULE-N: <text>`.".
- PROOF-11 now checks that the text of both notes is absent from everything the parser returns. Before, it checked one note against string values only.

The new PROOF-19 test starts `purlin_run.py --test --all` in a temporary git project. At the gate `passed` it starts only pytest on that project's one test file, so it reaches no model and no network.

The test file imports dev/suites.py, an existing helper that is not on the frozen list, and does not edit it.

Helper scripts are in /private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/8c7da91f-67d4-4e89-8416-d6695b075a74/scratchpad/phase2/schema_spec_format/: count_words.py and breaks.py.

### `purlin_agent`

Branch split/purlin_agent, 2 commits on top of 57ebd6168. It touches only specs/instructions/purlin_agent.md and dev/test_purlin_agent.py.

- **Proof ids.** PROOF-1 to PROOF-12 keep their ids. The new ids are PROOF-16 to PROOF-46. PROOF-13 to PROOF-15 are left unused because this spec's history used them before.
- **Proof order.** Proofs are listed by rule: 1, 16-20, 2, 21-24, 3, 25-32, 4, 33-36, 5, 8, 9, 10, 37, 6, 38, 39, 7, 40-44, 11, 12, 45, 46.
- **Tests.** There is one test per proof, grouped by rule. The frozen helper dev/skill_checks.py is only imported (it now also imports `on_copy`), never edited. There is one new local helper, `refused()`, and one new edit, `lines_long()`.
- **Nothing outside these files.** The agent definition itself (agents/purlin.md) is unchanged and still exactly 135 lines, at its ceiling.
- **Merge.** main has moved 10 commits past the cut point; neither file changed there, so a rebase should apply cleanly.

### `skill_build`

- The branch is 2 commits on 57ebd6168. Main has moved on by 10 commits, none of which touches skills/build/SKILL.md, references/commit_conventions.md, references/purlin_commands.md or dev/skill_checks.py. So it rebases cleanly, but a strict fast-forward of main to this branch is not possible without a rebase.
- dev/test_skill_build.py no longer runs dev/test_e2e_build_changeset.sh. That script still runs in the full sweep as its own suite (dev/run_tests.sh line 45), but no proof is tied to it any more. It commits hand-written messages to a scratch repository and checks them against a checker defined inside the script, so it reads nothing Purlin wrote. RULE-5 is now proved from the build skill's section on committing, and from the commit conventions' table and example. Whether to delete the script is question 2 below.
- The test file no longer uses the shared helper frontmatter_refusals; it builds each of the six broken frontmatters as a test of its own. The helper is unchanged, and other skill files may still use it.
- Proof ids 13 to 23 were used earlier in this spec's history, so the new ids start at PROOF-24 and run to PROOF-45.
- The six refusal checks behind PROOF-32, 33, 38, 39 and 45 were shown to discriminate. Each check was disabled in turn, and each test failed.

### `skill_spec_from_code`

1. New proof ids start at PROOF-125. The spec's own history already used ids up to PROOF-124, back when this file described an older skill (commit e0412a572), so no id is reused. The spec is now ordered by rule, not by id.
2. RULE-3 had the same wording as the RULE-3 of the other skill specs ("names the next step and computes it from the state the skill found"). This lane reworded it to a sentence the skill actually carries, `name the next step from the state`. Other skill lanes may reword theirs differently, so the specs may not match after the merge.
3. A trap for every lane that breaks a Python helper on purpose: if the break keeps the file size the same (for example 130 changed to 131) and `git checkout` restores the file within the same second, Python keeps using the stale compiled copy under dev/__pycache__. The next test run then sees the broken value. I hit this with the frozen helper's ceiling and cleared it by deleting dev/__pycache__/skill_checks.*.pyc. The helper file itself is back exactly as it was on main.
4. Nothing in these tests starts a process. They read the skill and the command reference, and every broken copy is made in memory.

### `config_engine`

- The branch is one commit on top of 57ebd6168, and main has moved 10 commits past that point. Rebase or merge before a fast-forward; neither owned file changed on main, so no conflict is expected.
- Proof ids now run 1-5, 7-10, 12 and 15-31. 16 to 31 are new, and none of them was used before in this spec's history, which only ever went up to PROOF-15.
- The markers are one per test, except PROOF-5, which two tests carry: one starts the command line as its own process and one runs it in-process.
- The tests now use pytest's tmp_path and monkeypatch fixtures instead of setup and teardown methods. Tests that check the working-directory fallback now change into a known temporary folder instead of depending on where pytest was started.
- Nothing under scripts/ was changed.

### `server`

The branch touches only its two owned files. It is 2 commits ahead of its branch point and 10 commits behind main, so it needs a rebase or merge before a fast-forward; neither owned file changed on main, so no conflict is expected. New proof ids run from PROOF-125 to PROOF-138. The spec's history had used ids up to PROOF-124 (commit 5941569a0), so no earlier id is reused. The rewording of RULE-6, RULE-7 and RULE-8 changes their rule hashes, so their evidence reads out of date until the next run. Two tests start real processes, and both are safe: one runs the server as its own process, and the other runs the plugin manifest's `sh scripts/purlin_python.sh .../server.py` with PURLIN_PYTHON set to the test's own interpreter. Neither reaches `claude` or the network. In this fixture, sync_status prints `→ Run: purlin:init --update`, apparently because the frozen helper's settings file lacks a key the product now expects. That belongs to the helper's owner, not this lane.

### `skill_status`

- The branch is cut at 57ebd6168 (decision 85). Main has moved on to 25d660433, but none of the files these proofs read or run changed on main since: the status skill, the command reference, status.py, summary.py, report_data.py and payload.py. The merge is clean.
- The Scope line of specs/skills/skill_status.md now names scripts/mcp/purlin/status.py, scripts/mcp/purlin/summary.py and scripts/mcp/purlin/report_data.py beside skills/status/SKILL.md, because PROOF-21 and PROOF-24 run that code. After this lands, a change to any of those files ends the signatures of this spec's rules. See the owner question on scope.
- PROOF-21 builds its throwaway project with the frozen dev/mcp_project.py helpers (Project, _commit_tests, _entry) and calls the real status tool in the same process. It starts only git, never claude and never a network service.
- The 13 deliberate breaks were made one at a time in my worktree, and each file was restored with `git checkout -- <file>`:
  - status.py prints one fewer Left to do line: PROOF-21 fails.
  - report_data.py writes no lines of work: PROOF-21 fails.
  - report_data.py writes a recounted summary: PROOF-21 fails.
  - summary.py's audit kind names purlin:test: PROOF-21, 24 and 25 fail.
  - The skill's audit row runs purlin:test: PROOF-10, 24 and 25 fail.
  - The skill's table loses `to strengthen`: PROOF-24 and 26 fail.
  - The skill's description is changed: PROOF-1 fails.
  - The reference's purpose cell is changed: PROOF-12 fails.
  - The reference loses `[name]`: PROOF-12, 19, 20, 29 and 30 fail.
  - The skill's usage line is changed: PROOF-5 fails.
  - The last heading is renamed: PROOF-3 and 23 fail.
  - The skill grows to 101 lines: PROOF-4 fails.
  - The 'to test' row loses its arrow: PROOF-23 and 24 fail.
- Four of those breaks were transient edits to the frozen dev/skill_checks.py, each restored at once and none committed:
  - The ceiling set to 101: PROOF-28 fails.
  - The purpose cell no longer required: PROOF-20 fails.
  - An empty description accepted: PROOF-14 fails.
  - An indented continuation accepted: PROOF-18 fails.
- Proof ids 12 to 34 are new. The highest id in the spec's history was 11; the PROOF-19 and PROOF-21 that turn up in `git log -p --follow` are in commit messages about report_data, not in this spec.

### `skill_spec`

The branch split/skill_spec is 2 commits on 57ebd6168. Main is now at 44b080c34; its newer commits touch none of my files, so a rebase has nothing to merge. I read decisions 86 to 93 on main and none of them touches the spec skill.

Proof ids: the highest id this spec ever used was PROOF-13 (it was retired in its history), so new ids start at 14. PROOF-1 to 9 keep their ids. The new ones are 14 to 41, listed in rule order.

Three changes a reviewer should know about:
- The scope line of skill_spec now also names references/purlin_commands.md. RULE-1 reads that file, so a change there should put this feature out of date.
- My check of the closing section now asks that the skill's last heading reads exactly `When you are done`. The shared check accepted any heading that names the next step. This is stricter, not weaker.
- The test file uses only existing names from dev/skill_checks.py, which stays unchanged.

How I checked the new assertions: I broke each source file on purpose, reran the tests, and restored the file with git checkout each time. The tests only read Markdown files; nothing starts `claude` or any service. Each break turned the test named after it red:
- In the skill, "in either copy of the spec:" changed to "in the copy on `origin/main`:" → PROOF-2's test failed.
- The skill's `## When you are done` heading renamed `## Next step` → PROOF-3's test failed.
- "say what moved before the offer" changed to "after the offer" → PROOF-3's and PROOF-27's tests failed.
- "and no tag is written" deleted → PROOF-30's and PROOF-34's tests failed.
- "at least one failure case" moved out of the drafting sentence → PROOF-36's test failed.
- "one starting situation and one action" deleted from the skill → PROOF-7's test failed.
- In the guide, "one starting situation, one action" deleted → PROOF-40's test failed.
- In the guide, "A refusal or a boundary is a case of its own..." deleted → PROOF-40's and PROOF-41's tests failed.
- The purpose cell of the `purlin:spec <name>` row in the command reference emptied → PROOF-14's test failed.
- The skill padded to 211 lines → PROOF-4's, 28's and 29's tests failed.

### `purlin_version`

What changed in this branch:
- **Proof numbering.** The spec now has 34 proofs, split out of the original 8. New ids start at PROOF-11, because PROOF-9 and PROOF-10 were used by earlier versions of this spec (visible at commits 6e6c4227d and fd068ff03). Each rule's proofs are listed together, under that rule.
- **Tests.** Every proof has exactly one test with a marker directly above it, and the test names describe the case in plain words. No marker names an id that the spec does not have.
- **Scope line.** The spec's `> Scope:` line now also lists `scripts/init/scaffold.py`. The new PROOF-21 runs setup (`scaffold.py --project-root <tmp> --yes --gate passed` in a fresh git repository) and reads the version it writes. Setup starts only `git`; I checked this before breaking anything.
- **Scope may be too narrow.** The Scope line does not name every module of the package, even though RULE-4 covers all of them. So a version number added to a module that is not listed would not end this feature's signatures. I left it unchanged. Adding `scripts/mcp/purlin/*.py` is the owner's call, because then any change to the package would end this feature's signatures.
- **Rebase.** The branch is based on 57ebd6168, and main is now at 44b080c34. The newer commits on main touch none of my files, so this branch should rebase cleanly.

Deliberate breaks. Each was undone with `git checkout -- <file>`:
- **Setup writes the version as `'0.0.0'` instead of reading the VERSION file:** the PROOF-21 test failed with `AssertionError: {'version': '0.0.0', 'gate': 'passed', ...}`.
- **The bump script's `--check` matching line prints `match %s` instead of `ok    %s`:** the PROOF-28, PROOF-29 and PROOF-33 tests failed.
- **The line for a missing key is reworded to `FAIL  missing`:** the PROOF-30 test failed.
- **A missing key no longer fails `--check`:** the PROOF-30 test failed.
- **The package's fallback for a missing VERSION file returns `'unknown'` instead of `'0.0.0'`:** the PROOF-17 test failed.
- **The server's reported version is a fixed `"0.10.0"`:** the PROOF-2, 16, 17, 4, 22 and 23 tests failed.
- **This repository's `.purlin/config.json` is set to 0.9.2:** the PROOF-6 test failed.
- **A `version` row is added to references/glossary.md:** the PROOF-34 and PROOF-35 tests failed.

Breaks to the test's own checks, made in the working copy of the test file and undone the same way:
- **Whole-line comments are no longer skipped:** PROOF-23 failed.
- **A missing key is read as a match:** PROOF-19, 24 and 26 failed.
- **The stale-number comparison is removed:** PROOF-20, 25 and 27 failed.
- **skills/ is no longer scanned:** PROOF-35 failed.
- **The owner row's check for the VERSION file, or for a restated number, is removed:** PROOF-36 failed each time.
- **The version pattern is loosened to two numbers with no end anchor:** PROOF-11, 13 and 15 failed.

Two slips outside the worktree:
- I briefly wrote a copy of the test file into /tmp/x/, a folder that already existed. I removed that one file and nothing else.
- The first attempt at the break of the missing-key line did not apply, and the tests passed. I redid it and recorded the result above.

### `skill_anchor`

The branch has 2 commits on 57ebd6168 and touches only specs/skills/skill_anchor.md and dev/test_skill_anchor.py. Main has moved 10 commits ahead, but none of them touches these two files, so a rebase should apply cleanly. Proof ids now run 1 to 32, and the highest id ever used is 32.

The test file now has one test per proof, grouped in five classes by rule. It imports on_copy, sections, field, frontmatter and COMMAND_REF from dev/skill_checks.py, and the frozen helpers are unchanged.

It no longer calls frontmatter_refusals or next_step_refusals, which bundle several cases in one call. It builds each broken copy itself, so each case has its own test and marker.

During the deliberate breaks I edited dev/skill_checks.py, skills/anchor/SKILL.md and references/purlin_commands.md in this worktree only, and restored each with git checkout -- <file>. None of those edits was committed. Nothing in these tests starts claude, git remotes or any service; every test reads text files.

### `skill_drift`

The branch is split/skill_drift with one commit, 9aed78147, on top of 57ebd6168. It changes only specs/skills/skill_drift.md and dev/test_skill_drift.py. The new proof ids are PROOF-9 to PROOF-35; PROOF-5 to PROOF-8 appear in the spec's history, so they were skipped. The test file imports only from the frozen dev/skill_checks.py and edits none of it. Its own helpers are in the test file. Two new checks read references/drift_criteria.md:
- The restatement check reads the eng/qa `From` column, the `Where the range starts` column, the anchor `Condition` column and every backticked `git ...` command.
- The closing-table check reads the Key column of the pm, eng and qa tables.
If another lane adds a key to those criteria tables, PROOF-27's test fails with "names the line <key>, which this check maps to no row" until the skill gets a row for it and OUTCOME_ROWS in the test maps it. This is intended.

### `claude-md`

One commit, CLAUDE.md only, on split/claude-md at fda59eefb, cut from 57ebd6168. main has since moved to 44b080c34 (decisions 86 to 93), and none of those commits touches CLAUDE.md, so a rebase or merge has no conflict. Decisions 86 to 93 contradict nothing now in CLAUDE.md: decision 89 keeps the rule's page, which matches the two screenshots.


## The rules that must hold on Windows

**Summary**

1. I sorted all 563 rules in the 34 specs. 90 rules in 17 specs must hold on Windows, because what they specify changes with the operating system: how files are written (line endings, atomic replace, temp folders, links, permissions), how paths are spelled, how bash, git, gh, az, claude, stryker, sqlite3 and ssh-keygen are found and started, timeouts, environment variables and console encoding. The other 473 rules read the same on every system, including every skill, dashboard, wording and anchor-format rule.
2. If they are marked `@env(windows)`, those 90 rules (179 proofs) read `to test on Windows` until `purlin:test --remote` brings back a green Windows run. They wait again after any change to one of those 17 specs, their code or their tests, and those specs cover most of `scripts/`.
3. Six tied tests stop a Windows run being green today. The two end-to-end init walks print a line and exit 0 on Windows, which counts as passed without walking. Four more skip there (the `gh` on PATH test, the unreadable-file test, the symlink test, the sqlite3 test), and a skipped tied test makes a run exit 1.
4. Reading the code (nothing was run) turned up four places likely wrong on Windows. Their tests would still pass there, because the fakes are files with no `.exe` or `.cmd` ending:
   - `gh` is looked for with no `.exe`, so `purlin:test --remote` and `purlin:init` would say gh is not installed.
   - Stryker's project copy is looked for with no `.cmd`.
   - An anchor added with a backslash `--path` gets the wrong name.
   - Python and git look up `~/.ssh` from different variables on Windows.
5. I need three decisions from you: accept, trim or extend the list (the ten I am least sure of are below); tag an existing proof per rule or add one Windows proof per rule; and what to do about the six tests in point 3.

**Count per spec** (must hold on Windows / rules in the spec)

| Spec | Windows | Rules |
|---|---|---|
| _anchors/schema_spec_format | 0 | 12 |
| _anchors/security_no_dangerous_patterns | 0 | 6 |
| anchor/upstream | 7 | 17 |
| dashboard/purlin_report | 0 | 47 |
| export/package | 3 | 10 |
| init/scaffold | 11 | 35 |
| init/update | 9 | 28 |
| instructions/purlin_agent | 0 | 8 |
| instructions/purlin_version | 1 | 8 |
| mcp/config_engine | 5 | 10 |
| mcp/drift | 0 | 18 |
| mcp/evidence | 5 | 20 |
| mcp/server | 3 | 11 |
| mcp/specs | 2 | 11 |
| mcp/states | 3 | 53 |
| mcp/summary | 0 | 11 |
| review/ai_audit | 2 | 16 |
| review/signatures | 6 | 39 |
| run/evidence_writer | 4 | 19 |
| run/host | 7 | 19 |
| run/mutation | 6 | 22 |
| run/reports | 6 | 24 |
| run/run_script | 10 | 43 |
| 11 skill specs (anchor 6, audit 7, build 9, drift 4, export 6, init 7, sign 10, spec_from_code 8, spec 7, status 5, test 7) | 0 | 76 |
| **Total** | **90** | **563** |

**The 90 rules**

In the last column, "Yes" means the test as written could run on Windows. Every entry that says otherwise names what it uses that Windows lacks.

| Spec | Rule | What it says | Why it differs on Windows | Can its tests run on Windows |
|---|---|---|---|---|
| config_engine | RULE-1 | The root is `PURLIN_PROJECT_ROOT` when it names a folder that exists | Environment variable, path | Yes |
| config_engine | RULE-2 | Otherwise the root is found by climbing to the nearest `.purlin/` | Paths; the climb ends at the drive root | Yes |
| config_engine | RULE-8 | A write sets one key in `.purlin/config.json`, creating it | Text-mode write gives CRLF; temp file beside it | Yes |
| config_engine | RULE-10 | The write is atomic: temp file beside it, then moved over it | On Windows the move fails while another program holds the file open | Yes; the interruption is simulated, a real lock is not |
| config_engine | RULE-13 | `resolve_project_root` names env, climb or cwd | Environment variable, paths | Yes |
| upstream | RULE-1 | `add` writes `specs/_anchors/<name>.md` with Source and Pinned | Starts git; the clone folder is removed although git marks its files read-only | Yes (local repos; the removal helper clears read-only) |
| upstream | RULE-3 | With no `--name`, the anchor is named after the `--path` file | Path split on `/` only, so `specs\x.md` gives a wrong name | Yes, but the proof uses `/`, so the gap is not shown |
| upstream | RULE-7 | A readable text file becomes a free-text anchor pinned by the hash of its text | Drive-letter path versus repository; line endings in the hash | Yes |
| upstream | RULE-8 | `sync --check` writes no file and reports current or behind | Starts `git ls-remote` | Yes |
| upstream | RULE-9 | Exit 0, 1 or 2, including a source that cannot be read | Starts git; deletes a source repository with read-only files | Yes |
| upstream | RULE-11 | `sync <name>` rewrites the copy at the new head and reports the delta | Git clone, temp folder, file write | Yes |
| upstream | RULE-22 | Every file written lies under the project root | Paths, temp folders | Yes |
| package | RULE-1 | A bare run writes the package, commits nothing, leaves no checkout | Temp folder and a git worktree that must be removed | Yes |
| package | RULE-8 | The same commit gives the same bytes: `\n` line ends, same from a second clone | Line endings; git's checkout conversion | Yes; autocrlf is not set by the tests |
| package | RULE-9 | Fingerprint of the canonical bytes; `--check` | A package checked out with CRLF | Yes |
| scaffold | RULE-13 | A workflow is written only for an `@env` proof for a system this machine is not | Depends on which system this is | Yes (the test picks a foreign system) |
| scaffold | RULE-19 | An appended block is added once, never twice | Line endings of the project's own file | Yes |
| scaffold | RULE-20 | A second run at the same gate writes no file | Byte comparison, line endings | Yes |
| scaffold | RULE-21 | No file written names the plugin's folder | Path spelling | Yes, but it looks only for this system's spelling, not `C:/...` |
| scaffold | RULE-22 | A marketplace copy sets a project up the same way | `CLAUDE_PLUGIN_ROOT`, paths | Yes |
| scaffold | RULE-23 | No file written points at this repository's `dev/` | Path spelling | Yes, but it looks only for `/dev/` and `dev/`, not `dev\` |
| scaffold | RULE-34 | A run ends on the status lines or `→ Run: purlin:spec ...` | `→` on a cp1252 console | Yes (output captured, not a real console) |
| scaffold | RULE-36 | A project walks the three gates up to the signed tag | bash, ssh-keygen, signed commits and tag | No: `dev/test_init_e2e_gates.sh` exits 0 on Windows without walking |
| scaffold | RULE-37 | Each language is set up the same way and its marked test runs | Starts pytest, npx, dotnet, go through bash | No: `dev/test_init_e2e_wiring.sh` exits 0 on Windows; the Go proof skips where go is missing |
| scaffold | RULE-44 | Remote and host are checked; gh or az is reported present or absent | Finding programs; the check misses `gh.exe` | No: skipped when `os.name == 'nt'`; the fake gh is a `#!/bin/sh` file |
| scaffold | RULE-47 | The evidence README has the same bytes as the template | Line endings (copied as bytes for Windows' sake) | Yes |
| update | RULE-5 | `--yes` applies everything; a second run changes neither the commit nor the tree | `git status` under line-ending conversion | Yes |
| update | RULE-7 | Each rewritten file is backed up with its previous bytes | Bytes | Yes |
| update | RULE-8 | Proof and run files removed from disk and git; `.purlin/cache/` deleted | Deleting files and folders, git | Yes |
| update | RULE-16 | Old plugin copies removed; wiring removed from conftest and jest/vitest config, with backups | Files | Yes |
| update | RULE-18 | One commit for the run; nothing left uncommitted but the backups | Git and line endings | Yes |
| update | RULE-20 | No emoji; ends with `→ Run:` or the summary | Console encoding | Yes (captured) |
| update | RULE-28 | The evidence README has the bytes init writes | Line endings | Yes |
| update | RULE-29 | Old markers become comments; shell harness calls become no-ops; backups | Rewriting files, line endings, shell scripts | Yes (rewrites text, runs no script) |
| update | RULE-31 | A `purlin-report.html` that is a link is replaced by a copy | Symbolic links | Partly: skips where no link can be made (Windows without Developer Mode or administrator) |
| purlin_version | RULE-7 | `dev/bump_version.sh` writes VERSION and every copy; `--check` | Shell script (sed) under Git Bash | Yes, through Git Bash; used only by maintainers |
| evidence | RULE-1 | Fingerprint is three sha256 values taken from the working tree | `git hash-object` and line-ending conversion | Yes |
| evidence | RULE-4 | The code part covers files, folders and globs of the Scope line | Paths, git pathspecs | Yes |
| evidence | RULE-7 | The tests part covers tracked test files that carry a marker | Paths (suite globs) | Yes |
| evidence | RULE-8 | Untracked files change nothing and are listed; ignored files are not | Git, paths | Yes |
| evidence | RULE-14 | Sections keyed windows, macos, linux; this machine reads `windows` on Windows | Names this system | Yes (system simulated) |
| server | RULE-5 | Stdout carries JSON-RPC only; the startup line goes to stderr | Text-mode stdout gives CRLF and cp1252 | Yes (started with the test's Python, not through sh) |
| server | RULE-6 | A call may name its own `project_root` | Windows or Git Bash path spelling | Yes |
| server | RULE-22 | The manifest starts the server through `sh` and the interpreter resolver | Needs sh on Windows; the resolver falls back to `py -3` | Reads the manifest only; nothing starts the server through sh |
| specs | RULE-11 | A spec is an anchor when its path lies under `_anchors/` | Path separators | Yes |
| specs | RULE-14 | A file that cannot be read is skipped | File permissions | No: skipped with no `os.geteuid`, which is always the case on Windows |
| states | RULE-28 | A feature entry carries the spec, signature and evidence paths | Paths use `/` for links | Yes |
| states | RULE-32 | The data file is written as `const PURLIN_DATA = ...` | Temp file and replace | Yes |
| states | RULE-47 | Signed `at` is the commit date, or the file's stamp where git cannot answer | Git run with `TZ=UTC` in its environment | Yes |
| ai_audit | RULE-3 | `claude -p --output-format json`, prompt on stdin, 300 s | Starting claude (`claude.cmd`), timeout | Yes: the fake writes a `claude.cmd` too |
| ai_audit | RULE-7 | Unreachable model: not on PATH, error exit, timeout, no settled line | Finding a program, killing on timeout | Yes |
| signatures | RULE-17 | No key: prints the setup lines, ssh-keygen only while `~/.ssh/id_ed25519` is missing | Home folder, environment variables | Partly: the test moves HOME, which Python ignores on Windows (it reads USERPROFILE) |
| signatures | RULE-18 | One invocation is one signed commit | Git signing through ssh-keygen | Yes, where ssh-keygen is on PATH |
| signatures | RULE-20 | A signature counts when the last commit touching its file is signed | Git's signature check depends on the gpg and ssh programs present | Yes |
| signatures | RULE-45 | Writes the signed tag `signed/<version>` | Git signing | Yes |
| signatures | RULE-50 | Records email, user.name and key fingerprint | `ssh-keygen -l` | Yes |
| signatures | RULE-60 | Key fingerprint from a `.pub` path, a private key path or a `key::` value | Paths (`~`, backslashes), ssh-keygen | Yes |
| evidence_writer | RULE-1 | `--test` writes local evidence keyed by this system, with machine and hostname | Names this system and host | Yes |
| evidence_writer | RULE-4 | Replaces only its own system's section; the others stay byte for byte | Text-mode write, line endings | Yes |
| evidence_writer | RULE-7 | The same observation leaves the file byte for byte | Line endings | Yes |
| evidence_writer | RULE-16 | `machine` is the host's name, or `unknown` | Host name lookup | Yes |
| host | RULE-5 | A GitHub CI commit through the API: one tree with each path's text | `/` paths; bytes as written on the runner | Yes (API faked) |
| host | RULE-12 | `purlin:test --remote`: push, gh run list and watch, pull, delete | Starts git and gh; gh looked for with no `.exe` | Yes, but the fake gh has no extension, so the gap is not shown |
| host | RULE-18 | The rendered workflow's triggers and steps end on `--all --ci` | Bash and python3 steps on a Windows runner | Reads the text only; only a real remote run shows it |
| host | RULE-24 | `deleted_files()` gives git `.purlin/evidence` with `/` | Paths | Yes (Windows joining simulated) |
| host | RULE-26 | A root that is not the job's workspace speaks for nothing | Environment variables, path comparison | Yes |
| host | RULE-27 | The API commit is refused the same way | Same | Yes |
| host | RULE-31 | Azure: az list and show, intervals, limits, no credential prompt | Finding az (`az.cmd`), timeouts | Likely no: the fake az has no extension, which Windows lookup does not match |
| mutation | RULE-5 | Stryker runs once per feature with a generated config and report path | Temp folder, paths | Yes (checks the command, does not run it) |
| mutation | RULE-7 | The project's `node_modules/.bin/stryker` wins over PATH | Windows has `stryker.cmd` | Yes, but the fake has no extension, so the gap is not shown |
| mutation | RULE-13 | Stryker.NET arguments; the report is found by walking the output folder | Temp folder, paths | Yes |
| mutation | RULE-14 | `dotnet` on PATH; install check `dotnet stryker --version` | Finding programs | Yes (faked) |
| mutation | RULE-18 | Without mutmut there is no engine; the reason names `pip install mutmut` | mutmut 3 installs on Windows but does not run there | Yes (faked) |
| mutation | RULE-22 | An engine past `--arm-timeout` measures nothing | Killing a child process | No: PROOF-22 fakes mutmut as a `#!/bin/sh` script with `sleep 30` |
| reports | RULE-3 | Suite globs `*`, `?`, `**` | Paths | Yes |
| reports | RULE-10 | A case's file comes from the `file` attribute, a class path or a module | Reports written on Windows carry backslashes | Yes, but it reads reports captured on a Mac |
| reports | RULE-15 | An `exit` suite runs the command once per file | File path handed to bash | Yes (Git Bash found from git) |
| reports | RULE-16 | `{files}` is quoted and the command runs through bash from the root | Shell | Yes |
| reports | RULE-17 | The report is deleted before the run; `-` is read from stdout | Deleting open files, stdout | Yes |
| reports | RULE-21 | `markers.py --near-misses` prints JSON with `file` | Paths | Yes |
| run_script | RULE-4 | A SQL script run through `sqlite3 -bail` is one test | Starts sqlite3 with bash redirection | No where sqlite3 is not installed (skipif) |
| run_script | RULE-10 | An `@env` proof for another system is not counted and names both systems | Names this system | Yes |
| run_script | RULE-12 | `--ci` writes the runner's section as `remote runner, <system>` and commits | Names the system, paths | Yes (API faked) |
| run_script | RULE-21 | This system reads as windows, macos or linux | Names this system | Yes (win32 simulated) |
| run_script | RULE-39 | stdout and stderr are set to UTF-8 before printing | Console encoding | Yes (cp1252 simulated) |
| run_script | RULE-40 | A suite that fails or is killed shows its last 60 lines | Killing a `bash -c` child and its children | Yes |
| run_script | RULE-43 | No marker is read from `mutants/` | Paths | Yes |
| run_script | RULE-55 | Selection includes untracked files under the Scope or beside marker files | Git, paths | Yes |
| run_script | RULE-58 | `{files}` holds only the marked test files of the features run | Paths on a command line handed to bash | Yes |
| run_script | RULE-63 | The suggested entry is the tool's own command, such as `python3 -m pytest` | A python.org install on Windows has no `python3` | Yes (reads text) |

**Test files that skip on Windows today**

- **`dev/test_init_e2e_gates.sh` and `dev/test_init_e2e_wiring.sh`.** Both source `dev/windows_skip.sh`, print "This suite does not run under Git Bash on Windows" and exit 0. An `exit` suite records that as passed. This covers scaffold PROOF-36, 90–93 (RULE-36) and PROOF-37, 94–97 (RULE-37).
- **`dev/test_init_scaffold.py::test_gh_present_or_absent_is_named_and_the_workflow_written`.** It calls `pytest.skip` when `os.name == 'nt'` (scaffold PROOF-78, 79, RULE-44).
- **`dev/test_specs_reader.py::test_a_spec_that_cannot_be_read_is_skipped`.** It is skipped when `os.geteuid` is missing, which is always true on Windows (specs PROOF-15, RULE-14).
- **`dev/test_init_update.py::test_the_page_linked_into_the_old_plugin_is_replaced`.** It skips when a symbolic link cannot be made (update PROOF-31).
- **Skips that are not about Windows but usually fire there:**
  - `dev/test_run_script.py` skips without sqlite3 (run_script PROOF-4).
  - `dev/test_init_scaffold.py` skips without go (scaffold PROOF-52).
  - `dev/test_reports.py` skips without npm, dotnet or go; these are untied capture tests.
  - `dev/test_purlin_report.py` skips without Playwright.
- **`dev/test_consumer_ci.py`.** It does not skip: it expects the fixture's Linux-only test to fail on any other system.
- A skipped tied test reads `not run`, and that makes a run exit 1 (run_script RULE-8).

**The ten I am least sure of**

1. **host RULE-18 (in).** Its tests only read the rendered workflow text, so running them on Windows adds nothing. A real remote run is the proof.
2. **server RULE-22 (in).** Same problem: the test reads the manifest and never starts the server through sh.
3. **scaffold RULE-34 and update RULE-20 (in).** They are about console encoding of `→`, and may repeat run_script RULE-39, since the entry points already set UTF-8.
4. **mutation RULE-18 (in).** mutmut 3 does not run on Windows at all (noted in `dev/plans/TODO-0.10.0.md` item 5). The rule may need a Windows answer, such as strength `n/a`, rather than a Windows proof.
5. **purlin_version RULE-7 (in).** It only affects maintainers; consumers never run `dev/bump_version.sh`.
6. **states RULE-28 (in).** The product already turns every path to `/`, so this is only a guard.
7. **The skill specs' RULE-2 (all out).** The skills tell the agent to run `python3 "${CLAUDE_PLUGIN_ROOT}/..."`, which fails where Windows has no python3. But their tests read text, so a Windows run proves nothing.
8. **update RULE-13, 23, 24 (out).** They rewrite spec lines in text mode, which turns LF into CRLF on Windows. "The rest untouched" holds line by line but not byte for byte.
9. **drift RULE-17 and states RULE-35 (out).** Uncommitted-spec detection and "every checkout and CI read the same hash" both rest on git's line-ending handling, which differs on Windows.
10. **dashboard/purlin_report RULE-1 and RULE-2 (out).** The build writes text mode, so it gives CRLF on Windows. It is maintainer-only.

**What it would take to run them**

- **Waiting.** 90 of 563 rules (16%) would wait on a remote run before counting as passed; the other 473 pass from your Mac alone. They cover 179 proofs across 17 specs.
- **When they wait again.** After any edit to one of those 17 specs, their code or their tests, that feature's Windows result goes out of date and its tagged rules read `to test on Windows` again. Those specs cover most of `scripts/`, so most code changes would send some of the 90 back.
- **How to tag.** Tagging an existing proof `@env(windows)` means only Windows proves it, and your Mac stops counting it. Keeping both takes one new Windows proof line per rule, with a second marker above the same test: at least 90 new lines.
- **What the remote run is.** One Windows job running the whole suite. It last ran green on Windows in about 16 minutes, before much of the 0.10.0 rewrite; the Linux job took 5. It runs every rule's tests, not just the 90: a rule that fails only on Windows reads `partial` and lands in `to fix`, tagged or not.
- **Before the first green run:**
  - the six skipping tests need a decision;
  - `gh` must be found as `gh.exe` if anyone runs `--remote` from a Windows machine;
  - this repository needs its runner file written again (decision 83). Nothing carries `@env` today, and there is no CI evidence and no signature, so no signature would end.

**Questions for you**

1. When a rule's only test reads text, like the workflow template or the plugin manifest, should it still wait on a Windows run, or is a real remote run enough proof?
2. Should your Mac keep proving these 90 rules, meaning one new Windows proof per rule, or should Windows alone prove them?
3. The two end-to-end init walks need a POSIX shell and SSH signing. Should Windows be made to walk them, or should those two rules be left off the Windows list and the skip made to read `not run` instead of passed?
4. On Windows, should a pytest project's test strength simply read `n/a` because mutmut does not run there, and should the rules say so?
5. Should rules only maintainers use, like the version bump script, be on the list?
6. Should the four likely Windows defects be fixed before the first remote run, or should that run be what finds them?

The working files are in `/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/8c7da91f-67d4-4e89-8416-d6695b075a74/scratchpad/`: `rules.txt`, `proofs.txt`, `markers.txt` and `g1.txt` (the list above, by spec and rule).
