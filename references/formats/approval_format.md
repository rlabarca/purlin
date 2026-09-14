> Format-Version: 1

# Approval Format

An approval is one named person's attestation that a rule, its proof and its
test belong together. It is a committed file, so who approved what and when is
in git history. CI writes the same file for a low-risk rule it auto-approves.

## File name

```
specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.<approver-slug>.json
specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.ci.json
```

| Part | What it is |
|---|---|
| `<feature>` | the spec that holds the rule, matching `specs/<category>/<feature>.md` |
| `<RULE-N>` | the rule the approval is for |
| `<hash8>` | the first eight characters of the triple the approval binds |
| `<approver-slug>` | the approver's email local part, lowercased, every non-alphanumeric character replaced by `-` |
| `ci` | in place of a slug, for an approval CI wrote itself |

One approval is one file, so two approvals never conflict and a batch of forty
adds forty files in one commit. The review brief written for the same rule sits
in the same directory as `<RULE-N>.<hash8>.brief.json`; it is a brief, never an
approval, and the reader skips it.

## The triple

What an approval binds is three hashes, not the files they came from:

| Letter | What it hashes |
|---|---|
| R | the rule text, its tags stripped and its whitespace normalised, so reflowing a long line does not stale the approval |
| P | the proof descriptions of that rule, in order, normalised the same way |
| T | the test files backing those proofs, each with the test's name and the file's blob id |
| D | the pinned design a `origin: design` rule rests on, and null for every other origin |

The triple hash is `sha256` over R, P and T, one per line, and the first eight
characters of it name the file. D is recorded and compared beside the triple
rather than folded into it, because a rule with no design has none.

`test_hash_kind` says what T was taken from: `file` for a test file version
control tracks, `manual` for a proof with no test at all, and `none` for a rule
with nothing behind it yet.

## Fields

```json
{
  "schema": "purlin-approval/1",
  "feature": "login",
  "rule": "RULE-3",
  "triple": "9f2c7a1e5b8d4c6f",
  "rule_hash": "4b1f...",
  "proof_hash": "c07a...",
  "test_hash": "1d93...",
  "test_hash_kind": "file",
  "design_hash": null,
  "risk": "high",
  "approver": "jane@acme.com",
  "timestamp": "2026-09-13T12:00:00Z",
  "gate": "approved",
  "brief": "specs/auth/login.approvals/RULE-3.9f2c7a1e.brief.json",
  "record": ".purlin/records/login/20260913T120000Z-abc1234-ci.json"
}
```

REQUIRED: `schema`, `feature`, `rule`, `triple`, `rule_hash`, `proof_hash`,
`test_hash`, `risk`, `approver`, `timestamp`. Every other field is OPTIONAL.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-approval/1` for this format version |
| `feature` | string | the spec that holds the rule |
| `rule` | string | `RULE-N` |
| `triple` | string | the first sixteen characters of the triple hash, of which the file name carries eight |
| `rule_hash` | string | R |
| `proof_hash` | string | P |
| `test_hash` | string | T |
| `test_hash_kind` | string | `file`, `manual` or `none` |
| `design_hash` | string or null | D, the spec's `> Pinned:` hash for a `origin: design` rule |
| `risk` | string | `high`, `medium` or `low`, as the rule was tagged when it was approved |
| `approver` | string | the approver's email, or `ci` for an auto-approval |
| `timestamp` | string | ISO 8601 UTC with `Z` |
| `gate` | string | the gate in force when the approval was made |
| `brief` | string or null | the brief the approver read |
| `record` | string or null | the record the approval rests on |

## Current, and Stale

An approval is **current** when the three hashes it binds still equal the
recomputed ones, the design hash still matches, and the risk it names still
matches the rule's. Anything else is Stale and a person has to look.

Changing the risk stales the approval on purpose: raising a rule from low to
high changes what approving it meant, and the old attestation was given under
the old bar.

Changing the code alone stales nothing. A record carries the tree hash of the
spec's `> Scope:` files, so a code change leaves the approval standing and
flags the rule `re-verify pending` until CI runs again.

## What counts

A current approval is not automatically an approval that counts. Three things
decide, and each has its own line in the status so you can see which one failed:

| Condition | How it is read |
|---|---|
| The commit that added the file is signed | `git log -1 --format=%G?` prints `G` |
| The author's email is on the approver list | `approvers` in `.purlin/config.json`, as of that commit |
| The author is not the author of the commit that last touched the test | write the test or approve it, not both |

Under the `approved` gate the gate also checks that the approval commit is an
ancestor of the protected branch head, so an approval that exists only on a
side branch does not let a change merge.

## CI auto-approval

CI writes `<RULE-N>.<hash8>.ci.json` for a rule that is low risk, has a passing
record, and has test strength at or above `min_strength`. A project with no
break engine has no strength to compare, so the free checks on the proof text
stand in for it: every check clear, or nothing is written.

A CI auto-approval is exempt from the signature, the approver list and the
author check, because no person made it. What bounds it is the rule above:
`high` and `medium` are never auto-approved, and a `@manual` proof is never
auto-approved at any risk, because its evidence is a person's note.
