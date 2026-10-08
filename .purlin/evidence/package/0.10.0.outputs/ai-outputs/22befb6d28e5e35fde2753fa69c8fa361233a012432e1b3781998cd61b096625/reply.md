RULE-3 of `sample_intake` now reads `strong`: the settle printed `PROOF-5: the test now catches the bug it missed at src/intake.py:17.`

- **The finding:** the PROOF-5 test compared the record's age with `age_hours(collected, received)`, so it took its expected value from the code under test. The planted bug (rounding to nearest, giving 26 hours) still passed.
- **The fix:** `tests/test_intake.py:41` now asserts the age is `25`, the value the proof names. I also dropped the `age_hours` import the test no longer uses. `src/intake.py` and the spec are untouched.
- **The commit:** `dd7a2e3 test(sample_intake): strengthen RULE-3`, made directly on `main`, holding the test file only.

All 8 rules pass their tests, and the audit now finds 2 of 8 strong. Two things are left:

- **Evidence not committed:** `.purlin/evidence/local/sample_intake.json` is modified, so the status reads `Tests: not met` until it is committed.
- **Two other weak rules:** the status still lists 2 rules to strengthen, which I left alone because you asked for RULE-3 only.

→ Run: `purlin:test --commit`