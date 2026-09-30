# Lane `reader` of decision 102: report

Branch `lane/d102-reader`, from `origin/d102/base` at `ac4a55b`. Built C1 and C2 of
`d102-plan.md` in `scripts/mcp/purlin/specs.py`, with `references/formats/spec_format.md`,
`specs/mcp/schema_spec_format.md` and `dev/test_schema_spec_format.py`.

## Highest lines after the work

| Spec | `> Highest-Rule:` | `> Highest-Proof:` |
|---|---|---|
| `specs/mcp/schema_spec_format.md` | 37 (was 34) | 85 (was 80) |
| `specs/mcp/specs.md` | 21 (unchanged) | 43 (unchanged) |

New: RULE-35, RULE-36, RULE-37; PROOF-81 to PROOF-85, each one case under 60 words (41, 32, 39,
23, 44 words) with a marked test of its own. No number reused. `specs/mcp/specs.md` did not
change: no reader test broke.

## What was built

- `scan_specs` gives `doubled_proofs`, `doubled_lines`, `conflict_lines`, `highest_rule`,
  `highest_proof` as C1 says. A proof id written twice is read once, in the place first written,
  with the text of its last line, as a rule id is.
- `CONFLICT_RE`, `DOUBLED_REASON`, `CONFLICT_REASON` and `broken_reasons(info)` word for word.
- `PROOF_WRITTEN_TWICE`, `CONFLICT_ONE`, `CONFLICT_MANY` word for word; `spec_mistakes` prints
  them after the `RULE_WRITTEN_TWICE` lines and before the `PROOF_LINE_UNREAD` lines, the quoted
  line cut to `PROOF_LINE_SHOWN` (60).
- `spec_format.md` stays at format 21: "Rules format" gives section 7's collision sentence in its
  id paragraph, says a rule written twice and a conflict line make every rule read `failed`, and
  defines the conflict line; "Proof format" says the same of a proof written twice.

## Tests

- `dev/test_schema_spec_format.py`: 72 passed before, 77 passed after.
- `dev/test_specs_reader.py`: 40 passed and 1 skipped before and after.
- `bash dev/run_tests.sh --fast`: 2146 passed, 12 skipped, 3 failed, 1 error. All four fail the
  same way on `origin/d102/base` without this lane's commit (checked in a separate worktree).
- Deliberate break: `doubled_proofs` stopped being added to; PROOF-81's test failed (and
  PROOF-85's); restored with `git checkout -- scripts/mcp/purlin/specs.py`; both pass.

## Rules and proofs deleted or reworded

None.

## Calls left

- C1's `doubled_lines`, `conflict_lines`, `highest_rule` and `highest_proof` carry no proof in
  this lane: the plan gives this lane no rule for them and leaves `specs/mcp/specs.md` unchanged.
  Lanes `drift` and `counting` read them through their own proofs.
- A proof id written twice under two rules still lists the id in `proofs_by_rule` under both
  rules, while `proofs[id]['rules']` holds the last line's rules alone. Left as it was ("nothing
  else about how a spec is read changes"); the spec now reads `failed` until it is fixed.

## Words chosen that section 7 does not give

- RULE-35: `A proof number written twice is warned of, and the proof is read once, with the text of its second line` (the plan's wording).
- RULE-36: `A line left from a merge conflict is warned of with its line number` (the plan's).
- RULE-37: `The reasons a spec's rules fail are named in order: each rule number written twice, then each proof number written twice, then a line left from a merge conflict`.
- PROOF-85 reads `has the reasons its rules fail named in this order:` where the plan wrote `gives`,
  so the proof names what is read, not a function.
- `spec_format.md`: `A line left from a merge conflict, one opening with seven <, =, > or | followed by a space or the line's end, is warned of with its line number, and every rule of the spec reads failed, with the reason ..., until it is taken out. A line of eight = is not one. The spec is otherwise read as written, both sides' lines included.`; `... until one of the two lines is renumbered.`; `A line left from a merge conflict fails the spec wherever it stands in the file, as "Rules format" says.`

## Failures in files this lane does not own

All four fail identically on `origin/d102/base`; each comes from the cloud container, not code:

- `dev/test_signatures.py::TestTheMachines::test_a_new_system_ends_nothing` and
  `::test_a_system_it_names_that_is_gone_ends_it`, and
  `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name`: the
  container's git signing program (`environment-runner code-sign`) refuses every operation but
  `-Y sign`, so verifying a signed commit or tag fails.
- `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`
  (error at setup): the pip `playwright` wants a browser build `/opt/pw-browsers` does not hold.

## Tests that fail only because another lane has not merged

None.
