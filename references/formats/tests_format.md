> Format-Version: 1

# Test Results Format

The test results are what `purlin:test` writes after it runs the tagged tests,
and what it commits itself. There are two files: one JSON file per feature,
which is what a reader parses, and one Markdown table for the whole project,
which is what a teammate reads on the git host without running anything.

```
.purlin/tests/<feature>.json
.purlin/tests.md
```

Both are tracked. Nothing under `.purlin/tests/` is gitignored, because the
point of the files is that somebody who did not make the run can read them.

The results are the **`local` source**: they say what the last run on
somebody's machine saw. They count under the gate `passed` and under nothing
above it. `strong` and `signed` read a record CI wrote, which is a different
file in a different directory, described in `references/formats/record_format.md`.

## The file name

`<feature>` is the spec's name, matching `specs/<category>/<feature>.md`. One
file per feature, replaced whole on every run that covered that feature. A
`--feature` run replaces the files of the features it ran and leaves the rest
alone.

## Fields

```json
{
  "schema": "purlin-tests/1",
  "feature": "login",
  "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7",
  "at": "2026-09-26T12:00:00Z",
  "os": "macos",
  "rules": {
    "RULE-1": "passed",
    "RULE-2": "no test"
  },
  "proofs": [
    {
      "id": "PROOF-1",
      "rule": "RULE-1",
      "result": "pass",
      "tier": "unit",
      "env": null,
      "test": "tests/test_login.py::test_rejects_a_wrong_password"
    }
  ]
}
```

REQUIRED: `schema`, `feature`, `commit`, `at`, `os`, `rules`, `proofs`.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-tests/1` for this format version |
| `feature` | string | the spec this run covered |
| `commit` | string | the full sha of the commit the working tree was on |
| `at` | string | ISO 8601 UTC with `Z`, when the run finished |
| `os` | string | `windows`, `macos` or `linux`, the machine the run was on |
| `rules` | object | one entry per rule the spec writes, `RULE-N` to a word |
| `proofs` | array | one entry per proof of those rules |

Each `rules` value is the passed cell's own word for what this run saw:

| Word | What it means |
|---|---|
| `passed` | every proof of the rule that could run here has a passing test |
| `failed` | a test claiming one of the rule's proofs failed |
| `no test` | no proof names the rule, or nothing observed any of its proofs |
| `not run` | a proof of the rule is tagged `@env` for another operating system, so this machine could not answer |

Each `proofs` entry:

| Field | Type | What it holds |
|---|---|---|
| `id` | string | `PROOF-N` |
| `rule` | string | the `RULE-N` the proof covers |
| `result` | string | `pass`, `fail` or `missing` |
| `tier` | string | `unit`, `integration`, `e2e` or `manual` |
| `env` | string or null | the operating system the proof's `@env` tag named, or null |
| `test` | string | `<file>::<name>` for the test that observed the proof, empty when nothing did |

## The table

`.purlin/tests.md` is rendered from every file under `.purlin/tests/`, so it
is always the whole project even when the run was one feature. It carries a
heading line naming the commit, one table, and one sentence saying what the
numbers are:

```
# Test results at 4f1c2ab

| Feature | Rules | Passed | Failing | No test | Last run |
|---|---|---|---|---|---|
| login | 12 | 11 | 0 | 1 | 4f1c2ab · 2026-09-26T12:00:00Z · macos |

These are the last local run of each feature, and they count only at the gate `passed`.
```

`Passed` counts the rules reading `passed` and `Failing` those reading
`failed`. `No test` counts every other rule, so a rule waiting on another
operating system is counted there rather than left out of the row. `Last run`
is `<sha7> · <time> · <os>` from that feature's own file.

## The commit

`purlin:test` commits both files itself, under the person's own git identity,
with the subject:

```
purlin: tests at <sha7>
```

It never pushes and never prints a push command. A run that changed neither
file commits nothing and says `Test results unchanged.`

## What is not here

No strength, no findings, no observations and no signature. Those belong to
the audit and to the record, and a person writes none of them: the record is
CI's.
