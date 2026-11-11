RULE-3 is still weak and I haven't changed anything. Its only proof doesn't name a number the test could check, so the fix has to start in the spec.

**What the audit found:**
```
RULE-3  passed  weak
  PROOF-5: the test still passes when src/intake.py:17 reads "return int(round(seconds / 3600))"
  PROOF-5: the AI says this breaks: a sample received 25 and a half hours after it was collected;
           the proof names no age; the changed code gives 26 hours where the code gave 25
```

**Why the test can't be fixed on its own:**
- `tests/test_intake.py:37` compares `record['age_hours']` with `age_hours(collected, received)`, which is the function being tested. Whatever rounding the code does, the test gets the same answer back, so the planted rounding bug got through.
- PROOF-5 only says the sample "has its age in whole hours". It gives no times and no expected age. If I wrote `assert ... == 25` I'd be checking a value the spec never states. The build rules say to stop at that point and propose a sharper proof instead.

**Proposed PROOF-5:**

> - PROOF-5 (RULE-3): A sample collected at `2026-03-01T08:00` is received at `2026-03-02T09:30`, 25 and a half hours later; its age is `25` hours

This uses the times the test already sets up. It names the exact value, and the half hour is what tells rounding down apart from rounding to the nearest hour.

**Stop and ask:** Shall I change PROOF-5 to this with `purlin:spec sample_intake`? If yes, I'll then:
1. Make the test assert `record['age_hours'] == 25`.
2. Run `purlin:test sample_intake`.
3. Run `purlin:audit sample_intake RULE-3 --settle` and report the result.
4. Commit as `feat(sample_intake):`.