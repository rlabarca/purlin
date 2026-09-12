<!-- Checked-in working plan. This copy is authoritative: the original lived in a
     per-user ~/.claude/plans/ directory that does not travel between machines.
     Update this file as phases complete, in the same commit as the work. -->

# Deterministic quality gate, complete Pass 1 coverage, and a canonical proof-plugin contract

## Context

`docs/regulated-environments.md` says Purlin is "not a test quality gate": an agent can write
`assert True` and produce a valid proof, the two quality gauges are advisory, and nothing reads
them as a gate. That undersells what exists. Pass 1 of `scripts/audit/static_checks.py` already
catches `assert True`, missing assertions, bare `except: pass`, logic mirroring and mocked-out
targets deterministically, grades them HOLLOW with no override, and binds each grade to the
test's source. Pass D1 grades proof descriptions the same way. Neither needs a model or a cache,
so both can be recomputed from scratch in CI and enforced by branch protection, exactly as the
existing CI gate `scripts/ci/verify_gate.py --check` is enforced today.

Three findings shaped the scope:

1. Pass 1 covers Python, JS/TS, shell and C# only. Purlin ships proof emitters for PHP, SQL and
   C too, and `.mjs`/`.cjs` are skipped by an extension oversight. The user chose to close every
   gap first, so the gate never has an "unmeasurable" category for a shipped framework.
2. Nothing says in one place what a proof plugin must do. `specs/_anchors/proof_common.md`
   (21 rules) is the de facto contract, `proofs_format.md` covers most of it and omits the run
   marker, and `docs/testing-workflow-guide.md`'s "Writing a custom plugin" mis-teaches the
   merge rule. Auditing the eight shipped plugins against the rules found four defects: the SQL
   plugin's fallback warning omits the path and the `purlin:spec` hint; the xUnit plugin's
   orphan-reaping check is cwd-relative while its paths are root-relative, so a test project
   below the repo root reaps every committed entry; SQL, PHP and C record `test_file` as given
   rather than project-relative; jest and vitest need an undeclared npm `glob` package.
3. A new config field must not disturb projects that never opt in. Any key added to
   `templates/config.json` makes every existing project report a `config-fields-missing`
   migration, and the scaffold test asserts the written key set equals the template's. So the
   field is optional, like `platforms`, read with a default.

## Decisions (binding, from the user)

