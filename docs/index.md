# Purlin documentation

Thirteen guides, and the references behind them.

Purlin shows, rule by rule, that your software does what you said it must. It keeps two
things: the evidence of what your tests saw, and a person's sign-off over it. It shows them as
two facts:

- `Tests: met` or `not met`;
- `Sign-off: signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since` or `not signed`.

## Guides

| Guide | Who it is for | What it covers |
|-------|---------------|----------------|
| [How Purlin works](how-purlin-works.md) | everyone | A rule, its proof and its test, and the two facts |
| [Getting started](getting-started.md) | a developer | Five steps from install to a first result |
| [Specs and anchors](specs-and-anchors.md) | anyone who writes rules | Writing rules and proofs, and rules for the whole project |
| [Running the tests](running-and-evidence.md) | a developer | `purlin:test` and the evidence a run leaves |
| [Testing a prompt or a skill](testing-ai.md) | a team whose product is a prompt or a skill | An AI proof from rule to evidence: the models, the model runs and what is kept |
| [Graded by an AI](graded-by-ai.md) | anyone who writes or reads a graded proof | A second model grades an output against one sentence |
| [Working together](working-together.md) | a team | What product, QA and developers each do |
| [The sign-off](sign-off.md) | whoever signs | A person signs the evidence once, with `purlin:sign` |
| [Regulated work](regulated.md) | QA and anyone who must show evidence | What the evidence holds, and where Purlin stops |
| [The audit](audit.md) | anyone who asks whether the tests are sound | Whether your tests would catch a bug |
| [The research behind the audit](audit-research.md) | a reader who wants the evidence | The papers, the quotes and a trial behind the audit's design |
| [The dashboard](dashboard.md) | everyone | The page that shows where every rule stands |
| [Upgrading](upgrading.md) | a project set up with Purlin 0.9.5 | `purlin:init --update` and what it changes |

## Reference

| File | What it covers |
|------|----------------|
| [Commands](../references/purlin_commands.md) | Every command, its syntax and what it writes |
| [Evidence and sign-off](../references/evidence_and_signoff.md) | The two facts, and which evidence counts for a sign-off |
| [Glossary](../references/glossary.md) | The one word for each concept |
| [Spec format](../references/formats/spec_format.md) | The spec, field by field |
| [Anchor format](../references/formats/anchor_format.md) | The anchor, local and remote |
| [Marker format](../references/formats/marker_format.md) | The comment that ties a test to a proof |
| [Evidence format](../references/formats/evidence_format.md) | The file a run writes for each feature |
| [Package format](../references/formats/package_format.md) | The evidence package `purlin:sign` builds |
| [Signature format](../references/formats/signature_format.md) | The sign-off file `purlin:sign` writes |
| [Spec quality](../references/spec_quality_guide.md) | Writing a rule and a proof worth having |
| [Audit criteria](../references/review_criteria.md) | The heuristic spot tests, and what the model is sent |
| [Supported frameworks](../references/supported_frameworks.md) | The test tools the first test run recognises |
