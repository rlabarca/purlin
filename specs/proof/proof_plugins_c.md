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
`c_purlin_emit.py`, which performs the shared write-scoped overwrite. Only the C marker
signature and the two-stage emit pipeline live here.

## Rules

- RULE-1: The C marker is `purlin_proof("feature", "PROOF-N", "RULE-N", passed_bool, "test_name", __FILE__, "tier")` called from C source code
- RULE-2: `purlin_proof_finish()` prints accumulated proofs as JSON to stdout; `c_purlin_emit.py` reads stdin and performs write-scoped overwrite to proof files

## Proof

- PROOF-1 (RULE-1): Compile with gcc and run a C test calling `purlin_proof("math_ops", "PROOF-1", "RULE-1", sum == 5, "test_addition", "test_math.c", "unit")`; verify the matching entry printed on stdout equals, field for field with nothing else in it, the arguments it was given: `feature: "math_ops"`, `id: "PROOF-1"`, `rule: "RULE-1"`, `status: "pass"` for the true `passed_bool`, `test_name: "test_addition"`, `test_file: "test_math.c"`, `tier: "unit"`, plus the transport-only `platforms: ""` that `c_purlin_emit.py` consumes to pick the file name @integration
- PROOF-2 (RULE-2): Compile and run a C test whose `purlin_proof_finish()` prints its proofs as JSON on stdout and pipe that stdout to `c_purlin_emit.py`; verify `specs/auth/login.proofs-unit.json` is written holding the single entry `PROOF-1`/`RULE-1` with `status: "pass"`. Separately, feed `c_purlin_emit.py` a stdin payload for feature `arithmetic` against an `arithmetic.proofs-unit.json` pre-seeded with a `geometry` entry (`test_geo.c`/`test_area`) and a stale `arithmetic` entry (`test_old.c`/`old_test`, `status: "fail"`); verify the rewritten file still holds the `geometry` entry and holds exactly one `arithmetic` entry, `test_name: "test_addition_v2"` with `status: "pass"`, so the emitter performs the write-scoped overwrite instead of truncating the file @integration
- PROOF-3 (RULE-1): Compile a C test where the `passed_bool` is false; run and pipe to emitter; verify `status: "fail"` in the proof file @integration
