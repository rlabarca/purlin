> Format-Version: 3

# Signature Format

A signature is one named person's attestation that a rule, its proof and its
test belong together. It is a committed file, so who signed what and when is in
git history. CI writes no signature, ever: every file in the directory was
written by a person.

## File name

```
specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json
specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<holder-slug>.hold.json
```

| Part | What it is |
|---|---|
| `<feature>` | the spec that holds the rule, matching `specs/<category>/<feature>.md` |
| `<RULE-N>` | the rule the signature is for |
| `<hash8>` | the first eight characters of the triple the signature binds |
| `<signer-slug>` | the signer's email local part, lowercased, every non-alphanumeric character replaced by `-` |
| `<holder-slug>` | the same slug for the person who wrote a hold |

One signature is one file, so two signatures never conflict and a batch of
forty adds forty files in one commit. The slug `brief` is reserved: the reader
skips `<RULE-N>.<hash8>.brief.json` rather than reading it as a signature by
someone called `brief`.

## The triple

What a signature binds is three hashes, not the files they came from:

| Letter | What it hashes |
|---|---|
| R | the rule text, its tags stripped and its whitespace normalised, so reflowing a long line does not stale the signature |
| P | the proof descriptions of that rule, in order, normalised the same way |
| T | the test files backing those proofs, each with the test's name and the file's blob id. The tests are the ones the feature's latest counting records observed, every operating system together, so every checkout reads the same T; a proof no record has observed yet takes them from the checkout's own runtime proofs |
| D | the pinned design a `origin: design` rule rests on, and null for every other origin |

The triple hash is `sha256` over R, P and T, one per line, and the first eight
characters of it name the file. D is held and compared beside the triple
rather than folded into it, because a rule with no design has none.

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
  "design_hash": null,
  "risk": "high",
  "signer": "jane@acme.com",
  "note": null,
  "timestamp": "2026-09-13T12:00:00Z",
  "gate": "signed",
  "brief": ".purlin/briefs/login/RULE-3.9f2c7a1e.brief.json",
  "record": ".purlin/records/login/20260913T120000Z-abc1234-ci.json"
}
```

REQUIRED: `schema`, `feature`, `rule`, `triple`, `rule_hash`, `proof_hash`,
`test_hash`, `risk`, `signer`, `timestamp`. Every other field is OPTIONAL.

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
| `design_hash` | string or null | D, the spec's `> Pinned:` hash for a `origin: design` rule |
| `risk` | string | `high`, `medium` or `low`, as the rule was tagged when it was signed |
| `signer` | string | the signer's email |
| `note` | string or null | the one line `purlin:sign --note` writes for a `@manual` proof or a model review that could not settle; null otherwise |
| `timestamp` | string | ISO 8601 UTC with `Z` |
| `gate` | string | the gate in force when the signature was written: `passed`, `strong` or `signed` |
| `brief` | string or null | the brief the signer read |
| `record` | string or null | the record the signature rests on |

## Current, and stale

A signature is **current** when the three hashes it binds still equal the
recomputed ones, the design hash still matches, and the risk it names still
matches the rule's. Anything else is a signature stale and a person has to
look.

Changing the risk stales the signature on purpose: raising a rule from low to
high changes what signing it meant, and the old attestation was given under the
old bar.

Changing the code alone stales nothing. A record carries the tree hash of the
spec's `> Scope:` files, so a code change leaves the signature standing and the
rule's passed cell reads `code changed` until CI runs again.

## When a signature counts

A current signature is not automatically a signature that counts. What decides
depends on the gate, and each condition has its own line in the status so you
can see which one failed.

Under `strong` a signature from anyone counts, as long as the file is committed
and its hashes match. What it clears there is a question the machine could not
settle: a `@manual` proof, or a model review that could not tell.

Under `signed` four conditions hold:

| Condition | How it is read | The reason when it fails |
|---|---|---|
| The commit that added the file is signed and verifies | `git log -1 --format=%G?` prints `G` | `the signing commit is not signed` |
| The author's email is on the signer list | `signers` in `.purlin/config.json`, as of that commit | `the signer is not on the list` |
| The author is not the author of the commit that last touched the test | write the test or sign it, not both | `the signer last touched the test` |
| The signing commit is on the protected branch | the commit is an ancestor of the branch head | `the signing commit is not on <branch>` |

The last one keeps a signature that exists only on a side branch from letting a
change merge.

A signature is required at or above `sign_at` in `.purlin/config.json`, which
defaults to `medium`. Below it the signed cell reads `not required`.
`references/hard_gates.md` holds the gate levels and the signer list.

## Holds

A hold is a person's statement that the test does not prove the proof as
written. `purlin:sign <feature> RULE-N --hold "<the missing case>"` writes it
and commits it signed as `hold(<feature>): RULE-N`. It is named and bound like
a signature, with a fourth part in the name:

```json
{
  "schema": "purlin-hold/1",
  "feature": "records",
  "rule": "RULE-12",
  "triple": "9f2c7a1e5b8d4c6f",
  "rule_hash": "4b1f...",
  "proof_hash": "c07a...",
  "test_hash": "1d93...",
  "test_hash_kind": "file",
  "design_hash": null,
  "risk": "low",
  "holder": "jane@acme.com",
  "reason": "the tests call _azure and _host apart; none calls run_remote()",
  "timestamp": "2026-09-16T12:00:00Z",
  "brief": ".purlin/briefs/records/RULE-12.9f2c7a1e.brief.json"
}
```

REQUIRED: `schema`, `feature`, `rule`, `triple`, `rule_hash`, `proof_hash`,
`test_hash`, `risk`, `holder`, `reason`, `timestamp`. The hashes, `risk` and
`brief` mean what they mean in a signature; `holder` is the person's email and
`reason` the missing case, in words.

A hold is current under the same test as a signature. While it is current the
rule's strong cell and its signed cell both read `held`, each with the reason
`held by <holder>: <reason>`. A current signature for the
same hashes outranks it. A hold only ever withholds, so the holder need not be
on the signer list.
