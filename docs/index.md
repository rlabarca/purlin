# Purlin documentation

For anyone looking for the guide that fits their role.

## Everyone

| Guide | What it covers |
|-------|----------------|
| [Getting started](getting-started.md) | What Purlin touches in your project, the ten-minute path from install to a first run, and the day to day at the gate `passed` |
| [How Purlin works](how-purlin-works.md) | The two cells and the release in one diagram, the loop, who writes each file, and the questions every developer asks: where tests run, when a run exits 1, which operating system |
| [Working together](working-together.md) | What product, developers and QA each run and read, and drift per role |

The gate says what a release asks. The whole loop runs on one machine at either gate, and the audit is a tool at both.

| Gate | What a release must have | The commands that make it |
|------|--------------------------|---------------------------|
| `passed` | every rule's tests pass at the release commit | `purlin:test --release` |
| `signed` | that, and a person's signature over the evidence package | `purlin:test --release`, then `purlin:sign` |

## Developer

| Guide | What it covers |
|-------|----------------|
| [Specs and anchors](specs-and-anchors.md) | The spec format, local anchors, the anchor repo option, pins, id allocation |
| [Running the tests](running-and-evidence.md) | `purlin:test` and the evidence it writes, `purlin:audit` and what it adds, test strength, and the one reason a project has a remote runner |
| [Specs from existing code](spec-from-code.md) | `purlin:spec-from-code` once on a codebase that predates Purlin |

## Product

| Guide | What it covers |
|-------|----------------|
| [Team workflow](team-workflow.md) | Who writes what, the audit as a tool, one traced sprint, releasing a version |

## QA

| Guide | What it covers |
|-------|----------------|
| [From criteria to a sign-off](qa-guide.md) | Acceptance criteria to proofs, what the developer adds, drift after a pull, the release, the sign-off and what the package records, where the risk is |
| [The release and the sign-off](review-and-signing.md) | `purlin:test --release` and what it checks, the sign-off walk and its stops, several signers, when a sign-off counts, the tags |
| [Dashboard](dashboard.md) | The page that opens from disk, its screens, filters, both themes |

## Raising the gate

| Guide | What it covers |
|-------|----------------|
| [Raising the gate and upgrading](raising-the-gate-and-upgrading.md) | The two gates, `purlin:init --gate` both ways, and `purlin:init --update` |
| [Regulated workflow](regulated-workflow.md) | The gate `signed`, what Purlin produces for a regulated sign-off system, and where its part ends |

## Reference

| File | What it covers |
|------|----------------|
| [Commands](../references/purlin_commands.md) | Every command's syntax, its purpose, and what it writes |
| [The gate](../references/hard_gates.md) | The two gates, the release, which evidence counts, when a sign-off counts, what the tags mean |
| [Glossary](../references/glossary.md) | The word this project uses for each concept, with its one definition |
| [Spec format](../references/formats/spec_format.md) | The 2-section spec, field by field |
| [Marker format](../references/formats/marker_format.md) | The comment that ties a test to a proof, in every language |
| [Evidence format](../references/formats/evidence_format.md) | The file per feature per source a run writes, and its fingerprint |
| [Signature format](../references/formats/signature_format.md) | The sign-off file `purlin:sign` writes over the evidence package |
| [Package format](../references/formats/package_format.md) | The evidence package `purlin:test --release` and `purlin:export` write |
| [Spec quality](../references/spec_quality_guide.md) | Writing a rule and a proof worth having, and reading the cell that blocks a rule |
| [Supported frameworks](../references/supported_frameworks.md) | The test tools the first test run recognises, and the `tests` entry it suggests for each |
