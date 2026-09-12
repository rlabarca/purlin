> Format-Version: 2

# Verification Receipt Format

A receipt is the record that one feature's rules were all proved at one commit.
It lives next to the spec it covers, as `specs/<category>/<feature>.receipt.json`,
and it is written by `purlin:verify` Step 3 (in this repository, by
`dev/issue_receipts.py`, which drives the server's own verdict function).

A receipt is not a signature and not tamper evidence. Anyone who can write the
file can write any value in it. What a receipt buys is staleness detection: the
`vhash` changes whenever anything it binds changes, so a receipt that no longer
matches the current state is visibly out of date.

## Version 2

```json
{
  "feature": "login",
  "vhash": "a1b2c3d4",
  "vhash_version": 2,
  "commit": "<full sha of HEAD when the receipt was issued>",
  "timestamp": "<ISO 8601, UTC>",
  "rules": ["RULE-1", "RULE-2", "security/RULE-3"],
  "rule_hashes": {"RULE-1": "<16 hex>", "RULE-2": "<16 hex>",
                  "security/RULE-3": "<16 hex>"},
  "proofs": [
    {"feature": "login", "id": "PROOF-1", "rule": "RULE-1", "status": "pass",
     "tier": "unit", "test_file": "tests/test_login.py",
     "test_name": "test_rejects_empty", "platform": null}
  ],
  "manual": [
    {"feature": "login", "proof_id": "PROOF-9", "rule": "RULE-9",
     "email": "pm@example.com", "date": "2026-03-01", "sha": "<commit>"}
  ],
  "evidence": {
    "test_run": {"at": "<ISO 8601>", "commit": "<sha>",
                 "sweep": "dev/run_tests.sh", "passed": 676, "failed": 0,
                 "skipped": 27},
    "proof_files": [
      {"file": "specs/auth/login.proofs-unit.json", "tier": "unit",
       "platform": null, "commit": "<sha>", "committed_at": "<ISO 8601>",
       "runner": null, "executed_in_test_run": true}
    ]
  },
  "awaiting_runner": [
    {"id": "PROOF-7", "tier": "unit", "platform": "windows-2022"}
  ]
}
```

### Fields

| Field | Meaning |
|---|---|
| `feature` | The feature name, matching the spec's `# Feature:` line |
| `vhash` | 8 hex of the verification hash, computed as below |
| `vhash_version` | `2`. A receipt without this key was written under version 1 |
| `commit` | HEAD when the receipt was issued |
| `timestamp` | When the receipt was issued, ISO 8601 in UTC |
| `rules` | Sorted active rule keys, a required or global rule keyed `<source>/RULE-N` |
| `rule_hashes` | Rule key to 16 hex of its whitespace-normalised text |
| `proofs` | Every proof entry that counted, with `feature`, `id`, `rule`, `status`, `tier`, `test_file`, `test_name` and `platform` (`null` when the result is platform agnostic) |
| `manual` | Manual stamps that counted toward coverage. Omitted when empty |
| `evidence` | Where the proofs came from, see below |
| `awaiting_runner` | `{id, tier, platform}` per proof declared `@on(<platform>)` with no result satisfying it. Omitted when empty |

### `evidence`

`evidence.test_run` is the run marker the issuer read: `at`, `commit`, `sweep`,
`passed`, `failed` and `skipped`.

`evidence.test_run` is null for a receipt issued without a run marker, which is
what `--no-run-check` produces. A null `test_run` means the receipt records proof
files, not an observed run, and nothing about the receipt should be read as saying
the tests were executed at this commit.

`evidence.proof_files` (`proof_files`) carries one row per proof file that contributed:

| Key | Meaning |
|---|---|
| `file` | Project-relative path of the proof file, forward slashes |
| `tier` | The file's tier |
| `platform` | The platform id the file is scoped to, `null` when agnostic |
| `commit` | The commit that last wrote that file, `null` when it has none |
| `committed_at` | That commit's committer date, ISO 8601 |
| `runner` | The commit's `Purlin-Runner:` trailer, `null` for a local commit |
| `executed_in_test_run` | Whether every entry in that file names a `test_file` the recorded run executed |

A file that no recorded run executed and no runner committed is evidence with no
witness. The issuer refuses the whole feature in that case rather than writing a
receipt over it.

### What the vhash binds

Segments joined with `\x00`, hashed with sha256, truncated to 8 hex:

```
["purlin-vhash/2"]
per active rule key, sorted:  ["R", key, sha256(" ".join(text.split()))[:16]]
per proof, sorted by (feature, id, rule, tier, platform, test_file, test_name):
    ["P", feature, id, rule, status, tier, platform or "", test_file, test_name]
per counted manual stamp, sorted:
    ["M", feature, proof_id, rule, email, date, sha]
```

It binds: the set of active rule keys, each rule's text, and for every proof its
feature, id, rule, status, tier, platform, test file and test name. So a reworded
rule, a renamed or rewritten test, a proof moved between tiers or platforms, and
a status flip all stale the receipt. Whitespace is normalised, so reflowing a
rule does not.

It does not bind: the proof file's contents beyond those fields, the source code
under test, the commit, the timestamp, the evidence block, or anything about who
issued it. `commit` and `evidence` are recorded beside the hash for that reason:
they are context a reader needs and the hash does not carry.

The version tag is the first segment, so a version 1 and a version 2 hash of the
same state cannot collide.

## Version 1 (historical)

Version 1 receipts carried only:

```json
{"feature": "login", "vhash": "a1b2c3d4", "commit": "<sha>",
 "timestamp": "<ISO 8601>", "rules": ["RULE-1"],
 "proofs": [{"id": "PROOF-1", "rule": "RULE-1", "status": "pass"}],
 "awaiting_runner": [{"id": "PROOF-7", "tier": "unit", "platform": "windows"}]}
```

Its hash was `sha256(sorted rule ids + "|" + sorted "<id>:<status>" pairs)[:8]`.
It bound no rule text, no test identity, no tier and no platform, and it keyed
proofs by id alone, so the same `PROOF-3` under a feature and under a required
anchor hashed the same. A version 1 receipt has no `vhash_version` key; it never
matches a version 2 hash, so it reads as stale and is reissued.
