> Format-Version: 14

# Signature Format

A sign-off is one person's signature over a release's evidence package. It is
a committed file, added in a signed commit, carrying the package's
`fingerprint`, what the signer was shown in the sign-off walk and every note
they typed. Who signed which package and when is in git history. A run writes
no sign-off, ever: every file in the folder was written by a person, through
`purlin:sign`.

## File name

```
.purlin/evidence/package/<version>.signoffs/<signer-slug>.json
```

| Part | What it is |
|---|---|
| `<version>` | the version of the package it signs, `.purlin/evidence/package/<version>.json` beside it |
| `<signer-slug>` | the signer's email local part, lowercased, every non-alphanumeric character replaced by `-` |

One file per signer per version, so two signers never conflict. A signer who
already signed the committed package is refused; a signer whose earlier
sign-off was over another package for the same version writes over it.

## Fields

```json
{
  "schema": "purlin-signoff/1",
  "version": "1.2.0",
  "package": ".purlin/evidence/package/1.2.0.json",
  "package_hash": "<the package's fingerprint field>",
  "commit": "<the commit the package describes>",
  "signer": "quinn.qa@labconnect.example",
  "signer_name": "Quinn QA",
  "key_fingerprint": "SHA256:vrDM+WX4Ab76HvBbinAXOjKHP5EQjT33PqbnJT6Xy4Q",
  "timestamp": "2026-10-02T09:14:00Z",
  "shown": {
    "overview": {"rules": 40, "passing": 38, "hand_checks": 2, "strong": 30,
                 "weak": 2, "not_audited": 6, "systems": ["linux", "windows"]},
    "one_by_one": [{"feature": "sample_age", "rule": "RULE-1", "why": "weak"}],
    "in_list": [{"feature": "sample_age", "rule": "RULE-2"}],
    "list_opened": true
  },
  "notes": [{"feature": "accession_screen", "rule": "RULE-1",
             "kind": "hand check",
             "note": "the tube colour is red on an expired sample"}]
}
```

Every field is REQUIRED, in this order.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-signoff/1` for this format version |
| `version`, `package` | string, string | the version signed, and the package file's path, `/` separated |
| `package_hash` | string | the package's own `fingerprint` field, as `package_format.md` gives it |
| `commit` | string | the full sha the package describes, its own `commit` field |
| `signer` | string | the signer's email as git holds it |
| `signer_name` | string or null | git's `user.name` |
| `key_fingerprint` | string | `SHA256:` and the unpadded base64 of the sha256 of the SSH key the signer signs with, as `ssh-keygen -l` prints it |
| `timestamp` | string | ISO 8601 UTC with `Z`, when the file was written |
| `shown` | object | what the walk showed the signer. See below |
| `notes` | array | every note typed, in the order typed: `{feature, rule, kind, note}`, `kind` being `hand check` or `note` |

`shown`:

| Field | Type | What it holds |
|---|---|---|
| `overview` | object | the overview's numbers: `rules`, `passing` (rules that pass their tests, hand checks aside), `hand_checks`, `strong`, `weak`, `not_audited` (each over the rules that are not hand checks), and `systems`, the operating systems the package holds results for |
| `one_by_one` | array | every stop in the order walked: `{feature, rule, why}`, `why` being `hand check`, `weak`, `not audited` or `strong` |
| `in_list` | array | every rule the audit found strong that the signer did not walk, `{feature, rule}`, whether or not the list was opened |
| `list_opened` | bool | whether the signer asked to see the strong list |

The file records what was shown and what was typed, and no answer word: it
holds no judgment. A hand check's note is the line the signer typed at its
stop; a `note` is one typed at any other stop.

## The commit and the tag

`purlin:sign` adds the file in one signed commit whose subject is
`sign(<version>): <signer email>`, carrying that file alone. The first
sign-off of a version writes the signed tag `signed/<version>` on its commit;
a later one adds its file after the tag, which does not move.

## When a sign-off counts

A sign-off counts when the last commit that touched its file is signed, that
signature verifies over the commit, and its `package_hash` equals the
`fingerprint` of the package HEAD holds for its version. The key is not
compared with the signer.

The file is tracked, and the last commit that touched it carries a `gpgsig`
header (`gpgsig-sha256` in a SHA-256 repository) among its headers. An SSH
signature verifies when `ssh-keygen -Y check-novalidate -n git` accepts it
over the commit object without that header; it reads the key the signature
carries, so it needs no list of allowed signers, and a key deleted since
still verifies. Any other signature verifies when `git verify-commit` exits
0. The key is not checked against any list, the commit's author is not
compared with the signer, and the answer is the same at every gate.

| What is read | The reason it does not count |
|---|---|
| The last commit touching the file carries no signature header, or the file is not tracked | `the commit that added it is not signed` |
| That commit carries a signature that does not verify | `the signature on the commit that added it does not verify` |
| `package_hash` is not the committed package's `fingerprint` | `it signs another evidence package than the one committed` |

`references/hard_gates.md` holds the gates and what the tag `signed/<version>`
means.
