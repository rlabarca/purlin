# The hand-run checks

Three checks a person runs. Two drive the real `claude` CLI once against a throwaway project
with this checkout loaded as the plugin. Each costs money, so each sends one prompt, holds it
to one timeout (600 seconds by default), and prints where the transcript landed. The third
asks a real Azure DevOps project what `purlin:test --remote` asks it, and runs only on a
machine with Azure DevOps access.

| Check | What it drives | What it prints |
|---|---|---|
| `check_spec.py` | `purlin:spec` on the sentence from the design's solo start | the spec file, its rule count, whether every rule carries a proof, the tags, and whether the reply ends with the offer to build |
| `check_build.py` | `purlin:build` on that spec | the files created, whether the tests carry proof markers, the `--test` run, and the commit body's three sections |
| `check_azure_remote.py` | the lookup and the poll of `scripts/run/remote.py` against a real Azure DevOps pipeline | each command, its raw output and a one-line ok or FAIL: the remote parsed, `az` and its extension present and signed in, the seconds a run takes to register, the shape of the status answer, and that `remote.py` reads the same id and result |

Run those two from the repository root, in this order:

```bash
export PATH=/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH
python3 dev/manual/check_spec.py --keep
python3 dev/manual/check_build.py
```

`check_build.py` picks up the project `check_spec.py --keep` left behind; `--spec <file>`
builds a committed fixture spec in a fresh project instead. Both take `--keep` and
`--timeout`, and exits 0 when the CLI ran and the printed checks passed, 1 when a check
failed, and 2 when `claude` is not on PATH.

`check_azure_remote.py` runs from a clean clone of an Azure DevOps repository whose pipeline
is `purlin.azure-pipelines.yml`, after `az login`:

```bash
python3 /path/to/purlin/dev/manual/check_azure_remote.py
```

It pushes HEAD to `run/purlin-azure-check-<sha7>`, which starts one pipeline run, and deletes
that branch before it exits; it creates, pulls and commits nothing locally. It exits 0 when
every check passed, 1 when one failed, and 2 when `origin` is not an Azure DevOps URL or
`az` is not on PATH.

Nothing here is in `dev/run_tests.sh`, and nothing here may be added to it. The sweep must
stay free, repeatable and offline; these three are none of those.
