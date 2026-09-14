---
name: rename
description: Rename a feature across specs, tests, approvals and records
---

Rename a feature everywhere Purlin wrote its name, in one commit. A name left behind points a
live test, an approval or a record at a spec that no longer exists.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:rename <old-name> <new-name>
```

Plain language reaches it too: "rename login to authentication".

## What carries the name

| Where | What changes |
|-------|--------------|
| `specs/<category>/<old>.md` | The file name, and `# Feature: <old>` inside it |
| `> Requires:` in other specs | The old entry, matched whole between commas |
| Proof markers in test code | Every marker form in `references/formats/proofs_format.md#feature-name-token` |
| `specs/<category>/<old>.approvals/` | The directory name; the files inside are unchanged |
| `.purlin/records/<old>/` | The directory name; the records inside are unchanged |
| `designs/<old>/` | The directory name, and the `> Source:` line of any anchor naming it |

Proof files are runtime (`.purlin/runtime/proofs/`) and the next run regenerates them, so they
are not renamed. Nothing outside these places is touched: a test function called
`test_login_valid` keeps its name, and so does every comment. An approval binds the hashes of
the rule text, the proof text and the test body, none of which a rename changes, and a record
names the feature in its path only, so approvals and records both survive it.

## Steps

1. **Find the spec.** No match: stop with `No spec found for '<old-name>'.` Several matches:
   list them and ask. An anchor carrying a `> Source:` is owned elsewhere: stop with
   `Cannot rename '<old-name>': it is pinned from <source>. Rename it there and sync.`
2. **Show what will change** and wait for an answer. Do not proceed on your own.

```
rename: login → authentication
  specs/auth/login.md            → specs/auth/authentication.md
  specs/auth/login.approvals/    → specs/auth/authentication.approvals/  (6 files)
  .purlin/records/login/         → .purlin/records/authentication/       (3 records)
  tests/test_login.py            5 markers
  specs/auth/session.md          1 requires line
  [y] proceed   [n] cancel
```

3. **Move the files** with `git mv`, directories included, so history follows them.
4. **Rewrite the markers**, one pass per row of the proof-marker table, not only the languages
   this project happens to use.
5. **Rewrite `# Feature:` and every `> Requires:` entry.** Match the old name whole: renaming
   `login` must leave `login_oauth` alone.
6. **Call `sync_status`.** Any unresolved reference it reports is a miss; fix it before the
   commit rather than reporting a rename that half happened.
7. **Commit** as `chore: rename <old-name> to <new-name>`, per
   `references/commit_conventions.md`.

## Name the next step

| What sync_status shows afterwards | The line to print |
|-----------------------------------|-------------------|
| Everything resolved | `→ Run: purlin:test <new-name>` |
| A marker still names the old feature | `→ Fix the marker in <file>, then re-run.` |
| A record or approval was left behind | `→ Move it by hand, then re-run.` |
