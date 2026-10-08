> Format-Version: 18

# Evidence format

The evidence is what a test run and an audit leave behind for one feature:
each proof's result on each operating system, what the suite's report holds
for each test, each model run of an AI proof's test on each model it names, the
machine the tests ran on, the commit and the time, and,
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
         "manual": false, "test": "tests/test_login.py::test_rejects_a_wrong_password",
         "reported": {
           "cases": [{"name": "test_rejects_a_wrong_password",
                      "class": "tests.test_login", "outcome": "pass",
                      "duration": 0.012}],
           "report": {"file": ".purlin/runtime/reports/pytest.xml",
                      "sha256": "<sha256>"}}},
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
                 "bugs": {"PROOF-1": {"aim": "past the test",
                                        "case": "a wrong password; the proof says refused; the changed code signs in",
                                        "file": "src/login.py", "line": 12,
                                        "before": "return check(password)",
                                        "after": "return True",
                                        "result": "caught", "why": "",
                                        "bug_key": "<sha256>"}},
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
| `not run` | a tied test did not run; or a proof of the rule is tagged `@env` for another operating system, so this machine could not answer; or the run left out the test of a proof tagged `@slow`; or an AI proof of the rule holds no passing result on one of its models |
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
| `reported` | object | optional: what the suite's report holds for the test, `{cases, report}`. See "What the report held" |
| `carried` | object | optional: present only on an entry whose result the run that wrote the section's `commit` did not take. It names the run that took the result: `commit`, the full sha, `at`, `machine` and `email`, as that run's section held them. An entry with no `carried` was taken by the run the section names. See "Carried forward" |
| `models` | array | present only on an entry of an AI proof, one tagged `@ai`, whose test a run has started: one entry per model the tag names, in the tag's order. See "The models of an AI proof" |

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
- **`not run`**, with the test named, where the proof is an AI proof and one
  of its models holds no passing result: no run has started its test, a
  model gave no answer, or a model holds fewer model runs than are asked. See
  "The models of an AI proof".

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

### What the report held

`reported` keeps what the test tool itself reported for one test, beside the
result Purlin reads from it:

```json
"reported": {
  "cases": [
    {"name": "test_total[uk]", "class": "tests.test_cart", "outcome": "pass",
     "duration": 0.004},
    {"name": "test_total[fr]", "class": "tests.test_cart", "outcome": "fail",
     "duration": 0.011,
     "text": "AssertionError: assert 4 == 5\n\ndef test_total(country):\n>       assert total(country) == 5\nE       AssertionError: assert 4 == 5\n\ntests/test_cart.py:9: AssertionError"}
  ],
  "report": {"file": ".purlin/runtime/reports/pytest.xml", "sha256": "<sha256>"}
}
```

| Field | Type | What it holds |
|---|---|---|
| `cases` | array | one entry per case of the report tied to the test, in the report's order. A test that is not parametrised has one |
| `report` | object or null | `{file, sha256}`: the report file the first case was read from, relative to the project root, `-` for the command's standard output, and the sha256 of that file's bytes as the suite left it. Null where the bytes could not be read |

Each `cases` entry:

| Field | Type | What it holds |
|---|---|---|
| `name` | string | the case's name as the report gives it: `test_total[uk]`, `cart > adds two prices`, `Total(country: "uk")`, `TestTotal/uk` |
| `class` | string | optional: the class, module or package the report names for the case. Left out where it names none |
| `outcome` | string | `pass`, `fail`, `error` or `skip`. `error` is a case its tool reports as an error and not as a failure: the test stopped, in its setup say, before it could fail. Purlin reads both `fail` and `error` as `fail` |
| `duration` | number | optional: how long the case took, in seconds, as the report gives it. Left out where the report gives none |
| `text` | string | optional: for `fail` and `error`, the whole text the report holds for it; for `skip`, the reason the tool gave. Left out where the report holds none, and for `pass` |
| `cut` | int | optional: present only where `text` was longer than 20,000 characters. The text then holds its first 10,000 and its last 10,000 characters around the line `[... <n> characters cut ...]`, and `cut` is `<n>` |

`references/formats/marker_format.md`, "The four report formats", says
where each format holds a case's duration and its text. What each gives:

| Format | `duration` | `text` for a failure |
|---|---|---|
| `junit` | the case's `time`; left out where the writer adds none | each `failure` and `error` child's `message` and text |
| `trx` | the result's `duration`; left out where it has none | the result's error `Message` and `StackTrace` |
| `gotest` | the event's `Elapsed`; left out where it has none | what the test printed |
| `exit` | none | none |

An `exit` suite writes no report, so its entries hold no `reported`. Neither
does an entry whose test the run left out, one whose proof is tagged `@env`
for another operating system, one with an empty `test`, or one whose test
the report holds no case for.

