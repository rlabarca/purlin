# Feature: proof_plugins_sql

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/sql_purlin.sh
> Stack: sql/sqlite3 (shell driver + inline python3)
> Description: The SQL proof plugin. Runs `-- @purlin`-marked test blocks against sqlite3 and
>   maps PASS/FAIL output to status. Inherits all shared proof-plugin behavior from proof_common.

## What it does

A bash driver that parses `-- @purlin` comment markers from a `.sql` file, runs each marked
test block through sqlite3, and maps the block's output to pass/fail before writing proof
files. Only the SQL comment marker syntax and the PASS/FAIL output convention live here.

## Rules

- RULE-1: The SQL marker is `-- @purlin feature PROOF-N RULE-N [tier]` as a comment line preceding the test block
- RULE-2: Each SQL test block must produce output starting with `PASS` or `FAIL` when executed against sqlite3; any other output or error maps to `status: "fail"`

## Proof

- PROOF-1 (RULE-1): Create a SQL file with `-- @purlin` markers; run `sql_purlin.sh`; verify proof entries match the marker fields @integration
- PROOF-2 (RULE-2): Create a SQL test block that outputs `PASS`; verify `status: "pass"`. Create one that outputs `FAIL`; verify `status: "fail"` @integration
