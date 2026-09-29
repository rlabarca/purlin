> Format-Version: 5

# Evidence format

The evidence is what a test run and an audit leave behind for one feature:
each proof's result on each operating system, the machine the tests ran
on, the commit and the time, and,
once an audit has read the feature, what the audit found for each rule.
There is one JSON file per feature per source, and a reader parses it to
decide every rule's cells.

```
.purlin/evidence/local/<feature>.json   a person's own run
.purlin/evidence/ci/<feature>.json      a remote runner's run
```

All of them are tracked. Nothing under `.purlin/evidence/` is gitignored,
because the point of the files is that somebody who did not make the run can
read them.

## The two folders

**The folder is the source.** A file under `local/` is written by
`purlin:test` and `purlin:audit` on a person's machine and committed under
that person's own git identity. A file under `ci/` is written only by the
`--ci` arm on a run branch, through the git host's API; `purlin:test
--remote` pulls that commit home.

The file's `source` field repeats the folder. A file whose `source` disagrees
with its folder is ignored, and the reader prints one warning naming it.

## The file name

`<feature>` is the spec's name, matching `specs/<category>/<feature>.md`.
Anchors have files of their own like any other spec. One file holds every
operating system that ran the feature, one section each.

## Fields

```json
{
  "schema": "purlin-evidence/2",
  "feature": "login",
  "source": "local",
  "spec": "specs/auth/login.md",
  "platforms": {
    "macos": {
      "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7",
      "dirty": false,
      "at": "2026-09-27T12:00:00Z",
      "runner": "jane",
      "machine": "jane-mbp",
      "hostname": "jane-mbp",
      "fingerprint": {"spec": "<sha256>", "code": "<sha256>", "tests": "<sha256>"},
      "rules": {"RULE-1": "passed", "RULE-2": "no test"},
      "proofs": [
        {"id": "PROOF-1", "rule": "RULE-1", "result": "pass", "env": null,
         "manual": false, "test": "tests/test_login.py::test_rejects_a_wrong_password"}
      ]
    }
  },
  "audit": {
    "mutation": {"engine": "mutmut", "score": 71, "at": "2026-09-27T12:05:00Z",
                 "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7"},
    "rules": {
      "RULE-1": {"rule_hash": "<sha256>", "proof_hash": "<sha256>",
                 "test_hash": "<sha256>", "verdict": "strong", "findings": [],
                 "model": "example-model-1",
                 "criteria": "<sha256>",
                 "notes": ["PROOF-1 holds two cases."],
                 "at": "2026-09-27T12:05:00Z",
                 "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7"}
    }
  }
}
```

REQUIRED: `schema`, `feature`, `source`, `spec`, `platforms`. `audit` is
present only once an audit has run.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-evidence/2`. A file carrying any other value is ignored with one warning |
| `feature` | string | the feature, the spec's name |
| `source` | string | `local` or `ci`, the same word as the folder the file sits in |
| `spec` | string | the spec's path, `/` separated |
| `platforms` | object | one section per operating system, keyed `windows`, `macos` or `linux`; a system that is neither Windows nor macOS writes under `linux`. Any other key is skipped. A person reads the three as `Windows`, `macOS` and `Linux/Unix` |
| `audit` | object | the audit's findings, per rule |

### A platform section

| Field | Type | What it holds |
|---|---|---|
| `commit` | string | the full sha of `HEAD` when the run started |
| `dirty` | bool | whether the working tree had changes that were not committed. It is shown and not compared: the fingerprint is what decides |
| `at` | string | ISO 8601 UTC with `Z`, when the run finished |
| `runner` | string | the slug of the runner's email, or `ci` |
| `machine` | string | where the tests ran: the host's name, or `unknown` where it reports none, for a `local` section; `remote runner, <Windows\|macOS\|Linux/Unix>` for a `ci` section. Compared: a run on another machine replaces the section |
| `hostname` | string | the host's own name, the one a remote runner's host lent it included. Kept and never compared |
| `fingerprint` | object | `spec`, `code` and `tests`, three sha256 hex strings. See "The fingerprint" |
| `rules` | object | `RULE-N` to one word for what this run saw |
| `proofs` | array | one entry per (proof, test) pair |

