# Purlin documentation

Nine guides, and the references behind them.

Purlin shows, rule by rule, that your software does what you said it must. It keeps two
things: the evidence of what your tests saw, and a person's sign-off over it. It shows them as
two facts:

- `Tests: met` or `not met`;
- `Sign-off: signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since` or `not signed`.

## Guides

| Guide | Who it is for | What it covers |
|-------|---------------|----------------|
| [How Purlin works](how-purlin-works.md) | everyone | The rule, its proof and its test, the two facts, the loop, who writes each file, and the questions every developer asks |
| [Getting started](getting-started.md) | a developer | What Purlin touches in your project, and the ten-minute path from install to a first run |
| [Specs and anchors](specs-and-anchors.md) | anyone who writes rules | The spec format, judgment calls, slow tests, operating systems, ids across branches, and the two kinds of anchor |
| [Running the tests](running-and-evidence.md) | a developer | `purlin:test` and the evidence it writes, `purlin:audit`, which results count for a sign-off, and testing on another system |
| [Working together](working-together.md) | a team | What product, QA and developers each run and read, drift, what can collide, and more than one checkout |
| [The sign-off](sign-off.md) | whoever signs | QA's path from criteria to a signature, the walk of `purlin:sign`, what the package and the sign-off record, and where Purlin's part ends beside a regulated system |
| [The audit](audit.md) | anyone who asks whether the tests are sound | The heuristic spot tests, one planted bug per proof, a target such as 80% strong, and the research behind the approach |
| [The dashboard](dashboard.md) | everyone | The page that opens from disk: the two facts, the board, one rule, both themes |
| [Upgrading](upgrading.md) | a project set up with Purlin 0.9.5 | `purlin:init --update` and what each migration changes |

## Reference

| File | What it covers |
|------|----------------|
| [Commands](../references/purlin_commands.md) | Every command's syntax, its purpose, and what it writes |
| [Evidence and sign-off](../references/evidence_and_signoff.md) | The two facts, which evidence counts for a sign-off, when a sign-off counts, what `signed/<version>` means |
| [Glossary](../references/glossary.md) | The word this project uses for each concept, with its one definition |
| [Spec format](../references/formats/spec_format.md) | The 2-section spec, field by field |
| [Anchor format](../references/formats/anchor_format.md) | The anchor, local and remote |
| [Marker format](../references/formats/marker_format.md) | The comment that ties a test to a proof, in every language |
| [Evidence format](../references/formats/evidence_format.md) | The file per feature per source a run writes, and its fingerprint |
| [Package format](../references/formats/package_format.md) | The evidence package `purlin:sign` builds and signs |
| [Signature format](../references/formats/signature_format.md) | The sign-off file `purlin:sign` writes over the evidence package |
| [Spec quality](../references/spec_quality_guide.md) | Writing a rule and a proof worth having |
| [Audit criteria](../references/review_criteria.md) | The heuristic spot tests, and what the model is sent |
| [Supported frameworks](../references/supported_frameworks.md) | The test tools the first test run recognises, and the `tests` entry it suggests for each |
