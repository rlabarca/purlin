> Format-Version: 11

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
| 1 | `applies_to`, the feature the rule is signed in |
| 2 | `rule_hash`: the rule text, its whitespace normalised, so reflowing a long line leaves it as it was |
| 3 | `proof_hash`: the proof descriptions of that rule, in order, normalised the same way |
| 4 | `test_hash`: the test files backing those proofs, each with the test's name and the file's blob id. The tests are the ones the feature's current evidence sections list, every operating system and both sources together, so every checkout reads the same hash |
| 5 | `code_hash`: the files the `> Scope:` of `applies_to` names, each with its path and blob id |
| 6 | `audit_hash`: what the audit found, the feature's test strength from `audit.mutation`, the `verdict` of the audit entry for the rule's current hashes and its `findings` sorted; `sha256` of the empty string where no such entry exists |
| 7 | `machines`, written as `os=machine` pairs, sorted and joined with `,` |

A field with no value reads as the empty string. Nothing that moves on its
own is in it: no timestamp, no commit id, no path, and not the model that
audited, so running the same audit again over the same code changes nothing.

`machines` maps each system whose results the rule's passed cell read,
`windows`, `macos` or `linux`, to the machine those results came from: the
host's name for a person's own run, and `remote runner, <Windows|macOS|Linux/Unix>`
for a remote runner, so a second remote run names the same machine. The
machine the signature itself was made on is not part of it.

An anchor's rule is signed once in each feature it applies to. Each file
carries that feature in `applies_to` and is made over that feature's code, so
a change to one feature's files ends that one signature alone.

`test_hash_kind` says what line 4 was taken from: `file` for a test file
version control tracks, `manual` for a proof with no test at all, and `none`
for a rule with nothing behind it yet.

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
| `applies_to` | string | the feature the rule is signed in: the owner, or for an anchor's rule the feature that uses it |
| `signed_hash` | string | the hash over the seven lines above, of which the file name carries eight characters |
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
| `timestamp` | string | ISO 8601 UTC with `Z` |
| `gate` | string | the gate in force when the signature was written: `passed`, `strong` or `signed` |
| `evidence` | string or null | the feature's evidence file the signature rests on, the `local` one where both sources have one |

## Current

A signature is **current** while `signed_hash`, taken again from the rule as
it now stands in the feature it applies to, equals the one stored. Line 7 is
taken from the rule's machines restricted to the systems the signature's own
`machines` names:

| What changed | What happens |
|---|---|
| The rule, its proof, its test, the code, or what the audit found | the signature is no longer current |
| A system the signature names now has results from another machine | the signature is no longer current |
| A system the signature names has no results any more | the signature is no longer current |
| Results arrive from a system the signature does not name | the signature is still current |
| The same machine runs the tests again, with nothing changed | the signature is still current |

A signature that is no longer current stays on disk and is read back; its
rule returns to `to sign`. No message is printed for it.

## When a signature counts

A current signature counts when the last commit that touched its file is
signed: the commit carries a `gpgsig` or `gpgsig-sha256` header. The file is
tracked, and nothing else is read. The key is not checked against any list,
the commit's author is not compared with the signer, and the answer is the
same at every gate. A signature counts on whatever commit carries it, on any
branch. Where the commit is not signed the reason reads
`the commit that added it is not signed`.

`references/hard_gates.md` holds the gates and what the tag `signed/<version>`
means.
