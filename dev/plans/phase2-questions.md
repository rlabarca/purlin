# The 79 questions, the faults and Windows, grouped

Source: `dev/plans/phase2-report.md`, read against `dev/plans/three-levels.md` decisions 31 to 93,
`dev/plans/handoff.md`, `dev/plans/phase1-plan.md` section 9, `CLAUDE.md`,
`references/writing_style.md` and `references/spec_quality_guide.md`. Question numbers are the
report's.

Counts: 79 questions. 10 already answered. 55 have one sensible reading (52 lines, three pairs
merged). 14 are real choices, merged into 5 questions for the owner. 12 merged as duplicates in
all (9 into the owner's 5, 3 pairs among the readings). Of the 8 product faults left for the
owner, 6 take one reading and 2 fold into owner questions. Windows: 3 questions, 5 readings.

## Already answered

- Q1 (a check repeated at each of the three gates in one proof): decision 71, one starting situation per proof, so one proof per gate.
- Q3 (`No proof` box and `To write a proof for` button carry one number): decisions 87 and 85 keep both, the box first among the steps, the button as a line of `Left to do`.
- Q5 (the `To tag` button): decision 85, every line of `Left to do` is a filter button that names its command; keep it as built.
- Q6 (`FAILED` on a rule that passed on one system and failed on another): decision 85, `FAILED` where a test fails; decision 69, passed only when every tied test ran and passed.
- Q8 (several inputs with the same result): decision 71, a refusal or a boundary is a case of its own; one proof per input.
- Q14 (a second setup run asks before each file): decisions 70 and 80, setup asks the gate and, at `strong` and `signed`, the breaking question, and nothing else; stop asking per file.
- Q31 (drift's QA view carries rules not yet audited): decisions 61 and 78, no person judges strength, and QA's view holds hand checks and signatures only; remove the list.
- Q34 (the package promises it names no test editor): decision 52, "Nothing about who last changed the test is put in the evidence"; keep the promise and its check.
- Q56 (the 135-line cap on the agent's instructions): decision 80, each command's instructions keep their maximum length, a change cuts as many lines as it adds; keep 135.
- Q62 (the build skill at `passed` ends on `→ Run: git push`): decision 76, a finished project at `passed` and `strong` ends on `Nothing left to do.` and names no command.

## One sensible reading

Each line: the question, the reading, and what it rests on. The owner can object to any.

- Q2 (states RULE-4 and RULE-5 always pass or fail together): fold RULE-5 into RULE-4, its proofs moved; quality guide, overlap means merge.
- Q4 (the dashboard's closing line when nothing is left): show it where the filter buttons stand, `Nothing left to do.`, and at `signed` the push of the tag, as built; decisions 76 and 85, the buttons take the place of `Left to do`, and every output says what to do next.
- Q7 and fault `run_script` (a rule waiting only on another system is listed as `to fix: purlin:build`): a proof whose test is skipped here because another system owns it counts under the existing line `to test on <system>: purlin:test --remote`; one whose test does not exist counts under `purlin:build`; decisions 65 and 69, advice fits the cause.
- Q9 (the emoji check covers one script and part of the range): one rule, one check of every emoji and pictograph across everything Purlin prints, and the emoji clauses scattered over five other specs go; `CLAUDE.md` and the writing style make it one promise with one home.
- Q10 (the out-of-range parallel-audit warning prints twice): print it once, beside the status table with the other settings warnings.
- Q11 (`purlin:sign` exits 0 when the tag was not written): exit 1 when the tag was refused for a reason the person must fix (uncommitted work or results, no version, package not committed); exit 0 when the tag already exists; decision 69, the ending and the exit code agree.
- Q12 and Q26 (a named rule that does not exist: sign prints no next step; the audit reader prints nothing): one line naming the rule that was not found and `purlin:status <feature>` to list the feature's rules, printed last above the summary; decision 69.
- Q13 (two signature rules for a rule the spec lacks, one of them internal): remove the internal one and its proof; the one a person sees covers the case; quality guide, a rule says what a caller sees.
- Q15 (two scaffold rules promise no plugin folder is named): one rule holds both starting situations, the check at `passed` filed under it; overlap means merge.
- Q16 (the TypeScript and C# walk through the gates, tied to no rule): remove it; the Python walk shows the gates, each language is shown to set up and run its tests, and each breaking tool has rules of its own.
- Q17 (the dashboard switch's own upgrade rule repeats the seven-settings rule): remove the switch's rule and move its two checks, as proofs, under the seven-settings rule; overlap means merge, and each check is a case.
- Q18 (the upgrade takes a non-gate answer silently): print the same line setup prints, naming the gate it used; decision 69.
- Q19 (the eight checks that a project reads as set up by 0.9.5): one rule under the test run, "a project set up by 0.9.5 and not upgraded stops the run and names the upgrade", with each of the eight signs as a proof of it; decision 80 and the guide's observable rule.
- Q20 and fault `evidence_writer` (a rule with some proofs untested reads `not run`): the rule reads `no test`, the run names the proof with no test, and `Left to do` points at `purlin:build`; decision 69.
- Q21 (a local result records the computer's name twice): record the lent host name only for a remote runner; decision 77.
- Q22 (a comment naming nothing fails the run while the last line says `Nothing left to do.`): keep the failure (decision 56) and add the line `<n> test comments to correct: purlin:build` to `Left to do`, so the ending names the work; decisions 69 and 79.
- Q23 and fault `reports` RULE-8 (three rarer .NET outcomes count as passed): count `Warning`, `Completed` and `PassedButRunAborted` as passed, because each says the test itself ran and passed, and reword the rule and the marker format to match; decision 69 asks that the test ran and passed, not that the whole run finished.
- Q24 (the near-miss suggestion names a rule a comment may not name): suggest only ids a comment may name; where the nearest rule has exactly one proof, suggest that proof; a suggestion must survive the next run.
- Q25 (the audit's notes are not printed with its findings): print them under their own heading after the findings; decision 75 keeps the notes, and an output that holds them should show them.
- Q27 (the job's folder rule and the refused commit rule): merge into one rule with the same five proofs; overlap means merge.
- Q28 (the fallback that guesses the default branch): remove it; when nothing names the branch, the commit goes on the current branch or is refused with a line saying no branch could be read; the reason it existed went with decisions 32 and 67.
- Q29 (a runner on a branch that is neither a run branch nor a signed tag prints `Tag run: ...`): a line of its own that says what the run is and that nothing is written, with a proof; a page says what is.
- Q30 (drift never mentions a deleted file): count it under the feature whose scope covered it, and name uncovered deletions with the other uncovered files; decisions 42 and 72, a deleted covered file is a code change.
- Q32 and fault `drift` RULE-10 (an Azure DevOps anchor is never checked): try every source that passed the safety check and report `error` when it cannot be read; drift reports facts and nothing is left out silently (decisions 33 and 43).
- Q37 and Windows Q4 (breaking on, nothing measured): an engine not installed or timed out makes the rule weak with a reason naming the command that fixes it, since decision 35 says the share must reach the minimum; an engine that cannot run on this system (the Python tool on Windows) counts as no engine, and the audit alone decides with `test strength: not measured` (decisions 35 and 93).
- Q38 (the Python tool's breaks matched to a scope by module name): turn each module name into its file and count it for every feature whose scope reaches that file, as a scope reaches files everywhere else.
- Q39 (another JSON file read when the .NET report is missing): remove it; only the named report counts, else the log says no report was written; decision 51, Purlin never guesses.
- Q40 (half the sign skill's proofs describe a damaged copy caught by the check): take them out of the spec and keep each damaged copy as a second check inside the test of the proof it guards; the guide says a proof is not about the test.
- Q41 and fault `upstream` RULE-15 (a plain sync downloads the source once per anchor): fix the product to download each source once per run, so the rule holds as written; the rule is right and the product is wrong.
- Q44 (the `@manual` and `@env` rules stated in the spec-format anchor and again in the spec reader): keep them in the anchor, which every spec must meet; the reader drops its three and relies on requiring the anchor; `CLAUDE.md`, one home.
- Q46 and Q48 (proof numbers after a spec file was replaced whole): count from the current file, for every spec; nothing recorded under the old numbers survives (0.10.0 is a clean release, decision 44, and nothing is signed yet).
- Q49 (C# program starts passed a named value): remove the C# part of the rule; Purlin ships no C# code, so the rebuild test says it is not a rule.
- Q50 (the one Python program start that takes a named list): change that start so its list is written in place, and hold every start of that form to it; the rule is then checked in full.
- Q51 (`system(` and `passthru(` named by two security rules): keep them only under the rule about handing a command line to the system, which is what they do; overlap means merge.
- Q52 (the export's line for a package that fails its fingerprint): name the command that takes the package the tag already carries, `git show signed/<version>:.purlin/evidence/package/<version>.json`; decision 55, the tagged commit carries the package, and decision 69.
- Q57 (the agent does not explain `No proof`): leave both words to the glossary and drop the agent's `no proof written` sentence, which frees a line under the cap; `CLAUDE.md`, the glossary is the one home of each word.
- Q58 (where the agent's emoji ban lives): keep it inside the fourth never; the agent's instructions are the one text every session reads.
- Q60 (the check that commits hand-written messages, tied to no proof): delete it; it reads nothing Purlin wrote.
- Q61 (does the changeset in a build commit carry a heading): yes, `Changeset:`, like `Decisions:` and `Review:`; the conventions' example and the skill change together, and the three sections read alike.
- Q64 (the skill's "no rule for a private helper" is unguarded): add a rule and its proof, like every other instruction of the skill; decisions 66 and 81.
- Q65 (an unreadable settings file reads as empty and is later overwritten): commands say the file cannot be read and name the line, and saving is refused until it is fixed; decision 69 treats a missing settings file the same way.
- Q66 (a failed save reports success): the save stops with an error naming the cause, and the tool says the setting was not saved; decision 69, the answer matches the disk.
- Q67 (the shell command line that reads settings, used by nothing): remove it, its rule, proofs and tests, with a line in `RELEASE_NOTES.md`; remove a mechanism where one can.
- Q68 and Q69 (the settings tool accepts an empty value and a gate of `gold`): refuse both for the settings Purlin knows, name the accepted values, and leave the file unchanged; decision 69.
- Q70 (a missing setting answers in a different shape): answer in the same data shape either way, with the setting shown as absent; the rule says so.
- Q72 (the status skill's spec now lists the status tool's code): move the proof that the printed lines and the dashboard data agree to the spec that covers the status tool, and list only the skill's instructions; decision 72, a signature's code is its own feature's files.
- Q74 (who writes the version fields): only the bump script sets a new number; anything else may copy it from `VERSION`, and a test checks nothing writes it from another source; `CLAUDE.md`, the version lives in one file.
- Q75 (the settings template's version reaches no project): remove it from the template, the bump script, its check and `CLAUDE.md`'s list of derived locations; a copy nothing reads is a mechanism to remove.
- Q76 (a missing `VERSION` file reports 0.0.0): keep reporting 0.0.0 and working, as the rules now read; an install always ships the file.
- Q77 (a skill that adds a contradicting line elsewhere): leave the checks where they stand; a fixed list of phrases catches only those phrases, and review of each change holds the rest.
- Q78 and fault `skill_drift` (the drift skill's samples; one shows a 40-character sha): remove the sample view from the skill and point at the drift criteria reference, which already shows one line of each kind; `CLAUDE.md`, one home, and the wrong sha goes with it.
- Q79 (which tag marks a release of Purlin itself): the signed tag `purlin:sign` writes, pushed by the owner; the release steps say set the version, commit, sign, push the tag; decisions 31 and 76, the tag is the one marker.

## For the owner

Ordered most basic first. Each question merges the report's questions named after it.

### 1. Test tools

(Q47)

**What it is for.** Purlin runs your project's own test command. Setup asks only how far every rule must go; the first test run looks at the project, suggests a command for the test tool it recognises, and runs it once you confirm. A project with tests in two tools, for example Python and JavaScript, needs two commands.

**The question.** How does a project with two test tools get its second command?

**Options.**
1. **First run suggests all.** Recommended. The first test run suggests one command for each test tool it recognises and you confirm them together; setup loses its flag for adding a tool. Setup keeps asking one thing, and nobody has to know a second step exists.
2. **Keep the setup flag.** Setup keeps a flag that adds one more tool's command. A person with two tools types one more command, once they know it is there.
3. **Remove the flag, edit by hand.** The first run suggests one tool, and a second is added by changing the settings through Purlin's settings tool or in the file. Nothing new to build, and the least guided.

### 2. Spec errors

(Q33, Q43, Q53, Q54, Q55, and the fault that a reused rule number goes unreported)

**What it is for.** Purlin reads your specs to know which rules exist, which files each spec covers, and which proof belongs to which rule. Some mistakes it can see and today reports nowhere: an entry in the list of files a spec covers that finds no file, so a typo leaves that file silently uncovered; two specs in different folders with the same file name, so one is read and the other's rules vanish from the status, the tests and signing; a rule number used twice, so one screen says 2 rules while the list of work says 3; a proof line it cannot read, which is dropped; and a first heading that names a different feature from the file.

**The question.** When Purlin can see a mistake in a spec, should it say so?

**Options.**
1. **Warn and name the fix.** Recommended. The status and every test run print one line naming the spec, the mistake and the command that fixes it, and carry on. Nothing is refused, so Purlin logs and does not police, and an agent reading the line knows what to change. New product work in five places.
2. **Warn where rules vanish.** Warn only where rules or results go missing: two specs with one name, a number used twice, a proof line dropped. The covered-files typo and the heading stay silent. Less work; a typo in the covered files still goes unnoticed.
3. **Stop the run.** A run stops, names the mistake and writes nothing until it is fixed. Nothing is ever silently missing, and one typo blocks every run, the remote runner included.
4. **Say nothing.** The rules are reworded to say the author keeps specs right. No product work; the screens can disagree and rules can vanish without a word.

### 3. Strength

(Q36, and the fault that a test is matched by the end of its file path)

**What it is for.** At the gates that ask for an audit, Purlin can break the code on purpose and count how many breaks the tests catch; a rule is strong only when that share reaches the minimum. The tools for JavaScript and .NET say which test caught each break, so Purlin can work out a share for each rule from its own tests. The Python tool cannot, so Python gives one share for the whole feature. Today the share per rule is worked out and thrown away: every rule is judged on its feature's share, and the docs say otherwise. Keeping it would first need a fix, because a test is matched to its file by the end of the path, so a test of the same name in another folder is credited to the wrong rule.

**The question.** Should a rule be judged on the breaks its own tests caught, where the tool can tell?

**Options.**
1. **One share per feature.** Recommended. Every rule is judged on its feature's share, in every language; the working per rule and the rules about it go, and the docs are corrected. Strength means one thing everywhere, and a mechanism is removed.
2. **Per rule where possible.** A JavaScript or .NET rule is judged on its own tests' share, a Python rule on its feature's, and the file matching is fixed first. More exact in two languages, and strength then means two things depending on the language.
3. **Worked out, unused.** The share per rule is still worked out and nothing reads it; only the docs are corrected. Nothing changes for a user, and code stays that nothing uses.

### 4. Skill specs

(Q59, Q63, Q71, Q73)

**What it is for.** Each command, spec, build, test, audit, sign and the rest, is a set of instructions the agent follows. Eleven of Purlin's own specs hold rules about those instructions, and their tests can only read the instructions and check that the right sentences are there. They cannot show that an agent, once told, does it: writes the commit in the agreed shape, ties the tests a project already has, prints the status as given.

**The question.** What should a rule about a command's instructions claim, and what shows the agent follows them?

**Options.**
1. **Say what it tells.** Recommended. Each rule says what the instructions tell the agent, and the tests read the instructions, as most of these specs now do. What passes is exactly what is checked; real behaviour is shown by the sanity checks before each release, which run the commands for real.
2. **Add a hand check.** As above, plus a few proofs a person carries out before each release on a small practice project, signing what they saw. Real behaviour is on the record, at the cost of a person's time every release.
3. **Run the agent in the tests.** The test suite runs the real command on a practice project and reads what it wrote. A change in the model's behaviour is caught, and every full test run calls the model, takes minutes, costs money and can vary.
4. **Remove these specs.** The eleven specs about instructions go, and review of each change holds the instructions. 76 fewer rules to audit and sign; nothing fails when a sentence an agent relies on is deleted.

### 5. Rule size

(Q35, Q42, Q45)

**What it is for.** A person signs a rule as a whole, and an edit to its words or proofs ends its signature. Some rules list several separate things: the one rule listing the roughly thirty items the evidence package carries for each rule; the audit command's one rule, with sixteen proofs, covering what it runs at each gate, what it prints, what it commits and that it never waits on a signature; and three rules of the test command's instructions. Each is now proved one case per proof, so a failure already names the item that broke.

**The question.** Should a rule that lists several separate things be split?

**Options.**
1. **Split by claim.** Recommended. Each such rule is split into the few separate claims it makes, with the proofs moved unchanged; for the audit, three rules. It meets the guide's one claim per rule, and an edit to one part ends only that part's signature. A handful more rules to audit and sign.
2. **Keep them whole.** One line to read, audit and sign for each; the proofs already say which item broke. The guide's one claim per rule is not met.
3. **One rule per item.** Every item becomes its own rule. The finest reporting and the most to sign, dozens more rules.

## Windows

The report ends by asking for three decisions. Its six questions fold into them or take a reading.

### W1. Windows list

**What it is for.** Some rules must also hold on Windows, because what they promise depends on the system: how files are written, how paths are spelled, how other programs are found and started. An agent sorted all 563 rules and found 90, in 17 specs; the rest read the same everywhere. Once marked, those 90 wait for a Windows run before they pass, and wait again after most code changes.

**The question.** Which rules go on the Windows list?

**Options.**
1. **Trim and extend.** Recommended. Take the 90; leave off those whose only test reads a text file, since a Windows run of it shows nothing new, those only Purlin's maintainers run, and the two about console characters another rule already covers; add the five left off that rest on line endings, the upgrade's rewrite of spec lines and the checks that depend on git's line-ending handling. A Windows run proves what could differ, and nothing that could differ is left out.
2. **Accept the 90.** Mark the list as sorted. Some rules wait on a Windows run that can show nothing new, and the line-ending rules go unproven there.
3. **Mark none.** No rule waits on Windows and no remote runner is written; Windows is checked by a person before a release. Nothing waits, and Windows is on the record only as a person's note.

### W2. Mac and Win

**What it is for.** A rule is marked for Windows by a tag on one of its proofs. A proof tagged for Windows is proven only by a Windows run; your Mac no longer counts it.

**The question.** How is each rule on the list marked?

**Options.**
1. **Add a Windows proof.** Recommended. Each rule gets one more proof line, tagged for Windows and tied to the same test by a second comment; the Mac keeps proving the proof it has. Both systems you care about stay on the record, at the cost of one new line per rule, at least 90.
2. **Tag the existing proof.** One existing proof per rule is tagged for Windows. No new lines; for these rules the Mac result no longer counts, though the Mac is where you develop.

### W3. Win skips

**What it is for.** The Windows run runs the whole test suite, and six tied tests stop it being green today. Two walk a new project through the three gates up to the signed tag, using a Unix shell and SSH signing; on Windows they print a line and report success without walking, which counts as passed. Four skip on Windows: finding the GitHub command-line tool, an unreadable file, a symbolic link, and the SQLite program. A skipped tied test fails the run.

**The question.** What happens to these six tests on Windows?

**Options.**
1. **Run or mark each.** Recommended. The two walks stop reporting success when they did not walk. Each test that can be made to run on Windows is fixed to run there; each that cannot, such as the walks and the symbolic link, has its proof tagged for macOS, so a Windows run leaves it out and says why. No result claims something happened that did not.
2. **Make all six run.** The walks and the four skipping tests are made to run on the Windows runner, with the Unix shell that comes with git, SSH signing and symbolic links set up there. The most proven, and the most work before the first green run.
3. **Mark all six macOS.** All six proofs are tagged for macOS and the walks stop reporting success on Windows. The least work; none of the six is proven on Windows.

### Readings for the rest of the Windows questions

- Q1 (a rule whose only test reads text waits on Windows?): no; it reads the same on every system, and is left off in W1's first option.
- Q4 (mutmut on Windows): see Q37 above; an engine that cannot run on this system counts as no engine, and strength reads not measured.
- Q5 (rules only maintainers use): left off; no consumer runs them, and the maintainer works on a Mac.
- Q6 (fix the four likely defects before the first run, or let it find them): fix them first. The run would not find them, because the stand-in programs in the tests have no `.exe` or `.cmd` ending; give the stand-ins those endings so the tests show each fix.
- Not asked, found in the sort: the skills tell the agent to start Purlin's scripts with `python3`, which a python.org install on Windows lacks. Reading: the skills start them through the same interpreter lookup the plugin's server uses, which falls back to `py -3`.
