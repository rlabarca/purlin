> Format-Version: 10

# Signature Format

A signature is one named person's attestation that a rule, its proof, its test
and the audit that read them belong together. It is a committed file, so who
signed what and when is in git history. CI writes no signature, ever: every
file in the directory was written by a person.

## File name

```
specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json
```

| Part | What it is |
|---|---|
| `<feature>` | the spec that holds the rule, matching `specs/<category>/<feature>.md` |
| `<RULE-N>` | the rule the signature is for |
| `<hash8>` | the first eight characters of the triple the signature binds |
| `<signer-slug>` | the signer's email local part, lowercased, every non-alphanumeric character replaced by `-` |

One signature is one file, so two signatures never conflict and a batch of
forty adds forty files in one commit.

## The triple, and the audit beside it

What a signature binds is hashes, not the files they came from:

| Letter | What it hashes |
|---|---|
| R | the rule text, its tags stripped and its whitespace normalised, so reflowing a long line does not stale the signature |
| P | the proof descriptions of that rule, in order, normalised the same way |
| T | the test files backing those proofs, each with the test's name and the file's blob id. The tests are the ones the feature's current evidence sections list, every operating system and both sources together, so every checkout reads the same T; where no section is current, every section's list answers, so a code change alone does not move T |
| A | what the audit found: the feature's test strength from `audit.mutation`, the `verdict` of the audit entry for the rule's current R, P and T, and its `findings` sorted. `sha256` of the empty string where no such entry exists |

The triple hash is `sha256` over R, P and T, one per line, and the first eight
characters of it name the file. A is kept and compared beside the triple
rather than folded into it, because a rule no audit has reached has no audit
entry to take A from.

A is what locks the audit in. A signature says the test proves the proof, and
what the signer read before saying so was what the audit found: the strength
and the AI audit's findings. A re-audit that finds something different is a
new answer to that question, so the signature goes stale and a person looks
again. Nothing that moves on its own is hashed: no timestamp, no commit id, no
path, so running the same audit again over the same code changes nothing.

`test_hash_kind` says what T was taken from: `file` for a test file version
control tracks, `manual` for a proof with no test at all, and `none` for a rule
with nothing behind it yet.

## Fields

```json
{
  "schema": "purlin-signature/1",
  "feature": "login",
  "rule": "RULE-3",
  "triple": "9f2c7a1e5b8d4c6f",
  "rule_hash": "4b1f...",
  "proof_hash": "c07a...",
  "test_hash": "1d93...",
  "test_hash_kind": "file",
  "audit_hash": "e3b0c442...",
  "level": "signed",
  "signer": "jane@acme.com",
  "machine": "jane-laptop",
  "os": "macos",
  "note": null,
  "timestamp": "2026-09-13T12:00:00Z",
  "gate": "signed",
  "evidence": ".purlin/evidence/local/login.json"
}
```

REQUIRED: `schema`, `feature`, `rule`, `triple`, `rule_hash`, `proof_hash`,
`test_hash`, `audit_hash`, `level`, `signer`, `timestamp`. Every other field
is OPTIONAL.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-signature/1` for this format version |
| `feature` | string | the spec that holds the rule |
| `rule` | string | `RULE-N` |
| `triple` | string | the first sixteen characters of the triple hash, of which the file name carries eight |
| `rule_hash` | string | R |
| `proof_hash` | string | P |
| `test_hash` | string | T |
| `test_hash_kind` | string | `file`, `manual` or `none` |
| `audit_hash` | string | A, the hash of what the audit found |
| `level` | string | `passed`, `strong` or `signed`, the rule's level when it was signed. Logged, not compared |
| `signer` | string | the signer's email |
| `machine` | string | the name of the host the signature was made on, as its operating system reports it. Logged, not hashed and not compared |
| `os` | string | `windows`, `macos` or `linux`, the operating system of that host. Logged, not hashed and not compared |
| `note` | string or null | the one line `purlin:sign --note` writes for a `@manual` proof or an AI audit that could not settle; null otherwise |
| `timestamp` | string | ISO 8601 UTC with `Z` |
| `gate` | string | the gate in force when the signature was written: `passed`, `strong` or `signed` |
| `evidence` | string or null | the feature's evidence file the signature rests on, the `local` one where both sources have one |

## Current, and stale

A signature is **current** when the three hashes it binds still equal the
recomputed ones and the audit hash still matches. Anything else is a
signature stale and a person has to look.

`machine` and `os` say where the signature was made, beside `signer` and
`timestamp`, and like them are not hashed: a signature means the same whichever
machine made it.

The level is logged, not locked: `level` says what the rule asked for when it
was signed, and marking the rule differently afterwards leaves the signature
current. A re-audit that finds something different stales it: the strength
moved, or the AI audit's `verdict` or one of its `findings` changed. The model
that answered and the criteria it was sent are not hashed, so a new model
that finds the same thing stales nothing. A rule whose first audit writes an
entry where there was none goes stale for the same reason, which is the
honest answer: there is evidence now that there was not before.

Changing the code alone stales nothing. The evidence carries the fingerprint
of the spec's `> Scope:` files, not the signature, so a code change leaves the
signature standing and the rule's passed cell reads `out of date` until the
tests run again.

## When a signature counts

A current signature is not automatically a signature that counts. What decides
depends on the gate.

Below `signed` a committed signature counts, as long as its hashes match. What
it clears at `strong` is a question the machine could not settle: a `@manual`
proof, or an AI audit that could not tell.

Under `signed` a signature counts when two things hold:

| Condition | How it is read | The reason when it fails |
|---|---|---|
| The commit that added the file is signed and verifies | `git log -1 --format=%G?` prints `G` | `the signing commit is not signed` |
| Its hashes are current | the rule, proof, test and audit hashes, as above | `audit findings changed after the signature` where the rule, proof and test still match and only what the audit found moved, else `hashes changed after the signature` (the cell reads `stale`) |

Nothing else is read. Signing is logged, not policed: the file names the
signer and git names the commit's author, and neither is compared with a list
or with the author of the test. A signature counts on whatever commit carries
it, on any branch.

`trust: remote` in `.purlin/config.json` is read when a rule is signed, not
when a signature is counted: `purlin:sign` refuses a rule with a proof that
has a test when its feature's `ci` evidence holds no section current for this
code, and says to run `purlin:test --remote` first. A rule whose proofs are
all `@manual` is not refused. At the default, `trust: local`, your own run is
the evidence.

A rule needs a signature exactly when its level is `signed`. A rule whose
level is lower still shows its signed cell, and that cell does not keep it
from meeting the gate. `references/hard_gates.md` holds the gate levels and what the tag `signed/<version>` means.
