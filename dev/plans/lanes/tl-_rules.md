# Rules shared by every three-levels lane

Design and plan: `dev/plans/three-levels.md`. Read it in full before your brief. Part A is the
vocabulary, the chain, the gate, the commands and the surfaces; Part B is the technical design;
Part C is the execution. The 22 decisions at its top were made by the user and no lane reopens
one. Nothing in the plan is left to a lane's judgment except wording.

## Where you work

- Your worktree: `git worktree add /Users/richlabarca/LocalCode/purlin-wt/<lane> -b lane/<lane>
  three-levels`, run from `/Users/richlabarca/LocalCode/purlin`. Every edit, test run and commit
  happens inside the worktree. Never edit the main tree.
- Read `dev/plans/three-levels.md` in full, this file, `design/readme.md` "Content fundamentals"
  (and the whole file where your brief says so), then your brief. Do not read another lane's
  brief. Do not edit `dev/plans/`: your report is your final message, not a DONE section.
- Touch only the files your brief names, plus files you must touch to keep the sweep green,
  named in your report. Another lane owns everything else.
- Push `lane/<lane>` whenever a CI run would tell you something (`git push -u origin
  lane/<lane>`); the orchestrator merges. No tags. `VERSION` stays 0.10.0 and
  `dev/bump_version.sh` is not run. No `purlin:sign`, and no signature or hold file written by
  any agent, in any tree, for any reason.

## Vocabulary

- Every doc, skill, reference, message, test string and comment uses the words of Part A and
  no others. Retired outright, any casing, whole word: `tested`, `recorded`, `approved`,
  `approve`, `approval`, `approver`, `approvers`, `verified`, `verdict`, `reviewed`,
  `re-verify`; the phrases `Proof ready`, `lowest state`, `seven states`, `auto-approval`,
  `review queue`; the names `purlin:verify`, `purlin:review`, `purlin:approve`, `verify_gate`,
  `verify-gate:`, `validated/`. Plain English uses are rewritten too ("the run recorded a
  pass" becomes "the run wrote a pass"; "a reviewed rule" becomes what the cell says). `verify`
  as a verb stays legal. `audit` is legal and means the level 2 run only. `Stale` survives only
  as `signature stale` and as the adjective. `record` and `review list` survive. The older
  retired words stay retired: gauge, HOLLOW, PROVABLE, receipt, platform, `@on(`, mode (in
  prose), mutation score, caught score, records branch, Pages, forge, queue, CODEOWNERS,
  approver rule.
- `dev/test_vocabulary.py` enforces this over every tracked file. `PENDING_REWRITE` there
  stages the files a lane has not reached yet, grouped by lane. **Delete your lane's entries in
  the commit that rewrites those files** and run `pytest dev/test_vocabulary.py` before you
  report. A file that must name a retired spelling (a migration table, a parser's detection
  branch, a test that feeds the parser that spelling) ends each such line with the marker in
  `MARKED` for its file type, and no other line in that file may carry a retired word.
- No emoji anywhere: CLI output, pull request comments, tests, fixtures, docs.
- Prose follows `design/readme.md` "Content fundamentals": plain, declarative, second person
  for the reader, third person for the system, exact numbers, limits stated, sentence case,
  no superlatives, command names lowercase with the colon. Machine text (commands, rule ids,
  paths, shas, gate values, cell words) in backticks.

## The chain, as the fixtures pin it

`dev/fixtures/report/solo.json` (gate `passed`), `team.json` (`strong`) and `regulated.json`
(`signed`) are schema 5 payloads written by hand from Part B1. They are the contract between
the payload (lane 1A) and the dashboard (lane 4), and the reference for every other surface.
Where the plan is silent, the fixtures decide, and they encode these orchestrator decisions:

1. **Every cell at or below the gate exists for every rule**, including a drafted one. A cell
   above the gate is absent (the key is missing, not null).
2. **When the passed cell is not met, the strong cell reads `weak` with the one reason
   `not passed`.** The strength shown is the latest counting record's, or null.
3. **The signed cell is computed from the signature files regardless of the cells below it**:
   `signed`, `unsigned`, `stale`, `held`, or `not required` when risk is below `sign_at` and
   no hold is current. A signature is a fact about files.
4. **A current hold** makes the strong cell read `needs a person` with the reason
   `held by <email>: <case>` and the signed cell read `held` with the same reason, whatever
   the risk. `flags.held` is true. A signature by a person for the current hashes outranks
   the hold.
5. **`needs a person` for a `@manual` proof or an unsettled review** sets `flags.needs_person`
   and the strong reason `manual proof` or `review not settled`. A held rule does not set
   `needs_person`; `held` and `needs_person` are counted apart in every rollup.
6. **`bucket`**: `untested` is drafted, or ready with no test, or ready with no current
   counting run (`not run` and `code changed` both land here); `failing` when any counting
   run failed; `passed` when level 1 is met and either the gate is `passed` or level 2 is not
   met; `strong` when levels 1 and 2 are met and either the gate is `strong` or level 3 is not
   met; `signed` when every cell to the gate is met at `signed`. `stale` and `held` are flags
   counted beside the buckets.
7. **`blocked_by`** is the lowest unmet cell in the order `spec`, `passed`, `strong`, `signed`,
   or null when the rule meets the gate. `spec` blocks while the spec status is `drafted`.
8. **The review list** holds exactly the rules whose `blocked_by` is `strong` with the word
   `needs a person`, or `signed` with the word `unsigned`, `stale` or `held`. A rule blocked at
   `spec` or `passed` is never on it. It is `[]` under `passed`. Rows are grouped by risk high
   first, then within a group stale and held before the rest, then feature and rule id.
   `why` tokens are the closed set `unsigned`, `stale`, `held`, `needs a person`, `manual`
   (`manual` replaces `needs a person` when a `@manual` proof is the cause).
9. **A passed cell with no source** (`no test`, or `not run` with nothing to read) has
   `source` null, `current` false, `counts` false. `not run` for a missing `@env` has the
   record's source, `current` true, `counts` true and `missing_env` naming the environment.
10. **The passed cell's word for a record that does not count** under the gate (a `developer`
    or `local` source at `strong` and above) is `not run` with the reason
    `<source> record does not count under <gate>`.
