I've stopped before changing anything. RULE-3 can't be strengthened yet because PROOF-5 doesn't name a value for its test to check.

**What the audit found.** RULE-3 reads `weak` because a planted bug got past its test. The audit changed `src/intake.py:17` to round the age to the nearest hour (`return int(round(seconds / 3600))`) instead of rounding down. A sample received 25½ hours after collection then gets 26 hours instead of 25, and the test still passed.

**Why the test missed it.** `tests/test_intake.py:36` compares `record['age_hours']` with `age_hours(collected, received)`. That is the function under test, so the check can never fail.

**Why I can't just fix the test.** PROOF-5 says *"A sample received the day after it was collected has its age in whole hours."* It gives no exact age to assert. If I picked one myself, the spec still wouldn't say it, and the rules don't allow narrowing or rewording a proof to make a finding go away. So the proof needs to be sharper first.

**Proposed PROOF-5:**

> - PROOF-5 (RULE-3): A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:45`, 25 hours 45 minutes later; its age is `25` hours

I chose 45 minutes past the hour because any rounding up or to the nearest hour gives 26, so the test catches the planted bug and similar ones.

Once you agree:
1. Run `purlin:spec sample_intake` to change PROOF-5. It keeps its number, and the current test comment will then be flagged as one to correct.
2. Run `purlin:build sample_intake`. I'll change the test to use those times and assert `record['age_hours'] == 25`, then run `purlin:test sample_intake` and `purlin:audit sample_intake RULE-3 --settle`.

→ Run: `purlin:spec sample_intake`

The status shows two other weak rules, which I didn't touch:
- **RULE-2:** PROOF-3's test doesn't check that the sample is stored.
- **RULE-7:** PROOF-11's test prints the accession numbers but asserts nothing.