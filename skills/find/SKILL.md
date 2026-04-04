---
name: find
description: Search specs by name and show coverage
---

Find a spec by name and display its rule coverage from `sync_status`.

## Usage

```
purlin:find <name>              Find a spec by name
purlin:find                     List all specs
```

## With Argument — Find by Name

1. Search `specs/**/<name>.md` for an exact filename match.
2. If not found, try a substring match against all spec filenames.
3. If still not found:

```
No spec found matching "<name>".

Available specs:
  specs/auth/login.md
  specs/auth/user_profile.md
  specs/webhooks/webhook_delivery.md
  specs/_anchors/design_tokens.md
```

4. If found, read the spec and call `sync_status`. Display the spec's coverage:

```
Found: specs/auth/login.md

# Feature: login

> Requires: security_auth
> Scope: src/auth/login.js, src/auth/login.test.js

Rules: 3 | Proved: 3/3 | Status: READY | vhash=a1b2c3d4

  RULE-1: PASS (PROOF-1 in tests/test_login.py)
  RULE-2: PASS (PROOF-2 in tests/test_login.py)
  RULE-3: PASS (PROOF-3, manual, verified 2026-03-30)
```

## Without Argument — List All

List all specs grouped by category:

```
Specs (12 total):

  auth/ (3 specs)
    login.md — 3/3 rules proved
    user_profile.md — 1/2 rules proved
    permissions.md — no rules

  webhooks/ (2 specs)
    webhook_delivery.md — 2/3 rules proved
    webhook_config.md — READY

  _anchors/ (2 anchors)
    design_tokens.md — 5 rules
    api_contracts.md — 3 rules
```
