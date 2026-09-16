# Purlin 0.10.0: three levels

One ladder of seven states becomes a spec status plus three evidence levels, three commands
carry the three levels, and the gate level is the only thing that decides how much of the chain
anyone sees. Written 2026-09-16 from a full scan of the code, the dashboard, the skills, the
references, the docs, this repository's own specs, tests, signatures and records, then settled
with the user question by question. This file is the design and the plan. Lane briefs go in
`dev/plans/lanes/tl-*.md`, written by the orchestrator from Part C. Nothing in this plan is
left to a lane's judgment except wording.

0.10.0 was never released. This work ships as 0.10.0: `VERSION` stays, no bump, and the
0.10.0 entry in `RELEASE_NOTES.md` is overwritten as the phases land.

## Decisions (all made by the user; no lane reopens any)

1. **Three levels, three gate values, three commands.** `passed` / `strong` / `signed`. The gate
   value is the word the cell reads when the level is met. `purlin:test` runs level 1,
   `purlin:audit` runs level 2 and writes the record, `purlin:sign` is level 3 and walks the
   review list when given no rule. `purlin:verify`, `purlin:review` and `purlin:approve` are
   gone, not aliased. Twelve skills.
2. **Level 2 is fully automatic.** A person first appears at level 3.
3. **Spec status is Drafted or Ready.** Ready means the proof text clears the blocking free
   checks.
4. **The brief reports, it recommends nothing.** Strength beside the minimum, the free-check
   findings, what the model review observed, and whether it could settle the question. The four
   verdict words are retired.
5. **A local pass meets level 1.** Under `strong` and `signed` only a CI record counts; a local
   `purlin:audit` there is a preview that says it does not count.
6. **Under `passed`, `purlin:audit` runs the tests only** and the record carries strength
   `n/a`. Raising the gate to `strong` turns the breaks on, locally and in CI.
7. **Under `signed`, a signature is required at or above `sign_at`, default `medium`.** Low risk
   meets the `signed` gate at strong. `sign_at: low` signs everything.
8. **CI writes no signature file, ever.** The `.ci.json` auto-approval is gone. Signature
   directories hold only files a person wrote.
9. **Briefs live in `.purlin/briefs/<feature>/`** beside the records, committed by CI. The CI-only
   branch ruleset covers `.purlin/records/**` and `.purlin/briefs/**`.
10. **The old approval files, CI files and briefs are dropped, not migrated.** This checkout's 37
    `.approvals/` directories and its `.purlin/records/` are deleted by hand in Phase 7. The
    0.9.5 → 0.10.0 migration in `update.py` lands a project straight on the new layout; there is
    no migration from the intermediate layout and no test for one. The user re-signs afterwards.
11. **Rule text is rewritten freely** wherever the model changes what a rule claims.
12. **A `@manual` proof, or a model review that could not settle, reads `needs a person`**, and a
    signature file from anyone clears it under `strong`; under `signed` the signer rules apply.
13. **The review list carries only what needs a person**: unsigned, stale, held, needs a person.
    A weak rule is build work and stays on the board.
14. **Tiles**: `Untested`, `Failing`, `Passed`; `Strong` at `strong`; `Signed` and a `Stale` flag
    card at `signed`. **Columns**: `Spec`, `Rules`, `Spec status`, `Tests`, `Last run`; `Strength`
    and `Strong` at `strong`; `Signed` at `signed`.
15. **Retired outright, any casing, whole word**: `tested`, `recorded`, `approved`, `approve`,
    `approval`, `approver`, `approvers`, `verified`, `verdict`, `Reviewed`, `re-verify`, plus the
    phrases `Proof ready`, `lowest state`, `seven states`, `auto-approval`, `review queue`. Plain
    English uses are rewritten too. `verify` as a verb stays legal; the names `purlin:verify`,
    `verify_gate`, `verify-gate:` are retired. `Stale` survives only as `signature stale` and the
    adjective. `record` and `review list` survive. **`audit` is un-retired**: it leaves the
    glossary's retired table and `dev/test_vocabulary.py`'s word list, and means one thing, the
    level 2 run: an audit proves a rule strong or weak. The old `purlin:audit`'s grading scores
    (gauge, Proof Design, Proof Integrity) stay retired.
16. **`scripts/ci/verify_gate.py` becomes `scripts/ci/gate_check.py`**, log prefix `gate:`, spec
    `specs/ci/gate_check.md`, JSON key `result` instead of `verdict`. `purlin:audit --tag`
    writes `record/<name>` tags.
17. **The docs page `review-and-approval.md` becomes `review-and-signing.md`.**
18. **In scope as extras**: delete `dev/screenshots/`; update `design/components` StatusPill and
    cards to the cell words; restate `dev/plans/TODO-0.10.0.md` and `held-rules-0.10.0.md` in the
    new words after Phase 7; overwrite the `RELEASE_NOTES.md` 0.10.0 entry.
19. **Execution**: one Opus orchestrator, unattended through Phase 7, one subagent per lane in
    its own worktree. Opus for every lane except the two word-swap lanes (5C, 6B), which run on
    Sonnet.
20. **`states.py` keeps its name** and so does the `states` spec; its subject is "the spec status
    and the three evidence levels of a rule". `approvals.py` → `signatures.py`, `approve.py` →
    `sign.py`.
