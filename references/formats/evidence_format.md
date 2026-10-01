> Format-Version: 9

# Evidence format

The evidence is what a test run and an audit leave behind for one feature:
each proof's result on each operating system, the machine the tests ran
on, the commit and the time, and,
once an audit has read the feature, what the audit found for each rule.
There is one JSON file per feature per source, and a reader parses it to
decide every rule's cells.

```
.purlin/evidence/local/<feature>.json   a person's own run
.purlin/evidence/ci/<feature>.json      a project's own run on another system
```

All of them are tracked. Nothing under `.purlin/evidence/` is gitignored,
because the point of the files is that somebody who did not make the run can
read them.

## The two folders

**The folder is the source.** A file under `local/` is written by
`purlin:test` and `purlin:audit` on a person's machine and committed under
that person's own git identity. A file under `ci/` is written only by
`scripts/run/purlin_run.py --ci`, which a project's own run on another
system runs. With `--commit` that run commits the file under the git
identity its checkout sets, and the results come back with `git pull`.

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
      "email": "jane@example.com",
      "machine": "jane-mbp",
      "fingerprint": {"spec": "<sha256>", "code": "<sha256>", "tests": "<sha256>"},
      "rules": {"RULE-1": "passed", "RULE-2": "no test"},
      "proofs": [
        {"id": "PROOF-1", "rule": "RULE-1", "result": "pass", "env": null,
         "manual": false, "test": "tests/test_login.py::test_rejects_a_wrong_password"},
        {"id": "PROOF-2", "rule": "RULE-2", "result": "nothing to check",
         "reason": "this project has no screens", "env": null, "manual": false,
         "test": "tests/test_login.py::test_every_screen_has_a_title"}
      ]
    }
  },
  "audit": {
    "rules": {
      "RULE-1": {"rule_hash": "<sha256>", "proof_hash": "<sha256>",
                 "test_hash": "<sha256>", "verdict": "strong", "findings": [],
                 "breaks": {"PROOF-1": {"file": "src/login.py", "line": 12,
                                        "before": "return check(password)",
                                        "after": "return True",
                                        "result": "caught", "why": "",
                                        "break_key": "<sha256>"}},
                 "explanation": ["The test types a wrong password and reads the refusal."],
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
| `commit` | string | the full sha of the code the section describes: `HEAD` after the run's own commit of the specs, tests and settings where `--commit` made one, else `HEAD` when the run started |
| `dirty` | bool | whether the working tree had changes that were not committed. It is shown and not compared: the fingerprint is what decides |
| `at` | string | ISO 8601 UTC with `Z`, when the run finished |
| `runner` | string | the slug of `email`, made from its part before the `@`; `unknown` where there is none |
| `email` | string | the `git config user.email` of the checkout the run was made in, or `unknown` where git has none. Kept and never compared |
| `machine` | string | where the tests ran: the host's name, or `unknown` where it reports none. Compared: a run on another machine replaces the section |
| `fingerprint` | object | `spec`, `code` and `tests`, three sha256 hex strings. See "The fingerprint" |
| `rules` | object | `RULE-N` to one word for what this run saw |
| `proofs` | array | one entry per (proof, test) pair |

A section carries the same fields under either source. A `ci` section
answers only for the proofs tagged `@env` for the system it was taken on:
its `proofs` list those proofs alone, and its `rules` the rules they prove.
A feature with no such proof gets no `ci` file from that run.

Each `rules` value:

| Word | What it means |
|---|---|
| `failed` | a tied test of a proof that could run here failed, or a test marked with the rule's id failed |
| `no test` | else, a proof of the rule that is not `@manual`, tagged `@env` or not, has no test tied to it; or no proof names the rule and no test is marked with its id |
| `not run` | else, a tied test did not run, a proof of the rule is tagged `@env` for another operating system, so this machine could not answer, or the run left out the test of a proof tagged `@slow` |
| `passed` | else: every test tied to every proof of the rule that could run here ran and passed; for a rule with no proof, every test marked with the rule's own id passed |

The words are read in that order. A rule whose proofs are all `@manual`
reads `passed`, since no run was ever going to observe one. A proof that
reads `nothing to check` counts as passed in an anchor's section and as not
run in any other.

Each `proofs` entry:

| Field | Type | What it holds |
|---|---|---|
| `id` | string | `PROOF-N`, or `RULE-N` for a test marked with the id of a rule that has no proof |
| `rule` | string | the `RULE-N` the proof covers, the same as `id` for a rule-marked test |
| `result` | string | `pass`, `fail`, `missing`, `not run` or `nothing to check` |
| `env` | string or null | the operating system the proof's `@env` tag names, or null |
| `manual` | bool | whether the proof is tagged `@manual` |
| `test` | string | `<file>::<name>` for the test that observed the proof, `""` when nothing did. The name is the test's own, as the marker format spells it |
| `reason` | string | present only where `result` is `nothing to check`: the text after `nothing to check: ` in the reason the test's tool gave for its skip |

A test is tied to its proof by the marker comment above it, as
`references/formats/marker_format.md` says. A proof whose test was skipped, or
that no case in the report is, reads `missing` with the test named. A proof
whose every tied test skipped with a reason starting exactly `nothing to
check:` reads `nothing to check` instead, each entry carrying its `reason`;
in an anchor's section its rule reads `passed`, and in any other spec's
section `not run`. A proof
tagged `@env` for another operating system than the section's reads `not run`
whatever its tied test did there: a test carrying a Mac proof's marker and a
Windows proof's marker runs on the Mac and proves only the Mac proof. A proof
no test is tied to has one entry with an empty `test`, reading the same way.
A proof tagged `@slow` whose test the run left out reads `not run` with the
test named, unless the section the run replaces was taken over the same
fingerprint and holds a result for that test: then the entry keeps that
result.

A reader takes a proof's result in a section as the worst of its entries:
`fail` where one failed, else `not run` where one reads `missing` or `not
run`, else `nothing to check` where one reads so, with its `reason`, else
`pass`. A proof has passed only when every test tied to it ran and
passed.

### The audit

| Field | Type | What it holds |
|---|---|---|
| `audit.rules` | object | `RULE-N` to the audit of that rule. `audit` holds `rules` alone |

Each `audit.rules` entry:

| Field | Type | What it holds |
|---|---|---|
| `rule_hash` | string | sha256 of the rule text the audit read |
| `proof_hash` | string | sha256 of the proof texts the audit read |
| `test_hash` | string | sha256 of the sorted lines `<file> <test name> <sha256 of the test's source>`, one per test tied to the rule's proofs, the source as the marker format bounds it with line ends read as `\n`; a test of an `exit` suite, or one not found by its name, gives `<file> <test name> <blob id>` |
| `verdict` | string | `strong` or `weak` |
| `findings` | array of strings | one sentence per finding; empty when the audit found nothing |
| `breaks` | object | `PROOF-N` to the bug the audit planted for that proof: `file`, `line`, `before`, `after`, `result` (`caught`, `survived` or `not made`), `why` (empty where there is no reason) and `break_key`, the sha256 that says whether the proof needs a new bug. `{}` for an anchor's rule |
| `explanation` | array of strings | the model's reading of the rule's tests, one sentence per line. It sets no verdict |
| `model` | string | the model that answered, its name and version as the `claude` command's JSON reports them, or `unknown` where it reports none |
| `criteria` | string | sha256 of `references/review_criteria.md` as it was sent to the model |
| `at` | string | ISO 8601 UTC with `Z` |
| `commit` | string | the full sha of `HEAD` when the audit ran |
| `notes` | array of strings | optional: one sentence per proof the audit found longer than the standard or holding two cases. Present only when there are some. A note does not make the rule weak |

`verdict` is `weak` when a heuristic spot test fired on one of the rule's
tests or a planted bug survived, each finding one sentence, and `strong`
otherwise. `strong` is written only where the model was reached. A rule the
model could not be reached for, for a planted bug or for its reading, gets no
entry at all, so the next audit reads it again, unless a spot test fired on
one of its tests or a kept planted bug survived: it is then written `weak`,
with the model `unknown` and no bug recorded for a proof the model was not
reached for.

`model` and `criteria` name the model that gave the explanation and the
instructions it was given. The evidence package carries each rule's
`verdict`, `findings`, `breaks` and `explanation` as they stand at the commit
it describes.

Two entries are the same when their three hashes, `verdict`, `findings`,
`model` and `criteria` are: an audit that repeats the entry on file leaves it
as it was, `at` and `commit` included, and one that differs in any of them
replaces it.

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
| `spec` | the spec's own rule and proof lines. A rule line is `<spec> <RULE-N> <text>`; a proof line is `<spec> <PROOF-N> <rules> <text>`, then `@manual`, `@slow` and `@env(<os>)` where the proof carries them. `> Description:` and the other metadata fields are not covered |
| `code` | for a feature, the tracked files the `> Scope:` entries reach, each as `<path> <blob>`. A file names itself, a directory names every tracked file under it, and an entry holding `*`, `?` or `[` is a git glob, so `scripts/**/*.py` reaches every Python file under `scripts/`. For an anchor, every tracked file but the records Purlin writes: `.purlin/evidence/` whole, the results, the evidence package and its sign-offs. Any other change to the project changes it; writing a record does not |
| `tests` | every tracked test file carrying a marker for the feature, each as `<path> <blob>`. A test file is one a suite of the `tests` setting names |

A file git does not track is in no part: it would change the fingerprint on
the one machine that holds it and nowhere else. It joins the fingerprint once
`git add` tracks it, and until then Purlin names it when it sits under the
feature's scope or in the directory of one of its marker files.

A feature spec with no `> Scope:` line names no files. Its `code` part is
the sha256 of the empty string, and its sections are compared on `spec` and
`tests` alone. A scope entry that reaches no tracked file, a path that does not exist
or a glob that matches nothing, is named and adds nothing.

A section is **current** when all three of its stored parts equal a
fingerprint taken now. Otherwise it is `out of date`, and the reason names
each part that differs: `code changed since 4f1c2ab`, `spec changed since
4f1c2ab`, `tests changed since 4f1c2ab`, where the sha is the section's
`commit`. Only current sections decide a rule's passed cell.

## How a writer merges

- A test run reads the file from disk and replaces `platforms[<this os>]`
  whole, so a run on another machine replaces the results of the one before.
  Every other section and `audit` stay as they are. One result is carried
  from the section replaced into the new one: that of a slow proof's test
  the run left out, where both sections have the same fingerprint.
- An audit run first makes the same test-run write. It then replaces
  `audit.rules[<rule>]` for each rule it read and leaves every other entry as
  it is.
- Every write drops the `rules` and `audit.rules` entries of rules the spec no
  longer carries.
- A test run over a file a merge left conflicted, which is not JSON, writes it
  afresh and keeps from both sides each `audit.rules` entry whose `rule_hash`,
  `proof_hash` and `test_hash` equal the rule's current ones, the newer `at`
  where both hold one.
- Every run deletes the files under `local/` and `ci/` whose feature has no
  spec.
- A `--ci` run merges the same way: it replaces its own system's section
  of the `ci/` file on disk and leaves every other section as it was. Two
  systems in one pipeline run one after the other, each on the branch as
  the one before left it.

## Retention

A file keeps the newest section per operating system and the newest audit
entry per rule. The history is the file's `git log`. Nothing is pruned.

A run that sees the same results over the same fingerprint on the same
`machine` as the section already there leaves the file byte for byte as it
was, `at`, `commit`, `dirty` and `email` included, where every
commit from the one the section names to the run's own changes only paths
under `.purlin/`, so a second run finds nothing new to commit. Any other
section replaces it, with its own `at`, `commit`, `dirty` and `email`.

## The two commits

`purlin:test` and `purlin:audit` write the files and do not commit them. With `--commit` they make two commits in one step, under the
person's own identity. The first carries the work the results describe: the
spec of each feature run, the test files carrying their markers and
`.purlin/config.json`, where any of them changed:

```
purlin: specs, tests and settings for <feature>[, <feature>...]
```

The run prints `Committed <sha7>, the work these results describe:` and then
each file that commit changed, one per line, indented two spaces. Where none
changed it makes no such commit and prints nothing.

A run that selected nothing to run still makes the first commit, of every
spec, every test file carrying a marker and `.purlin/config.json` that
changed. Its subject names each feature whose spec or marked tests it holds;
where it holds only the settings, the subject is:

```
purlin: specs, tests and settings
```

The second carries the files under `local/` and any file the run removed:

```
purlin: evidence at <sha7>
```

where `<sha7>` is the first seven characters of the first commit, or of
`HEAD` when there was nothing to commit first. The run prints `Evidence
committed.`, or `Evidence unchanged.` when no file changed and there was
nothing to commit. Neither command ever pushes.

A `--ci` run writes its `ci/` files and does not commit them. With
`--commit` it makes one commit, of the files under `ci/` and any evidence
file the run removed and nothing else, under the git identity set in that
checkout, with the same subject, where `<sha7>` names `HEAD` when the run
started. It prints `Evidence committed.` or `Evidence unchanged.` the same
way, and it never pushes.
