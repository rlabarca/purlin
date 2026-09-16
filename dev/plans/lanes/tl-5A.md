# Lane 5A: skills and agent

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full).
Worktree `/Users/richlabarca/LocalCode/purlin-wt/5A`, branch `lane/5A` off `three-levels`.

You start from the phase 0 commit: the code still carries the old names while you draft, and
phases 1 to 4 land on `three-levels` while you work. Draft from Part A; when the orchestrator
tells you phase 4 is merged, `git rebase three-levels`, check every script path and message
your skills cite against the code as it then is (`scripts/review/sign.py`,
`scripts/ci/gate_check.py`, `scripts/run/purlin_run.py --record`, the status table), run the
acceptance again, then report.

## What you own (Part C2, phase 5A)

- `git mv skills/approve skills/sign`; `git mv skills/verify skills/audit`;
  `git rm -r skills/review`. Twelve skills remain: anchor, audit, build, drift, find, init,
  rename, sign, spec, spec-from-code, status, test.
- Rewrite `skills/sign/SKILL.md`: the walk (no argument: read the review list, render each
  brief, take one answer: sign, add a case as a proof line the reviewer writes, hold, skip),
  the direct forms (`purlin:sign <feature> [RULE-N ...]`, `--batch`, `--hold "<case>"`,
  `--note "<text>"`), what each writes (Part A4), the gate scaling of Part A5 (under `passed`
  it says the gate is `passed` and what `purlin:init --gate strong` would add, then stops;
  under `strong` the walk, `--note` and `--hold` work and a bare signature says signatures are
  required only under `signed`, then writes it anyway if asked), the signer rules of Part A3
  in one table, the commit prefixes.
- Rewrite `skills/audit/SKILL.md`: level 2; runs the tests then the breaks (never under
  `passed`), writes the record, on `--ci` also the briefs; a local run under `strong` or
  `signed` is a preview that says it does not count; `--tag <name>` writes `record/<name>`;
  `--remote`; delegates execution to `scripts/run/purlin_run.py` as `purlin:test` does today.
- Rewrite `skills/status/SKILL.md` (the table of Part A6, the summary line, the `→ Next:`
  line, the gate scaling) and `skills/init/SKILL.md` (three gate answers with their one
  sentence each, the signer question under `signed`, the three branch rules, what raising the
  gate adds, `--update`).
- Section-rewrite `skills/find`, `skills/test` (the pattern every skill follows for gate
  scaling), `skills/spec` (no risk tag asked under `passed`; `@manual`), `skills/drift` (`qa`
  says the same as `purlin:sign` under `passed`; the new drift rows).
- `agents/purlin.md`: the words block (Part A1), the `sync_status` paragraph ("the spec status
  and the cells of every rule"), NEVER 2, 3, 4, 5 in the new words, the routing rows (twelve
  skills, none for review, verify or approve).
- Every skill's "Paths in this skill" block cites `scripts/` paths that exist after phase 2;
  nothing cites `dev/` or this repository's `specs/`.

## Tests

`dev/test_skills.py`: L34–38 the skill name list (twelve), L223, L238, L247, L257, L499,
L538, L553, L571–596 as `skill_sign`, L656, L716, L723, L770, L818, L822, L862, and every
assertion that reads an old skill name, gate value or state word. Every marker names the
spec's feature and RULE id after your renaming and renumbering.

## Specs

Through the rename path (`tl-_rules.md` "Code"): `specs/skills/skill_approve.md` →
`skill_sign.md` (`git mv` the spec, its `.approvals` directory, `.purlin/records/skill_approve`;
markers `("skill_sign", ...)`), `skill_verify.md` → `skill_audit.md` likewise; then rewrite
both. `git rm` `specs/skills/skill_review.md`, its `.approvals` directory,
`.purlin/records/skill_review/`, and its tests in `dev/test_skills.py`. Section-rewrite
`skill_init.md` RULE-5, `skill_find.md` PROOF-2, `specs/instructions/purlin_agent.md` RULE-3
and RULE-5.

## Words

Part A1 in full. `purlin:test` / `purlin:audit` / `purlin:sign` for the three levels;
`the walk`; `sign`, `hold`, `note`, `add a case`, `skip`; `brief`; `review list`;
`needs a person`. Never `purlin:verify`, `purlin:review`, `purlin:approve`, `approve`,
`approval`, `approver`, `verdict`, `re-verify`, `Proof ready`, `seven states`.

## Expected red

Anything that is not `dev/test_skills.py` or `dev/test_vocabulary.py` may be red while phases
1 to 4 land. After the rebase the orchestrator asks for, only files another lane names may
stay red; name each in your report.

## Acceptance

```
pytest dev/test_skills.py dev/test_vocabulary.py
ls skills/   (twelve directories)
grep -rn "dev/\|specs/" skills/ agents/purlin.md | grep -v "^skills/.*: *\`\?specs/<" | grep -v "specs/<category>\|specs/_anchors\|\.purlin"   (nothing that names this repository's dev/ or specs/)
```
