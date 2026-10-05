> Format-Version: 15

# Package format

The evidence package is one data file describing one version. It is written
for a reviewer who cannot open the repository. It holds, in this order:

- whether every rule's tests pass, the total of rules and the count that
  pass;
- what the audit found, and what is left to do;
- who ran the tests, where and when;
- every rule: its words, its proofs and its tests, each result on each
  operating system, what the audit found, and who wrote and last changed the
  rule, each proof and each test;
- every hand check.

```
.purlin/evidence/package/<version>.json
```

`purlin:sign` builds it, and nothing else writes it. The first sign-off of a
version commits it, in the same signed commit as that sign-off, and writes
the tag `signed/<version>` on that commit. A later sign-off of the version
leaves the package as committed and adds its own file beside it. The file is
tracked like the rest of `.purlin/evidence/`.

The sign-offs sit beside the package, one file per signer:

```
.purlin/evidence/package/<version>.signoffs/<signer-slug>.json
```

A sign-off never rewrites the package, so every sign-off of a version carries
the same `fingerprint`. `signature_format.md` holds the sign-off's fields.

## What the package is for

Purlin makes no claim that the software is compliant. The package is
evidence for review in a regulated document and sign-off system, such as
Veeva, which holds the controlled document, the authority to sign it off and
the signature that counts under the regulation. Purlin hands the data over;
how it is shown is the receiving system's job.

## The file name

`<version>` is the version the project states: the `VERSION` file at the
project root, else `version` in `package.json`, else the `[project]` or
`[tool.poetry]` version in `pyproject.toml`, else the `<Version>` of the
first `*.csproj` at the root. `purlin:sign --version <name>` names another,
and the file, `version` and `tag` then carry that name. Where the project
states none and `--version` names none, `purlin:sign` prints `No version:
nothing in this project states one. Run purlin:sign --version <version>, or
write it to a VERSION file.`, writes nothing and exits 1.

## What it reads

The package is built from a checkout of one commit, so it describes only what
git holds. `purlin:sign` refuses while tracked files are changed and not
committed, `.purlin/config.json` among them, while evidence is written and
not committed, and over a result whose section reads `dirty`, taken while
files were changed and not committed.

That commit is the one the evidence was taken at: `HEAD`, stepping back over
any commit that changed nothing but files under `.purlin/evidence/package/`,
a sign-off included. A package names the commit below the one that carries
it, because a file cannot name the commit that contains it, and a package
built at the tag again reads the same commit.

## Fields

```json
{
  "schema": "purlin-package/4",
  "met": true,
  "rules": 42,
  "steps": {"passed": 41},
  "audit": {"not_audited": 3, "out_of_date": 1, "spot_checked": 3,
            "strong": 32, "weak": 2},
  "left": [
    {"command": "purlin:build", "count": 2, "kind": "to_strengthen",
     "text": "2 rules to strengthen"}
  ],
  "purlin_version": "0.10.0",
  "project": "labconnect",
  "version": "0.1.0",
  "tag": "signed/0.1.0",
  "commit": "1cf829e4b2d9c8e7f6a5b4c3d2e1f0a9b8c7d6e5",
  "runs": [
    {"at": "2026-10-01T12:17:13Z", "by": "dana.dev@labconnect.example",
     "commit": "1cf829e4b2d9c8e7f6a5b4c3d2e1f0a9b8c7d6e5",
     "carried": false, "machine": "dana-laptop", "os": "linux",
     "rules": 42, "source": "local"}
  ],
  "features": [],
  "hand_checks": [
    {"checked": "in the sign-offs", "feature": "accession_screen",
     "proofs": ["PROOF-3"], "rule": "RULE-2"}
  ],
  "warnings": [],
  "fingerprint": "<sha256>"
}
```