11. **Rollup and summary keys**: `rules, met, failing, untested, passed, stale, held,
    needs_person`, plus `strong` at `strong` and above, plus `signed` at `signed`; the rollup
    adds `test_strength` and `latest_record`; the summary adds `features`. `met` counts rules
    with `meets_gate` true.
12. **`test_hash_kind`** is `file`, `manual` or `none`, as `signatures.test_hash_kind` returns.
13. `records`, `latest_record`, `warnings`, `remote_url` and the feature fields not named in
    Part B1 keep their schema 4 shape and names (`label` stays `label` on a record entry; the
    cell carries `source`).

## Code

- Python 3.9 floor; every `open()` passes `encoding='utf-8'`; stdlib only under `scripts/`.
- Nothing under `scripts/`, `skills/`, `agents/`, `references/` or `templates/` cites `dev/`
  or this repository's own `specs/`. A consumer's checkout has neither.
- Before any test run: `export PATH=/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH`. Before
  any xUnit run: `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH`.
- Never `git checkout -- specs/`: it reverts spec edits. Restore proof JSON with
  `git checkout -- 'specs/**/*.proofs-*.json'` and remove untracked ones with
  `git clean -f specs/`. Never commit a `.proofs-*.json` file your commit's feature did not
  change.
- When you change a proof plugin under `scripts/proof/`, re-copy it to
  `dev/fixtures/consumer-ci/.purlin/plugins/` and `.purlin/plugins/`: two proofs compare the
  copies byte for byte.
- Feature renames (`approvals` to `signatures`, `skill_approve` to `skill_sign`,
  `skill_verify` to `skill_audit`) follow `skills/rename/SKILL.md` "What carries the name"
  by hand in the worktree: `git mv` the spec and the evidence directory, rename
  `.purlin/records/<old>/` with `git mv`, rewrite every proof marker's feature token, rewrite
  `# Feature:` and every `> Requires:` entry whole-word, then `sync_status` must resolve every
  reference. RULE and PROOF renumbering goes through `ids.renumber`. Keep every marker's
  feature and RULE id aligned with the rewritten spec; renumber markers when the spec
  renumbers.
- Format files under `references/formats/` bump `> Format-Version:` in the same commit as the
  code they govern, per `CLAUDE.md`. Lane 1B owns `signature_format.md` (from
  `approval_format.md`, version 3); lane 2B owns `record_format.md` (version 2); lane 5B owns
  the wording of `spec_format.md`, `proofs_format.md` and `anchor_format.md` and touches
  neither of the other two.

## Tests

- Run whole test files, never a `-k` subset: a filtered run truncates that file's proof JSON.
- `dev/run_tests.sh` in your worktree before you report. Green means: every test your brief
  names passes, `dev/test_vocabulary.py` passes, and every other failure is one your brief
  lists under "Expected red" or one you name in your report with the lane that owns it. Phase
  0 changed the fixtures and the gate values before the code, so a later lane's tests may be
  red in your worktree; do not fix another lane's test, name it.
- Spec maxima: report the highest RULE and PROOF id per touched spec, read with
  `grep -o "^- RULE-[0-9]*" <spec> | sort -t- -k3 -n | tail -1` and the same for PROOF.
- Test count deltas: the pytest summary line before and after, per commit.

## Commits

- Prefix from `references/commit_conventions.md` (`feat(<name>):`, `fix(<name>):`,
  `test(<name>):`, `docs:`, `chore:`), one logical change per commit, and end every message
  with these two lines:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TWQME4FLjSPpNwDAXT2wkB
```

- Set `PURLIN_SKIP_DIGEST=1` in the environment of every `git commit`.

## Finishing

1. Run the acceptance commands from your brief; they must pass.
2. `git rebase three-levels` inside your worktree (other lanes land there while you work),
   then run the acceptance commands again.
3. `git status` clean after `git clean -f specs/`.
4. End your final message with the report in this shape:

```
DONE <lane>
branch: lane/<lane>  head: <sha>  pushed: yes|no
files: <created / rewritten / renamed / deleted, one line each>
specs: <spec path>: RULE max N, PROOF max M   (one line per touched spec)
tests: <acceptance command> -> <pytest summary line or pass/fail>; delta <before> -> <after>
expected red: <test file: reason and owning lane>
decisions: <each choice the plan and this file did not settle, one line with the reason>
undone: <none, or what and why>
```
