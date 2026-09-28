# Sanity check 2: a new user follows the docs

Run on 2026-09-28 against `main` at `0e2926559`. Seven paths, one fresh Opus agent each, run at
the same time, each in its own scratch project outside this repository. Each agent had the
README, `docs/` and what the commands print, and nothing else. This repository was not changed:
`git status` was clean at the same commit before and after.

What the check did not cover, in every path: the install from the marketplace and the commands
typed inside a Claude Code session. The agents ran the scripts from the checkout. So what Claude
says around a command, and the skills that are driven by a model (`purlin:spec`,
`purlin:build`, `purlin:spec-from-code`), were not exercised. Path 7 alone ran the
`claude plugin` commands, against a scratch home folder; the marketplace gave it 0.9.5.

Real model calls: 6 in total. Path 4 made 3 and path 6 made 3, all from `purlin:audit`, one per
rule. The other five paths made none.

Every agent's full log is under the session scratch folder, `sanity2/<path>/LOG.md`, with the
screenshots of paths 1, 2, 3, 4, 5 and 6 beside it.

## 1. The verdict

A stranger can get from nothing to a proven rule with the docs alone, and from there to a signed
tag, but not without two guesses the docs do not prepare them for: what a Python project needs
before setup finds pytest, and one more line of git setup before a signature counts. The
ten-minute path took about 2 minutes 30 seconds of commands at a script's pace (path 1); with
reading, a person should fit inside the ten minutes if setup finds their test framework, and
will not if it does not. The worst moment was in path 4 and again in path 6: the signing walk
printed `3 signed` and on the next line `No tag: 3 of 3 rules do not meet the gate signed.`, with
no reason, after the reader had set signing up exactly as the docs say.

## 2. Where the docs were wrong

Each entry: what the docs say, what the product did, the paths that met it.

1. **Setup finds the test framework.** `docs/getting-started.md`: "Init reads your test
   framework from the tree". On a Python project with `tests/test_cart.py` and no `conftest.py`,
   `pytest.ini` or `pyproject.toml`, setup printed `There is nothing here to detect a test
   framework from. What command runs the tests?`. Paths 1, 4, 5, 6, 7. Path 3's project was
   detected with nothing asked, and so was path 2's Vitest project.
2. **The questions setup asks.** `docs/getting-started.md`: "Answer `passed` to the first
   question, `What must be true of every rule before a version is proven?`, `y` to `Do you trust
   your own machine for the tests?`, and the default to anything else it asks." The second
   question is in fact `Measure test strength by breaking the code on purpose? It needs mutmut
   and takes minutes to hours per run. [y/N]`, or, where no framework is found, the test command.
   Answers given in the docs' order turned breaking on (`"mutation_engine": "auto"`, a
   `setup.cfg` written) or stored `y` as the test command (`"run": "y {files}"`). Paths 1, 2, 3,
   4, 5, 6, 7. `docs/running-and-evidence.md` says "No breaks run under `passed`", and the
   question is asked at `passed`.
3. **Taking the default.** The same sentence says to take the default. The default answer to
   the test command question gives `No test command was given, so no suite is written.`,
   `Gate passed. Suites none.`, and then `→ Next: run purlin:spec to write the first spec.` with
   exit 0. Paths 1, 5, 7.
4. **Signing setup.** `docs/review-and-signing.md` and `docs/regulated-workflow.md` give three
   commands: `git config gpg.format ssh`, `git config user.signingkey ~/.ssh/id_ed25519.pub`,
   `git config commit.gpgsign true`. After exactly those: `Walked 3 rules: 3 signed, 0 cases
   added, 0 skipped.` / `No tag: 3 of 3 rules do not meet the gate signed.` Git's own words:
   `error: gpg.ssh.allowedSignersFile needs to be configured and exist for ssh signature
   verification`. Paths 4, 6.
5. **The exit code table.** `docs/running-and-evidence.md`, the table: "`1` | A test failed,
   evidence is missing, a marker names nothing a spec has, or the gate is not met". The product
   printed `gate passed not met: 0 of 12 rules meet it` and exited 0. The same page's prose says
   "The exit code follows the tests, whatever the gate line says". Paths 3, 5.
6. **The next step for a rule with no test.** `docs/how-purlin-works.md` says the next step is
   `purlin:spec`. The product prints `→ Next: run purlin:build. 1 rule has no test.` Path 5.
