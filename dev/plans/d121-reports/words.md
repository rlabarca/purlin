# Lane `words` of decision 121: report

Branch `lane/d121-words`, cut from `main` at `fe512e267`. No spec and no file under `scripts/`
was edited. Section 6.9's experimental wording is not written.

## What changed, by file

| File | Change |
|---|---|
| `skills/audit/SKILL.md` | Section 6.5 whole: the description, the opening sentence, the three steps, the three words, the calls and the cost, Step 2's block with no dollar figure, its four list lines, Step 3's `spot-checked` line. The exit line reads `changed while the audit ran`. |
| `docs/audit.md` | Section 6.6 whole: step 3, the `spot-checked` paragraph and its line, the share line, three bullets of "What you can count on", three of "What it does not do", the table's last row and the line under it. |
| `docs/how-purlin-works.md` | The question `What do strong, weak, spot-checked and not audited mean?` with its five bullets and `waiting`; the audit paragraph names the three words. |
| `docs/running-and-evidence.md` | When a rule is read; steps 2 and 3; the three bullets; the `could not be reached` line; the block and the share line of 6.5; the status sentence under it; the `changed while the audit ran` line; the flow chart's audit box; the `audit` object's parts; the slow sentence; the test-command sentence. |
| `docs/sign-off.md` | Two refusal rows; the overview's audit line; the tag git could not write; the two sentences under "What is recorded"; the package hash and `HEAD` under "When a sign-off counts". |
| `docs/specs-and-anchors.md` | The `kept` sentence in the slow section; `purlin:anchor add ... [--name <name>]` and its three sentences. |
| `docs/dashboard.md` | `Strong` is there once any rule has an audit entry; `SPOT-CHECKED` and `OUT OF DATE` with their reasons; the `Audit` panel's `Spot-checked.` and `Out of date:`; `No audit has read this rule yet.` |
| `docs/getting-started.md` | One sentence: a caught bug and no finding make the rule `strong`. |
| `references/evidence_and_signoff.md` | The strong cell's words; the summary and its form; `not signed`; the test-command sentence; the slow sentence; the package hash, `HEAD` and the hand-written tag under "When a sign-off counts"; two refusals; the tag git could not write; "What stops nothing". |
| `references/glossary.md` | The summary; `out of date` for the strong cell, inside its one definition; the audit's three steps; `strong`, `spot-checked` and `kept`; the chain's `strong` row. |
| `references/spec_quality_guide.md` | The `not audited` row's cause; the rows `spot-checked` and `out of date`. |
| `references/purlin_commands.md`, `README.md` | The `purlin:audit` purpose sentence, the same in both; the command list's line; `--name` on `purlin:anchor add`; the exit code row. |
| `skills/sign/SKILL.md` | The overview's audit line; the package refusal; two list lines; the tag git could not write, under Step 6 and in Step 7's table. |
| `skills/status/SKILL.md`, `agents/purlin.md` | The summary sentence. |
| `skills/test/SKILL.md` | The slow sentence. |
| `skills/anchor/SKILL.md` | `--name` on the `add` line and its three sentences. |
| `CLAUDE.md` | "Tool folder separation", last sentence. |
| `RELEASE_NOTES.md` | Five bullets under "What is new"; the formats line; the summary; the audit paragraph; the refusals; the anchor line. |
| `dev/plans/deck/build_deck.py` | `why`'s audit row, `audit`'s row 3 and notes, `manual`'s notes. |

## Lines chosen here, word for word

Where the plan gives a line, it is the plan's. These are the ones this lane chose.