A result carried forward keeps the `reported` it had when it was taken: its
durations, its texts and the report it names are those of the run its
`carried` names.

**The report file.** A run keeps each report file it read on the machine
that ran it, as `.purlin/runtime/kept/<sha256><extension>`, the bytes as the
suite left them and the extension the report's own. `.purlin/runtime/` is
ignored by git, so the file is not committed there. A run removes each kept
file whose sha256 no evidence file on disk names. At the first sign-off of a
version `purlin:sign` commits, beside the evidence package, each report the
package lists that the signing machine still keeps
(`references/formats/package_format.md`, "Outputs"). A report taken on
another machine, or removed since, is not there to commit, and the evidence
still names it by its sha256.

### The models of an AI proof

An AI proof is one tagged `@ai(<model>, ...)`. Its test is started alone,
once per model run, on each model the tag names, and its entry holds what
every model run did:

```json
{"id": "PROOF-4", "rule": "RULE-2", "result": "pass", "env": null,
 "manual": false, "test": "tests/test_report.py::test_names_findings",
 "models": [
   {"model": "claude-opus-5-5", "passed": 3, "of": 3, "graded": false,
    "runs": [
      {"result": "pass", "output": "<sha256>", "made": "helper",
       "reported": {"cases": [{"name": "test_names_findings",
                               "class": "tests.test_report",
                               "outcome": "pass", "duration": 41.2}],
                    "report": {"file": ".purlin/runtime/reports/pytest.xml",
                               "sha256": "<sha256>"}}},
      {"result": "pass", "output": "<sha256>", "made": "helper"},
      {"result": "pass", "output": "<sha256>", "made": "helper"}]},
   {"model": "claude-sonnet-5-5", "passed": 0, "of": 3, "graded": false,
    "runs": [
      {"result": "not run", "why": "The login expired.", "made": "helper"}]}
 ]}
```

Each `models` entry:

| Field | Type | What it holds |
|---|---|---|
| `model` | string | the model, as the proof's `@ai` tag names it |
| `passed` | int | how many of `runs` read `pass` |
| `of` | int | how many model runs were asked for when they were taken: the proof's own `runs=`, else the `runs` setting, else 3 |
| `graded` | bool | whether the proof is tagged `@graded` |
| `runs` | array | one entry per model run that happened, in order, pass or fail. A failure stops none of the model runs after it. A model no test was started on holds `[]` |
| `carried` | object | optional: present only on a model whose model runs the run that wrote the section's `commit` did not take, with the same four values an entry's `carried` holds |

Each `runs` entry:

| Field | Type | What it holds |
|---|---|---|
| `result` | string | `pass`, `fail` or `not run` |
| `output` | string | the sha256 of the folder the model run wrote, taken over every file in it but `purlin.json`. Left out of a `not run` model run, and of one that wrote no file |
| `made` | string | `helper` where `purlin_ai.py run` made the output, `project` where the project's own test handed it over with `purlin_ai.py record`. Left out where the folder holds no record |
| `why` | string | present only on a `not run` model run: one sentence, the reason the helper's record gave, or `The test at <file>:<line> has no result.` where the test itself did not run |
| `reported` | object | optional: what the suite's report holds for that model run, as "What the report held" gives it |
| `grade` | object | present only where the helper's record holds one: `model`, the grader, `accepted`, true, false, or null where the grader gave no answer, and `reason`, its one sentence |

A model run reads `not run`, whatever its test did, where the helper's record
reads `reached` false or holds a `grade` whose `accepted` is null: a model
gave no answer. The run starts no further test on that model, or graded by
that grader, so the models it would have asked hold fewer model runs than `of`.

A reader works out three words from these fields, each against the model
runs asked for now, which a changed `runs` setting changes:

- **A model** reads `failed` where one of its model runs reads `fail`;
  else `not run` where one reads `not run` or it holds fewer than are asked
  now; else `passed`.
- **The entry** reads `fail` where a model reads `failed`, else `not run`
  where a model reads `not run`, else `pass`. The run writes that as the
  entry's `result`, against the model runs asked when it ran.
- **The rule** reads from its proofs as any rule does.

An entry of an AI proof whose test no run has started holds no `models` and
reads `not run`.

**The output folder.** Each model run writes to
`.purlin/runtime/ai/<feature>/<PROOF-N>/<model>/<n>/`, `<n>` the model run
from 1,
and the second and each later test of one proof to `<n>.<t>`. A character
of the model's name that is not a letter, a digit, `.`, `_` or `-` is
written `_`. The run empties the folder before each model run. The folder holds
`reply.md`, `transcript.jsonl`, `files/`, `input/`, which is what the AI was
given, and `purlin.json`, the helper's record, which is no part of the
sha256. `input/` is part of it, so one sha256 names what the AI produced
together with what it was given. `.purlin/runtime/` is ignored by
git, so the folder stays on the machine that ran the test, found by its
sha256. A run removes each such folder whose sha256 no evidence file on
disk names.

