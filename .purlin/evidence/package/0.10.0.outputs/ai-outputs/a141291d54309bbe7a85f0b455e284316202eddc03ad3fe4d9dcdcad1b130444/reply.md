I stopped without changing anything: RULE-3 can't be strengthened by `purlin:build` as its proof is worded, because PROOF-5 names no value to assert.

**What the audit found on RULE-3**
- The test `test_age_is_whole_hours` (`tests/test_intake.py:37`) takes its expected age from the code: it asserts `record['age_hours'] == age_hours(collected, received)`.
- A planted bug survived: the test still passes when `src/intake.py:17` reads `return int(round(seconds / 3600))`. For a sample received 25½ hours after collection, that gives 26 where the real code gives 25.

**Why I stopped**
PROOF-5 reads: "A sample received the day after it was collected has its age in whole hours". It gives no collection time, no receipt time and no age, so any exact number I put in the test would be mine and not the spec's.

**Proposed sharper proof**
> PROOF-5 (RULE-3): A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:30`, 25 and a half hours later; its age is `25` hours

This keeps the times the test already uses, and the half hour is what separates rounding down (25) from rounding to nearest (26), so it catches the planted bug.

**Next step**
→ Run: `purlin:spec sample_intake` to reword PROOF-5 (as above, or with your own values), then `purlin:build sample_intake` again. I'll then change the test to assert the literal `25`, run `purlin:test sample_intake`, and settle with `purlin:audit sample_intake RULE-3 --settle`.

The status also lists two other weak rules besides RULE-3; I did not look at them.