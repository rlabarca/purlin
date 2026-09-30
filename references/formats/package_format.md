> Format-Version: 7

# Package format

The evidence package is one data file describing one version: whether it is
finished, the total of rules, the count that pass, what the audit found and
what is left to do, then every rule's words, its proofs and its tests, each
result on each operating system and what the audit found, and last every hand
check. It is written for a reviewer who cannot open the repository.

```
.purlin/evidence/package/<version>.json
```

`purlin:export` writes it at any time and at any gate. `purlin:test --release`
writes it once per release run and commits it alone: at the gate `passed` it
then writes the tag `passed/<version>` on that commit; at `signed` the first
sign-off writes `signed/<version>`. The tagged commit carries the package that
describes it. The file is tracked like the rest of `.purlin/evidence/`.

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

`<version>` is the version the project states, read as `purlin:test --release`
reads it for the tag: the `VERSION` file at the project root, else `version` in
`package.json`, else the `[project]` or `[tool.poetry]` version in
`pyproject.toml`, else the `<Version>` of the first `*.csproj` at the root.
`purlin:export --release <name>` names another, which is the same name
`purlin:test --release <name>` gives the tag. Where the project states none
and `--release` names none, `purlin:export` prints `No version: nothing in
this project states one. Run purlin:export --release <version>, or write it
to a VERSION file.`, writes nothing and exits 1.

## What it reads

The package is built from a checkout of one commit, so it describes only what
git holds. Evidence that is written and not committed is left out, and each such file is named in `warnings` and on the terminal.

That commit is the one the evidence was taken at: `HEAD`, stepping back over
any commit that changed nothing but files under `.purlin/evidence/package/`,
a sign-off included. When `purlin:test --release` writes the package, this is
the parent of the commit that carries the package, because a file cannot name
the commit that contains it.

## Fields

```json
{
  "schema": "purlin-package/3",
  "state": "finished",
  "rules": 42,
  "steps": {"passed": 42},
  "audit": {"not_audited": 8, "strong": 32, "weak": 2},
  "left": [
    {"command": "purlin:build", "count": 2, "kind": "to_strengthen",
     "text": "2 rules to strengthen"}
  ],
  "purlin_version": "0.10.0",
  "project": "ledger",
  "version": "1.4.0",
  "tag": "signed/1.4.0",
  "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7",
  "gate": "signed",
  "mutation_engine": "auto",
  "features": [],
  "hand_checks": [
    {"checked": "in the sign-offs", "feature": "ledger_screen",
     "proofs": ["PROOF-3"], "rule": "RULE-2"}
  ],
  "warnings": [],
  "fingerprint": "<sha256>"
}
```

