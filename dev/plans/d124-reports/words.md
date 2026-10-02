# Lane `words`, decision 124

Branch `lane/d124-words`, from `main` at `8bcad22e2`. Section 2 of `dev/plans/d124-plan.md`,
all of it but `references/review_criteria.md`. Nothing was pushed, tagged, signed, audited or
published.

## What was built, page by page

| Page | What changed |
|---|---|
| `skills/build/SKILL.md` | A new part, `Strengthening a weak rule`, between `Running them` and `Committing`: a spot test's finding, then the plan's five steps for a planted bug that survived. `When you are done` points at it. |
| `skills/audit/SKILL.md` | The `--settle` usage line; Step 1 says which arguments it takes; Step 2 gains three bullets, for the two printed lines and for `nothing to settle`; the two bullets on a surviving bug no longer tell a person to judge; Step 3's `weak` line is `→ Run: purlin:build <feature>` and nothing else. |
| `docs/audit.md` | `What to do with a finding` after `How it works`, the six bullets word for word, and a link to `Settling a finding`. Two bullets, word for word, under `What it does not do`. `On Purlin's own tests` after the trial. Four sentences that said a person judges a surviving bug now say a test run settles it. `Sources` lists the new link. |
| `docs/running-and-evidence.md` | The usage line; after the `Left to do` example, what `purlin:build` does for a weak rule and the two ways a settle ends. `and you judge it` removed. |
| `docs/how-purlin-works.md`, `docs/getting-started.md` | Where each says what `weak` means: `purlin:build` strengthens the test and settles the finding with a test run. `and you judge it` removed. |
| `README.md` | The audit paragraph gains one sentence; the command table's row gains the syntax. |
| `agents/purlin.md` | The core loop says a weak rule is `purlin:build`'s; one routing row. |
| `references/purlin_commands.md` | The syntax in the table's row and in the help block; the row says `purlin:build` runs it. |
| `references/glossary.md` | *settle*, one definition. *finding* no longer says a person judges. |
| `references/spec_quality_guide.md` | The two `weak` rows of "Reading the cell": the next step is `purlin:build` alone. |
| `RELEASE_NOTES.md` | The plan's one sentence, at the end of the bullet `The audit.` |
| `dev/plans/deck/build_deck.py` | The `audit` slide's notes: `and you judge it` removed, two sentences on settling added. Not published. |

The ten descriptions are unchanged. `references/evidence_and_signoff.md` needed no change:
`<n> rules to strengthen: purlin:build` stands.

## Rules and proofs, word for word

**`skill_audit`**: `> Highest-Rule:` 29 to 30, `> Highest-Proof:` 59 to 60.