21. **Risk stays inside the signature's hash set.** A risk re-tag stales a signature.
22. **Format versions bump as `CLAUDE.md` says**: record 1 → 2, approval 2 → signature 3, payload
    schema 4 → 5, drift criteria 3 → 4. Spec, proofs and anchor formats change wording only.

---

# Part A: the design

Every doc, skill, reference, message and test uses these words and no others.

## A1. Vocabulary

- **spec status**: what the spec says about a rule. **Drafted**: no proof line names it.
  **Ready**: at least one proof names it and no blocking free check fires on the proof text.
- **evidence level**: one of three questions about a rule, each answered by its own cell.
  **passed**: every tagged test for the rule passed. **strong**: the tests are worth trusting.
  **signed**: a person signed the rule, proof and test hashes.
- **cell**: the answer to one level for one rule. A cell reads one word, carries its reasons,
  and exists only at or below the project's gate. Above the gate a cell is absent, not empty.
- **gate**: the one project setting, `passed`, `strong` or `signed`. A rule **meets the gate**
  when every cell up to the gate's level is met.
- **run**: one execution of the tagged tests. **record**: the machine's evidence of one run:
  results, strength and scope tree, written by `purlin:audit`, committed by CI. Nobody signs a
  record. **source**: where a pass came from: `ci` (a record CI wrote), `developer` (a record a
  person committed), `local` (the last run in this checkout). Under `passed` every source
  counts. Under `strong` and `signed` only `ci` counts.
- **current**: a record describes the checkout when its commit is HEAD or its scope tree still
  hashes the same. A CI pass that is not current reads **code changed**, and CI clears it on the
  next run.
- **audit**: the level 2 run: the tests, then the breaks, the free checks and the model review
  where risk asks, ending in a record and, on CI, the briefs. An audit proves a rule strong or
  weak. **the breaks**: deliberate changes to the code; **test strength**: the share the tests
  caught, as a percentage. Measured only at `strong` and above.
- **brief**: the machine's report on one rule: the strength beside the minimum, the free-check
  findings on the proof text and the test body, the model review's observations, and whether it
  settled. It recommends nothing.
- **signature**: a named person's attestation that a rule, proof and test belong together, a
  committed file. **signer list**: `signers` in `.purlin/config.json`. **hold**: a person's
  committed statement that the test does not prove the proof, with the missing case.
  **note**: the one line a signer writes for a `@manual` proof or an unsettled review.
- **signature stale**: the signed cell's word when a signature exists and its hashes no longer
  match.
- **review list**: the rules whose next step is a person. Exists only at `strong` and above.
- **risk**: unchanged tag, default `low`. Read only at `strong` and above; never asked, shown
  or required under `passed`.
- **rollup**: rules meeting the gate out of rules total, plus one count per bucket.

## A2. The chain

For one rule, top to bottom. Each row is a cell; the gate decides how many rows exist.

| Level | Met when | Words the cell can read | Reasons it carries |
|-------|----------|-------------------------|--------------------|
| spec | proof text clears the blocking free checks | `drafted`, `ready` | the blocking finding names |
| passed | every proof has a passing test from a counting source, and a CI pass is current | `passed`, `failed`, `no test`, `not run`, `code changed` | `failing: <where>`, `<os>: no record yet`, `code changed since <commit7>`, `developer record does not count under <gate>`, `local run does not count under <gate>` |
| strong | passed from `ci`; strength at or above `min_strength`, or `n/a` with no engine and no blocking proof-text finding; no test-body finding; when risk is at or above `ai_review_at`, a brief for the current triple that observed nothing and settled; no hold | `strong`, `weak`, `needs a person` | `strength 64% under 80%`, `no engine: free checks only`, the finding names, the observation sentences, `manual proof`, `review not settled`, `held by <who>: <case>` |
| signed | a counting signature for the current hashes, when risk is at or above `sign_at`; `not required` below it | `signed`, `unsigned`, `stale`, `held`, `not required` | `by <email>`, `the signing commit is not signed`, `the signer is not on the list`, `the signer last touched the test`, `the signing commit is not on <branch>`, `hashes changed after the signature` |

A signature file for the current hashes clears `needs a person`: from anyone under `strong`,
from a counting signer under `signed`. A hold blocks both the strong and the signed cell while
it is current, and a signature by a person outranks it.

A rule's **bucket** is the one tile it is counted in: `untested` (drafted, or ready with no
test or no run), `failing`, `passed` (level 1 met, and either the gate is `passed` or level 2
is not met), `strong`, `signed`. Two flags are counted beside the buckets, never instead of
them: `stale` and `held`.

## A3. The gate

| Gate | Cells that exist | What CI requires before merge | Derived defaults |
|------|------------------|-------------------------------|------------------|
| `passed` | spec, passed | every rule's passed cell is met; any source | `min_strength` unused, `ai_review_at` never, `sign_at` n/a, tags optional, breaks off |
| `strong` | + strong | every rule's strong cell is met; only `ci` counts | `min_strength` 70, `ai_review_at` high, `sign_at` n/a, tags optional |
| `signed` | + signed | every rule's signed cell is met; signer list present | `min_strength` 80, `ai_review_at` medium, `sign_at` medium, risk and origin required |

