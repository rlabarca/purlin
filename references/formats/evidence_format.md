> Format-Version: 15

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
that person's own git identity. A file under `ci/` holds the sections
`scripts/run/purlin_run.py --ci` writes, which a project's own run on another
system runs. With `--commit` that run commits the file under the git
identity its checkout sets, and the results come back with `git pull`. A
`purlin:test --all` run takes no result into `ci/`; it records a section
there again only to carry it forward. See "Carried forward".

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
      "rules": {"RULE-1": "passed", "RULE-2": "not run"},
      "proofs": [
        {"id": "PROOF-1", "rule": "RULE-1", "result": "pass", "env": null,
         "manual": false, "test": "tests/test_login.py::test_rejects_a_wrong_password"},
        {"id": "PROOF-2", "rule": "RULE-2", "result": "nothing to check",
         "reason": "this project has no screens", "env": null, "manual": false,
         "test": "tests/test_login.py::test_every_screen_has_a_title"},
        {"id": "PROOF-3", "rule": "RULE-1", "result": "pass", "env": null,
         "manual": false, "test": "tests/test_login.py::test_a_thousand_logins",
         "carried": {"commit": "9b2e7c4d1a6f3e8b5c0d2a7f4e1b6c3d8a5f2e9b",
                     "at": "2026-09-26T09:30:00Z", "machine": "jane-mbp",
                     "email": "jane@example.com"}}
      ]
    }
  },
  "audit": {
    "rules": {
      "RULE-1": {"rule_hash": "<sha256>", "proof_hash": "<sha256>",
                 "test_hash": "<sha256>", "code_hash": "<sha256>",
                 "verdict": "strong", "findings": [], "no_bug": [],
                 "breaks": {"PROOF-1": {"aim": "past the test",
                                        "case": "a wrong password; the proof says refused; the changed code signs in",
                                        "file": "src/login.py", "line": 12,
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
| `commit` | string | the full sha of the code the section describes: `HEAD` after the run's own commit of the specs, tests and settings where `--commit` made one, else `HEAD` when the run started. A run that carries the section forward writes its own here |
| `dirty` | bool | whether the working tree had changes that were not committed, outside `.purlin/`. It decides no cell: the fingerprint does. A run over a tree whose `dirty` differs replaces the section |
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

Each `rules` value is one word. The rows are read from the top, and the
first that holds gives the word:

| Word | When it holds |
|---|---|
| `checked at sign-off` | every proof of the rule is `@manual`: no test is written for it, so no run observes it and a person checks it in the sign-off walk |
| `failed` | a tied test of a proof that could run here failed; or a test marked with the rule's id failed |
| `no test` | a proof of the rule that is not `@manual` has no test tied to it, whether it is tagged `@env` or not; or no proof names the rule and no test is marked with its id |
| `not run` | a tied test did not run; or a proof of the rule is tagged `@env` for another operating system, so this machine could not answer; or the run left out the test of a proof tagged `@slow` |
| `passed` | none of the rows above holds: every test tied to every proof of the rule that could run here ran and passed. For a rule with no proof, every test marked with the rule's own id passed |

Where a `@manual` proof stands beside a proof that is not `@manual`, the
rule reads from the rows below the first. A proof that reads `nothing to check` counts as passed
in an anchor's section and as not run in any other.

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
| `carried` | object | optional: present only on an entry whose result the run that wrote the section's `commit` did not take. It names the run that took the result: `commit`, the full sha, `at`, `machine` and `email`, as that run's section held them. An entry with no `carried` was taken by the run the section names. See "Carried forward" |

A test is tied to its proof by the marker comment above it, as
`references/formats/marker_format.md` says. Besides `pass` and `fail`, an
entry reads:

- **`missing`**, with the test named, where the test was skipped or the
  report holds no case for it.
- **`nothing to check`** instead, where every test tied to the proof skipped
  with a reason starting exactly `nothing to check:`. Each entry carries its
  `reason`. The proof's rule reads `passed` in an anchor's section and
  `not run` in any other spec's section.
- **`not run`** where the proof is tagged `@env` for another operating system
  than the section's, whatever its tied test did there. A test carrying a Mac
  proof's marker and a Windows proof's marker runs on the Mac and proves only
  the Mac proof.
- **`not run`**, with the test named, where the proof is tagged `@slow` and
  the run left its test out. One case differs: the section the run replaces
  was taken over the same fingerprint and holds a result for that test. The
  entry then keeps that result and holds `carried`: the `commit`, `at`,
  `machine` and `email` of the section the result was taken in, or the
  `carried` that entry already held. The section's own `commit`, `at`,
  `machine` and `email` are this run's.

A reader counts a carried result as the result it is: a carried `pass` is a
`pass` in every cell, and at a sign-off, where it counts like any other
result of a section recorded on the commit being signed.

A proof no test is tied to has one entry with an empty `test`. It reads
`missing`, or `not run` where the proof is tagged `@env` for another
operating system.

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
| `code_hash` | string | the `code` part of the feature's fingerprint when the audit read the rule |
| `verdict` | string | `strong`, `weak` or `spot-checked` |
| `findings` | array of strings | one sentence per finding; empty when the audit found nothing |
| `no_bug` | array of strings | one sentence for each proof no bug was caught for, saying why, and one for each proof settled with its test unchanged; empty where a bug was caught for every proof and none was settled so |
| `breaks` | object | `PROOF-N` to the bug the audit planted for that proof: `aim` (`past the test` or `plain`), `case` (the model's one line saying which case of the proof the bug breaks, at most 300 characters, empty where it gave none), `file`, `line`, `before`, `after`, `result` (`caught`, `survived`, `not made` or `not run`), `why` (empty where there is no reason) and `break_key`, the sha256 that says whether the proof needs a new bug. Two fields are optional: `test_key`, on a `survived` bug alone, the sha256 of the proof's own tests when the bug got past them, and `test_unchanged`, present and `true` only where a settle went on with the proof's test as it was. A proof the model could not be reached for, or one tagged for another system, has no entry. `{}` for an anchor's rule |
| `explanation` | array of strings | the model's reading of the rule's tests, one sentence per line. It sets no verdict |
| `model` | string | the model that answered, its name and version as the `claude` command's JSON reports them, or `unknown` where it reports none |
| `criteria` | string | sha256 of `references/review_criteria.md` as it was sent to the model |
| `at` | string | ISO 8601 UTC with `Z` |
| `commit` | string | the full sha of `HEAD` when the audit ran |
| `notes` | array of strings | optional: one sentence per proof the audit found longer than the standard or holding two cases. Present only when there are some. A note does not make the rule weak |

`verdict` is `weak` when a heuristic spot test fired on one of the rule's
tests or a planted bug survived, each finding one sentence. It is `strong`
when none did and a planted bug was caught by its proof's test. It is
`spot-checked` when none did and no bug was planted and caught, and `no_bug`
then says why.

A break's `result` is `caught` when the proof's test ran and failed with the
bug in place, `survived` when it still passed, `not made` when the change
could not be made, and `not run` when the test did not run with the bug in
place, or ended in an error its tool does not report as a failure, which is
neither caught nor survived. For such an error `why` reads
`the test ended in an error, not a failure`.

`purlin:audit <feature> RULE-N --settle` plants a `survived` bug again
(`references/review_criteria.md`, "Settling a finding"). Where the test then
fails, the entry reads `caught` with the same change. Where the test still
passes and one new bug survives too, no bug is kept: `result` reads
`not made`, `why` reads `two planted bugs left the proof's check passing`,
`file`, `line`, `before` and `after` are null, and `no_bug` holds
`No bug was caught for PROOF-N: two planted bugs left the proof's check passing.`
A dropped bug is in no field. A proof whose last result was not `survived`
and was taken on another test or code has no entry under `breaks` after a
settle, so the next audit plants a bug for it. An entry settled without a
model being asked keeps the `model` and `criteria` of the entry it replaces,
and its `explanation` is empty.

`test_key` says whether a proof's test changed since its bug got past it.
It is the sha256 of the sorted lines `<file> <test name> <sha256 of the
test's source>`, one per test tied to that proof, the source as the audit
reads it: the test's own lines, not its file. `break_key` covers the
feature's code as well, so it cannot tell a changed test from changed code.
A settle plants nothing for a proof whose `test_key` is the one taken now,
and the bug stays `survived`. A test whose source is not found is read as
changed.

`purlin:audit <feature> RULE-N --settle --sound PROOF-N` lets the settle go
on for such a proof. The entry the settle then writes for the proof holds
`test_unchanged`: `true`, whatever its `result`, unless a new bug for it
reads `survived`, and `no_bug` holds
`PROOF-N was settled with its test unchanged: it was judged to assert what the proof names.`
Both stay while the entry is kept, and go when a later audit plants a new
bug for the proof. Where the model could not be reached for the new bug,
the proof has no entry and `no_bug` holds the sentence alone. `--sound` for
a proof whose test did change writes neither.

A rule the model could not be reached for is written with the model `unknown`
and no bug recorded for a proof the model was not reached for, so the next
audit reads it again.

`model` and `criteria` name the model that gave the explanation and the
instructions it was given. The evidence package carries each rule's
`verdict`, `findings`, `breaks` and `explanation` as they stand at the commit
it describes.

Two entries are the same when their four hashes, `verdict`, `findings`,
`no_bug`, `model` and `criteria` are: an audit that repeats the entry on file leaves it
as it was, `at` and `commit` included, and one that differs in any of them
replaces it.

An audit entry is **current** while its `rule_hash`, `proof_hash`,
`test_hash` and `code_hash` all equal the ones taken now: the rule's text, its
proofs' text, its tests' source and the `code` part of the feature's
fingerprint. Otherwise it is out of date on each part that differs, `rule`,
`proof`, `test` or `code`, and it stays in the file. `commit` and `at` are
shown and not compared, so an entry taken at an earlier commit is still
current. Where both sources hold an entry, a current one is read before one
out of date, and then the later `at`.

## Carried forward

`purlin:test --all` runs a feature whose spec, code or tests changed since
its results here were taken, a feature whose results here are not all
passes, and every anchor. Every other feature it carries forward: it records
the feature's results again on the run's own commit and runs none of its
tests. `purlin:test --clean` runs every test and carries nothing.

A section is carried forward where its stored fingerprint equals the one
taken now and its `dirty` is false. The run writes the section again:

- `commit` is the run's own, as it would write for a section it took.
- Every `proofs` entry holds `carried`, the `commit`, `at`, `machine` and
  `email` of the run that took the result: the `carried` the entry already
  held, else the section's own four values as they stood. So a result
  carried a second time still names the run that took it.
- `at`, `runner`, `email`, `machine`, `dirty`, `fingerprint` and `rules`
  stay as they were: the section still says who took it, where and when.

A section that already names the run's commit, or a commit from which every
commit up to it changes only paths under `.purlin/` and leaves the `tests`
setting as it was, is left byte for byte as it was.

The same holds for every section of the feature's two files: the section
another operating system wrote, and one under `ci/`, are carried forward by
the same test, from whichever machine took them, whether or not the feature
itself runs on this machine. A section taken over another fingerprint, or
with `dirty` true, is left as it was, and a run on its own system takes it
again.

This system's `local` section is carried only where the feature does not
run. A feature runs, and its section is replaced, where that section is
missing, was taken over another fingerprint or with `dirty` true, or holds a
result other than `pass` for a proof this system can run; where an untracked
file sits under its scope or beside its tests; where its spec names no
files; and where it is an anchor.

## The fingerprint

A fingerprint says what a section was taken over. Each part is a sha256 hex
string, and every file is read from the working tree with `git hash-object`,
so an edit counts before it is committed.

| Part | What it covers |
|---|---|
| `spec` | the spec's own rule and proof lines. A rule line is `<spec> <RULE-N> <text>`; a proof line is `<spec> <PROOF-N> <rules> <text>`, then `@manual`, `@slow` and `@env(<os>)` where the proof carries them. `> Description:` and the other metadata fields are not covered |
| `code` | for a feature, the tracked files the `> Scope:` entries reach, each as `<path> <blob>`. A file names itself, a directory names every tracked file under it, and an entry holding `*`, `?` or `[` is a git glob, so `scripts/**/*.py` reaches every Python file under `scripts/`. For an anchor, every tracked file but the records Purlin writes, `.purlin/evidence/` whole, the results, the evidence package and its sign-offs, and but the settings file `.purlin/config.json`, whose `tests` setting the `tests` part covers. Any other change to the project changes it; writing a record does not, and neither does changing the settings file's `version` |
| `tests` | every tracked test file carrying a marker for the feature, each as `<path> <blob>`, and, where `.purlin/config.json` holds `tests`, the line `tests-setting <sha256>`, the sha256 of that setting as JSON with sorted keys and no spaces. A test file is one a suite of the `tests` setting names. The setting is read from the working tree, so changing a suite's command puts every feature's sections out of date on `tests`; the file's layout and its other keys, `version` included, change nothing |

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
  the run left out, where both sections have the same fingerprint. Its
  entry is marked `carried`.
- A `purlin:test --all` run writes again each section it carries forward,
  in either folder, as "Carried forward" says, and leaves every other
  section it did not take as it was.
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
`machine`, with the same `dirty`, as the section already there leaves the
file byte for byte as it was, `at`, `commit` and `email` included, where
every commit from the one the section names to the run's own changes only
paths under `.purlin/`, so a second run finds nothing new to commit. Any
other section replaces it, with its own `at`, `commit`, `dirty` and `email`.

`carried` is left out of that comparison in one direction: a result the run
carried forward is the result the section on disk already holds, so the file
stays as it was, with no `carried` in it. A result the run took itself
replaces an entry the section on disk holds as `carried`.

## The two commits

`purlin:test` and `purlin:audit` write the files and do not commit them. With
`--commit` a run makes two commits, the work and then the evidence, which
holds the files under `local/` and each file under `ci/` in which the run
carried a section forward.
`references/commit_conventions.md`, "The two commits of a run", says what each
commit holds and how its subject reads. This section gives what the run
prints:

| When | The run prints |
|---|---|
| It made the first commit | `Committed <sha7>, the work these results describe:`, then each file that commit changed, one per line, indented two spaces |
| No spec, test file or setting changed, so it made no first commit | nothing |
| It made the evidence commit | `Evidence committed.` |
| No evidence file changed, so there was nothing to commit | `Evidence unchanged.` |

`<sha7>` is the first seven characters of the first commit.

A `--ci` run writes its `ci/` files and does not commit them. With `--commit`
it makes the evidence commit alone, and prints `Evidence committed.` or
`Evidence unchanged.` the same way.

No run ever pushes.
