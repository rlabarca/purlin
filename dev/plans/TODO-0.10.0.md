# Purlin 0.10.0: outstanding after the unattended run (2026-09-14)

Everything below is open. The refactor's lanes have all landed on `evidence-workflow`; this
is what the run could not finish, found and left, or left to a person.

## For the user, in order

1. **Approve.** 428 rules are recorded and not approved (high and medium); CI has auto-approved
   the 77 low-risk ones and its approvals are on the branch. `purlin:review` walks them; `purlin:approve <feature> RULE-N` makes each
   signed commit (repo-local SSH signing is configured; the public key still has to be
   uploaded to GitHub for the host to show Verified). `verify_gate.py --check` exits 1 until
   every high and medium rule has a current approval on the branch.
2. **Apply the three GitHub rulesets** init printed (require a pull request and the `purlin`
   check with the Actions app as the only bypass; restrict `.purlin/records/**` and
   `specs/**/*.approvals/*.ci.json` to the Actions app; block force pushes and deletions).
3. **Release.** One more green sweep to set the `Tests at this commit` line, `purlin:verify
   --tag 0.10.0` for the validation tag, a pull request from `evidence-workflow` to `main`,
   the `v0.10.0` tag (`VERSION` already reads 0.10.0; `dev/bump_version.sh --check` guards
   the derived copies).
4. **`purlin:verify --remote`** from this Mac has not been exercised (C4 item 4); the GitHub
   branch of `scripts/run/remote.py` is untested against a live host. The Azure DevOps
   branch prints the pipeline URL and carries `TODO(ado-remote)` for the work machine.

## Defects and gaps found by the run, not fixed

5. **Test strength is `n/a` everywhere.** No engine runs in CI: `requirements.txt` installs
   pytest and playwright only, and `setup.cfg`'s `[mutmut]` block names `source_paths = dev`,
   which would mutate the tests rather than `scripts/`. Decide whether CI installs mutmut
   (a full run over `scripts/` is slow) and fix the block init writes for this repository.
   With no engine the gate does not compare strength to the 80 minimum.
6. **The local anchor repository is not reproducible.** `dev/setup-external-refs.sh` yields a
   different sha on each fresh setup, so `specs/_anchors/security_no_dangerous_patterns.md`'s
   pin (`379a046`) reads as behind on every other machine. Fix the script's determinism
   (fixed author, committer and dates) or pin after each setup.
7. **`scan.py` prints counts only**, so the QA tool in Claude Desktop cannot produce a
   per-rule review list from it; it reports an empty list plus the Drafted count.
8. **The shell arm runs only `*.test.sh` at the project root.** Shell suites under `dev/`
   prove nothing unless a root wrapper calls them (`init_e2e.test.sh`,
   `proof_plugins.test.sh` exist); three proofs carry `@env(linux)` because the wrappers skip
   on Windows. A consumer with shell tests under a subdirectory meets the same limit.
9. **A Windows developer's record commit stages nothing**: `scripts/run/records.py`
   `deleted_records` and `_commit_as_developer` hand git a `.purlin\records` pathspec (lane
   F11's note; the CI path is fine).
10. **Two stale sentences** still say the matrix is "one job per operating system named":
    `skills/init/SKILL.md` around line 121 and `docs/raising-the-gate-and-upgrading.md`
    around line 43. Linux is always in the matrix now.
11. **The spec skill's "one sentence in, three rules out"** reads as a target count; the
    real model writes five or six defensible rules (lane 9H's finding). Say "at least three".
12. **`dev/manual/` checks** drive the nested CLI with permissions skipped; fine for a
    throwaway project, worth knowing before running them elsewhere.
13. **The Windows job takes 15 to 18 minutes** (playwright plus the whole suite); the Linux
    job four. Acceptable, noted.
14. **Part A of the plan is stale in three places** (`dev/plans/evidence-workflow.md`): A4's
    claim that the API commit's committer is `github-actions[bot]` (it is GitHub's web-flow
    identity, the bot is the author); the matrix wording (Linux always present); the
    `report` config key, which no longer exists. The DONE sections record the corrections;
    the design file itself was left verbatim.

## Housekeeping

15. Delete the merged `lane/*` branches (41) and the harness's `worktree-agent-*` branches
    (`git branch -D`); prune `.claude/worktrees/`.
16. `.purlin/records/` now holds three records per feature per runner plus the developer's;
    retention is working. The first `validated/*` tag will pin the ones that matter.
17. The design system copy under `design/` leaves out the PNG renders (gitignored `*.png`),
    the deck templates, slides and the reference dashboard kit, per A11.
