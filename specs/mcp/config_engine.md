# Feature: config_engine

> Requires: security_no_dangerous_patterns
> Scope: scripts/mcp/config_engine.py
> Stack: python/stdlib, json

## What it does

Two-file configuration system that separates shared team defaults (`config.json`, committed) from per-user overrides (`config.local.json`, gitignored). Resolution merges both files so framework updates remain visible while respecting local preferences.

## Rules

- RULE-1: `find_project_root` returns `PURLIN_PROJECT_ROOT` env var when set and the directory exists
- RULE-2: `find_project_root` climbs from the start directory looking for a `.purlin/` marker directory
- RULE-3: `find_project_root` falls back to cwd if no `.purlin/` marker is found in any ancestor
- RULE-4: `resolve_config` merges config.json (base) with config.local.json (overrides) — local keys win for duplicates, base keys are preserved when absent from local
- RULE-5: `resolve_config` returns config.json contents when config.local.json does not exist
- RULE-6: `resolve_config` ignores config.local.json and warns to stderr when it contains invalid JSON, returning config.json only
- RULE-7: `resolve_config` returns empty dict when neither config file exists
- RULE-8: `update_config` writes only to config.local.json, never to config.json
- RULE-9: `update_config` preserves existing keys in config.local.json when adding or updating a key
- RULE-10: `update_config` uses atomic replacement (write to .tmp, then os.replace) to prevent partial writes

## Proof

- PROOF-1 (RULE-1): Set PURLIN_PROJECT_ROOT to a temp dir with .purlin/ inside; call find_project_root; verify it returns that dir without climbing
- PROOF-2 (RULE-2): Create /tmp/a/b/c with .purlin/ in /tmp/a; call find_project_root(start_dir="/tmp/a/b/c"); verify returns /tmp/a
- PROOF-3 (RULE-3): Call find_project_root on a dir with no .purlin/ ancestor; verify returns cwd
- PROOF-4 (RULE-4): Create config.json with {"team": "default", "shared": "base"} and config.local.json with {"shared": "override", "local_only": true}; call resolve_config; verify result is {"team": "default", "shared": "override", "local_only": true} — base key preserved, shared key overridden, local-only key included
- PROOF-5 (RULE-5): Create config.json with {"key": "val"} and no config.local.json; call resolve_config; verify returns {"key": "val"} and config.local.json was NOT created
- PROOF-6 (RULE-6): Create config.local.json with invalid JSON and config.json with {"key": "fallback"}; call resolve_config; verify returns {"key": "fallback"} and stderr contains warning
- PROOF-7 (RULE-7): Call resolve_config in a dir with no config files; verify returns {}
- PROOF-8 (RULE-8): Create config.json with {"team": "v1"}; call update_config(root, "user_pref", "dark"); verify config.json still has {"team": "v1"} unchanged and config.local.json has {"user_pref": "dark"}
- PROOF-9 (RULE-9): Create config.local.json with {"existing": "keep"}; call update_config(root, "added", "new"); verify config.local.json has both {"existing": "keep", "added": "new"}
- PROOF-10 (RULE-10): Call update_config; verify no .tmp file remains and os.replace is used in source
- PROOF-11 (RULE-4): Create config.json with {"report": true, "version": "0.9.0"} and config.local.json with {"pre_push": "strict"}; call resolve_config; verify result has all three keys — framework key "report" visible despite not being in local. This is the key scenario: framework adds a new default, existing user keeps their overrides, new default is visible
- PROOF-12 (RULE-8): Call update_config to set "report" to false; verify config.json is untouched and config.local.json now has "report": false; call resolve_config; verify merged result has "report": false (local override wins)