7. **`--dry-run`.** `docs/raising-the-gate-and-upgrading.md`: "Add `--dry-run` to print every
   file init would write or edit and write none of them." It asked `write .purlin/config.json
   [Y/n]:` and printed `wrote .purlin/config.json`. Nothing was in fact written. Paths 3, 4, 6.
8. **The counts.** `docs/dashboard.md`: "`Passing`, `Strong` and `Signed` count levels reached,
   so a signed rule is counted in all three". The dashboard does that (Passing 3, Strong 3,
   Signed 3). The terminal counts each rule once: `Passing 0 · Strong 0 · Signed 3`. Paths 4, 6.
9. **The hover on the gate count.** `docs/dashboard.md` says the box `4 of 10 rules meet the
   gate` has a hover that says "how many of those need their tests only, an audit too or a
   signature too". When the count is 0 the hover is empty. Path 6.
10. **The description.** `docs/specs-and-anchors.md` says of `> Description:` that "The
    dashboard displays it". It appears nowhere on the dashboard. Path 6.
11. **What setup writes.** `docs/getting-started.md`: "an empty `specs/`". Setup also writes
    `specs/_anchors/`. All seven paths.
12. **The sample output.** `docs/getting-started.md` shows `Running the pytest suite.`; with a
    command typed by hand the product prints `Running the tests suite.` Paths 1, 7. The sample
    also lacks a blank line the product prints. Paths 1, 4, 6.

## 3. Where the docs were silent

1. **How to run a command anywhere but inside Claude Code.** No page says. No page names the
   setup script. `docs/running-and-evidence.md` names the run script and none of its flags;
   `--help` answers `purlin: unknown argument --help.` and a usage line. Every agent listed the
   file names under `scripts/` and guessed. All guessed right. Status has no script a person can
   run; paths 4, 5 and 6 used the plugin's MCP tool.
2. **What makes a Python project one that setup recognises.** Only
   `references/supported_frameworks.md` says, which `docs/index.md` links. Paths 1, 5 and 7 read
   that one page. Guesses (an empty `conftest.py`, an empty `pytest.ini`) were right.
3. **What to answer to `Where does that command write its report?`** Guessed from another page;
   right. Path 5 answered with the sentence `A JUnit XML file` and setup took it as a path.
4. **An allowed signers file, and making a key at all.** Paths 4 and 6 guessed; right.
5. **When to commit the spec, the settings and the comments.** No page says. Every path met it.
6. **With tests already written, which way in.** `docs/getting-started.md` sends an existing
   codebase to `purlin:spec-from-code` and also says "Tests you already have, or new ones".
   Path 3 took the typed way; it worked. `purlin:spec-from-code` was not run.
7. **Whether several tests may carry one rule's comment**, and where the comment goes on a
   decorated or parametrized test. Path 3 guessed; every placement worked.
8. **The comment in JavaScript.** The README shows only `#`. `docs/getting-started.md` has `//`.
9. **Writing a proof by hand.** The docs give `purlin:spec`. Path 4 wrote the section by hand
   from `docs/specs-and-anchors.md`; it parsed the first time.
10. **What the signed tag is named.** The docs say the version is from `VERSION` "or the
    `version` in `.purlin/config.json`". That value is Purlin's own version, which setup stamps,
    so a new project's first tag is `signed/0.10.0`. Paths 4, 6.
11. **Leaving.** The removal text does not mention the marketplace entry in
    `.claude/settings.json` or uninstalling the plugin. The `.gitignore` block has no first or
    last line that marks it. Path 7.
12. **A deleted settings file; a typo in the comment.** Neither is described. Path 5.
13. **Which word wins, `stale` or `waiting`.** Path 6.

## 4. Where the product was unclear

1. **Signed, and not counted.** `3 signed` then `No tag`, no reason in the terminal. The
   dashboard and the gate check give the reason `the signing commit is not signed`, which is not
   so: it was signed and this machine could not verify it. Status then says `→ Next: run
   purlin:sign. 3 rules are waiting for a person.`, which loops. Paths 4, 6.
2. **One rule, three answers.** A rule with one passing test and one skipped test that carries
   its comment: the run prints `Evidence is missing` and exits 1, and also `3 of 3 rules meet the
   gate passed.` and `→ Next: nothing is outstanding at gate passed.`; the evidence file says
   `"RULE-3": "not run"`; `.purlin/tests.md` counts it under "No test". Paths 2, 3, 5.
3. **Which rule.** `1 rule has a failing test.` and `1 rule has no test.` never name the rule.
   Paths 3, 5.
4. **The next step points the wrong way.** `→ Next: run purlin:build` for a mistyped feature
   name, for tests that exist and only lack the comment, and for a deleted settings file. Paths
   3, 5.
5. **Typos in the comment.** `# purln:`, `# purlin:cart` and `# Purlin:` give no message. A
   comment naming a rule no spec has is counted in `Markers: 4 tied to a test, 0 not tied.` and
   the fix line says `Remove the comment, or write the proof it names.` when it names a rule.
   Paths 2, 3, 5.
6. **The settings file deleted.** The run said `No test suite: .purlin/config.json names no
   tests`, though the file is not there; it wrote three `"no test"` entries over committed
   passing evidence; it exited 0. Status, in the same state, said it correctly. Path 5.
7. **A deleted test.** Deleting an untracked test file: `Nothing to run`, exit 0, evidence still
   citing the file (path 2). Deleting a whole test file: exit 1 with pytest's `no tests ran` and
   no sentence from Purlin (path 5).
8. **"since".** `code changed since 5ea7291` when 5ea7291 is still the latest commit; the
   evidence commit `purlin: evidence at 8b5ca9b` holds evidence that names `508f44d`, `"dirty":
   true`. Paths 1, 2, 4, 5.
9. **The evidence package names a commit from before the proofs existed** and drops `dirty`.
   Path 4.
