# Step P1 `shared` (phase 4, alone before fan-out 1)

You are step P1 of phase 4 of Purlin 0.10.0: sanity check 3 applied, with the owner's answers of
decision 98. You run alone, before 20 lanes start; they build on what you land. Purlin is a
Claude Code plugin for spec-driven development that uses itself. This brief is complete in
itself. No reviewer follows you: you check your own work with the self-check and report.

- Start only once the `winfix-1` branch is merged into `main` (`git log main` holds its two
  fixes; if it does not, stop and report).
- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-p1-shared`, branch `p4/p1-shared`, from
  `main`: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/p4-p1-shared -b p4/p1-shared main`.
- Scratch folder: `<the scratchpad directory your session gives>/p4-p1-shared`.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` decisions 94 to 98.
3. `dev/plans/sanity-3.md` section 7 faults 2 and 3, section 6 items 13 and 44, section 11
   question 14.
4. `dev/plans/phase4-plan.md` sections 1 and 3, and `dev/plans/phase4-contracts.md` K1 and K7.

## What you may write

Only what the two items need, in any file: `scripts/mcp/purlin/status.py`,
`scripts/mcp/purlin/payload.py`, `scripts/init/scaffold.py` (`next_step` alone),
`scripts/init/update.py` (`_print_ending` alone), `scripts/run/purlin_run.py` (the no-spec
print alone), `specs/mcp/states.md`, `specs/init/scaffold.md`, `specs/init/update.md`,
`specs/run/run_script.md`, `specs/_anchors/schema_spec_format.md`, `skills/init/SKILL.md` (the
quoted ending alone), and the test files that quote the old lines: `dev/test_states.py`,
`dev/test_init_scaffold.py`, `dev/test_init_update.py`, `dev/test_run_script.py`,
`dev/test_schema_spec_format.py`, `dev/test_skill_init.py`, `dev/test_mcp_server.py` if it
quotes them. Nothing else in those files changes. The frozen helpers stay as they are:
`dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`, `dev/run_project.py`,
`dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

## The work

1. **One ending for a project with no spec** (faults 2 and 3; §6 item 13; contracts K1.1).
   `status.no_spec_lines(project_root) -> list[str]`, the two lines by state exactly as K1.1
   gives them, and "the tree holds code" exactly as K1.1 defines it. `NO_SPECS` goes. Its four
   callers print the two lines: `status.sync_status` (returns them joined by a newline),
   `scaffold.next_step` (setup's last lines), `update._print_ending` (after its blank line),
   `purlin_run.main` (then exit 1). Rules and proofs: states RULE-39 says the two lines by
   state; PROOF-46 becomes the set-up-with-code case, and two new proofs take "set up, no code"
   and "not set up"; scaffold RULE-34 and PROOF-34 say setup ends on the same two lines, with
   one proof for a tree with code and one for a tree with none; update gains one proof that an
   upgrade of a project with no spec ends on the two lines; run_script PROOF-104 stays (it reads
   the first line). `skills/init/SKILL.md` line 185 quotes the new ending. Every test that
   quotes the old lines follows.
2. **The warning for rule lines with no number** (A14; §6 item 44; K1.2). `payload.py` builds
   the two lines of K1.2, in the same place in `warnings`. schema_spec_format PROOF-2 and
   PROOF-45 quote them whole; PROOF-13 and PROOF-14 say the status carries no line containing
   `is not numbered`; their tests follow.

Number new ids one above the highest each spec has ever held (`git log -p --follow -- <spec>`,
the spec's own ids); a proof holds one case in at most 60 words and has a marked test of its
own.

## How to test

```
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH
cd /Users/richlabarca/LocalCode/purlin-wt/p4-p1-shared
.venv/bin/python -m pytest dev/test_states.py dev/test_init_scaffold.py dev/test_init_update.py dev/test_run_script.py dev/test_schema_spec_format.py dev/test_skill_init.py dev/test_mcp_server.py -q
bash dev/run_tests.sh --fast
```

## Limits

- Commit on `p4/p1-shared` only, with the prefixes of `references/commit_conventions.md`, each
  message ending with the attribution lines your session gives. Push nothing, tag nothing.
- Run no `purlin:audit` and no `purlin:sign`; never start the real `claude` program or any real
  service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`,
  `.github/workflows/purlin.yml`.
- A word a person reads that K1 does not give: leave it and report it.

## Self-check (run it, then report each result)

1. Every proof you wrote or reworded: one case, at most 60 words, a marked test of its own.
2. `git grep -n NO_SPECS` and `git grep -n "WARNING:"` outside `dev/plans/` and
   `RELEASE_NOTES.md` print nothing; `git grep -n "purlin:init to set this project up, or"`
   prints nothing.
3. No generated file is staged.
4. No id reused.
5. Break each on purpose, see its test fail, restore with `git checkout -- <file>`: (a) make
   `no_spec_lines` answer the no-code line for a tree with code: the with-code proof fails;
   (b) put `WARNING: ` back before K1.2's line: PROOF-2 fails; (c) make setup end on the old
   `→ Run: purlin:spec to write the first spec.`: scaffold PROOF-34 fails.

## Report, as your final message

The branch and its commits; each spec's highest RULE and PROOF id after the work; tests of the
named files before and after and the `--fast` result; the self-check's five results; anything
left and why.
