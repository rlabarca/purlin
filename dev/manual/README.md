# The hand-run checks

Four checks a person runs. Two drive the real `claude` CLI once against a throwaway project
with this checkout loaded as the plugin. Each costs money, so each sends one prompt, holds it
to one timeout (600 seconds by default), and prints where the transcript landed. The other two
ask a real Azure DevOps project what `purlin:test --remote` and the tag run ask it, and run
only on a machine or in a pipeline with Azure DevOps access.

| Check | What it drives | What it prints |
|---|---|---|
| `check_spec.py` | `purlin:spec` on two sentences of requirements | the spec file, its rule count, whether every rule carries a proof, the tags, and whether the reply ends with the offer to build |
| `check_build.py` | `purlin:build` on that spec | the files created, whether the tests carry proof markers, the `--test` run, and the commit body's three sections |
| `check_azure_remote.py` | the lookup and the poll of `scripts/run/remote.py` against a real Azure DevOps pipeline | each command, its raw output and a one-line ok or FAIL: the remote parsed, `az` and its extension present and signed in, the seconds a run takes to register, the shape of the status answer, and that `remote.py` reads the same id and result |
| `check_azure_provenance.py` | the tag run's committer check in `scripts/mcp/purlin/provenance.py` against a real Azure DevOps project | the identity `connectionData` names, the `push.pushedBy` of a named commit, and an ok or FAIL line for each of the two assumptions the check rests on: that `commits/<sha>` returns `push.pushedBy` for a commit the Pushes API created, and that the build service's id is the same on the run branch run and the tag run |

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

`check_azure_provenance.py` answers both assumptions only from a step in a pipeline job
started by a `signed/*` tag, with `SYSTEM_ACCESSTOKEN: $(System.AccessToken)` in the step's
`env`, in a project whose `ci/` evidence a run branch run pushed:

```bash
python3 "$PURLIN_ROOT/dev/manual/check_azure_provenance.py"
```

From a clean clone on your own machine, `--pat-env <variable>` reads a personal access token
from that variable and answers the first assumption alone; the second reads FAIL by design,
because the identity is then yours. `--commit <sha>` names the commit, which is otherwise the
last one that changed a file under `.purlin/evidence/ci/`. It sends two GET requests and
changes nothing. It exits 0 when both checks passed, 1 when one failed, and 2 with no token,
no collection or no commit. Its header names the fallback to try for each assumption that
fails.

Nothing here is in `dev/run_tests.sh`, and nothing here may be added to it. The sweep must
stay free, repeatable and offline; these four are none of those.
