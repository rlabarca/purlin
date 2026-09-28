# Glossary

The one list of the words this repository uses for its own concepts. A term here is the spelling
every doc, skill, agent definition and reference uses. The retired table below is the only place
in the shipped prose where a retired spelling may still be written.

## The words

- **rule**: a claim about what the software must do, one line in a spec. **proof**: how the
  claim is observed. **test**: the executable form of a proof, tagged with its rule.
- **no proof written**: the reason the passed cell gives for a rule no proof line names. The
  cell reads `no test`, and the next step is `purlin:spec`.
- **evidence level**: one of three questions about a rule, each answered by its own cell.
  **passed**: every tagged test for the rule passed. **strong**: the tests are worth trusting.
  **signed**: a person signed the rule, proof and test hashes, in a signed commit.
- **cell**: the answer to one level for one rule. A cell reads one word, carries its reasons,
  and exists only at or below the project's gate. Above the gate a cell is absent, not empty.
- **gate**: the one project setting, `passed`, `strong` or `signed`. A rule **meets the gate**
  when every cell up to the gate's level is met.
- **run**: one execution of the tagged tests. **evidence**: what runs saw, one file per
  feature per source, `.purlin/evidence/<source>/<feature>.json`, with one **section** per
  operating system and, once an audit has read the feature, what the audit found; the table
  `.purlin/tests.md` sums it up for the project. `purlin:test` and `purlin:audit` write it and
  `--commit` commits it; nobody signs it. **source**: where a pass came from, and the folder the
  file sits in: `ci` (`.purlin/evidence/ci/`, which a remote runner writes and a tag run checks
  the provenance of) or `local` (`.purlin/evidence/local/`, which anyone may write). A file's
  own `source` field must agree with its folder or the file is ignored. Both sources count at
  every gate, `signed` included: what a signature locks is the evidence, not the machine that
  produced it.
- **platform**: one operating system a counting run covered. The passed cell
  carries one entry per platform, each with its own word, source and time, and
  the cell's own word rolls them up. **partial**: the passed cell's word when a
  rule's tests passed on some platforms and failed or did not run on others.
  `partial` is not met, so a rule green on one machine and red on another
  blocks the gate exactly as a failure does. Test strength is platform
  independent: the breaks are measured once per feature.
- **current**: a section describes the checkout while its **fingerprint**, over the spec, the
  covered code and the tests, is the one taken now. A pass that is not current reads **out of
  date**, naming what changed, and the next run clears it.
- **audit**: the level 2 run: the tests, then the breaks and the AI audit on every rule whose
  level is `strong` or `signed`. An audit measures how good the tests are and proves a rule strong or weak.
  It writes what it found into each feature's evidence, and `--commit` commits it as
  `purlin: evidence at <sha7>`; it never pushes. The breaks run on a person's machine
  and nowhere else: CI reruns the tests and verifies. **the breaks**: deliberate changes to the
  code. **test strength**: the share of the breaks the tests caught, as a percentage. Config key
  `min_strength`, evidence field `audit.mutation`, status column `Strength`. Measured only at
  `strong` and above.
- **brief**: the machine's report on one rule: the strength beside the minimum, the AI audit's
  observations, and whether it settled. It recommends nothing.
- **level**: what a rule must have to meet the gate, in the gate's own words: `passed` its
  tests; `strong` its tests and the audit; `signed` its tests, the audit and a signature. A tag
  on the rule, `[level: passed]`, `[level: strong]` or `[level: signed]`; a rule with no tag
  takes the project's gate. The gate is the ceiling, so a tag above it is read as the gate. A
  signature logs the level and does not lock it.
- **signable**: a rule whose level is `signed`, whose passed and strong cells are met, and that
  does not have a counting signature. The board's `Signable` column counts them and the `Sign`
  list holds them.
- **AI audit**: the model's read of one rule inside an audit. It runs on every rule whose level
  is `strong` or `signed`, and on no other, and it says what it saw the test observe and whether it could settle the
  question.