10. **Setup's summary.** `Mutation testing is off: no engine breaks tests code, so the AI audit
    alone judges test strength.` at a gate with no audit; `Suites tests.`; `Git host not read
    from a remote.` beside `"ci": "github"` in the settings. Paths 1, 2, 3, 4, 5, 6, 7.
11. **The dashboard.** Before a spec exists the empty page says to run status, and status writes
    nothing and says to run init. At the gate `strong` with no proofs, `0 of 3 rules meet the
    gate` and every tile and filter reads 0. The Passing and Strong tiles are amber when every
    rule meets the gate. Hovers: `minimum strength 0%` with breaking off; `1 need their tests
    only`; Proofs `0` with `every proof has a test`. `n/a` in the Strong column is not
    explained. At 390 pixels a test's name breaks over two lines. Paths 4, 6.
12. **Small.** The echoed command lacks its quotes (`$ bash -c python3 -m pytest ...`). Vitest's
    colour codes are printed raw. Under piped input a prompt's default prints at the start of
    the next question's line. `gate: 3 rules across 1 features.` `wrote .gitignore` twice.

## 5. Where Purlin touched more than it promised

The README: "A settings file and the specs you write: `.purlin/config.json`,
`.purlin/evidence/`, `specs/`, a block in `.gitignore`, and an ignored copy of the dashboard
page." And: "Nothing committed unless you ask", "Nothing installed in your test suite".

| Created or changed | By | In git | In the README's list |
|---|---|---|---|
| `.purlin/config.json` | setup, each raise of the gate | yours to commit | yes |
| `.purlin/evidence/README.md` | setup | yours to commit | yes |
| `.purlin/evidence/local/<feature>.json` | a run | committed with `--commit` | yes |
| `.purlin/evidence/package/<version>.json` | signing | committed, signed | yes |
| `.purlin/tests.md` | a run | committed with `--commit` | no; `docs/getting-started.md` names it |
| `.purlin/report-data.js` | status, a run | ignored | no |
| `.purlin/runtime/reports/*`, `.purlin/runtime/run.log` | a run | ignored | no |
| `purlin-report.html` | setup | ignored | yes |
| `specs/` | setup | empty | yes |
| `specs/_anchors/` | setup | empty | no |
| `specs/<area>/<feature>.signatures/*.json` | signing | committed, signed | no |
| `.gitignore`, 12 lines added | setup | yours to commit | yes |
| `setup.cfg` or a block in `pyproject.toml`, a `mutants/` ignore line | setup, breaking on | yours to commit | no |
| `.claude/settings.json`, the marketplace entry | the install | committed | no; only under "Install from a checkout" |
| The plugin, enabled for the user in every project | the install | outside the project | no |
| Commits `purlin: evidence at <sha>`, `sign(<feature>): ...`; the tag `signed/<version>` | a run with `--commit`, signing | | other pages |

The two other promises held in every path: nothing was committed without `--commit` or
signing, and nothing was installed in a test suite. No hook, no workflow file and no git
setting was written by Purlin in any path. Path 6 counts `specs/_anchors/` as inside the listed
`specs/`; the other paths count it as not listed.

## 6. What worked well

- **The run.** Once the test command was right, every line the README and
  `docs/getting-started.md` quote came out word for word: the table, `Tests: 3 of 3 rules
  pass.`, `gate passed met: 3 of 3 rules`, the failing case with exit 1, `Nothing to run: ...`,
  `code changed since <sha>`. All seven paths. Runs took 0.5 to 1.3 seconds.
- **One comment, any language.** Vitest was found with nothing asked; `//` comments tied inside
  nested `describe` blocks and above `it.each`. In Python, on class methods and above or below
  a decorator. Twenty existing tests came under Purlin with 20 comment lines added, 0 lines
  changed, 0 deleted.
- **A failing test** shows the suite's own output, then the table, then exit 1.
- **A comment whose test is gone** fails loudly, as documented.
- **Setup** lists every file it wrote, commits nothing, and says `kept` for every file when run
  again.
- **Raising the gate** asked one question each time, changed one setting, and gave the right
  next step each time.
- **The audit** ran unattended: 3 rules in about 10 seconds, and a second run skipped all three.
- **Signing**, once git could verify: the walk matched the docs, and the tag and the package
  came in one step. The package exported again was the same, byte for byte.
- **The dashboard** agreed with the terminal on every rule's word and on the gate count at
  every stage, opened from disk with no error, did not scroll sideways at 390 or 1500 pixels.
- **Leaving.** The documented steps returned `.gitignore` byte for byte and the tests ran as
  before.
- **An in-tree `.venv`** with 141 test files did no harm.

## 7. Questions for the owner

Most basic first. Each: what the thing is for, the question, the options.

**1. Running a command without Claude Code.** Purlin's commands are typed inside a Claude Code
session. Underneath, each is a script that also runs in a plain terminal or a build server. The
docs never say whether a person may do that. Which is it?
- Claude Code only. The docs say so plainly. A build server uses only the check Purlin sets up
  for it. Least to document and to keep stable.
- Both, documented. Each command's page gives its terminal form. The script names become a
  promise you keep across releases.
- One terminal command, `purlin <command>`, that stands for all of them. New code; the simplest
  thing to document.

**2. Finding the test framework at setup.** Setup looks at the project to work out how its
tests are run, so the user is not asked. A plain Python project with test files and no settings
file for pytest is not recognised, and the user is asked two questions the docs do not explain.
- Recognise more: test files named the usual way count. Fewer users are asked; a wrong guess
  becomes possible.
- Leave it, and say in the first page what setup looks for and what to answer when asked.
- Remove the guessing: setup always asks one question, with the usual command for each
  framework offered. Less code, one more question for everyone.

**3. Setup that ends with no way to run the tests.** A user who takes the defaults, or answers
in the order the docs give, can end setup with no test command or a wrong one. Setup still says
the next step is to write a spec.
- Setup tries the command once and refuses to finish if it cannot run.
- Setup finishes, says plainly that no tests can run yet, and names the fix as the next step.
- Leave it.

**4. The question about breaking code on purpose.** At the higher levels Purlin can change the
code on purpose to see whether the tests notice. Setup asks whether to turn that on even at the
lowest level, where it never runs.
- Ask only when the level is one where it runs.
- Remove the question from setup; it is turned on later by raising the gate.
- Keep it, and list every setup question in the docs in the order asked.

**5. What a test run's failure means.** A build server reads a run's exit code to decide
whether to stop. Today a run fails only when a test fails or a comment is wrong. It succeeds
when a rule has no test, when a test was deleted, and when nothing ran at all. One table in the
docs says otherwise.
- A run fails whenever the gate is not met. Matches the table. A project part-way to its gate
  fails every run until it arrives.
- A run fails when a test fails, a comment is wrong, or nothing could run. The gate is judged
  only by the separate check. The table is corrected.
- Leave the product; correct the table.

**6. A missing settings file.** With the settings file gone, a run wrote "no test" over good
committed results and reported success.
- Stop, write nothing, say the file is missing and how to restore it.
- Leave it.

**7. Saving results before the work they describe.** A run can commit its results. It will do
so when the spec and the tests those results describe are not yet committed, so a teammate
receives results for a spec they cannot see, naming a commit that does not hold it.
- Refuse until the spec, the tests and the settings are committed.
- Warn and carry on.
- Commit them together in the one commit.
- Remove the saving of results from the run; results are committed by hand like any file.

**8. A signature that does not count.** A signature counts only when the machine can verify
whose it is. Git needs one more piece of setup for that than the docs give, and without it
Purlin says "signed", then "not signed", and gives no reason.
- Add the missing step to the docs and to what setup prints, check for it before the walk, and
  say "signed, but this machine cannot verify it" where that is the case.
- Purlin writes that piece of setup itself, from the people the project already names as
  signers.
- A signature made on this machine counts without being verified here; verification happens on
  the build server only.

**9. The name of the signed tag.** When every rule is signed, Purlin tags the version. In a
project with no version file of its own the tag takes Purlin's version, so a new project's
first release is tagged 0.10.0.
- Refuse to tag until the project states its own version.
- Ask for the version at signing.
- Remove the version from the tag: name it by date or by commit.

**10. Signed results from a run on uncommitted work.** The evidence package names the commit
the tests ran on. If the tests ran on uncommitted changes, the package names the commit before
them and does not say so.
- A signed tag needs a run on a clean tree.
- The package says the run was on uncommitted work.
- Leave it.

**11. One count, two meanings.** The dashboard counts a signed rule as passing, strong and
signed. The terminal counts it once, as signed. The same project reads "Passing 3" in one and
"Passing 0" in the other.
- Both count levels reached.
- Both count each rule once, at its highest level.
- Remove the count line from the terminal; the table above it already shows each feature.

**12. A rule with one test that passed and one that did not run.** A rule may have several
tests. If one passes and another is skipped, the terminal and the dashboard say the rule
passed, the results file says it did not run, and the run fails.
- The rule has not passed until every test that names it ran and passed. All four places agree.
- The rule passed; a skipped test is a warning only, and the run succeeds.
- Leave it.

**13. Mistakes in the comment.** The comment above a test is how Purlin ties it to a rule. A
near miss in the first word is ignored without a message. A comment naming a rule that does not
exist is counted as tied.
- Look for near misses and say what was probably meant; count a comment that names nothing as
  not tied.
- Document the exact form and leave the product.

**14. Which rule, and what next.** When a rule fails or has no test, the run gives a count and
not the rule, and its last line sends the user to have the code and tests written even when the
fix is a typo or a missing comment.
- Name each rule, and choose the next step from the cause.
- Name each rule; leave the next step.
- Remove the next-step line from a run.

**15. The rehearsal of setup.** Setup can be run so that it only says what it would do. It asks
a question and says "wrote" for files it did not write.
- It asks nothing and says "would write".
- Remove the rehearsal.

**16. Rules that block with nowhere to see them.** At the second level, a rule with no proof
blocks the gate, and no box or filter on the dashboard counts it.
- Give it a box and a filter.
- Count it under "untested".
- Leave it. (This meets your request about the header box and the queue; asked with it.)

**17. The description of a feature.** A spec may carry one line describing its feature. The
docs say the dashboard shows it. It does not.
- Show it.
- Remove the line from the spec format.
- Correct the docs only.

**18. The empty folder for anchors.** Setup creates an empty folder for anchors, which are
rules shared between features. A project that never uses them keeps the empty folder.
- Create it when the first anchor is written.
- Keep it and list it in the README.

**19. Leaving.** The removal text covers what is in the project. It does not cover the line the
install added to the project's Claude settings, or the plugin itself.
- Add both to the removal text, and mark the first and last line of the `.gitignore` block.
- Add both to the removal text only.

Not questions, corrected without a decision once you say to go: the README's list of what
Purlin touches; the `//` form in the README; the sample output; the example test that still
passes when the code adds where it should multiply; the unquoted echoed command; the raw colour
codes; `1 features`; `1 need`; the double space; the hovers in section 4.11.

## 8. Docs or product

Each finding was checked against the code on `main` at `6731b7ed0`, the specs, the skills, and the plans (`three-levels.md` decisions 31 to 59, `morning-list.md`, `handoff.md`). File paths are relative to the repository root. "Per rule" means the code does exactly what the named rule asks, so changing the behaviour means changing that rule. "Per decision" means changing it reopens that decision.

### Section 2: where the docs were wrong

| Finding | Verdict | Evidence |
|---|---|---|
| 2.1 Setup finds the test framework | docs | Confirmed. `scripts/mcp/purlin/frameworks.py:175-178` detects pytest only from `conftest.py`, `pytest.ini` or `[tool.pytest` in `pyproject.toml`; test file names count for nothing. This is exactly what `references/supported_frameworks.md:16` says, and scaffold RULE-7 names the frameworks. `docs/getting-started.md` claims more than the product does. Recognising `test_*.py` would be new product work (question 2). |
| 2.2 The questions setup asks | docs | Confirmed. `scripts/init/scaffold.py:685-697` asks in this order: the gate, the test command (only when nothing is detected), mutation, trust. That order is per scaffold RULE-1, the module docstring and `skills/init/SKILL.md` "The questions". RULE-45 asks the mutation question wherever an engine exists, at any gate, per decision 35 ("`purlin:init` asks once whether to turn it on"). "No breaks run under `passed`" is also true (run_script RULE-45). The getting-started sentence is the fault. Asking about test strength at `passed` sits against decision 50 ("Five words at `passed`"); that is question 4. |
| 2.3 Taking the default | both | Confirmed. The default answer to `COMMAND_QUESTION` is empty, so `asked_suite` prints `NO_COMMAND` and writes no suite (`scaffold.py:584-589`). `next_step` (`scaffold.py:533-542`) returns `→ Next: run purlin:spec ...` because no spec exists yet. Both are per scaffold RULE-6 ("with no command given it gets no suite and is told where to add one") and RULE-34. The docs send the reader to that default. The product, per its rules, ends on a next step that ignores the missing suite (question 3). |
| 2.4 Signing setup | both | Confirmed. The three commands come from `SIGNING_SETUP` (`scripts/review/sign.py:150-154`), printed by init (`scaffold.py:649-655`) and by `signing_help` (`sign.py:608`); the docs copy them. A signature counts only when `git log -1 --format=%G?` prints `G` (`scripts/mcp/purlin/signatures.py:189-196`). An SSH-signed commit with no `gpg.ssh.allowedSignersFile` does not print `G`, so it reads `the signing commit is not signed` (`signatures.py:236-237`). Requiring verification is per decisions 32 and 48. The missing step is missing in the product's printed setup and in the docs alike. |
| 2.5 The exit code table | docs | Confirmed. `scripts/run/purlin_run.py:849-850` and `:889` exit on the tests alone. That is per run_script RULE-11 ("The run exits on the tests, whatever the gate line says") and the morning list, "later pieces": "`purlin:test` exits on the tests alone". The table at `docs/running-and-evidence.md:195-201` sits under the `## purlin:audit` heading and still overstates `--audit`: per RULE-48, a rule waiting only on a signature does not exit 1, and at `passed` nothing does. Decision 28's "exits 1 when not met" was replaced by that later choice, which is recorded in the morning list and not as a numbered decision. |
| 2.6 The next step for a rule with no test | docs | Confirmed. `scripts/mcp/purlin/status.py:314-317` sends a rule with no proof and no test to `purlin:build` at `passed`. That is the morning list's choice under "The sweep": "At `passed`, a rule with neither proof nor test is sent to `purlin:build`". Decision 51 makes `purlin:build` the step that marks an existing test. `docs/how-purlin-works.md:144` is stale. |
| 2.7 `--dry-run` | product | Confirmed. `Plan.allowed` asks `[Y/n]` whenever a config already exists, dry run or not (`scaffold.py:287-294`, `:369-373`), and `Plan.write` notes `wrote` after skipping the write (`scaffold.py:336-349`). RULE-30 ("prints the plan and writes nothing") holds. RULE-18 ("each path it says it wrote is on disk afterwards") does not, and neither does the skill's own sentence "print every file init would write". |
| 2.8 The counts | product | Confirmed. The terminal line is `board.bucket_line` over exclusive buckets (`status.py:156`, `board.py:214-224`), per states RULE-23 ("A rule's bucket is exactly one of ...") and RULE-37. The dashboard adds them up (`scripts/report/src/app.js:28-35`), per purlin_report RULE-8 and decision 24 ("The tiles read cumulative levels"). `docs/dashboard.md` describes the dashboard correctly. The two surfaces follow two rules that disagree (question 11). |
| 2.9 The hover on the gate count | docs | Confirmed. `app.js:501-503` keeps one line per level that has a met rule, so the hover is empty at 0. That is per purlin_report RULE-7 ("one line per level that has a rule meeting the gate"). `docs/dashboard.md` describes more than the rule gives. |
| 2.10 The description | docs | Confirmed. The payload carries `description` (`scripts/mcp/purlin/payload.py:316`), but no file under `scripts/report/src/` reads it, and no rule in `specs/dashboard/purlin_report.md` asks for it. The wrong claim is also in `references/formats/spec_format.md:45` and `:51`. Showing it would be new product work (question 17). |
| 2.11 What setup writes | docs | Confirmed. `scaffold.py:708` creates `specs/_anchors/`, which `skills/init/SKILL.md` "What init writes" names. `docs/getting-started.md` leaves it out (question 18). |
| 2.12 The sample output | docs | Confirmed. A suite typed in by hand is named `tests` (`scaffold.py:595`, per scaffold RULE-6), so the product prints `Running the tests suite.`; the sample assumes pytest was detected. The blank line comes from `purlin_run.py:816-818`, and `docs/running-and-evidence.md:55` shows it. `docs/getting-started.md` does not. |

### Section 3: where the docs were silent

| Finding | Verdict | Evidence |
|---|---|---|
| 3.1 How to run a command anywhere but inside Claude Code | neither (the check's own doing) | `README.md:7`: "Purlin is a Claude Code plugin"; decision 51: "Product, QA and developers all work in Claude Code on a checkout"; decision 28: "At `passed` a person runs no script". Status has no script: `scripts/mcp/purlin/status.py` has no `__main__` and `skills/status/SKILL.md` calls the MCP tool `sync_status`. `--help` is refused at `purlin_run.py:233` (argparse handles it in `scaffold.py`); that is a small product point. Whether the terminal forms become a promise is question 1. |
| 3.2 What makes a Python project one that setup recognises | docs | Same code as 2.1. The rule lives only in `references/supported_frameworks.md:16`. |
| 3.3 What to answer to `Where does that command write its report?` | both | Confirmed. `format_for` (`scaffold.py:571-581`) reads any answer that is not empty, `-`, `.trx` or a trailing `/` as a JUnit path, so a sentence is stored as a path. No page explains the question. |
| 3.4 An allowed signers file, and making a key at all | both | Same code as 2.4. `signing_configured` (`sign.py:593-595`) checks `user.signingkey` alone, and no line the product prints mentions key generation or an allowed signers file. |
| 3.5 When to commit the spec, the settings and the comments | docs | Inside Claude Code, `purlin:spec` commits the spec (`skills/spec/SKILL.md:28`, `:166`) and `purlin:build` commits the code and tests (`skills/build/SKILL.md:107-117`); the check ran neither skill. The ten-minute path in `docs/getting-started.md` has the reader type the spec and comments by hand and never says to commit them, and init commits nothing (scaffold docstring). The product does not look: `commit_local` (`scripts/run/evidence.py:543-554`) commits evidence whatever `specs/` holds (question 7). |
| 3.6 With tests already written, which way in | docs | Not a code question. Both routes exist, and decision 51 has `purlin:build` "look first for an existing test". No page says which to take. |
| 3.7 Whether several tests may carry one rule's comment, and where the comment goes | docs | Supported and specified: reports RULE-4 ("blank lines, decorators, attributes and other comments may sit between them") and RULE-11 (parametrised cases). Decision 51: "A test may carry several". No page in `docs/` says so. |
| 3.8 The comment in JavaScript | docs | The README shows `#` only. Section 7 of the report already lists this as a fix that needs no decision. |
| 3.9 Writing a proof by hand | docs | The format is in `references/formats/spec_format.md`; the docs point only at `purlin:spec`. The hand-written section parsed, so the product did its part. |
| 3.10 What the signed tag is named | product | Confirmed. `project_version` (`sign.py:460-474`) falls back to the config's `version`, which init stamps with Purlin's own `VERSION` (`scaffold.py:403`, per scaffold RULE-5 and PROOF-5). The fallback is written into signatures RULE-45 ("falling back to the config's") and `scripts/export/package.py:14`. Decision 31 says only "the `VERSION` file's value", and `specs/export/package.md` RULE-1 names the `VERSION` file alone. See answer b. |
| 3.11 Leaving | both | Confirmed. `templates/gitignore.purlin` opens with a comment and has no closing line that marks the block's end. The marketplace entry is written by `claude plugin marketplace add --scope project`, which is Claude Code, not Purlin. The removal text names neither (question 19). |
| 3.12 A deleted settings file; a typo in the comment | docs | Neither case is described. What the product does is in 4.5 and 4.6. |
| 3.13 Which word wins, `stale` or `waiting` | docs | `stale` wins. `scripts/mcp/purlin/states.py:203-211` turns only an `unsigned` cell with no current signature into `waiting`, and `:213` keeps `stale` over `names no files`. No page says so. |

### Section 4: where the product was unclear

| Finding | Verdict | Evidence |
|---|---|---|
| 4.1 Signed, and not counted | product | Confirmed. `No tag: %d of %d rules do not meet the gate %s.` (`sign.py:131`, printed in `tag_if_met`) gives no reason. `the signing commit is not signed` (`signatures.py:237`) is printed for any `%G?` other than `G`, so "cannot verify here" and "not signed" read the same. The rule stays in the queue, so status's `next_step` keeps naming `purlin:sign` (`status.py`, the `person` branch). Only the requirement itself is settled (decisions 32 and 48); the message and the loop are not. |
| 4.2 One rule, three answers | product | Confirmed. The evidence word for a rule marked by its own id needs every test to pass (`evidence.py:185-194`, per evidence_writer RULE-15). The passed cell reads `proof_results`, which drops everything but `pass` and `fail` (`scripts/mcp/purlin/evidence.py:238-255`, read at `states.py:526-527`), so one pass is enough. The run exits 1 per run_script RULE-8, and `tests.md` counts the rule under "No test" per evidence_writer RULE-8. Each place follows its own rule, and the rules disagree (question 12). |
| 4.3 Which rule | product | Confirmed. `_said` counts and names no rule (`status.py:314-331`). The exact text is written into run_script PROOF-5 and states PROOF-79. No decision covers it. |
| 4.4 The next step points the wrong way | product | Confirmed for a mistyped feature name and for a deleted settings file: both land in `status.py:314-317`. For "tests that exist and only lack the comment", `purlin:build` is the step decision 51 names ("looks first for an existing test ... offers to add the marker"), and `skills/build/SKILL.md:45-47` does it. That part is settled. |
| 4.5 Typos in the comment | product | `_COMMENT_RE` (`scripts/mcp/purlin/markers.py:62-65`) needs lower-case `purlin:` followed by whitespace. `# purln:` and `# Purlin:` are not `purlin:` comments, so staying silent is per reports RULE-1. `# purlin:cart` is also silent, which contradicts RULE-1 ("a `purlin:` comment of any other shape is reported"); the morning list's P9 notes that a marker "needs a space after `purlin:`". A marker naming nothing fails the run per decision 56 and reports RULE-19. The `tied` count (`purlin_run.py:804-807`) counts markers followed by a test, whatever they name. `FIX_ONE` (`scripts/run/reports.py:61`) is the one sentence RULE-19 fixes, whatever the marker names. |
| 4.6 The settings file deleted | product | Confirmed. With no config, `read_suites` returns none and `NO_SUITES` (`purlin_run.py:165`, `:758-759`) says the file "names no tests". `write_sections` (`purlin_run.py:867`) still writes every selected feature, and the exit code is 0 because no suite ran (`:849-850`). No rule covers a missing file (question 6). |
| 4.7 A deleted test | product | Confirmed. The fingerprint leaves out files git does not track (`scripts/mcp/purlin/fingerprint.py:11-14`), so deleting an untracked test changes nothing and the run says `Nothing to run`. For a whole test file deleted, pytest's own "no tests ran" exit counts as failed tests (`purlin_run.py:442`), and only the suite's output is printed (`:785-786`). |
| 4.8 "since" | product | The first half is per rule: run_script RULE-20 names "the commit the run started on", which is HEAD while the change is uncommitted. The second half is confirmed: `_nothing_to_run` commits the evidence an earlier run wrote (per RULE-57) under a subject naming today's HEAD (`purlin_run.py:976-979`). The evidence keeps its own `commit` and `dirty` (evidence_writer RULE-7). |
| 4.9 The evidence package names a commit from before the proofs existed | product | Per decision 55: "The package names the commit its evidence was taken at". An audit reruns no tests, so that commit is the last test run's. `dirty` is not a field in `references/formats/package_format.md`, and `package.py:364` copies `commit` alone (question 10). |
| 4.10 Setup's summary | product | Confirmed. `NO_ENGINE` (`scaffold.py:149-150`) is printed at every gate and names the suite `tests`, which is against decision 50 ("no word of a higher level" at `passed`). `Suites tests.` is per scaffold RULE-6. `"ci": "github"` comes from `templates/config.json`; `write_config` overwrites it only when a host is read (`scaffold.py:408-409`). |
| 4.11 The dashboard | product | Confirmed. With no spec, `report_data.refresh` writes nothing (`scripts/mcp/purlin/report_data.py:43-44`), the page says to run `purlin:status` (`app.js:558`), and status says to run init or spec (`status.py:36-38`). `no_proof` is not in `COUNTED_FLAGS` (`states.py:99`), so no tile counts those rules (question 16). The tile tone is `pass` only when the bucket equals the gate (`app.js:141-148`), and that clashes with decision 24's cumulative tiles. `minStrength()` turns null into 0 (`app.js:123`). `need` has no singular form (`app.js:501`). `every proof has a test` shows at 0 proofs (`scripts/report/src/board.js:141`). The line break at 390 pixels was not confirmed; it needs the screenshot. |
| 4.12 Small | product, except one | Confirmed. The echo is `' '.join(command)` (`purlin_run.py:341`). The Vitest command sets no colour option (`frameworks.py:39-40`). `%d rules across %d features.` has no singular form (`scripts/ci/gate_check.py:256`). `wrote .gitignore` is noted twice when mutation testing is on (`scaffold.py:435` then `:478`). The prompt's default showing at the start of the next line is the check's own doing: `input()` prints its prompt with no newline when answers are piped (`scaffold.py:282`). |

### Section 5: rows the README does not list

| Row | Verdict | Evidence |
|---|---|---|
| `.purlin/tests.md` | docs | Written by every run (evidence_writer RULE-8) and committed with `--commit` (RULE-10). Decision 40: "`.purlin/tests.md`, the summary table, stays." |
| `.purlin/report-data.js` | docs | Written by `report_data.refresh` and kept out of git by the block. Decision 50: `purlin:test`, `purlin:audit`, `purlin:sign` and `purlin:status` "each refresh the data as they finish". |
| `.purlin/runtime/reports/*`, `.purlin/runtime/run.log` | docs | Written by a run (reports RULE-17, run_script RULE-15) and kept out of git by `templates/gitignore.purlin`. |
| `specs/_anchors/` | docs | `scaffold.py:708`, named in the init skill (question 18). |
| `specs/<area>/<feature>.signatures/*.json` | docs | Written by `purlin:sign`, documented in `docs/review-and-signing.md` and `references/formats/signature_format.md`. |
| `setup.cfg` or a block in `pyproject.toml`, a `mutants/` line | docs | Written only when mutation testing is on (scaffold RULE-39, RULE-40). The block configures mutmut; it is not the test suite. |
| `.claude/settings.json`, the marketplace entry | docs | Written by Claude Code's `claude plugin marketplace add --scope project`, not by Purlin. |
| The plugin, enabled for the user in every project | docs | Claude Code's install scope, not Purlin. |
| The commits and the tag | docs | Each is something the person asked for: `--commit` (evidence_writer RULE-10) or `purlin:sign` (signatures RULE-45). This agrees with "Nothing committed unless you ask"; the README's list just does not name them. |

### Answers

**a. The terminal, and what the skills do.** No page, decision or rule makes a person's terminal a supported way in. The README calls Purlin "a Claude Code plugin". Decision 51: "Product, QA and developers all work in Claude Code on a checkout". Decision 28: "At `passed` a person runs no script". The paths under `scripts/` are stable because the CI workflow and the skills call them (CLAUDE.md, "Tool folder separation"), not because a person types them.

Inside Claude Code the skills run the same scripts through `${CLAUDE_PLUGIN_ROOT}`:
- `purlin:init` runs `scaffold.py --project-root . --gate <level>`.
- `purlin:test` and `purlin:audit` run `purlin_run.py`.
- `purlin:sign` runs `sign.py`.
- `purlin:status` calls the MCP tool `sync_status`, and has no script.

What the skills handle:
- **The question order.** `skills/init/SKILL.md` lists it as gate, test command and report, mutation, trust, which matches the code. A model following the skill knows the order that `docs/getting-started.md` gets wrong.
- **Answers the skill cannot pass.** The skill's only flags are `--gate`, `--mutation`, `--yes`, `--add` and `--dry-run`. There is no flag for the test command, the report path or trust. `Console` takes the default at end of input (`scaffold.py:267-285`). So if the Bash tool gives the script no input, which I could not confirm here, an undetected project ends with no suite and `trust: local`. `handoff.md` records one hang under piped output.
- **Committing the spec before the evidence.** `purlin:spec` commits the spec by itself (`skills/spec/SKILL.md:28`, `:166`), and `purlin:build` commits the code and tests (`skills/build/SKILL.md:107-117`). Nothing in `purlin:test` checks it. The documented ten-minute path skips both skills.

**b. The version in the tag's name.** `sign.py:460-480` uses the `VERSION` file at the project root, else `version` in `.purlin/config.json`, else `unversioned`; `--release` overrides. Init writes the config's `version` from the plugin's own `VERSION` (`scaffold.py:403`; scaffold RULE-5, PROOF-5: "`version` equals the `VERSION` file"). So a project with no `VERSION` is tagged with Purlin's version.

The fallback is written into `specs/review/signatures.md` RULE-45 ("taking the version from the `VERSION` file at the project root and falling back to the config's") and into `package.py:14`. Decision 31 says only "(the `VERSION` file's value; `--release <name>` overrides)", and `specs/export/package.md` RULE-1 and RULE-2 name the `VERSION` file alone. The fallback therefore rests on a rule, not on a decision.

**c. Verifying an SSH signature.**
- **What counts.** `commit_is_signed` (`signatures.py:189-196`) runs `git log -1 --format=%G? -- <path>` on the signature file and counts only `G`. Anything else gives `the signing commit is not signed` (`signatures.py:236-237`), and git's own reason is not shown. The requirement is decisions 32 and 48: a signature counts "in a commit that is cryptographically signed and verifies".
- **What is checked before the walk.** `signing_configured` (`sign.py:593-595`, called at `:961`) checks only that `user.signingkey` is set.
- **What is not checked.** Nothing reads `gpg.ssh.allowedSignersFile`, and nothing runs `git verify-commit` after the walk's `git commit -S` (`sign.py`, `_commit`). The walk prints `Walked ... 3 signed` (`sign.py:850`) and then the reasonless `No tag` line (`sign.py:131`).

**d. Exit codes of a test run.**
- **`--test`.** run_script RULE-11: "The run exits on the tests, whatever the gate line says: 1 where a test failed, evidence is missing or a marker names nothing a spec has, 0 otherwise". The code matches (`purlin_run.py:849-850`, `:889`). A run that selects nothing exits 1 only where the evidence holds a failing test (RULE-57, `:988`).
- **`--audit`.** RULE-48: exit 1 above `passed` when a rule is short of its passed or strong cell. A rule waiting only on a signature does not exit 1, and at `passed` nothing the audit finds does (`:1160-1166`). A rule the model could not be reached for exits 1 above `passed` (RULE-52).
- **What the docs say.** The prose at `docs/running-and-evidence.md:98-100`, `docs/how-purlin-works.md:124` and `skills/test/SKILL.md` match RULE-11. The table at `docs/running-and-evidence.md:195-201` does not: "or the gate is not met" is wrong for `purlin:test` and overstates `purlin:audit`. Line 96 of the same page also misquotes the met line as `gate <gate>: <n> of <rules>`; the product prints `gate <gate> met: <n> of <rules> rules`.
- **Where it was settled.** Decision 28 said `purlin:test` "exits 1 when not met". The morning list, "later pieces", replaced that: "`purlin:test` exits on the tests alone".

**e. The count line against the tiles.**
- **The terminal line.** It is states RULE-37 ("counts the buckets the gate reaches in the tiles' own words and order") over RULE-23's exclusive buckets ("A rule's bucket is exactly one of ..."), rendered by `board.bucket_line` (`status.py:156`, `board.py:214-224`).
- **The dashboard tiles.** They are purlin_report RULE-8 ("The three level tiles are cumulative ... added up in the page from the payload's exclusive buckets"), which carries out decision 24 ("The tiles read cumulative levels: ... `Strong` (strong cell met, signed rules included)").
- **The gap.** No decision covers the terminal line. RULE-37 borrows the tiles' words and not their way of counting.

### Settled by an owner's decision or a recorded choice

- 2.2: the question order is scaffold RULE-1. The mutation question at every gate that has an engine is decision 35 and scaffold RULE-45, and it sits against decision 50.
- 2.5: `purlin:test` exits on the tests alone. This is run_script RULE-11 and the morning list's "later pieces" choice, which replaced decision 28's "exits 1 when not met".
- 2.6 and part of 4.4: `purlin:build` is the step for a rule with no test at `passed` (morning list, "The sweep") and the step that marks an existing test (decision 51).
- 2.8: cumulative tiles on the dashboard, decision 24.
- 4.1: a signature counts only in a commit that verifies, decisions 32 and 48. The message and the loop are not settled.
- 4.5: a marker naming a feature, proof or rule no spec has fails the run, decision 56. A space is required after `purlin:`, morning list P9.
- 4.9: the package names the commit its evidence was taken at, decision 55.
- 4.10: at `passed` no word of a higher level appears, decision 50. The summary line breaks this decision.
- 3.10: decision 31 names the `VERSION` file only. The fallback to the config's version is in signatures RULE-45 and in no decision.

## 9. What the owner decided

Every question of section 7 was put to the owner on 2026-09-28. The answers are decisions 60
to 72 in `three-levels.md`.
