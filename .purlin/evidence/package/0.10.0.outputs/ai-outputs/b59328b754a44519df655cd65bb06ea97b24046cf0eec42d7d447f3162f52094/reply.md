I stopped before changing anything: RULE-3 can't be strengthened by `purlin:build` as its proof is worded, because PROOF-5 names no value to assert.

**The finding**
- The audit's planted bug changed `src/intake.py:17` from `int(seconds // 3600)` to `int(round(seconds / 3600))`, and the test still passed.
- `tests/test_intake.py:41` asserts `record['age_hours'] == age_hours(collected, received)`, so the expected age comes from the code under test and any rounding bug moves both sides together.

**Why this is a spec problem**
- PROOF-5 reads: "A sample received the day after it was collected has its age in whole hours". It gives no collection time, no receipt time and no age.
- The audit says the same: "the proof names no age".
- The build skill says to stop here rather than invent the expected value in the test, so the test and the spec are untouched.

**Proposed sharper proof** (same id, same rule; it uses the times the test already has):

> PROOF-5 (RULE-3): A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:30`, 25 and a half hours later; its age is `25` hours

The half hour matters: rounding down gives 25 and rounding to nearest gives 26, so asserting `25` catches the planted bug.

**Next steps**
1. Run `purlin:spec sample_intake` to reword PROOF-5 as above.
2. Run `purlin:build sample_intake` again. I'll change the assertion to `== 25`, run `purlin:test sample_intake`, then `purlin:audit sample_intake RULE-3 --settle`.

Two other tests I noticed while reading are likely behind the other weak rules:
- **PROOF-7:** the test at `tests/test_intake.py:54` receives at `07:00` (71 hours), not the `08:00` (exactly 72 hours) the proof names.
- **PROOF-11:** the test at `tests/test_intake.py:85` prints the accession numbers and asserts nothing.