- RULE-29, reworded. Was: `skills/audit/SKILL.md` names the commands `purlin:audit`,
  `purlin:audit --all` and `purlin:build`, and the paths
  `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, `.purlin/evidence/local/<feature>.json`
  and `references/review_criteria.md`. Now: the same, with
  `purlin:audit <feature> RULE-N --settle` after `purlin:audit --all`.
- PROOF-59, reworded the same way: "A reader of the audit skill finds each of `purlin:audit`,
  `purlin:audit --all`, `purlin:audit <feature> RULE-N --settle`, `purlin:build`,
  `"${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py"`, `.purlin/evidence/local/<feature>.json`
  and `references/review_criteria.md` named in it".
- RULE-30, added: "The audit skill shows the two lines a settle prints, each in the words
  `references/review_criteria.md` gives under its heading `Settling a finding`".
- PROOF-60 (RULE-30), added: "The audit skill and the part of `references/review_criteria.md`
  under the heading `Settling a finding` each hold `the test now catches the bug it missed at`
  and `did not break what the proof says. A new bug was planted.`"

**`skill_build`**: `> Highest-Rule:` 21 and `> Highest-Proof:` 51, both unchanged.

- RULE-21, reworded: "The build skill names the commands `sync_status`, `purlin:test`,
  `purlin:test --all --commit`, `purlin:spec` and `purlin:audit <feature> RULE-N --settle`, and
  the files `scripts/purlin_python.sh`, `scripts/mcp/purlin/markers.py`,
  `scripts/mcp/purlin/wording.py`, `references/commit_conventions.md` and
  `references/review_criteria.md`". It was the same without the settle command and without
  `references/review_criteria.md`.
- PROOF-51, reworded the same way: "The text of `skills/build/SKILL.md` holds each of
  `sync_status`, `purlin:test`, `purlin:test --all --commit`, `purlin:spec`,
  `purlin:audit <feature> RULE-N --settle`, `scripts/purlin_python.sh`,
  `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/wording.py`,
  `references/commit_conventions.md` and `references/review_criteria.md`; none is missing".

**`purlin_docs`**: `> Highest-Rule:` 16 to 17, `> Highest-Proof:` 24 to 25.

- RULE-17, added: "`docs/audit.md` says what to do with a finding under its heading `What to do
  with a finding`, which stands straight after `How it works`: run `purlin:build`, and the rule
  ends `strong` or `spot-checked`".
- PROOF-25 (RULE-17), added: "In `docs/audit.md` the heading `What to do with a finding` is the
  next heading after `How it works`; the part under it holds exactly 6 bullets and names
  `purlin:build`, `strong` and `spot-checked`".

**`purlin_agent`**: `> Highest-Rule:` 24 to 25, `> Highest-Proof:` 55 to 56.

- RULE-25, added: "`references/purlin_commands.md` and `references/glossary.md` each name the
  command that settles a weak rule, `purlin:audit <feature> RULE-N --settle`".
- PROOF-56 (RULE-25), added: "The text of `references/purlin_commands.md` holds
  `purlin:audit <feature> RULE-N --settle`, and so does the text of `references/glossary.md`".

No rule or proof was deleted. The two descriptions of `purlin_docs` and `purlin_agent` were
brought in step ("says what to do with a finding", "six checks").

## Seen failing first

With the specs and tests written and no page changed, 6 tests failed:

- `test_skill_audit.py`: PROOF-59 (`audit does not name purlin:audit <feature> RULE-N
  --settle`), PROOF-56 (the same line beside the one it expects) and PROOF-60.
- `test_skill_build.py`: PROOF-51.
- `test_purlin_docs.py`: PROOF-25 (`'What you can count on' == 'What to do with a finding'`).
- `test_purlin_agent.py`: PROOF-56.

After the pages: all pass but the two that wait on lane `audit`, below.

`wording.py` then named the tests of `skill_audit` PROOF-59 and `skill_build` PROOF-51 as test
comments to correct, since each proof was reworded and its test's own lines had not changed.
Each test now states the settle command in its name and in an assertion, in its own commit,
and `wording.py` prints `No test comment to correct.`

## Tests that wait on lane `audit`

Both pass once `references/review_criteria.md` holds a heading `Settling a finding` with the
two printed lines in the plan's words.

1. `dev/test_skill_audit.py::test_the_skill_and_the_criteria_hold_the_two_lines_a_settle_prints`
   (`skill_audit` PROOF-60).
2. `dev/test_purlin_docs.py::test_every_relative_link_on_the_docs_pages_names_a_file_and_a_heading`
   (`purlin_docs` PROOF-17): `docs/audit.md` (twice) and `docs/running-and-evidence.md` link
   to `../references/review_criteria.md#settling-a-finding`.

No skill writes `--settle` on a line that names `purlin_run.py`, so `purlin_agent` PROOF-52
(every flag a skill passes is one its script takes) does not wait.

## Lines a person reads that this lane chose

The plan's bullets for `docs/audit.md`, its five steps and its release-notes sentence are
used word for word. These are chosen:

| Line | Where |
|---|---|
| `purlin:audit <feature> RULE-N --settle  Plant each bug that survived again, and run its proof's test` | the usage block of `skills/audit/SKILL.md`, `docs/running-and-evidence.md` and `references/purlin_commands.md` |
| `Strengthening a weak rule` | the heading in `skills/build/SKILL.md` |
| "A rule the audit found `weak` is left to do as a rule to strengthen. The status carries each finding as a reason of the rule's `strong` cell." | `skills/build/SKILL.md` |
| "A rule that still reads `weak` has a new finding: start again at step 1 with it." | `skills/build/SKILL.md`, after step 5 |
| Step 5's three ways each end on the rule's word: "the test now catches the bug, and the rule reads `strong`; the finding was wrong and a new bug was caught, and the rule reads `strong`; two bugs left the proof's check passing, and the rule reads `spot-checked`. Nothing more is asked." | `skills/build/SKILL.md` |
| "...is a planted bug the test did not catch: `purlin:build <feature>` settles it." and "...is the model's claim about which case the bug breaks. A test run settles whether it holds." | `skills/audit/SKILL.md`, Step 2 |
| "...is printed by a settle: the bug that survived was planted again and the test fails on it. The finding was right, and it is gone." | `skills/audit/SKILL.md`, Step 2 |
| "...is printed by a settle: the test still passes with that bug in place, so the bug was dropped and one new bug was planted for the proof. Where the new bug survives too, the rule's block holds `No bug was caught for PROOF-N: two planted bugs left the proof's check passing.`" | `skills/audit/SKILL.md`, Step 2 |
| "`<feature> RULE-N has no planted bug that survived: nothing to settle.` means the rule named with `--settle` is left as it is." | `skills/audit/SKILL.md`, Step 2 |
| "A finding is build work. `purlin:build <feature>` strengthens the test, then settles the rule with `purlin:audit <feature> RULE-N --settle`." | `skills/audit/SKILL.md` |
| "**settle**: to decide a surviving bug's finding with a test run. `purlin:audit <feature> RULE-N --settle` plants each bug that survived again and runs its proof's test as it stands now. `purlin:build` runs it once the test is stronger." | `references/glossary.md` |
| "`purlin:build` strengthens a weak test and settles the finding with a test run." and its like | `README.md`, `agents/purlin.md`, `docs/getting-started.md`, `docs/how-purlin-works.md` |
| `"strengthen the weak tests", "the audit found a rule weak"` routed to `purlin:build` | `agents/purlin.md` |
| "Most surviving bugs show a case the test does not check. Some rest on a strict reading of the proof's words. A test run tells them apart." | `docs/audit.md`, step 3 |
| "It does not check the AI's claim about which case a bug breaks. `purlin:build` puts the claim to a test run." | `docs/audit.md`, `What it does not do` |
| "**A test run settles a surviving bug.**" with "`purlin:build` writes the check the proof names, and the bug is planted again. The check fails: the finding held. The check passes: the bug did not break what the proof says." | `docs/audit.md`, the reasoning |
| "it is the one that raises the most flags on sound tests" and "It is a case to settle with a test run." | `docs/audit.md`, the trial's close and `What Purlin does not claim` |
| The whole of `On Purlin's own tests`: five bold bullets and the close "A new bug aimed past each stronger test finds a new gap, so auditing again does not end at zero in one pass. So a finding is settled against the bug the test missed, and a wrong finding is replaced once." | `docs/audit.md` |
| "`purlin:build` does the work for a weak rule. It fixes a test a spot test flagged. For a bug that survived, it writes the check the proof names, runs `purlin:test`, then settles the rule" and the two bullets under it | `docs/running-and-evidence.md` |
| "To settle one, run purlin:build: it writes the check the proof names and runs it against that bug. The check fails and the rule reads strong; the check passes and the audit plants one more, and if that one is wrong too the rule reads spot-checked and nothing more is asked." | the deck's `audit` slide notes |

## Calls the plan did not make

- **Every "a person judges a surviving bug" was removed**, since decision 124 says no person
  judges a finding: `docs/audit.md` (four places), `docs/running-and-evidence.md`,
  `docs/how-purlin-works.md`, `docs/getting-started.md`, `references/glossary.md`,
  `references/spec_quality_guide.md`, `skills/audit/SKILL.md` and the deck's notes.
- **A fourth ending in the build skill.** The contract leaves a rule `weak` where the recorded
  change can no longer be planted and the new bug survives. The skill says to start again at
  step 1.
- **The build skill does not repeat the printed lines.** It points at the audit skill's Step 2
  for how each reads and at `Settling a finding` for what the settle does.
- **The two wrong findings in `On Purlin's own tests` are told without Purlin's own names**:
  "the AI named a wrong result for the changed code: the code still gave what the proof says"
  and "the bug sat on a path no run reaches".
- **"each got a sharper sentence"** for the 12 loose proofs is true once lanes `proofs` and
  `audit` are merged.
- **The new rule on the two references went into `purlin_agent`**, whose scope holds
  `references/`.
- **PROOF-60 checks the two fixed phrases**, not the whole printed line, so it holds whether
  `review_criteria.md` writes `PROOF-2` and `src/auth.py:12` or placeholders.
- **`On Purlin's own tests` is in the first commit**, with the rest of the audit page.
- **The usage line is given once per form.** `--settle` takes one rule per flag in the script;
  the pages show one rule, as the plan writes the command.

## Seen and left, another lane's

- The plan's grep (section 5, step 3) prints `scripts/review/audit_run.py:8:2. one model call
  per rule, four at once`. It is on `main` and is lane `audit`'s file.

## Acceptance

- `dev/test_skill_*.py`, `dev/test_purlin_docs.py`, `dev/test_purlin_agent.py`: 31 passed,
  2 failed, the two that wait on lane `audit`.
- The deck, with `DECK_ROOT` in the scratch folder: `check_deck.py` prints `contentBottom: 920`
  of `limit: 920` for each of the 14 slides, the `audit` slide included; `check_overlap.py`
  prints no hit.
- `bash dev/run_tests.sh --fast`: `2 failed, 928 passed, 9 skipped`, then
  `Suites: 0 passed, 1 failed`. The 2 are the same two. The sweep ran before the commit that
  changed the two tests' names; the lane's test files were run again after it.
- `git rebase main`: `main` had not moved.
