> Format-Version: 1

# Package format

The evidence package is one data file describing one version: every rule's
words, its proofs and its tests, each result on each operating system, what
the audit found, who signed it, and whether it meets the gate. It is written
for a reviewer who cannot open the repository.

```
.purlin/evidence/package/<version>.json
```

`purlin:export` writes it at any time and at any gate, and at the gate
`signed` `purlin:sign` writes and commits it before it writes the tag
`signed/<version>`, so the tagged commit carries the
package that describes it. The file is tracked like the rest of
`.purlin/evidence/`.

## What the package is for

Purlin makes no claim that the software is compliant. The package is
evidence for review in a regulated document and sign-off system, such as
Veeva, which holds the controlled document, the authority to sign it off and
the signature that counts under the regulation. Purlin hands the data over;
how it is shown is the receiving system's job.

## The file name

`<version>` is the value of the `VERSION` file at the project root, else
`version` in `.purlin/config.json`, else `unversioned`. `purlin:export
--release <name>` names another, which is the same name `purlin:sign
--release <name>` gives the tag.

## What it reads

The package is built from a checkout of one commit, so it describes only what
git holds. Evidence or a signature that is written and not committed is left
out, and each such file is named in `warnings` and on the terminal.

That commit is the one the evidence was taken at: `HEAD`, stepping back over
any commit that changed nothing but files under `.purlin/evidence/package/`.
When `purlin:sign` writes the package for a tag, this is the parent of the
commit that carries the package, because a file cannot name the commit that
contains it.

## Fields

```json
{
  "schema": "purlin-package/1",
  "state": "work in progress",
  "not_for_approval": true,
  "rules_meeting_gate": 38,
  "rules_short_of_gate": 4,
  "purlin_version": "0.10.0",
  "project": "ledger",
  "version": "1.4.0",
  "tag": "signed/1.4.0",
  "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7",
  "gate": "signed",
  "trust": "local",
  "mutation_engine": "auto",
  "min_strength": 80,
  "features": [],
  "warnings": [],
  "fingerprint": "<sha256>"
}
```

The top-level keys appear in exactly this order, and every one is REQUIRED.
The state is the first thing a reader sees after the schema.

| Field | Type | What it holds |
|---|---|---|
| `schema` | string | `purlin-package/1` |
| `state` | string | `signed`, `gate <gate> met` or `work in progress`. See "The state" |
| `not_for_approval` | bool | false only when `state` is `signed` |
| `rules_meeting_gate` | int | the rules that meet the project's gate, each counted once under the feature that owns it |
| `rules_short_of_gate` | int | the rules that do not |
| `purlin_version` | string | the version of Purlin that wrote the package |
| `project` | string | `project_name` in `.purlin/config.json`, else the project folder's name |
| `version`, `tag` | string, string | the version the file is named for, and the tag named for it, `signed/<version>` |
| `commit` | string | the full sha the evidence was taken at. See "What it reads" |
| `gate` | string | `passed`, `strong` or `signed` |
| `trust` | string | `local` or `remote` |
| `mutation_engine` | string or null | the setting as the project resolves it |
| `min_strength` | int or null | the test strength a rule's strong cell compares with |
| `features` | array | one entry per spec, ordered by name |
| `warnings` | array of strings | one sentence per file left out, then each warning reading the specs and the evidence raised |
| `fingerprint` | string | sha256 hex. See "The fingerprint" |

### A feature

| Field | Type | What it holds |
|---|---|---|
| `name` | string | the spec's name |
| `spec` | string | the spec's path, `/` separated |
| `scope` | array of strings | the spec's `> Scope:` entries, as written |
| `requires` | array of strings | the specs its `> Requires:` names |
| `anchor` | bool | whether the spec is an anchor |
| `rules` | array | the spec's own rules, ordered by rule number |

### A rule

| Field | Type | What it holds |
|---|---|---|
| `id` | string | `RULE-N` |
| `text` | string | the rule's words as the spec has them, its `[level: ...]` tag stripped. A requirement's number written in the words, such as `(URS-042)`, is part of them; Purlin does nothing else with it |
| `level` | string | `passed`, `strong` or `signed` |
| `level_marked` | bool | whether the spec marks the level with `[level: ...]`; false means the rule takes the gate |
| `proofs` | array | `{id, text, manual, env}` per proof: `manual` is whether the proof is a hand check (`@manual`), `env` the operating system its `@env` names, or null |
| `tests` | array | `{proof, file, name}` per test backing a proof, then per test marked with the rule's own id, whose `proof` is then the `RULE-N` |
| `results` | array | one entry per evidence section, ordered by operating system then source. See below |
| `audit` | object or null | what the audit found for the rule's current words, proof and test. Null where no audit has |
| `signatures` | array | every signature whose hashes still match the rule, ordered by `at`. A stale signature is not listed; the signed status names it |
| `statuses` | object | `passed`, `strong` and `signed`, each `{word, reasons}`, or null where the gate creates no such cell |
| `meets_gate` | bool | whether the rule meets the gate |

Each `results` entry:

| Field | Type | What it holds |
|---|---|---|
| `os` | string | `windows`, `macos` or `linux` |
| `source` | string | `local` or `ci` |
| `result` | string | `passed`, `failed`, `no test` or `not run`, what that run saw for the rule |
| `at` | string | when the run finished |
| `commit` | string | the full sha the run started at |
| `runner` | string | who ran it: the slug of the runner's email, or `ci` |
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

Each `signatures` entry:

| Field | Type | What it holds |
|---|---|---|
| `signer` | string | the signer's email |
| `at` | string | the time the signature file records |
| `committed_at` | string or null | when the commit carrying it was made |
| `machine` | string or null | the host it was made on |
| `os` | string or null | that host's operating system |
| `note` | string or null | what the signer wrote about a hand check |
| `level` | string | the rule's level when it was signed |
| `gate` | string | the gate in force when it was signed |
| `path` | string | the signature file |
| `commit_verifies` | bool | whether the commit that added it is signed and verifies |
| `locked` | object | `triple`, `rule_hash`, `proof_hash`, `test_hash`, `test_hash_kind` and `audit_hash`, the hashes it binds (`signature_format.md`) |

Nothing in the package names who last changed a test.

Every time is ISO 8601 UTC with `Z`.

## The state

| State | When |
|---|---|
| `signed` | every rule meets the gate `signed`, and the package is written for the tag, or read at the commit the tag `signed/<version>` names |
| `gate <gate> met` | every rule meets the gate, and the version is not signed and tagged: the gate is `passed` or `strong`, where no tag is written and a tag found on the commit changes nothing, or no tag names this commit yet |
| `work in progress` | at least one rule does not meet the gate |

Only a version that is signed and tagged is put forward for approval, so
`not_for_approval` is true for every state but `signed`.

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
not a signature: the tag's own signature, and the regulated system's, are
what say who stands behind it.
