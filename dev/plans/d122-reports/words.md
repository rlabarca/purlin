# Lane `words`: report for decisions 122 and 123

Branch `lane/d122-words`, from `main` at `e02c9b4f5`. Nothing was pushed, tagged, signed or
published.

## What was built

- **The ten skills and `agents/purlin.md`** take the words of d122 sections 6.8 and 6.9, less
  `skills/audit/SKILL.md`, which is lane `audit`'s.
- **The docs**: `README.md`, `docs/dashboard.md`, `docs/getting-started.md`,
  `docs/how-purlin-works.md`, `docs/running-and-evidence.md`, `docs/sign-off.md`,
  `docs/specs-and-anchors.md`, `docs/working-together.md`.
- **The references**: `drift_criteria.md`, `evidence_and_signoff.md`, `glossary.md`,
  `purlin_commands.md`, `spec_quality_guide.md`, `supported_frameworks.md`.
- **`RELEASE_NOTES.md`**, 0.10.0, and two lines of `dev/plans/deck/build_deck.py`.
- **Two specs and their tests**: `purlin_agent` RULE-24 and PROOF-55; `skill_drift` RULE-15 and
  PROOF-46.
- `CLAUDE.md` is not changed, as the plan says.

Answer B to d122's question 2 is applied: no page of this lane says `one model call`. Each
says the model is asked for a small bug for each proof and for its reading. Every page that
says how the bug is chosen now says what d123 section 3 says.

## Rules and proofs, word for word

`specs/instructions/purlin_agent.md`. `> Highest-Rule:` 23, now 24. `> Highest-Proof:` 54, now
55. Its description's `four checks` reads `five checks`.

Added:

- RULE-24: Every skill that names `sync_status` names the tool as a session lists it, `mcp__plugin_purlin_purlin__sync_status`, and the script that prints the same status, `scripts/run/purlin_status.py`
- PROOF-55 (RULE-24): Each `SKILL.md` holding `sync_status` holds `mcp__plugin_purlin_purlin__sync_status` and `scripts/run/purlin_status.py`; the same check on a copy of the build skill with the script's line taken out lists `build does not name scripts/run/purlin_status.py`

`specs/skills/skill_drift.md`. `> Highest-Rule:` 15 and `> Highest-Proof:` 46, both unchanged.

Reworded:

- RULE-15: The skill names the commands `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:anchor sync` and `git fetch`, and the files `references/drift_criteria.md` and `scripts/run/purlin_drift.py`
- PROOF-46 (RULE-15): The drift skill names `purlin:drift`, `purlin:spec`, `purlin:build`, `purlin:anchor sync`, `git fetch`, `references/drift_criteria.md` and `scripts/run/purlin_drift.py`

None deleted.

## Seen failing first

Written and run before any skill changed:

- `dev/test_purlin_agent.py::test_every_skill_naming_the_status_names_the_tool_and_the_script`
  (PROOF-55): failed, no skill named the tool's full name or the script.
- `dev/test_skill_drift.py::test_the_drift_skill_names_its_commands_and_its_criteria` (PROOF-46):
  failed with `['scripts/run/purlin_drift.py']`.
- `dev/test_skill_drift.py::test_a_copy_without_the_spec_command_is_reported` (PROOF-43): failed
  with the extra line `drift does not name scripts/run/purlin_drift.py`.

The two drift tests pass now. PROOF-55 waits on lane `audit`, below.

## Tests waiting on another lane

`bash dev/run_tests.sh --fast` on this branch alone ends
`4 failed, 832 passed, 9 skipped in 820.19s (0:13:40)`. The four:

| Test | Waits on |
|---|---|
| `purlin_agent` PROOF-51, `test_every_path_a_skill_or_the_agent_definition_names_exists` | lane `run`: `scripts/run/purlin_status.py` and `scripts/run/purlin_drift.py` |
| `purlin_agent` PROOF-52, `test_every_flag_a_skill_passes_is_one_its_script_takes` | lane `collision`: `renumber.py --yes` |
| `purlin_agent` PROOF-55, `test_every_skill_naming_the_status_names_the_tool_and_the_script` | lane `audit`: `skills/audit/SKILL.md`, line 16, still reads ``when `sync_status` opens with a pending-migrations advisory``. d122 section 6.8 gives it as `when the status opens with a pending-migrations advisory`. Until that line changes the test lists `audit does not name mcp__plugin_purlin_purlin__sync_status` and `audit does not name scripts/run/purlin_status.py` |
| `dev/test_collaboration.py::test_three_people_reach_a_signed_version` | lane `collision`: on `main` the test looks for ``Call `sync_status` ``, `drift(project_root=` and ``run the same command without `--dry-run` `` in the skills. The lane's own copy of the test already looks for the new words |