A `ci` section answers only for the proofs tagged `@env` for the runner's
own system: its `proofs` list those proofs alone, and its `rules` the rules
they prove. A feature with no such proof gets no `ci` file from that runner.

Each `rules` value:

| Word | What it means |
|---|---|
| `passed` | every test tied to every proof of the rule that could run here ran and passed; for a rule with no proof, every test marked with the rule's own id passed |
| `failed` | a test claiming one of the rule's proofs, or marked with the rule's id, failed |
| `no test` | no proof names the rule and no test is marked with its id, or no test is tied to any of its proofs |
| `not run` | a test tied to the rule did not run, or a proof of the rule is tagged `@env` for another operating system, so this machine could not answer |

Each `proofs` entry:

| Field | Type | What it holds |
|---|---|---|
| `id` | string | `PROOF-N`, or `RULE-N` for a test marked with the id of a rule that has no proof |
| `rule` | string | the `RULE-N` the proof covers, the same as `id` for a rule-marked test |
| `result` | string | `pass`, `fail`, `missing` or `not run` |
| `env` | string or null | the operating system the proof's `@env` tag names, or null |
| `manual` | bool | whether the proof is tagged `@manual` |
| `test` | string | `<file>::<name>` for the test that observed the proof, `""` when nothing did. The name is the test's own, as the marker format spells it |

A test is tied to its proof by the marker comment above it, as
`references/formats/marker_format.md` says. A proof whose test was skipped, or
that no case in the report is, reads `missing` with the test named. A proof
tagged `@env` for another operating system than the section's reads `not run`
whatever its tied test did there: a test carrying a Mac proof's marker and a
Windows proof's marker runs on the Mac and proves only the Mac proof. A proof
no test is tied to has one entry with an empty `test`, reading the same way.

A reader takes a proof's result in a section as the worst of its entries:
`fail` where one failed, else `not run` where one reads `missing` or `not
run`, else `pass`. A proof has passed only when every test tied to it ran and
passed.

### The audit

| Field | Type | What it holds |
|---|---|---|
| `audit.mutation` | object or null | `engine` (string), `score` (int or null), `at` and `commit`. Null when mutation testing is off |
| `audit.rules` | object | `RULE-N` to the audit of that rule |

Each `audit.rules` entry:

| Field | Type | What it holds |
|---|---|---|
| `rule_hash` | string | sha256 of the rule text the audit read |
| `proof_hash` | string | sha256 of the proof texts the audit read |
| `test_hash` | string | sha256 of the tests the audit read |
| `verdict` | string | `strong`, `weak` or `undecided` |
| `findings` | array of strings | one sentence per finding; empty when the audit found nothing |
| `model` | string | the model that answered, its name and version as the `claude` command's JSON reports them, or `unknown` where it reports none |
| `criteria` | string | sha256 of `references/review_criteria.md` as it was sent to the model |
| `at` | string | ISO 8601 UTC with `Z` |
| `commit` | string | the full sha of `HEAD` when the audit ran |
| `notes` | array of strings | optional: one sentence per proof the audit found longer than the standard or holding two cases. Present only when there are some. A note does not make the rule weak |

`verdict` is what the AI audit answered. It is `strong` with no findings when
the model settled and found nothing, `weak` when it settled and found
something, each finding one sentence, and `undecided` when it could not
settle, its findings being the reason it gave. A rule the model could not be
reached for gets no entry at all, so the next audit reads it again.

`model` and `criteria` name the judge and the instructions it was given. A
signature locks neither, nor the `notes`: it locks the `verdict`, the test
strength and the `findings`, so a new model that finds the same thing ends no
signature.

An audit entry answers a rule while its `rule_hash`, `proof_hash` and
`test_hash` all equal the rule's current ones. `commit` and `at` are shown and
not compared, so an entry taken at an earlier commit still answers. Where both
sources hold an entry that answers, the later `at` is read.

## The fingerprint

A fingerprint says what a section was taken over. Each part is a sha256 hex
string, and every file is read from the working tree with `git hash-object`,
so an edit counts before it is committed.

