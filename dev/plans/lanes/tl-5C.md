# Lane 5C: word swaps

Plan: `dev/plans/three-levels.md` (read Part A and Part C in full; skim Part B). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Worktree `/Users/richlabarca/LocalCode/purlin-wt/5C`,
branch `lane/5C` off `three-levels`. You start after lane 5A has merged, so
`dev/test_skills.py` already reads the new skill names.

This lane changes words, not behaviour. Every edit replaces a retired spelling (decision 15
and `tl-_rules.md` "Vocabulary") with the word Part A gives it, in the sentence the file
already has. Where a sentence describes a retired mechanism (an approval file, a verdict, the
seven states) rather than only using a retired word, rewrite the sentence to say what the
three-level model does, in the same length. Do not add sections, examples or rules.

## Files

- `skills/build/SKILL.md`, `skills/spec-from-code/SKILL.md`, `skills/anchor/SKILL.md`,
  `skills/rename/SKILL.md` per decision 15 and Part A4 (`purlin:verify`→`purlin:audit`,
  `purlin:approve`→`purlin:sign`, `purlin:review`→`purlin:sign`, `approval`→`signature`,
  `.approvals/`→`.signatures/`, gate values). The rename skill's table row for the evidence
  directory reads `specs/<category>/<old>.signatures/`.
- `specs/skills/skill_rename.md` and `specs/skills/skill_drift.md`: the descriptions and any
  rule text that names the old words. Keep every RULE and PROOF id.
- `hooks/hooks.json`: read it; it should need no change; say so in your report.
- `scripts/proof/pytest_purlin.py`, `jest_purlin.js`, `vitest_purlin.ts`, `shell_purlin.sh`,
  `sql_purlin.sh`, `xunit_purlin.cs`: `purlin:verify`→`purlin:audit`; "recorded" in plain
  English ("every recorded test_file" becomes "every test_file it writes"; "the record
  `purlin:verify` writes" becomes "the record `purlin:audit` writes"). Then re-copy
  `pytest_purlin.py`, `jest_purlin.js`, `vitest_purlin.ts` and `shell_purlin.sh` (as
  `purlin-proof.sh`) to `dev/fixtures/consumer-ci/.purlin/plugins/` and `.purlin/plugins/`
  where a copy exists, byte for byte: `dev/test_consumer_ci.py` PROOF-2 and
  `specs/_anchors/proof_common.md` PROOF-20 compare them.
- `scripts/purlin_python.sh` L32: "platform" becomes "operating system".
- `scripts/mcp/purlin/frameworks.py`, `scripts/run/mutation/__init__.py`, `scripts/run/remote.py`:
  only if a retired word is still there after phases 1 and 2 (lanes 1A and 2B own the logic;
  a leftover word is yours).
- `dev/fixtures/consumer-ci/.purlin/records/README.md`, `dev/fixtures/consumer-ci/specs/core/greeting.md`,
  `dev/fixtures/consumer-ci/tests/test_greeting.py`: one word each.
- `dev/test_multilang_proof_plugins.py`, `dev/test_mutation_adapters.py`,
  `dev/test_plugin_contract.py`, `dev/test_pre_push_hook.py`, `dev/test_proof_plugins.sh`,
  `dev/test_proof_plugins_missing.py`, `dev/test_proof_stress.py`: the word in a docstring,
  a comment or a message string; never an assertion's meaning.
- `specs/mcp/config_engine.md`, `specs/_anchors/proof_common.md`: one word each.
- Delete every one of the above from `PENDING_REWRITE` in `dev/test_vocabulary.py`.

## Acceptance

```
pytest dev/test_vocabulary.py dev/test_skills.py dev/test_plugin_contract.py dev/test_proof_plugins_missing.py dev/test_pre_push_hook.py dev/test_mutation_adapters.py
cmp scripts/proof/pytest_purlin.py dev/fixtures/consumer-ci/.purlin/plugins/pytest_purlin.py && cmp scripts/proof/pytest_purlin.py .purlin/plugins/pytest_purlin.py
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH; pytest dev/test_multilang_proof_plugins.py
bash dev/run_tests.sh --fast   (report the summary and the red list)
```