- **signature**: a named person's attestation that a rule, its proof, its test and the audit
  that read them belong together, a committed file. It binds an **audit hash** beside the
  triple, taken over the test strength and the `verdict` and sorted `findings` of the audit
  entry for the current hashes, so a re-audit that finds something different stales it. Signing is logged, not policed: the
  file names the signer and git names the commit's author, and no list says who may sign.
  **counting signature**: under `signed`, one whose commit is signed and verifies and whose
  bound hashes still match the rule, proof, test and audit; below `signed`, any committed
  one. It counts on whatever commit carries it. **hold**: a person's committed statement that the test does not prove the proof, with the
  missing case; a hold binds no audit hash, and it wins in the strong cell whatever the tests
  are doing. **note**: the one line a signer writes for a rule reading `manual test` or
  `unsettled`.
- **manual test**: the strong cell's word for a rule whose proofs are `@manual`. No test can be
  written, so a person runs it and a signature with a note records what they saw.
- **not audited**: the strong cell's word for a rule whose level is `strong` or `signed` and over whose
  current code no audit has run. It is on no list: `purlin:audit` moves it, not a person.
- **unsettled**: the strong cell's word for a rule whose AI audit ran and could not tell
  whether the test observes what the proof names. A person judges the proof against the test
  and signs, adds a case or holds. Where no model could be reached the audit did not run, so
  nothing is unsettled: the strength answers level 2 on its own.
- **signature stale**: the signed cell's word when a signature exists and its hashes no longer
  match.
- **Review**: the list of rules whose strong cell reads `manual test`, `unsettled` or `held`.
  Exists only at `strong` and above. **Sign**: the list of signable rules, at the gate
  `signed`. **review list**: the two together, which is what `purlin:sign` walks.
- **rollup**: rules meeting the gate out of rules total, plus one count per bucket.
- **anchor**: a spec for something shared across features. **local anchor**: in the project.
  **anchor repo**: an optional separate repository holding anchors for one or more projects. **pinned anchor**: the project's local copy of an anchor from an anchor repo,
  tied to a commit.
- **git host**: the service that holds the repository and runs CI: GitHub or Azure DevOps.
  **CI**: the git host's hosted runner executing the same run script a person runs, on a run
  branch and on a signing tag and nowhere else. **remote runner**: CI seen from a person's
  machine. A project has one for two reasons and no others: a proof is tagged `@env` for an
  operating system this machine is not, and a project whose trust is `remote`. A project with
  neither gets no workflow at all.
- **trust**: the one setting that is not derived from the gate, asked once by `purlin:init` as
  `Do you trust your own machine for the tests and the signing? [y/n]` and written as `trust`.
  `local`, the default, is a project whose own runs count and whose own signature is the
  evidence. `remote` is one that does not, and there `purlin:sign` refuses a rule with a test
  whose feature has no current `ci` section.
- **tag run**: the CI run a pushed `signed/<version>` tag starts. It writes nothing: it reruns
  the tagged tests on a clean machine and ends with `gate_check.py --check --verify`, which
  checks every committed signature and hold against this code and every `ci/` file against the
  runner's own identity.
- **push**: `git push`. It is free, to any branch, and nothing runs at push time: no hook is
  installed at all. No skill pushes and none opens a pull request; a command commits, prints
  `Run: git push` and stops. That an agent does not push is an instruction in
  `agents/purlin.md`, not a mechanism.
- **tag**: the marker of proven code. `purlin:sign` writes the annotated tag `signed/<version>`
  when every rule meets the gate, naming the commit and the gate, and a person pushes it.
  **`signed/<version>` means**: at the tagged commit every rule meets the gate, which is that
  its passed cell is met, its strong cell where its level is `strong` or `signed`, and a
  counting signature where its level is `signed`. A rule whose level asks for no signature
  does not hold the tag back for one, and `trust: remote`
  is read when a rule is signed, not by the tag. `references/hard_gates.md` gives it at length.
