# Feature: init_e2e

> Scope: skills/init/SKILL.md, templates/config.json, scripts/proof/, scripts/hooks/pre-push.sh, scripts/mcp/purlin_server.py
> Stack: shell/bash, python3 (sync_status, config_engine), node (jest reporter)
> Description: End-to-end verification that the project structure produced by `purlin:init` works correctly with ALL downstream Purlin tools. Tests the full contract between init's output and `sync_status`, proof plugins (pytest, jest, shell), the pre-push hook, and the dashboard report, across different project configurations (Python, JavaScript, multi-framework, shell-only, re-init).

## Rules

- RULE-1: After init, `.purlin/`, `.purlin/plugins/`, `specs/`, and `specs/_anchors/` directories all exist
- RULE-2: `config.json` is valid JSON containing all 5 required fields: `version`, `test_framework`, `spec_dir`, `pre_push`, `report`
- RULE-3: The `version` field in `config.json` matches the contents of the `VERSION` file
- RULE-4: Default config values are `test_framework: "auto"`, `spec_dir: "specs"`, `pre_push: "warn"`, `report: true`
- RULE-5: When `conftest.py` exists at project root, auto-detection selects pytest
- RULE-6: When `pyproject.toml` contains `[tool.pytest]`, auto-detection selects pytest
- RULE-7: When `package.json` contains `"jest"`, auto-detection selects jest
- RULE-8: When `package.json` contains `"vitest"`, init scaffolds `jest_purlin.js` (vitest maps to jest)
- RULE-9: When both `conftest.py` and `package.json` with `jest` exist, both plugins are scaffolded and `test_framework` is `"pytest,jest"`
- RULE-10: When no framework indicators are present, shell plugin is scaffolded as fallback
- RULE-11: Scaffolded `pytest_purlin.py` in `.purlin/plugins/` is byte-identical to `scripts/proof/pytest_purlin.py`
- RULE-12: Scaffolded `jest_purlin.js` in `.purlin/plugins/` is byte-identical to `scripts/proof/jest_purlin.js`
- RULE-13: Scaffolded `purlin-proof.sh` in `.purlin/plugins/` is byte-identical to `scripts/proof/shell_purlin.sh`
- RULE-14: Scaffolded `pytest_purlin.py` produces valid `.proofs-unit.json` when run with `@pytest.mark.proof` markers against a spec
- RULE-15: Scaffolded `jest_purlin.js` produces valid `.proofs-unit.json` when invoked as reporter with `[proof:...]` markers against a spec
- RULE-16: Scaffolded `purlin-proof.sh` produces valid `.proofs-unit.json` when `purlin_proof` + `purlin_proof_finish` are called against a spec
- RULE-17: After init with empty specs dir, `sync_status` returns "No specs found" message without errors
- RULE-18: After creating a spec with no proofs, `sync_status` reports UNTESTED; after adding passing proofs for all behavioral rules, reports PASSING; after adding a failing proof, reports FAILING
- RULE-19: When `report: true` in config, `sync_status` generates `.purlin/report-data.js` containing valid `PURLIN_DATA`
- RULE-20: `.gitignore` contains all required purlin entries: `.purlin/runtime/`, `.purlin/plugins/__pycache__/`, `.purlin/cache/`, `/purlin-report.html`, `.purlin/report-data.js`
- RULE-21: Running init twice (re-init with --force) does not create duplicate entries in `.gitignore`
- RULE-22: After init, `.git/hooks/pre-push` exists, is executable, and contains "purlin"
- RULE-23: When a non-purlin pre-push hook exists before init, the existing hook is preserved (not overwritten)
- RULE-24: When `report: true`, `purlin-report.html` exists at the project root; when `report: false`, it does not
- RULE-25: Full lifecycle works end-to-end: init creates structure, spec created in `specs/`, proof plugin runs tests with markers, proofs emitted as `.proofs-unit.json`, `sync_status` reads proofs and reports PASSING, pre-push hook allows push

## Proof

