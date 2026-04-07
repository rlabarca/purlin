# Feature: skill_init

> Scope: skills/init/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:init` skill initializes a project for spec-driven development. It creates `.purlin/`, `specs/`, detects the test framework, scaffolds the proof plugin, and manages plugin configuration.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `init`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: `--add-plugin` validates plugin files against language-specific patterns (Python: `proofs`+`json`, JS: `proofs`+`JSON`, Shell: `purlin_proof`, Java: `proofs`+`Proof`) and warns if validation fails
- RULE-6: `--add-plugin` supports both local file paths and git URL sources with distinct handling for each
- RULE-7: `--list-plugins` identifies built-in plugins (`pytest_purlin`, `jest_purlin`, `purlin-proof`) by framework name and labels all others as `custom`
- RULE-8: After init, `.purlin/`, `.purlin/plugins/`, `specs/`, and `specs/_anchors/` directories all exist
- RULE-9: `config.json` is valid JSON containing all 5 required fields: version, test_framework, spec_dir, pre_push, report
- RULE-10: The version field in config.json matches the contents of the VERSION file
- RULE-11: Default config values are test_framework: auto, spec_dir: specs, pre_push: warn, report: true
- RULE-12: When conftest.py exists at project root, auto-detection selects pytest
- RULE-13: When pyproject.toml contains [tool.pytest], auto-detection selects pytest
- RULE-14: When package.json contains jest, auto-detection selects jest
- RULE-15: When package.json contains vitest, init scaffolds jest_purlin.js (vitest maps to jest)
- RULE-16: When both conftest.py and package.json with jest exist, both plugins are scaffolded and test_framework is pytest,jest
- RULE-17: When no framework indicators are present, shell plugin is scaffolded as fallback
- RULE-18: Scaffolded pytest_purlin.py in .purlin/plugins/ is byte-identical to scripts/proof/pytest_purlin.py
- RULE-19: Scaffolded jest_purlin.js in .purlin/plugins/ is byte-identical to scripts/proof/jest_purlin.js
- RULE-20: Scaffolded purlin-proof.sh in .purlin/plugins/ is byte-identical to scripts/proof/shell_purlin.sh
- RULE-21: Scaffolded pytest_purlin.py produces valid .proofs-unit.json when run with @pytest.mark.proof markers
- RULE-22: Scaffolded jest_purlin.js produces valid .proofs-unit.json when invoked as reporter with [proof:...] markers
- RULE-23: Scaffolded purlin-proof.sh produces valid .proofs-unit.json when purlin_proof + purlin_proof_finish are called
- RULE-24: After init with empty specs dir, sync_status returns No specs found without errors
- RULE-25: Status progression: no proofs reports UNTESTED, all passing reports PASSING, one failing reports FAILING
- RULE-26: When report: true in config, sync_status generates .purlin/report-data.js containing valid PURLIN_DATA
- RULE-27: .gitignore contains all required purlin entries
- RULE-28: Running init twice (re-init) does not create duplicate entries in .gitignore
- RULE-29: After init, .git/hooks/pre-push exists, is executable, and contains purlin
- RULE-30: When a non-purlin pre-push hook exists before init, the existing hook is preserved
- RULE-31: When report: true, purlin-report.html exists at project root; when report: false, it does not
- RULE-32: Full lifecycle works end-to-end: init creates structure, spec created, proof plugin runs, proofs emitted, sync_status reports PASSING, pre-push hook allows push
- RULE-33: Init prints DETECTING CODEBASE before scanning for test frameworks
- RULE-34: Init always presents the full framework selection list to the user, even when auto-detection succeeds, with detected frameworks pre-selected
- RULE-35: When a single framework is detected, the selection list shows it pre-selected with [x] and all others unselected with [ ]
- RULE-36: When multiple frameworks are detected, all detected frameworks are pre-selected in the list
- RULE-37: When no frameworks are detected, the selection list shows all options unselected

## Proof

- PROOF-1 (RULE-1): Grep `skills/init/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/init/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `init`
- PROOF-4 (RULE-4): Grep `skills/init/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/init/SKILL.md` for language validation entries (`Python`, `JavaScript`, `Shell`, `Java`) and warning text `doesn't look like a standard proof plugin`; verify all present
- PROOF-6 (RULE-6): Grep `skills/init/SKILL.md` for `local file path` and `git URL`; verify both source types are documented with distinct handling steps
- PROOF-7 (RULE-7): Grep `skills/init/SKILL.md` for `pytest_purlin.py` with `Python/pytest`, `jest_purlin.js` with `JavaScript/Jest`, and the label `custom`; verify the labeling table exists
- PROOF-8 (RULE-8): e2e: Create init-equivalent structure; verify .purlin/, .purlin/plugins/, specs/, specs/_anchors/ all exist @e2e
- PROOF-9 (RULE-9): e2e: Read config.json; parse as JSON; verify all 5 required fields present @e2e
- PROOF-10 (RULE-10): e2e: Read VERSION file and config.json version; verify identical @e2e
- PROOF-11 (RULE-11): e2e: Create project with no overrides; verify default values @e2e
- PROOF-12 (RULE-12): e2e: Create project with conftest.py; run pre-push; verify pytest detected @e2e
- PROOF-13 (RULE-13): e2e: Create project with pyproject.toml [tool.pytest]; verify pytest detected @e2e
- PROOF-14 (RULE-14): e2e: Create project with package.json jest; verify jest detected @e2e
- PROOF-15 (RULE-15): e2e: Create project with vitest; verify jest_purlin.js scaffolded @e2e
- PROOF-16 (RULE-16): e2e: Create project with conftest.py + package.json jest; verify both plugins and pytest,jest config @e2e
- PROOF-17 (RULE-17): e2e: Create project with no framework indicators; verify purlin-proof.sh scaffolded @e2e
- PROOF-18 (RULE-18): e2e: Diff scaffolded pytest_purlin.py against source; verify byte-identical @e2e
- PROOF-19 (RULE-19): e2e: Diff scaffolded jest_purlin.js against source; verify byte-identical @e2e
- PROOF-20 (RULE-20): e2e: Diff scaffolded purlin-proof.sh against source; verify byte-identical @e2e
- PROOF-21 (RULE-21): e2e: Scaffold pytest plugin; create spec; run pytest with markers; verify valid proofs emitted @e2e
- PROOF-22 (RULE-22): e2e: Scaffold jest reporter; create spec; exercise via node; verify valid proofs emitted @e2e
- PROOF-23 (RULE-23): e2e: Scaffold shell harness; create spec; call purlin_proof + purlin_proof_finish; verify valid proofs @e2e
- PROOF-24 (RULE-24): e2e: Create project with empty specs/; run sync_status; verify No specs found @e2e
- PROOF-25 (RULE-25): e2e: Status progression: no proofs UNTESTED, passing proofs PASSING, failing proof FAILING @e2e
- PROOF-26 (RULE-26): e2e: Create project with report:true and passing proofs; run sync_status; verify report-data.js generated @e2e
- PROOF-27 (RULE-27): e2e: Verify .gitignore contains all required purlin entries @e2e
- PROOF-28 (RULE-28): e2e: Run init twice; verify no duplicate gitignore entries @e2e
- PROOF-29 (RULE-29): e2e: Verify .git/hooks/pre-push exists, is executable, contains purlin @e2e
- PROOF-30 (RULE-30): e2e: Create existing non-purlin hook; run init; verify hook preserved @e2e
- PROOF-31 (RULE-31): e2e: Verify report:true creates purlin-report.html, report:false does not @e2e
- PROOF-32 (RULE-32): e2e: Python lifecycle: init, spec, pytest, proofs, PASSING, hook ok @e2e
- PROOF-33 (RULE-32): e2e: Shell lifecycle: init, spec, shell proof, proofs, PASSING @e2e
- PROOF-34 (RULE-32): e2e: Jest lifecycle: init, spec, reporter, proofs, PASSING @e2e
- PROOF-35 (RULE-33): e2e: Verify SKILL.md contains "DETECTING CODEBASE" print instruction before framework scan @e2e
- PROOF-36 (RULE-34): e2e: Verify SKILL.md documents always presenting the framework selection list with [x] and [ ] markers, including when auto-detection succeeds @e2e
- PROOF-37 (RULE-35): e2e: Verify SKILL.md shows a single-detection example with one [x] pre-selected and remaining [ ] unselected @e2e
- PROOF-38 (RULE-36): e2e: Verify SKILL.md shows a multi-detection example with multiple [x] pre-selected @e2e
- PROOF-39 (RULE-37): e2e: Verify SKILL.md shows a no-detection example with all [ ] unselected @e2e
