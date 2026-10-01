> Format-Version: 16

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
| `<signer-slug>` | the signer's email local part, lowercased, every non-alphanumeric character replaced by `-`; then `-2`, `-3` and on where `HEAD` holds that name for another signer |

One file per signer per version, so two signers never conflict. Two signers
whose addresses differ and whose local parts are the same each keep a file:
after `jane@acme.com` signs as `jane.json`, `jane@labs.org` signs as
`jane-2.json`, and the first file is left as it was. Addresses are compared
with their case set aside. A signer who already signed the committed package
is refused; a signer whose earlier sign-off was over another package for the
same version writes over it.

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
      "audit": {"strong": 17, "weak": 1, "spot_checked": 0, "out_of_date": 0,
                "not_audited": 1}
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
| `package_hash` | string | the package's own `fingerprint` field, as `package_format.md` gives it: the fingerprint computed over the package `HEAD` holds for the version once the sign-off is committed |
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
| `overview` | object | the overview's numbers: `systems`, one `{os, rules, passing, hand_checks}` per operating system the package holds results for, in the order `linux`, `macos`, `windows`; and `audit`, `{strong, weak, spot_checked, out_of_date, not_audited}` as the package counts them, or null where the audit read no rule. The walk prints them as `  The audit: 34 strong, 4 weak, 2 spot-checked.`, a count of zero left out but `strong` |
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

Where git cannot write the tag, the commit stands and `purlin:sign` prints
`No tag: git could not write signed/<version>: <git's reason>. Fix that, then
run purlin:sign again to write it.` and exits 1. The next `purlin:sign` writes
the tag on the commit that added the package, while the code has not changed
since. A signer who already signed gets the tag alone and no second sign-off;
`purlin:sign --show` then prints `signed/<version> is not written yet: <signer>
signed <version> at <sha7>. Run purlin:sign to write the tag.`

## When a sign-off counts

A sign-off counts when the last commit that touched its file is signed, that
signature verifies over the commit, and its `package_hash` equals the
fingerprint computed over the package `HEAD` holds for its version. The key
is not compared with the signer.

A sign-off is read as `HEAD` holds it. The files are listed and read from
`HEAD`'s tree: a file git does not track is no sign-off, and an edit that is
not committed is not read, so its note is not shown. A note is shown only
from a sign-off that counts.

The package's fingerprint is computed from its content, as
`package_format.md` gives it; the `fingerprint` field the file stores is not
taken on trust. A package changed after it was signed no longer matches, so
every sign-off of it stops counting, and a later sign-off is refused with
`No sign-off: .purlin/evidence/package/<version>.json does not match its
fingerprint: <why>. Restore it as it was signed, or name a new version:
purlin:sign --version <version>.`

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
| `package_hash` is not the fingerprint computed over the committed package, or that package does not match its own fingerprint | `it signs another evidence package than the one committed` |

## Where the status reads `signed`

The status reads `signed <version>` only where `signed/<version>` names a
commit that holds the package for that version and a sign-off of it counts.
The newest such tag on `HEAD` or an ancestor of it answers. A tag that does
not is passed over, with one warning, and the status reads `not signed`
where no tag is left:

| The tag | The warning |
|---|---|
| names a commit that holds no package for its version, as a tag written by hand does | `signed/<version>: it names a commit that holds no evidence package for <version>, so it is not a sign-off. Delete it: git tag -d signed/<version>.` |
| names a commit that holds the package, and no sign-off of it counts | `signed/<version>: no sign-off of <version> counts: <the reason above, or HEAD holds none>. Restore the files as they were signed, or sign this code: purlin:sign --version <version>.` |

`references/evidence_and_signoff.md` holds when a sign-off counts and what
the tag `signed/<version>` means.
