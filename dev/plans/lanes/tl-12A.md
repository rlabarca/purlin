# Lane 12A: the bar replaces risk; not audited and unsettled; Review and Sign; Signable

Plan: `dev/plans/three-levels.md` (in full; decision 30 is yours and overrides 23, 29 and Part
A where they disagree). Rules: `dev/plans/lanes/tl-_rules.md` (in full). Worktree
`/Users/richlabarca/LocalCode/purlin-wt/12A`, branch `lane/12A` off the stack tip. **Do not
push. Do not open a pull request.** Your work stays committed on your branch. Lane 12B does
the board and the docs in parallel from the same decision text; you own the code, the tests,
the specs, the formats, the fixtures, and the words in skills and references.

## Decision 30, restated as code

1. **The bar.** A rule tag `[bar: passed]` or `[bar: strong]`. `specs.py` parses it; a rule
   with no tag has the project's gate as its bar (`passed` at `passed`; `strong` at `strong`
   and `signed`). Payload: `rules[].bar`, `rules[].bar_from` (`tag` | `gate`). The rule's
   `risk` field, the `[risk:]` tag, `ai_review_at`, `sign_at`'s old meaning and every
   risk-keyed decision are gone: `gate.py` drops `ai_review_at`; `RETIRED_KEYS` gains it and
   `risk`. `spec_format.md` bumps: `[bar:]` documented, `[risk:]` retired, with the migration
   `high` and `medium` → `[bar: strong]`, `low` → `[bar: passed]`, which `update.py` applies
   to a consumer's specs and `ids`/`specs` tooling keeps hashing the same way (the bar is
   inside the signature's hash set, as risk was).
2. **The AI audit runs on every rule whose bar is `strong`**, none other. `brief.py`'s
   `write_briefs` selects by bar. A rule whose bar is `passed` never reads `unsettled` or
   `not audited`.
3. **The strong cell's words** are `strong`, `weak`, `not audited`, `unsettled`, `manual test`,
   `held`. `not audited`: the bar is `strong` and no counting brief exists for the current
   hashes; reason `no audit has run on this code`. `unsettled`: the brief exists and
   `settled` is false; reason `the AI audit could not settle`. `manual audit` is retired
   outright (the vocabulary guard). `flags.audit` becomes `flags.unsettled`; rollup and
   summary keys `unsettled`, `not_audited`.
4. **Cleared its bar.** A rule has cleared its bar when its bar is `passed` and its passed
   cell is met, or its bar is `strong` and its strong cell is met. Payload: `rules[].cleared`.
5. **`sign_at`** is `strong` or `all`, set by init at the `signed` gate (question with one
   sentence each; `--update` re-asks; config key kept, values changed; an old value maps:
   `medium` and `high` → `strong`, `low` → `all`). A rule **needs a signature** when the gate
   is `signed` and (`sign_at` is `all`, or its bar is `strong`). The signed cell reads
   `signed`, `unsigned`, `stale`, `held`; `not required` is gone: a rule that needs no
   signature has `cells.signed.required` false and its word is `signed` only when a
   counting signature exists, else `unsigned`, and neither blocks the gate.
6. **Signable.** `rules[].signable`: cleared its bar, needs a signature, and its signed cell
   is not `signed` (so `unsigned`, `stale` or `held`). `summary.signable`,
   `rollup.signable`. A rule meets the gate `signed` when it has cleared its bar and, if it
   needs a signature, its signed cell reads `signed`.
7. **Two lists.** `review_list` holds the rules whose strong cell reads `manual test`,
   `unsettled` or `held` (kind = that word); exists at `strong` and above. `sign_list` holds
   the signable rules; exists at `signed`. Both ordered bar `strong` first, then feature and
   rule id. `sign.py`: the walk goes through `review_list` then `sign_list`; `signable()`
   reads `sign_list`. `purlin:status` prints `<n> rules to review` and `<n> rules to sign`
   with the two lists' counts; `gate_check.py` sections: `Not passed`, `Partial`, `Weak`,
   `Not audited`, `To review`, `To sign`.
8. **The board's strings** (`scripts/mcp/purlin/board.py`, mirrored by lane 12B in app.js):
   `COLUMNS` gains `Signable` between `Strong` and `Signed` (at `signed`): `<n> of <rules>`.
   Bucket labels unchanged. Tiles unchanged; a `To sign` flag card beside `Stale` at
   `signed` is lane 12B's, fed by `summary.signable`.
9. **This repository's specs**: every `[risk: …]` tag replaced by the mapped `[bar: …]` tag
   with the migration code itself, in one commit, so the migration is proven on 500 rules.
   `.purlin/config.json` here: `sign_at: strong`.
10. `references/`: `glossary.md` (bar, cleared, signable, not audited, unsettled, the two
    lists; `risk`, `manual audit`, `not required`, `ai_review_at` in the retired table),
    `hard_gates.md`, `review_criteria.md`, `spec_quality_guide.md` (writing the bar),
    `purlin_commands.md`, `commit_conventions.md`, `drift_criteria.md` (`qa` rows by the two
    lists), `rule_examples.md`; `skills/spec`, `sign`, `audit`, `status`, `init`, `find`,
    `build` and `agents/purlin.md` where they name risk or the old words. Lane 12B does the
    docs pages.

## Tests and specs

Every test and spec that names risk, `ai_review_at`, `manual audit`, `not required`,
`needs_person`, the review list's membership or `sign_at`'s old values. New tests for the
bar's parse and default, the migration on a spec fixture, `not audited` versus `unsettled`,
`cleared`, `signable`, both lists, the gate check's sections, init's `sign_at` question, and
the status lines. Fixtures: `dev/fixtures/report/*.json` to schema 7 with `bar`, `bar_from`,
`cleared`, `signable`, `unsettled`, `not_audited`, `sign_list`, and a `not audited` rule and
an `unsettled` rule in regulated; `tl-_rules.md` items 5, 8 and 11 follow (you may edit that
file for this). Keep every marker aligned.

## Acceptance

```
pytest dev/test_mcp_server.py dev/test_review_list.py dev/test_signatures.py dev/test_holds.py dev/test_gate_check.py dev/test_brief.py dev/test_init_scaffold.py dev/test_init_update.py dev/test_run_script.py dev/test_records.py dev/test_scan.py dev/test_skills.py dev/test_schema_spec_format.py dev/test_vocabulary.py
bash dev/test_init_e2e.sh
bash dev/run_tests.sh --fast
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima, the test delta, the fixture
keys, the exact wording of init's `sign_at` question, decisions, and anything undone.
