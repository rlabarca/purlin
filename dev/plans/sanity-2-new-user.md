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
