# Purlin documentation

For anyone looking for the guide that fits their role. Every entry is one sitting's read.

## Everyone

| Guide | What it covers |
|-------|----------------|
| [How Purlin works](how-purlin-works.md) | The chain in one diagram, the five words, who writes each file, and the questions every developer asks: what the loop is, where tests run, what red means, which operating system |
| [Getting started](getting-started.md) | Install, `purlin:init` and its one question, the first spec, build, test, push |
| [Working together](working-together.md) | What each role needs, what they run, what they see, and drift per role |

One setting, the **gate**, decides how much of that chain a project asks for.

| Gate | What CI requires before merge | Where the counting record comes from |
|------|-------------------------------|--------------------------------------|
| `passed` | every rule's passed cell is met | your machine's test results, which `purlin:test` commits; a pass from any source counts |
| `strong` | every rule's strong cell is met too | your own `purlin:audit`, or CI: both count here |
| `signed` | every rule has cleared its bar, and every rule that needs a signature has a current one | CI alone, on the protected branch or on a remote run's run branch, plus a person's signature |

Every rule also has a **bar**, `passed` or `strong`: the evidence that rule must have before it
can be signed. A rule says its own with a tag; a rule with no tag takes the project's gate.

## Engineer

| Guide | What it covers |
|-------|----------------|
| [Solo workflow](solo-workflow.md) | The `passed` gate end to end, the test results `purlin:test` commits, the remote runner, the pre-push hook |
| [Specs and anchors](specs-and-anchors.md) | The spec format, local anchors, the anchor repo option, pins, id allocation |
| [Running and records](running-and-records.md) | `purlin:test` and its two files, `purlin:audit` and the record it writes, CI, the record shape, retention, test strength |
| [Specs from existing code](spec-from-code.md) | `purlin:spec-from-code` once on a codebase that predates Purlin |

## PM and designer

| Guide | What it covers |
|-------|----------------|
| [Design in specs](design-in-specs.md) | `designs/`, design anchors, `origin: design` rules, mock beside screenshot |
| [Team workflow](team-workflow.md) | The `strong` gate, the record and who writes one, one traced sprint |

## QA

| Guide | What it covers |
|-------|----------------|
| [Review and signing](review-and-signing.md) | The bar, the Review and Sign tabs, the brief, `purlin:sign`, what stales a signature |
| [Dashboard](dashboard.md) | The local page and the CI artifact, the four screens, filters, both themes |

## Admin

| Guide | What it covers |
|-------|----------------|
| [Regulated workflow](regulated-workflow.md) | The `signed` gate, the signer list, signed commits, the evidence trail |
| [Raising the gate and upgrading](raising-the-gate-and-upgrading.md) | `purlin:init --gate` both ways, and `purlin:init --update` |

## Reference

| File | What it covers |
|------|----------------|
| [Commands](../references/purlin_commands.md) | Every command's syntax, its one-liner, and what it writes |
| [The gate](../references/hard_gates.md) | The one setting, which records count, the branch rules, the signer list |
| [Glossary](../references/glossary.md) | The word this project uses for each concept, and the retired spellings |
| [Spec format](../references/formats/spec_format.md) | The 2-section spec, field by field |
| [Test results format](../references/formats/tests_format.md) | The two files `purlin:test` writes and commits |
| [Record format](../references/formats/record_format.md) | The record an audit writes, yours or CI's |
| [Signature format](../references/formats/signature_format.md) | The signature file and what it binds |
| [Spec quality](../references/spec_quality_guide.md) | Writing a rule worth having, and diagnosing a failure |
| [Supported frameworks](../references/supported_frameworks.md) | How each test framework is detected and wired |