Branch rules `purlin:init` prints: (1) require a pull request and the `purlin` check, Actions app
the only bypass; (2) restrict `.purlin/records/**` and `.purlin/briefs/**` to the Actions app;
(3) no force push, no deletion. Under `passed` only (3). Azure: the build service alone holds
Contribute on those two paths.

A signature counts when: the commit that added the file is signed and verifies; the author's
email is on `signers` as of that commit; that author did not author the last commit to the test
file; the bound hashes match; and under `signed` the commit is on the protected branch.

## A4. Commands

| Command | Purpose (the one sentence) | Writes |
|---------|----------------------------|--------|
| `purlin:test [feature]` | Run the tagged tests and print each rule's passed cell | `.purlin/runtime/proofs/` |
| `purlin:audit [feature] [--commit] [--ci] [--tag <name>] [--remote]` | Run the tests and the breaks, then write the record | `.purlin/records/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json`; under `--ci` also `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`; `--tag` writes `record/<name>` |
| `purlin:sign` | Walk the review list one brief at a time, signing, holding or skipping | signatures and holds, in signed commits |
| `purlin:sign <feature> [RULE-N ...]` | Sign a rule, a feature or a batch as a signed commit | `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json` |
| `purlin:sign --batch` | Sign everything currently signable | same |
| `purlin:sign <feature> RULE-N --hold "<case>"` | Hold a rule: the test does not prove the proof | `<RULE-N>.<hash8>.<holder-slug>.hold.json` |
| `purlin:sign <feature> RULE-N --note "<text>"` | Sign a `@manual` proof's evidence, or settle what the model could not | the signature file with `note` set |
| `purlin:status` | Show every rule's cells and what blocks the gate | nothing |
| `purlin:init --gate passed\|strong\|signed` | unchanged syntax, new values | config, workflow, readmes |

`purlin:build`, `purlin:spec`, `purlin:spec-from-code`, `purlin:find`, `purlin:drift`,
`purlin:anchor`, `purlin:rename` keep their syntax. The walk's answers are human actions: sign,
add a case (a proof line the reviewer writes), hold, skip.

Commit prefixes: `sign(<feature>): RULE-N ...`, `sign(batch): <feature> RULE-N, ...`,
`hold(<feature>): RULE-N ...`, `purlin: record for <commit7>` (records and briefs only).

## A5. Skills scale with the gate

Under `passed`: `purlin:status`, `purlin:find`, `purlin:test`, `purlin:audit`, the pull
request comment and the board print no strength, no risk, no review list, no signature.
`purlin:audit` runs no breaks. `purlin:spec` does not ask for a risk tag. `purlin:sign` says
the gate is `passed` and what `purlin:init --gate strong` would add, then stops. `purlin:drift
qa` says the same.

Under `strong`: strength, the strong cell, the review list and risk appear. A local
`purlin:audit` prints its strength as a preview and says only CI's record counts.
`purlin:sign` works for the walk, `--note` and `--hold`; a bare signature says signatures are
required only under `signed`, then writes it anyway if asked.

Under `signed`: the signed cell, the signer list, the sign panel.

## A6. Surfaces

**Board** (build and test). Headline: `<met> of <rules> rules meet the gate <gate> · <failing>
failing`. Tiles per decision 14. Spec table columns: `Spec`, `Rules`, `Spec status`
(`ready · drafted`), `Tests` (`passed · failing · no test`, each count in its tone), `Last run`
(source, os, age); at `strong` add `Strength`, `Strong` (`n of m` with a bar); at `signed` add
`Signed` (`n of m`, stale count in the fail tone). No risk column, no coverage column, no state
column, no risk-by-state grid. Expanded rule rows: id, text, one pill per existing cell.
Filters: `Untested`, `Failing`; at `strong` add `Weak`; at `signed` add `Unsigned`, `Stale or
held`.

**Rule screen**: spec status, then one row per existing cell with its word and reasons, then
Proofs. At `strong` and above, the Brief panel: strength beside the minimum, the findings, the
observations, each in one sentence naming the proofs it concerns. At `signed`, the Sign panel:
`purlin:sign <feature> <RULE-N>` or `Signed by <email>`.

**Review list** (tab exists at `strong` and above). Header: `<n> rules need a person`, then the
risk summary: one line per risk with counts of unsigned, stale, held and needs-a-person. Rows
grouped by risk high first, stale and held first within a group; each row carries feature, rule
id, text, risk tag, the blocking cell's word, and its reasons.

**Status table** (`purlin:status`, the pull request comment, `scan.py`): `Feature | Rules |
Spec | Tests | Run` then `| Strength | Strong` at `strong` then `| Signed` at `signed`. Summary
line: `<met> of <rules> meet the gate <gate>`. Then one `→ Next:` line.

**Gate check** (`scripts/ci/gate_check.py --check`): sections `Not passed (n)`, `Weak (n)`,
`Not signed (n)`, each rule with its blocking reason. Log prefix `gate:`. JSON: `{gate,
min_strength, commit, rules, met, not_passed, weak, not_signed, result, exit, signer_list?}`.

---

# Part B: technical design

## B1. Payload, schema 5

