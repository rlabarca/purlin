# Lane d102 `drift`: report

Built C7 on `lane/d102-drift` from `origin/d102/base`: `drift.default_branch(project_root)`,
`drift.fetched_age(project_root, ref)`, the numbers written twice, the test comments whose proof's
wording changed, the age line, the proofs added, changed and moved in `pm` and `qa`, and the
ended signatures in `qa`. Files written: `scripts/mcp/purlin/drift.py`, `specs/mcp/drift.md`,
`dev/test_drift.py`, `references/drift_criteria.md`, `skills/drift/SKILL.md` (75 to 88 lines, ceiling
150), `specs/skills/skill_drift.md`, `dev/test_skill_drift.py`, and this report.

## Highest lines after the work

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/mcp/drift.md` | 34 (was 27) | 80 (was 66) |
| `specs/skills/skill_drift.md` | 12 (was 10) | 38 (was 36) |

New: drift RULE-28 to RULE-34, PROOF-67 to PROOF-80; skill_drift RULE-11, RULE-12, PROOF-37,
PROOF-38. Every new or rewritten proof holds one case in at most 60 words (the longest, PROOF-75, is 55)
and has a marked test of its own.

## Tests

| File | Before | After |
|---|---|---|
| `dev/test_drift.py` | 64, all pass | 78: 73 pass, 5 wait for other lanes (below) |
| `dev/test_skill_drift.py` | 13, all pass | 15, all pass |

`dev/test_security.py` passes whole: every new git call hands its ref after `--end-of-options`.
With a scratch stand-in for C1's keys (not committed), all of `dev/test_drift.py` passes except
PROOF-78.

`bash dev/run_tests.sh --fast`: 2149 passed, 12 skipped, 11 failed, 1 error before the
`--end-of-options` fix. After that fix, the failures are the 5 waits below and the 4 in files
this lane does not own, listed further down.

Deliberate break: `numbers_twice` took the line holding the default branch's text as the one that
moves; PROOF-70's test failed (run with the C1 stand-in), then
`git checkout -- scripts/mcp/purlin/drift.py` restored it and the test passed.

## Rules and proofs deleted or reworded

- drift PROOF-49 reworded: it held three cases (the keys of `pm`, `eng` and `qa`). It now holds the
  `pm` keys, new keys included. The `eng` keys moved to the new PROOF-79 and the `qa` keys to the new
  PROOF-80, each with its own test. The plan gives no ids for these two, so they take the next free
  numbers after PROOF-78.
- drift PROOF-12: wording unchanged. Its test's new `login` keeps its proofs as they were, so the
  PM view still reads exactly the three rule lines (it would otherwise print `1 proof added`).
- The Description of `specs/mcp/drift.md` names the new lines.
- Nothing deleted.

## Calls this lane made

- **The age reads the reflog entry's own time.** C7 names
  `git reflog show -1 --format=%ct refs/remotes/<ref>`, but `%ct` gives the time of the commit
  the entry points at, not the fetch. Drift reads `--date=unix --format=%gd` (`<ref>@{<secs>}`),
  which is the time C7 describes. The criteria name that command.
- **`summary.ended_lines`** is called only where it exists (`getattr`), so the `qa` view works
  before lane `counting` merges. Integration may call it directly once it has merged.
- **C1's keys** are read with `.get`: `doubled_lines`, `doubled_rules`, `doubled_proofs`,
  `highest_rule`, `highest_proof`. Order is rule ids first, then proof ids, each in the order
  first written.
- **Several numbers written twice in one spec** each take the next number after the one before, so
  two suggestions never collide.
- **More than two lines under one id**: the first line that is not the keeper is the one named
  to move.
- **"The default branch writes it twice too"**: the line quotes the checkout's last line under
  that id as "the second".
- **Default branch present, spec absent there**: read as neither line being on the default branch
  (the second form).
- **A proof moved and then given new text** is listed both as moved and as changed, as C7 says
  literally ("an id whose text differs is changed").
- **A move target** must be an id that did not already hold that text at the range's start.
- **Test comments**: `git blame` on the working-tree file. A line not yet committed is skipped,
  and so is a comment whose proof is absent now or at the blamed commit. A proof "whose text
  differs between the range's two ends" includes a proof added in the range.
- **The age line** prints only when a number is written twice and a default branch exists. With
  no default branch the fourth form already says so.
- **`default_branch` in JSON** is computed in every view, `{"ref", "age_seconds"}` or null, even
  when no line prints.
- **JSON shapes C7 leaves open:**
  - `numbers_twice`: `[{feature, id, to, text, line}]`, where `text` is null in the forms that
    quote none.
  - `comments_changed`: `[{file, line, feature, id, commit, old, new, now_under, text}]`.
- **`references/drift_criteria.md`** goes from Criteria-Version 10 to 11 for the new lines.

## Words chosen that section 7 does not give

- Drift criteria: the section `### Every view`, its paragraphs, and the case table.
- Skill:
  - The paragraph "Drift reads only this checkout: it never fetches, pulls or reaches the host.
    When it names a number written twice it also says how old this checkout's copy of the
    default branch is. If that copy is old, run `git fetch`, then run drift again."
  - The section "A number written twice": "The line already on the default branch keeps the
    number; the other line moves to the number drift names. Renumber that line with
    `purlin:spec <feature>`, move the test comments that name it, and tell the person whose line
    moved so the comments on their branch move with it."
- Skill closing-table rows:
  - `A proof added, changed or moved` → `→ Run: purlin:build <feature>`
  - `A signature that ended` → `→ Run: purlin:sign`
  - `A number written twice` → `→ Run: purlin:spec <feature>`
  - `A test comment whose proof's wording changed` → `→ Run: purlin:build <feature>`
  - `How old the copy of the default branch is` → `→ Run git fetch, then purlin:drift again.`

## Failures in files this lane does not own

These also fail on a clean checkout of `origin/d102/base` in this container, so they come from the
environment, not from this lane:
- `dev/test_signatures.py::TestTheMachines::test_a_new_system_ends_nothing` and
  `::test_a_system_it_names_that_is_gone_ends_it`: the fixture expects a `macos` machine, and the
  container is Linux.
- `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name`: the cloud
  runner's code-sign helper refuses `git tag -v`.
- `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`
  (error): the pip `playwright` wants `chromium_headless_shell-1243`, which `/opt/pw-browsers`
  does not hold.

## Tests that fail only because another lane has not merged

- drift PROOF-70, PROOF-71, PROOF-72, PROOF-73: they need `doubled_lines` / `doubled_proofs` from
  lane `reader` (C1). PROOF-73 is also on this list because its age line prints only beside a
  number written twice.
- drift PROOF-78: it needs `summary.ended_lines` from lane `counting` (C4). The rule reads `signed`
  before the edit today, so only counting's line is missing.
