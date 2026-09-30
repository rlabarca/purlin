# Lane `run` of decision 102

Built on `lane/d102-run` from `d102/base` at `24cf528`, in a Linux cloud session. The lane builds
C13, the exit on a broken spec, the audit that skips a broken spec, and the evidence write that
keeps matching audits from a file a merge left conflicted.

## What was built

- `scripts/mcp/purlin/frameworks.py`: the pytest detector also answers yes where `tests/` at the
  root holds a `test_*.py` at any depth. The walk skips the same folders detection skips
  elsewhere (dot folders, `node_modules`, `bin`, `obj`, `mutants` and the fixture folders).
- `references/supported_frameworks.md`: the pytest row reads C13's words exactly.
- `scripts/run/purlin_run.py`:
  - `broken_specs(features)` names the features whose `specs.broken_reasons(info)` is not empty.
  - `--test` and `--audit` exit 1 when any spec is broken, whichever features ran, after every
    test has run and printed. A run that selected nothing exits 1 the same way. `--ci` is
    unchanged: RULE-12 says it exits on its tests alone.
  - `--audit` reads no rule of a broken spec.
  - `write_sections` reads each side of a conflicted evidence file before writing. After the
    new sections are written it takes each rule's current hashes from the payload and writes
    the audit entries that match back into the file.
- `scripts/run/evidence.py`: `conflict_sides`, `read_conflicted` and `kept_audits`. The lines
  outside a hunk belong to both sides. The lines after `<<<<<<<` make one side and those after
  `=======` the other. A `|||||||` base belongs to neither side.
- `references/formats/evidence_format.md` gains one bullet under "How a writer merges". The
  version stays 7.

## Highest lines after the work

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/run/run_script.md` | 89 | 264 |
| `specs/run/evidence_writer.md` | 26 | 89 |

New rules and proofs: `run_script` RULE-87 with PROOF-261, RULE-88 with PROOF-262 and PROOF-263,
RULE-89 with PROOF-264; `evidence_writer` RULE-26 with PROOF-88 and PROOF-89. Each proof has a
marked test of its own.

## Tests before and after

`dev/test_run_script.py` and `dev/test_evidence_writer.py`: 286 collected before (285 passed, 1 skipped);
292 collected after. Run whole on the branch, 289 pass, 1 is skipped (Windows only), and the 2
tests waiting for lane `reader` fail. With a throwaway `broken_reasons` stub in `specs.py`, never
committed and restored with `git checkout`, all 291 pass and 1 is skipped.

`bash dev/run_tests.sh --fast`: 2144 passed, 6 failed, 12 skipped, 1 error. See the last two
sections.

Deliberate break: `kept_audits` was made to return no entries. PROOF-88's test failed and
PROOF-89's still passed. `scripts/run/evidence.py` was restored with `git checkout --`, and both
tests passed again.

## Rules reworded

- `run_script` RULE-11: the `--test` exit now reads "1 where a test failed, evidence is missing,
  a marker names nothing a spec has or RULE-87 applies, 0 otherwise". Without this change it
  would contradict RULE-87.
- `run_script` RULE-69: now ends "exits on them, except as RULE-87 says", for the same reason.

No rule or proof was deleted.

## Calls left

- `broken_specs` reads `specs.broken_reasons` through `getattr`. Until lane `reader` merges, no
  spec reads as broken, so every other run test passes on this branch. After the merge,
  integration may make it a direct call.
- `evidence.py` has its own conflict-line pattern. It matches C1's `CONFLICT_RE` and also
  accepts `|||||||`. Once lane `reader` merges, integration may point it at
  `specs.CONFLICT_RE` so the pattern lives in one place.
- The recovery keeps only audits. A conflicted file's sections for other systems are not
  recovered, because the contract names audits alone. The next run on each system writes its
  own section again.
- `--ci` does not exit 1 on a broken spec (RULE-12). The plan's call covers "the test run".

## Words chosen that section 7 does not give

- The text of RULE-87, RULE-88, RULE-89 and RULE-26, and the proof texts, which follow
  section 4's wording.
- No new printed line: the run prints nothing of its own about a broken spec. The warnings of C2
  print through the status.

## Failures in files this lane does not own

- `dev/test_purlin_docs.py::TestQuotedLines::test_the_no_tool_line_is_printed_by_that_run`
  (purlin_docs PROOF-8) fails because the docs sample's `tests/test_cart.py` is now detected as
  pytest. The plan expects this and lane `words` fixes it.
- `docs/getting-started.md:135-136` says the first run recognises pytest only by
  `conftest.py`, `pytest.ini` or `[tool.pytest`. It should add "and no file named `test_*.py`
  under `tests/`". No lane owns this file, so integration should fix it.
- `dev/test_signatures.py::TestTheMachines` (2 tests) and
  `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name` fail
  here and fail the same way on `d102/base`. The cloud's git signing program only supports
  `-Y sign`, so they are an environment failure, not a code failure.
- `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`
  errors because no browser starts: the pip playwright wants `chromium_headless_shell-1243`.
  This is left to integration.

## Tests that fail only because another lane has not merged

- `dev/test_run_script.py::TestABrokenSpec::test_a_test_run_writes_its_results_and_exits_1`
  (PROOF-261) needs `specs.broken_reasons` from lane `reader`.
- `dev/test_run_script.py::TestABrokenSpec::test_the_audit_reads_no_rule_of_it` (PROOF-264)
  needs `specs.broken_reasons` from lane `reader`.
