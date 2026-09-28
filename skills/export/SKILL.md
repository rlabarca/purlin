---
name: export
description: Write the evidence package for a version, the data file a regulated system of record reviews
---

Write one data file that holds the evidence for a version: every rule's words, its proofs, its
tests, each result on each operating system, what the audit found, who signed it, and whether
it meets the gate. A reviewer who cannot open the repository reads it in the system that holds
the authority to sign the version off.

Purlin makes no claim that the software is compliant. The package is evidence for review in a
regulated document and sign-off system, such as Veeva; how it is shown is that system's job.
`references/formats/package_format.md` holds every field.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:export                     Write the package for the VERSION file's value
purlin:export --release <name>    Name the version, the file and the tag another way
purlin:export --commit            The same, then commit the package
purlin:export --check <file>      Check a package against its fingerprint
```

Plain language reaches the same place: "export the evidence", "what do we hand to QA".

## Step 1: run the script

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py" [--release <name>] [--commit]
```

It writes `.purlin/evidence/package/<version>.json` and prints the path and the state:

```
Evidence package written to .purlin/evidence/package/1.4.0.json. State: work in progress, 38 of 42 rules meet the gate signed. Not for approval.
```

Print its lines verbatim. It works at every gate and at any time. It reads only what git holds:
evidence or a signature that is written and not committed is left out, and each such file is
named on a line of its own and in the package's `warnings`.

## Step 2: read the state

| State | What it means |
|-------|---------------|
| `work in progress` | At least one rule does not meet the gate. Not for approval |
| `gate <gate> met` | Every rule meets the gate, and the version is not signed and tagged. Not for approval |
| `signed` | Every rule meets the gate `signed`, and the package is the one the tag carries |

Only `purlin:sign` writes a package whose state is `signed`: when every rule meets the gate it
writes the package, commits it as a signed commit, and writes the tag on that commit, so the
tagged code carries the package that describes it.

## Step 3: commit only when asked

Run by itself the command commits nothing. With `--commit` it commits the package alone as
`purlin: evidence at <sha7>`, naming the commit the evidence was taken at, and prints
`Package committed.`, or `Package unchanged.` when the file was already committed as it stands.
It never pushes.

## Checking a package

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py" --check <file>
```

prints `The package matches its fingerprint.`, or names the mismatch and exits 1. The same tag
always gives the same bytes, so a package exported again at the tag matches the one committed.

## Step 4: name the next step

| What the export found | The line to print |
|-----------------------|-------------------|
| Evidence not committed | `→ Run: purlin:test --commit` |
| `work in progress` | `→ Run: purlin:status` |
| `gate <gate> met` at the gate `signed` | `→ Run: purlin:sign` |
| `signed` | `→ Hand .purlin/evidence/package/<version>.json to the system of record.` |
| `--check` named a mismatch | `→ Export the package again at its tag: purlin:export` |
