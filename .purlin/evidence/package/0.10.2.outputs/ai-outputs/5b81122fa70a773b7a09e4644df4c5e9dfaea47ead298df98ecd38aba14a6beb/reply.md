RULE-3 of `sample_intake` is now **strong**. The audit put a rounding bug back into the code and the test now catches it.

**The problem:** The test for RULE-3 (PROOF-5) checked the bench's age against `age_hours()`, the same function the code uses to work out the age. So any bug in that function showed up on both sides of the comparison. When the audit changed the code to round to the nearest hour instead of down (`int(round(seconds / 3600))`), the age came out as 26 and the test still passed.

**The fix:** In `tests/test_intake.py:37`, the test now checks for the exact value the proof gives: a sample collected at `2026-03-01T08:00` and received at `2026-03-02T09:30` has an age of `25` hours. It no longer compares against the code's own result. I renamed the test `test_age_is_whole_hours_rounded_down` and removed the `age_hours` import, which nothing used any more. I changed no code under `src/`, and the spec stays as it was.

**Results:**
- All 12 tests passed.
- Re-checking RULE-3 printed `PROOF-5: the test now catches the bug it missed at src/intake.py:17.`
- 2 of 8 rules are now strong, up from 1.

**Commits** (on `main`, not pushed):
- `ea28e4e test(sample_intake): strengthen RULE-3` (the test change)
- `6fa1ffd purlin: evidence at ea28e4e` (the test results)

I used the `test(...)` prefix rather than `feat(...)` because only a test changed.

**Still to do:** Two other rules are still weak; I didn't touch them because you asked for RULE-3 only.
- **RULE-2:** the PROOF-3 test checks the returned status but never checks that the sample is stored on the bench.
- **RULE-7:** the PROOF-11 test only prints the accession numbers and checks nothing.

→ Run: `purlin:build sample_intake` to strengthen those two. Once they're done, `purlin:test --all --commit` prepares the version for sign-off.