> Format-Version: 13

# Signature Format

A signature is one person's attestation that a rule, its proof, its test, the
code its feature lists and what the audit found belong together, over the
results of the machine each system's tests ran on. It is a committed file, so
who signed what and when is in git history. A run writes no signature, ever:
every file in the directory was written by a person.

## File name

```
specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json
```

| Part | What it is |
|---|---|
| `<feature>` | the spec that holds the rule, matching `specs/<category>/<feature>.md` |
| `<RULE-N>` | the rule the signature is for |
| `<hash8>` | the first eight characters of `signed_hash` |
| `<signer-slug>` | the signer's email local part, lowercased, every non-alphanumeric character replaced by `-` |

One signature is one file, so two signatures never conflict and a batch of
forty adds forty files in one commit.

## What a signature is made over

`signed_hash` is `sha256` over seven lines, joined by a newline:

| Line | What it holds |
|---|---|
| 1 | `applies_to`, the spec that holds the rule |
| 2 | `rule_hash`: the rule text, its whitespace normalised, so reflowing a long line leaves it as it was |
| 3 | `proof_hash`: the proof descriptions of that rule, in order, normalised the same way |
| 4 | `test_hash`: the test files backing those proofs, each with the test's name and the file's blob id. The tests are the ones the feature's current evidence sections list, every operating system and both sources together, so every checkout reads the same hash |
| 5 | `code_hash`: the files the `> Scope:` of `applies_to` names, each with its path and blob id; for an anchor, every file git tracks but Purlin's own records, as `evidence_format.md` gives them |
| 6 | `audit_hash`: what the audit found, the feature's test strength from `audit.mutation`, the `verdict` of the audit entry for the rule's current hashes and its `findings` sorted; `sha256` of the empty string where no such entry exists |
| 7 | `machines`, written as `os=machine` pairs, sorted and joined with `,` |

A field with no value reads as the empty string. Where `test_hash_kind` is
`manual`, a hand check, lines 4 to 7 are each the empty string, so the
signature is made over lines 1 to 3 alone. The file still records every
field. Nothing that moves on its
own is in it: no timestamp, no commit id, no path, and not the model that
audited, so running the same audit again over the same code changes nothing.

`machines` maps each system whose results the rule's passed cell read,
`windows`, `macos` or `linux`, to the machine those results came from: the
host's name for a person's own run, and `remote runner, <Windows|macOS|Linux/Unix>`
for a remote runner, so a second remote run names the same machine. The
machine the signature itself was made on is not part of it.

An anchor's rule is signed once, over every file of the project but Purlin's
own records, so any change to the project ends that signature, unless it is
a hand check.

A hand check's signature is made over the rule's and its proofs' wording
alone: a change to the code, a test or the machines does not end it, and a
change to that wording does. Every other signature covers the rule's test
files whole and the machine each system's results came from, so editing
another test in the same file, or running the same tests on another
computer, ends it.

A rule of a pinned anchor that does not apply to this project is signed with
`purlin:sign <anchor> RULE-N --does-not-apply "<why>"`. The signature is made
over the same seven lines as any other and carries the reason in
`does_not_apply`, which, like `note`, is outside `signed_hash`: the signed
commit is what holds it. No other rule is signed this way.

`test_hash_kind` says what line 4 was taken from: `file` for a test file
version control tracks, `manual` for a proof with no test at all, and `none`
for a rule with nothing behind it yet. A rule with a `@manual` proof and no
proof tied to a test reads `manual`; a rule mixing a hand check with a tested
proof reads `file` and is signed over all seven lines.

## Fields

```json
{
  "schema": "purlin-signature/2",
  "feature": "login",
  "rule": "RULE-3",
  "applies_to": "login",
  "signed_hash": "9f2c7a1e5b8d4c6f...",
  "rule_hash": "4b1f...",
  "proof_hash": "c07a...",
  "test_hash": "1d93...",
  "code_hash": "77e0...",
  "audit_hash": "e3b0c442...",
  "machines": {"macos": "jane-laptop"},
  "signer": "jane@acme.com",
  "signer_name": "Jane",
  "key_fingerprint": "SHA256:vrDM+WX4Ab76HvBbinAXOjKHP5EQjT33PqbnJT6Xy4Q",
  "test_hash_kind": "file",
  "note": null,
  "does_not_apply": null,
  "timestamp": "2026-09-13T12:00:00Z",
  "gate": "signed",
  "evidence": ".purlin/evidence/local/login.json"
}
```

