# Feature: proof_plugins_c

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/c_purlin.h, scripts/proof/c_purlin_emit.py
> Stack: c/gcc (header-only collector), python3 emitter reading stdin
> Description: The C proof plugin. A header-only collector prints accumulated proofs as JSON to
>   stdout; a python emitter reads stdin and writes proof files. Inherits all shared
>   proof-plugin behavior from proof_common.

## What it does

`c_purlin.h` is included in C test code; `purlin_proof(...)` calls accumulate results and
`purlin_proof_finish()` prints them as JSON. The compiled test's stdout is piped to
`c_purlin_emit.py`, which performs the shared feature-scoped overwrite. Only the C marker
signature and the two-stage emit pipeline live here.

## Rules

- RULE-1: The C marker is `purlin_proof("feature", "PROOF-N", "RULE-N", passed_bool, "test_name", __FILE__, "tier")` called from C source code
- RULE-2: `purlin_proof_finish()` prints accumulated proofs as JSON to stdout; `c_purlin_emit.py` reads stdin and performs feature-scoped overwrite to proof files

## Proof

- PROOF-1 (RULE-1): Compile a C test with `purlin_proof()` calls using gcc; run the binary; verify stdout JSON contains all 7 required fields @integration
- PROOF-2 (RULE-2): Compile and run a C test; pipe stdout to `c_purlin_emit.py`; verify proof file is written to spec directory with correct entries @integration
- PROOF-3 (RULE-1): Compile a C test where the `passed_bool` is false; run and pipe to emitter; verify `status: "fail"` in the proof file @integration
