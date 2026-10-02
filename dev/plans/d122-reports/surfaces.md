# Lane `surfaces`: report

Branch `lane/d122-surfaces`, from `main` at `e02c9b4f5`. One commit of work, then this report.

## What was built

- **`states.py`.** A rule whose every proof is `@manual` reads `checked at sign-off` in its
  passed cell, with the reason `no sign-off has checked it yet`. Once `hand_notes` holds a note
  and `hand_changed` is empty it reads `passed`, the note its reason. With `hand_changed` it
  reads `checked at sign-off` again, a `HAND_CHANGED` line per part before the note. The strong
  cell of a rule with a `@manual` proof opens with the same lines. `NOT_CHECKED`, `HAND_CHANGED`
  and `BUCKETS` are contract K3's, word for word. The bucket `by_hand`; the flag `by_hand`.
- **`summary.py`.** `steps` answers `{'passed', 'by_hand'}`. The sentence gains its third part
  (`BY_HAND_ONE`, `BY_HAND_MANY`). `rule_kind` answers None for a passed word of
  `checked at sign-off`, so the tests read `met` beside it.
- **`board.py`.** `passing` leaves `by_hand` out. `tests_cell` appends `· <k> by hand`.
  `strong_cell` reads `<strong> of <n>`, `n` being the new `audited_rules(rollup)`, and `''`
  where `n` is 0.
- **`payload.py`.** `SCHEMA_VERSION` 16. It already handed `hand_changed` on (seam B2).
- **The dashboard** (`app.js`, `board.js`, `rule.js`). `SCHEMA` 16, `WORDS.by_hand`, the `Tests`
  and `Strong` cells as `board.py` words them, the `Passing` box complete once every other rule
  is checked at sign-off, the `Strong` box complete once it equals the `Audit` box's `<n>`.
- **The fixtures.** Schema 16, `steps.by_hand`, each rollup's and the summary's `by_hand`, the
  flag `by_hand` on every rule, and regulated's invoice `RULE-3` reading `checked at sign-off`.
- `status.py` and `report_data.py` needed no change.

## `> Highest-*`, before and after

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `states` | 126, 127 | 294, 299 |
| `summary` | 24, 25 | 57, 60 |
| `purlin_report` | 78, 78 | 243, 247 |

## Rules and proofs, word for word

Every line below is the plan's (d122 section 3), but the two marked **chosen**.

### `states`

Added:

- RULE-127: Where the rule's text, or the text of one of its `@manual` proofs, changed since the newest sign-off noted it, each cell reading `checked at sign-off` carries, before the note, `the rule's wording changed since its last note` or `the proof's wording changed since its last note`
- PROOF-295 (RULE-109): After `quinn.qa@labconnect.example` signs `0.1.0` at HEAD with the note `the tube is red` on a rule whose one proof is `@manual`, its passed cell reads `passed` with the one reason `noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, at this commit: the tube is red`
- PROOF-296 (RULE-127): A rule checked by hand alone was noted at the sign-off of `0.1.0`, 1 commit ago, and its text was reworded since; its passed cell reads `checked at sign-off` with the reasons `the rule's wording changed since its last note` and then `noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 1 commit since: the tube is red`
- PROOF-297 (RULE-127): A rule has `PROOF-1` marked `@manual` and `PROOF-2` whose test passes, noted at the sign-off of `0.1.0`, and `PROOF-1` was reworded since; its passed cell reads `passed`, and its strong cell reads `checked at sign-off` with the first reason `the proof's wording changed since its last note`
- PROOF-298 (RULE-121): A spec of 3 rules, 2 that pass their tests and 1 whose one proof is `@manual`, reads `2 of 3 · 1 by hand` in its `Tests` cell
- PROOF-299 (RULE-121): A spec of 10 rules, 9 that pass their tests and are found strong and 1 whose one proof is `@manual`, reads `9 of 9` in its `Strong` cell

Reworded:

- RULE-23: A rule's bucket is exactly one of `untested`, `failing`, `partial`, `by_hand` and `passed`: `failing` where its passed cell reads `failed`, `partial` where it reads `partial`, `by_hand` where it reads `checked at sign-off`, `passed` where it reads `passed`, and `untested` where it reads any other word, a rule no proof line names included
- RULE-27: `schema version 15` became `schema version 16`.
- RULE-59: `signoff` carries `word`, `version`, `commit` and `since` for the newest version whose sign-off counts, found by its `signed/*` tag on HEAD or an ancestor of it, or by its sign-off files where this checkout holds no such tag, numbered versions compared as numbers, `word` reading as the status's `Sign-off:` line does, and `word` reads `not signed` where there is none
- RULE-81: its opening became `` `summary` carries `steps`, holding `passed` and `by_hand`, `audit` and `sentence`; ``.
- RULE-109: A rule whose every proof is `@manual` reads `checked at sign-off` in its passed cell, with the reason `no sign-off has checked it yet`, until a sign-off that counts holds a note for it on the rule's and the proof's wording as they are; then it reads `passed`, with that note as its reason; its strong cell reads `checked at sign-off` throughout
- RULE-121: The status table shows one row per spec under `Spec`, `Rules`, `Proofs` and `Tests`, with `Strong` added where any rule has an audit entry and `Proofs` left out where no spec writes a proof line; `Tests` reads `<passed> of <rules>` and appends `· <k> by hand`, `· <k> partial` and `· <k> failing`; `Strong` reads `<strong> of <n>`, `<n>` the spec's rules that pass their tests and have a tested proof, and is empty where it has none; where the project has an anchor, the anchors' rows stand under the line `Anchors` and every other spec's under `Specs`
- PROOF-31: `` `schema_version` 15 `` became `` `schema_version` 16 ``.
- PROOF-264 (RULE-109): A rule whose one proof is `@manual`, with no test marked, nothing run and no sign-off, reads `checked at sign-off` in its passed cell with the one reason `no sign-off has checked it yet`, `checked at sign-off` in its strong cell, and the bucket `by_hand`
- PROOF-294 (RULE-121): Over a spec of two rules whose tests pass, the audit finds `RULE-2` strong and never reads `RULE-1`, and `RULE-2`'s test then fails; the status report's header still ends with `Strong`, and the spec's `Strong` cell reads `0 of 1`

### `summary`

Added:

- RULE-25: A rule whose passed cell reads `checked at sign-off` is counted under no kind of work and not among the rules that pass, so the tests read `met` where every rule that has a test passes it on the committed evidence, whether or not anyone has checked that rule
- PROOF-58 (RULE-22): 10 rules, 9 that pass their tests and 1 whose one proof is `@manual` and that no sign-off has noted, read `10 rules. 9 pass their tests. 1 is checked at sign-off.`
- PROOF-59 (RULE-25): Over those 10 rules on committed evidence, the status's second line reads `Tests: met`, it holds no `Left to do:` line, and its last line reads `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`
- PROOF-60 (RULE-22): 9 rules pass their tests and are found strong, and a tenth has one `@manual` proof; the sentence reads `10 rules. 9 pass their tests. 1 is checked at sign-off. The audit found 9 of 9 rules strong (100%): 9 strong.`

Reworded:

- RULE-20: `for the newest signed/* tag on HEAD or an ancestor of it whose sign-off counts,` became ``for the newest version whose sign-off counts, found by its `signed/*` tag on HEAD or an ancestor of it or by its sign-off files where this checkout holds no such tag,``; the rest stands.
- RULE-22: The sentence reads `<N> rules. <p> pass their tests.`, `1 rule.` and `1 passes its tests.` for a count of one, then ` <h> are checked at sign-off.`, `1 is checked at sign-off.` for one, where a passed cell reads `checked at sign-off`, counting each rule once under the spec that owns it; where a rule that passes has an audit entry it adds ` The audit found <s> of <n> rules strong (<p>%): <s> strong`, then `, <n> weak`, `, <n> spot-checked`, `, <n> out of date` and `, <n> not audited`, each only where not zero

### `purlin_report`

Added:

