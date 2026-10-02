# Lane `anchors`: the last two bullets of decision 125

Branch `lane/d125-anchors`, worktree `/Users/richlabarca/LocalCode/purlin-wt/d125-anchors`.

## What was built

**An anchor's `Strong` cell says what the audit found, in one word.**

- `scripts/mcp/purlin/board.py`: `anchor_word(rollup)` gives `weak`, `out of date`,
  `spot-checked` or nothing. `strong_cell` and `row_cells` take the feature's `is_anchor`, and
  `scripts/mcp/purlin/status.py` hands it to them. A feature's cell reads `<s> of <n>` as before.
- `scripts/report/src/board.js`: `strongCell` reads the same word for an anchor through
  `anchorWord`, `weak` in the warn tone and the other two words in the page's text colour. The
  hover opens on `No bug is planted for an anchor's rule.` and then carries the line it carried
  before, the newest audit's source and age. An empty cell carries no hover.
- `dev/test_states.py`'s PROOF-58 holds the table and the page to the same cells over the
  three samples, the anchors' rows included.

**An anchor's rules are left out of the share of strong rules.**

- `scripts/mcp/purlin/summary.py`: `audit_share(counts, anchors)` is the one home of the share.
  `anchors_audit(features)` counts what the audit found for the anchors' rules, `audit_line` and
  `sentence` take those counts and leave them out of `<s>`, `<n>` and `<p>`, and the counts
  after the colon are unchanged. `features_audit_line(features)` gives the line over a set of
  feature entries, for the audit's last line.
- `scripts/mcp/purlin/payload.py`: `build_payload` hands the sentence the anchors' counts.
- `scripts/report/src/app.js`: `auditShare()` counts the share from the features, leaving out
  each one whose `is_anchor` is true; `auditTotal()` is deleted. The `Strong` box is in the pass
  tone once `strong === over` of that share. The box's count and its hover are unchanged.
- **The payload keeps its shape and schema 16.** The page reads `is_anchor` and each rule's
  strong cell, which it already had, so no key was added.
- `dev/fixtures/report/team.json`: the anchor `checkout_design`'s one rule read `strong`, which
  no audit can write. It now reads `spot-checked` with the sentence the audit gives an anchor's
  rule, and the counts and the sentence follow. `dev/fixtures/report/regulated.json`: the
  sentence alone, `3 of 6 rules strong (50%)` where it read `3 of 7 rules strong (42%)`.

Every place that computes or prints the share:

| Place | State |
|---|---|
| `summary.sentence`, so the status and every run's ending | done, from `audit_share` |
| the payload's `summary.sentence` | done |
| the dashboard's `Strong` box tone | done, `auditShare()` mirrors `audit_share` |
| the audit's last line, `scripts/review/audit_run.py` `share_line` | **not mine; needs the change below** |
| the sign-off's overview, `scripts/review/sign.py` | prints the counts through `summary.audit_words` and no share; nothing to change |
| the evidence package, `scripts/export/package.py` | stores the five counts and no share; nothing to change |

## Rules and proofs, word for word

### `specs/mcp/summary.md`: `> Highest-Rule:` 25 to 26, `> Highest-Proof:` 60 to 62

Added:

- RULE-26: The share `<s> of <n> rules strong (<p>%)` counts no rule of an anchor, since no bug is planted for an anchor's rule and it is never found strong; the counts after the colon count an anchor's rules with every other
- PROOF-61 (RULE-26): A feature of 3 rules, 2 found strong and 1 weak, beside an anchor of 8 rules found spot-checked, all 11 passing their tests, reads `11 rules. 11 pass their tests. The audit found 2 of 3 rules strong (66%): 2 strong, 1 weak, 8 spot-checked.`
- PROOF-62 (RULE-26): On committed evidence, a feature's one rule found strong beside an anchor's one rule found spot-checked, both passing their tests, reads `2 rules. 2 pass their tests. The audit found 1 of 1 rules strong (100%): 1 strong, 1 spot-checked.`

The `> Description:` gained `, an anchor's rules left out of the share`.

### `specs/mcp/states.md`: `> Highest-Rule:` 127 to 128, `> Highest-Proof:` 299 to 303

Reworded, RULE-121: `` `Strong` reads `<strong> of <n>` `` became
`` a feature's `Strong` reads `<strong> of <n>` ``. No proof of it was reworded.

Added:

- RULE-128: An anchor's `Strong` cell in the status table reads one word and never `<strong> of <n>`, counting the anchor's rules that pass their tests and have a tested proof: `weak` where the audit found any of them weak, else `out of date` where the audit entry of any is out of date, else `spot-checked` where the audit found every one of them spot-checked, else nothing
- PROOF-300 (RULE-128): The anchor `security`, 2 rules that pass their tests and that the audit found spot-checked, beside the feature `login` whose one rule it found strong, reads `spot-checked` in its `Strong` cell in the status table, and `login` reads `1 of 1`
- PROOF-301 (RULE-128): With `security`'s `RULE-1` found spot-checked and its `RULE-2` found weak, its `Strong` cell in the status table reads `weak`
- PROOF-302 (RULE-128): With both of `security`'s rules found spot-checked and the project's code changed since `RULE-1`'s entry was written, its `Strong` cell in the status table reads `out of date`
- PROOF-303 (RULE-128): With `security`'s `RULE-1` found spot-checked and its `RULE-2` never read by the audit, its `Strong` cell in the status table is empty

