# Lane 7B: manual test, and the review list is where a person is needed

Plan: `dev/plans/three-levels.md` (in full, and decision 23 at the top). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Worktree `/Users/richlabarca/LocalCode/purlin-wt/7B`,
branch `lane/7B` off `three-levels`.

## The decision (23)

The phrase `needs a person` is retired outright, any casing, as a cell word, a flag, a summary
key, a `why` token, a filter, a tile, a message and in prose. It meant two different things:
a test that must be manual, and a rule waiting on a person. From now on:

- A rule whose proofs are `@manual` reads **`manual test`** in its strong cell (the test itself
  must be manual; a person runs it and a signer's `--note` records it). Flag `manual`, summary
  and rollup key `manual`, `why` token `manual test`, review-list summary column `manual`.
- A rule whose model review could not settle, or that has no brief for the current hashes when
  its risk asks for one, reads **`unsettled`** in its strong cell (reason `review not settled`
  or `no brief for the current hashes`). Flag `unsettled`, summary and rollup key `unsettled`,
  `why` token `unsettled`.
- A held rule reads **`held`** in its strong cell as well as its signed cell (reason `held by
  <email>: <case>`); flag `held` as today.
- The strong cell's words are therefore `strong`, `weak`, `manual test`, `unsettled`, `held`.
  The `why` tokens are the closed set `unsigned`, `stale`, `held`, `manual test`, `unsettled`.
- **The review list is the one place a person is needed.** Its membership rule is unchanged:
  a rule blocked at `strong` with `manual test`, `unsettled` or `held`, or at `signed` with
  `unsigned`, `stale` or `held`. Its header stays `<n> rules need a person`; that sentence is
  the only place the words "need a person" survive, and only in that sentence shape (the
  vocabulary guard allows the literal `rules need a person` and `rule needs a person`, and
  nothing else).
- `flags.needs_person` and `summary.needs_person` are gone: `manual` and `unsettled` replace
  them. `CELL_TONES`: `manual test` and `unsettled` warn.

## What you own

Everything that carries the phrase. Start with `grep -rni "needs a person\|needs_person\|needs-a-person\|needs a human" --include=* .` outside `.git`, `.purlin/records`, `.purlin/briefs` and `dev/plans/`:

- `dev/fixtures/report/team.json` and `regulated.json` (the contract: team login RULE-1 and
  regulated checkout_design RULE-1 read `unsettled`; regulated login RULE-3 reads `held` in the
  strong cell; the flags and summaries follow; add one `manual test` rule to regulated: a new
  low-risk invoice RULE-3 with a `@manual` proof, strong cell `manual test`, signed cell
  `not required`, on the review list with why `manual test`).
- `scripts/mcp/purlin/states.py`, `payload.py`, `status.py`, `drift.py`
  (`qa.needs_person` becomes `qa.manual` and `qa.unsettled`), `scripts/review/sign.py`
  (`signable()`, `--note` allowed on `manual test` and `unsettled`, the walk's rendering),
  `scripts/review/brief.py`, `scripts/ci/gate_check.py` (the `Weak (n)` section header is
  wrong for these words: split the strong section into `Weak (n)` for `weak` and
  `Waiting on a person (n)` for `manual test`, `unsettled` and `held`, JSON keys `weak` and
  `waiting`), `scripts/report/scan.py`, `scripts/report/src/app.js` (`CELL_TONES`, `level`
  helpers), `filters.js` (`Weak` filter stays `weak` only), `review.js` (the risk summary
  columns: unsigned, stale, held, manual, unsettled), `rule.js`, `board.js` only where a word
  appears (lane 7A rewrites its layout in parallel; do not touch `styles.css` or the count
  renderers).
- `skills/*/SKILL.md`, `agents/purlin.md`, `references/*.md` and `references/formats/*.md`,
  `README.md`, `CLAUDE.md`, `docs/*.md`, `tools/QA/purlin-qa-report.md` (then
  `bash dev/pack_tools.sh`), `RELEASE_NOTES.md` 0.10.0 entry, `design/components/**` where the
  word appears.
- `dev/plans/lanes/tl-_rules.md` items 5 and 8 and the fixture list; nothing else under
  `dev/plans/`.
- `dev/test_vocabulary.py`: `LITERALS` gains `needs a person`, `needs_person`,
  `needs-a-person`; a new `ALLOWED_PHRASES` tuple holds `rules need a person` and
  `rule needs a person`, and a line is skipped only when every hit on it is inside one of
  those phrases.
- Every test that asserts the old words: `dev/test_mcp_server.py`, `test_review_list.py`,
  `test_signatures.py`, `test_holds.py`, `test_gate_check.py`, `test_brief.py`,
  `test_run_script.py`, `test_scan*.py`, `test_drift.py`, `test_skills.py`,
  `test_purlin_report.py` (the assertions on words and filters only; lane 7A owns the layout
  assertions), `test_init_e2e.sh` (the gate walk's expected lines).
- Specs whose rules say the word: `specs/mcp/states.md`, `specs/review/signatures.md`,
  `specs/review/brief.md`, `specs/ci/gate_check.md`, `specs/run/records.md`,
  `specs/run/run_script.md`, `specs/mcp/drift.md`, `specs/dashboard/purlin_report.md` (the
  word rules only), `specs/skills/skill_sign.md`, `skill_status.md`, `skill_find.md`,
  `specs/tools/qa_report.md`, `specs/instructions/purlin_agent.md`. Keep every marker aligned.
- `references/glossary.md`: `needs a person` joins the retired table with this replacement
  text; `manual test` and `unsettled` join the words and the chain table.
- Formats: `record_format.md` and `signature_format.md` only if they name the word; bump only
  if a field changes (none should).

## Acceptance

```
grep -rn "needs a person\|needs_person" --exclude-dir=.git --exclude-dir=.purlin --exclude-dir=plans . | grep -v "rules need a person\|rule needs a person\|glossary.md\|test_vocabulary.py"   (nothing)
pytest dev/test_vocabulary.py dev/test_mcp_server.py dev/test_review_list.py dev/test_gate_check.py dev/test_signatures.py dev/test_holds.py dev/test_brief.py dev/test_scan.py dev/test_scan_review_list.py dev/test_drift.py dev/test_skills.py dev/test_run_script.py
bash dev/test_init_e2e.sh
bash dev/run_tests.sh --fast
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima per touched spec and the test
delta. Do not run the browser suite (`dev/test_purlin_report.py`) against the fixtures until
lane 7A has landed; name its word assertions you changed.
