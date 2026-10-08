RULE-3 of `sample_intake` now reads **strong**: the settle printed `PROOF-5: the test now catches the bug it missed at src/intake.py:17.`

- **The finding:** the PROOF-5 test took its expected age from `age_hours` itself, so the planted bug (rounding to nearest, giving 26 hours) still passed.
- **The fix:** `tests/test_intake.py:41` now asserts the literal `25` the proof names, both on the stored record and on `age_hours` directly. The code under test and the spec are unchanged.
- **Commits on `main`, not pushed:** `631ab81` (the test change) and `12ef1c9` (the evidence for it).

All 8 rules pass their tests on the committed evidence, and the audit now finds 2 of 8 rules strong. Two rules still read weak; I left them alone since you asked for RULE-3 only.

→ Run: `purlin:build sample_intake` to strengthen the remaining two.