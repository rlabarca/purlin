# Lane `docs`, round 2

Built on `lane/d115-docs` from round 1's merged line, locally, not pushed. Specs: `purlin_docs`
(3 rules, 4 proofs) and `install` (5 rules, 5 proofs).

## Tests

`python -m pytest dev/test_purlin_docs.py dev/test_install.py -q`

| When | Passed | Failed | Skipped |
|---|---|---|---|
| Before the first change (`dev/test_purlin_docs.py` alone; `dev/test_install.py` did not exist) | 10 | 1 | 0 |
| After the last change | 8 | 1 | 0 |

- No test skipped for a missing tool. The real `claude` is on this Mac, so all five tests of
  `install` ran.
- **Waiting on `words`: `purlin_docs PROOF-17`.** The pages link to
  `references/evidence_and_signoff.md`, which `words` writes. On this branch alone the test
  names 4 links to it (in `how-purlin-works.md`, `index.md`, `running-and-evidence.md`,
  `sign-off.md`). Read against a copy of this branch's `docs/` and `README.md` beside the
  `references/` of `lane/d115-words` at `02f983d2c`, every relative link and every `#` part
  resolves: 0 broken.
- The install test made 2 runs with the model, the limit set for building it. Both passed.

## Section 4's row

| | Gone | Reworded | To add |
|---|---|---|---|
| As found (appendix A's script printed `13 gone, 1 reworded, 0 right as they stand.`: the 10 of the row and the 3 sample comments inside the file) | 10 + 3 | 1 | 8 |
| As left | 0 | 0 | 0 |

Last line the script prints for `dev/test_purlin_docs.py dev/test_install.py`:
`0 gone, 0 reworded, 9 right as they stand.`

Proof comments: `purlin: purlin_docs PROOF-` 4 of 4 (17, 21, 22, 24); `purlin: install PROOF-`
5 of 5 (1 to 5).

## Reworded comments

- `dev/test_purlin_docs.py:84 purlin_docs PROOF-17 fixed`: it read four named pages, the
  README among them; it now reads every `docs/*.md` page, follows each link from the page's
  own folder, and its own samples show a missing file, a missing heading and a link that climbs
  out of `docs/`.

## Tests deleted

Each named a proof no spec holds, and showed none of the four that are left.

- `TestCommandTable::test_each_row_carries_the_references_purpose_sentence`
- `TestCommandTable::test_every_command_of_the_reference_has_a_row`
- `TestQuotedLines::test_setups_lines_are_printed_by_setup`
- `TestQuotedLines::test_the_first_runs_lines_are_printed_by_it`
- `TestQuotedLines::test_the_confirmed_runs_lines_are_printed_by_it`
- `TestQuotedLines::test_the_commit_runs_lines_are_printed_by_it`
- `TestQuotedLines::test_the_failing_runs_lines_are_printed_by_it`
- `TestQuotedLines::test_the_no_tool_line_is_printed_by_that_run`
- `TestQuotedLines::test_every_quote_names_a_run_and_every_block_a_language`
- `TestReleasePage::test_the_table_of_tags_names_both_tags_and_their_commands`

With them went the sample project the file built, its helpers and the `<!-- sample: -->`
comments on the pages.

## The pages as they stand

| Page | What it is |
|---|---|
| `docs/how-purlin-works.md` | rewritten: the two facts, the loop, four words, the runner on first need, the questions |
| `docs/getting-started.md` | rewritten: the install as three shell lines under step 1, one setup question, the status's opening lines, the commit of the results |
| `docs/specs-and-anchors.md` | edited: a spec ahead of its code, hand checks reading `checked at sign-off`, a test comment to correct, an anchor's rule with nothing to check, the source checked and not pulled |
| `docs/running-and-evidence.md` | rewritten: the kinds of work and which block, the audit's three steps, which results count for a sign-off, the runner written by the first `purlin:test --remote` |
| `docs/working-together.md` | rewritten: one drift view, three things that collide, the paragraph of `purlin_docs RULE-16` |
| `docs/sign-off.md` | new, from `review-and-signing.md`, `qa-guide.md` and `regulated-workflow.md` |
| `docs/upgrading.md` | renamed from `raising-the-gate-and-upgrading.md`, the upgrade from 0.9.5 alone |
| `docs/dashboard.md` | rewritten to `purlin_report`'s rules: the header line, the two boxes, the information lines, `Back to the board` |
| `docs/audit.md` | the owner's page, changed in six places: the finding's line as K9 gives it, the two bullets on what waits and what is kept, a bullet for decision 117, one table cell, and the spot tests reference listed under `Sources` so that every link of the text is there (`PROOF-22`) |
| `docs/index.md` | rewritten: nine guides and the references |
| `README.md` | rewritten: `## Install` with the shell lines, the two facts, the command table |

Deleted: `review-and-signing.md`, `qa-guide.md`, `regulated-workflow.md`, `team-workflow.md`,
`spec-from-code.md`. `docs/images/*.png` are not touched; integration retakes them.

The coordinator's two notes after the lane started are applied: the README's purpose sentences
and command cells equal those of `references/purlin_commands.md` on `lane/d115-words`, with no
`purlin:export` row; and decision 117 is in the pages (the sign-off refuses for a rule with no
test and for files changed and not committed; `strong` means the model's part of the audit
ran; the dashboard's Audit panel shows the explanation and the planted bug a test missed).

## Lines a person reads that this lane chose

| Line | Where |
|---|---|
| `claude plugin install purlin@purlin --scope project`, as the third install line, after `cd my-project` and `claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project` | `README.md` under `Install`, `docs/getting-started.md` step 1. The pages gave the install as `/plugin install purlin@purlin` typed inside Claude Code, which no test can run; `install PROOF-2` runs "the pages' commands" |
| `Start Claude Code in the project, or run /reload-plugins in a session that is already open, and the purlin: commands are there.` | the same two places |
| `claude is not installed here` | the skip reason of `dev/test_install.py`, as section 6 gives it |
| `Nine guides, and the references behind them.` | `docs/index.md`, first line |
| The headings `Four words`, `The two facts`, `Run from a checkout`, `When the tests are met`, `The hand-off`, `What it refuses`, `A key to sign with`, `What is recorded`, `Beside a regulated system`, `Which results count for a sign-off`, `A comment to correct`, `A rule with nothing to check`, `More than one checkout`, `Any screen, both themes`, `When it refuses`, `After the upgrade` | the pages |
| The table of `Left to do` lines with a column `Blocks Tests: met` | `docs/running-and-evidence.md` |
| The sample hand check, `The error messages follow the brand voice guide`, and the sample audit output `login RULE-2   weak` with `PROOF-2: the test still passes when src/auth.py:31 reads "return True"` | `docs/sign-off.md`, `docs/running-and-evidence.md`: examples in the shapes K8 and K9 fix |
| `PROOF-1: the test still passes when src/age.py:12 reads "return minutes + 60"` | `docs/audit.md`, in place of `sample_age PROOF-1: the test still passes when src/age.py:12 adds an hour.`, which is not the shape K9 prints |
| The prompt `List every slash command or skill available to you whose name starts with purlin: and nothing else. Answer with the names only, one per line. Use no tool.` | sent to the model by `install PROOF-4`'s test; no person reads it |

The paragraph of `purlin_docs RULE-16` is section 6's, word for word, with `purlin:status` in
backticks.

## Differences from section 3's contracts

None in code: this lane owns no code under `scripts/`. The pages quote K6, K8, K9 and K11 as
written. Three places where the pages follow something other than the plan's text:

- `sign.py`'s refusal for uncommitted work is quoted as K8's `NO_SIGNOFF_WORK`; decision 117
  words it "commit them or set them aside, then run `purlin:sign` again". The page quotes K8 and
  says "commit them or set them aside" beside it. If the line changes, `docs/sign-off.md`'s
  table follows.
- The dashboard page says the Audit panel shows the model's explanation and the planted bug a
  test missed (`purlin_report RULE-39`, decision 117), which the payload of round 1 does not
  carry yet.
- Setup's printed lines are shown as `scaffold`'s proofs give them (`wrote`, `copied`, the one
  question, `Committed <sha7>, the files setup wrote:`). Its closing lines are no longer a rule
  (decision 112), so the pages quote none.

## Left unbuilt, left open, and failures elsewhere

1. **`install PROOF-4` under a person's login, for the owner.** The install is made under a
   configuration folder of its own (`CLAUDE_CONFIG_DIR`), so `PROOF-5` holds. That folder is
   not logged in: on this Mac `claude auth status` under it reads `loggedIn: false`, and the
   same with `HOME` moved. So the one prompt runs in one of two ways:
   - with `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` in the environment: under the
     install's own folder, in the project, exactly as the proof words it;
   - with the person's login alone, which is what ran here: under the person's login, in the
     project, with `--plugin-dir <the folder the install wrote>` and `--setting-sources user`,
     so the project's settings are not read and the person's plugins and marketplaces are not
     written. The skills the model names then come from the installed copy, loaded for that
     session, and not through the project's enabled-plugin setting, which `PROOF-2` shows
     without a model.
   The second way is this lane's choice where no contract gives one. The alternative is to skip
   `PROOF-4` where the environment carries no credential of its own.
2. **A trace under the person's `~/.claude/projects/`.** A prompt under the person's login
   leaves an empty folder named after the test's project there, though the call passes
   `--no-session-persistence`. The test removes it, and only where it holds no file. The
   person's `settings.json`, `installed_plugins.json` and `known_marketplaces.json` had the
   same checksums before and after both runs.
3. **`skills/export/` is still on this branch**, so the install test counted 11 skills and the
   model named all 11. With `words` merged it is 10; the test reads the folders, so it follows.
4. **K15's greps over this lane's files find nothing but the audit page's citations**: the
   titles `Are Mutants a Valid Substitute for Real Faults in Software Testing?`,
   `Practical Mutation Testing at Scale`, `Mutation-Guided LLM-based Test Generation at Meta`
   and `LLMorpheus: Mutation Testing using Large Language Models`, and the address
   `.../mutation-effectiveness-fse2014.pdf`. They are the papers `purlin_docs PROOF-21` names.
   A grep for `mutation` that ignores case will name those five lines of `docs/audit.md`.
5. **`--ignore=mutants`** stands in the suggested pytest command the pages quote, as the run
   prints it (`run_script PROOF-126`).
6. **No test holds the README's command table or the pages' quoted output any more**:
   `purlin_docs` lost those proofs. The quoted run output on `getting-started.md`,
   `running-and-evidence.md` and the README was taken from the sample project the old test file
   built, run on round 1's merged line before that file was rewritten.
7. **`dev/run_tests.sh` and `dev/suites.py` are integration's**: `dev/test_install.py` is
   collected by a plain `pytest dev/` until integration holds it out and wires `--install`.
8. **`references/commit_conventions.md` on this branch** still names
   `chore(init): set up Purlin at the gate <gate>`; the pages give `chore(init): set up Purlin`
   (`scaffold RULE-68`). It is `words`' file.

## Broken on purpose, once each

- The README's third install line, with `--scope project` taken off: `install PROOF-1` failed,
  the two pages no longer giving the same lines.
- The word `worktree` taken out of `docs/working-together.md`: `purlin_docs PROOF-24` failed.
  Restored with `git checkout -- docs/working-together.md`.

## What the session cost

Not readable from inside the session. The install test's two prompts went to the smallest
model, `--model haiku`, one prompt each, with no MCP server started.