- `skills/audit/SKILL.md`, after the three words: `One caught bug makes a rule strong. Each of its proofs with no caught bug is named under it, with the reason. A test that is skipped, is not collected or runs past its limit with the bug in place is not a caught bug. An anchor's rule reads spot-checked: no bug is planted for one. No bug is planted on this machine for a proof tagged for another system.` and `The model is started with no tools, no plugins and none of your settings, in an empty folder.`
- `docs/audit.md`, step 2 gains `The AI is asked once for each rule.`; after the `spot-checked` line: `One caught bug makes a rule strong. Each of its proofs with no caught bug is named under it, with the reason.`
- `docs/running-and-evidence.md`: `it has no audit entry, its entry is out of date, or a proof still waits for its bug.`; in step 2, `A proof whose test and covered code are as the audit last read them keeps its result and gets no new bug. The reading explains the tests and sets no verdict.`; in step 3, `A test that is skipped, is not collected or runs past its limit decides nothing. The copy is then removed.`; `No bug is planted for an anchor's proof, a @manual proof or a proof tagged for another system. So an anchor's rule reads spot-checked.`; `A rule a spot test fired on is still weak, and the next purlin:audit reads the others again.`; `It prints how many model calls it will make, then each rule with what it found, then what the calls cost, and last the share of rules it found strong:`; `A test command in .purlin/config.json is part of the tests: changing one ends the results, as changing the code does. Changing version alone does not.`
- `docs/sign-off.md`: the kept row's cause, `a slow result kept from an earlier run: a plain run carried it over, and purlin:test --all --commit takes it on this version`; `Two things are listed in the package and stop no sign-off: what the audit found, whatever its word, and a rule whose tests pass with no proof line.`; `Where the commit is made and git cannot write the tag, the walk prints` the `No tag:` line, then `The next purlin:sign writes the tag on the signed commit and signs nothing twice.`; `A package changed after it was signed no longer matches.`
- `docs/specs-and-anchors.md` and `skills/anchor/SKILL.md`: `Your copy takes its name from the file. --name gives it another, in letters, digits and _. A name an anchor in the project already holds is refused, and the refusal names purlin:anchor sync <name>.`
- `docs/dashboard.md`: `SPOT-CHECKED: the spot tests found nothing and no bug was planted and caught. The reason says why` and `OUT OF DATE: the rule, its proof, its test or its code changed since the audit read it. The reasons name what changed and the last result`.
- `references/evidence_and_signoff.md`: `no signed/* tag on HEAD or behind it has a sign-off that counts`; `What the audit found never blocks the sign-off, whatever its word.`; `Where git cannot write the tag, the next purlin:sign writes it on the signed commit and adds no second sign-off.`
- `references/glossary.md`, in `out of date`: `It is also the strong cell's word when the rule, its proof, its test or its code changed since the audit read it: the last result stays on screen until the audit reads the rule again.`; `strong: the spot tests found nothing and a planted bug was caught by its proof's test.`
- `skills/sign/SKILL.md`: `A slow result kept from an earlier run reads not taken on this version of the code. A slow result must be taken on the version being signed, and purlin:test --all --commit takes it.`; `A package that does not match its fingerprint was changed after it was signed.`; the table rows `No tag: git could not write signed/<version>:` to `Fix what git named, then run: purlin:sign` and `signed/<version> is not written yet:` to `Run: purlin:sign`.
- `dev/plans/deck/build_deck.py`, `manual`'s notes: `The next walk shows that note at the rule's stop.`

## Where this lane differs from the plan's words

1. **The summary sentence where `Left to do` follows.** The plan gives `40 rules. 40 pass their
   tests. The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.` In
   `references/evidence_and_signoff.md`, `references/glossary.md`, `skills/status/SKILL.md`,
   `agents/purlin.md` and `RELEASE_NOTES.md` the sentence stands above `3 rules to fix`, or
   beside `40 rules. 35 pass their tests.`, which `references/writing_style.md` also quotes. So
   those read `40 rules. 35 pass their tests. The audit found 30 of 35 rules strong (85%): 30
   strong, 2 weak, 3 spot-checked.` The form is the plan's; the counts fit the lines around it.
2. **The sign-off's overview line.** The plan gives `The audit: 34 strong, 4 weak, 2
   spot-checked.` The block in `docs/sign-off.md` and `skills/sign/SKILL.md` counts 19 rules,
   so it reads `The audit: 17 strong, 1 weak, 1 spot-checked.`
3. **The `purlin:audit` purpose sentence** keeps its ending `into the evidence`, which the
   plan's quote leaves off: `Run the tests, the heuristic spot tests, one model call per rule
   and one planted bug per proof, then write what it found into the evidence`.
4. **`CLAUDE.md`'s reference table.** The tree's `CLAUDE.md` already names
   `references/evidence_and_signoff.md`; no file in the tree names `references/hard_gates.md`.
   Nothing to correct.
5. **`RELEASE_NOTES.md`'s formats line** now reads evidence 11, signature 16, package 11 and
   schema 15, section 7's numbers. It is true once lanes `evidence`, `signoff` and `surfaces`
   land them.

## Tests

`python3 -m pytest dev/test_skill_*.py dev/test_purlin_docs.py dev/test_purlin_agent.py
dev/test_purlin_output.py -q`: 31 passed before, 31 passed after. No test file was changed. The
install test's real model call was not run.

The deck: `build_deck.py`, `check_deck.py` and `check_overlap.py` run with `DECK_ROOT` set to a
scratch folder. Every slide ends at 920 of 920, no overlap. The `audit` slide's spacer is 8
pixels, so row 3 fits with little room left. The deck is not published.

Step 7's greps are empty over this lane's files. No dollar figure stands in a skill, a doc page
or a reference this lane owns; the cost line is `$<total> in all, $<per rule> a rule`.

Against lane `setup`'s four checks: no skill, agent or reference line added here names a path
under `dev/`; every path named exists; the one flag added to a script line, `--name`, is in
`upstream.py add --help`; the sign skill's answers file is unchanged.

## Edits needed in files this lane does not own

- `specs/skills/skill_audit.md`, the Description: `one planted bug per proof and the model's
  reading` should read `one model call per rule and one planted bug per proof`. No lane owns
  this spec.
- `references/review_criteria.md` lines 32, 256, 277 and 278 still hold `stays not audited`,
  `$0.16 a rule` and the old share line: lane `audit`'s, section 6.8.

## Left open

- The docs describe what the other lanes build. Until they merge, the code prints the old
  lines.
- `docs/images/*.png` are not retaken; integration's step 8 does it.
- Section 6.9 is not written.
