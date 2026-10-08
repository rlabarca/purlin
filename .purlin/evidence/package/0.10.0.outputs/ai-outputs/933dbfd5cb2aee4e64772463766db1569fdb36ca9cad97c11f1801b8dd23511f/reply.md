I made no changes: RULE-3 can't be strengthened by `purlin:build` as PROOF-5 is worded, and the skill says to stop there instead of inventing the expected value.

**Why it is weak.** The audit planted `return int(round(seconds / 3600))` at `src/intake.py:17` and the test still passed. `test_age_is_whole_hours` (`tests/test_intake.py:37`) compares the record's age to `age_hours(collected, received)`, so it takes its expected value from the code under test and passes whatever that function returns.

**Why I stopped.** PROOF-5 reads: "A sample received the day after it was collected has its age in whole hours". It names no times and no age, and the audit's own finding says "the proof names no age". The build skill only allows asserting the exact value the proof gives.

**Proposed sharper proof** (same id, same rule):

> PROOF-5 (RULE-3): A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:30`, 25 and a half hours later; its age is `25` hours

These are the times the test already uses, and the half hour is what separates rounding down (25) from the planted rounding (26).

**Next steps**
1. Run `purlin:spec sample_intake` to reword PROOF-5 as above.
2. Run `purlin:build sample_intake` again. I would then change the assertion to `record['age_hours'] == 25`, run `purlin:test sample_intake`, and settle with `purlin:audit sample_intake RULE-3 --settle`.

If you'd like me to make the spec change myself via `purlin:spec`, say so and I'll carry it through to the settle.

The status shows two other weak rules. I did not look up their findings, but from reading the tests they are probably these:
- **RULE-4:** the PROOF-7 test receives at `07:00` (71 hours), where the proof says `08:00` (exactly 72).
- **RULE-7:** the PROOF-11 test prints the accession numbers and asserts nothing.