- PROOF-1 (RULE-1): Create init-equivalent structure via helper; verify `.purlin/`, `.purlin/plugins/`, `specs/`, `specs/_anchors/` all exist as directories @e2e
- PROOF-2 (RULE-2): Read `config.json` from init-equivalent project; parse as JSON; verify `version`, `test_framework`, `spec_dir`, `pre_push`, `report` keys all present @e2e
- PROOF-3 (RULE-3): Read VERSION file and `config.json` version field; verify they are identical @e2e
- PROOF-4 (RULE-4): Create project with no overrides; verify `test_framework=="auto"`, `spec_dir=="specs"`, `pre_push=="warn"`, `report==true` @e2e
- PROOF-5 (RULE-5): Create project with `conftest.py` at root and `test_framework: "auto"` in config; run pre-push hook; verify output contains "(pytest)" @e2e
- PROOF-6 (RULE-6): Create project with `pyproject.toml` containing `[tool.pytest]` and auto config; run pre-push hook; verify output contains "(pytest)" @e2e
- PROOF-7 (RULE-7): Create project with `package.json` containing `"jest"` and auto config; run pre-push hook; verify output contains "(jest)" @e2e
- PROOF-8 (RULE-8): Create project with `package.json` containing `"vitest"`; scaffold plugins via helper with "jest"; verify `.purlin/plugins/jest_purlin.js` exists @e2e
- PROOF-9 (RULE-9): Create project with `conftest.py` + `package.json` with jest; use framework "pytest,jest"; verify both `.purlin/plugins/pytest_purlin.py` and `.purlin/plugins/jest_purlin.js` exist and config `test_framework` is "pytest,jest" @e2e
- PROOF-10 (RULE-10): Create project with no framework indicators; scaffold with "shell"; verify `.purlin/plugins/purlin-proof.sh` exists @e2e
- PROOF-11 (RULE-11): Diff scaffolded `.purlin/plugins/pytest_purlin.py` against `scripts/proof/pytest_purlin.py`; verify zero differences @e2e
- PROOF-12 (RULE-12): Diff scaffolded `.purlin/plugins/jest_purlin.js` against `scripts/proof/jest_purlin.js`; verify zero differences @e2e
- PROOF-13 (RULE-13): Diff scaffolded `.purlin/plugins/purlin-proof.sh` against `scripts/proof/shell_purlin.sh`; verify zero differences @e2e
- PROOF-14 (RULE-14): Scaffold pytest plugin; create spec with 2 rules; write test file with `@pytest.mark.proof` markers; run `python3 -m pytest`; verify `.proofs-unit.json` exists with 2 passing entries @e2e
- PROOF-15 (RULE-15): Scaffold jest reporter; create spec; exercise reporter via `node -e` with Module._load mock for glob; verify `.proofs-unit.json` exists with correct feature and status=pass @e2e
- PROOF-16 (RULE-16): Scaffold shell harness; create spec; source scaffolded `purlin-proof.sh`; call `purlin_proof` + `purlin_proof_finish`; verify `.proofs-unit.json` exists with status=pass @e2e
- PROOF-17 (RULE-17): Create init-equivalent project with empty `specs/` dir; run `sync_status`; verify output contains "No specs found" @e2e
- PROOF-18 (RULE-18): Phase A: create spec with 2 behavioral rules, no proofs — verify `sync_status` reports UNTESTED; Phase B: add passing proofs for both rules — verify PASSING; Phase C: change one proof to fail — verify FAILING @e2e
- PROOF-19 (RULE-19): Create project with `report: true` and a spec with passing proofs; run `sync_status`; verify `.purlin/report-data.js` exists and starts with `const PURLIN_DATA = ` @e2e
- PROOF-20 (RULE-20): Create init-equivalent `.gitignore`; grep for each of the 5 required entries; verify all present @e2e
- PROOF-21 (RULE-21): Run init helper twice on same project; count occurrences of `.purlin/runtime/` in `.gitignore`; verify exactly 1 @e2e
- PROOF-22 (RULE-22): Create init-equivalent project with pre-push hook installed; verify `.git/hooks/pre-push` exists (`-f`), is executable (`-x`), and `grep -q purlin` succeeds @e2e
- PROOF-23 (RULE-23): Create project with existing pre-push hook containing "#!/bin/bash\necho custom"; run init helper; verify hook still contains "echo custom" @e2e
- PROOF-24 (RULE-24): Create project with `report=true`; verify `purlin-report.html` exists; create project with `report=false`; verify it does not exist @e2e
- PROOF-25 (RULE-25): Python lifecycle: init → create spec with 2 rules → write test with `@pytest.mark.proof` → run pytest → verify proofs emitted → run `sync_status` → verify PASSING → run pre-push hook → verify exit 0 @e2e
- PROOF-26 (RULE-25): Shell lifecycle: init → create spec with 2 rules → source scaffolded shell plugin → call `purlin_proof` + `purlin_proof_finish` → verify proofs → run `sync_status` → verify PASSING @e2e
- PROOF-27 (RULE-25): Jest lifecycle: init → create spec → exercise scaffolded reporter via `node -e` → verify proofs → run `sync_status` → verify PASSING @e2e