### `specs/dashboard/purlin_report.md`: `> Highest-Rule:` 79 to 80, `> Highest-Proof:` 248 to 255

Reworded, RULE-8: `in the pass tone once every rule the audit could read is strong` became
`in the pass tone once every rule the audit could read that is not an anchor's is strong`.

Reworded, RULE-9: `` `Strong` `<s> of <n>` `` became `` a feature's `Strong` `<s> of <n>` ``.

No proof of either was reworded.

Added:

- RULE-80: An anchor's `Strong` cell reads one word and never `<s> of <n>`, counting the anchor's rules that pass their tests and have a tested proof: `weak`, in the warn tone, where the audit found any of them weak, else `out of date` where the audit entry of any is out of date, else `spot-checked` where the audit found every one of them spot-checked, else nothing. Its hover reads `No bug is planted for an anchor's rule.` on its first line, then the newest audit's source and age
- PROOF-249 (RULE-80): Open the board with the team sample, where the one rule of the anchor checkout_design passes its tests and the audit found it spot-checked; checkout_design's `Strong` cell reads `spot-checked`, and the feature receipt's reads `1 of 1`
- PROOF-250 (RULE-80): Open the board with the regulated sample, where the audit found checkout_design's one rule weak; its `Strong` cell reads `weak` in the warn tone
- PROOF-251 (RULE-80): Open the board with the team sample after the code changed since the audit entry of checkout_design's rule was written; its `Strong` cell reads `out of date`
- PROOF-252 (RULE-80): Open the board with the team sample after checkout_design's rule, passing its tests, is left with no audit entry; the headings end with `Strong`, and the `Strong` cells of checkout_design and of security_baseline, whose one rule has no test, are empty
- PROOF-253 (RULE-80): Open the board with the team sample; the hover of checkout_design's `Strong` cell reads two lines, `No bug is planted for an anchor's rule.` and then `audit · local · <age>`, and the hover of receipt's `Strong` cell does not hold that sentence
- PROOF-254 (RULE-8): Open the board with the team sample after login's `RULE-1`, the one rule the audit found weak, is found strong, the anchor checkout_design's one rule reading `spot-checked`; the `Strong` box reads `5` in the pass tone, and its hover opens on the two lines `5 strong` and `1 spot-checked`
- PROOF-255 (RULE-8): Open the board with the team sample, whose audit found 4 rules strong, login's `RULE-1` weak and the anchor checkout_design's one rule spot-checked; the `Strong` box reads `4` in the warn tone

Nothing was deleted, and no number was used twice.

## What was seen failing first

Against the code and the page as they stood on `main`, with the new tests in place:

| Test | What it read |
|---|---|
| summary PROOF-61 | `The audit found 2 of 11 rules strong (18%): 2 strong, 1 weak, 8 spot-checked.` |
| summary PROOF-62 | `The audit found 1 of 2 rules strong (50%): 1 strong, 1 spot-checked.` |
| states PROOF-300, 301, 302, 303 | `0 of 2` in each |
| purlin_report PROOF-249, 250, 251, 252 | `0 of 1` in each |
| purlin_report PROOF-253 | one hover line, `audit · local · 20 days old` |
| purlin_report PROOF-254 | the `Strong` box in the warn tone, `rgb(255, 216, 97)` |

purlin_report PROOF-255 passed before and after: it holds the other direction, a weak rule that
is not an anchor's keeping the box in the warn tone.

## What was looked at

The team sample (an anchor whose rule is spot-checked), the regulated sample (an anchor's rule
weak) and the solo sample (never audited), each at 1500 and 390 pixels, dark and light, opened
headless with playwright from the `.venv`. In all 12 the page has no sideways scroll and every
`Strong` value sits on one line. `spot-checked` is in the page's text colour, `weak` in the warn
tone, and an anchor with nothing to say has an empty cell, which the narrow layout leaves out.
The solo sample draws no `Strong` column.

## Lines a person reads

The decision gave every line a person reads: the three cell words and the hover's first line,
`No bug is planted for an anchor's rule.` No line was chosen.

## Calls the decision did not make

1. **`every rule` means every rule the audit can speak of.** The cell reads `spot-checked`
   where every rule of the anchor that passes its tests and has a tested proof reads
   `spot-checked`: the same rules a feature's `<n>` counts. A rule that fails its tests or is
   checked by hand alone does not empty the cell; a rule that passes and that no audit has read
   does.
