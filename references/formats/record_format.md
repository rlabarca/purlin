> Format-Version: 1

# Record Format

A record is one verify run's observations for one feature, written as a file in
the tree and committed. Records are how a rule reaches the Recorded state, and
the git history of `.purlin/records/` is the log of what was verified and when.

## File name

```
.purlin/records/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json
```

| Part | What it is |
|---|---|
| `<feature>` | the spec's name, matching `specs/<category>/<feature>.md` |
| `<timestamp>` | ISO 8601 UTC without separators, `20260913T120000Z` |
| `<commit7>` | the first seven characters of the commit the run observed |
| `<runner>` | `ci`, or the developer's git email local part, lowercased, every non-alphanumeric character replaced by `-` |
| `<os>` | `windows`, `macos` or `linux`, and absent when the run was not one job of a matrix |

One run writes one file per feature. Adding a file never conflicts, so two runs
never collide and a matrix job never overwrites another job's observations.

## Fields

```json
{
  "schema_version": 1,
  "feature": "login",
  "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7",
  "timestamp": "2026-09-13T12:00:00Z",
  "runner": "ci",
  "os": "linux",
  "gate": "recorded",
  "test_strength": 71,
  "scope_tree": "9f2c7a1e5b8d4c6f0a3e9b2d7c4f1a8e6b0d3c5f",
  "environment": {
    "os": "linux",
    "id": "linux-x86_64",
    "kind": "ci",
    "job": "verify",
    "host": "github-runner-3",
    "engines": ["mutmut"]
  },
  "proofs": [
    {
      "id": "PROOF-1",
      "rule": "RULE-1",
      "status": "pass",
      "tier": "unit",
      "env": null,
      "test_file": "tests/test_login.py",
      "test_name": "test_rejects_a_wrong_password"
    }
  ]
}
```

REQUIRED: `schema_version`, `feature`, `commit`, `timestamp`, `runner`,
`gate`, `proofs`. Every other field is OPTIONAL.

| Field | Type | What it holds |
|---|---|---|
| `schema_version` | integer | `1` for this format version |
| `feature` | string | the spec this run observed |
| `commit` | string | the full sha of the commit the run observed |
| `timestamp` | string | ISO 8601 UTC with `Z`, matching the file name |
| `runner` | string | `ci` or the developer's runner slug, matching the file name |
| `os` | string or null | the operating system of this matrix job, or null |
| `gate` | string | `tested`, `recorded` or `approved`, the gate in force at the run |
| `test_strength` | integer or null | of the deliberate breaks made to the code, the percentage the tests caught; null when no engine measured it |
| `scope_tree` | string | the git tree hash of the spec's `> Scope:` files, which is what tells a code change from a rule change |
| `environment` | object | where the run happened, described below |
| `proofs` | array | one entry per proof the run observed |

A record may carry more than this. A verify run also writes the detail it
gathered on the way: `features` (the per-rule result, tests and attachments),
`plugins`, `missing`, `log` and `dirty`. Those are OPTIONAL and no reader
depends on them, so a record written with the fields above alone is a complete
record.

The `environment` object, and every field in it, is OPTIONAL:

| Field | Type | What it holds |
|---|---|---|
| `os` | string | `windows`, `macos` or `linux`, matching the file name's `<os>` |
| `id` | string | a short name for the machine's shape, such as `darwin-arm64` |
| `kind` | string | `ci`, `developer` or `local`, what the run called itself |
| `job` | string or null | the CI job the run was part of, or null off CI |
| `host` | string or null | the runner or machine name |
| `engines` | array | the break engines the run used, empty when none measured |

`kind` is what the run called itself and is never the label. The label comes
from the commit, as the next section says: a record claiming `kind` `ci` that a
person committed is a `developer` record.

Each `proofs` entry:

| Field | Type | What it holds |
|---|---|---|
| `id` | string | `PROOF-N` |
| `rule` | string | the `RULE-N` the proof covers |
| `status` | string | `pass`, `fail` or `skip` |
| `tier` | string | `unit`, `integration`, `e2e` or `manual` |
| `env` | string or null | the operating system the proof's `@env` tag named, or null |
| `test_file` | string | the file holding the tagged test |
| `test_name` | string | the test's name inside that file |

## The label comes from git, not from the file

A file can claim anything. What decides whether a record counts is the last
commit that touched it:

| Label | What git shows |
|---|---|
| `ci` | the committer is the git host's build identity. On GitHub that is `github-actions[bot]` and `git log --format=%G?` prints `G`, because a commit made through the Git Data API with the Actions token and no author or committer field is signed by GitHub. On Azure DevOps it is the build service and no signature exists, which is what Azure DevOps documents |
| `developer` | a person committed it |
| `local` | it is not committed at all |

`tested` counts a `ci` or a `developer` record. `recorded` and `approved`
count a `ci` record alone, which the git host's file-path rule on
`.purlin/records/**` enforces on the other side.

## Retention

A feature keeps the newest three records per operating system. Verify prunes
the rest as it writes, so a matrix of three operating systems keeps nine
records per feature and no more.

A record any annotated `validated/<name>` tag names in its message is kept for
ever. `purlin:verify --tag <name>` writes such a tag; its message lists the
record paths it vouches for, one per line, and retention reads those paths with
`git for-each-ref --format='%(contents)' refs/tags/validated/`.

## Freshness

A record carries `scope_tree`, the git tree hash of the spec's `> Scope:`
files. That is what separates two kinds of change:

- the code changed, the rule, proof and test text did not: the approval stands
  and the rule is flagged `re-verify pending` until CI runs again
- the rule, proof or test text changed: the rule is `Stale` and a human looks
