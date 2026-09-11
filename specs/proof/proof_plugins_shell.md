# Feature: proof_plugins_shell

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/shell_purlin.sh
> Stack: shell/bash, inline python3 for JSON (no jq dependency)
> Description: The shell proof harness. Sourced by bash test scripts; accumulates entries in
>   memory and writes them on finish. Inherits all shared proof-plugin behavior from proof_common.

## What it does

Provides `purlin_proof` and `purlin_proof_finish` shell functions. Test scripts source the
harness, record results as they run, and call finish once to flush proof files. Only the
shell-specific arg order, tier source, caller-file resolution, and accumulate/finish lifecycle
live here.

## Rules

- RULE-1: `purlin_proof` accepts 5 args: `feature`, `proof_id`, `rule_id`, `status`, `test_name`; tier comes from `PURLIN_PROOF_TIER` env var (default: `"unit"`)
- RULE-2: `test_file` is recorded from `BASH_SOURCE[1]` (the caller's file)
- RULE-3: `purlin_proof_finish` must be called to write proof files — entries are accumulated in memory until then
- RULE-4: After `purlin_proof_finish`, the accumulated entries are cleared (reset for next batch)
- RULE-5: `test_file` is recorded as a project-relative POSIX path and is identical for a given test script however that script was invoked, so neither one machine's home directory nor the caller's choice of an absolute or relative path reaches a committed proof file. `BASH_SOURCE` is resolved to an absolute path when the proof is recorded, then made relative at write time against the project being written to, or failing that against the project the test script itself lives in. A path that resolves outside both is left absolute rather than rewritten with `../` segments

## Proof

- PROOF-1 (RULE-1): Call `purlin_proof "feat" "PROOF-1" "RULE-1" pass "desc"` with `PURLIN_PROOF_TIER=integration`; call `purlin_proof_finish`; verify the proof entry has `tier: "integration"` @integration
- PROOF-2 (RULE-2): Source `shell_purlin.sh` from a test script; call `purlin_proof`; verify `test_file` matches the caller's filename @integration
- PROOF-3 (RULE-3): Call `purlin_proof` twice without calling `purlin_proof_finish`; verify no proof files exist yet. Then call `purlin_proof_finish`; verify files are written @integration
- PROOF-4 (RULE-4): Call `purlin_proof_finish`; verify `_PURLIN_PROOFS` is empty afterwards; call again; verify it's a no-op @integration
- PROOF-5 (RULE-5): Invoke a sourcing test script by absolute path; verify the emitted `test_file` is the project-relative POSIX path with no leading `/` and no home directory. Invoke the same script again by a relative path and verify the emitted `test_file` is byte-identical to the absolute run's, since under the `(feature, tier, test_file)` merge key a difference would accumulate as two entries for one proof rather than collapse. Verify a script outside the project tree keeps an absolute path rather than gaining `../` segments @integration
