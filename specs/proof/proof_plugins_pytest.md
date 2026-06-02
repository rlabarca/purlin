# Feature: proof_plugins_pytest

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/pytest_purlin.py
> Stack: python/stdlib, pytest plugin (pytest_configure + pytest_runtest_makereport hooks)
> Description: The pytest proof plugin. Collects `@pytest.mark.proof(...)` markers during the
>   test call phase and emits standardized proof JSON. Inherits all shared proof-plugin
>   behavior (spec-dir resolution, naming, fallback, feature-scoped overwrite, the 7 fields,
>   status, no-op, discovery, stderr warning, purge) from proof_common.

## What it does

Registers a pytest plugin that reads `@pytest.mark.proof` decorators from test functions as
they run and writes one proof file per feature/tier. Only the pytest-specific marker syntax,
arg handling, path resolution, and hook wiring live here; everything else is proof_common.

## Rules

- RULE-1: The marker signature is `@pytest.mark.proof("feature", "PROOF-N", "RULE-N", tier="unit")` where tier defaults to `"unit"`
- RULE-2: Markers with fewer than 3 positional args are silently skipped
- RULE-3: `test_file` is recorded as the path relative to the pytest rootdir
- RULE-4: The plugin registers itself via `pytest_configure` and collects results in `pytest_runtest_makereport` during the `call` phase only

## Proof

- PROOF-1 (RULE-1): Create a test with `@pytest.mark.proof("feat", "PROOF-1", "RULE-1")`; run pytest; verify the proof entry has `feature: "feat"`, `tier: "unit"` @integration
- PROOF-2 (RULE-2): Create a test with `@pytest.mark.proof("feat", "PROOF-1")` (only 2 args); run pytest; verify no proof entry is emitted for that test @integration
- PROOF-3 (RULE-3): Run pytest from a project root; verify `test_file` in the proof entry is relative to the root (not absolute) @integration
- PROOF-4 (RULE-4): Verify `pytest_configure` registers the `proof` marker and the `purlin_proof` plugin @integration
