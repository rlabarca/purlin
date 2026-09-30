# Lane `words`, decision 102

Branch `lane/d102-words`, from `d102/base` at `24cf528`.

## Summary

Section 7's lines are written into the references, the guides and the 0.10.0 release notes, and
`docs/qa-guide.md`, `From criteria to a signature`, is new and first in the QA table of
`docs/index.md`. The docs sample with no test tool now holds `tests/cart_check.rb`.

## Ids

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/instructions/purlin_docs.md` | 12 (unchanged) | 17 (unchanged) |

No rule or proof was added, deleted or reworded: no proof of `purlin_docs` quotes a line this lane
changed.

## Tests

- `dev/test_purlin_docs.py`: 10 passed before the change of the sample, 10 passed after.
- `bash dev/run_tests.sh --fast`, after: 2141 passed, 3 failed, 12 skipped, 1 error. None is in
  a file this lane owns or reads a file it changed; each is this container's:
  - `dev/test_signatures.py::TestTheMachines::test_a_new_system_ends_nothing` and
    `::test_a_system_it_names_that_is_gone_ends_it` expect the machine's system to be `macos`;
    here it is `linux`.
  - `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name`:
    `git tag -v` goes through the container's global `gpg.ssh.program=/tmp/code-sign`, which
    supports only `-Y sign`.
  - `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`,
    error: the pip playwright wants `chromium_headless_shell-1243`, not at `/opt/pw-browsers`.

## Deliberate break

None in code, as section 4 says. `dev/test_purlin_docs.py` passes whole, and a grep of the lane's
files for `signature filenames`, `incoming one` and `> Highest-Proof: 2` is empty.

## What changed, by file

- `docs/specs-and-anchors.md`: the example's `> Highest-Proof:` reads 4; "Ids across branches"
  (the page's heading for "After a merge conflict") gives the collision rule, drops the rename
  advice, and says a spec holding a number twice or a conflict line reads `failed`.
- `docs/team-workflow.md`: who commits evidence and the conflict re-run; the collision rule; a new
  section `Releasing a version` for the release branch.
- `docs/working-together.md`: the QA section points at `qa-guide.md`; the drift table gains the
  proofs added, changed and moved and the ended signatures; a paragraph on numbers written twice,
  changed comments and that drift never fetches.
- `docs/review-and-signing.md`: the walk's tied test (the example gains two `tied to` lines), the
  verified commit, the hand check's binding, the ended-signature line and its causes, the two tag
  refusals as table rows, the signing refusal, the release branch; F13's consequences (test
  files whole, another computer).
- `docs/running-and-evidence.md`: plain `tests/test_*.py`; `### Who commits the evidence`.
- `docs/regulated-workflow.md`: the release branch; the flowchart gains the broken-spec and
  host-branch refusals; the signature counts only when its commit verifies, and ending prints a
  line.
- `docs/qa-guide.md`, new. `docs/index.md`: its row first under QA. `README.md`: one line pointing
  at it under Documentation.
- `references/hard_gates.md`: `to_repair` in the kinds table; "refuses nothing" gains its one
  exception; the verified commit; the hand check's binding; the ended line; the tag's two new
  conditions (it now writes "when all four hold").
- `references/glossary.md`: `release branch`, `to repair`; the hand check's binding; a counting
  signature verifies and its ending prints a line.
- `references/purlin_commands.md`: `purlin:sign` refuses a broken spec and a tag behind its host
  copy (writes row, exit codes, the two lines); `purlin:drift` reads only this checkout, names
  numbers written twice, never fetches; the run's exit 1 for a broken spec.
- `RELEASE_NOTES.md` 0.10.0: section 7's lines, plus the release branch and the collision rule;
  the formats line reads signature 13, package 6, schema 12.

## The QA page, statement by rule

| Section | Held by |
|---|---|
| Your criteria become proofs | `skill_spec` RULE-15 (pasted acceptance criteria), RULE-6 (print, ask, save), RULE-7 and RULE-11 (one case, 60 words), RULE-10 (the guideline), RULE-22 and RULE-3 (commit, closing line) |
| What the developer adds | `skill_build` RULE-12 (the marker), RULE-2 (tests through `purlin:test`); `skill_spec`'s guide, `@manual` (quality guide "Manual proofs") |
| The walk | `skill_sign` RULE-2 (what waits), RULE-6 (three answers, skip waits again), RULE-12 (what the audit found), RULE-22 (a case is a proof line); `signatures` RULE-101, PROOF-200 and PROOF-201 (tied test, lane `signing`); `skill_sign` RULE-25 (lane `skills`) |
| The signature | `skill_sign` RULE-5 (what it is made over); `signatures` RULE-96 (hand check), RULE-97 (verifies), both lane `signing` |
| What ends a signature | `states` RULE-103, RULE-104 (lane `counting`) |
| Drift after a pull | `drift` RULE-28 to RULE-34; `skill_drift` RULE-11, RULE-12 (lane `drift`) |
| Where the risk is | `skill_spec` RULE-28 (lane `skills`) |

## Words chosen that section 7 does not give

- `docs/team-workflow.md` heading `Releasing a version`; `docs/qa-guide.md` headings
  `Your criteria become proofs`, `What the developer adds`, `The walk`, `The signature`,
  `What ends a signature`, `Drift after a pull`, `Where the risk is`, and its opening paragraph
  naming the five steps.
- "`tied to no test` means no test carries that proof out yet."
- "Read the cause, look at what changed, and sign again when the rule still holds."
- "On `release/1.2.0` the tag keeps up with `origin/release/1.2.0`." and "On a release branch the
  ref is that release branch's, so the default branch moving on does not stop the tag."
- "A hand check is a rule whose every proof is `@manual` or has no test." (from section 9)
- "The walk names each test; open the file to read its body." (from section 9)
- "Move the test comments that name the moved id with it." (`docs/specs-and-anchors.md`)
- `references/hard_gates.md`: "**Purlin refuses nothing a person does, with one exception.**"
- The glossary's `to repair` definition, and the `to_repair` row's "When it applies".
- `docs/index.md`'s description of the QA page; `README.md`'s pointer line.
- The regulated flowchart's nodes `a spec to repair?`, `No tag: a feature cannot be counted`,
  `the branch on the host holds commits you lack?`, `No tag: pull, then purlin:test --commit`.
- `RELEASE_NOTES.md`: the two lines beyond section 7's, "A version is signed on a release
  branch..." and "When two branches take the same number...".

## Calls left

- `docs/getting-started.md` (no lane) lines 135-136 describe pytest detection as `conftest.py`,
  `pytest.ini` or `[tool.pytest` alone; after C13 it misses `tests/test_*.py`. Left as it is.
- `docs/how-purlin-works.md` (no lane) line 79: "A change to any of the six ends it, with no
  message"; after C4 a line is printed. Left as it is.
- `README.md` line 112 names the tag's conditions as "nothing is left to do and every result came
  from committed work"; it points at `hard_gates.md` for the rest. Left as it is.

## Failures in files this lane does not own

The three failures and one error of `--fast` above, each an environment matter of this container.

## Waiting for another lane

- `docs/qa-guide.md`'s link `../references/spec_quality_guide.md#where-the-risk-is` names a
  heading lane `skills` writes (section 7's "Where the risk is"); it resolves once that lane
  merges with that heading. No test of this lane reads it: `purlin_docs` PROOF-17 checks only
  the four pages.
- `purlin_docs` PROOF-8 needs no other lane: the sample holds no `test_*.py`.
