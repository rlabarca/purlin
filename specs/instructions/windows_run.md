# Feature: windows_run

> Description: How this repository proves its own rules tagged `@env(windows)`. It is this
>   project's own setup, as any project's would be: one workflow file for GitHub and one script
>   the owner starts from a Mac. Purlin ships neither.
> Scope: dev/windows_run.py, .github/workflows/windows.yml
> Stack: python/stdlib (subprocess, json), git, the GitHub CLI
> Highest-Rule: 3
> Highest-Proof: 4

## Rules

- RULE-1: `dev/windows_run.py` pushes this commit to the run branch `run/<branch>-<sha7>` on `origin`, waits on the run the `windows.yml` workflow starts for that branch, then pulls the commit that run made with `git pull --ff-only`, deletes the run branch and prints the status, after a red run as after a green one, and exits 1 when the run failed
- RULE-2: `dev/windows_run.py` refuses before anything is pushed, says what is wrong and how to fix it, and exits 1, when the checkout is on no branch or holds uncommitted changes, and when `gh` is not installed
- RULE-3: `.github/workflows/windows.yml` starts on a push to a `run/` branch and on nothing else, holds the one job `windows-latest`, runs `scripts/run/purlin_run.py --ci --commit`, and then pushes that commit to the branch it ran on, whether the tests passed or not

## Proof

- PROOF-1 (RULE-1): On the branch `feature-x` at HEAD `4f1c2ab…`, with `gh` on the search path and GitHub registering run `987`, `dev/windows_run.py` starts `git push origin HEAD:refs/heads/run/feature-x-4f1c2ab`, `gh run watch 987 --exit-status`, `git pull --ff-only origin run/feature-x-4f1c2ab` and `git push origin --delete run/feature-x-4f1c2ab`, in that order, ends its output with the status table, and exits 0
- PROOF-2 (RULE-1): When `gh run watch` exits 1, `dev/windows_run.py` prints `The run failed on GitHub. The table below is what came back.`, still starts the pull and then the delete of the run branch, ends its output with the status table, and exits 1
- PROOF-3 (RULE-2): With one file in the tree that is not committed, `dev/windows_run.py` exits 1, prints exactly `This checkout has changes that are not committed, so a run would prove something other than what is here. Commit them, then run python3 dev/windows_run.py again.`, and starts no push
- PROOF-4 (RULE-3): `.github/workflows/windows.yml` triggers on a `push` of `branches: ['run/**']` alone, names `windows-latest` and no other system, holds a step that runs `scripts/run/purlin_run.py" --ci --commit` or the same without the quote, and after it a step under `if: always()` that pushes `HEAD` to the branch the run was started for
