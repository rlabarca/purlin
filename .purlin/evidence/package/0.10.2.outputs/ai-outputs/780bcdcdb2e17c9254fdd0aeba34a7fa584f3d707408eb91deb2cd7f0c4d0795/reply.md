RULE-3 of `sample_intake` now reads **strong**. The rule check went up from 1 of 8 strong rules to 2 of 8.

**What was wrong:** the PROOF-5 test compared the record's age against `age_hours(collected, received)`, which is the same function under test. So it couldn't fail. The audit flagged this, and its planted bug survived: changing `src/intake.py:17` to `int(round(seconds / 3600))` gives 26 hours, and the test still passed.

**Fix:** I edited only the test, not `src/intake.py` or the spec. At `tests/test_intake.py:37`, the test now receives a sample collected at `2026-03-01T08:00` at `2026-03-02T09:30` and asserts `record['age_hours'] == 25`, the number the proof gives. I also removed the `age_hours` import, which nothing used any more.

**Results:**
- `purlin:test sample_intake`: all 12 proofs pass, and all 8 rules pass.
- The settle for RULE-3 printed "PROOF-5: the test now catches the bug it missed at src/intake.py:17."

**Commit:** `9f12164 test(sample_intake): strengthen RULE-3`, with the test only. I used `test(...)` instead of the build skill's `feat(...)` because no behaviour changed. The updated evidence in `.purlin/evidence/local/sample_intake.json` is not committed yet, so the status reads "Tests: not met" until it is.

**Still to do:**
- 2 other rules are still weak. One is RULE-7: its PROOF-11 test prints the accession numbers instead of asserting them.
- Commit the evidence with the hand-off run. A sign-off needs this.

→ Run: `purlin:test --all --commit`