The top-level keys appear in exactly this order, and every one is REQUIRED.
The state is the first thing a reader sees after the schema.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-package/3` |
| `state` | string | `finished` or `not finished`. See "The state" |
| `rules` | int | the rules of the project, each counted once under the feature that owns it |
| `steps` | object | `{"passed": p}`: the rules whose tests pass, a hand check included |
| `audit` | object | `{"strong", "weak", "not_audited"}`: what the audit found, over the rules whose tests pass |
| `left` | array | the lines of `Left to do`, in the order the work is done: `{kind, count, text, command}` each. See "What is left" |
| `purlin_version` | string | the version of Purlin that wrote the package |
| `project` | string | `project_name` in `.purlin/config.json`, else the project folder's name |
| `version`, `tag` | string, string | the version the file is named for, and the tag the release writes for it: `passed/<version>` at the gate `passed`, `signed/<version>` at `signed` |
| `commit` | string | the full sha the evidence was taken at. See "What it reads" |
| `gate` | string | `passed` or `signed` |
| `mutation_engine` | string or null | the setting as the project resolves it |
| `features` | array | one entry per spec, ordered by name |
| `hand_checks` | array | one entry per rule with a `@manual` proof, by feature then rule number. See "Hand checks" |
| `warnings` | array of strings | one sentence per file left out, then each warning reading the specs and the evidence raised |
| `fingerprint` | string | sha256 hex. See "The fingerprint" |

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
| `text` | string | the rule's words as the spec has them. A requirement's number written in the words, such as `(URS-042)`, is part of them; Purlin does nothing else with it |
| `left` | string or null | the one kind of work the rule waits for, the first that applies in the order of "What is left", or null when it waits for none |
| `proofs` | array | `{id, text, manual, env}` per proof: `manual` is whether the proof is a hand check (`@manual`), `env` the operating system its `@env` names, or null |
| `tests` | array | `{proof, file, name}` per test backing a proof, then per test marked with the rule's own id, whose `proof` is then the `RULE-N` |
| `results` | array | one entry per evidence section, ordered by operating system then source. See below |
| `audit` | object or null | what the audit found for the rule's current words, proof and test. Null where no audit has |
| `statuses` | object | `{"passed": {word, reasons}, "strong": {word, reasons}}` at both gates. `strong` is what the audit found, and nothing waits on it |

Each `results` entry:

| Field | Type | What it holds |
|---|---|---|
| `os` | string | `windows`, `macos` or `linux` |
| `source` | string | `local` or `ci` |
| `result` | string | `passed`, `failed`, `no test` or `not run`, what that run saw for the rule |
| `at` | string | when the run finished |
| `commit` | string | the full sha the run started at |
| `runner` | string | who ran it: the slug of the runner's email, or `ci` |
| `machine` | string or null | the machine the tests ran on, as the evidence section records it: the host's name, or for a remote runner its kind, such as `remote runner, Windows` |
| `current` | bool | whether the section's fingerprint matches the spec, code and tests at the package's own `commit` |
| `out_of_date` | array of strings | the parts that differ, of `code`, `spec` and `tests`; empty when current |

`audit`:

| Field | Type | What it holds |
|---|---|---|
| `verdict` | string | `strong`, `weak` or `undecided` |
| `findings` | array of strings | one sentence per finding |
| `strength` | int or null | the feature's test strength, null where mutation testing is off |
| `model` | string | the model that judged, or `unknown` |
| `criteria` | string or null | sha256 of the instructions the model was given |
| `at` | string | when the audit ran |
| `commit` | string | the full sha the audit ran at |
| `source` | string | `local` or `ci`, the evidence file the entry sits in |

### Hand checks

Each `hand_checks` entry:

| Field | Type | What it holds |
|---|---|---|
| `feature` | string | the spec that holds the rule |
| `rule` | string | `RULE-N` |
| `proofs` | array of strings | the rule's `@manual` proofs, by number |
| `checked` | false or string | `false` at the gate `passed`, where nobody signs and no hand check is recorded; `in the sign-offs` at `signed`, where each signer types what they saw |

What a signer typed for a hand check is in that signer's sign-off, not here.

Nothing in the package names who last changed a test.

Every time is ISO 8601 UTC with `Z`.

## The state

| State | When |
|---|---|
| `finished` | no line of `left` stops a release: every rule's tests pass, and every spec and test comment can be read |
| `not finished` | `left` holds a line of `to_repair`, `to_correct`, `to_fix`, `no_test`, `to_test` or `to_test_remote` |

A weak rule (`to_strengthen`) and a rule with no proof (`no_proof`) are listed
in `left` and leave the state `finished`.

The state and the gate beside it are what the receiving system reads to
decide what the package may be used for.

## What is left

`rules`, `steps` and `left` are what `purlin:status` says of the commit the
package reads. Each rule is counted under one kind, the first that applies,
and a kind at zero has no line. `to_repair` counts specs, not rules: a spec
that writes a number twice or holds a line left from a merge conflict, whose
every rule is counted there. `to_correct` counts test comments, not rules,
and is carried by the project:

| `kind` | `text`, for one rule and for more | `command` |
|---|---|---|
| `to_repair` | `1 spec to repair`, `<n> specs to repair` | `purlin:spec` |
| `no_proof` | `1 rule to write a proof for`, `<n> rules to write a proof for` | `purlin:spec` |
| `to_correct` | `1 test comment to correct`, `<n> test comments to correct` | `purlin:build` |
| `to_fix` | `1 rule to fix`, `<n> rules to fix` | `purlin:build` |
| `no_test` | `1 rule to write a test for`, `<n> rules to write a test for` | `purlin:build` |
| `to_test` | `1 rule to test`, `<n> rules to test` | `purlin:test` |
| `to_test_remote` | `1 rule to test on <systems>`, `<n> rules to test on <systems>` | `purlin:test --remote` |
| `to_strengthen` | `1 rule to strengthen`, `<n> rules to strengthen` | `purlin:build` |

`<systems>` names each system in the words `Linux/Unix`, `macOS` and
`Windows`, in that order. `no_proof` is counted at the gate `signed` alone.

## The canonical form

The same tag always gives the same bytes, with the same version of Purlin:

- The top-level keys in the order above. Every other object's keys sorted.
- Lists in the order this page gives them.
- Two-space indent, `": "` and `","` as JSON's separators, characters
  outside ASCII written as themselves, not escaped.
- UTF-8, `\n` line ends on every operating system, one trailing newline.
- Nothing records when the export ran.

## The fingerprint

`fingerprint` is the sha256 hex of the canonical bytes of the package with
`fingerprint` set to the empty string. To check a package, parse it, set
`fingerprint` to `""`, write it in the canonical form, hash it and compare;
then compare the canonical form of the package as parsed with the file's
bytes, so an edit to whitespace alone is caught too.

`purlin:export --check <file>` does both and prints `The package matches its
fingerprint.`, or names the mismatch and exits 1.

The fingerprint shows the file was not changed after it was written. It is
not a signature: each sign-off carries it as `package_hash`, and the sign-off's
signed commit, and the regulated system's signature, are what say who stands
behind it.
