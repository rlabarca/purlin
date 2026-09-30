# Purlin documentation

For anyone looking for the guide that fits their role.

## Everyone

| Guide | What it covers |
|-------|----------------|
| [Getting started](getting-started.md) | What Purlin touches in your project, the ten-minute path from install to a first run, and the day to day at the gate `passed` |
| [How Purlin works](how-purlin-works.md) | The three steps in one diagram, the loop, who writes each file, and the questions every developer asks: where tests run, when a run exits 1, which operating system |
| [Working together](working-together.md) | What product, developers and QA each run and read, and drift per role |

The gate is the last step every rule must reach before a version is finished. The whole loop runs on one machine at every gate.

| Gate | What every rule must have | The command that answers it |
|------|---------------------------|-----------------------------|
| `passed` | its tests pass over the current code | `purlin:test` |
| `strong` | that, and an audit that found the tests sound | `purlin:audit` |
| `signed` | that, and a person's signature | `purlin:sign` |

## Developer

| Guide | What it covers |
|-------|----------------|
| [Specs and anchors](specs-and-anchors.md) | The spec format, local anchors, the anchor repo option, pins, id allocation |
| [Running the tests](running-and-evidence.md) | `purlin:test` and the evidence it writes, `purlin:audit` and what it adds, test strength, and the one reason a project has a remote runner |
| [Specs from existing code](spec-from-code.md) | `purlin:spec-from-code` once on a codebase that predates Purlin |

## Product

| Guide | What it covers |
|-------|----------------|
| [Team workflow](team-workflow.md) | The gate `strong`, who writes what, one traced sprint |

## QA

| Guide | What it covers |
|-------|----------------|
| [From criteria to a signature](qa-guide.md) | Acceptance criteria to proofs, what the developer adds, the walk, the signature and what ends it, drift after a pull, where the risk is |
| [Review and signing](review-and-signing.md) | What the audit found, `purlin:sign` and the rules it walks, a check by hand, the tag, and when a signature counts |
| [Dashboard](dashboard.md) | The page that opens from disk, its screens, filters, both themes |

## Raising the gate

| Guide | What it covers |
|-------|----------------|
| [Raising the gate and upgrading](raising-the-gate-and-upgrading.md) | `purlin:init --gate` both ways, and `purlin:init --update` |
| [Regulated workflow](regulated-workflow.md) | The gate `signed`, what Purlin produces for a regulated sign-off system, and where its part ends |

## Reference

| File | What it covers |
|------|----------------|
| [Commands](../references/purlin_commands.md) | Every command's syntax, its purpose, and what it writes |
| [The gate](../references/hard_gates.md) | The one setting, which evidence counts, when a signature counts, what `signed/<version>` means |
| [Glossary](../references/glossary.md) | The word this project uses for each concept, with its one definition |
| [Spec format](../references/formats/spec_format.md) | The 2-section spec, field by field |
| [Marker format](../references/formats/marker_format.md) | The comment that ties a test to a proof, in every language |
| [Evidence format](../references/formats/evidence_format.md) | The file per feature per source a run writes, and its fingerprint |
| [Signature format](../references/formats/signature_format.md) | The signature file and what it binds |
| [Package format](../references/formats/package_format.md) | The evidence package `purlin:export` and `purlin:sign` write |
| [Spec quality](../references/spec_quality_guide.md) | Writing a rule and a proof worth having, and reading the cell that blocks a rule |
| [Supported frameworks](../references/supported_frameworks.md) | The test tools the first test run recognises, and the `tests` entry it suggests for each |
