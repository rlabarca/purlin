The audit ran on `sample_intake`: all 8 rules pass their tests, but only 3 of 8 read strong (37%). The other 5 are weak, each because a planted bug got past its proof's test.

```
sample_intake RULE-1   strong
sample_intake RULE-2   weak
  PROOF-3: the test still passes when src/intake.py:52 reads "self.received[barcode] = dict(record, status='pending')"
  PROOF-3: the AI says this breaks: a sample with the barcode LC-12345678 is handed in; the proof says it is stored with the status accepted; the changed code stores it with the status pending and only the returned record says accepted
sample_intake RULE-3   weak
  PROOF-5: the test still passes when src/intake.py:17 reads "return int(seconds // 3600) + 1"
  PROOF-5: the AI says this breaks: a sample collected at 2026-03-01T08:00 and received at 2026-03-02T09:30; the proof says its age is 25 hours; the changed code gives 26
sample_intake RULE-4   weak
  PROOF-7: the test still passes when src/intake.py:40 reads "if age >= MAX_AGE_HOURS:"
  PROOF-7: the AI says this breaks: a sample collected 2026-03-01T08:00 and received 2026-03-04T08:00, exactly 72 hours later; the proof says it is stored as accepted; the changed code stores it as expired
sample_intake RULE-5   weak
  PROOF-8: the test still passes when src/intake.py:52 reads "self.received[barcode] = dict(record, status='accepted')"
  PROOF-8: the AI says this breaks: a frozen sample received at -19.9 C; the proof says it is stored as temperature excursion; the changed code returns temperature excursion but keeps the sample on the bench as accepted
  PROOF-9: the test still passes when src/intake.py:52 reads "self.received[barcode] = dict("
  PROOF-9: the AI says this breaks: a frozen sample received at -20.0 C; the proof says it is stored as accepted; the changed code returns accepted but keeps the sample on the bench as temperature excursion
sample_intake RULE-6   strong
sample_intake RULE-7   weak
  tests/test_intake.py::test_accession_numbers_count_up: the test checks nothing.
  PROOF-11: the test still passes when src/intake.py:49 reads "accession = '%s-%d-%04d' % (site, received.year, number)"
  PROOF-11: the AI says this breaks: two samples from site BOS received in 2026; the proof says BOS-2026-00001 and BOS-2026-00002; the changed code gives BOS-2026-0001 and BOS-2026-0002
sample_intake RULE-8   strong
The audit found 3 of 8 rules strong (37%): 3 strong, 5 weak.
```

What the weak rules have in common:

- **RULE-2 and RULE-5 (PROOF-3, 8, 9):** the tests check the record that intake returns, not the status actually stored for the sample.
- **RULE-3 (PROOF-5):** the age test misses an off-by-one when the age is not a whole number of hours.
- **RULE-4 (PROOF-7):** nothing tests a sample at exactly 72 hours.
- **RULE-7 (PROOF-11):** the spot tests found that `test_accession_numbers_count_up` checks nothing, so a four-digit accession number passes where the proof says five.

The "AI says this breaks" lines are the model's claims about each bug; that the tests still pass with the bug in place is what the run confirmed.

The evidence is written to `.purlin/evidence/local/sample_intake.json` and is not committed. The status reads tests not met and not signed.

→ Run: `purlin:build sample_intake` to strengthen the five weak tests and settle each rule.

The status also lists `purlin:test --commit` for the uncommitted results.