`scripts/mcp/purlin/payload.py`: `SCHEMA_VERSION = 5`; `scripts/report/src/app.js`
`SCHEMA = 5`.

```
gate:     {gate, ai_review_at, sign_at, min_strength, mutation_engine, sql_engine, ci,
           signers, test_framework, pre_push}
summary:  {rules, features, met, failing, untested, passed, strong, signed,
           stale, held, needs_person}            # strong/signed absent below their gate
features[]: {name, category, spec_path, ..., rollup: {same keys as summary minus features,
           plus test_strength, latest_record}, rules: [...], signatures: [paths]}
rules[]:  {id, feature, label, text, risk, origin, criterion, rule_hash, proof_hash,
           test_hash, test_hash_kind, design_hash, proofs,
           spec: 'drafted'|'ready',
           cells: {passed: {...}, strong: {...}|absent, signed: {...}|absent},
           bucket, meets_gate, blocked_by: 'spec'|'passed'|'strong'|'signed'|null,
           flags: {failing, stale, held, needs_person, code_changed}}
review_list[]: {feature, owner, rule, risk, cell, why: [tokens]}    # [] under passed
records, warnings, commit, dirty, generated_at, generated_by, project, version
```

Cell shapes:

```
passed:   {word, source: 'ci'|'developer'|'local'|null, current: bool, counts: bool,
           missing_env: [], reasons: []}
strong:   {word, strength: int|null, findings: [], observations: [], brief: path|null,
           settled: bool|null, reasons: []}
signed:   {word, required: bool, signer: email|null, path: str|null, reasons: []}
```

Gone: `states`, `project_rollup`, `counts`, `lowest_state`, `proved`, `by_risk`,
`re_verify_pending`, `needs_review`, `flags.auto_approvable`, `flags.needs_ai_review`,
`flags.on_review_list`, `review_list[].reason`, `reasons`. `why` tokens are the closed set
`unsigned`, `stale`, `held`, `needs a person`, `manual`.

## B2. Core package `scripts/mcp/purlin/`

- `gate.py`: `GATES = ('passed', 'strong', 'signed')`; `_DERIVED` gains `sign_at` (`None`,
  `None`, `'medium'`) and `breaks` (`False`, `True`, `True`); `GateConfig` slot `signers`
  replaces `approvers`, `tags_required` is dropped; `RETIRED_KEYS` gains `approvers`; an
  unrecognised `gate` falls back to `passed` with the existing warning shape.
- `states.py`: rewrite. `rule_cells(inp, cfg)` returns `{spec, cells, bucket, meets_gate,
  blocked_by, flags}`; `feature_rollup` and `project_rollup` count buckets and `met`. No
  `STATE_ORDER`, no `_rank`, no `lowest`, no brief-as-state. Inputs are today's plus `sign_at`,
  the brief's `settled` and `observations`. Keep `_record_verdict` (renamed `_record_passes`),
  `_failing_where`, `_local_passes`.
- `signatures.py` (from `approvals.py`, `git mv`): `signatures_dir()` returns
  `<spec>.signatures`; `SIGNATURE_NAME_RE`, `HOLD_NAME_RE` unchanged in shape; `signer_slug`;
  `load_signatures` reads `signer`; no legacy body, no `is_ci`; `is_current`, `counts`,
  `commit_is_signed`, `commit_author`, `is_ancestor` as today with the new words.
  `ids._approval_paths` uses `signatures_dir()`.
- `payload.py`: schema 5 as B1; `_counting` keyed on the new gate names; review entries only
  when `cfg.gate != 'passed'`; briefs read from `.purlin/briefs/`.
- `records.py` (mcp): `counts_under(gate, label)` keyed on the new values only.
- `checks.py`: `blocks_proof_ready` becomes `blocks_ready`.
- `status.py`: columns and summary per A6; `_directives` from the blocking cell: drafted →
  `purlin:spec`; no test or failing → `purlin:build`; code changed or a non-CI source at
  `strong`+ → push, CI records; weak → `purlin:build` naming the reason; needs a person,
  unsigned, stale, held → `purlin:sign`; everything met → "nothing is outstanding at gate
  <gate>".
- `drift.py`: `qa.signatures_stale`, `qa.review_list_size`, `qa.needs_person`;
  `eng.code_changed`; `design.design_rules_stale` reads the signed cell; `unproved` is
  `spec == 'drafted'`.
- `server.py`: tool descriptions say "the spec status and the cells of every rule".

## B3. Review and gate `scripts/review/`, `scripts/ci/`

