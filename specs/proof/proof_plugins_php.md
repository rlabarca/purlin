# Feature: proof_plugins_php

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/phpunit_purlin.php
> Stack: php (standalone runner, docblock annotations)
> Description: The PHP proof runner. Runs each `@purlin`-annotated function individually and
>   maps thrown exceptions to fail. Inherits all shared proof-plugin behavior from proof_common.

## What it does

A standalone PHP script that parses `@purlin` docblock annotations from a test file, executes
each annotated function, and maps the outcome to pass/fail before writing proof files. Only the
PHP docblock marker syntax and the per-function exception-to-status mapping live here.

## Rules

- RULE-1: The PHP marker is a `/** @purlin feature PROOF-N RULE-N [tier] */` docblock annotation before the test function
- RULE-2: The PHP plugin runs each annotated function individually; an unhandled exception maps to `status: "fail"`, no exception maps to `status: "pass"`

## Proof

- PROOF-1 (RULE-1): Create a PHP test with `@purlin` docblock; run `phpunit_purlin.php`; verify proof entry has correct feature, id, rule from the docblock @integration
- PROOF-2 (RULE-2): Create a PHP test that throws an exception; run plugin; verify `status: "fail"`. Create one that doesn't throw; verify `status: "pass"` @integration
