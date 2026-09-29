---
name: export
description: Write the evidence package for a version, the data file a regulated system of record reviews
---

Write one data file that holds the evidence for a version: whether it is finished, the count at
each step, what is left to do, and every rule's words, its proofs, its tests, each result on each
operating system, what the audit found and who signed it. A reviewer who cannot open the
repository reads it in the system that holds the authority to sign the version off.

Purlin makes no claim that the software is compliant. The package is evidence for review in a
regulated document and sign-off system, such as Veeva; how it is shown is that system's job.
`references/formats/package_format.md` holds every field.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:export                     Write the package for the version the project states
purlin:export --release <name>    Name the version, the file and the tag another way
purlin:export --commit            The same, then commit the package
purlin:export --check <file>      Check a package against its fingerprint
```

Plain language reaches the same place: "export the evidence", "what do we hand to QA".

## Step 1: run the script

```
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py" [--release <name>] [--commit]
```

It writes `.purlin/evidence/package/<version>.json` and prints the path and the state:

```
Evidence package written to .purlin/evidence/package/1.4.0.json. State: not finished.
```

The version is the one `purlin:sign` names its tag for: the `VERSION` file, else the version the
project's package description states. With neither, the script prints `No version: nothing in
this project states one. Name it with --release <version>.` and writes nothing.

Print its lines verbatim. It works at every gate and at any time. It reads only what git holds:
evidence or a signature that is written and not committed is left out, and each such file is
named on a line of its own and in the package's `warnings`.

## Step 2: read the state

| State | What it means |
|-------|---------------|
| `finished` | Nothing is left to do at the package's gate: `left` is empty |
| `not finished` | `left` holds the lines of `Left to do`, first the next step, each with its command |

The package also carries `rules`, the total, and `steps`, the count that reached each step up to
the gate, as `purlin:status` says them. The receiving system reads the state beside the gate.

## Step 3: commit only when asked

Run by itself the command commits nothing. With `--commit` it commits the package alone as
`purlin: evidence at <sha7>`, naming the commit the evidence was taken at, and prints
`Package committed.`, or `Package unchanged.` when the file was already committed as it stands.
It never pushes.

## Checking a package

```
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py" --check <file>
```

prints `The package matches its fingerprint.`, or names the mismatch and exits 1. The same tag
always gives the same bytes, so a package exported again at the tag matches the one committed.

## Step 4: name the next step

| What the export found | The line to print |
|-----------------------|-------------------|
| Evidence not committed | `→ Run: purlin:test --commit` |
| No version | `→ Run: purlin:export --release <version>` |
| `not finished` | `→ Run: <the command of the first line of left>` |
| `finished` | `→ Hand .purlin/evidence/package/<version>.json to the system of record.` |
| `--check` named a mismatch | `→ Run: git show signed/<version>:.purlin/evidence/package/<version>.json` |
