# Feature: proof_plugins_vitest

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/vitest_purlin.ts
> Stack: typescript/vitest, custom reporter (onFinished(files) tree walk, Vitest 2.x to 4.x)
> Description: The Vitest TypeScript reporter. Reuses the Jest marker syntax in test titles and
>   collects proofs by walking the onFinished(files) file/suite/test task tree recursively on
>   run completion. The marker syntax it shares with Jest and that Vitest-specific tree walk and
>   state mapping are all this spec adds; it inherits every other proof-plugin behavior from
>   proof_common.

## Rules

- RULE-1: The TypeScript Vitest reporter uses the same `[proof:feature:PROOF-N:RULE-N:tier]` marker syntax in test titles as the Jest reporter
- RULE-2: The Vitest reporter collects proofs by recursively walking the file/suite/test tree passed to `onFinished(files)`, the stable Vitest 2.x to 4.x reporter API. For each task of type `test`/`custom` it reads `task.name`, maps `task.result.state === "pass"` to `"pass"` (all other terminal states to `"fail"`), skips tasks with no terminal result (`skip`/`todo`/unrun), and resolves `test_file` from the file task's `filepath`. It does not use `onTaskUpdate` (whose pack shape changed in Vitest 2 and silently yielded zero proofs)

## Proof

- PROOF-1 (RULE-1): Drive `vitest_purlin.ts` `onFinished` with a test task whose name contains `[proof:feat:PROOF-1:RULE-1:integration]`; verify the marker parses into `feature: "feat"`, `id: "PROOF-1"`, `rule: "RULE-1"`, `tier: "integration"`: identical fields to the Jest reporter's parsing of the same marker @integration
- PROOF-2 (RULE-2): Load `vitest_purlin.ts` (compiled with tsc, or run directly via Node TypeScript type-stripping); drive its `onFinished(files)` with a synthetic Vitest 2.x+ task tree (a file suite task carrying `filepath` and nested `test` tasks whose names contain `[proof:...]` markers and whose `result.state` is `pass`/`fail`/`skip`); verify the emitted proof JSON has all 7 fields, that `state: pass` → `status: "pass"` while `state: fail` → `status: "fail"`, that a `skip` task is not recorded, and that `test_file` is resolved from the file task's `filepath` @integration