REQUIRED: `schema`, `feature`, `rule`, `applies_to`, `signed_hash`,
`rule_hash`, `proof_hash`, `test_hash`, `code_hash`, `audit_hash`, `machines`,
`signer`, `key_fingerprint`, `timestamp`. Every other field is OPTIONAL.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-signature/2` for this format version |
| `feature` | string | the spec that holds the rule, which owns it |
| `rule` | string | `RULE-N` |
| `applies_to` | string | the spec that holds the rule, the same as `feature` |
| `signed_hash` | string | the hash over the seven lines above, lines 4 to 7 empty for a hand check, of which the file name carries eight characters |
| `rule_hash` | string | line 2 |
| `proof_hash` | string | line 3 |
| `test_hash` | string | line 4 |
| `code_hash` | string | line 5 |
| `audit_hash` | string | line 6 |
| `machines` | object | line 7, `{os: machine}`; `{}` where no result named a machine |
| `signer` | string | the signer's email as git holds it |
| `signer_name` | string or null | git's `user.name` |
| `key_fingerprint` | string | `SHA256:` and the unpadded base64 of the sha256 of the SSH key the signer signs with, as `ssh-keygen -l` prints it |
| `test_hash_kind` | string | `file`, `manual` or `none` |
| `note` | string or null | what the signer saw, for a `@manual` proof; null where none was given |
| `does_not_apply` | string or null | the reason, as one line, a pinned anchor's rule does not apply to this project; null or absent for any other signature |
| `timestamp` | string | ISO 8601 UTC with `Z` |
| `gate` | string | the gate in force when the signature was written: `passed`, `strong` or `signed` |
| `evidence` | string or null | the feature's evidence file the signature rests on, the `local` one where both sources have one |

## Current

A signature is **current** while `signed_hash`, taken again from the rule as
it now stands in the spec that holds it, equals the one stored. Whether the
rule is a hand check is read from the rule as it now stands, not from the
signature. Line 7 is taken from the rule's machines restricted to the systems
the signature's own `machines` names:

| What changed | What happens |
|---|---|
| The rule, its proof, its test, the code, or what the audit found | the signature is no longer current |
| A system the signature names now has results from another machine | the signature is no longer current |
| A system the signature names has no results any more | the signature is no longer current |
| Results arrive from a system the signature does not name | the signature is still current |
| The same machine runs the tests again, with nothing changed | the signature is still current |
| A hand check's signature: its rule's or a proof's wording changed | no longer current |
| A hand check's signature: the code, a test or the machines changed | still current |

A signature that is no longer current stays on disk and is read back; its
rule returns to `to sign`. The status and every test run print one line
naming the rule, the signer and why it ended.

## When a signature counts

A signature counts when the commit that added it is signed and that
signature verifies over the commit. The key is not compared with the signer.

The file is tracked, and the last commit that touched it carries a `gpgsig`
header (`gpgsig-sha256` in a SHA-256 repository) among its headers. An SSH
signature verifies when `ssh-keygen -Y check-novalidate -n git` accepts it
over the commit object without that header; it reads the key the signature
carries, so it needs no list of allowed signers, and a key deleted since
still verifies. Any other signature verifies when `git verify-commit` exits
0. The key is not checked against any list, the commit's author is not
compared with the signer, and the answer is the same at every gate. A
signature counts on whatever commit carries it, on any branch.

| The last commit touching the file | The reason it does not count |
|---|---|
| carries no signature header, or the file is not tracked | `the commit that added it is not signed` |
| carries a signature that does not verify | `the signature on the commit that added it does not verify` |

`references/hard_gates.md` holds the gates and what the tag `signed/<version>`
means.
