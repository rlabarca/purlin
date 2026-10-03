# Decision 128, lane `run4`: the report

Branch `lane/d128-run4`, two commits of work on `main` at `ff3a7be98`, then this report.
Acceptance: the four test files, `165 passed`; `bash dev/run_tests.sh --fast` ended
`1124 passed, 9 skipped`, `Suites: 1 passed, 0 failed`. Nothing is pushed, tagged or
signed. No file under `references/formats/` changed.

## What was built, per item

**4. `purlin:status <name>` shows one spec's rules.** `scripts/run/purlin_status.py`,
`spec_lines` and `view_lines`. `--spec <name>` prints, where the spec has a mistake, each
warning that names it (the check as before), then an empty line; then the spec's view: its
path and rule count, one line per rule in the spec's order with its two cells' words, under
it each reason of a cell that reads neither `passed` nor `strong` as `<word>: <reason>`, the
passed cell's first, then one line per proof with its result and its first test, each further
test set under the first. A rule no proof line names lists the tests marked with its id.
Exit 1 where a warning was printed, else 0; a name no spec has is said so, exit 1, as before.
The view is read from the payload and writes nothing. The status skill's part `With a name`
now runs the script and its example is what the script prints (held by a test).

**6. An anchor's `Tests` cell says how many of its rules are out of date.**
`scripts/mcp/purlin/board.py`: `tests_cell(rollup, out_of_date=0)` appends `· <n> out of date`
after `by hand`, `partial` and `failing`; `out_of_date_rules(rules)` counts the rule entries
whose passed cell reads `out of date` (`states.OUT_OF_DATE`); `row_cells` takes the entry's
`rules` and passes the count for an anchor only. `status._row` hands it the rules. The rollup
and the payload are unchanged, so lane `dashboard4` counts from the rules' passed cells, as
the plan says.

## Rules and proofs, word for word

`specs/mcp/server.md`: `Highest-Rule` 41 to 44, `Highest-Proof` 177 to 185.

