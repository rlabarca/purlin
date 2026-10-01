> Format-Version: 15

# Signature Format

A sign-off is one person's signature over a version's evidence package. It is
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
  "version": "0.1.0",
  "package": ".purlin/evidence/package/0.1.0.json",
  "package_hash": "<the package's fingerprint field>",
  "commit": "<the commit the package describes>",
  "signer": "quinn.qa@labconnect.example",
  "signer_name": "Quinn QA",
  "key_fingerprint": "SHA256:vrDM+WX4Ab76HvBbinAXOjKHP5EQjT33PqbnJT6Xy4Q",
  "timestamp": "2026-10-02T09:14:00Z",
  "shown": {
    "overview": {
      "systems": [{"os": "linux", "rules": 19, "passing": 19,
                   "hand_checks": 1}],
      "audit": {"strong": 17, "weak": 1, "not_audited": 1}
    },
    "runs": [{"at": "2026-10-01T12:17:13Z", "by": "dana.dev@labconnect.example",
              "commit": "<40 hex>", "machine": "dana-laptop", "os": "linux",
              "rules": 19, "source": "local"}],
    "hand_checks": [{"feature": "accession_screen", "rule": "RULE-1"}],
    "audit_list_opened": false
  },
  "notes": [{"feature": "accession_screen", "rule": "RULE-1",
             "note": "the tube colour is red on an expired sample"}]
}
```

Every field is REQUIRED, in this order.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-signoff/1` |
| `version`, `package` | string, string | the version signed, and the package file's path, `/` separated |
| `package_hash` | string | the package's own `fingerprint` field, as `package_format.md` gives it: the fingerprint of the package `HEAD` holds for the version once the sign-off is committed |
| `commit` | string | the full sha the package describes, its own `commit` field |
| `signer` | string | the signer's email as git holds it |
| `signer_name` | string or null | git's `user.name` |
| `key_fingerprint` | string | `SHA256:` and the unpadded base64 of the sha256 of the SSH key the signer signs with, as `ssh-keygen -l` prints it |
| `timestamp` | string | ISO 8601 UTC with `Z`, when the file was written |
| `shown` | object | what the walk showed the signer. See below |
| `notes` | array | every note typed, one per hand check walked, in the order walked: `{feature, rule, note}`. An empty answer is recorded as `no note` |

`shown`:

| Field | Type | What it holds |
|---|---|---|
| `overview` | object | the overview's numbers: `systems`, one `{os, rules, passing, hand_checks}` per operating system the package holds results for, in the order `linux`, `macos`, `windows`; and `audit`, `{strong, weak, not_audited}` as the package counts them, or null where the audit read no rule |
| `runs` | array | the package's `runs`, as the walk's opening lines named them |
| `hand_checks` | array | every hand check walked, in the order walked: `{feature, rule}` |
| `audit_list_opened` | bool | whether the signer asked to see the audit's findings |

The file records what was shown and what was typed, and no answer word: it
holds no judgment.

## The commit and the tag

`purlin:sign` adds the file in one signed commit whose subject is
`sign(<version>): <signer email>`. The first sign-off of a version carries
the package, `.purlin/evidence/package/<version>.json`, and its own file in
that commit, and writes the signed tag `signed/<version>` on it, with the
message `Signed <version>.`, a blank line and `Commit: <the package's
commit>`. A later sign-off carries its own file alone, after the tag, which
does not move.

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
0. The key is not checked against any list, and the commit's author is not
compared with the signer.

| What is read | The reason it does not count |
|---|---|
| The last commit touching the file carries no signature header, or the file is not tracked | `the commit that added it is not signed` |
| That commit carries a signature that does not verify | `the signature on the commit that added it does not verify` |
| `package_hash` is not the committed package's `fingerprint` | `it signs another evidence package than the one committed` |

`references/evidence_and_signoff.md` holds when a sign-off counts and what
the tag `signed/<version>` means.