- **remote run**: `purlin:test --remote`, the one case in which Purlin pushes. **run branch**:
  `run/<branch>-<sha7>`, the branch a remote run creates, waits on, pulls the evidence back from
  and deletes. The branch you are working on is never pushed.

## The chain

For one rule, top to bottom. Each row is a cell; the gate decides how many rows exist.

| Level | Met when | Words the cell can read |
|-------|----------|-------------------------|
| passed | a proof line names the rule and every proof has a passing test in a current section from either source, on every platform a current section covers | `passed`, `partial`, `failed`, `no test`, `not run`, `out of date` |
| strong | passed, an audit measured it, the strength at or above `min_strength`, and where the level is `strong` or `signed` an audit entry for the current hashes that settled and found nothing, no hold | `strong`, `weak`, `not audited`, `unsettled`, `manual test`, `held` |
| signed | a counting signature for the current rule, proof, test and audit hashes | `signed`, `unsigned`, `stale`, `held` |

A rule's **bucket** is the one tile it is counted in: `untested`, `failing`, `partial`, `passed`,
`strong`, `signed`. Two flags are counted beside the buckets, never instead of them: `stale` and
`held`.

## Where each is defined

| Term | Where the authority lives |
|------|---------------------------|
| spec, rule, proof | `references/formats/spec_format.md` |
| proof marker, proof file | `references/formats/proofs_format.md` |
| anchor spec, pinned anchor | `references/formats/anchor_format.md` |
| evidence, source, section, fingerprint, test strength, the table | `references/formats/evidence_format.md` |
| signature, hold, note | `references/formats/signature_format.md` |
| the gate, which evidence counts, when a signature counts, what `signed/<version>` means | `references/hard_gates.md` |
| drift, the four role views, config field ownership | `references/drift_criteria.md` |
| what the audit looks for, the two lists, the brief's layers, what the brief reports | `references/review_criteria.md` |
| every command's syntax and one-liner | `references/purlin_commands.md` |
| every commit message shape | `references/commit_conventions.md` |

## Skill one-liners

