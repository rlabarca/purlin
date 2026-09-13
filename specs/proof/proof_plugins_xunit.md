# Feature: proof_plugins_xunit

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/xunit_purlin.cs
> Stack: dotnet/xunit, custom ITestLoggerWithParameters registered via `dotnet test --logger purlin`; the marker is the xUnit trait named exactly `PurlinProof` (NUnit and MSTest are not supported)
> Description: The xUnit/.NET proof plugin (`scripts/proof/xunit_purlin.cs`). A custom
>   `dotnet test` logger collects proof markers expressed as the `PurlinProof` test trait,
>   maps the test outcome to pass/fail, and emits standardized proof JSON. Inherits all
>   shared proof-plugin behavior (spec-dir resolution, naming, fallback, write-scoped
>   overwrite, the 7 fields, status, no-op, discovery, stderr warning, purge) from proof_common.
>   The marker is a trait rather than a parsed string because `TestCase.Traits` is the metadata
>   channel the .NET test platform hands every logger; the logger reads exactly one trait name,
>   `PurlinProof`, compared ordinally, so `Category`, `Property`, `TestProperty` or the same
>   word in another casing is not a marker. Collecting in process during the run, rather than
>   parsing a `.trx` afterwards, is what makes it the same reporter model as the pytest, Jest
>   and Vitest plugins. Wiring the `Purlin.TestLogger` assembly and the
>   `CollectSourceInformation=true` switch that populates `test_file` is documented once, in
>   `references/formats/proofs_format.md`.

## Rules

- RULE-1: The .NET marker is the xUnit test trait whose name is exactly `PurlinProof`: `[Trait("PurlinProof", "feature:PROOF-N:RULE-N:tier")]`. The trait name is compared ordinally, so a trait with any other name - `Category`, `Property`, `TestProperty`, or `PurlinProof` spelled in another case - is not a marker and is ignored; NUnit and MSTest support is not claimed. The trait value is a colon-delimited `feature:PROOF-N:RULE-N:tier` string where tier defaults to `"unit"`
- RULE-2: The plugin is a custom `dotnet test` logger (`ITestLoggerWithParameters`) registered via `dotnet test --logger purlin`; it collects results during the run, not by post-parsing a `.trx` file
- RULE-3: Tests without a `PurlinProof` trait are ignored: no proof entry is emitted for them
- RULE-4: A test `Outcome` of `Passed` maps to `status: "pass"`; `Failed` and all other non-skipped outcomes (e.g. `NotExecuted`) map to `status: "fail"`; a `Skipped` test is not recorded at all
- RULE-5: `test_file` is recorded as the source file path relative to the project root (resolved from `TestCase` source information / `CodeFilePath`); `test_name` is the fully-qualified test method name
- RULE-6: On run completion the logger emits proof JSON to the resolved spec directory following the shared write-scoped overwrite contract

## Proof

- PROOF-1 (RULE-1): Build an xUnit project whose `tests/Tests.cs` carries four marked methods - `[Trait("PurlinProof", "feat:PROOF-1:RULE-1:unit")]`, `[Trait("PurlinProof", "feat:PROOF-7:RULE-7")]` with the tier segment omitted, `[Trait("Category", "feat:PROOF-9:RULE-9:unit")]`, and `[Trait("purlinproof", "feat:PROOF-8:RULE-8:unit")]` whose name differs from the marker only in case - and run `dotnet test --logger purlin`; verify `specs/svc/feat.proofs-unit.json` holds an entry with `feature: "feat"`, `id: "PROOF-1"`, `rule: "RULE-1"`, `tier: "unit"` and an entry with `id: "PROOF-7"`, `rule: "RULE-7"`, `tier: "unit"` rather than an empty or missing tier, so the omitted segment takes the default; and verify that across every `*.proofs-*.json` file under the project root no entry has `id: "PROOF-9"` or `id: "PROOF-8"`, so the `Category` trait and the differently-cased `purlinproof` trait were both ignored (a logger matching trait names loosely would write a PROOF-8 or PROOF-9 entry) @integration
- PROOF-2 (RULE-2): Run `dotnet test tests/tests.csproj --logger purlin` on a project with marked tests, with no `trx` token anywhere in the argv; verify the run's output carries the logger's own in-run line `[PurlinProofLogger] collected`, that `specs/svc/feat.proofs-unit.json` holds the `PROOF-1` entry afterwards, and that a recursive search for `*.trx` under the project root finds no file, so the proofs were collected in-process and not parsed out of a result file @integration
- PROOF-3 (RULE-3): Run a test with no `PurlinProof` trait; verify no proof entry is emitted for that test @integration
- PROOF-4 (RULE-4): Run a passing marked test and a failing marked test; verify `status: "pass"` and `status: "fail"` respectively; add a `[Fact(Skip="...")]` marked test and verify it is not recorded @integration
- PROOF-5 (RULE-5): Run `dotnet test` from a project root; verify `test_file` is relative (not absolute) and `test_name` is the fully-qualified method name @integration
- PROOF-6 (RULE-6): Pre-seed a proof file with feature B entries; run the logger for feature A; verify feature B entries are preserved and feature A entries are replaced (inherits the proof_common write-scoped overwrite contract) @integration
