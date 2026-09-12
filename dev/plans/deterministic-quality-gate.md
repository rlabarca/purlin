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
