I didn't change anything for RULE-3. Its only proof is too vague to write the assertion the audit is asking for, so the spec has to be sharpened first.

**What the audit found.** RULE-3 reads `weak` because a planted bug got through. It changed `src/intake.py:17` from rounding down to rounding to the nearest hour (`int(round(seconds / 3600))`), and the test still passed. A sample received 25 and a half hours after collection would then be 26 hours old instead of 25.

**Why the test missed it.** `tests/test_intake.py::test_age_is_whole_hours` checks the bench's answer against `age_hours(...)`, which is the code under test. Whatever that function returns, the test agrees with it, so it can never fail.

**Why I can't just fix the test.** PROOF-5 says only "A sample received the day after it was collected has its age in whole hours." It gives no collection time, no receipt time and no expected age. The build rules say that when a proof names too little, I stop and propose a sharper proof instead of picking an expected value myself. Changing the source code or rewording RULE-3 to clear the finding is also not allowed.

**Proposed wording for PROOF-5:**

> PROOF-5 (RULE-3): A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:30`, 25 and a half hours later; its age is `25` hours

These are the times the test already uses. A fixed half-hour remainder means rounding down and rounding to nearest give different answers. Once the proof reads like this, the test can assert `record['age_hours'] == 25`, which catches the planted bug.

→ Run: `purlin:spec sample_intake` to update PROOF-5, then `purlin:build sample_intake` again. That run will rewrite the test, run `purlin:test sample_intake`, then `purlin:audit sample_intake RULE-3 --settle`, and commit.

Two other rules are also `weak`, but I left them alone because you asked only about RULE-3:
- **RULE-2:** PROOF-3's test doesn't check that the sample is actually stored on the bench.
- **RULE-7:** PROOF-11's test prints the accession numbers but asserts nothing.