| Question | Decision |
|---|---|
| Gate fails on | HOLLOW executed tests (Pass 1) and UNPROVABLE declared descriptions (Pass D1). |
| Config | `"quality_gate": "off" \| "deterministic"`, optional, not in the template. `purlin:init --quality-gate deterministic` sets it on a new or existing project; `purlin:init --update` never backfills or asks. |
| Language gaps | Closed first: `.mjs`/`.cjs` dispatch; PHP, SQL and C checkers; cache-key extractors for all three. Unmeasurable remains only for an unknown extension (a custom plugin's language) and never fails. |
| Contract | `proof_common` stays the rule-bearing anchor and gains the missing rules; a new reader-facing checklist `references/proof_plugin_contract.md` cites those rules and lists every wiring site. All eight plugins are brought up to it. |
| Enforcement | Unchanged: the field declares, branch protection on the `verify-gate` job enforces. Exactly one framework gate; this is project policy layered on it. |
| Output under `off` | The gate prints one extra line, `verify-gate: quality_gate = off`, loads no checker and computes nothing. Everything else is byte-identical to today. |
| Not in scope | A dashboard chip for the quality gate (the payload is rebuilt after every tool call by the refresh hook; a sweep there is a per-turn cost for a CI-only setting). Any change to `.github/workflows/verify-gate.yml` (it would force a consumer-fixture regeneration; the gate reads config instead). |

Spec ids: another session shares this checkout and reserves ids as it goes. Verify each
spec's maximum with `grep -o "^- RULE-[0-9]*" <spec> | sort -t- -k3 -n | tail -1` (and PROOF)
right before every commit; the ids below are the next-free values at planning time. Message
that session the maxima left and the test-count delta after each commit; no receipts, no
`verify:` commits, no push.

Order: Part A first (the contract's last rule and the gate both need the sweep), then Part B,
then Part C with Part D's docs in the same commits. Each commit runs its own test files whole
(a `-k` filtered pytest run truncates that file's proof JSON), records its mutation checks in
the body, and restores proof JSON files for features it did not change.

## Part A: complete Pass 1 and add the deterministic sweep (`scripts/audit/static_checks.py`)

1. **One extension table.** Module constants `_JS_EXTENSIONS` (`.js .jsx .mjs .cjs .ts .tsx`),
   `_C_EXTENSIONS` (`.c .h`), `_CHECKER_EXTENSIONS` (those plus `.py .sh .cs .php .sql`), and
   `_TEST_CODE_EXTENSIONS = _CHECKER_EXTENSIONS - {'.sh'}`. `analyze_test_file` dispatches from
   it; `_test_bodies` gets an explicit branch per language and `else: None` (JS is no longer a
   silent fallback). Shell keeps no extractor, so PROOF-63/64/68 (which scaffold `.sh` as the
   no-extractor language) stay valid.
2. **`check_php`.** Marker regex copied byte-for-byte from `scripts/proof/phpunit_purlin.php:56`
   (including its `(?:public\s+)?function` quirk, so the audited function is the executed one);
   body via a generalised `_read_c_like_balanced(content, i, opener, closer, line_comment_prefixes)`
   that `_read_csharp_balanced` also calls (PHP passes `('//', '#')`; heredoc/nowdoc not
   tracked, documented). `assert_true` on `assertTrue(true)`, `assertFalse(false)`,
   `assert(true)`, `assertSame/assertEquals` of two identical literals, and a constant `if`
   guard on a throw; `no_assertions` when none of `$this->assert*|fail|expectException*`,
   `self::|static::|Assert::assert*`, `assert(`, `expect(`, `throw` appears. `test_name` is
   the function name. Shared generator `_iter_php_proof_bodies` feeds both the check and the
   cache extractor (CLAUDE.md dedup).
3. **`check_sql`.** Block delimiting identical to `scripts/proof/sql_purlin.sh:80-100` (marker
   to next marker or EOF), `test_name` from `-- Test:` else the proof id. `assert_true` on an
   unconditional `SELECT 'PASS'` or a `CASE WHEN ... THEN 'PASS'` whose predicate has no
   identifier outside `and or not is null in like glob between true false escape` (so `1 = 1`
   and `'alice' = 'alice'` are flagged, `changes() = 1` and any subquery are not);
   `no_assertions` only when the executable block has no `SELECT` at all. Generator
   `_iter_sql_proof_blocks`.
4. **`check_c`.** Find `purlin_proof(` / `purlin_proof_on(` calls, read the balanced argument
   list (strings, chars, comments skipped), split on depth-0 commas, require seven or more
   arguments and a first argument equal to the feature. Only one check, documented as such:
   `assert_true` when the fourth argument (`passed`) is a constant expression (tokens only
   literals, operators, `true`, `false`, parentheses); a variable is an assertion computed
   before the call and passes. `test_name` from the fifth argument when it is a string literal.
   Cache-key body: the enclosing top-level `{...}` block (over-invalidation on any edit in
   `main`, the safe direction). Generator `_iter_c_proof_bodies`.
5. **Run-scope memo for Python parses.** `_RunCache` gains `py_parses` and a
   `_python_parse(path, content)` memo used by `_python_proof_sources` and `check_python`
   (thread `lines` into `_check_mock_target_match`, replacing its two `get_source_segment`
   calls with `_segment`). One `ast.parse` per file per scope even when a file carries two
   features; PROOF-68's counters stay at one and zero.
6. **`deterministic_sweep(project_root)`**, public, under one `run_scope()`: for every
   `specs/**/*.md` feature, `check_proof_design(spec)` for D1 levels, then every executed proof
   backing from a new `_proof_backings(project_root, feature)` (all `(test_file, test_name)`
   per proof id across the feature's proof files, deduped by `(test_file, proof_id)`;
   `_proof_records` becomes "first backing" derived from it), grouped by test file, one
   `analyze_test_file` per `(test_file, feature)` with rule descriptions, empty `.cs` test
   files resolved through `resolve_test_file_from_name`. A file outside `_CHECKER_EXTENSIONS`
   is `unmeasurable/no_checker`, a missing file `unmeasurable/missing_file`, a marker the
   checker cannot find `unmeasurable/marker_not_found`; a proof with several backings takes
   `fail` over `unmeasurable` over `pass`. Return shape:
   `{'project_root', 'features': {name: {'spec', 'design': {pid: {rule_id, level, check, reason}},
   'integrity': {pid: {rule_id, status, check, reason, test_file, test_name, backings}}}},
   'hollow': [...], 'unprovable': [...], 'unmeasurable': [...], 'counts': {...}}`, every list
   sorted by `(feature, proof_id, test_file)`. It opens nothing for writing. CLI
   `--deterministic-sweep [--project-root P]` prints the JSON; `_USAGE`, the docstring and the
   dispatch stay in step (RULE-34).
7. **Spec `specs/audit/static_checks.md`** (next free RULE-44 / PROOF-71 at planning time):
   `> Description:` names all seven languages; RULE-39 reworded ("a shell script, or a language
   without an extractor"); new rules for the shared extension table and no-fallback dispatch
   (proof: `.mjs .cjs .php .sql .c .h` fixtures each yield `assert_true`, `.rb` yields `[]` and
   `_test_bodies` returns None for it), PHP checks (three proofs: tautologies, no assertions,
   real assertion forms pass including a `#` comment containing `{`), SQL checks (three
   proofs), C constant check (two proofs, including a string argument containing `,` and `)`),
   extractors for `.php .sql .c` (edit-then-recompute proof mirroring PROOF-65), and the sweep
   (unit proof on a temp project with `.py .sh .mjs .cs .php .sql .c .rb` files and two
   features sharing one Python file, asserting statuses, the `.rb` `no_checker`, the resolved
   `.cs` path, one `ast.parse` per Python file, and a tree snapshot unchanged; e2e proof
   running `--deterministic-sweep` on this repository with `counts.features` equal to the spec
   count, no `no_checker` entry, and the repository snapshot unchanged).
8. **References and tests.** `references/audit_criteria.md` Pass 1 section gains C#-specific
   (backfill), PHP-specific, SQL-specific and C-specific subsections, the JS heading names
   `.mjs`/`.cjs`, and the sentence at :338 becomes "(shell, or a language no shipped checker
   reads)". `references/supported_frameworks.md:35` C# callout generalised to every shipped
   plugin. `dev/test_cheat_matrix.py` rows that flip from "needs LLM" to a Pass 1 catch (C and
   PHP and SQL tautologies, SQL fixture-only `'alice' = 'alice'`, C and PHP and SQL
   no-assertion rows) gain a checker assertion beside the runtime pass; `skipif`s kept.
   `dev/test_static_checks.py` gains `TestCheckPhp`, `TestCheckSql`, `TestCheckC` (each with a
   `_php/_sql/_c(body, proof_id, rule_id)` helper like `_cs`), `TestDispatchAllExtensions`,
   `TestExtractorsForPhpSqlC`, `TestDeterministicSweep`.

Risks: a false HOLLOW is a blocked merge under the gate, so every detector claims only what a
regex proves; a PHP test delegating all assertions to a helper is the one known false-positive
path (same as C#), documented. No `Format-Version` bump: markers and JSON are unchanged.

Commits: A1 `feat(static_checks)`: extension table, PHP/SQL/C checkers, extractors, criteria
and cheat-matrix flips. A2 `feat(static_checks)`: the sweep, its CLI and proofs.

## Part B: the proof-plugin contract and every plugin brought up to it

Current `proof_common` maxima RULE-21 / PROOF-27 (the other session's T3 landed RULE-20/21);
next free RULE-22 / PROOF-28. Re-verify before each commit.

- **B1 `fix(proof_common)`: SQL fallback warning.** `scripts/proof/sql_purlin.sh:224` prints the
  seven-plugin sentence (path and `purlin:spec <feature>`). PROOF-9 becomes a parametrised
  eight-plugin proof in `dev/test_multilang_proof_plugins.py` (`TestFallbackWarningPerPlugin`,
  `skipif` per toolchain); the two existing PROOF-9 tests stay.
- **B2 `feat(proof_common)`: RULE-22 project root by walk, RULE-23 project-relative
  `test_file`.** The project root is the nearest ancestor of the working directory (or the test
  file) holding `specs/` or `.purlin/`, else the working directory; the specs glob, the `specs/`
  fallback, the RULE-11 existence check and the run marker are all rooted there, so running
  from a subdirectory works. `test_file` is relativised against that root from whatever path
  the framework handed the plugin (absolute in, relative out; a file outside the root uses the
  nearest root above the file, shell's existing two-candidate rule). Edits: pytest (root helper,
  existence from root), shell (`_project_root_of` reused for cwd), jest/vitest (`findRoot`,
  `path.join(root, ...)` in the kept filter), sql and c (a `_project_root` + `_relativize` in
  their own Python, mirroring shell), php (`project_root()`/`relativize()`, guard `is_dir`,
  delete the dead glob loop), xunit (`File.Exists(Path.Combine(_root, tf))`, `FindRoot` also
  accepts `.purlin/`). PROOF-28 runs each of the eight from `<root>/sub/` with a kept sibling
  entry and asserts the file lands under `<root>/specs/`, the entry survives, and `test_file` is
  root-relative; PROOF-29 hands each plugin an absolute test path and asserts the relative
  result. PROOF-27's xUnit arm (which had the reaping defect baked in as expected behaviour) is
  amended to seed the kept entry and expect it kept. `proofs_format.md`'s orphan-reaping prose
  and `keep(e)` are rewritten to the rooted rule (the bump comes in B4). `.purlin/plugins/`
  copies of the edited plugins are synced in the same commit (PROOF-20 byte identity).
- **B3 `feat(proof_common)`: RULE-24 atomic PID-unique proof writes, RULE-25 no undeclared
  runtime dependency.** Every plugin writes `<path>.<pid>.tmp` then replaces (xUnit drops its
  delete-then-move for `File.Move(tmp, path, true)`). jest and vitest replace `globSync` with a
  `fs.readdirSync(..., {withFileTypes: true})` walk (the test drivers' `_GLOB_SHIM` is deleted
  so a reporter that re-requires `glob` fails to load). PROOF-30 greps each source for a PID
  token in the tmp expression and asserts no `*.tmp` remains after a run; PROOF-31 allow-lists
  each source's imports (node builtins plus `vitest`; Python stdlib plus `pytest`; .NET BCL plus
  the test-platform object model; PHP none) and loads jest/vitest with an empty `node_modules`.
- **B4 `docs(purlin_references)`: the contract and proofs_format Format-Version 6.** New
  `references/proof_plugin_contract.md` (no Format-Version: a checklist, not a parsed format;
  dash-free per purlin_docs RULE-11) with four sections: (A) behavioural requirements, one row
  per `proof_common` rule, citing the rule id and the two legitimate merge shapes (two-clause for
  skip-exempt plugins, four-clause for skip-capable); (B) the ordered wiring list a new language
  must touch: `supported_frameworks.md` tables, `scaffold.py` `_DETECTORS`/`_WIRING`/
  `_DEST_OVERRIDES`, `pre_push_gate.py` `KNOWN_FRAMEWORKS`, `pre-push.sh`, `skills/init/SKILL.md`,
  `skills/test/SKILL.md`, the docs framework sections, `proofs_format.md` marker section,
  `audit_criteria.md` Pass 1 subsection, `static_checks.py` dispatch table and `_test_bodies`,
  `specs/proof/proof_plugins_<x>.md`, the dev test classes, `dev/run_tests.sh`, and the spec pins
  (purlin_references RULE-3/23, skill_init RULE-48/50/64/71, pre_push_hook RULE-5, purlin_agent
  RULE-4, purlin_skills RULE-15), plus a per-framework table `framework | plugin file | test
  extensions | Pass 1 checker | extractor`; (C) the checker and extractor requirement; (D) how
  to prove a plugin (the test classes per behavioural row, the per-plugin spec template).
  `proofs_format.md` gains a `## Run marker` section (fields per RULE-19/20, merge rule, atomic
  replace): structural, so Format-Version 5 to 6, with the stale-reference grep CLAUDE.md
  requires. `docs/testing-workflow-guide.md` "Writing a custom plugin" becomes a pointer plus a
  corrected minimal sample (`kept` keeps other features and unexecuted-but-existing files);
  `supported_frameworks.md` "Adding More Frameworks" becomes a pointer; `docs/index.md`
  resources row; CLAUDE.md "Authoritative reference files" bullet; `purlin_references`
  `> Scope:` (thirteen files) and `> Description:`. New purlin_references rules: the checklist
  names every wiring site (proof parses section B and asserts each of a fixed set of existing
  paths is named); every requirement row cites an existing `proof_common` rule id; `proofs_format.md`
  carries the run-marker section naming the RULE-19 fields. New `dev/test_plugin_contract.py`
  carries these and the structural rows; `dev/run_tests.sh` gains it.
- **B5 `fix(pre_push_hook)`: `KNOWN_FRAMEWORKS` names xunit.** Keep the tuple (the hook never
  reads markdown at runtime), add `'xunit'`, amend RULE-5, and add a proof that the tuple equals
  the registry's id set.
- **B6 `spec(purlin_references)`: every registered framework has a Pass 1 checker and an
  extractor.** Lands after Part A: the proof reads the contract's per-framework table, runs
  `analyze_test_file` on a marked tautological fixture per extension and requires an
  `assert_true` result, and requires `_extract_test_code` to return a body for every extension
  but shell (documented exception).

## Part C: the gate, its config field, init and update, payload and status line

Next free ids at planning time: `verify_gate` RULE-14..17 / PROOF-14..17; `report_data` RULE-46
/ PROOF-47; `sync_status` RULE-66 / PROOF-105; `skill_init` RULE-75 / PROOF-78 plus RULE-70/
PROOF-73 and RULE-74/PROOF-77 amended.

1. **`scripts/ci/verify_gate.py`.** `QUALITY_MODES = ('off', 'deterministic')` and a
   `_QUALITY_ENFORCEMENT_NOTE` mirroring `_ENFORCEMENT_NOTE`'s three sentences for
   `quality_gate`. `_load_static_checks()` imports the checker by path like `_load_payload`.
   In `check()`: after the remote mode is validated, read `payload.get('quality_gate', 'off')`
   and exit 2 on any other value in every remote mode; after the remote mode line print
   `verify-gate: quality_gate = <mode>` (plus the note under `deterministic`); after the
   existing blocks, under `deterministic` only, run `deterministic_sweep(project_root)` and
   print a `Quality gate (deterministic): H HOLLOW, U UNPROVABLE, M unmeasurable` section with
   one line per finding (`feature: PROOF-N HOLLOW (check) test_file::test_name`,
   `feature: PROOF-N UNPROVABLE (check)`, `feature: PROOF-N unmeasurable (test_file: no
   deterministic checker for .ext)`) and the sentence that unmeasurable proofs never fail; a
   checker that cannot be loaded or a sweep that raises exits 2 naming the module. Verdict:
   `remote_fail` and `quality_fail` are independent; the existing PASS/FAIL lines are printed
   byte-for-byte when only the remote gate applies, both FAIL lines when both hold. Docstring
   gains a `QUALITY GATE` section carrying the literal `` `quality_gate` field DECLARES ``.
2. **Payload and status line (`scripts/mcp/purlin_server.py`).** `'quality_gate':
   config.get('quality_gate', 'off')` beside `remote_verification` in `_build_report_data`,
   carried verbatim (the gate is the reader that refuses a typo); `_quality_gate_line(config)`
   beside `_remote_verification_line`, appended after the remote line in `_build_summary_table`,
   empty under `off`/absent, naming the mode, what the gate fails on and the declaration/
   enforcement split under `deterministic`, and "not a recognized mode" otherwise. It never runs
   the sweep. report_data RULE-46/PROOF-47 and sync_status RULE-66/PROOF-105 as drafted by the
   design agent (verbatim carry, present-when-absent, no line for off projects).
3. **Init and update.** `scripts/init/scaffold.py`: `--quality-gate {off,deterministic}` flag,
   `'quality_gate': args.quality_gate` in the answers dict (written only when answered, kept
   under `--force`), docstring usage and "WHAT IT WRITES" / "WHAT `--force` KEEPS" lines.
   `scripts/update/migrate.py` untouched, on purpose: the field is not a template key, so it is
   neither backfilled nor listed as `config-fields-missing` nor asked. `skills/init/SKILL.md`:
   usage line, "who does what", the scaffold invocation block (PROOF-61 greps it), the
   single-step re-answer list, a config-table row after `platforms`, the Step 5d KEEPING block,
   and a "Setting the quality gate on an existing project" note (`purlin:init --quality-gate
   <mode>` runs the scaffolder with `--force --quality-gate <mode>` and nothing else).
   `specs/skills/skill_init.md`: RULE-70/PROOF-73 and RULE-74/PROOF-77 gain the flag; new
   RULE-75/PROOF-78 (written only when answered, absent otherwise with the key set equal to the
   template's, kept under `--force`, invalid value exits 2, `migrate.py --check` names no pending
   entry for it). `references/drift_criteria.md` gains the row and the "six optional fields"
   sentence; purlin_references RULE-20/PROOF-20 and the test's `optional` set gain the name.
   `docs/installation-guide.md`: "Three further fields are optional" and a `quality_gate`
   paragraph.
4. **verify_gate spec.** RULE-14 (mode read from the payload, closed set, fail closed, `off`
   prints one line and computes nothing), RULE-15 (the section, the independent verdicts,
   unmeasurable never fails, no cache read, exit 2 when the checker is unloadable), RULE-16
   (declaration/enforcement wording in output and header; exactly one `## Gate N` in
   `hard_gates.md`), RULE-17 (RULE-5 holds under `deterministic`: no cache written, no
   `.purlin/cache/` created). PROOF-14..17 as drafted, with a `.rb` proof as the unmeasurable
   case (PHP is graded after Part A) and PROOF-5 amended to snapshot under `deterministic` too.

Commits: C1 `feat(verify_gate,report_data,sync_status)`: gate, payload, status line, their
specs and tests. C2 `feat(skill_init)`: flag, SKILL.md, spec, drift row, installation guide.

## Part D: the docs that currently say nothing reads the gauges as a gate

Landed with C1. Exact sentences are in the design notes; the constraints that matter:

- `docs/regulated-environments.md` bullet becomes `- **Not a test quality gate by default.**`
  (keeps the `- **Not ` shape purlin_docs RULE-1 keys on) with the honest split: the
  deterministic halves prove the absence of a fixed defect list and bind grades to test source;
  the LLM halves are judgment; advisory in the framework; `quality_gate: "deterministic"` makes
  the deterministic half an exit 1 from the gate with branch protection as the enforcement;
  human review stays for the judgment half. The vhash "not bound" row gets the same nuance.
  "Policy lives outside the repo" names both fields. New `### The deterministic quality gate`
  subsection under "How a Regulated Pipeline Would Use Purlin" (at least one backticked
  `scripts/` path, no approval phrases). `quality_gate` joins purlin_docs RULE-9's closed field
  set and `CONFIG_FIELDS` in `dev/test_purlin_docs.py`.
- `references/hard_gates.md`: the "What Is NOT a Gate" bullet keeps `Proof Design`,
  `Proof Integrity` and "advisory by default" and adds the opt-in sentence (purlin_references
  RULE-17 amended to "never blocks unless the project declares `quality_gate`"; PROOF-17's split
  on `What Is NOT a Gate` and `exactly 1 hard gate` regex still hold); Layer 3 row keeps
  `verify_gate.py`, `branch protection`, `remote_verification` and adds `quality_gate` (five
  rows unchanged); "Project Policy Is Not a Framework Gate" names both fields.
- `README.md` Hard Gate paragraph: "neither quality gauge is a gate by default" plus the opt-in
  sentence. `docs/testing-workflow-guide.md` gate sentence and a trigger-table row.
  `references/remote_verification.md` mode section cross-reference. `docs/lifecycle-guide.md:33`
  "neither is a gate by default". `references/audit_criteria.md:12` and `skills/audit/SKILL.md:28`
  "Neither gauge is a gate by default". No em or en dashes in any of these (purlin_docs RULE-11).

## Backward compatibility (what stays byte-identical)

- Existing gate fixtures lack the field: every run gains one line, `verify-gate: quality_gate =
  off`, and nothing else; PROOF-3's membership checks, PROOF-6's literals, PROOF-9's
  `'PASS' not in out` under exit 2, PROOF-12's two-space filter and PROOF-13's exact lines hold.
- The workflow and the consumer fixture do not change; the fixture config lacks the field.
- `sync_status` output is unchanged for projects without the field; the summary line is
  untouched; PROOF-81 matches `Remote verification:` only.
- A default `purlin:init` still writes exactly the eight template keys (PROOF-9 e2e, PROOF-65);
  `--force` keeps unanswered keys (PROOF-64); `purlin:init --update` reports no new migration.
- Dashboard JS ignores an unknown top-level payload key; `report-data.js` gains
  `"quality_gate": "off"` on its next refresh.
- This repository does not turn the gate on in this work. Running the sweep here first and
  reading 0 HOLLOW / 0 UNPROVABLE is a separate decision.

## Verification

1. Part A: `python3 -m pytest dev/test_static_checks.py dev/test_cheat_matrix.py -q` (rows
   skip without gcc, php, sqlite3, tsc; this host has gcc, php, sqlite3, node, dotnet);
   `python3 scripts/audit/static_checks.py --deterministic-sweep --project-root .` prints counts
   with no `no_checker` entry and `git status --porcelain` is unchanged afterwards; the bare
   CLI exits 2 with `--deterministic-sweep` in `_USAGE`.
2. Part B: `python3 -m pytest dev/test_multilang_proof_plugins.py dev/test_plugin_contract.py
   dev/test_proof_plugins_missing.py -q`, `bash dev/test_proof_plugins.sh`,
   `dev/test_purlin_references.py`, `dev/test_pre_push_hook.py`; each plugin run from a
   subdirectory of a temp project writes under `<root>/specs/` with relative `test_file`.
3. Part C and D: `python3 -m pytest dev/test_verify_gate.py dev/test_report_data.py
   dev/test_mcp_server.py dev/test_init_scaffold.py dev/test_init_update.py
   dev/test_purlin_docs.py dev/test_purlin_references.py dev/test_consumer_ci.py
   dev/test_skill_specs.py -q`; `bash dev/test_init_e2e.sh`; `scripts/init/scaffold.py --help
   | grep quality-gate`; `python3 scripts/ci/verify_gate.py --check --project-root .` before
   and after a temporary `"quality_gate": "deterministic"` (reverted): today's output plus one
   line, then the section.
4. Mutations recorded per commit: a `require("glob")` restored fails PROOF-31; xUnit's
   `File.Exists(tf)` restored fails PROOF-28's xUnit arm; SQL's short warning restored fails
   PROOF-9's SQL arm; a wiring path dropped from the checklist fails its proof; a
   `setInterval`-style shortcut is not applicable here, but a `'PASS'` line printed before the
   quality check fails PROOF-14; a `_TEST_CODE_EXTENSIONS` entry removed fails the extractor
   proof; `.mjs` removed from the table fails the dispatch proof.
5. Full sweep `bash dev/run_tests.sh` before handing the tree to the closeout session for
   receipts and the `verify:` commit.

## DONE

### B1

`fix(proof_common): the SQL plugin's no-spec warning names the path and the purlin:spec hint like the other seven`

Files touched:

- `scripts/proof/sql_purlin.sh` (one line: the RULE-9 warning, now byte-identical in wording to `shell_purlin.sh`'s)
- `dev/test_multilang_proof_plugins.py` (`TestFallbackWarningPerPlugin`, eight `_warn_*` drivers, `_warn_project`; `TestTypeScriptProofPlugin._drive_reporter` now returns its `CompletedProcess` so the vitest arm can read stderr)
- `specs/_anchors/proof_common.md` (PROOF-9 amended)
- `specs/_anchors/proof_common.proofs-integration.json` (8 new PROOF-9 entries)

Maxima left in `specs/_anchors/proof_common.md`: RULE-21 / PROOF-27, unchanged. PROOF-9 was
amended in place, not added; no new RULE id.

Test counts, `dev/test_multilang_proof_plugins.py` run whole:

- before: 71 passed, 0 skipped
- after: 79 passed, 0 skipped (+8, one parametrised arm per plugin)
- `bash dev/test_proof_plugins.sh`: 28/28 before and after; it never drives the SQL plugin.

Mutation: the short warning (`print(f'WARNING: No spec found for feature \"{feature}\"', ...)`)
put back at `sql_purlin.sh:224`. 1 failed, 78 passed, on the `[sql]` arm with
AssertionError: "sql must name the `purlin:spec` command that creates the missing
spec:", with the one-clause warning printed under it. Restored; 79 passed.

Adjacent defect found, not fixed: this host's `dotnet` on PATH is 10.0.400 and ships only the
10.0.11 runtime, while `_LOGGER_CSPROJ` and `_TEST_CSPROJ` target `net8.0`. Every xUnit case in
`dev/test_multilang_proof_plugins.py` (6 failures, 6 collection errors) therefore fails on the
bare PATH. `/opt/homebrew/opt/dotnet@8/bin` is installed and carries 8.0.31, so every run
recorded above was made with that directory prepended to PATH and the file is green there,
at HEAD as well as after this commit. Nothing in the repository pins the runtime; a consumer
or CI host with only .NET 10 sees the same failures.

### A1

`feat(static_checks): Pass 1 checkers for PHP, SQL and C, .mjs/.cjs dispatch, and cache-key
extractors for all three`

Files touched:

- `scripts/audit/static_checks.py` — extension table, `check_php`, `check_sql`, `check_c`, the
  shared `_read_c_like_balanced`/`_skip_c_like_noncode`/`_strip_c_like_comments` scanners, the
  `_python_parse` run-scope memo, `_test_bodies` branches
- `specs/audit/static_checks.md` — RULE-44 to RULE-48, PROOF-71 to PROOF-81, amended RULE-42 and
  `> Description:`
- `specs/audit/static_checks.proofs-unit.json` — 11 new entries (97 to 108)
- `dev/test_static_checks.py` — `TestCheckPhp`, `TestCheckSql`, `TestCheckC`,
  `TestDispatchAllExtensions`, `TestExtractorsForPhpSqlC`, one new `TestRunScope` proof,
  `_scaffold_proof(write_test=False)`
- `dev/test_cheat_matrix.py` — `_assert_pass1_catches` beside the runtime pass on the seven rows
  that flipped from "needs LLM" to a Pass 1 catch
- `references/audit_criteria.md` — Criteria-Version 20: C#, PHP, SQL and C Pass 1 subsections,
  `.mjs`/`.cjs` named in the JS heading, the no-extractor sentence generalised
- `references/supported_frameworks.md` — the C# Pass 1 callout generalised to every shipped plugin

Spec maxima left: `specs/audit/static_checks.md` RULE-48 / PROOF-81. No other spec touched.

Test counts (whole files): `dev/test_static_checks.py` 91 passed, 0 skipped to 102 passed, 0
skipped. `dev/test_cheat_matrix.py` 20 passed, 5 skipped to 20 passed, 5 skipped (the five skips
are the `tsc` rows; the flipped rows gained assertions, not tests).

Mutations run on `scripts/audit/static_checks.py`, `dev/test_static_checks.py` run whole each
time, restored after each:

1. `.mjs` dropped from `_JS_EXTENSIONS`. PROOF-71 failed with
   `AssertionError: .mjs: dispatch produced []`.
2. `_TEST_CODE_EXTENSIONS` narrowed to `_CHECKER_EXTENSIONS - {'.sh', '.php'}`. PROOF-80 failed
   with `AssertionError: .php: no test code entered the key - there is no extractor` (PROOF-71's
   derived-set assertion failed too).
3. `_php_constant_guard` disabled in `_php_tautology`. PROOF-72 failed with
   `AssertionError: constant if guard: not flagged - {... 'status': 'pass' ...}`.
4. The `_SQL_PLAIN_PASS_RE` candidates dropped in `_sql_tautology`. PROOF-75 failed with
   `AssertionError: bare: not flagged - {... 'status': 'pass' ...}`.
5. The `_is_constant_expression` test disabled in `check_c`. PROOF-78 failed with
   `AssertionError: 1: not flagged - {... 'status': 'pass' ...}`.
6. `#` dropped from `_PHP_LINE_COMMENTS`. PROOF-73 failed with
   `AssertionError: {'proof_id': 'PROOF-1', ... 'test_name': 'test_no_assert', 'status': 'pass'}`.

Decisions taken beyond the plan:

- Comments are stripped from a PHP body and a SQL block before either check runs. Without it the
  cheat matrix's own PHP no-assertion fixture passes on the word `throw` inside `// No throw =
  pass.`, and a trailing `-- ... SELECT 'PASS'` comment reads as an unconditional pass. Both were
  false verdicts in the dangerous direction.
- Only the first `'PASS'` producer in a SQL block is judged, because sqlite3 prints rows in
  statement order and the plugin reads the first line, so a later unconditional `SELECT 'PASS'`
  cannot rescue a block whose first check printed FAIL.
- `_read_c_like_balanced` takes `verbatim_strings` as well as `line_comment_prefixes`. PHP's `@`
  is the error-suppression operator, so reading `@"..."` as a C# verbatim string there would
  mis-scan a body and could produce a false `no_assertions`.
- `check_shell` and `check_js` gained an ignored `rule_descs=None` so every checker in the
  dispatch table has one signature.
- RULE-39 was left as written: it carries no language list to reword (the "shell, SQL, PHP, C"
  list the plan meant is `audit_criteria.md`'s cache-key sentence, which was reworded).
- `references/audit_criteria.md` Criteria-Version 19 to 20. It documents new deterministic checks,
  which is a substantive criteria change; the version does not enter any cache key.

Deferrals and adjacent findings:

- `check_csharp` reads its bodies raw, so a C# comment naming `Assert.True(true)` is a false
  HOLLOW and one naming an assertion hides a real `no_assertions`. The fix is one call to the new
  `_strip_c_like_comments` in `check_csharp`, but it changes behaviour RULE-31's proofs pin and
  belongs with a C# commit, not this one.
- PHP heredoc/nowdoc and C# raw string literals are not tracked by the shared scanner, so an
  unbalanced brace inside one ends the scanned body early. Documented on
  `_skip_c_like_noncode`; a body can only come out shorter than the author wrote it.
- `dev/test_multilang_proof_plugins.py` fails 6 and errors 6 on this host, all `TestXUnit*`, on a
  clean `git stash` of this work as well. A pre-existing `dotnet` toolchain problem, not this
  commit's.

### B2

`feat(proof_common): every plugin finds the project root by walk and records test_file project-relative`

Files touched:

- `scripts/proof/pytest_purlin.py`, `shell_purlin.sh`, `jest_purlin.js`, `vitest_purlin.ts`,
  `sql_purlin.sh`, `c_purlin_emit.py`, `phpunit_purlin.php`, `xunit_purlin.cs` (all eight)
- `.purlin/plugins/pytest_purlin.py`, `jest_purlin.js`, `vitest_purlin.ts`, `purlin-proof.sh`
  (the four synced copies, PROOF-20 byte identity)
- `specs/_anchors/proof_common.md` (RULE-22, RULE-23, PROOF-28, PROOF-29; PROOF-27's xUnit
  sentence amended; `> Description:` and one "What it does" paragraph)
- `specs/proof/proof_plugins_pytest.md`, `specs/proof/proof_plugins_jest.md` (RULE-3 and
  PROOF-3 named pytest's `rootdir` and jest's `rootDir` as the base; both now name the
  project root and cite proof_common RULE-23)
- `dev/test_multilang_proof_plugins.py` (`TestProjectRootFoundByWalking`,
  `TestTestFileIsProjectRelative`, eight `_rooted_*` drivers, `_ROOTED_ARMS`; `_GLOB_SHIM`
  honours `{cwd}` like the real glob; PROOF-27's xUnit arm seeded, `_ORDINAL_IDS_NO_KEPT` and
  `_two_runs(seed=)` deleted)
- `references/formats/proofs_format.md` (orphan-reaping prose and the `keep(e)` sample rooted;
  no Format-Version bump, B4 owns that)
- `specs/_anchors/proof_common.proofs-integration.json` (16 new entries, 8 per new proof)

Maxima left: `specs/_anchors/proof_common.md` RULE-23 / PROOF-29.
`specs/proof/proof_plugins_pytest.md` RULE-4 / PROOF-4 and
`specs/proof/proof_plugins_jest.md` RULE-4 / PROOF-5, both unchanged (rules amended in
place, no new ids).

Test counts:

- `dev/test_multilang_proof_plugins.py` run whole: 79 passed before, 95 after (+16, one arm
  per plugin for each of PROOF-28 and PROOF-29), 0 skipped either way
- `dev/test_proof_plugins_missing.py`: 31 passed before and after
- `bash dev/test_proof_plugins.sh`: 28/28 before and after
- `bash dev/test_proof_pytest.sh`, `dev/test_proof_jest.sh`, `dev/test_proof_shell.sh`:
  5 passed / 0 failed each, before and after
- `python3 -m pytest dev/test_init_scaffold.py -q`: 15 passed before and after
- `python3 -m pytest dev/test_pre_push_hook.py -q` (the repository's own pytest plugin,
  driven the way the sweep drives it): 27 passed, and its committed proof JSON files came
  back byte-identical, so the rooted writer records the same paths from the repo root

Mutations, `dev/test_multilang_proof_plugins.py` run whole each time:

1. xUnit's existence check put back to the cwd-relative `File.Exists(tf)`. 2 failed, 93
   passed: PROOF-28's xUnit arm with "AssertionError: xunit must write its own entry beside
   the one the RULE-4 merge keeps; got [{... 'id': 'PROOF-1' ...}]" (the kept `PROOF-11` entry
   reaped), and PROOF-27's now-seeded xUnit arm with "AssertionError: xunit_purlin must write
   entries in ordinal (id, test_file, test_name) order ['PROOF-1', 'PROOF-10', 'PROOF-11',
   'PROOF-2'], got ['PROOF-1', 'PROOF-10', 'PROOF-2']".
2. The SQL harness's relativization removed (`recorded_file` back to the path as given).
   2 failed, 93 passed: PROOF-29's sql arm with "AssertionError: sql was handed the absolute
   path '/private/var/.../proj/feat.sql' and must record it relative to the project root as
   'feat.sql'; got '/private/var/.../proj/feat.sql'", and PROOF-28's sql arm with
   "AssertionError: sql must record test_file relative to the project root, so the
   subdirectory is part of the path: expected 'sub/feat.sql', got 'feat.sql'".

Restored after each; 126 passed across the two pytest files.

Decisions:

- RULE-22's walk starts at the working directory, except for jest, which is handed
  `globalConfig.rootDir` and walks from there. Starting jest at `process.cwd()` broke
  `dev/test_proof_plugins.sh`'s three jest cases, which construct the reporter from the
  repository root and `process.chdir` into the temp project only before `onRunComplete`;
  `rootDir` is also the firmer statement of where a jest run lives. The rule says so
  explicitly rather than leaving it to the implementation.
- The shell harness's `_project_root_of` no longer accepts `.git` as a root marker, so all
  eight plugins recognise a root by the same two directories. A git repository that is not a
  Purlin project is not a root, and every Purlin project has `.purlin/`.
- RULE-23's outside-the-root clause (measure from the nearest root above the file, leave it
  absolute when there is none, never write `../`) is implemented in all eight rather than in
  the shell harness alone, so one `relativize` shape reads the same in every language.

Deferral: the `require("glob")` shims in `dev/test_multilang_proof_plugins.py` and
`dev/test_proof_plugins_missing.py` are still two copies of the same stand-in. B3 deletes
both when jest and vitest stop depending on `glob`, so they were not consolidated here.

### A2

`feat(static_checks): deterministic_sweep grades every proof backing in a project without a
model or a cache`

Files touched:

- `scripts/audit/static_checks.py` — `_proof_backings` (every executed backing, deduplicated by
  `(test_file, proof_id)`), `_proof_records` re-derived from it as "first backing",
  `_RunCache.proof_backings` replacing `proof_records`, `_SWEEP_STATUS_RANK`,
  `_sweep_unmeasurable_reason`, `_sweep_file_verdicts`, `deterministic_sweep`, the
  `--deterministic-sweep` dispatch, one new `_USAGE` line, the module docstring
- `specs/audit/static_checks.md` — RULE-49, RULE-50, PROOF-82, PROOF-83, `> Description:`
- `specs/audit/static_checks.proofs-unit.json` — PROOF-82
- `specs/audit/static_checks.proofs-e2e.json` — PROOF-83
- `dev/test_static_checks.py` — `TestDeterministicSweep`, module-level `_tree_snapshot`,
  `hashlib` import
- `references/audit_criteria.md` — a `### The deterministic sweep` subsection under Pass 1

Spec maxima left: `specs/audit/static_checks.md` RULE-50 / PROOF-83. No other spec touched.

Test counts (whole files): `dev/test_static_checks.py` 102 passed, 0 skipped to 104 passed, 0
skipped. Run green and unchanged in count: `dev/test_purlin_references.py`,
`dev/test_skill_specs.py`, `dev/test_cheat_matrix.py`, `dev/test_e2e_audit_cache_pipeline.py`,
`dev/test_purlin_docs.py`, `dev/test_schema_spec_format.py`, `dev/test_schema_proof_format.py`
(272 passed, 5 skipped together; none of their proof JSONs changed).

Sweep over this worktree, `python3 scripts/audit/static_checks.py --deterministic-sweep
--project-root .`: 46 features, 831 declared proofs, 826 executed, 914 backings, 720 pass,
82 hollow, 0 unprovable, 24 unmeasurable, no `no_checker` row. `git status --porcelain` is
identical before and after, and the bare CLI exits 2 printing the new usage line.

Mutations run on `scripts/audit/static_checks.py`, `dev/test_static_checks.py` run whole each
time, restored after each:

1. A `no_checker` backing counted as `pass`. PROOF-82 failed with
   `AssertionError: assert got == self._EXPECTED`, differing items
   `{('mixed', 'PROOF-1'): ('pass', 'no_checker')} != {('mixed', 'PROOF-1'): ('unmeasurable',
   'no_checker')}` and the same for `rbfeat`.
2. `_SWEEP_STATUS_RANK` inverted to `{'pass': 0, 'unmeasurable': 2, 'fail': 1}`. PROOF-82 failed
   with `{('worst', 'PROOF-1'): ('unmeasurable', 'no_checker')} != {('worst', 'PROOF-1'):
   ('fail', 'assert_true')}`.
3. `clear_audit_cache(project_root)` called at the top of the sweep, a cache write re-enabled.
   PROOF-82 failed with `AssertionError: the sweep wrote to the project it was only supposed to
   read`, naming `.purlin/cache/audit_cache.json` and `.purlin/cache/audit_cache.json.lock`;
   PROOF-83 failed with `AssertionError: the sweep wrote under .purlin/ (a cache or a runtime
   file)`.

Decisions taken:

- A proof stamped `@manual(...)` enters `design` only. It has no test backing, so it is neither
  hollow nor unmeasurable: calling a human stamp unmeasurable would park every manual proof in a
  gate's could-not-measure column forever, and calling it measured would claim a machine checked
  it. PROOF-82 pins it.
- An anchor under `specs/_anchors/` is swept like any other feature. Its proofs execute as real
  tests and its proof files sit beside every other one, so excluding it would leave the
  cross-cutting constraints ungraded. No code branch was needed; the `specs/**/*.md` glob already
  reaches them, and the repository sweep grades `proof_common` today.
- `backings` in an integrity entry is a count, not a list, and `test_file`/`test_name` name the
  backing whose verdict was taken. The full list is reconstructible from the proof JSONs, and a
  gate line wants one path.
- Mutation 2 did not fail on the first attempt: the fixture had a pass-plus-fail proof and a
  pass-plus-unmeasurable proof but no fail-plus-unmeasurable one, so inverting those two ranks
  was unobservable. A `worst` feature was added (an `assert True` Python test plus a `.rb` file
  that sorts ahead of it) before the mutation was recorded.
- `references/audit_criteria.md` keeps Criteria-Version 20. The new subsection documents a tool
  that recomputes existing criteria; it adds no criterion and changes no grade, so a consumer
  who pinned team criteria against version 20 is not grading against a different standard.

Deferrals and adjacent findings:

- `_check_logic_mirroring` reads any top-level `x = f(...)` assignment and flags an assert that
  calls `f` again, so a before/after invariance test (`before = snapshot(root)` ... `assert
  snapshot(root) == before`) is a false HOLLOW. PROOF-83 hit it and was restructured to unpack
  the snapshot into two names and assert the halves separately, which is a better test anyway
  (it says whether a tracked file or a `.purlin/` file moved). Three of this spec's own proofs
  (PROOF-12, PROOF-28, PROOF-33) are hollow for the same reason at HEAD. Fixing the checker is a
  behaviour change RULE-4's proofs pin and belongs with a Pass 1 commit.
- This repository's own sweep reads 82 HOLLOW and 24 unmeasurable, so turning the gate on here
  is a separate decision with work behind it, exactly as the plan's compatibility section says.
  The 24 unmeasurable are all `marker_not_found` in `dev/test_proof_plugins.sh`, whose
  `purlin_proof` calls are built from shell variables rather than the literal four-argument form
  `check_shell` matches.

### C2

`feat(skill_init): purlin:init --quality-gate sets the optional quality_gate field and nothing else`

Files touched:

- `scripts/init/scaffold.py` (`--quality-gate {off,deterministic}` with no default, the answers
  entry, the usage line, the "WHAT IT WRITES" and "WHAT `--force` KEEPS" paragraphs)
- `skills/init/SKILL.md` (usage line, "Who does what", the Step 2 invocation block, the
  Single-step re-answers list, a **Setting the quality gate on an existing project** note, the
  config-table heading and a `quality_gate` row after `platforms`, the Step 5d KEEPING block)
- `specs/skills/skill_init.md` (RULE-70/PROOF-73 and RULE-74/PROOF-77 amended; new
  RULE-75/PROOF-78)
- `dev/test_init_scaffold.py` (`TestQualityGate`; PROOF-73's seventh case, PROOF-77's fifth
  case, PROOF-61's invocation gains `--quality-gate off`)
- `references/drift_criteria.md` (the `quality_gate` ownership row, the "six optional fields"
  sentence)
- `specs/instructions/purlin_references.md` (RULE-20 and PROOF-20 name the sixth optional field;
  no new id taken)
- `dev/test_purlin_references.py` (PROOF-20's `optional` set)
- `docs/installation-guide.md` ("Three further fields are optional", a `quality_gate` paragraph)
- `specs/skills/skill_init.proofs-integration.json` (one new entry)

`scripts/update/migrate.py` and `templates/config.json` are untouched on purpose: the field is
not a template key, so `_config_field_gaps` never lists it and `_ASKED_CONFIG_FIELDS` never asks.

Maxima left: `specs/skills/skill_init.md` RULE-75 / PROOF-78;
`specs/instructions/purlin_references.md` RULE-29 / PROOF-29 (unchanged, no id taken).

Test counts (before -> after, whole files):

- `dev/test_init_scaffold.py` 15 -> 16 passed, 0 skipped
- `dev/test_init_update.py` 10 -> 10 passed
- `dev/test_skill_specs.py` 141 -> 141 passed
- `dev/test_purlin_references.py` 29 -> 29 passed
- `dev/test_purlin_docs.py` 16 -> 16 passed
- `bash dev/test_init_e2e.sh` 34 passed, 0 failed, 0 skipped (unchanged)

Mutations, both on `scripts/init/scaffold.py`, `dev/test_init_scaffold.py` run whole each time:

1. `_config` gained `config.setdefault('quality_gate', answers.get('quality_gate'))`, so an
   unanswered run writes the key as null. Failed 2/16, PROOF-78 with "AssertionError: an
   unanswered run must write exactly the template's keys; added ['quality_gate'], missing []"
   (PROOF-65 failed too, on the template key set).
2. `--force`'s base dropped the key: `base = {k: v for k, v in existing.items() if k !=
   'quality_gate'}`. Failed 1/16, PROOF-78 with "AssertionError: --force without --quality-gate
   dropped the recorded mode: None".

Restored after each; 16 passed, and the whole set ran 212 passed.

Decisions taken beyond the plan:

- PROOF-61's hardcoded invocation gained `--quality-gate off`. Its description says every flag
  the skill names is run against a real repo, and the Step 2 block now names this one, so leaving
  the run alone would have made the proof's second half untrue.
- The Step 2 note tells the agent NOT to ask about the quality gate during a full init and not to
  pass the flag unless the user asked. The decision table says a full init never writes it; a
  skill that offered the question would make the absent key an answer.
- "Two further fields are optional" in `docs/installation-guide.md` became "Three", keeping the
  sentence's own counting (`platforms`, the `audit_llm`/`audit_criteria` pair, `quality_gate`),
  and "`purlin:init` never writes them" became "a full `purlin:init` never writes them", which
  is what is true now that a flag writes one of them.

Deferrals and adjacent findings:

- `references/hard_gates.md` is cited by the new SKILL.md config row and `docs/regulated-
  environments.md` by the installation-guide paragraph; C1 owns both files and adds the sections
  those citations point at.

### B3

`feat(proof_common): every plugin writes through a PID-unique temp file and needs no undeclared runtime dependency`

Files touched:

- `scripts/proof/pytest_purlin.py`, `shell_purlin.sh`, `jest_purlin.js`, `vitest_purlin.ts`,
  `sql_purlin.sh`, `c_purlin_emit.py`, `phpunit_purlin.php`, `xunit_purlin.cs` (all eight:
  the proof-file temp name now carries the process id, as the RULE-19 marker name already
  did; xUnit's delete-then-move became one `File.Move(tmp, path, true)`; jest and vitest
  dropped `require("glob")`/`import { globSync }` for a `findSpecFiles(root)` walk over
  `fs.readdirSync(..., {withFileTypes: true})`)
- `.purlin/plugins/pytest_purlin.py`, `jest_purlin.js`, `vitest_purlin.ts`, `purlin-proof.sh`
  (the four synced copies, PROOF-20 byte identity)
- `specs/_anchors/proof_common.md` (RULE-24, RULE-25, PROOF-30, PROOF-31; `> Description:`
  and one new "What it does" paragraph)
- `dev/test_multilang_proof_plugins.py` (`TestTempNameCarriesTheProcessId`,
  `TestNoTempFileSurvivesARun`, `TestNoUndeclaredRuntimeDependency`, `_PLUGIN_SOURCES`,
  `_PID_EXPRESSIONS`, `_source_lines`, `_NODE_BUILTINS` and the import extractors;
  `_GLOB_SHIM` and its seven uses deleted)
- `dev/test_proof_plugins_missing.py` (the `Module._load` glob mock in `_jest_run_in_process`
  deleted), `dev/test_proof_plugins.sh` (three inline mocks), `dev/test_proof_jest.sh` (five),
  `dev/test_init_e2e.sh` (two): every driver now loads the reporter as shipped, so a reporter
  that re-acquires an npm dependency fails to load in all five
- `references/formats/proofs_format.md` (one paragraph on the PID-unique temp file and the
  single replace; no Format-Version bump, B4 owns that)
- `specs/_anchors/proof_common.proofs-integration.json` (27 new entries, no deletions)

Maxima left: `specs/_anchors/proof_common.md` RULE-25 / PROOF-31. No other spec touched.

Test counts:

- `dev/test_multilang_proof_plugins.py` run whole: 95 passed before, 122 after (+27:
  PROOF-30 contributes 8 source arms, the xUnit single-move case and 8 run arms; PROOF-31
  contributes 4 Python source arms, 2 node source arms, the xUnit and PHP cases and the two
  empty-`node_modules` load cases), 0 skipped either way with
  `/opt/homebrew/opt/dotnet@8/bin` first on PATH
- `dev/test_proof_plugins_missing.py`: 31 passed before and after
- `dev/test_init_scaffold.py`: 15 passed before and after
- `bash dev/test_proof_plugins.sh`: 28/28 before and after
- `bash dev/test_proof_jest.sh`, `dev/test_proof_pytest.sh`, `dev/test_proof_shell.sh`:
  5 passed / 0 failed each, before and after
- `bash dev/test_init_e2e.sh`: 34 passed / 0 failed / 0 skipped, before and after
- `dev/test_purlin_references.py`, `test_sweep_completeness.py`, `test_skill_specs.py`,
  `test_proof_stress.py` together: 188 passed, 1 skipped, unchanged

Mutations, `dev/test_multilang_proof_plugins.py` run whole each time, restored after each:

1. `const { globSync } = require("glob");` put back in `scripts/proof/jest_purlin.js`.
   14 failed, 108 passed. PROOF-31's two jest arms read
   "AssertionError: jest: jest_purlin.js imports ['glob'], which node does not ship. An npm
   package the reporter alone needs makes every consumer project install it before its proofs
   can be collected." and "AssertionError: the jest reporter must load in a project whose
   node_modules is empty: ... Error: Cannot find module 'glob'". The other twelve are every
   other jest arm in the file, which is the point of deleting the shims: with no stand-in on
   disk the reporter no longer loads at all.
2. `getmypid()` dropped from `phpunit_purlin.php`'s proof-file temp name. 1 failed, 121
   passed, with "AssertionError: php: phpunit_purlin.php:362 builds a temp name without the
   process id 'getmypid()', so two plugins writing this file at once share one temp path and
   one truncates the other's write: \"$tmp = $path . '.tmp';\"".

Decisions:

- PROOF-30's source arm reads every non-comment line carrying `.tmp`, not only the proof-file
  write, so the RULE-19 marker write is covered by the same arm and a third write site added
  later cannot slip in without the process id.
- The run arm looks for leftovers under `specs/` and `.purlin/runtime/` only. A .NET build
  drops its own temp files under `obj/`, and RULE-24 governs what the plugin writes, not what
  the toolchain does around it.
- `_NODE_BUILTINS` is a literal set rather than `node -p "require('module').builtinModules"`,
  so PROOF-31's source half needs no node and runs on every host. The two load arms are the
  ones that skip.
- The empty-`node_modules` arms create the directory and leave it empty rather than writing a
  `package.json`: an empty `node_modules` is what node's resolver actually meets in a project
  that installed nothing, and it is the shape a stale shim would be caught by.
- `dev/test_proof_jest.sh`'s five mocks and `dev/test_init_e2e.sh`'s two were removed as well
  as the three the plan named, and `dev/test_proof_plugins_missing.py`'s stayed a deletion
  rather than a consolidation (B2's deferral): with the reporters free of npm dependencies
  there is nothing left to share.

Deferrals and adjacent findings:

- `dev/fixtures/consumer-ci/.purlin/plugins/pytest_purlin.py` is a checked-in fixture copy of
  an older pytest plugin (it still globs `specs/**/*.md` from the working directory, pre
  RULE-22). It is a frozen consumer fixture, not a shipped plugin, so it was left alone; a
  commit that regenerates the consumer fixture should refresh it.
- `docs/testing-workflow-guide.md`'s "Writing a custom plugin" sample still writes its proof
  file without a temp file at all. B4 rewrites that section and is the right place to make the
  sample show the RULE-24 write.

### B5

`fix(pre_push_hook): KNOWN_FRAMEWORKS names xunit, and a proof pins the tuple to the framework registry`

Files touched:

- `scripts/hooks/pre_push_gate.py` (`KNOWN_FRAMEWORKS` gains `'xunit'`; the comment above it now
  names the registry and both of its plugin tables as the source of the ids)
- `specs/hooks/pre_push_hook.md` (RULE-5 amended, PROOF-31 added)
- `dev/test_pre_push_hook.py` (`_gate_module`, `_registry_framework_ids`,
  `TestRule5FrameworkDetection.test_known_frameworks_equals_the_registry_id_set`)
- `specs/hooks/pre_push_hook.proofs-integration.json` (1 new PROOF-31 entry)

Maxima left in `specs/hooks/pre_push_hook.md`: RULE-16 / PROOF-31. No new RULE id; RULE-5 was
amended in place.

Test counts, `dev/test_pre_push_hook.py` run whole:

- before: 27 passed, 0 skipped
- after: 28 passed, 0 skipped (+1)

Mutations, both restored, the file run whole each time:

1. `'xunit'` removed from `KNOWN_FRAMEWORKS`. 1 failed, 27 passed, with
   "AssertionError: KNOWN_FRAMEWORKS in scripts/hooks/pre_push_gate.py must equal the id set of
   references/supported_frameworks.md; tuple has ['c', 'jest', 'php', 'pytest', 'shell', 'sql',
   'vitest'], registry has ['c', 'jest', 'php', 'pytest', 'shell', 'sql', 'vitest', 'xunit']".
2. The `| **xUnit** |` row deleted from the Additional Plugins table of
   `references/supported_frameworks.md`, the tuple left correct. Same 1 failed, 27 passed, the
   two sides swapped ("Extra items in the left set: 'xunit'"), so the proof reads the registry
   rather than a second hardcoded list.

Decisions:

- The registry source is `references/supported_frameworks.md`, not `scaffold.py`'s `_DETECTORS`:
  `_DETECTORS` lists six ids (no shell, which has no detection heuristic, and no xunit, which is
  a manual-setup plugin), while the reference lists all eight across its two plugin tables. That
  is also the file `skill_init` RULE-48/63 already calls the framework registry. The id is the
  first word of a row's **Display name** cell, which is what the config value spells; RULE-5 and
  the test both say so.
- The tuple stays a tuple: the hook never reads markdown at runtime, so the proof is what keeps
  the two in step, not a parse in the gate.
- Adding `xunit` makes it behave exactly like `c`, `php` and `sql`: `resolve_frameworks` keeps it
  instead of dropping it with a stderr warning, and `pre-push.sh` has no runner arm for it, so it
  falls to the existing `*)` "no pre-push runner arm" line and the verdict still runs. No change
  to `detect_frameworks`, because the registry does not auto-detect xUnit.

Deferrals: none. No other file in `docs/`, `skills/` or `references/` enumerates the set of
names the hook accepts, so nothing went stale with this edit.

### B4

`docs(purlin_references): the proof-plugin contract, and proofs_format Format-Version 6 with the
run-marker section`

Files touched:

- `references/proof_plugin_contract.md` (new; no `Format-Version` line, dash free) with sections
  A (one requirement row per `proof_common` RULE-1 to RULE-25, plus the two legitimate merge
  shapes), B (the 19-step wiring list and the per-framework table of the eight shipped plugins),
  C (the checker and extractor requirement, shell the documented no-extractor exception) and D
  (which test class proves which row, and the per-plugin spec template)
- `references/formats/proofs_format.md` (new `## Run marker` section: the nine RULE-19 fields,
  `skipped_proofs` per RULE-20, the same-commit merge, the PID temp file and single replace;
  `> Format-Version: 5` to `6`, structural)
- `docs/testing-workflow-guide.md` ("Writing a custom plugin" now points at the contract and
  carries a corrected sample: rooted per RULE-22, a `kept` filter that keeps other features and
  unexecuted-but-existing files, a `(id, test_file, test_name)` sort, and a PID temp file
  replaced in one operation)
- `references/supported_frameworks.md` ("Adding More Frameworks" points at the contract and
  names the tables as step 2 of its wiring list)
- `docs/index.md` (resources row), `CLAUDE.md` (authoritative reference files bullet)
- `specs/instructions/purlin_references.md` (`> Scope:` gains the new file, `> Description:`
  Twelve to Thirteen, RULE-30 to RULE-32, PROOF-30 to PROOF-32)
- `dev/test_plugin_contract.py` (new; the three proofs)
- `dev/run_tests.sh` (the new file in the pytest block, which `dev/test_sweep_completeness.py`
  parses)
- `specs/instructions/purlin_references.proofs-unit.json` (3 new entries)
- `RELEASE_NOTES.md`, `dev/test_multilang_proof_plugins.py` (the two in-tree citations of
  `proofs_format.md` version 5, comment and prose only)

Spec maxima left: `specs/instructions/purlin_references.md` RULE-32 / PROOF-32. No other spec
touched. All three new proof descriptions grade PROVABLE under
`static_checks.py --check-proof-design`, and Pass 1 grades all three backings `pass`.

Test counts (whole files, before -> after, passed/skipped):

- `dev/test_plugin_contract.py` 0/0 -> 3/0 (new)
- `dev/test_purlin_references.py` 29/0 -> 29/0
- `dev/test_purlin_docs.py` 16/0 -> 16/0
- `dev/test_sweep_completeness.py` 1/0 -> 1/0
- `dev/test_skill_specs.py` 141/0 -> 141/0
- `dev/test_purlin_agent.py` 12/0 -> 12/0
- `dev/test_schema_proof_format.py` 11/0 -> 11/0
- together: 210 passed -> 213 passed, 0 skipped either way. Only
  `purlin_references.proofs-unit.json` changed; every other feature's proof JSON came back
  byte-identical.

Mutations, `dev/test_plugin_contract.py` run whole each time, restored after each:

1. Step 4's `` `scripts/hooks/pre_push_gate.py` `` replaced with the prose "the pre-push gate".
   1 failed, 2 passed. PROOF-30: "AssertionError: the contract's wiring list does not name
   ['scripts/hooks/pre_push_gate.py']. A framework is wired into that site from memory or not at
   all, which is how a plugin ships half wired: selectable in one file and unknown to the hook
   that runs it".
2. The `RULE-13` requirement row's id changed to `RULE-99`. 1 failed, 2 passed. PROOF-31:
   "AssertionError: proof_common carries ['RULE-13'] with no row in the contract's requirement
   table. A rule the checklist does not mention is one a plugin author never reads" (the
   citation half, which reports `RULE-99` as cited but absent, is reached once the coverage half
   is satisfied).
3. `## Run marker` renamed to `## The test run record` in `proofs_format.md`. 1 failed, 2 passed.
   PROOF-32: "AssertionError: proofs_format.md must carry a `## Run marker` section: a consumer
   reading only [... 'The test run record'] concludes a plugin writes proof files and nothing
   else, and every receipt issued in that project records evidence.test_run as null".

Decisions:

- Section B's path check reads every backticked token in the section that carries a `/` and none
  of `<`, `>` or `*`, rather than one table column. A template such as
  `proof_plugins_<framework>.md` names no single file, and the filter keeps the per-framework
  table's eight plugin paths inside the existence half for free.
- The contract carries no `> Format-Version:` line and is not in `references/formats/`. Nothing
  parses it, so a version on it would be a number nobody could act on, and a consumer pinning it
  would be pinning prose.
- `references/proof_plugin_contract.md` is written dash free but was not added to
  `dev/test_purlin_docs.py`'s `DASH_FREE_REFERENCES`. That tuple is purlin_docs RULE-11's proof
  scope, and widening another feature's proof is a change that belongs with that feature.

Deferrals and adjacent findings:

- Two in-tree citations of `proofs_format.md` version 5 were left alone because C1 owns both
  files this session: `scripts/mcp/purlin_server.py:1193` ("proofs_format.md v5 the tier says
  what kind of test a proof is") and `dev/test_report_data.py:48` ("proofs_format.md v5"). Both
  are comments and neither changes behaviour; they should read v6.
- `specs/instructions/purlin_references.md` RULE-2 and PROOF-2 still pin the three-part merge key
  `(feature, tier, test_file)` while `proofs_format.md` and `proof_common` RULE-4 have carried the
  four-part `(feature, tier, platform, test_file)` since the platform work. The proof passes
  because the three-part string is still in the file, in the sentence explaining that within one
  file the merge is unchanged. Correcting the rule is an amendment to a rule this commit does not
  own a proof for.

### C1

`feat(verify_gate,report_data,sync_status): the opt-in deterministic quality gate, its payload
field, its status line, and the docs that said nothing reads the gauges as a gate`

Files touched:

- `scripts/ci/verify_gate.py` — `QUALITY_MODES`, `_QUALITY_ENFORCEMENT_NOTE`, `_UNMEASURABLE_NOTE`,
  `_load_static_checks`, `_quality_finding_line`, `_unmeasurable_because`, `_quality_section`, the
  mode read and its fail-closed validation, the mode line, the sweep call, the two independent
  verdicts, and a `QUALITY GATE` section in the module docstring
- `scripts/mcp/purlin_server.py` — `_QUALITY_GATE_MODES`, `_quality_gate_line`, its append in
  `_build_summary_table`, and `'quality_gate'` in `_build_report_data`'s payload
- `specs/ci/verify_gate.md` — RULE-14 to RULE-17, PROOF-14 to PROOF-17, PROOF-5 and
  `> Description:` amended
- `specs/mcp/report_data.md` — RULE-46 / PROOF-47; `specs/mcp/sync_status.md` — RULE-66 / PROOF-105
- `specs/instructions/purlin_docs.md` — RULE-9's closed config-field set gains `quality_gate`
- `specs/instructions/purlin_references.md` — RULE-17 and PROOF-17 amended, no new id
- `dev/test_verify_gate.py`, `dev/test_report_data.py`, `dev/test_mcp_server.py`,
  `dev/test_purlin_docs.py` (`CONFIG_FIELDS`), `dev/test_purlin_references.py`
- Part D docs: `docs/regulated-environments.md` (the `- **Not a test quality gate by default.**`
  bullet, two vhash does-not-bind rows, "Policy lives outside the repo", the new
  `### The deterministic quality gate` subsection), `references/hard_gates.md` (the
  "What Is NOT a Gate" bullet, the Layer 3 row, "Project Policy Is Not a Framework Gate"),
  `README.md`, `docs/testing-workflow-guide.md` (gate sentence and a trigger-table row),
  `docs/lifecycle-guide.md`, `references/remote_verification.md`, `references/audit_criteria.md`,
  `skills/audit/SKILL.md`

Spec maxima left: `verify_gate` RULE-17 / PROOF-17; `report_data` RULE-46 / PROOF-47;
`sync_status` RULE-66 / PROOF-105; `purlin_docs` RULE-11 / PROOF-16 (unchanged, RULE-9 amended);
`purlin_references` RULE-29 / PROOF-29 (unchanged, RULE-17 and PROOF-17 amended in place).

Test counts, whole files, before to after:

- `dev/test_verify_gate.py` 13 passed to 17 passed, 0 skipped
- `dev/test_report_data.py` 47 to 48; `dev/test_mcp_server.py` 89 to 90
- `dev/test_purlin_docs.py` 16, `dev/test_purlin_references.py` 29, `dev/test_skill_specs.py` 141,
  `dev/test_purlin_agent.py` 12: unchanged
- `dev/test_e2e_audit_cache_pipeline.py`, `dev/test_purlin_report.py`, `dev/test_static_checks.py`,
  `dev/test_windows_native.py` run green and unchanged (213 passed, 2 skipped together)

Gate run on this worktree, `python3 scripts/ci/verify_gate.py --check --project-root .`: 42 lines
and exit 0 before, with the one new line `verify-gate: quality_gate = off`; 152 lines and exit 1
with a temporary `"quality_gate": "deterministic"`, reporting `Quality gate (deterministic): 82
HOLLOW, 0 UNPROVABLE, 24 unmeasurable` and the quality FAIL line. The config was reverted. No
refresh of `.purlin/report-data.js` was needed or made: the gate calls `read_report_payload`,
which rebuilds the payload from `.purlin/config.json` and the specs, and never reads that file.

Mutations, each reverted and the file re-run green after:

1. `print('verify-gate: PASS (nothing to check).')` before the quality-mode read.
   PROOF-14 failed with "AssertionError: remote mode 'required': a gate that cannot read its own
   declaration must not print a PASS" (PROOF-9 and PROOF-15 failed too).
2. The sweep run under every mode (`if quality in QUALITY_MODES`). PROOF-14 failed with
   "AssertionError: under 'off' the mode line is the whole of the difference; the rest of the
   output still mentions the gate", the `Quality gate (deterministic): 0 HOLLOW ...` section
   printed under it.
3. `'quality_gate'` dropped from `_build_report_data`'s payload. PROOF-47 failed with
   "AssertionError: the payload must carry the declared quality gate verbatim; declared
   'deterministic', payload says None".
4. `quality_fail = bool(hollow or unprovable or unmeasurable)`. PROOF-15 failed with
   "AssertionError: with the tautology gone the gate must pass, got 1".
5. `_quality_gate_line`'s `off` branch deleted, so the line prints for every project. PROOF-105
   failed with "AssertionError: a project with no quality_gate field must print no line".
6. `os.makedirs(<root>/.purlin/cache)` in the deterministic branch. PROOF-17 failed with
   "AssertionError: a deterministic run created .purlin/cache/; the gate grades the evidence and
   must not write beside it".
7. The opt-in sentence removed from `hard_gates.md`'s "What Is NOT a Gate" list. verify_gate
   PROOF-16 failed with "the opt-in mode must be named in the list where a reader counts gates,
   not only in a later section" and purlin_references PROOF-17 with "the list must name
   `quality_gate` as the opt-in that makes the deterministic half of the gauges a CI failure".

Decisions taken:

- The quality mode is validated immediately after the remote mode and before the registry check,
  so a typo fails closed in every remote mode including the one whose registry is broken.
- When only the quality gate fails, no remote PASS line is printed: the two verdicts are computed
  first, then the FAIL lines, then the remote PASS lines. With `quality_gate` off this is
  byte-identical to the previous ordering, which is what PROOF-3, PROOF-6, PROOF-9, PROOF-12 and
  PROOF-13 keep pinning.
- The unmeasurable sentence is printed only when the sweep reported an unmeasurable proof. It
  explains the third count; with nothing in that column it is noise.
- `sync_status`'s line never runs the sweep. A status call happens on every turn and the sweep is
  a CI cost the project asked CI to pay; the dashboard chip stays out of scope, as the plan says.
- Mutation 7 did not fail on the first attempt: both new assertions split `hard_gates.md` on
  `What Is NOT a Gate` and read everything after it, and `quality_gate` also appears in the Layer 3
  row and in "Project Policy Is Not a Framework Gate" further down. Both tests now cut the split at
  the next `## ` heading, which also tightens the pre-existing `Proof Design`/`Proof Integrity`
  assertion in purlin_references PROOF-17.

Deferral and adjacent defect found, not fixed: `dev/test_consumer_ci.py::test_fixture_is_a_complete
_tracked_consumer_project` (consumer_ci PROOF-2) fails at HEAD, before any change in this commit.
B2 edited `scripts/proof/pytest_purlin.py` without syncing
`dev/fixtures/consumer-ci/.purlin/plugins/pytest_purlin.py`, which the proof requires to be
byte-identical. It is B2's fixture to re-copy; `specs/ci/consumer_ci.proofs-unit.json` was restored
rather than committed with the failing entry.

### Fixture re-sync (adjacent defect from B2 and B3)

`fix(consumer_ci): the fixture's pytest plugin copy follows the plugin B2 and B3 changed`

consumer_ci PROOF-2 compares `dev/fixtures/consumer-ci/.purlin/plugins/pytest_purlin.py` with
`scripts/proof/pytest_purlin.py` byte for byte, and B2 and B3 changed the plugin without
re-copying it, so the proof failed at HEAD from 64e535b3 to 8460dabe. The copy is re-synced.
Two comments that cited `proofs_format.md v5` (`scripts/mcp/purlin_server.py`,
`dev/test_report_data.py`) now cite v6, the version B4 set. No spec touched, no id taken.
Test counts: `dev/test_consumer_ci.py`, `dev/test_report_data.py`, `dev/test_mcp_server.py`
run whole together, 140 passed, every proof JSON byte-identical. Sanity: the fixture copied
to a temp dir and run with `python3 -m pytest` writes `specs/core/greeting.proofs-unit.json`
with `test_file` `tests/test_greeting.py`; its Linux-only platform test fails on macOS by
design. Mutation: the state before this commit (the plugin copy one commit behind) is the
failing case, PROOF-2 `test_fixture_is_a_complete_tracked_consumer_project` failed on the
byte comparison at 8460dabe; after the re-copy it passes.
