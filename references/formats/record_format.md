> Format-Version: 4

# Record Format

A record is one audit's observations for one feature, written as a file in
the tree and committed. `purlin:audit` writes one record per feature it
audited and commits it under the person's own identity; the CI job does the
same under the build identity. Neither pushes. At `passed` no record is
written at all: the evidence there is the test results, described in
`references/formats/tests_format.md`.

A record is what the strong cell of a rule reads, and the git history of
`.purlin/records/` is the log of what ran and when. Nobody signs a record.

## File name

```
.purlin/records/<source>/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json
```

| Part | What it is |
|---|---|
| `<source>` | `ci` or `local`. **The folder is the source**, and the file's own `source` field must say the same word |
| `<feature>` | the spec's name, matching `specs/<category>/<feature>.md` |
| `<timestamp>` | ISO 8601 UTC without separators, `20260913T120000Z` |
| `<commit7>` | the first seven characters of the commit the run observed |
| `<runner>` | `ci`, or a git email's local part, lowercased, every non-alphanumeric character replaced by `-` |
| `<os>` | `windows`, `macos` or `linux`, and absent when the run was not one job of a matrix |

One run writes one file per feature. Adding a file never conflicts, so two runs
never collide and a matrix job never overwrites another job's observations.

## Fields

```json
{
  "schema": "purlin-record/3",
  "schema_version": 3,
  "feature": "login",
  "source": "ci",
  "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7",
  "timestamp": "2026-09-13T12:00:00Z",
  "runner": "ci",
  "os": "linux",
  "gate": "strong",
  "test_strength": 71,
  "scope_tree": "9f2c7a1e5b8d4c6f0a3e9b2d7c4f1a8e6b0d3c5f",
  "environment": {
    "os": "linux",
    "id": "linux-x86_64",
    "kind": "ci",
    "job": "audit",
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

REQUIRED: `schema_version`, `feature`, `source`, `commit`, `timestamp`,
`runner`, `gate`, `proofs`. Every other field is OPTIONAL.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-record/3` for this format version |
| `schema_version` | integer | `3` for this format version |
| `feature` | string | the spec this run observed |
| `source` | string | `ci` or `local`, matching the folder the file sits in. A file where the two disagree is ignored |
| `commit` | string | the full sha of the commit the run observed |
| `timestamp` | string | ISO 8601 UTC with `Z`, matching the file name |
| `runner` | string | `ci` or a runner slug, matching the file name |
| `os` | string or null | the operating system of this matrix job, or null |
| `gate` | string | `passed`, `strong` or `signed`, the gate in force at the run |
| `test_strength` | integer or null | of the deliberate breaks made to the code, the percentage the tests caught; null when no engine measured it, which is every run under `passed`, where the breaks do not run at all |
| `scope_tree` | string | the git tree hash of the spec's `> Scope:` files, which is what tells a code change from a rule change |
| `environment` | object | where the run happened, described below |
| `proofs` | array | one entry per proof the run observed |

A record may carry more than this. A CI run also writes the detail it
gathered on the way: `features` (the per-rule result, tests and attachments),
`plugins`, `missing`, `log` and `dirty`. Those are OPTIONAL and no reader
depends on them, so a record written with the fields above alone is a complete
record.

The `environment` object, and every field in it, is OPTIONAL:

| Field | Type | What it holds |
|---|---|---|
| `os` | string | `windows`, `macos` or `linux`, matching the file name's `<os>` |
| `id` | string | a short name for the machine's shape, such as `darwin-arm64` |
| `kind` | string | `ci` or `local`, what the run called itself |
| `job` | string or null | the CI job the run was part of, or null off CI |
| `host` | string or null | the runner or machine name |
| `engines` | array | the break engines the run used, empty when none measured |

`kind` is what the run called itself and is never the source. The source is
the folder, as the next section says, and `source` beside it is the same fact
written twice so a file moved out of its folder stops being read.

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

## The source is the folder

A file can claim anything, so the source is not read out of the file alone.
It is the folder the file sits in, checked against the file's own `source`
field:

| Source | The folder | Who may write it |
|---|---|---|
| `ci` | `.purlin/records/ci/<feature>/` | the build identity alone, which the git host's file-path rule on `.purlin/records/ci/**` enforces |
| `local` | `.purlin/records/local/<feature>/` | anyone. `purlin:audit` writes here and commits under the person's own identity |

A record whose `source` field disagrees with its folder is ignored, with one
warning naming the path. Guessing which half is right would let a file copied
from one folder to the other claim a source no rule enforces.

The gate decides which sources count. `passed` and `strong` count both: the
breaks a person ran are the same breaks CI runs, and an audit is an audit.
`signed` counts a `ci` record alone, for the tests and the audit both,
because a signature attaches to the run on the protected branch after the
merge and a local run there is a preview. A record the gate does not count is
still read: the passed cell names its source and says `<source> record does
not count under <gate>`.

## The platforms a record covers

A record names the operating system it ran on, in its file name for a matrix
job and in `environment.os` always. The passed cell of every rule the record
observed carries one `platforms` entry per operating system a counting run
named, each with that platform's own word, its source and when it ran. Where
the platforms disagree the cell reads `partial`, which is not met: a rule
whose tests pass on Linux and fail on Windows is neither passed nor failed.
Test strength is platform independent, because the breaks are measured once
per feature.

## What the record commit carries

A run's commit carries the records it wrote and the briefs the same run wrote
under `.purlin/briefs/<source>/<feature>/`. Its subject is `purlin: record for
<commit7>`, whoever made it. It carries no signature file: a signature is a
named person's attestation, and no runner writes one, ever. It carries no test
results either: those are what `purlin:test` commits, with its own subject.

`purlin:audit` prints `Record committed.` when the commit was made,
`Record unchanged.` when the run saw exactly what the last one saw, and it
never pushes. CI commits through the git host's REST API with no author and
no committer field, so GitHub signs the commit with its own key and reports
`github-actions[bot]` as the committer; Azure DevOps pushes through its
Pushes API with the build service's token.

## Retention

A feature keeps the newest three records per operating system. The run prunes
the rest as it writes, so a matrix of three operating systems keeps nine
records per feature and no more.

A record any annotated `record/<name>` tag names in its message is kept for
ever. `purlin:audit --tag <name>` writes such a tag; its message lists the
record paths it vouches for, one per line, and retention reads those paths with
`git for-each-ref --format='%(contents)' refs/tags/record/`.

## Freshness

A record carries `scope_tree`, the git tree hash of the spec's `> Scope:`
files. That is what separates two kinds of change:

- the code changed, the rule, proof and test text did not: the signature stands
  and the passed cell reads `code changed` until CI runs again
- the rule, proof or test text changed: the signature no longer binds the
  hashes, the signed cell reads `stale`, and a person looks