The top-level keys appear in exactly this order, and every one is REQUIRED.
Whether the tests are met is the first thing a reader sees after the schema.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-package/4` |
| `met` | bool | true when no line of `left` is of a kind that stops the tests being met. See "Met" |
| `rules` | int | the rules of the project, each counted once under the feature that owns it |
| `steps` | object | `{"passed": p}`: the rules whose `passed` status reads `passed` |
| `audit` | object | `{"strong", "weak", "spot_checked", "out_of_date", "not_audited"}`, as `purlin:status` counts them: the rules that pass their tests and have a tested proof, each counted once under the word its `strong` status reads, `strong`, `weak`, `spot-checked`, `out of date` or `not audited`. A rule whose `passed` status does not read `passed` is in none of the five, and neither is a rule checked by hand, whose `strong` status reads `checked at sign-off` |
| `left` | array | the lines of `Left to do`, in the order the work is done: `{kind, count, text, command}` each. See "What is left" |
| `purlin_version` | string | the version of Purlin that wrote the package |
| `project` | string | the name the project's own files give it, read when the package is built: `name` under `[project]` or `[tool.poetry]` in `pyproject.toml`, `name` in `package.json`, the first root `*.csproj` file's name, the last segment of the `origin` remote, else the folder's name |
| `version`, `tag` | string, string | the version the file is named for, and `signed/<version>` |
| `commit` | string | the full sha the evidence was taken at. See "What it reads" |
| `runs` | array | one entry per group of results sharing a source, a system, who took them, a machine and whether they were carried forward. See "Runs" |
| `features` | array | one entry per spec, ordered by name |
| `hand_checks` | array | one entry per rule with a `@manual` proof, by feature then rule number. See "Hand checks" |
| `warnings` | array of strings | each warning reading the specs and the evidence raised. A warning about a `signed/*` tag is not among them: a tag is a checkout's own, and one commit gives the same bytes in every clone |
| `fingerprint` | string | sha256 hex. See "The fingerprint" |

### Runs

Each `runs` entry, local first, then by system in the order `linux`, `macos`,
`windows`, the results a run took before the ones it carried forward:

| Field | Type | What it holds |
|---|---|---|
| `by` | string | the email of the run that took the results, or `unknown` where the evidence records none |
| `machine` | string or null | the host's name of the run that took the results |
| `os` | string | `windows`, `macos` or `linux` |
| `source` | string | `local` or `ci` |
| `at` | string | when the newest of the runs that took the group's results finished |
| `commit` | string | the full sha that run's tests ran at |
| `rules` | int | how many rules the group holds a result for |
| `carried` | bool | true for results an earlier run took and a later run carried forward: `by`, `machine`, `at` and `commit` then name the newest of the runs that took them. False for results the run that recorded them took |

A rule is in a carried group where every result its section holds for it was
carried forward, and otherwise in the group of the run that recorded the
section.

### A feature

| Field | Type | What it holds |
|---|---|---|
| `name` | string | the spec's name |
| `spec` | string | the spec's path, `/` separated |
| `scope` | array of strings | the spec's `> Scope:` entries, as written; `[]` for an anchor, whose rules cover the whole project |
| `anchor` | bool | whether the spec is an anchor |
| `rules` | array | the spec's own rules, ordered by rule number |

A feature entry holds exactly these five fields.

### A rule

| Field | Type | What it holds |
|---|---|---|
| `id` | string | `RULE-N` |
| `text` | string | the rule's words as the spec has them. A requirement's number written in the words is part of them and travels with the rule into the package; Purlin does nothing else with it |
| `left` | string or null | the one kind of work the rule waits for, the first that applies in the order of "What is left", or null when it waits for none |
| `proofs` | array | `{id, text, manual, env}` per proof: `manual` is whether the proof is a hand check (`@manual`), `env` the operating system its `@env` names, or null |
| `tests` | array | `{proof, file, name}` per test backing a proof, then per test marked with the rule's own id, whose `proof` is then the `RULE-N` |
| `results` | array | one entry per evidence section that holds a result for the rule, ordered by operating system then source. See below |
| `audit` | object or null | what the audit last found for the rule, which may be out of date. Null where no audit has read it |
| `statuses` | object | `{"passed": {word, reasons}, "strong": {word, reasons}}`. `passed` reads `checked at sign-off` for a rule whose every proof is `@manual`, until a sign-off that counts has noted it on its wording as it stands, and then `passed`. `strong` is what the audit found, and nothing waits on it: its word reads `strong`, `weak`, `spot-checked`, `out of date`, `not audited`, `checked at sign-off`, `no proof` or `waiting` |
| `authors` | object | who wrote and last changed the rule, its proofs and its tests. See "Authors" |

Each `results` entry:

| Field | Type | What it holds |
|---|---|---|
| `os` | string | `windows`, `macos` or `linux` |
| `source` | string | `local` or `ci` |
| `result` | string | `passed`, `failed`, `no test` or `not run`, what that run saw for the rule; `checked at sign-off` for a rule whose every proof is `@manual`, whatever word the run wrote, since no test runs for it |
| `at` | string | when the run that wrote the section finished, as the section records it |
| `commit` | string | the full sha of the code the section is recorded on: the commit the run's tests ran at, or, for a section carried forward, the commit of the run that carried it |
| `runner` | string | who ran it: the slug of the email the section records |
| `machine` | string or null | the machine the tests ran on, as the evidence section records it: the host's name |
| `current` | bool | whether the section's fingerprint matches the spec, code and tests at the package's own `commit` |
| `out_of_date` | array of strings | the parts that differ, of `code`, `spec` and `tests`; empty when current |
| `same_code` | bool | true when every commit from the result's `commit` to the package's `commit` changes only files under `.purlin/` and leaves the `tests` setting of `.purlin/config.json` as it was. A result counts for a sign-off only where it is true |
| `carried` | array | `{proof, commit, at, machine, email}` per proof of the rule whose result the section's own run did not take, by proof number: the proof, and the full sha, the time, the machine and the email of the run that took it, as `evidence_format.md` gives `carried`. `[]` where the section's own run took every result |
| `nothing_to_check` | array | `{proof, reason}` per proof whose every tied test skipped with a reason beginning `nothing to check:`, the reason the text after it |

`audit`:

| Field | Type | What it holds |
|---|---|---|
| `verdict` | string | `strong`, `weak` or `spot-checked`: the entry's last result, which may be out of date |
| `findings` | array of strings | one sentence per finding |
| `no_bug` | array of strings | one sentence per proof no planted bug was caught for, saying why, and one per proof settled with its test unchanged |
| `out_of_date` | array of strings | the parts that changed since the audit read the rule, of `rule`, `proof`, `test` and `code`; `[]` for a current entry |
| `notes` | array of strings | the model's notes, where it gave some |
| `explanation` | array of strings | the model's reading of the rule's tests |
| `breaks` | object | the planted bug per proof, as the evidence file's audit entry holds it, its `aim` and `case` included, and `test_key` and `test_unchanged` where that entry holds them; `{}` for an anchor |
| `model` | string | the model that read the rule, or `unknown` |
| `criteria` | string or null | sha256 of the instructions the model was given |
| `at` | string | when the audit ran |
| `commit` | string | the full sha the audit ran at |
| `source` | string | `local` or `ci`, the evidence file the entry sits in |

### Authors

Read from git in the checkout of the package's `commit`. Every address is
git's author email, and every commit a full sha; a value git cannot give is
null.

| Field | Type | What it holds |
|---|---|---|
| `rule` | object | `{written_by, commit}`: the oldest commit whose diff adds the rule's words, whatever id they stood under, so a renumber does not move it |
| `proofs` | array | `{id, written_by, written_commit, changed_by, changed_commit}` per proof: the commit that first wrote the proof's line, followed through each later edit of it, and the commit that last changed it |
| `tests` | array | `{file, name, changed_by, changed_commit}` per test in `tests`: the newest commit that changed the lines from the test's comment to its last line, or any line of a file run whole |

### Hand checks

Each `hand_checks` entry:

| Field | Type | What it holds |
|---|---|---|
| `feature` | string | the spec that holds the rule |
| `rule` | string | `RULE-N` |
| `proofs` | array of strings | the rule's `@manual` proofs, by number |
| `checked` | string | `in the sign-offs`: what each signer saw is in that signer's sign-off |

Every time is ISO 8601 UTC with `Z`.

## Met

| `met` | When |
|---|---|
| `true` | no line of `left` stops the tests being met: every rule's tests pass, and every spec and test comment can be read |
| `false` | `left` holds a line of `to_repair`, `to_correct`, `to_fix`, `no_test`, `to_test`, `to_run_slow` or `to_test_remote` |

A weak rule (`to_strengthen`) and a rule with no proof (`no_proof`) are listed
in `left` and leave `met` true. `purlin:sign` refuses while `met` is false,
and names `purlin:build` where a rule has no test (`no_test`).

## What is left

`rules`, `steps` and `left` are what `purlin:status` says of the commit the
package reads. Each rule is counted under one kind, the first that applies,
and a kind at zero has no line. `to_repair` counts specs, not rules: a spec
that writes a number twice or holds a line left from a merge conflict, whose
every rule is counted there. `to_correct` counts test comments, not rules,
and is carried by the project. `to_run_slow` counts proofs, not rules: each
proof tagged `@slow` that reads `not run`:

| `kind` | `text`, for one rule and for more | `command` |
|---|---|---|
| `to_repair` | `1 spec to repair`, `<n> specs to repair` | `purlin:spec` |
| `no_proof` | `1 rule to write a proof for`, `<n> rules to write a proof for` | `purlin:spec` |
| `to_correct` | `1 test comment to correct`, `<n> test comments to correct` | `purlin:build` |
| `to_fix` | `1 rule to fix`, `<n> rules to fix` | `purlin:build` |
| `no_test` | `1 rule to write a test for`, `<n> rules to write a test for` | `purlin:build` |
| `to_test` | `1 rule to test`, `<n> rules to test` | `purlin:test` |
| `to_run_slow` | `1 slow proof to run`, `<n> slow proofs to run` | `purlin:test --all` |
| `to_test_remote` | `1 rule to test on <systems>`, `<n> rules to test on <systems>` | `run purlin:test on <systems>` |
| `to_strengthen` | `1 rule to strengthen`, `<n> rules to strengthen` | `purlin:build` |

`<systems>` names each system in the words `Linux/Unix`, `macOS` and
`Windows`, in that order.

## The canonical form

The same commit always gives the same bytes, with the same version of Purlin:

- The top-level keys in the order above. Every other object's keys sorted.
- Lists in the order this page gives them.
- Two-space indent, `": "` and `","` as JSON's separators, characters
  outside ASCII written as themselves, not escaped.
- UTF-8, `\n` line ends on every operating system, one trailing newline.
- Nothing records when the package was built.

## The fingerprint

`fingerprint` is the sha256 hex of the canonical bytes of the package with
`fingerprint` set to the empty string. To check a package, parse it, set
`fingerprint` to `""`, write it in the canonical form, hash it and compare;
then compare the canonical form of the package as parsed with the file's
bytes, so an edit to whitespace alone is caught too.

`purlin:sign --check <file>` does both and prints `The package matches its
fingerprint.`, or `The package does not match its fingerprint: <why>.` and
exits 1. Its reasons:

| What is wrong | `<why>` |
|---|---|
| The bytes are not UTF-8, or not JSON | `the file is not UTF-8 JSON` |
| `schema` is not this format's | `the file does not carry the schema purlin-package/4` |
| A top-level key the format does not name | `the package carries keys the format does not name: <keys>` |
| The top-level keys are not exactly these, in this order | `the top-level keys are not the ones the format names, in its order` |
| The content gives another fingerprint | `the package records the fingerprint <recorded> and its content gives <computed>` |
| The bytes are not the canonical form | `the fingerprint matches the content, but the bytes are not in the canonical form` |
| The file cannot be opened | `the file could not be read: <the operating system's message>` |

The fingerprint shows the file was not changed after it was written. It is
not a signature: each sign-off carries it as `package_hash`, and the sign-off's
signed commit, and the regulated system's signature, are what say who stands
behind it.
