# Feature: proof_plugins_pytest

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/pytest_purlin.py
> Stack: python/stdlib, pytest plugin (pytest_configure + pytest_collection_modifyitems + pytest_runtest_makereport hooks)
> Description: The pytest proof plugin. Collects `@pytest.mark.proof(...)` markers during the
>   test call phase and emits standardized proof JSON. Inherits all shared proof-plugin
>   behavior (spec-dir resolution, naming, fallback, write-scoped overwrite, the 7 fields,
>   status, no-op, discovery, stderr warning, purge) from proof_common. The pytest marker
>   syntax, its argument handling, path resolution and hook wiring are all this spec adds.

## Rules

- RULE-1: The marker signature is `@pytest.mark.proof("feature", "PROOF-N", "RULE-N", tier="unit")` where tier defaults to `"unit"`
- RULE-2: Markers with fewer than 3 positional args are silently skipped
- RULE-3: `test_file` is recorded as the path relative to the project root (proof_common RULE-23), not to pytest's own `rootdir`, which is the invocation directory when the run started below the project root
- RULE-4: The plugin registers itself via `pytest_configure` and collects results in `pytest_runtest_makereport` during the `call` phase only
- RULE-5: `pytest_configure` registers `unit`, `integration` and `e2e` as pytest markers, and the collector's `pytest_collection_modifyitems` adds to every test carrying a proof marker the marker its `tier` kwarg names (`unit` when absent), so a proof tier is selectable with `-m` without any test restating it. The tier marker is added alongside whatever the test already carries, never substituted for it, and a tier outside the three registered names is added verbatim

## Proof

- PROOF-1 (RULE-1): Create a test with `@pytest.mark.proof("feat", "PROOF-1", "RULE-1")`; run pytest; verify the proof entry has `feature: "feat"`, `tier: "unit"` @integration
- PROOF-2 (RULE-2): Create a test with `@pytest.mark.proof("feat", "PROOF-1")` (only 2 args); run pytest; verify no proof entry is emitted for that test @integration
- PROOF-3 (RULE-3): Run pytest from a project root; verify `test_file` in the proof entry is relative to the project root (not absolute) @integration
- PROOF-4 (RULE-4): Hand `pytest_configure` a fake config; verify it adds an ini line naming the `proof` marker and registers a `ProofCollector` under the plugin name `purlin_proof`. Then run a real pytest session over one file holding a marked test whose fixture raises (setup phase) and a marked test that fails in its own body (call phase); verify the written proof file holds the call-phase test as `PROOF-2` with `status: "fail"` and holds no entry at all for the setup-phase test's `PROOF-1`, because `pytest_runtest_makereport` collects during the `call` phase only @integration
- PROOF-5 (RULE-5): Load the real plugin over a fixture holding 3 tests marked for feature `feat` at tiers `unit`, `integration` and `e2e`; run pytest with no `-m`, then again with `-m "not integration and not e2e"`; verify the first run writes `feat.proofs-unit.json`, `feat.proofs-integration.json` and `feat.proofs-e2e.json`, the second writes only `feat.proofs-unit.json` holding exactly 1 entry, and `pytest --markers` lists `unit`, `integration` and `e2e` @integration
