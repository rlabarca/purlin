# Evidence

What a run leaves behind for each feature: each proof's result on each operating system, the
commit and the time. There is one JSON file per feature per source:

```
.purlin/evidence/local/<feature>.json   a person's own run
.purlin/evidence/ci/<feature>.json      this project's own run on another system
```

The folder is the source. A run on your own machine writes `local/`, and `--commit` commits it
under your own git identity. A run your project makes on another system writes `ci/` and commits
it there. Every file here is tracked, because the point of the files is that somebody who did
not make the run can read them. You do not edit anything here by hand.

The format is `references/formats/evidence_format.md` in the Purlin plugin.