**What a run keeps.** A run that does not start an AI proof, which is every
run but `purlin:test --all`, `purlin:test --clean`, a settle of the proof's
rule and a project's own run on another system, keeps the entry the section
it replaces holds, `models` included, where both sections have the same
fingerprint. The entry and each model hold `carried`. `purlin:test --all`
and a settle keep, the same way, each model that passed every model run asked
for now, and start the test on the other models alone; each kept model holds
`carried` and the entry holds none unless every model was kept.
`purlin:test --clean` and a project's own run on another system start every
model.

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
| `bugs` | object | `PROOF-N` to the bug the audit planted for that proof: `aim` (`past the test` or `plain`), `case` (the model's one line saying which case of the proof the bug breaks, at most 300 characters, empty where it gave none), `file`, `line`, `before`, `after`, `result` (`caught`, `survived`, `not made` or `not run`), `why` (empty where there is no reason) and `bug_key`, the sha256 that says whether the proof needs a new bug. Three fields are optional: `test_key`, on a `survived` bug alone, the sha256 of the proof's own tests when the bug got past them; `test_unchanged`, present and `true` only where a settle went on with the proof's test as it was; and `output`, on the bug of an AI proof alone, the sha256 of the kept output folder the wrong output was planted in, `file` then being a path inside that folder. A proof the model could not be reached for, or one tagged for another system, has no entry. `{}` for an anchor's rule |
| `explanation` | array of strings | the model's reading of the rule's tests, one sentence per line. It sets no verdict |
| `model` | string | the model that answered, its name and version as the `claude` command's JSON reports them, or `unknown` where it reports none |
| `criteria` | string | sha256 of `references/review_criteria.md` as it was sent to the model |
| `at` | string | ISO 8601 UTC with `Z` |
| `commit` | string | the full sha of `HEAD` when the audit ran |
| `notes` | array of strings | optional: one sentence per proof the audit found longer than the standard or holding two cases. Present only when there are some. A note does not make the rule weak |

`references/review_criteria.md`, "The verdict", says what sets `verdict`.
Under `spot-checked`, `no_bug` says why no bug was planted and caught.

A planted bug's `result` is `caught` when the proof's test ran and failed with the
bug in place, `survived` when it still passed, `not made` when the change
could not be made, and `not run` when the test did not run with the bug in
place, or ended in an error its tool does not report as a failure, which is
neither caught nor survived. For such an error `why` reads
`the test ended in an error, not a failure`.

`references/review_criteria.md`, "Settling a finding", says what
`purlin:audit <feature> RULE-N --settle` does. What it leaves in the entry:

- A bug the test now catches reads `caught`, with the same change.
- Where the test still passes and one new bug survives too, no bug is kept:
  `result` reads `not made`, `why` reads
  `two planted bugs left the proof's check passing`, `file`, `line`,
  `before` and `after` are null, and `no_bug` holds
  `No bug was caught for PROOF-N: two planted bugs left the proof's check passing.`
  A dropped bug is in no field.
- A proof whose last result was not `survived` and was taken on another test
  or code has no entry under `bugs`, so the next audit plants a bug for it.
- An entry settled without a model being asked keeps the `model` and
  `criteria` of the entry it replaces, and its `explanation` is empty.
- Under `--sound PROOF-N` the proof's entry holds `test_unchanged`: `true`,
  whatever its `result`, unless a new bug for it reads `survived`, and
  `no_bug` holds
  `PROOF-N was settled with its test unchanged: it was judged to assert what the proof names.`
  Both stay while the entry is kept, and go when a later audit plants a new
  bug for the proof. Where the model could not be reached for the new bug,
  the proof has no entry and `no_bug` holds the sentence alone. `--sound`
  for a proof whose test did change writes neither.

`test_key` says whether a proof's test changed since its bug got past it.
It is the sha256 of the sorted lines `<file> <test name> <sha256 of the
test's source>`, one per test tied to that proof, the source as the audit
reads it: the test's own lines, not its file. `bug_key` covers the
feature's code as well, so it cannot tell a changed test from changed code.

`purlin:test --all` and `purlin:test --clean` write an anchor's entries
again (`references/review_criteria.md`, "Anchors and rules with no proof").
Such an entry reads `spot-checked` or `weak`, holds no bug, and keeps the
`model` and `criteria` of the entry it replaces. It keeps that entry's
`explanation` and `notes` where the rule, its proofs and its tests are as
that entry read them, and holds neither where one of them changed.

A rule the model could not be reached for is written with the model `unknown`
and no bug recorded for a proof the model was not reached for, so the next
audit reads it again.

`model` and `criteria` name the model that gave the explanation and the
instructions it was given. The evidence package carries each rule's
`verdict`, `findings`, `bugs` and `explanation` as they stand at the commit
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

`references/evidence_and_signoff.md`, "Which evidence counts", says which
features `purlin:test --all` runs and which it carries forward: it records a
carried feature's results again on the run's own commit and runs none of its
tests. This section gives the test a section must meet and what is written.

A section is carried forward where its stored fingerprint equals the one
taken now and its `dirty` is false. The run writes the section again:

- `commit` is the run's own, as it would write for a section it took.
- Every `proofs` entry holds `carried`, the `commit`, `at`, `machine` and
  `email` of the run that took the result: the `carried` the entry already
  held, else the section's own four values as they stood. So a result
  carried a second time still names the run that took it. Each model under
  an entry's `models` holds `carried` the same way.
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
files; and where it is an anchor. An AI proof's result is read there against
the model runs asked for now, so a feature runs again once the `runs` setting
asks for more than a model holds.

## The fingerprint

A fingerprint says what a section was taken over. Each part is a sha256 hex
string, and every file is read from the working tree with `git hash-object`,
so an edit counts before it is committed.

| Part | What it covers |
|---|---|
| `spec` | the spec's own rule and proof lines. A rule line is `<spec> <RULE-N> <text>`; a proof line is `<spec> <PROOF-N> <rules> <text>`, then `@manual`, `@slow` and `@env(<os>)` where the proof carries them; an AI proof's line reads `@slow` and ends `@ai(<models>)`, the models joined by `,` with `runs=<n>` after them where the proof sets it, then `@graded(<grader>)` where it names one, so another model, another count or another grader puts the section out of date. `> Description:` and the other metadata fields are not covered |
| `code` | for a feature, the tracked files the `> Scope:` entries reach, each as `<path> <blob>`. A file names itself, a directory names every tracked file under it, and an entry holding `*`, `?` or `[` is a git glob, so `scripts/**/*.py` reaches every Python file under `scripts/`. For an anchor, every tracked file but the records Purlin writes, `.purlin/evidence/` whole, the results, the evidence package and its sign-offs, and but the settings file `.purlin/config.json`, whose `tests` setting the `tests` part covers. Any other change to the project changes it; writing a record does not, and neither does changing the settings file's `version` |
| `tests` | every tracked test file carrying a marker for the feature, each as `<path> <blob>`, and, where `.purlin/config.json` holds `tests`, the line `tests-setting <sha256>`, the sha256 of that setting as JSON with sorted keys and no spaces. A test file is one a suite of the `tests` setting names. The setting is read from the working tree, so changing a suite's command puts every feature's sections out of date on `tests`; the file's layout and its other keys, `version` and `runs` included, change nothing |

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
  Every other section stays as it is, and so does `audit`, but for an
  anchor's entries under `purlin:test --all` and `--clean`, as "The audit"
  says. One result is carried
  from the section replaced into the new one: that of a slow proof's test
  the run left out, where both sections have the same fingerprint. Its
  entry is marked `carried`. An AI proof's models are carried the same way,
  as "The models of an AI proof" says.
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
  spec, and prints `Removed <path>: no spec defines <feature>.` No other
  file is deleted: the history is the file's `git log`.
- A `--ci` run merges the same way: it replaces its own system's section
  of the `ci/` file on disk and leaves every other section as it was. Two
  systems in one pipeline run one after the other, each on the branch as
  the one before left it.

**A run that sees nothing new writes nothing.** A run that sees the same
results over the same fingerprint on the same `machine`, with the same
`dirty`, as the section already there leaves the file byte for byte as it
was, `at`, `commit` and `email` included, where every commit from the one
the section names to the run's own changes only paths under `.purlin/`, so
a second run finds nothing new to commit. Any other section replaces it,
with its own `at`, `commit`, `dirty` and `email`. Two things are left out
of that comparison:

- `carried`, on an entry or a model, where the run carried the result
  forward: the file stays as it was, with no `carried` in it. A result the
  run took itself replaces one the section on disk holds as `carried`.
- Each case's `duration` and the `report` of a `reported`, a model run's
  included: they say when a run happened, not what it saw. A section left
  as it was keeps the durations and the report of the run that wrote it,
  and that report stays kept.

Everything else is compared: the cases' names, outcomes and texts, and each
model run's `result`, `output`, `made`, `why` and `grade`. A test that fails
with another text, or a model run that wrote another output, replaces the
section.

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
