# Feature: proof_plugins_xunit

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/xunit_purlin.cs
> Stack: dotnet/xunit, custom ITestLoggerWithParameters registered via `dotnet test --logger purlin`; trait-based marker, also compatible with NUnit/MSTest via TestCase.Traits
> Description: The xUnit/.NET proof plugin (`scripts/proof/xunit_purlin.cs`). A custom
>   `dotnet test` logger collects proof markers expressed as the `PurlinProof` test trait,
>   maps the test outcome to pass/fail, and emits standardized proof JSON. Inherits all
>   shared proof-plugin behavior (spec-dir resolution, naming, fallback, feature-scoped
>   overwrite, the 7 fields, status, no-op, discovery, stderr warning, purge) from proof_common.

## What it does

Collects Purlin proofs from .NET test projects. The marker is a test trait rather than a
parsed string, because traits are the standard, framework-neutral metadata channel in the .NET
test platform — xUnit's `[Trait]`, NUnit's `[Category]`/`[Property]`, and MSTest's
`[TestProperty]` all surface as `TestCase.Traits`. A custom test logger registered via
`dotnet test --logger purlin` receives each result during the run and writes proof files on
completion, mirroring the reporter model of the pytest/Jest/Vitest plugins (collect in-process,
no second XML-parsing step).

**Setup (consumer projects):** the .NET test platform only discovers loggers from assemblies
whose filename ends with `TestLogger.dll`, so compile `xunit_purlin.cs` into an assembly named
`Purlin.TestLogger` (e.g. `<AssemblyName>Purlin.TestLogger</AssemblyName>`) and reference that
project from your test project so the DLL lands in the test output directory. Run with:

    dotnet test --logger purlin -- RunConfiguration.CollectSourceInformation=true

The `CollectSourceInformation=true` switch is what populates `TestCase.CodeFilePath`, which
RULE-5 records as `test_file`; without it the source path is unavailable.

## Rules

- RULE-1: The .NET marker is the test trait `[Trait("PurlinProof", "feature:PROOF-N:RULE-N:tier")]` (xUnit), equivalently `[Category]`/`[TestProperty]` in NUnit/MSTest; the trait value is a colon-delimited `feature:PROOF-N:RULE-N:tier` string where tier defaults to `"unit"`
- RULE-2: The plugin is a custom `dotnet test` logger (`ITestLoggerWithParameters`) registered via `dotnet test --logger purlin`; it collects results during the run, not by post-parsing a `.trx` file
- RULE-3: Tests without a `PurlinProof` trait are ignored — no proof entry is emitted for them
- RULE-4: A test `Outcome` of `Passed` maps to `status: "pass"`; `Failed` and all other non-skipped outcomes (e.g. `NotExecuted`) map to `status: "fail"`; a `Skipped` test is not recorded at all
- RULE-5: `test_file` is recorded as the source file path relative to the project root (resolved from `TestCase` source information / `CodeFilePath`); `test_name` is the fully-qualified test method name
- RULE-6: On run completion the logger emits proof JSON to the resolved spec directory following the shared feature-scoped overwrite contract

## Proof

- PROOF-1 (RULE-1): Build an xUnit test annotated `[Trait("PurlinProof", "feat:PROOF-1:RULE-1:unit")]`; run `dotnet test --logger purlin`; verify the proof entry has `feature: "feat"`, `id: "PROOF-1"`, `rule: "RULE-1"`, `tier: "unit"` @integration
- PROOF-2 (RULE-2): Run `dotnet test --logger purlin` on a project with one marked test; verify the logger is invoked and produces proof output during the run (no separate `.trx` parse step required) @integration
- PROOF-3 (RULE-3): Run a test with no `PurlinProof` trait; verify no proof entry is emitted for that test @integration
- PROOF-4 (RULE-4): Run a passing marked test and a failing marked test; verify `status: "pass"` and `status: "fail"` respectively; add a `[Fact(Skip="...")]` marked test and verify it is not recorded @integration
- PROOF-5 (RULE-5): Run `dotnet test` from a project root; verify `test_file` is relative (not absolute) and `test_name` is the fully-qualified method name @integration
- PROOF-6 (RULE-6): Pre-seed a proof file with feature B entries; run the logger for feature A; verify feature B entries are preserved and feature A entries are replaced (inherits the proof_common feature-scoped overwrite contract) @integration
