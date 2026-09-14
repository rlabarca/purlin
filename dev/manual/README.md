# The hand-run checks

Three checks a person runs, each driving the real `claude` CLI once against a throwaway
project with this checkout loaded as the plugin. Each costs money, so each sends one prompt,
holds it to one timeout (600 seconds by default), and prints where the transcript landed.

| Check | What it drives | What it prints |
|---|---|---|
| `check_spec.py` | `purlin:spec` on the sentence from the design's solo start | the spec file, its rule count, whether every rule carries a proof, the tags, and whether the reply ends with the offer to build |
| `check_build.py` | `purlin:build` on that spec | the files created, whether the tests carry proof markers, the quick run, and the commit body's three sections |
| `check_qa_tool.py` | `tools/QA/purlin-qa-report.md` over `scripts/report/scan.py` output | the triage report, and whether it is ordered by risk and names the review list only |

Run them from the repository root, in this order:

```bash
export PATH=/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH
python3 dev/manual/check_spec.py --keep
python3 dev/manual/check_build.py
python3 dev/manual/check_qa_tool.py
```

`check_build.py` picks up the project `check_spec.py --keep` left behind; `--spec <file>`
builds a committed fixture spec in a fresh project instead. Every check takes `--keep` and
`--timeout`, and exits 0 when the CLI ran and the printed checks passed, 1 when a check
failed, and 2 when `claude` is not on PATH.

Nothing here is in `dev/run_tests.sh`, and nothing here may be added to it. The sweep must
stay free, repeatable and offline; these three are none of those.
