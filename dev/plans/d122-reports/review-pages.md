# Sanity check of the pages, local `main` at `4edfb0e16`

Read only. Nothing in the repository was changed, no test was run, nothing under `.purlin/` was
written. Every page named in the brief was read in full; the code was read and grepped, never run.
"Certain" means the two texts, or the text and the code's own line, were both read and disagree.
"Likely" means the code was read but not run, or the source is outside what could be checked here.

Sorted by seriousness: A wrong instruction an agent would follow, B wrong fact, C stale word,
D style.

## A. A wrong instruction an agent or a person would follow

**A1. `references/drift_criteria.md:48-49`** (certain)
- As it stands: "`lines` holds every sentence to print after the one naming the range, in the
  order of the table below."
- Contradicts: `scripts/mcp/purlin/drift.py:912`, `'lines': ([rng['line']] + ([MERGE_LINE] if
  merging else []) + lines)`: the range sentence is the first entry of `lines`. Also
  `skills/drift/SKILL.md:56`, "Print `lines` as they come, one per line, the first naming the
  range", and the same file's line 73, "the view's second, right after the one naming the range".
- Effect: an agent that follows the reference prints `since.line` and then `lines`, so the range
  line twice.

**A2. `references/drift_criteria.md:173-175`** (certain)
- As it stands: "A script run on the command line takes `--project-root`; without it,
  `PURLIN_PROJECT_ROOT` answers where it names a folder that exists, else the climb from the
  working directory to the first `.purlin/` folder."
- Contradicts the code for most scripts: `scripts/run/purlin_run.py:262` and `:1151`,
  `scripts/review/sign.py:1206`, `scripts/review/ai_audit.py:675`, `scripts/spec/renumber.py:681`,
  `scripts/run/purlin_status.py` and `scripts/run/purlin_drift.py` (`found.get('--project-root',
  '.')`) all default to the working directory and read no environment variable. Only
  `scripts/anchor/upstream.py:543`, `scripts/mcp/purlin/wording.py:305` and the server
  (`server.py:264`) call `config_engine.find_project_root` / `resolve_project_root`.
- Both new scripts' own docstrings say "`--project-root` defaults to the working directory".

**A3. `docs/specs-and-anchors.md:417`** (certain)
- As it stands: "`--name` gives it another, in letters, digits and `_`."
- Contradicts: `scripts/anchor/upstream.py:279`, `not added. --name takes letters, digits, _ and -
  alone.`; `skills/anchor/SKILL.md:68-69`, "in the characters a spec's name may hold";
  `references/formats/spec_format.md:17-20`; the same page's line 25, "A name holds letters,
  digits, `_` and `-`." Decision 122, section 6.8, changed the skill and missed this page.

**A4. `docs/running-and-evidence.md:537`** (a judgment call)
- As it stands: `git clone --depth 1 --branch v0.10.0 https://github.com/rlabarca/purlin`, with
  "Use the tag of the Purlin version in your `.purlin/config.json`".
- `CLAUDE.md`, "Releasing a new version", writes and pushes only `signed/<version>`. The
  repository's `v*` tags stop at `v0.9.5`. A project that copies the workflow gets a clone that
  fails unless a `v0.10.0` tag is also pushed at release. Either the release steps gain the `v`
  tag or the example names `signed/0.10.0`.

**A5. `RELEASE_NOTES.md:225`** (certain)
- As it stands: "`--yes` answers yes to every question."
- Contradicts: the same section's line 235, "It asks before it removes a workflow that names a
  proof file, and `--yes` removes none"; `docs/upgrading.md:106-107`; `skills/init/SKILL.md:92`;
  `scripts/init/update.py:543`, `if args.yes or not _confirm(WORKFLOW_QUESTION % rel, False):`
  keeps the workflow.

## B. A wrong fact