Every skill has exactly one purpose sentence, and it lives in the Purpose column of
`references/purlin_commands.md`. The frontmatter `description` of `skills/<name>/SKILL.md` and
the README table carry that same sentence; `agents/purlin.md` routes a phrase to a command and
repeats no purpose. It is not copied here: another copy is another thing to edit and the one a
reader meets stale.

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
| approver, approvers | signer. No config key names the people who may sign |
| verified | the cell word: `passed`, `strong` or `signed` |
| verdict, the four verdicts | what the brief reports: the strength, the findings, the `observations` and `settled` |
| Reviewed | removed. A brief is written by the audit; no state stands for it |
| re-verify, re-verify pending | `out of date`, the passed cell's word when the evidence is not current |
| Proof ready | the passed cell; a rule no proof line names reads `no test`, with the reason `no proof written` |
| lowest state | `blocked_by`, the lowest unmet cell |
| the seven states | the three evidence levels |
| auto-approval | removed. CI writes no signature file, ever |
| review queue | review list |
| `purlin:verify` | `purlin:audit` |
| `purlin:review` | `purlin:sign` with no argument, which walks the review list |
| `purlin:approve` | `purlin:sign` |
| `verify_gate`, `scripts/ci/verify_gate.py` | `gate_check`, `scripts/ci/gate_check.py` |
| `verify-gate:` as a log prefix | `gate:` |
| `validated/<name>` tags | the tag `purlin:sign` writes, `signed/<version>` |
| needs a person, needs-a-person, `needs_person` | `manual test` where the proofs are `@manual`, `unsettled` where the AI audit could not settle, `held` where a person holds the rule. The one surviving use is the review list's header, `<n> rules need a person` |
| risk, the `[risk: ...]` tag, the three levels | the **level**, tagged `[level: ...]` with the gate's own words |
| manual audit | `not audited` where the level is `strong` or `signed` and no audit has run over this code, `unsettled` where the AI audit ran and could not settle. The flags and rollup keys are `not_audited` and `unsettled` |
| not required | removed. A rule whose level is below `signed` needs no signature, and its signed cell reads `signed` or `unsigned` like any other |
| `ai_review_at` | removed. The AI audit runs on every rule whose level is `strong` or `signed` |
| the free checks, and every finding name they carried | the AI audit's observations, written as plain sentences inside the brief. No name reaches a cell, a list or the board |
| free scan, free scans, hint, hints (a scan's sentence handed to the audit) | the AI audit's observations. Nothing scans a proof or a test before the audit; `references/review_criteria.md` lists what the audit looks for |
| `pre_push`, the pre-push hook, the hook shim and the delegator | removed. Nothing runs at push time and nothing runs at commit time; a push is free |
| `record/<name>` tags, `purlin:audit --tag` | the tag `purlin:sign` writes, `signed/<version>` |
| the pull request run, the pull request comment, the `purlin-dashboard` artifact | CI runs on a run branch and on a `signed/*` tag and nowhere else, and writes no comment and no artifact |
| the branch rulesets `purlin:init` printed | removed. The gate's marker is the tag, and a tag is a marker rather than a barrier |
| `signers`, the signer list, `signer list missing` | removed. Signing is logged, not policed: a signature names its signer and git names the author. `purlin:init --update` drops the key |
| the protected branch, `is_ancestor` | removed. A signature counts on whatever commit carries it, and init checks only a remote and its host |
| the self-signing check, `the signer last touched the test` | removed. A signature counts whoever last committed to the test file; git names both authors |
| `--quick`, the first arm of `scripts/run/purlin_run.py` | `--test`, the arm `purlin:test` runs. `--quick` is refused as an unknown flag |

`audit` is not retired. It means one thing: the level-2 run, which proves a rule strong or weak.
The grading scores the old `purlin:audit` printed stay retired, in the table below.

### Retired earlier

| Retired | Use instead |
|---------|-------------|
| gauge, Proof Design, Proof Integrity | removed. Both grading scores are gone |
| `PROVABLE`, `LOOSE`, `UNPROVABLE`, `STRUCTURAL` | removed with Proof Design |
| `STRONG`, `WEAK`, `HOLLOW`, `EXCLUDED` | removed with Proof Integrity |
| receipt, vhash, `*.receipt.json` | the evidence: `.purlin/evidence/<source>/<feature>.json` |
| `verify:` as a commit prefix | `purlin: evidence at <commit7>` |
| platform registry, `@on(<id>)`, `--platform` | `@env(windows)`, `@env(macos)`, `@env(linux)`, and the CI matrix. **`platform` itself is not retired**: it means one operating system a counting run covered, and the passed cell lists them under `platforms` |
| `AWAITING RUNNER` | `needs <os>` |
| mutation score, caught score, kill rate | test strength |
| mutation testing | the breaks, in prose; `mutation_engine` in config and code |
| mode, pre-push mode, external LLM mode | removed. The gate is the one setting |
| records branch | the evidence lives in the tree, under `.purlin/evidence/` |
| Pages, the published dashboard site | the dashboard page each person opens from disk |
| forge | git host |
| queue | review list |
| CODEOWNERS, approver rule | removed. No file names who may sign; a signature names its signer |
| `verify --manual`, `verify --recheck` | removed. `@manual` proofs are evidenced by a signature file with a one-line note |
| the source `developer` | removed. An evidence file's source is its folder, `ci` or `local`; `purlin:test` and `purlin:audit` write into `local/` |
| `purlin:audit --remote` | `purlin:test --remote`: a remote runner runs the tests |
| `purlin_run.py --record` | `purlin_run.py --audit`, and `--ci` for the CI job's arm |
| `figma://`, `> Visual-Reference:`, the visual hash | removed: no design file is tied to a spec |
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
