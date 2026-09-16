# Glossary

The one list of the words this repository uses for its own concepts. A term here is the spelling
every doc, skill, agent definition and reference uses. The retired table below is the only place
in the shipped prose where a retired spelling may still be written.

## The words

- **rule**: a claim about what the software must do, one line in a spec. **proof**: how the
  claim is observed. **test**: the executable form of a proof, tagged with its rule.
- **spec status**: what the spec says about a rule. **Drafted**: no proof line names it.
  **Ready**: at least one proof names it and no blocking free check fires on the proof text.
- **evidence level**: one of three questions about a rule, each answered by its own cell.
  **passed**: every tagged test for the rule passed. **strong**: the tests are worth trusting.
  **signed**: a person signed the rule, proof and test hashes.
- **cell**: the answer to one level for one rule. A cell reads one word, carries its reasons,
  and exists only at or below the project's gate. Above the gate a cell is absent, not empty.
- **gate**: the one project setting, `passed`, `strong` or `signed`. A rule **meets the gate**
  when every cell up to the gate's level is met.
- **run**: one execution of the tagged tests. **record**: the machine's evidence of one run:
  results, strength and scope tree, a committed file written by `purlin:audit`. Nobody signs a
  record. **source**: where a pass came from: `ci` (a record CI wrote), `developer` (a record a
  person committed), `local` (the last run in this checkout). Under `passed` every source
  counts. Under `strong` and `signed` only `ci` counts.
- **current**: a record describes the checkout when its commit is HEAD or its scope tree still
  hashes the same. A CI pass that is not current reads **code changed**, and CI clears it on the
  next run.
- **audit**: the level 2 run: the tests, then the breaks, the free checks and the model review
  where risk asks, ending in a record and, on CI, the briefs. An audit proves a rule strong or
  weak. **the breaks**: deliberate changes to the code. **test strength**: the share of the
  breaks the tests caught, as a percentage. Config key `min_strength`, record field
  `test_strength`, status column `Strength`. Measured only at `strong` and above.
- **brief**: the machine's report on one rule: the strength beside the minimum, the free-check
  findings on the proof text and the test body, the model review's observations, and whether it
  settled. It recommends nothing.
- **signature**: a named person's attestation that a rule, proof and test belong together, a
  committed file. **signer list**: `signers` in `.purlin/config.json`, changed by pull request,
  so who could sign and when is in git history. **hold**: a person's committed statement that
  the test does not prove the proof, with the missing case. **note**: the one line a signer
  writes for a `@manual` proof or an unsettled review.
- **signature stale**: the signed cell's word when a signature exists and its hashes no longer
  match.
- **review list**: the rules whose next step is a person. Exists only at `strong` and above.
- **risk**: tag on a rule, `high`, `medium`, `low`; default `low`. Read only at `strong` and
  above; never asked, shown or required under `passed`.
- **origin**: tag on every rule naming its owner: `pm`, `design`, `qa`, `eng`. Default `eng`;
  required under `signed`. Drift routes changes by origin.
- **criterion**: optional tag linking a rule to an upstream acceptance-criterion id.
- **rollup**: rules meeting the gate out of rules total, plus one count per bucket.
- **anchor**: a spec for something shared across features. **local anchor**: in the project.
  **anchor repo**: an optional separate repository holding anchors and designs for one or more
  projects. **pinned anchor**: the project's local copy of an anchor from an anchor repo,
  tied to a commit.
- **git host**: the service that holds the repository, runs CI, and enforces branch rules:
  GitHub or Azure DevOps. **CI**: the git host's hosted runner executing the same
  `purlin:audit` a developer runs, on every push and pull request.

## The chain

For one rule, top to bottom. Each row is a cell; the gate decides how many rows exist.

| Level | Met when | Words the cell can read |
|-------|----------|-------------------------|
| spec | the proof text clears the blocking free checks | `drafted`, `ready` |
| passed | every proof has a passing test from a counting source, and a CI pass is current | `passed`, `failed`, `no test`, `not run`, `code changed` |
| strong | passed from `ci`, the strength at or above `min_strength`, no finding, the model review settled where risk asks, no hold | `strong`, `weak`, `needs a person` |
| signed | a counting signature for the current hashes, when risk is at or above `sign_at` | `signed`, `unsigned`, `stale`, `held`, `not required` |

A rule's **bucket** is the one tile it is counted in: `untested`, `failing`, `passed`, `strong`,
`signed`. Two flags are counted beside the buckets, never instead of them: `stale` and `held`.

## Where each is defined

