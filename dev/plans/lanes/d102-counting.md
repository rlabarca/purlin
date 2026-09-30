# Lane `counting`, decision 102

Built C3 (states, payload, summary), C4, C5 and C6 on `lane/d102-counting`, from `d102/base` at
`24cf528`. I ran it on Linux in a cloud session, with no real `claude` and no network service.

## Highest lines after the work

| Spec | `> Highest-Rule:` | `> Highest-Proof:` |
|---|---|---|
| `specs/mcp/states.md` | 105 (was 101) | 259 (was 247) |
| `specs/mcp/summary.md` | 16 (was 15) | 41 (was 39) |
| `specs/skills/skill_status.md` | 11 (unchanged) | 35 (unchanged) |

New: states RULE-102 to RULE-105 with PROOF-248 to PROOF-259; summary RULE-16 with PROOF-40 and
PROOF-41. Each proof has one case, at most 46 words, and a marked test of its own.

## Tests

- My own files, run whole (`dev/test_states.py`, `dev/test_summary.py`,
  `dev/test_backing_tests.py`, `dev/test_failing.py`, `dev/test_skill_status.py`):
  - Before: 259 passed.
  - After: 273 tests, 268 passed and 5 failed. Each failure waits for another lane (listed
    below).
- With a stand-in for C1's `broken_reasons` (never committed, removed with
  `git checkout -- scripts/mcp/purlin/specs.py`), every new test passed.
- `bash dev/run_tests.sh --fast`: 2150 passed, 9 failed, 12 skipped. The 9 failures:
  - 5 in my files, waiting for other lanes.
  - 1 in a file I do not own, caused by C5 (below).
  - 3 that also fail on `d102/base` in this container:
    - `dev/test_signatures.py` PROOF-121 and PROOF-122 assume the machine is macOS.
    - `dev/test_tag.py` "the tag is signed with the key the settings name" is stopped by the
      container's `code-sign` hook on `git tag -v`.
- The browser test needs `playwright==1.56.0` in the `.venv` to match
  `/opt/pw-browsers/chromium-1194`. It was installed only in the local `.venv`; nothing about it
  is committed.

## Deliberate breaks

- **Break 1.** I passed `spec_broken: []` to `rule_cells` in `payload.py`. The test for
  PROOF-248 failed. I restored the file with `git checkout -- scripts/mcp/purlin/payload.py` and
  the test passed again.
- **Break 2.** I dropped `CAUSE_TEST` from the causes in `states.py`. The test for PROOF-252
  failed. I restored the file with `git checkout -- scripts/mcp/purlin/states.py` and the test
  passed again.

## Rules and proofs reworded

None were deleted.

- **states RULE-20.** A signature that no longer binds gives RULE-103's reason where it ended,
  and no reason otherwise. It used to say "gives no reason".
- **states PROOF-72.** Now reads the one reason
  `the signature by jane@acme.com ended because what the audit found changed`. Its test was
  renamed to `test_a_new_strength_ends_the_signature_and_says_why`.
- **states RULE-27, PROOF-31, PROOF-96.** Schema 12. PROOF-31's test was renamed to
  `test_schema_twelve_...`.
- **states RULE-64.** Now opens "For the specs with no `> Scope:` line". A scope that finds no
  file now prints C5's line.
- **skill_status PROOF-24.** Now reads "from `specs to repair`". The status skill's closing
  table adds `<n> specs to repair` to its `purlin:spec` row. It gains no line and stays at 100.
  The row reader in `dev/test_skill_status.py` now also strips `<n> ` from `specs to repair`.

## Calls left

1. **The signed cell keeps `waiting` (RULE-73 and PROOF-94 kept).** When a signature ended and
   the strong cell is not met, the signed cell still reads `waiting` with
   `waiting for the audit`. The `ENDED` reason replaces the reason only where the cell reads
   `unsigned`. The ended line is printed in the status at every gate either way.
   - Because of this, PROOF-252 and PROOF-253 run the tests and the audit again after the edit.
   - C4 says the cell "reads `unsigned` with the one reason `ENDED`". Read literally, that would
     break RULE-73.
2. **A newer non-counting signature keeps its own reason.** Where a signature that binds but
   does not count exists, the signed cell keeps that signature's reason (RULE-22), for example
   `the commit that added it is not signed`, not `ENDED`.
3. **No ended line when no field differs.** Where the newest counting signature no longer binds
   but none of the compared fields differs, for example a signature file whose `signed_hash` was
   made under an older binding, no ended line and no reason are given.
4. **A broken spec's cells.** For a rule of a broken spec, `ended` is still computed and printed.
   Its strong cell reads `waiting` with `waiting for its tests to pass`. Its signed cell reads
   `waiting` with `waiting for the audit`, and its signer fields are empty.
5. **Which kind is compared for a hand check.** The kind comes from the rule's current
   `test_hash_kind`, else the signature's. `payload.py` now passes `test_hash_kind` into
   `rule_cells`' input, so lane `signing`'s `is_current` (C8) can read it from the entry it is
   given.
6. **`broken_reasons` read through `getattr`.** `payload.spec_broken(info)` calls
   `specs.broken_reasons` through `getattr`, so this branch runs before lane `reader` merges.
   Integration may replace it with a direct call once C1 is in.

## Words chosen that section 7 does not give

- `none`: the file list of `CAUSE_TEST` for a rule that names no test file now, giving
  `a test file behind it changed: none`.

## Failures in files I do not own

- **`dev/test_schema_spec_format.py` PROOF-55 (lane `reader`).**
  - The test is
    `test_a_scope_whose_every_entry_finds_nothing_gets_only_the_existing_line`.
  - Under C5, a `> Scope:` that finds no file now prints
    `1 spec's > Scope: finds no file in git yet, ...`, not `1 spec names no files, ...`.
  - The proof in `specs/mcp/schema_spec_format.md` and its test quote the old line. They need
    C5's singular line.
- **`docs/specs-and-anchors.md`, lines 79 to 83 (lane `words`).** They still say that a spec
  whose entries reach no tracked file prints the "names no files" line.
- **`specs/init/update.md`.** It quotes `incomplete_line`, which the upgrade still calls for
  specs with no `> Scope:` line alone. Its words did not change, so nothing breaks there.

## Tests that fail only because another lane has not merged

- **Waiting for lane `reader` (`specs.broken_reasons`, C1):** states PROOF-248, PROOF-249 and
  PROOF-251. PROOF-250 passes already, since both of its specs read as sound without the reader.
- **Waiting for lane `dashboard` (schema 12 fixtures with `broken` and `ended`):** states
  PROOF-82 and PROOF-96.
- **Summary PROOF-40 and PROOF-41 do not wait.** They build the payload by hand with a
  feature's `broken`, so they pass now.
