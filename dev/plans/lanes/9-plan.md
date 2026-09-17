# Phase 9: the order of work (wave 7)

1. Spawn 9A to 9G together (Opus 5, worktrees, briefs `9A.md` to `9G.md`). They write
   disjoint spec directories and tag disjoint test files; 9C waits on nothing but deletes
   `specs/ci/` only when 9B's deletion has landed.
2. Land each by rebase and fast-forward. After all seven: no frozen spec remains
   (`git ls-files specs | wc -l` equals the new set), `bash dev/run_tests.sh` green,
   `python3 scripts/run/purlin_run.py --all --quick` shows every rule Tested (or Proof ready
   for `@manual`).
3. Orchestrator, in the main tree: `python3 scripts/init/scaffold.py --update --yes
   --project-root .` then `--gate approved --yes` with the approver list set to the user's
   email (the first real run of the upgrade path on this repository: migrates
   `.purlin/config.json` to the B2 shape at `gate: approved`, deletes the pre-commit shim
   and its `.git/hooks` delegator, rewrites the pre-push shim, refreshes the plugin copies,
   creates `.purlin/records/`); restore `.git/hooks/pre-commit.off-0.10` is not needed
   (delete it). Commit `chore(update): migrate to 0.10.0 (<ids>)`.
4. Write and hand-run `dev/manual/check_spec.py`, `check_build.py`, `check_qa_tool.py`
   (one lane, Opus 5, brief to write: each drives the real `claude` CLI once against a
   temp project and prints what to eyeball; never in `run_tests.sh`).
5. `python3 scripts/run/purlin_run.py --all --record --commit` locally: the developer
   record (label `developer`, counts under `tested` only, so the table shows Tested with
   "recorded: waiting for CI"). Commit.
6. The orchestrator pushes `evidence-workflow` (the user allows branch pushes); `purlin.yml` runs the Linux and Windows jobs; both
   API commits land with label `ci`; `purlin:verify --remote` from this Mac returns the
   Windows result; the PR comment and artifact appear; `--tag rc1` survives a prune (C4
   item 4).
7. The user approves what the review list shows (signed commits; the orchestrator prints the
   signing setup from A5 if `git config gpg.format` is unset); CI auto-approves low risk; `bash dev/bump_version.sh 0.10.0`;
   release notes final; tag `validated/0.10.0`.
