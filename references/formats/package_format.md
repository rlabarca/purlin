> Format-Version: 3

# Package format

The evidence package is one data file describing one version: whether it is
finished, the total of rules, the count at each step and what is left to do,
then every rule's words, its proofs and its tests, each result on each
operating system, what the audit found and who signed it. It is written for a
reviewer who cannot open the repository.

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

`<version>` is the version the project states, read as `purlin:sign` reads it
for the tag: the `VERSION` file at the project root, else `version` in
`package.json`, else the `[project]` or `[tool.poetry]` version in
`pyproject.toml`, else the `<Version>` of the first `*.csproj` at the root.
`purlin:export --release <name>` names another, which is the same name
`purlin:sign --release <name>` gives the tag. Where the project states none
and `--release` names none, `purlin:export` prints `No version: nothing in
this project states one. Name it with --release <version>.`, writes nothing
and exits 1.

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
  "schema": "purlin-package/2",
  "state": "not finished",
  "rules": 42,
  "steps": {"passed": 40, "signed": 30, "strong": 35},
  "left": [
    {"command": "purlin:build", "count": 2, "kind": "to_fix",
     "text": "2 rules to fix"},
    {"command": "purlin:audit", "count": 5, "kind": "to_audit",
     "text": "5 rules to audit"},
    {"command": "purlin:sign", "count": 5, "kind": "to_sign",
     "text": "5 rules to sign"}
  ],
  "purlin_version": "0.10.0",
  "project": "ledger",
  "version": "1.4.0",
  "tag": "signed/1.4.0",
  "commit": "4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7",
  "gate": "signed",
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
| `schema` | string | `purlin-package/2` |
| `state` | string | `finished` or `not finished`. See "The state" |
| `rules` | int | the rules of the project, each counted once under the feature that owns it |
| `steps` | object | the rules that reached each step, `passed`, then `strong` and `signed` where the gate names them; each step counts only rules that reached the one before it |
| `left` | array | the lines of `Left to do`, in the order the work is done: `{kind, count, text, command}` each. See "What is left" |
| `purlin_version` | string | the version of Purlin that wrote the package |
| `project` | string | `project_name` in `.purlin/config.json`, else the project folder's name |
| `version`, `tag` | string, string | the version the file is named for, and the tag named for it, `signed/<version>` |
| `commit` | string | the full sha the evidence was taken at. See "What it reads" |
| `gate` | string | `passed`, `strong` or `signed` |
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
| `text` | string | the rule's words as the spec has them. A requirement's number written in the words, such as `(URS-042)`, is part of them; Purlin does nothing else with it |
| `left` | string or null | the one kind of work the rule waits for, the first that applies in the order of "What is left", or null when it waits for none |
| `proofs` | array | `{id, text, manual, env}` per proof: `manual` is whether the proof is a hand check (`@manual`), `env` the operating system its `@env` names, or null |
| `tests` | array | `{proof, file, name}` per test backing a proof, then per test marked with the rule's own id, whose `proof` is then the `RULE-N` |
| `results` | array | one entry per evidence section, ordered by operating system then source. See below |
| `audit` | object or null | what the audit found for the rule's current words, proof and test. Null where no audit has |
| `signatures` | array | every signature whose hashes still match the rule in the feature it applies to, ordered by `at`. A signature that no longer matches is not listed |
| `statuses` | object | one `{word, reasons}` per step up to the gate: `passed` always, `strong` at the gates `strong` and `signed`, `signed` at `signed`. A status above the gate is absent, not null |

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

Each `signatures` entry:

| Field | Type | What it holds |
|---|---|---|
| `signer` | string | the signer's email, as git holds it |
| `signer_name` | string or null | the signer's name, as git holds it |
| `key_fingerprint` | string or null | `SHA256:` and the fingerprint of the key the signer signs with |
| `applies_to` | string or null | the feature the signature was made in: the owner, or for an anchor's rule each feature it applies to |
| `machines` | object | `{os: machine}`, the machine each operating system's results came from when it was signed |
| `at` | string | the time the signature file records |
| `committed_at` | string or null | when the commit carrying it was made |
| `note` | string or null | what the signer wrote about a hand check |
| `gate` | string or null | the gate in force when it was signed |
| `path` | string | the signature file |
| `signed_commit` | bool | whether the commit that carries it is signed, which is what makes a signature count |
| `locked` | object | `signed_hash`, `rule_hash`, `proof_hash`, `test_hash`, `test_hash_kind`, `code_hash` and `audit_hash`, the hashes it binds (`signature_format.md`) |

Nothing in the package names who last changed a test.

Every time is ISO 8601 UTC with `Z`.

## The state

| State | When |
|---|---|
| `finished` | nothing is left to do: `left` is empty |
| `not finished` | `left` holds at least one line |

The state and the gate beside it are what the receiving system reads to
decide what the package may be used for.

## What is left

`rules`, `steps` and `left` are what `purlin:status` says of the commit the
package reads. Each rule is counted under one kind, the first that applies,
and a kind at zero has no line:

| `kind` | `text`, for one rule and for more | `command` |
|---|---|---|
| `no_proof` | `1 rule to write a proof for`, `<n> rules to write a proof for` | `purlin:spec` |
| `to_fix` | `1 rule to fix`, `<n> rules to fix` | `purlin:build` |
| `no_test` | `1 rule to write a test for`, `<n> rules to write a test for` | `purlin:build` |
| `to_test` | `1 rule to test`, `<n> rules to test` | `purlin:test` |
| `to_test_remote` | `1 rule to test on <systems>`, `<n> rules to test on <systems>` | `purlin:test --remote` |
| `to_test_by_hand` | `1 rule to test by hand`, `<n> rules to test by hand` | `purlin:sign` |
| `to_audit` | `1 rule to audit`, `<n> rules to audit` | `purlin:audit` |
| `to_strengthen` | `1 rule to strengthen`, `<n> rules to strengthen` | `purlin:build` |
| `no_scope` | `1 rule to tie to its files`, `<n> rules to tie to their files` | `purlin:spec` |
| `to_sign` | `1 rule to sign`, `<n> rules to sign` | `purlin:sign` |
| `to_tag` | `the version to tag`, with `count` 1 | `purlin:sign` |

`<systems>` names each system in the words `Linux/Unix`, `macOS` and
`Windows`, in that order. `to_tag` is the one line at the gate `signed` once
nothing else is left and no `signed/*` tag names the commit. The package
leaves it out when `purlin:sign` writes the package for the tag, and when the
package is read again at the commit the tag `signed/<version>` names, so the
package the tag carries reads `finished`.

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