Checked on a throwaway merge of this branch with `lane/d122-run` and `lane/d122-collision`, in
a scratch worktree since removed: PROOF-51, PROOF-52 and the collaboration test pass there, and
PROOF-55 alone fails, on the audit skill's line. Each phrase the collision lane's
`dev/test_collaboration.py` looks for in a skill is in the skill as written here.

The deck: `build_deck.py`, `check_deck.py` and `check_overlap.py` were run with `DECK_ROOT` in
the scratch folder. Every slide's content ends at 920 and no slide has a hit.

## Lines a person reads that this lane chose

The plan gave no words for these.

Skills:

- `spec`, "Renumbering": ``Where `purlin:drift`, the status, `purlin:build` or this skill finds
  a number written twice``. The plan's "After a merge conflict" took the skill's only
  `purlin:drift` out, and `skill_spec` RULE-32 holds that the skill names it.
- `spec`, "When you are done": `write the file, check it as step 7 says, commit it`.
- `spec`, Step 1, after the status block: `Read the state of the feature, if it already has one.`
- `status`, Step 1: `In a worktree the top folder is the worktree's own, since each checkout has
  its own results, status and dashboard.`
- `status`, Step 2: ``then `· <k> by hand`, `· <k> partial` and `· <k> failing` where not zero;
  `by hand` counts the rules checked at sign-off``, and ``as `<strong> of <n>`: of the rules that
  pass their tests and have a tested proof, the ones it found strong``.
- `status`, "With a name": the example's hand check reads
  `RULE-5  checked at sign-off  checked at sign-off   PROOF-6  a hand check`;
  `Print the lines the status holds.`; `get the status as Step 1 says`.
- `drift`, Step 1: `` `project_root` is the top folder of the git checkout you are working in.``
- `build`: `With no name, read the state from the status.`
- `test`, Step 2, second row: ``**Stop and ask**. On yes, write it as the `tests` setting with
  the `purlin_config` tool, and run Step 1 again``.
- `test`, Step 4: the passed cell's words gain `checked at sign-off`. Step 5: ``**Stop and ask**
  whether to start it`` and ``**Stop and ask**, in these words:``. Step 6: `the lines of the
  status`.
- `anchor`: `` `references/commit_conventions.md` holds the prefix.`` and ``in the characters a
  spec's name may hold, which `references/formats/spec_format.md` lists``.
- `spec-from-code`, step 3: `Show the list. **Stop and ask** whether it is right. Merge, split
  and rename until they say it is.`
- `sign`, Step 2: ``**Stop and ask** the person for the version and whether to write it to a
  `VERSION` file``; `**Stop and ask** before you delete a tag.`; `The wrong-key line comes after
  the commit: the script reads the key that signed it, and takes the commit back where it is not
  the key this checkout names.`
- `sign`, Step 5: `` `sign` is what the person typed at the last question.``, and ``Where `sign`
  is not the signer's address it signs nothing and ends on`` the `NOT_SIGNED_ANSWERS` line.
- `sign`, Step 6: `Where the person typed their address the script makes one signed commit`.
- `sign`, Step 7, one row beyond the plan's: `` `Nothing was signed: "sign" in` `` with
  `→ Ask the person the last question again, then run: purlin:sign --answers <file>`.
- `agents/purlin.md`, the audit sentence: `has an AI write for each proof the one small bug that
  proof's test is most likely to miss, plants it in a copy of the project to see whether the
  test catches it`. Its rename section reads `then get the status`.

Docs:

- `running-and-evidence.md`: the table row `Plants one bug per changed proof, aimed past its
  test`; step 2's heading `The model is asked for a small bug for each proof and for its
  reading.` with d123 section 3's sentences under it; `A finding is one line. A bug that
  survived adds two, the second the AI's own claim:`; `An answer that names no case of the
  proof, or whose change touches only a comment, is not planted, and the audit says so under the
  rule:`; the flow's box `the spot tests, then one planted bug per changed proof, aimed past its
  test, into the same file`; `each planted bug with its aim and the case the AI says it breaks`;
  the first run's question and `Wrote the tests setting` line; the passed cell's words.
- `getting-started.md`: `The agent shows you the difference, then asks ... On your yes the run
  writes the setting and runs the tests.`; `The status follows, as after every run:` with the
  status block under `Nothing to run`; the audit paragraph in d123's words.
- `dashboard.md`: `` `Passing` counts the rules that pass their tests. ... A rule checked at
  sign-off is not counted.``; `` `Passing` is complete once every rule passes or is checked at
  sign-off.``; the case `A rule checked by hand alone.`; `A bug that survived is followed by the
  case the AI says it breaks`.
- `how-purlin-works.md`: the `strong`, `weak` and hand check answers.
- `sign-off.md`: the wrong-key row's `Why` cell; `Where the rule or the proof was reworded
  since, a line above the note says so:`; the stop's `Results` now reads `No test runs for this
  rule: you check it here.`; `The agent asks the last question as`; `Any other value ends on`.
- `specs-and-anchors.md`: `A tag stands at the end of the proof line, after the text.`
- `README.md`: the audit paragraph in d123's words.

References:

- `purlin_commands.md`: the whole of "The tools and their scripts" and "Stops" beyond the
  lines d122 sections 5.3 and 6.2 give. "Stops" lists four questions, setup's among them; the
  release notes say three, the plan's count of the new ones.
- `evidence_and_signoff.md`: `What they require is that every rule that has a test passes it on
  the committed evidence`; the summary's `<a>`, `counting the rules that pass their tests and
  have a tested proof`; `A note is compared with the wording through the package of the version
  it was signed at.`
- `glossary.md`: the **planted bug**, **finding** and audit entries, and the chain's last
  sentence.
- `spec_quality_guide.md`: the `written twice` row's fix; the `weak` row's sentence on the AI's
  claim; `A rule checked by hand alone reads checked at sign-off in both cells until a sign-off
  notes it.`
- `supported_frameworks.md`: `Any other answer, or no answer, writes nothing. --write-tests
  writes it without the question, which is how purlin:test goes on once you have said yes.`
- `drift_criteria.md`: the sections "A merge in progress" and "A proof that follows a moved
  rule", and the sentence on Purlin's own folder.

## Calls this lane made that the plan did not

1. **The ten purposes.** `references/purlin_commands.md` is the one home of each skill's
   one-liner, and the README's table carries it. Both take the ten new descriptions, the audit's
   among them, so that lane `audit`'s `description` and these two pages say one thing.
2. **`> Criteria-Version:` of `drift_criteria.md` goes from 13 to 14.** The view gains a key,
   `merge_in_progress`, and an entry gains `follows`. The release notes name 14.
3. **The release notes' format numbers** read what d122 section 7 leaves: spec 24, anchor 12,
   evidence 12, signature 16, package 12, marker 5, the dashboard's data at schema 16. The
   coordinator raises evidence and package by one for decision 123 at integration, and that line
   with them.
4. **The deck.** The `manual` slide has no row on what a hand check reads; the words are in its
   notes, and the notes take the plan's phrase. The `together` slide's `purlin:drift` row takes
   the collision sentence. The `audit` slide is untouched.
5. **`purlin_agent` PROOF-55's check** is `status_unnamed` in `dev/skill_checks.py`, beside the
   other four.
6. **The spec skill's "Renumbering"** is replaced from `Otherwise ask exactly:` to the end of
   the section, as the plan says. The sentence on a comment on another branch went with it; "After
   a merge conflict" still says to tell the person whose line moved.
7. **The examples `19 pass their tests, 1 has a hand check`** in the sign skill and
   `docs/sign-off.md` stand: they hold where the hand check sits beside tested proofs.
8. **The order of `by hand`, `partial` and `failing`** in a `Tests` cell is written as the plan's
   example gives it, `· <k> by hand` first. Lane `surfaces` decides it in `board.tests_cell`.

## Left, or waiting

- The four tests above.
- `skills/audit/SKILL.md` line 16, lane `audit`'s.
- The release notes' two format numbers for decision 123, at integration.
- `Plain language reaches every command` stands in `references/purlin_commands.md`, the agent
  definition's "Routing" and three skills' "Usage". The plan changes only
  `docs/working-together.md` for finding 11, so they were left.
- The deck is not published.
