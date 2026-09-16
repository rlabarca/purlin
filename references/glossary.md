# Glossary

The one list of the words this repository uses for its own concepts. A term here is the spelling
every doc, skill, agent definition and reference uses. The retired table below is the only place
in the shipped prose where a retired spelling may still be written.

## The words

- **rule**: a claim about what the software must do, one line in a spec. **proof**: how the
  claim is observed. **test**: the executable form of a proof, tagged with its rule.
  **record**: one verify run's observations, a committed file. **approval**: a named
  person's attestation that a rule, proof and test belong together, a committed file.
  **hold**: a person's committed statement that a rule's test does not prove its proof, with
  the missing case; CI does not approve a held rule.
- **anchor**: a spec for something shared across features. **local anchor**: in the project.
  **anchor repo**: an optional separate repository holding anchors and designs for one or more
  projects. **pinned anchor**: the project's local copy of an anchor from an anchor repo,
  tied to a commit.
- **gate**: the one project setting, what CI must see before a change can merge: `tested`,
  `recorded`, `approved`.
- **test strength**: of the deliberate breaks made to the code, the share the tests caught,
  as a percentage. Config key `min_strength`, record field `test_strength`, status column
  `strength`.
- **approver list**: the emails of the people who may approve, kept in `.purlin/config.json`
  and changed by pull request, so who could approve and when is in git history. An approval
  counts when its commit is signed by someone on the list. People are added or removed at any
  time.
- **git host**: the service that holds the repository, runs CI, and enforces branch rules:
  GitHub or Azure DevOps. **CI**: the git host's hosted runner executing the same
  `purlin:verify` a developer runs, on every push and pull request.
- **origin**: tag on every rule naming its owner: `pm`, `design`, `qa`, `eng`. Default `eng`;
  required under `approved`. Drift routes changes by origin.
- **risk**: tag on a rule, `high`, `medium`, `low`; default `low`; required under `approved`.
- **criterion**: optional tag linking a rule to an upstream acceptance-criterion id.
- **The seven states** of a rule: Drafted (no proof), Proof ready (the proof text passes the
  free checks), Tested (a tagged test passes locally), Recorded (a record that counts under the
  gate exists at HEAD and passes), Reviewed (a brief exists for the current hashes), Approved
  (a current approval exists and the record passes), Stale (the rule, proof or test text
  changed after approval; a human must look). A separate flag, **re-verify pending**, means
  only the code changed: the approval stands and CI clears it on the next run.

## Where each is defined

| Term | Where the authority lives |
|------|---------------------------|
| spec, rule, proof, tier | `references/formats/spec_format.md` |
| proof marker, proof file | `references/formats/proofs_format.md` |
| anchor spec, pinned anchor | `references/formats/anchor_format.md` |
| record, test strength, the gate, the approver list | `references/hard_gates.md` |
| drift, the four role views, config field ownership | `references/drift_criteria.md` |
| the review list, what makes a rule need a look | `references/review_criteria.md` |
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

| Retired | Use instead |
|---------|-------------|
| audit, `purlin:audit`, the `purlin-auditor` agent | removed. `purlin:review` is where a person looks at a rule |
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
| queue, review queue | review list |
| CODEOWNERS, approver rule | the approver list in `.purlin/config.json` |
| `verify --manual`, `verify --recheck` | removed. `@manual` proofs are evidenced by an approval file with a one-line note |
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