- PROOF-244 (RULE-15): Open the regulated sample's invoice `RULE-3`, whose one proof is `@manual` and which no sign-off has noted; its passed row reads `CHECKED AT SIGN-OFF` in the neutral tone with the reason `no sign-off has checked it yet`, and its row on the board carries no `PASSED` badge
- PROOF-245 (RULE-9): Open the board with the regulated sample; invoice's `Tests` cell reads `2 of 3 · 1 by hand` and its `Strong` cell `1 of 2`
- PROOF-246 (RULE-71): Open the regulated sample's invoice `RULE-3` after its note of `0.1.0` is marked as written before the rule was reworded; above the note the screen reads `the rule's wording changed since its last note`
- PROOF-247 (RULE-8): Open the board with the regulated sample after every rule but invoice `RULE-3` is given a passing test; the `Passing` box reads `10` in the pass tone

Reworded:

- RULE-8: its middle became `` `Passing`, counting the rules whose tests pass, with the project's rule count beneath it as `<n> RULES TOTAL`, in the pass tone once every rule passes or reads `checked at sign-off`; and `Strong`, wherever a rule has an audit entry, counting the rules it found strong, in the pass tone once it equals the `<n>` of the `Audit` box ``.
- RULE-9: its end became `` `Tests` `<passed> of <rules>`, then `<k> by hand`, `<k> partial` and `<k> failing`; `Strong` `<s> of <n>`, `<n>` the spec's rules that pass their tests and have a tested proof ``.
- RULE-44: its list of statuses ends `` `not run`, `out of date` and `checked at sign-off` ``.
- RULE-71: it now ends `` and above that note, where the rule's or the proof's wording changed since it, `the rule's wording changed since its last note` or `the proof's wording changed since its last note` ``.
- PROOF-8: `whose 11 rules pass their tests 7 times` and `` `Passing` 7 ``.
- PROOF-40: `` `Strong` `2 of 3` ``.
- PROOF-167: ``7 rows carry `PASSED` ``.
- PROOF-243: `` login's `Strong` cell reads `0 of 1` ``.
- **Chosen**, PROOF-20: `this page reads schema 15` became `this page reads schema 16`. The plan did not list it; the notice names the page's schema.
- **Chosen**, PROOF-43: `` `▼ BILLING 2 specs 4 of 5 rules pass` `` became `` `▼ BILLING 2 specs 3 of 5 rules pass` ``. This is the one other proof whose count the fixture's hand check moved: a band counts the rules that pass their tests, and invoice `RULE-3` no longer does.

Nothing was deleted.

## What was seen failing first

On `main`'s code, with the new tests:

| Test | What it showed |
|---|---|
| `states` PROOF-264 | `assert 'passed' == 'checked at sign-off'` |
| `states` PROOF-295 | the passed cell's reasons were `[]`, not the note |
| `states` PROOF-296 | `assert 'passed' == 'checked at sign-off'` |
| `states` PROOF-297 | the strong cell's first reason was the note, with no line above it |
| `states` PROOF-31 | `assert 15 == 16` |
| `states` PROOF-294 | `assert '0 of 2' == '0 of 1'` |
| `states` PROOF-298 | `assert '3 of 3' == '2 of 3 · 1 by hand'` |
| `states` PROOF-299 | `assert '10 of 10' == '9 of 10 · 1 by hand'` |
| `summary` PROOF-58 | `10 rules. 10 pass their tests.` |
| `summary` PROOF-60 | `10 rules. 10 pass their tests. The audit found 9 of 9 rules strong (100%): 9 strong.` |
| `summary` PROOF-59 | passed on `main`, where the hand check read `passed`. With the `states` change alone it failed: `assert 'Tests: not met' == 'Tests: met'`. It passes with `rule_kind`'s change |
| `purlin_report` PROOF-247 | `Passing` read `10` in the warn tone |
| `purlin_report` PROOF-40 | `assert '2 of 4' == '2 of 3'` |
| `purlin_report` PROOF-245 | `assert '2 of 3' == '2 of 3 · 1 by hand'` |
| `purlin_report` PROOF-243 | `assert '0 of 3' == '0 of 1'` |

The dashboard's four were run against `main`'s built page with only its schema number raised,
so the failure was the cell and not the schema notice. On that page PROOF-244, PROOF-246,
PROOF-8 and PROOF-167 passed with the new fixture: the page already drew whatever word and
reasons the data holds. Those four hold what the fixture and the payload now say.

## Lines a person reads that this lane chose

None. Every line is the plan's: `checked at sign-off`, `no sign-off has checked it yet`, the two
`wording changed` lines, `1 is checked at sign-off.`, `<h> are checked at sign-off.`,
`· <k> by hand`, `<strong> of <n>`.

## Calls the plan did not make

1. **A rule whose every proof is `@manual` never reads its audit entry.** RULE-109 says its
   strong cell reads `checked at sign-off` throughout. Without this, an entry left from when
   the rule had a test would read `out of date` beside a passed cell that is not `passed`, and
   the table's `<n>` would differ from `summary.audit_counts`.
2. **The dashboard's `Strong` cell counts by the strong cell's word alone**, as `board.py` sums
   the five flags. Contract K4 says `summary.audit_counts` is the count; in a real payload the
   two agree, because a strong cell reads one of the five words only where the passed cell
   reads `passed`. PROOF-40's sample sets a passed word by hand and leaves the strong cell, and
   the plan's `2 of 3` is this reading.
3. **The `Tests` cell's share is in the pass tone once every rule passes or is checked by
   hand**, as the plan says of the `Passing` box. `1 by hand` is in the neutral tone.
4. **The `Strong` box is in the pass tone at `0` where the `Audit` box reads `0 of 0`**, the
   rule read as written.
5. **`states` PROOF-296 and PROOF-297 hand `rule_cells` its `hand_notes` and `hand_changed`
   directly.** Lane `signoff` fills `changed`; here it is always `[]`, so a test through a real
   sign-off could not pass in this lane.
6. **The hand check's passed cell is `current` and `counts`** in all three states.
7. **`spec_with_a_hand_check(rules)` is in `dev/mcp_project.py`**, shared by `dev/test_states.py`
   and `dev/test_summary.py`.
8. One commit holds the work: the status table, the page and the fixtures are compared with
   each other by `states` PROOF-58, so no part of it passes alone.

## The dashboard, looked at

`python3 dev/build_report.py`, then Playwright from the `.venv`, headless: the regulated sample
twice, once with invoice `RULE-3` not yet noted and once with its rule and proof reworded since
a note of `0.1.0`; both themes; 1500, 1280, 1024, 768 and 390 pixels; the board with login and
invoice open, invoice `RULE-3` and login `RULE-3`. 60 screens.

- Measured on every screen with the tests' own probes: 0 sideways scroll, 0 values broken
  across lines, 0 texts under 7 to 1 (4.5 to 1 for the dark theme's red and copper).
- Seen: the top boxes read `TESTS not met`, `SIGN-OFF signed 0.1.0, 4 commits since`,
  `AUDIT 3 of 7 strong`. `Passing` reads `7` over `11 RULES TOTAL`, in amber. Invoice's row
  reads `2 of 3 · 1 by hand`, `1 by hand` in teal, and `1 of 2` under `Strong`; login reads
  `3 of 4 · 1 partial` and `2 of 3`; `security_baseline`'s `Strong` cell is empty. Invoice
  `RULE-3`'s row carries no badge. The billing band reads `3 of 5 rules pass`.
- On invoice `RULE-3`: `CHECKED AT SIGN-OFF` in teal in the passed row, then
  `no sign-off has checked it yet`. Reworded, both rows read the two `wording changed` lines and
  then the note, and under the proof's tests each stands on its own line above the note. At 390
  pixels the reasons wrap as a sentence and the pill stays whole.
- Decision 123's finding, `PROOF-3: the AI says this breaks: ...`, was added to login `RULE-3`
  for the look only. It wraps as any long finding in the strong row and in the `Audit` panel,
  directly under `the test still passes when ...`. No change was needed, and the fixture does
  not hold it.

## Acceptance

```
192 passed in 78.75s (0:01:18)
```

over `dev/test_states.py`, `dev/test_summary.py`, `dev/test_backing_tests.py`,
`dev/test_failing.py`, `dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`
and `dev/test_report_refresh.py`. Then `bash dev/run_tests.sh --fast`:

```
843 passed, 9 skipped in 740.52s (0:12:20)
Suites: 1 passed, 0 failed
```

## Left, or waiting on another lane

- **The built page is not staged.** `scripts/report/purlin-report.html` on this branch is
  `main`'s, which reads schema 15. Run `python3 dev/build_report.py` at integration. The two
  doc screenshots change too: the board's `Passing` reads `7`, and invoice's row reads
  `2 of 3 · 1 by hand`.
- **Lane `signoff`** fills `hand_notes`' `changed`. Until it merges, no real project shows a
  `wording changed` line. A test through a real sign-off and a reworded rule belongs with
  `signatures` PROOF-272.
- **Lane `signoff`** brings `package.audit_counts` and a package result's `result` to K3 and
  K4; **lane `run`** writes `checked at sign-off` as the section's word. `summary.steps` now
  answers `by_hand` too; `package.py` reads `passed` alone from it, so the package's `steps`
  stays `{'passed': p}`.
- **`states` RULE-59 and `summary` RULE-20** are reworded for a sign-off found by its files.
  The code is `facts.py`, lane `signoff`'s, and its proof is `signatures` PROOF-274. No proof
  in this lane's specs shows that half until it merges.
- **Lane `words`**: any page that quotes the regulated sample's counts or the dashboard's
  `Strong` cell as `<n> of <rules>`.
