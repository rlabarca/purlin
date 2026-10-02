# The weak tests strengthened after the first audit of Purlin

The first audit of ten specs found 28 rules weak, with 35 surviving bugs
(`audit-1-findings.txt`). Two agents read each proof, its test and the bug, applied the bug by
hand, and strengthened the test where the finding held. Tests only: no code, rule or proof
changed. 33 findings held, and each test was seen to fail with its bug in place. 2 did not hold.

## Findings that did not hold

- `planted_bug` RULE-10, PROOF-12. With the change the whole file runs and only the proof's own
  test is read, so `PROOF-1` still reads `survived`. The model's claim, `not run`, was wrong. The
  change breaks RULE-26, and the test of PROOF-50 fails on it.
- `evidence_writer` RULE-16, PROOF-41. A `--all --test` run takes `machine` from
  `machine_name()` in `scripts/run/purlin_run.py`. The changed `local_machine()` in
  `scripts/run/evidence.py` is a fallback that run never reaches.

## Proofs worth sharpening

None was changed. Each test already checks the sharper reading.

- `run_script` PROOF-271: "`--all --test` prints, on the line straight after the `Markers:`
  line and before `Ran pytest on 1 feature.`, a line beginning `tests/test_feat.py:3 names feat
  PROOF-1, whose wording changed after the test was last changed in`, and exits 0".
- `run_script` PROOF-288 and PROOF-289: "`tests` holds one entry alone: name `pytest`, command
  `python3 -m pytest {files} --junitxml={report}`, report `.purlin/runtime/reports/pytest.xml`,
  format `junit`, files `**/test_*.py` and `**/*_test.py`; it exits 0".
- `run_script` PROOF-88, PROOF-91 and PROOF-93, added to each: "and prints `Ran pytest on 1
  feature.`, the suite's report holding X's test alone".
- `run_script` PROOF-117: "leaves that section as it was and adds this machine's beside it, its
  `machine` this machine's host name".
- `signatures` PROOF-228: "prints `  2 rules on Linux/Unix: 2 pass their tests, no hand check.`
  after the `Signing 2.1.0 at <sha7>.` line".
- `signatures` PROOF-238: "it writes the tag `signed/2.1.0` at the sign-off commit".
- `ai_audit` PROOF-122: "`RULE-2`'s entry reads `spot-checked` because the model could not be
  reached, whether `claude` exited with an error, was not on PATH or gave no answer, and nothing
  has changed since; the audit run again, with a `claude` that answers, reads `RULE-2` and
  starts `claude` exactly `1` time".
- `package` PROOF-52: "it exits 1, prints after what the walk showed exactly one line, `The
  evidence package was not written: <the operating system's own message>. Nothing was signed;
  run purlin:sign again.`, and adds no commit and no tag".
- `evidence` PROOF-88: "the `run` command of the `tests` setting is then changed to another of
  the same length; checked against a fingerprint taken again, the section reads out of date on
  exactly `tests`".
