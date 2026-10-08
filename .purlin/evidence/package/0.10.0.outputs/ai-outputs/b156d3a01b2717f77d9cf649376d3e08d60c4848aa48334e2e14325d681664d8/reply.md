RULE-3 of `sample_intake` now reads **strong**.

- **The weakness:** the PROOF-5 test took its expected age from `age_hours` itself, so it passed when the code rounded to the nearest hour instead of rounding down (26 instead of 25).
- **The fix:** `tests/test_intake.py:41` now asserts `record['age_hours'] == 25`, the value the proof names. I also dropped the now-unused `age_hours` import. No code under test and no spec wording changed.
- **The settle:** `PROOF-5: the test now catches the bug it missed at src/intake.py:17.`

All 8 rules pass their tests on the committed evidence, and the audit now finds 2 of 8 strong (2 strong, 2 weak, 4 spot-checked).

I made two local commits directly on `main`, following the Purlin flow, and pushed nothing:
- `3b37b82` — `test(sample_intake): assert the age PROOF-5 names for RULE-3`
- `b009436` — `purlin: evidence at 3b37b82`

Two other rules are still weak; I left them alone since you asked only for RULE-3.

→ Run: `purlin:build sample_intake`