**B1. Where the status reads `signed`: `docs/sign-off.md:311-313`,
`references/evidence_and_signoff.md:29-36` and `:209-211`** (certain that the pages disagree;
the code's logic was not run)
- As they stand: "The status reads `signed` only where the tag names a commit that holds the
  package and a sign-off of it counts."; "**The sign-off** reads one of three things, from the
  newest `signed/*` tag on `HEAD` or an ancestor of it"; "`not signed`: no `signed/*` tag on
  `HEAD` or behind it has a sign-off that counts".
- Contradicts: `references/formats/signature_format.md:155-165`, "only where a sign-off of that
  version counts, and one of two things holds", the second being "This checkout holds no tag
  `signed/<version>` ... and `HEAD` holds the version's package". Both pages then add the
  `git fetch --tags` paragraph (`docs/sign-off.md:315-317`, `evidence_and_signoff.md:216-217`),
  which contradicts their own "only where the tag names". `RELEASE_NOTES.md:30` has it right:
  "only where a sign-off counts". Decision 122, section 2.6, is the change.

**B2. `references/formats/evidence_format.md:56`, the example** (certain, from the page itself)
- As it stands: `"rules": {"RULE-1": "passed", "RULE-2": "no test"}`, while lines 60-62 give
  RULE-2's one proof, PROOF-2, a tied test and the result `nothing to check`.
- Contradicts the page's own table, lines 130-138: `no test` holds where a proof "has no test
  tied to it"; "A proof that reads `nothing to check` counts as passed in an anchor's section
  and as not run in any other." `login` is a feature (`specs/auth/login.md`), so RULE-2 reads
  `not run`.

**B3. The Kiele figure: `dev/plans/deck/build_deck.py:171-172` against `docs/audit.md:132`**
(certain that the two differ)
- Deck notes: "a bug aimed past the tests found a real gap 87.8 percent of the time, against
  12.2 percent".
- Audit page, quoting the abstract: "verified fault rates of 87.7% (HumanEval)".
- `dev/plans/audit-research.md:175-176` explains it: the abstract says 87.7%, section 4.1 and
  Figure 4 say 87.8% (144 of 164). Each is in the paper; the deck and the page should give one.
- Same slide, line 162: "A bug aimed past the test finds 7 times the gaps". That is HumanEval
  with the best model (87.8 / 12.2). On MBPP it is 79.1 against 23.0, about 3.4 times
  (`audit-research.md:169-170`). A judgment call whether "7 times" may stand unqualified.

**B4. `docs/audit.md:191-193`** (likely)
- As it stands: "Their 21 judges gave the same verdict on a rerun (0.943) and agreed only
  moderately with people (0.376 to 0.511 once chance is removed)."
- `dev/plans/audit-research.md:1077` and `:1086-1087`, `:1105`: 21 models were run as judges; the
  0.943 is the mean "across the 16 judges" of the consistency cohort (Table 6 lists 17). Section
  5, line 136, gives 0.943 with no count. The page ties 0.943 to 21 judges.

**B5. `docs/audit.md:291-292`** (likely; outside the "what Purlin does" section)
- As it stands: "an AI's planted bugs stood for 76.47% of them and a rule tool's for 44.15%
  (Wang et al., abstract)".
- `dev/plans/audit-research.md:137` (section 5) gives the measured comparison as "real-bug
  detection 85.0% for a model's bugs against about 42% to 44% for rule tools". 76.47 is nowhere
  in the research file; 44.15 is (`:1293`, the abstract's figure, which the paper contradicts
  with 41.64). The 76.47% needs checking against the paper.

**B6. The model cannot be reached: `references/review_criteria.md:31-32` and `:311`,
`skills/audit/SKILL.md:98-99`, `docs/audit.md:54-56`** (likely)
- As they stand: "a rule that passed them is written `spot-checked`"; "A rule on which a spot
  test fired is still written `weak`; any other is written `spot-checked`."; "Every other rule
  reads `spot-checked`".
- `scripts/review/audit_run.py:336-340` and `:361-369`: a proof whose bug is kept from an earlier
  audit still enters `breaks`, so a rule with a kept `caught` reads `strong` and one with a kept
  `survived` reads `weak` with the model unreachable. The module's own docstring, lines 26-28:
  "the spot tests and the bugs kept from earlier audits set its verdict". The printed line allows
  for it: its count of rules "spot-checked alone" is left out at zero.

**B7. Which rules the audit's share counts: `skills/status/SKILL.md:71-72`,
`docs/dashboard.md:88-89` and `:104`, `references/evidence_and_signoff.md:63-64`,
`references/review_criteria.md:332-334`, `references/formats/package_format.md:113`** (likely)
- As they stand: the status's and the dashboard's `Strong` count is "of the rules that pass
  their tests and have a tested proof"; `review_criteria.md`: "a rule with a hand check counted
  where it also has a tested proof".
- `scripts/mcp/purlin/states.py:780-785`: a rule with a `@manual` proof beside tested proofs
  whose audit is `strong`, or that has no entry, reads `checked at sign-off` in its strong cell.
  `scripts/mcp/purlin/summary.py:203-217` counts only the five audit words, so that rule is in
  no count on the status, the dashboard or the package.
- `scripts/review/audit_run.py:497-519` counts the same rule by its verdict in the audit's own
  last line. So for a project with such a rule the audit's last line and the status sentence
  printed under it give different totals, and `package_format.md:113` says both things in one
  cell ("the rules that pass their tests and have a tested proof" and "neither is a rule checked
  by hand, whose `strong` status reads `checked at sign-off`").

**B8. The walk's overview example: `docs/sign-off.md:122-126`, `skills/sign/SKILL.md:49-53`,
`references/formats/signature_format.md:46-49`** (likely)
- As they stand: "19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check." and
  "The audit: 17 strong, 1 weak, 1 spot-checked."
- `scripts/review/sign.py:696-699` leaves a rule checked by hand alone out of `passing`
  (`signature_format.md:81` says so), and `docs/sign-off.md:154-163` shows that hand check as
  `login RULE-2` with one `@manual` proof and "No test runs for this rule". That gives 18 pass and
  at most 18 audited. Decision 122's own line is "10 rules on Linux/Unix: 9 pass their tests, 1
  has a hand check." The numbers hold only if the hand check sits beside a tested proof and is the
  weak or the spot-checked rule.

**B9. When a run exits 1: `docs/how-purlin-works.md:122-129`, `docs/running-and-evidence.md:189`
and `:375`** (likely)
- "In any of these cases" and the exit table leave out a spec that writes a number twice or
  holds a conflict line: `scripts/run/purlin_run.py:1350`, `references/purlin_commands.md:186`.
- "An audit exits 1 when a test it ran failed or did not run, and 0 whatever it found" leaves out
  the stop where a project file changed: `skills/audit/SKILL.md:70-72`,
  `references/purlin_commands.md:186`.

**B10. `references/purlin_commands.md:85`, "Four questions are asked by the scripts themselves",
against `RELEASE_NOTES.md:46`, "Three questions"** (a judgment call)
- The three are the new ones and the fourth is setup's, so the two can both stand. Neither counts
  `scripts/init/update.py:1069` (`Apply <id>, which will ...? [y/N]`) and `:543` (`Remove <path>?
  [y/N]`), which the script also asks itself.

**B11. `references/review_criteria.md:221-224`, "Not made"** (likely, small)
- The list reads as whole and leaves out three reasons the code gives:
  `targeted_break.NO_DIFFERENCE` ("the change leaves %s as it was"), `OUTSIDE` and `NO_FILE`
  (`scripts/review/targeted_break.py:72-77`). `docs/audit.md:203-204` names the first.

**B12. `references/evidence_and_signoff.md:23-25`** (likely, small)
- The kinds that keep the tests `not met` are listed without a slow proof to run, which the
  table at line 80 and `docs/how-purlin-works.md:141` both have as blocking.

**B13. `dev/plans/deck/build_deck.py:198`, "The run on the other platform uses purlin:test"**
(a judgment call)
- `docs/running-and-evidence.md:566` and `references/evidence_and_signoff.md:157-158`: it is
  `scripts/run/purlin_run.py --ci --commit`, "the run script `purlin:test` runs, in the form a
  pipeline uses".

**B14. `dev/plans/deck/build_deck.py:162` and `docs/audit.md:296`, "AI-written tests often check
what the code does, not what was asked", cited to Konstantinou et al.** (a judgment call)
- `dev/plans/audit-research.md:135`: what was measured is that a model shown buggy code more
  often rejects the right expected answer, by 8 to 9 points, one model. The page's body says so
  under the heading; the slide's closing line gives the claim and the citation alone. Decision
  123 reworded the same claim in `references/review_criteria.md` checks 4 and 6.

## C. A stale word

**C1. `scripts/anchor/upstream.py:25-26`, docstring** (certain)
- "It also refuses a `--name` that is not letters, digits and `_`". The same file's line 279
  prints `--name takes letters, digits, _ and - alone`.

**C2. A count of calls in code that ships: `scripts/review/ai_audit.py:21` ("One call per rule,
`MODEL_TIMEOUT` seconds each, `AUDIT_PARALLEL` calls at once") and
`scripts/review/audit_run.py:8` ("one model call per rule, four at once")** (a judgment call)
- Docstrings, printed nowhere. `dev/plans/d122-plan.md` section 2.9 and `d123-plan.md` keep the
  call as a mechanism. They are the only counts of model calls left under what ships.

**C3. Left on disk, not tracked** (certain)
- `.purlin/runtime/audit_run.json`, written 2026-10-01 21:24 by the audit before decision 122;
  nothing reads or writes it now and git ignores it. `scripts/run/mutation/` holds only
  `__pycache__` (`mutmut`, `stryker`, `stryker_net`, `none`), with no tracked file. Also
  `.purlin/runtime/last_sweep.json`, `test_run.json`, `refresh_digest.lock` and `proofs/`, which
  no script or test names.

**C4. The skill listing a session loads** (likely)
- This session's list of skills gives `purlin:audit` as "Run the tests, the heuristic spot tests,
  one model call per rule and one planted bug per proof", and older sentences for the other nine.
  `skills/audit/SKILL.md:3` in the checkout has the new one. The installed copy of the plugin is
  an earlier build.

**C5. `skills/sign/SKILL.md:8`, "on their yes adds their sign-off"; `references/commit_conventions.md:158`,
"A sign-off walk ended with yes"** (a judgment call)
- Through the agent the answer that signs is the typed address (`skills/sign/SKILL.md:144-147`,
  `sign.py:156-157`); `y` signs only at a terminal. `references/purlin_commands.md:176` says both.

**C6. `RELEASE_NOTES.md:254`, "After it, run `purlin:test`", against `docs/upgrading.md:121`,
"Run `purlin:test --all --commit`"** (a judgment call)

## D. Style

- `docs/how-purlin-works.md:155`: the question names four words and six bullets follow; the
  strong cell's `checked at sign-off` and `no proof` are on neither (`references/glossary.md:159`
  has all eight).
- `docs/dashboard.md:146`: "The `Strong` row reads `STRONG`, `WEAK`, `SPOT-CHECKED` or `OUT OF
  DATE`", while line 160 gives it `CHECKED AT SIGN-OFF`; lines 165 and 167 write a badge's word
  in lower case (`not run`, `passed`) beside upper case elsewhere.
- `docs/audit.md:210`: "Google plants one per changed line"; the research has "at most one
  mutant per line", in changed lines tests cover (`audit-research.md:759`).
- `references/purlin_commands.md:5-6`: "nothing repeats it in its own words", and the page's own
  Syntax block (lines 123-163) gives each command a second, shorter sentence.
- `CLAUDE.md:35-36`, step 1 of the format procedure, names five script folders and leaves out
  `scripts/spec/` (`renumber.py` reads and writes specs) and `scripts/init/`.

## What was checked and found right

1. **Cost and call counts.** No dollar figure, no "cost" of a model, no count of model calls in
   `README.md`, `docs/`, `skills/`, `agents/purlin.md`, `references/`, `CLAUDE.md`,
   `templates/`, the 0.10.0 release notes or the deck. "A cost" at `docs/specs-and-anchors.md:403`
   and `skills/anchor/SKILL.md:27` is about a second repository. C2 is the one remainder.
2. **The planted bug.** `REQUEST_BUGS` and `REPLY_PARTS` in `scripts/review/ai_audit.py:264-311`
   are decision 123's words. `AI_SAYS`, `NO_CASE`, `ONLY_COMMENT`, `CASE_LIMIT = 300` and
   `HASH_COMMENTS` match `references/review_criteria.md`. Every page that shows a surviving
   bug's finding shows the second line directly under it, word for word: `docs/audit.md:21-22`,
   `docs/running-and-evidence.md:342-343` and `:359-360`, `skills/audit/SKILL.md:82-83`,
   `references/review_criteria.md:215-216`, `references/spec_quality_guide.md:370`. Both refusal
   lines match the code. `.purlin/runtime/audit_run.json` is named on no page and in no script.
3. **Versions.** spec 24, anchor 12, marker 5, evidence 13, package 13, signature 16, drift
   criteria 14; `payload.SCHEMA_VERSION = 16` and `app.js` `SCHEMA = 16`; `RELEASE_NOTES.md:49-50`
   quotes all of them right. `purlin-evidence/2`, `purlin-package/4`, `purlin-signoff/1` match
   the code.
4. **Commands and flags.** Every flag a page names is parsed: `--write-tests`, `--arm-timeout`,
   `--ci`, `--audit`, `--test`, `--all`, `--feature`, `--commit` (`purlin_run.py`); `--show`,
   `--answers`, `--check`, `--version` (`sign.py`); `--yes`, `--dry-run` (`renumber.py`);
   `--spec` (`purlin_status.py`); `--since`, `--json` (`purlin_drift.py`); `--near-misses`
   (`markers.py`); `--file` (`wording.py`); `--yes`, `--update` (`scaffold.py`); `add --path
   --name`, `sync --all --check --json` (`upstream.py`). Each new flag is on a page. About 150
   quoted printed lines were matched against the scripts with split string literals joined; all
   are there. `Spec saved: <name>. Next: purlin:build <name>` is the spec skill's own line, by
   design.
5. **One word, one sentence.** The purpose sentence of all ten commands is identical in
   `README.md`, `references/purlin_commands.md` and each skill's `description`, and so is the
   syntax column. The words each cell can read agree between the glossary, `states.py`,
   `evidence_and_signoff.md`, `package_format.md` and the test skill.
6. **Removed things.** No remote runner, no `--remote`, no gate (but "Two facts, no gate." in
   the release notes), no mutation testing outside paper titles and quotes, no `not audited` for
   an unreachable model, no `passed` for a hand check nobody did, no "take only a yes".
7. **`dev/` and own `specs/` paths.** None in a prose line of a skill, the agent definition or a
   reference; no rule id of Purlin's own specs there either.
8. **Links.** Every relative link, anchor, backticked `file.md#anchor`, quoted section name and
   backticked repository path in `README.md`, `docs/`, `references/`, `skills/`, `agents/` and
   `CLAUDE.md` resolves. The broken ones are all in release notes older than 0.10.0.
9. **Emoji, first person, history.** No emoji and no glyph beyond the six allowed and the
   box-drawing rules. "We" appears only inside quotations and paper titles. 0.9.5 is named only
   where a page describes the upgrade.
10. **`docs/audit.md` against the research, sections 1 to 5.** The trial table (3, 3 / 3, 3 /
    3, 3 and 0, 0 / 1, 1 / 1, 4), the project (8 rules, 12 proofs, 12 tests, 3 weak, 9 sound),
    the model, two runs, the subtle weak test, the hidden request's survivor, the one idea behind
    the aimed survivors, 68% to 87% and 54% to 78%, 9, 49 and 7 of 65, 403, 105 and 9 of 517,
    5 of 430, 137 of 381 (36%), 61%, 0.47 to 0.96, 53.61% on 1,650 pairs, about 6%, 0.376 to
    0.511, 6,712 to 2,333, 28% to 59%, 14% to 36%, and 8 to 9 points all match. B4 and B5 are the
    two that do not.
