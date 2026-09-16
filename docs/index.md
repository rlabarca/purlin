# Purlin documentation

For anyone looking for the guide that fits their role. Every entry is one sitting's read.

## Everyone

| Guide | What it covers |
|-------|----------------|
| [Getting started](getting-started.md) | Install, `purlin:init` and its one question, the first spec, build, test, verify |
| [Working together](working-together.md) | What each role needs, what they run, what they see, and drift per role |

## Engineer

| Guide | What it covers |
|-------|----------------|
| [Solo workflow](solo-workflow.md) | The `tested` gate end to end, your own record commit, the pre-push hook |
| [Specs and anchors](specs-and-anchors.md) | The spec format, local anchors, the anchor repo option, pins, id allocation |
| [Running and records](running-and-records.md) | `purlin:test`, `purlin:verify`, CI, the record shape, retention, test strength |
| [Specs from existing code](spec-from-code.md) | `purlin:spec-from-code` once on a codebase that predates Purlin |

## PM and designer

| Guide | What it covers |
|-------|----------------|
| [Design in specs](design-in-specs.md) | `designs/`, design anchors, `origin: design` rules, mock beside screenshot |
| [Team workflow](team-workflow.md) | The `recorded` gate, CI as the writer of the record, one traced sprint |

## QA

| Guide | What it covers |
|-------|----------------|
| [Review and approval](review-and-approval.md) | The review list, the brief, `purlin:review`, `purlin:approve`, what stales an approval |
| [Dashboard](dashboard.md) | The local page and the CI artifact, the three screens, filters, both themes |

## Admin

| Guide | What it covers |
|-------|----------------|
| [Regulated workflow](regulated-workflow.md) | The `approved` gate, the approver list, signed commits, the evidence trail |
| [Raising the gate and upgrading](raising-the-gate-and-upgrading.md) | `purlin:init --gate` both ways, and `purlin:init --update` |

## Reference

| File | What it covers |
|------|----------------|
| [Commands](../references/purlin_commands.md) | Every command's syntax, its one-liner, and what it writes |
| [The gate](../references/hard_gates.md) | The one setting, which records count, the branch rules, the approver list |
| [Glossary](../references/glossary.md) | The word this project uses for each concept, and the retired spellings |
| [Spec format](../references/formats/spec_format.md) | The 2-section spec, field by field |
| [Record format](../references/formats/record_format.md) | The record a verify run writes |
| [Signature format](../references/formats/signature_format.md) | The signature file and what it binds |
| [Spec quality](../references/spec_quality_guide.md) | Writing a rule worth having, and diagnosing a failure |
| [Supported frameworks](../references/supported_frameworks.md) | How each test framework is detected and wired |
