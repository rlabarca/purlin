The audit ran on `sample_intake`: all 8 rules pass their tests, but it found only 4 of 8 strong (50%).

```
sample_intake RULE-1   strong
sample_intake RULE-2   weak
  PROOF-3: the test still passes when src/intake.py:52 reads "self.received[barcode] = dict(record, status='received')"
  PROOF-3: the AI says this breaks: a sample with the barcode LC-12345678 is handed in; the proof says it is stored with the status accepted; the changed code stores it with the status received
sample_intake RULE-3   weak
  PROOF-5: the test still passes when src/intake.py:17 reads "return round(seconds / 3600)"
  PROOF-5: the AI says this breaks: a sample collected 2026-03-01T08:00 and received 2026-03-02T09:30; the proof says its age is 25 hours; the changed code gives 26
sample_intake RULE-4   weak
  PROOF-7: the test still passes when src/intake.py:40 reads "if age >= MAX_AGE_HOURS:"
  PROOF-7: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-04T08:00, exactly 72 hours later; the proof says it is stored as accepted; the changed code stores it as expired
sample_intake RULE-5   strong
sample_intake RULE-6   strong
sample_intake RULE-7   weak
  tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.
  PROOF-11: the test still passes when src/intake.py:49 reads "accession = '%s-%d-%04d' % (site, received.year, number)"
  PROOF-11: the AI says this breaks: two samples from the site BOS received in 2026; the proof says BOS-2026-00001 then BOS-2026-00002; the changed code gives BOS-2026-0001 then BOS-2026-0002
sample_intake RULE-8   strong
The audit found 4 of 8 rules strong (50%): 4 strong, 4 weak.
```

The four weak rules, in plain terms:

- **RULE-2 (PROOF-3):** the test does not notice when an accepted sample is stored with the status `received` instead of `accepted`.
- **RULE-3 (PROOF-5):** the test does not notice when the age in hours is rounded to nearest instead of as the proof expects (25 hours becomes 26).
- **RULE-4 (PROOF-7):** the test does not cover the boundary, so a sample exactly 72 hours old can be stored as expired without a failure.
- **RULE-7 (PROOF-11):** `test_accession_numbers_count_up` checks nothing, and a four-digit accession number passes where the proof says five.

The evidence was written to `.purlin/evidence/local/sample_intake.json`. Nothing was committed, and the audit changed no project files.

Left to do:

- **4 rules to strengthen** → Run: `purlin:build sample_intake`. It strengthens each test, then settles the rule.
- **1 feature whose results are not committed** → Run: `purlin:test --commit`.