| Part | What it covers |
|---|---|
| `spec` | the rule and proof lines of the feature, of every spec it requires, transitively, and of every anchor carrying `> Global: true`. A rule line is `<spec> <RULE-N> <text> <tag>`; a proof line is `<spec> <PROOF-N> <rules> <text>`, then `@manual` and `@env(<os>)` where the proof carries them. `> Description:` and the other metadata fields are not covered |
| `code` | the tracked files the `> Scope:` entries reach, each as `<path> <blob>`. A file names itself, a directory names every tracked file under it, and an entry holding `*`, `?` or `[` is a git glob, so `scripts/**/*.py` reaches every Python file under `scripts/` |
| `tests` | every tracked test file carrying a marker for the feature, each as `<path> <blob>`. A test file is one a suite of the `tests` setting names |

A file git does not track is in no part: it would change the fingerprint on
the one machine that holds it and nowhere else. It joins the fingerprint once
`git add` tracks it, and until then Purlin names it when it sits under the
feature's scope or in the directory of one of its marker files.

A spec with no `> Scope:` line names no files. Its `code` part is the sha256
of the empty string, and its sections are compared on `spec` and `tests`
alone. A scope entry that reaches no tracked file, a path that does not exist
or a glob that matches nothing, is named and adds nothing.

A section is **current** when all three of its stored parts equal a
fingerprint taken now. Otherwise it is `out of date`, and the reason names
each part that differs: `code changed since 4f1c2ab`, `spec changed since
4f1c2ab`, `tests changed since 4f1c2ab`, where the sha is the section's
`commit`. Only current sections decide a rule's passed cell.

## How a writer merges

- A test run reads the file from disk and replaces `platforms[<this os>]`
  whole, so a run on another machine replaces the results of the one before.
  Every other section and `audit` stay as they are.
- An audit run first makes the same test-run write. It then replaces
  `audit.rules[<rule>]` for each rule the model answered for and leaves every
  other entry as it is. It replaces `audit.mutation` for each feature it
  measured, which is a feature with at least one rule being read, when
  mutation testing is on.
- Every write drops the `rules` and `audit.rules` entries of rules the spec no
  longer carries.
- Every run deletes the files under `local/` and `ci/` whose feature has no
  spec.
- A `ci/` write carries only the runner's own section. In the API commit's
  retry loop the runner reads the file again at the new parent, merges its
  section into it and sends the result, so two runners on two operating
  systems do not overwrite each other.

## Retention

A file keeps the newest section per operating system and the newest audit
entry per rule. The history is the file's `git log`. Nothing is pruned.

A run that sees the same thing over the same fingerprint on the same
`machine` as the section already there leaves that section as it is, `at`,
`commit`, `dirty` and `hostname` included, so running the tests twice finds
nothing new to commit.

## The table

`.purlin/tests.md` is rendered again from every file under
`.purlin/evidence/` on each run, one row per feature from its newest section
in either source:

```
| Feature | Rules | Passed | Failing | No test | Last run |
```

`Passed` counts the rules that section reads `passed`, which are those every
tied test of which ran and passed, `Failing` those it reads `failed`, and `No
test` every other rule. `Last run` is `<sha7> · <at> · <system> · <source>`,
the system reading `Windows`, `macOS` or `Linux/Unix`. The table is tracked
beside the evidence.

## The two commits

`purlin:test` and `purlin:audit` write the files and the table and do not
commit them. With `--commit` they make two commits in one step, under the
person's own identity. The first carries the work the results describe: the
spec of each feature run, the test files carrying their markers and
`.purlin/config.json`, where any of them changed:

```
purlin: specs, tests and settings for <feature>[, <feature>...]
```

The run prints `Committed <sha7>, the work these results describe:` and then
each file that commit changed, one per line, indented two spaces. Where none
changed it makes no such commit and prints nothing.

The second carries the files under `local/`, the table and any file the run
removed:

```
purlin: evidence at <sha7>
```

where `<sha7>` is the first seven characters of the first commit, or of
`HEAD` when there was nothing to commit first. The run prints `Evidence
committed.`, or `Evidence unchanged.` when no file changed and there was
nothing to commit. Neither command ever pushes.

A remote runner always commits, with the same subject, through the git
host's API, because its evidence exists nowhere else. It commits its `ci/`
files alone; the table is rendered again by the next run on a person's
machine.
