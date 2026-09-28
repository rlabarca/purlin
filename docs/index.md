# Purlin documentation

For anyone looking for the guide that fits their role. Every entry is one sitting's read.

## Everyone

| Guide | What it covers |
|-------|----------------|
| [How Purlin works](how-purlin-works.md) | The chain in one diagram, the loop, the six words, who writes each file, and the questions every developer asks: where tests run, what red means, which operating system |
| [Getting started](getting-started.md) | Install, `purlin:init` and its one question, the first spec, build, test, push |
| [Working together](working-together.md) | What each role needs, what they run, what they see, and drift per role |

One setting, the **gate**, decides how much of that chain a project asks for. The whole loop
runs on one machine: `purlin:spec`, `purlin:build`, `purlin:test`, `purlin:audit`,
`purlin:sign`, `git push`. A project at `signed` with no CI anywhere is the ordinary case.

| Gate | What every rule must have | Where the evidence comes from |
|------|---------------------------|-------------------------------|
| `passed` | its passed cell met | your machine's evidence, which `purlin:test --commit` commits; a pass from any source counts |
| `strong` | its strong cell met too | `purlin:audit`, run by anyone; its record counts |
| `signed` | its signed cell met too, where its level is `signed` | the same, plus a person's signature and the tag `purlin:sign` writes |

Every rule also has a **level**, `passed`, `strong` or `signed`, meaning what the gate means. A
rule says its own with a tag, `[level: ...]`; a rule with no tag takes the project's gate, and a
mark above the gate is read as the gate.

## Engineer

| Guide | What it covers |
|-------|----------------|
| [Solo workflow](solo-workflow.md) | The `passed` gate end to end, the evidence `purlin:test` writes, and the one time a runner joins in |
| [Specs and anchors](specs-and-anchors.md) | The spec format, local anchors, the anchor repo option, pins, id allocation |
| [Running and records](running-and-records.md) | `purlin:test` and the evidence it writes, `purlin:audit` and what it adds, the evidence file, retention, test strength, and the two reasons a project has a remote runner |
| [Specs from existing code](spec-from-code.md) | `purlin:spec-from-code` once on a codebase that predates Purlin |

## PM and designer

| Guide | What it covers |
|-------|----------------|
| [Team workflow](team-workflow.md) | The `strong` gate, the record and who writes one, one traced sprint |

## QA

| Guide | What it covers |
|-------|----------------|
| [Review and signing](review-and-signing.md) | The level, the queue, the brief, `purlin:sign`, the tag, what stales a signature |
| [Dashboard](dashboard.md) | The page that opens from disk, the four screens, filters, both themes |

## Admin

| Guide | What it covers |
|-------|----------------|
| [Regulated workflow](regulated-workflow.md) | The `signed` gate, who may sign, signed commits, the tag, the evidence trail |
| [Raising the gate and upgrading](raising-the-gate-and-upgrading.md) | `purlin:init --gate` both ways, and `purlin:init --update` |

## Reference

| File | What it covers |
|------|----------------|
| [Commands](../references/purlin_commands.md) | Every command's syntax, its one-liner, and what it writes |
| [The gate](../references/hard_gates.md) | The one setting, which evidence counts, when a signature counts, what `signed/<version>` means |
| [Glossary](../references/glossary.md) | The word this project uses for each concept, and the retired spellings |
| [Spec format](../references/formats/spec_format.md) | The 2-section spec, field by field |
| [Evidence format](../references/formats/evidence_format.md) | The file per feature per source a test run and an audit write, yours or a runner's, and its fingerprint |
| [Signature format](../references/formats/signature_format.md) | The signature file and what it binds |
| [Spec quality](../references/spec_quality_guide.md) | Writing a rule worth having, and diagnosing a failure |
| [Supported frameworks](../references/supported_frameworks.md) | How each test framework is detected and wired |
