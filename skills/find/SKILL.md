---
name: find
description: Find a spec by name and show its rules' cells
---

Locate a spec and show what stands behind each of its rules. With no argument, list every
spec. This skill writes nothing.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:find <name>              Find one spec by name or by part of a name
purlin:find                     List every spec, grouped by category
```

Plain language reaches the same place: "where is the login spec", "what specs do we have".

## With a name

1. Look for `specs/**/<name>.md`.
2. If nothing matches exactly, match the name as a substring of a spec filename.
3. If several match, list them and ask which one.
4. If nothing matches, list every spec and stop.

When one spec matches, read it, call `sync_status`, and print the header, the rules and the
cells of each. One pill per cell the gate creates, in the order spec, passed, strong, signed:

```
Found: specs/auth/login.md
# Feature: login
> Description: People sign in with an email address and a password.
> Scope: src/auth/login.js, src/auth/login.test.js

8 rules, 6 meet the gate signed   strength 81%
  RULE-1  high    ready  passed  strong  signed      PROOF-1  tests/test_login.py::test_rejects_bad_password
  RULE-2  medium  ready  passed  strong  unsigned    PROOF-2  tests/test_login.py::test_locks_after_five
  RULE-3  low     ready  no test                     PROOF-3  no test carries this marker
```

Show the risk and the origin only when the spec carries them; under the `passed` gate both are
optional and a column of blanks says nothing.

## With no name

Group by category and give one line per spec:

```
Specs (12):
  auth/ (3)
    login              8 rules, 6 meet the gate, strength 81%
    permissions        4 rules, all drafted
  _anchors/ (2)
    design_tokens      5 rules, pinned 4 commits behind
```

## Name the next step

End with one line, for the spec you showed or for the weakest one you listed:

| What you found | The line to print |
|----------------|-------------------|
| A rule's spec status is `drafted` | `→ Run: purlin:spec <feature>` |
| A rule reads `no test` | `→ Run: purlin:build <feature>` |
| A rule reads `passed` with no record under `strong` or above | `→ Run: purlin:audit <feature>` |
| A rule is weak | `→ Run: purlin:build <feature>` |
| A rule needs a person, is unsigned or is stale | `→ Run: purlin:sign <feature>` |
| An anchor pin is behind | `→ Run: purlin:anchor sync <name>` |
| Nothing outstanding | `→ Nothing to do here.` |
