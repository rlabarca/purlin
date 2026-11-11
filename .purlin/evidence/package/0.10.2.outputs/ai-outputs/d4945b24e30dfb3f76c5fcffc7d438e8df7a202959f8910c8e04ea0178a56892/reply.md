RULE-3 of sample_intake now reads **strong**.

**The problem:** the PROOF-5 test (`tests/test_intake.py:37`) checked the record's age against what `age_hours()` returned. That compared the code with itself, so it could never fail. The audit showed this: when `src/intake.py:17` was changed to round to the nearest hour instead of down, the test still passed, even though the age came out as 26 hours instead of 25.

**The fix:** the test now checks for the value the proof states, `assert record['age_hours'] == 25`, for the 08:00 to 09:30 next-day case. I renamed it to `test_age_is_whole_hours_rounded_down_to_25` and removed the `age_hours` import, which nothing used any more. I didn't change any code under test.

**Result:** all 12 tests pass. Re-checking RULE-3 printed `PROOF-5: the test now catches the bug it missed at src/intake.py:17.` Strong rules went from 1 of 8 to 2 of 8.

**Commits** (not pushed):
- `089df41 test(sample_intake): strengthen RULE-3`, which only changes the test file
- `e37c74e purlin: evidence at 089df41`, the updated test results

Two rules are still weak:
- **RULE-2:** PROOF-3 doesn't check that the sample is actually stored.
- **RULE-7:** PROOF-11's test prints the accession numbers but never checks them.

→ Run: purlin:build sample_intake