The audit of `sample_intake` ran: all 8 rules pass their tests, but only 3 of 8 read strong (37%) — 3 strong, 5 weak, none spot-checked.

```
sample_intake RULE-1   strong
sample_intake RULE-2   weak
  PROOF-3: the test still passes when src/intake.py:52 reads "self.received[barcode] = dict(record, status='pending')"
  PROOF-3: the AI says this breaks: a sample with the barcode LC-12345678 is handed in; the proof says it is stored with the status accepted; the changed code stores it with the status pending while the returned record still reads accepted
sample_intake RULE-3   weak
  PROOF-5: the test still passes when src/intake.py:17 reads "return round(seconds / 3600)"
  PROOF-5: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-02T09:30; the proof says its age is 25 hours; the changed code gives 26
sample_intake RULE-4   weak
  PROOF-7: the test still passes when src/intake.py:40 reads "if age >= MAX_AGE_HOURS:"
  PROOF-7: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-04T08:00, exactly 72 hours later; the proof says it is stored as accepted; the changed code stores it as expired
sample_intake RULE-5   weak
  PROOF-8: the test still passes when src/intake.py:52 reads "self.received[barcode] = dict(record, status='accepted')"
  PROOF-8: the AI says this breaks: a frozen sample received at -19.9 C; the proof says it is stored as temperature excursion; the changed code returns that status but keeps the sample on the bench as accepted
  PROOF-9: the test still passes when src/intake.py:52 reads "self.received[barcode] = dict(record, status='temperature excursion' if storage == 'frozen' else status)"
  PROOF-9: the AI says this breaks: a frozen sample received at -20.0 C; the proof says it is stored as accepted; the changed code returns accepted but keeps the sample on the bench as temperature excursion
sample_intake RULE-6   strong
sample_intake RULE-7   weak
  tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.
  PROOF-11: the test still passes when src/intake.py:49 reads "accession = '%s-%d-%04d' % (site, received.year, number)"
  PROOF-11: the AI says this breaks: two samples from the site BOS received in 2026; the proof says BOS-2026-00001 and BOS-2026-00002; the changed code gives BOS-2026-0001 and BOS-2026-0002
sample_intake RULE-8   strong
The audit found 3 of 8 rules strong (37%): 3 strong, 5 weak.
```

What the weak rules have in common:

- **RULE-2 and RULE-5 (PROOF-3, 8, 9):** the tests pass even when the stored record's status differs from the returned one, so nothing checks what is actually kept in `received`.
- **RULE-3 (PROOF-5):** the test does not catch the age in hours being rounded instead of cut down (25 becoming 26).
- **RULE-4 (PROOF-7):** the test does not catch a sample at exactly 72 hours being stored as expired.
- **RULE-7 (PROOF-11):** `test_accession_numbers_count_up` checks nothing, and a four-digit accession number gets past it.

The evidence is written to `.purlin/evidence/local/sample_intake.json`; nothing was committed.

→ Run: `purlin:build sample_intake` to strengthen the tests for the 5 weak rules and settle them.

The status also lists the feature's results as not committed: `purlin:test --commit`.