- RULE-41 reworded: `purlin_status.py --spec <name>` prints first the warnings that name that spec, where it has any, then an empty line and the spec's view, and exits 1 where it printed a warning and 0 where it printed none; a name no spec of the checkout has prints only `<name>: no spec of this checkout has that name. Run purlin:status to see its specs.` and exits 1
- RULE-42: The spec's view opens on `<spec path>: <n> rules`, `1 rule` for one, then gives one line per rule in the order the spec writes them, `  <RULE-N>  <passed cell's word>  <strong cell's word>`, for an anchor as for a feature
- RULE-43: Under a rule's line, each reason of a cell whose word is neither `passed` nor `strong` reads `    <the cell's word>: <reason>`, the passed cell's reasons first; a cell reading `passed` or `strong` shows no reason
- RULE-44: After the reasons, each proof of the rule reads `    <PROOF-N>  <the proof's result>  <file>::<test name>`, each further test of the proof on a line of its own, set under the first; a proof with no test reads `    <PROOF-N>  <the proof's result>`; a rule no proof line names lists each test marked with its own id as `    <RULE-N>  <file>::<test name>`
- PROOF-175 reworded (RULE-41): `login` carries `> Requires: api`; `purlin_status.py --project-root <dir> --spec login` prints first `login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.`, then an empty line, then `specs/auth/login.md: 2 rules`, and exits 1
- PROOF-176 reworded (RULE-41): `login` holds 2 rules and 3 proofs and no mistake; `purlin_status.py --project-root <dir> --spec login` prints first `specs/auth/login.md: 2 rules`, holds no line naming a mistake, and exits 0
- PROOF-178 (RULE-41): In a project whose one spec is `login`, `purlin_status.py --project-root <dir> --spec signup` prints only `signup: no spec of this checkout has that name. Run purlin:status to see its specs.` and exits 1
- PROOF-179 (RULE-42): `login` of 2 rules, `RULE-1`'s test passed in a current section and `RULE-2` with no test; `--spec login` prints `specs/auth/login.md: 2 rules` first, and its rule lines are `  RULE-1  passed  not audited` and then `  RULE-2  no test  waiting`
- PROOF-180 (RULE-42): The anchor `security` of 1 rule that no test carries; `--spec security` prints `specs/_anchors/security.md: 1 rule` first and `  RULE-1  no test  waiting` second
- PROOF-181 (RULE-43): In that `login`, the two lines under `  RULE-2  no test  waiting` are `    no test: no test for PROOF-2` and `    waiting: waiting for its tests to pass`, and the line under `  RULE-1  passed  not audited` is `    not audited: no audit has read this rule`
- PROOF-182 (RULE-43): With `RULE-1` found strong by the audit, the line under `  RULE-1  passed  strong` is `    PROOF-1  passed  tests/test_login.py::test_proof_1`
- PROOF-183 (RULE-44): In that `login`, `RULE-1`'s last line is `    PROOF-1  passed  tests/test_login.py::test_proof_1` and `RULE-2`'s is `    PROOF-2  no test`, the last line printed
- PROOF-184 (RULE-44): `PROOF-1` is carried by `test_proof_1` and `test_proof_1_again`, both passing in a current section; the two lines after `RULE-1`'s reason are `    PROOF-1  passed  tests/test_login.py::test_proof_1` and `                     tests/test_login.py::test_proof_1_again`
- PROOF-185 (RULE-44): `login` of 1 rule and no proof line, its test `test_rule_1` marked with `RULE-1` and passing in a current section; the last line printed is `    RULE-1  tests/test_login.py::test_rule_1`
- The tests of PROOF-175 and 176 changed on their kept lines.

`specs/mcp/states.md`: `Highest-Rule` 136 to 137, `Highest-Proof` 322 to 325.

- RULE-137: An anchor's `Tests` cell in the status table appends `· <n> out of date` after its other parts, `<n>` counting the anchor's rules whose passed cell reads `out of date`; a feature's `Tests` cell never carries it
- PROOF-323 (RULE-137): The anchor `security` of 11 rules, each passing in a section taken before a commit that changes `src/login.py`, reads `0 of 11 · 11 out of date` in its `Tests` cell
- PROOF-324 (RULE-137): The anchor `security` of 3 rules, `RULE-3`'s one proof `@manual` and the other two passing in a section taken before a commit that changes `src/login.py`, reads `0 of 3 · 1 by hand · 2 out of date` in its `Tests` cell
- PROOF-325 (RULE-137): The feature `login` of 2 rules, both passing in a section taken before a commit that changes `src/login.py`, reads `0 of 2` in its `Tests` cell

`specs/skills/skill_status.md`: `Highest-Rule` 17 to 19, `Highest-Proof` 42 to 46.

- RULE-18: The skill's part `With a name` gives the command that prints one spec's view: a line naming `scripts/run/purlin_status.py` and `--spec <name>`
- RULE-19: The example in the skill's part `With a name` is, line for line, what `purlin_status.py --spec login` prints for `login` of 3 rules: `RULE-1`, whose test passed and which the audit found strong; `RULE-2`, which no test carries; and `RULE-3`, whose one proof is `@manual`
- PROOF-43 (RULE-18): The status skill as shipped holds, in its part `With a name`, a line naming both `scripts/run/purlin_status.py` and `--spec <name>`
- PROOF-44 (RULE-18): A copy of the status skill with every `--spec <name>` taken out holds no such line in that part
- PROOF-45 (RULE-19): The code block of the shipped skill's part `With a name` equals, line for line, what `purlin_status.py --spec login` prints for that `login`
- PROOF-46 (RULE-19): A copy of the status skill whose example reads `PROOF-1  passed` as `PROOF-1  passing` does not equal it

## Seen failing first

Against the code before each change: `server` PROOF-175, 176 and 179 to 185 (9 failed; 178
passes on `main`, which already said so); `states` PROOF-323 and 324 (`0 of 11` and
`0 of 3 · 1 by hand`; PROOF-325 says a part is absent and passes either way); `skill_status`
PROOF-43 to 46 against `main`'s skill file.

## On the real copies

A `cp -Rc` copy of `RLabGenMusic-upgrade-4` at `40bf938`, in the scratch folder.

- **4**, one feature, `--spec bus_chain`, exit 0 (first three of seven rules):

  ```
  specs/sunvox/bus_chain.md: 7 rules
    RULE-1  passed  not audited
      not audited: no audit has read this rule
      PROOF-1  passed  packages/sunvox-project/test/bus_chain.integration.test.ts::bus_chain > creates buses between the stems and the master and wires every node where it is routed
    RULE-2  passed  not audited
      not audited: no audit has read this rule
      PROOF-2  passed  packages/sunvox-project/test/bus_chain.integration.test.ts::bus_chain > builds the graph it built before buses when there are none, and sends unrouted stems to the master
  ```

  The spec writes `RULE-7` before `RULE-6`, and the view keeps that order.
- **4**, one anchor, `--spec honest_answers`, exit 0:

  ```
  specs/_anchors/honest_answers.md: 4 rules
    RULE-1  passed  not audited
      not audited: no audit has read this rule
      PROOF-3  passed  packages/web/test/honest_answers.browser.test.tsx::honest_answers > a refused write is not remembered and never reached the engine
    ...
    RULE-4  passed  not audited
      not audited: no audit has read this rule
      PROOF-4  passed  packages/web/test/honest_answers.browser.test.tsx::honest_answers > what a control can set, a control can read — as the value, not as a sentence
  ```

  With one tracked file edited, the same anchor reads:

  ```
  specs/_anchors/honest_answers.md: 4 rules
    RULE-1  out of date  waiting
      out of date: code changed since 4512b28
      waiting: waiting for its tests to pass
      PROOF-3  not run  packages/web/test/honest_answers.browser.test.tsx::honest_answers > a refused write is not remembered and never reached the engine
  ```
- **4**, this repository, `--spec ai_audit`, exit 0, 226 lines, 45 rules: 24 read
  `passed  out of date`, 21 `passed  not audited`. The first rule:

  ```
  specs/review/ai_audit.md: 45 rules
    RULE-1  passed  out of date
      out of date: code changed since 0c02885
      out of date: the last audit found it strong on 2026-10-02
      PROOF-4  passed  dev/test_ai_audit.py::TestWhichRulesAreRead::test_a_rule_with_an_entry_for_its_text_proof_test_and_code_is_not_read
      PROOF-103  passed  dev/test_ai_audit.py::TestWhichRulesAreRead::test_a_rule_whose_feature_code_changed_since_its_entry_is_read
      ...
  ```

  `git status` was the same before and after: the view writes nothing.
- **6**, the copy after one blank line was added to the tracked `samples/README.md`:

  ```
  Purlin status: rlab-gen-music, plugin 0.10.0
  Tests: not met
  Sign-off: not signed

  Spec                  Rules  Proofs  Tests
  ─────────────────────────────────────────────────────────────
  Anchors
  rlab_design_system    11     11      0 of 11 · 11 out of date
  honest_answers        4      4       0 of 4 · 4 out of date
  Specs
  bus_chain             7      7       7 of 7
  ...
  476 rules. 461 pass their tests.
  Left to do:
    15 rules to test: purlin:test
  ```

  `main`'s status on the same copy reads `0 of 11` and `0 of 4`. Before the edit both anchors
  read `11 of 11` and `4 of 4`, unchanged.

## Lines chosen

- The view's opening: `<spec path>: <n> rules` (`1 rule`), from the skill's example.
- A rule's line: `  <RULE-N>  <passed word>  <strong word>`, the cells' own words.
- A reason's line: `    <the cell's word>: <reason>`, so the reader sees which cell it is.
- A proof's line: `    <PROOF-N>  <result>  <file>::<test name>`, the result being the
  payload's own word for the proof (`passed`, `failed`, `not run`, `no test`, `hand check`).