- `sign.py` (from `approve.py`, `git mv`): `SCHEMA = 'purlin-signature/1'`, `HOLD_SCHEMA`
  unchanged; body field `signer`; `gate` at signing; `note` field, null unless `--note`;
  `--note` allowed on a rule whose strong cell reads `needs a person`; the walk (from
  `skills/review`'s steps: read the review list, render each brief, take the answer) lives
  here as the no-argument path; `auto_approve` deleted; `signable()` lists rules whose signed
  cell is `unsigned` or `stale`, or whose strong cell is `needs a person`; messages `sign:
  signer list missing: run purlin:init --gate signed`, `<email> is not on the signer list`;
  under `passed` prints what the gate lacks and exits 2; commit subjects per A4.
- `brief.py`: path `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`; `SCHEMA =
  'purlin-brief/2'`; `state`, `verdict`, `reasons` dropped; `observations` and `settled`
  added; `verdict_for` deleted; `model_prompt` asks the model to state what the test observes
  against what the proof names and to say when it cannot tell, never to recommend;
  `write_briefs` iterates the rules whose risk is at or above `ai_review_at` and whose passed
  cell counts; `render_brief` prints strength beside the minimum, the findings, the
  observations.
- `gate_check.py` (from `verify_gate.py`, `git mv`): `_REQUIRED_STATE` and `_rank` deleted;
  the check is `rule['meets_gate']` with `blocked_by` choosing the section; JSON per A6;
  `_SIGNER_LIST_MISSING = '→ signer list missing: run purlin:init --gate signed'`; `PREFIX =
  'gate:'`.
- `scripts/run/purlin_run.py`: `--record` skips the breaks when `cfg.breaks` is false;
  `_ci_review` writes briefs only; the record commit carries records and briefs;
  `build_record` writes the new gate value; `RECORD_SCHEMA = 'purlin-record/2'`,
  `schema_version` 2; `_VALIDATED_PREFIX` → `refs/tags/record/`. `scripts/run/records.py`
  docstrings follow. `scan.py` prints the bucket lines and the review list per A6.

## B4. Init and update `scripts/init/`

- `scaffold.py`: `GATE_CHOICES` three new answers; `SIGNER_QUESTION`; `write_config` writes
  `signers` under `signed` and never `approvers`; `_BRANCH_RULES` per A3; readmes;
  `print_signed`; `--gate` choices from `gate_module.GATES`; the workflow it writes runs
  `purlin_run.py --all --record --ci` as today.
- `update.py`: the existing 0.9.5 → 0.10.0 migrations now land on this layout: gate values
  `passed`/`strong`/`signed`, `signers`, no approvals directory. `GATE_QUESTION` in the new
  words; the retired-spelling table (`# retired` rows) gains the retired names from decision
  15. No migration from the intermediate layout. `dev/fixtures/upgrade-0.10-dev/` is deleted
  with its tests; `upgrade-0.9.5/` stays.
- `templates/config.json`: `gate: passed`. `templates/gitignore.purlin`:
  `.purlin/briefs/**/*.brief.txt`.

## B5. Dashboard `scripts/report/src/`

- `app.js`: `SCHEMA = 5`; `STATES`/`TONES` replaced by `BUCKETS` and `CELL_TONES` (`passed`,
  `strong`, `signed` pass; `failed`, `stale` fail; `no test`, `not run`, `code changed`,
  `unsigned`, `weak`, `needs a person`, `held` warn; `drafted`, `not required` idle);
  `pill(word)` solid only for `signed`; `hasRisks`, `hasRecords`, `hasApprovals` replaced by
  `level(name)` reading `DATA.gate.gate`.
- `board.js`: `statStrip` from `DATA.summary` and `level()`; `riskGrid` deleted;
  `boardColumns`, `featureRow`, headline per A6.
- `filters.js`: the five filters per A6, each gated by `level()`.
- `rule.js`: cell rows; `briefPanel` at `strong`+; `signPanel` at `signed`; `signerOf` reads
  the file's third dot part.
- `review.js`: risk summary block, six columns, `why` tokens rendered as sentences.
- `styles.css`: `.tiles` uses `repeat(auto-fit, minmax(0,1fr))`; `.strip` two columns only
  when the flag card exists; `.grid` rules deleted; `.rev` six columns.
- `dev/capture_doc_screenshots.py` descriptions in the new words; the five shots keep their
  names. Fixtures `dev/fixtures/report/{solo,team,regulated}.json` rewritten by hand to
  schema 5 first. `regulated` keeps one stale rule, one held rule, one `needs a person` rule,
  one `code changed` rule, one `weak` rule and one `windows: no record yet` rule.

## B6. Formats `references/formats/`

| File | Now | Change |
|------|-----|--------|
| `spec_format.md` | 11 | wording: the risk tag's meaning, `@manual`, the `@env` sentence. No bump. |
| `proofs_format.md` | 8 | wording: `@manual`. No bump. |
| `anchor_format.md` | 7 | wording: "stales the signatures". No bump. |
| `record_format.md` | 1 | **bump to 2**: `gate` enum, `purlin-record/2`, `test_strength` null under `passed`, source, Freshness says code changed |
| `approval_format.md` | 2 | **`git mv` to `signature_format.md`, bump to 3**: directory, filename grammar, `purlin-signature/1`, `signer`, `note`, `gate` enum, no CI variant, holds unchanged |

`references/drift_criteria.md` `> Criteria-Version:` 3 → 4. `CLAUDE.md` format table row
renamed.

## B7. Vocabulary enforcement

`dev/test_vocabulary.py`: `WORDS` gains every retired word from decision 15, matched whole-word
and case-insensitive (so `Untested` and `test_` never match `tested`); `LITERALS` gains the
retired phrases and the names `purlin:verify`, `purlin:review`, `purlin:approve`,
`verify_gate`, `verify-gate:`, `validated/`; `EXCLUDED` drops `"specs/"` and keeps `dev/plans/`,
`design/tokens/`, `RELEASE_NOTES.md` (rewritten anyway), the glossary, `dev/fixtures/upgrade-0.9.5/`
and `.purlin/`; `design/components/` and `design/readme.md` join the checked set once 6B lands.
`PENDING_REWRITE` stages files a phase has not reached; it is empty at closeout.

---

# Part C: execution

## C1. Rules for every lane

- Branch `three-levels` off `evidence-workflow`. Each lane in its own worktree
  `/Users/richlabarca/LocalCode/purlin-wt/<lane>` on `lane/<lane>`, merged back by the
  orchestrator in phase order. Push branches for CI freely. No tags. `VERSION` stays 0.10.0
  and `dev/bump_version.sh` is not run.
- Read this file in full, then `design/readme.md` where the brief says so, then your brief.
- Prose rules from `design/readme.md` "Content fundamentals". No emoji anywhere. Python 3.9,
  stdlib only under `scripts/`, `encoding='utf-8'` on every `open()`.
- Nothing under `scripts/`, `skills/`, `agents/`, `references/` or `templates/` cites `dev/`
  or this repository's `specs/`.
- Tests are tagged for the rewritten spec: keep the `@pytest.mark.proof("<feature>", "PROOF-N",
  "RULE-N")` and `purlin_proof` first argument equal to the spec's feature name, and renumber
  markers when the spec renumbers.
- `dev/run_tests.sh` green in the worktree before the lane reports. Report spec maxima (the
  highest RULE and PROOF ids per touched spec) and test count deltas.
- A lane writes no signature files and runs no `purlin:sign`.
- Feature renames (`approvals` → `signatures`, `skill_approve` → `skill_sign`, `skill_verify` →
  `skill_audit`) go through `scripts/mcp/purlin/ids.py`'s rename path so specs, markers and
  record directories move together. `skill_review` is deleted: its spec, its tests, its record
  directory.

## C2. Phases

Dependencies: 0 → 1 → {2, 3, 4} → 5 → 6 → 7. Phase 4 needs only the fixtures from 0 and can
start with 2 and 3. Phases 5 and 6 need only Part A and can be drafted in parallel with 1 to
4, but their tests (`test_skills.py`, screenshot tests) land after 4.

### Phase 0: contract (orchestrator)

1. Create the branch. Commit this file. Copy Part A into `dev/plans/lanes/tl-_rules.md` with C1.
2. Rewrite `dev/fixtures/report/solo.json`, `team.json`, `regulated.json` to schema 5 (B1,
   B5). These are the contract for phases 1 and 4.
3. `dev/fixtures/consumer-ci/.purlin/config.json`: `gate: strong`. Delete
   `dev/fixtures/upgrade-0.10-dev/`.
4. Arm `dev/test_vocabulary.py` per B7 with every not-yet-rewritten file in
   `PENDING_REWRITE`, so the guard fails only on what a later phase leaves behind. Drop `audit`
   from its word list.
5. Write the lane briefs from this plan.

### Phase 1: core package (2 lanes, Opus)

**1A states and payload.** `gate.py`, `states.py`, `payload.py`, `records.py` (mcp),
`checks.py`, `status.py`, `drift.py`, `server.py`, `ids.py`. Tests: `dev/test_mcp_server.py`
(the 41 state functions, the status-table test at L1075, the gate-defaults test at L580, the
counts-under test at L652), `dev/test_review_list.py`, `dev/test_backing_tests.py`,
`dev/test_failing.py`, `dev/test_drift.py` (L638, L847), `dev/test_scan.py` (L148, L173).
Specs: rewrite `specs/mcp/states.md`; section-rewrite `specs/mcp/drift.md` RULE-7, RULE-14;
`specs/mcp/server.md` PROOF-9; `specs/_anchors/schema_proof_format.md` RULE-1, RULE-3;
`specs/_anchors/schema_spec_format.md` RULE-4.

**1B signatures.** `signatures.py` (from `approvals.py`). Tests: `dev/test_signatures.py`
(from `test_approvals.py`: `TestTheTriple`, `TestStale`, `TestTheFile`, `TestTheSignedCommit`,
`TestTheAncestorCheck`; `TestAutoApproval` deleted), `dev/test_holds.py`. Spec:
`specs/review/approvals.md` → `specs/review/signatures.md` through the rename path,
rewritten: RULE-1..10 hashing and file, RULE-11..16, RULE-39, RULE-41 deleted, RULE-17..23
signing, RULE-24..38 moved to `specs/ci/gate_check.md` in phase 2, RULE-40 holds.

### Phase 2: sign, brief, gate, run (2 lanes, Opus)

**2A sign, brief, gate.** `scripts/review/sign.py` (from `approve.py`, with the walk from
`skills/review`), `brief.py`, `scripts/ci/gate_check.py` (from `verify_gate.py`). Tests:
`dev/test_gate_check.py` (from `test_verify_gate.py`, all 29), `dev/test_brief.py` (L271–296
the model layer, L391, L403, L412, L448), `dev/test_brief_files.py`,
`dev/test_brief_tests_named.py` (L98). Specs: new `specs/ci/gate_check.md` carrying the old
approvals RULE-24..38 rewritten as the three sections and the JSON; `specs/review/brief.md`
RULE-12, RULE-13 (verdicts → observations and settled), RULE-19, RULE-20 (deleted), PROOF-27,
PROOF-28, PROOF-34, PROOF-42.

**2B run and scan.** `scripts/run/purlin_run.py` (`--record` without breaks under `passed`,
`_ci_review`, `build_record`, record schema 2, `record/` tags), `scripts/run/records.py`,
`scripts/run/ci.py`, `scripts/report/scan.py`, `dev/manual/check_qa_tool.py`,
`dev/manual/check_spec.py`, `dev/manual/README.md`. Tests: `dev/test_run_script.py` (L312,
L668, L693, L719, L805, L826, L853), `dev/test_records.py` (L454, L515 and the gate-value
sites), `dev/test_scan_review_list.py`, `dev/test_scan.py` remainder, `dev/test_consumer_ci.py`
(L277, L318). Specs: `specs/run/records.md` RULE-5, RULE-14, RULE-21, RULE-25, PROOF-14,
PROOF-20, PROOF-28, PROOF-29; `specs/run/run_script.md` RULE-17, RULE-20, RULE-42, PROOF-11,
PROOF-17, PROOF-20, PROOF-61, plus the no-breaks-under-passed rule. Format:
`references/formats/record_format.md` to version 2 in the same commit as the record change.

### Phase 3: init and update (1 lane, Opus)

`scripts/init/scaffold.py`, `scripts/init/update.py` (B4), `templates/config.json`,
`templates/gitignore.purlin`. Tests: `dev/test_init_scaffold.py` (the gate and signer
functions at L196–L492, L587, L695; the fixture `--gate` arguments), `dev/test_init_update.py`
(L333–L420; the 0.9.5 fixture lands on the new layout; the 0.10-dev tests deleted),
`dev/test_init_e2e.sh` (the three-gate walk in the new words, `set_signers`, `gate_check.py`),
`dev/test_e2e_required_rules.sh` (L165–L193), the three e2e shell fixtures that write
`{"gate": "tested"}` (now `passed`). Specs: `specs/init/scaffold.md` RULE-2, RULE-3, RULE-4,
RULE-10, RULE-11, RULE-12, RULE-17, RULE-36, PROOF-35, PROOF-41; `specs/init/update.md`
RULE-10, RULE-12, PROOF-10, PROOF-12.

### Phase 4: dashboard (1 lane, Opus)

`scripts/report/src/*.js`, `styles.css`, `dev/capture_doc_screenshots.py`, rebuild through
`dev/build_report.py`, regenerate the five `docs/images/dashboard-*.png`. Tests:
`dev/test_purlin_report.py` (L227, L242, L360, L375, L387, L423, L436, L493, L524, L614,
L689 and `FILTER_CASES`), `dev/test_purlin_report_board_layout.py` (L41, L56). Spec:
`specs/dashboard/purlin_report.md` rewrite of RULE-7, RULE-8, RULE-9, RULE-13, RULE-15,
RULE-16, RULE-18, RULE-26, RULE-30, RULE-32 and their proofs; the 1200-line limit (RULE-2)
holds. Read `design/readme.md` first. Both themes ship, tokens only, no colour literal.

### Phase 5: skills, agent, references, tools (3 lanes)

**5A skills and agent (Opus).** `git mv skills/approve skills/sign`, `git mv skills/verify
skills/audit`, `git rm -r skills/review`; rewrite `skills/sign/SKILL.md` (the walk, the
answers, the write forms), `skills/audit/SKILL.md`, `skills/status/SKILL.md`,
`skills/init/SKILL.md`; section-rewrite `skills/find`, `skills/test`, `skills/spec`,
`skills/drift`; `agents/purlin.md` (the words block, the `sync_status` paragraph, NEVER 2, 3,
4, 5, the routing rows). Every skill's gate-scaling per A5, with `skills/test/SKILL.md` as the
pattern. Tests: `dev/test_skills.py` (L34–38 name list, L223, L238, L247, L257, L499, L538,
L553, L571–596 as `skill_sign`, L656, L716, L723, L770, L818, L822, L862). Specs:
`skill_approve.md` → `skill_sign.md` and `skill_verify.md` → `skill_audit.md` via the
rename path, rewritten; `skill_review.md` deleted; `skill_init.md` RULE-5; `skill_find.md`
PROOF-2; `specs/instructions/purlin_agent.md` RULE-3, RULE-5.

**5B references, formats, tools, root (Opus).** `references/glossary.md` (the words, the
chain, the retired rows from decision 15, the `audit` row removed from the retired table), `hard_gates.md` (rewrite: the level table, source,
the signer list, holds; "Auto-approval" section deleted), `review_criteria.md` (the free checks
stay; "The three risk levels" rewritten; "Verdicts" replaced by "What the brief reports"),
`purlin_commands.md` (twelve skills: anchor, audit, build, drift, find, init, rename, sign,
spec, spec-from-code, status, test; three tables and the syntax block per A4),
`commit_conventions.md` (prefix rows, the signature commit section, the record commit
paragraphs), `drift_criteria.md` (role table, config table with `signers` and `sign_at`,
version 4), `spec_quality_guide.md` (rule tags, `@manual`, "When a rule is stuck" rewritten as
one row per cell word), `references/formats/` per B6, `CLAUDE.md` (format table, one-home
table, the `purlin:build`/`purlin:test` delegation sentence), `README.md` (vocabulary
paragraph, gate table, command table), `tools/QA/purlin-qa-report.md` (Steps 2, 3, 5),
`tools/PM/purlin-anchor-userstories.md` (L39, L43, L69, L134–144), then `bash
dev/pack_tools.sh`. Specs: `specs/tools/qa_report.md` RULE-3, RULE-4, RULE-5, PROOF-3;
`specs/tools/pm_anchor_userstories.md` RULE-4, PROOF-4; `specs/mcp/specs.md` PROOF-4;
`specs/anchor/upstream.md` RULE-7 wording.

**5C skill word swaps (Sonnet).** `skills/build`, `skills/spec-from-code`, `skills/anchor`,
`skills/rename` per decision 15 and A4; `specs/skills/skill_rename.md` and `skill_drift.md`
descriptions; `hooks/hooks.json` checked, unchanged.

### Phase 6: docs and design (2 lanes)

**6A rewrites (Opus).** Full rewrite: `docs/dashboard.md` (against the phase 4 screenshots),
`docs/regulated-workflow.md` (the mermaid `stateDiagram-v2` redrawn as spec status → passed →
strong → signed with the stale and code-changed edges, init block from `docs/_mermaid.md`),
`git mv docs/review-and-approval.md docs/review-and-signing.md` and rewrite. Section
rewrite: `docs/running-and-records.md` (L15, L103, L117, L180, L192, L246–264),
`docs/team-workflow.md` (L1–8, L21–24, L62, L64, L99, L115), `docs/getting-started.md`
(L50–65, L161–175), `docs/raising-the-gate-and-upgrading.md` (L12–16, L32–50, L73, L111–124,
L129–134), `docs/working-together.md` (L68–72, L136–137, the drift samples).
`RELEASE_NOTES.md`: the 0.10.0 entry overwritten to describe this model, the three commands,
and every retired word.

**6B word swaps and design (Sonnet).** `docs/solo-workflow.md`, `docs/specs-and-anchors.md`
(and L135–139), `docs/design-in-specs.md`, `docs/spec-from-code.md`, `docs/index.md` (links
to the renamed page and format); `design/readme.md` L31 and L121–124; `design/components/core/
StatusPill.jsx`, `.d.ts`, `.prompt.md`, `core.card.html`, `data/StatTile.prompt.md`,
`data/data.card.html`, `data/GroupHeader.prompt.md`, `data/DataTable.prompt.md`,
`core/Button.prompt.md`, `core/Tag.prompt.md`, `editorial/CommandChip.prompt.md`,
`editorial/editorial.card.html`, `guidelines/type-scale-ui.card.html`,
`guidelines/type-mono.card.html` to the cell words and gate values; `git rm -r
dev/screenshots/`.

### Phase 7: this repository (orchestrator, after 1–6 are merged)

1. `git rm -r` the 37 `specs/**/*.approvals/` directories and `.purlin/records/*`. Edit
   `.purlin/config.json`: `gate: signed`, `signers: ["rich.labarca@gmail.com"]`, no
   `approvers`. Commit as `chore: drop the 0.10-dev evidence`.
2. `python3 dev/build_report.py`, `python3 dev/capture_doc_screenshots.py`, `bash
   dev/pack_tools.sh`, then a full `dev/run_tests.sh` and `python3 scripts/ci/gate_check.py
   --check`. `PENDING_REWRITE` is empty; the vocabulary test is green.
3. `dev/plans/README.md` names this file. `dev/plans/TODO-0.10.0.md` and
   `dev/plans/held-rules-0.10.0.md` restated in the new words: item 1 becomes "sign the review
   list", with the count from step 2.
4. Push `three-levels`. CI's record commit is the first with briefs under `.purlin/briefs/`.
   Confirm the pull request comment prints the new table and the board artifact opens.
5. Report: the sweep result, the gate check summarised as rules `Not signed`, the vocabulary
   test result, the spec maxima, and anything left undone with why.

### After the report (user)

Sign the review list with `purlin:sign`; apply the three branch rulesets init prints; pull
request `three-levels` → `main`; tag `v0.10.0`.

## C3. Counts to expect

| What | Now | After |
|------|-----|-------|
| rule states / cells | 7 states + 1 flag | 2 spec words, 3 cells, 4 flags |
| gate values | `tested recorded approved` | `passed strong signed` |
| commands for the levels | test, verify, review + approve | test, audit, sign |
| skills | 13 | 12 |
| brief output | 4 verdicts | strength, findings, observations, settled |
| payload schema | 4 | 5 |
| record format | 1 | 2 |
| approval format 2 | `approval_format.md` | `signature_format.md` 3 |
| evidence files in `specs/` | 471 person + 137 ci + 922 brief | 0 until the user signs |
| dashboard tiles at `passed` / `strong` / `signed` | 7 + 1 | 3 / 4 / 5 + 1 |
| board columns at `passed` / `strong` / `signed` | 4 / 7 / 8 | 5 / 7 / 8 |
| specs rewritten / section / swap / deleted / untouched | | 6 / 15 / 6 / 1 / 10 |
| docs rewritten / section / swap | | 3 / 5 / 5 |
