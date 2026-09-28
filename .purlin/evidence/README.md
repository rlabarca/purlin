# Evidence

What a test run and an audit leave behind for each feature: each proof's result on each
operating system, the commit and the time, and, once an audit has read the feature, what the
audit found for each rule. There is one JSON file per feature per source:

```
.purlin/evidence/local/<feature>.json   a person's own run
.purlin/evidence/ci/<feature>.json      a remote runner's run
```

The folder is the source. `purlin:test` and `purlin:audit` write `local/`, and `--commit` on
either commits it under your own git identity. A remote runner writes `ci/` and commits it
through the git host. Every file here is tracked, because the point of the files is that
somebody who did not make the run can read them. You do not edit anything here by hand.

The format is `references/formats/evidence_format.md` in the Purlin plugin.
