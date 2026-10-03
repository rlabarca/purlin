# The hand-run checks

Two checks a person runs. Each drives the real `claude` CLI once against a throwaway project
with this checkout loaded as the plugin. Each reaches a real model, so each sends one prompt,
holds it to one timeout (600 seconds by default), and prints where the transcript landed.

| Check | What it drives | What it prints |
|---|---|---|
| `check_spec.py` | `purlin:spec` on two sentences of requirements | the spec file, its rule count, whether every rule carries a proof, and whether the reply ends with the offer to build |
| `check_build.py` | `purlin:build` on that spec | the files created, whether each test file carries a marker, the `--test` run, and the commit body's three sections |

Run them from the repository root, in this order:

```bash
export PATH="$PWD/.venv/bin:$PATH"
python3 dev/manual/check_spec.py --keep
python3 dev/manual/check_build.py
```

`check_build.py` picks up the project `check_spec.py --keep` left behind; `--spec <file>`
builds a committed fixture spec in a fresh project instead. Both take `--keep` and
`--timeout`, and exits 0 when the CLI ran and the printed checks passed, 1 when a check
failed, and 2 when `claude` is not on PATH.

Nothing here is in `dev/run_tests.sh`, and nothing here may be added to it. The sweep is
repeatable and offline; these two are neither.
