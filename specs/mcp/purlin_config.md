# Feature: purlin_config

> Requires: security_no_dangerous_patterns
> Scope: scripts/mcp/purlin_server.py
> Stack: python/stdlib, json

## What it does

MCP tool for reading and writing Purlin configuration. Reads the full config or a single key, and writes single keys atomically.

## Rules

- RULE-1: Reads the full config or a single key, and writes single keys via `update_config`

## Proof

- PROOF-1 (RULE-1): Call with action "write" then action "read"; verify the written value is returned @integration