2. **`out of date` and `spot-checked` are drawn in the page's text colour**, with no state
   colour. The decision gives the warn tone to `weak` alone.
3. **An empty anchor cell carries no hover**, as an empty feature cell carries none.
4. **The share's `<s>` leaves an anchor's rule out too.** No audit writes `strong` for an
   anchor's rule. Were an evidence file to hold one, the share would still count neither side of
   it, and the count after the colon would. `states` was not changed to refuse such an entry.
5. **A project whose only audited rules are an anchor's** reads
   `The audit found 0 of 0 rules strong (0%): 0 strong, 8 spot-checked.`, and the `Strong` box
   reads `0` in the pass tone, since no rule that can be strong is short of it. Both follow from
   what the code did at zero before.
6. **No schema change.** The page had what it needed. The cost is the one change to the
   audit's last line below, which the payload's five counts alone cannot give.
7. **The team sample was corrected** rather than left holding an anchor's rule rated `strong`.
8. `scripts/mcp/purlin/board.py` is in no spec's `> Scope:`. That was so before this lane and
   is left as found.

## Changes needed in files this lane does not own

### Code

`scripts/review/audit_run.py`, `share_line`: the audit's last line still counts an anchor's rules
in the share. Replace its last five lines

```python
    own = [rule for feature in now.get('features') or ()
           if feature.get('name') in selected
           for rule in feature.get('rules') or ()
           if rule.get('feature') == feature.get('name')]
    return summary_module.audit_line(summary_module.audit_counts(own))
```

with

```python
    return summary_module.features_audit_line(
        [feature for feature in now.get('features') or ()
         if feature.get('name') in selected])
```

and in its docstring, after `so the line and the status give the same numbers`, add
`, the share counting no rule of an anchor`. A test for it belongs in `dev/test_ai_audit.py`:
an audit over a feature whose one rule is found strong and an anchor whose one rule passes ends
on `The audit found 1 of 1 rules strong (100%): 1 strong, 1 spot-checked.`

### Tests

No test in another lane's file fails on this branch. `dev/test_ai_audit.py` calls
`summary_module.audit_line(counts)` with the counts alone in the test of PROOF-99; the call
still works, and its project has no anchor.

### Sentences

| File and line | Now | Corrected |
|---|---|---|
| `docs/dashboard.md:88` | `` `Strong` counts the rules the audit found strong, of the rules that pass their tests and have a tested proof. It is there once any rule has an audit entry. `` | add after it: `` It is complete once every such rule that is not an anchor's is strong. `` |
| `docs/dashboard.md:104` | the `Strong` row of the columns table | `` `2 of 4`, as `<strong> of <n>`: how many rules the audit found strong, of the rules that pass their tests and have a tested proof. An anchor reads one word, `weak`, `out of date` or `spot-checked`, or nothing `` and, for its hover, `` where the newest audit came from and how old it is; an anchor's opens on `No bug is planted for an anchor's rule.` `` |
| `skills/status/SKILL.md:71` | `` A `Strong` column shows only where the audit read a rule, as `<strong> of <n>`: of the rules that pass their tests and have a tested proof, the ones it found strong. `` | add after it: `` An anchor's cell reads one word, `weak`, `out of date` or `spot-checked`, or nothing: no bug is planted for an anchor's rule. `` |
| `references/evidence_and_signoff.md:64` | `` `a` counting the rules that pass their tests and have a tested proof, then `` | `` `a` counting the rules that pass their tests, have a tested proof and are not an anchor's, then `` and, after `each only where it is not zero.`, `` Those counts take in an anchor's rules. `` |
| `references/review_criteria.md:343` | `` Each rule that passes its tests is counted under the word its strong cell reads; `` | `` Each rule that passes its tests is counted under the word its strong cell reads, and the share counts no rule of an anchor; `` |
| `references/glossary.md:50`, **summary** | `` A rule is counted once, under the spec that owns it. `` | add after it: `` The share counts no rule of an anchor. `` |
| `docs/running-and-evidence.md:354` | `` and last the share of rules it found strong: `` | `` and last the share of rules it found strong, which counts no rule of an anchor: `` |

The examples in `docs/audit.md:46`, `docs/running-and-evidence.md:363` and `:370`,
`skills/status/SKILL.md:79`, `skills/audit/SKILL.md:86`, `agents/purlin.md:78` and
`references/writing_style.md:33` name no anchor and stay true. `docs/audit.md:76` already says an
anchor's rule reads `spot-checked`, never `strong`.

## Acceptance

After `git rebase main`, which found the branch up to date:

- `dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`, `dev/test_summary.py`
  and `dev/test_states.py`: `194 passed`.
- `bash dev/run_tests.sh --fast`: `933 passed, 9 skipped`, and its last line
  `Suites: 1 passed, 0 failed`. No test failed, in this lane's files or another's.

A first run of the fast suite was stopped by its time limit at 78% with no failure; the run
above is the second, complete one. No test reached a model.