- The skill: `The tool shows every spec at once, so for one spec run the script with the spec's
  name, the file name without .md:`, `Print what it prints. It opens on ...`, `Where the spec has
  a mistake, the script prints each mistake first, as the status's warnings word it. The view
  writes nothing.`; in Step 2, `An anchor's cell then adds · <k> out of date, as in 0 of 11 ·
  11 out of date: an anchor covers the whole project, so a change to any tracked file puts its
  results out of date until the next run.`
- `docs/running-and-evidence.md`: `An anchor covers the whole project, so a change to any
  tracked file puts its rules out of date, and its Tests cell counts them: 0 of 11 · 11 out of
  date.`

## Calls the plan did not make

1. **The status tool takes no spec's name, so it gains no view.** The plan says "if it takes
   one"; `sync_status` takes `project_root` alone, and adding a parameter would change the
   tool's schema. The skill's part `With a name` runs the script instead (skill_status RULE-18).
2. **The skill's example was not what the code can print, and was corrected.** It put the proof
   on the rule's line, named `RULE-1`, `RULE-3` and `RULE-5` of `8 rules`, printed the spec's
   header, and used `no test carries this marker` and `a hand check`, words no cell carries. It
   now shows three rules of a sample project and is held, line for line, to what the script
   prints for that project (RULE-19).
3. **A clean spec no longer prints `login: 2 rules and 3 proofs read. No mistake found.`**: the
   view takes its place, opening on the path. The exit codes are unchanged, so `purlin:spec`'s
   check still works, but two files of no lane this round now describe the old line (below).
4. **A strong cell reading `not audited` or `waiting` shows its reason**, as the plan's
   "not `passed` or `strong`" says; on an unaudited project every rule carries the line
   `not audited: no audit has read this rule`.
5. **A proof of several tests shows the proof's result once**, on the first test's line; the
   further tests stand under it without a result.
6. **The out-of-date count is read from the rules' passed cells, not from the rollup.** The
   rollup holds no such count, and adding one would change the payload, which is
   `dashboard4`'s file. `board.out_of_date_rules` is the one count, for the terminal.
7. Two commits: one per item; the skill file's lines were split between them.

## Left, or waiting on another lane

- `skills/spec/SKILL.md` step 7 (no lane owns it this round), replace
  `It prints each mistake Purlin sees in the spec, or \`<name>: <n> rules and <m> proofs read. No
  mistake found.\`` with
  `It prints each mistake Purlin sees in the spec first and exits 1, or, with none, opens on the
  spec's path and its rule count and exits 0.`
- `references/purlin_commands.md` lines 68 to 73 (no lane owns it), replace with:
  `With \`--spec <name>\` it prints each mistake Purlin sees in that spec, then an empty line, and
  exits 1, or exits 0 where it sees none; either way it then prints that spec's view: its path and
  rule count, one line per rule with its two cells, the reasons of a cell that reads neither
  \`passed\` nor \`strong\`, and its proof lines. A name no spec has prints only:` and keep the one
  example line `login: no spec of this checkout has that name. Run purlin:status to see its specs.`
- `scripts/report/src/board.js` mirrors `board.tests_cell`: lane `dashboard4`'s item 6. Until it
  merges, a dashboard and a table over an anchor whose results are out of date differ in that
  cell (states RULE-49).
- Not run: the full `bash dev/run_tests.sh`, `dev/windows_run.py`.