| Term | Where the authority lives |
|------|---------------------------|
| spec, rule, proof, tier | `references/formats/spec_format.md` |
| proof marker, proof file | `references/formats/proofs_format.md` |
| anchor spec, pinned anchor | `references/formats/anchor_format.md` |
| record, source, test strength | `references/formats/record_format.md` |
| signature, hold, note | `references/formats/signature_format.md` |
| the gate, which records count, the signer list | `references/hard_gates.md` |
| drift, the four role views, config field ownership | `references/drift_criteria.md` |
| the review list, the brief's layers, what the brief reports | `references/review_criteria.md` |
| every command's syntax and one-liner | `references/purlin_commands.md` |
| every commit message shape | `references/commit_conventions.md` |

## Skill one-liners

Every skill has exactly one purpose sentence, and it lives in the Purpose column of
`references/purlin_commands.md`. The frontmatter `description` of `skills/<name>/SKILL.md`, the
README table and the `agents/purlin.md` table all carry that same sentence. It is not copied
here: another copy is another thing to edit and the one a reader meets stale.

## Retired terms

The retired spelling on the left may appear on this page and nowhere else in a shipped file.
The repository's own vocabulary check enforces that, reading this table for the terms.

### Retired by the three-level model

| Retired | Use instead |
|---------|-------------|
| tested, Tested, the `tested` gate | `passed`: the level-1 cell word and the first gate value |
| recorded, Recorded, the `recorded` gate | `strong`: the level-2 cell word and the second gate value |
| approved, Approved, the `approved` gate | `signed`: the level-3 cell word and the third gate value |
| approve | sign |
| approval | signature |
| approver, approvers | signer, signers. The config key is `signers` |
| verified | the cell word: `passed`, `strong` or `signed` |
| verdict, the four verdicts | what the brief reports: the strength, the findings, the `observations` and `settled` |
| Reviewed | removed. A brief is written by the audit; no state stands for it |
| re-verify, re-verify pending | `code changed`, the passed cell's word when the record is not current |
| Proof ready | `ready`, the spec status |
| lowest state | `blocked_by`, the lowest unmet cell |
| the seven states | the spec status and the three evidence levels |
| auto-approval | removed. CI writes no signature file, ever |
| review queue | review list |
| `purlin:verify` | `purlin:audit` |
| `purlin:review` | `purlin:sign` with no argument, which walks the review list |
| `purlin:approve` | `purlin:sign` |
| `verify_gate`, `scripts/ci/verify_gate.py` | `gate_check`, `scripts/ci/gate_check.py` |
| `verify-gate:` as a log prefix | `gate:` |
| `validated/<name>` tags | `record/<name>` tags |

`audit` is not retired. It means one thing: the level-2 run, which proves a rule strong or weak.
The grading scores the old `purlin:audit` printed stay retired, in the table below.

### Retired earlier

| Retired | Use instead |
|---------|-------------|
| gauge, Proof Design, Proof Integrity | removed. Both grading scores are gone |
| `PROVABLE`, `LOOSE`, `UNPROVABLE`, `STRUCTURAL` | removed with Proof Design |
| `STRONG`, `WEAK`, `HOLLOW`, `EXCLUDED` | removed with Proof Integrity |
| receipt, vhash, `*.receipt.json` | record: `.purlin/records/<feature>/<timestamp>-<commit7>-<runner>.json` |
| `verify:` as a commit prefix | `purlin: record for <commit7>` |
| platform, platform registry, `@on(<id>)`, `--platform` | `@env(windows)`, `@env(macos)`, `@env(linux)`, and the CI matrix |
| `AWAITING RUNNER` | `needs <os>` |
| mutation score, caught score, kill rate | test strength |
| mutation testing | the breaks, in prose; `mutation_engine` in config and code |
| mode, pre-push mode, external LLM mode | removed. The gate is the one setting |
| records branch | records live in the tree, under `.purlin/records/` |
| Pages, the published dashboard site | the `purlin-dashboard` build artefact, linked from the pull request comment |
| forge | git host |
| queue | review list |
| CODEOWNERS, approver rule | the signer list in `.purlin/config.json` |
| `verify --manual`, `verify --recheck` | removed. `@manual` proofs are evidenced by a signature file with a one-line note |
| `figma://`, `> Visual-Reference:`, the visual hash | `designs/<feature>/` files, pinned by a design anchor |
| `3-section format` | `2-section format`: `## Rules` and `## Proof` |
| `## What it does` | the `> Description:` continuation lines |
| `anchor file`, `.anchor.md` | `specs/_anchors/<name>.md` |
| `specs/schema/` | `specs/_anchors/` |
| `toolkit` | the Purlin plugin |
| `read-only` | "writes no code and no test files", or "pinned" for an anchor with a `> Source:` |
| `dev` as a role token | `eng` |
| `/purlin:` | `purlin:` |
| `--set`, `--sync-audit-criteria`, `--criteria`, `--anchor`, `--review`, `--resume`, `--local`, `--list-plugins`, `--mcp` | removed |
| `(confirmed)` on a rule | no tag at all |
