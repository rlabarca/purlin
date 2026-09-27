# Glossary

The one list of the words this repository uses for its own concepts. A term here is the spelling
every doc, skill, agent definition and reference uses. The retired table below is the only place
in the shipped prose where a retired spelling may still be written.

## The words

- **rule**: a claim about what the software must do, one line in a spec. **proof**: how the
  claim is observed. **test**: the executable form of a proof, tagged with its rule.
- **spec status**: what the spec says about a rule. **Drafted**: no proof line names it.
  **Ready**: at least one proof names it. Nothing else is read: what a proof is worth is the
  audit's question.
- **evidence level**: one of three questions about a rule, each answered by its own cell.
  **passed**: every tagged test for the rule passed. **strong**: the tests are worth trusting.
  **signed**: a person signed the rule, proof and test hashes.
- **cell**: the answer to one level for one rule. A cell reads one word, carries its reasons,
  and exists only at or below the project's gate. Above the gate a cell is absent, not empty.
- **gate**: the one project setting, `passed`, `strong` or `signed`. A rule **meets the gate**
  when every cell up to the gate's level is met.
- **run**: one execution of the tagged tests. **test results**: what `purlin:test` writes and
  commits after a run, `.purlin/tests/<feature>.json` per feature and `.purlin/tests.md` for the
  project. **record**: the machine's evidence of one audit at `strong` and above: results,
  strength and scope tree, a committed file. Nobody signs a record.
  **source**: where a pass came from, and the folder the record sits in: `ci`
  (`.purlin/records/ci/`, which the git host restricts to the build identity) or `local`
  (`.purlin/records/local/`, which anyone may write, and the test results `purlin:test`
  commits). A record's own `source` field must agree with its folder or the file is ignored.
  Both sources count at every gate, `signed` included: what a signature locks is the
  evidence, not the machine that produced it.
- **platform**: one operating system a counting run covered. The passed cell
  carries one entry per platform, each with its own word, source and time, and
  the cell's own word rolls them up. **partial**: the passed cell's word when a
  rule's tests passed on some platforms and failed or did not run on others.
  `partial` is not met, so a rule green on one machine and red on another
  blocks the gate exactly as a failure does. Test strength is platform
  independent: the breaks are measured once per feature.
- **current**: a record describes the checkout when its commit is HEAD or its scope tree still
  hashes the same. A CI pass that is not current reads **code changed**, and CI clears it on the
  next run.
- **audit**: the level 2 run: the tests, then the breaks and the AI audit on every rule whose
  bar is `strong`. An audit measures how good the tests are and proves a rule strong or weak.
  It writes one record per feature it audited, with the briefs beside it, and commits them
  itself as `purlin: record for <sha7>`; it never pushes. The breaks run on a person's machine
  and nowhere else: CI reruns the tests and verifies. **the breaks**: deliberate changes to the
  code. **test strength**: the share of the breaks the tests caught, as a percentage. Config key
  `min_strength`, record field `test_strength`, status column `Strength`. Measured only at
  `strong` and above.
- **brief**: the machine's report on one rule: the strength beside the minimum, the AI audit's
  observations, and whether it settled. It recommends nothing. **hint**: one sentence a free
  scan of the proof text or the test body wrote, handed to the AI audit inside the brief and
  read by no cell and no surface; the audit's own judgment is what carries it.
- **bar**: the evidence a rule must have before it can be signed, `passed` or `strong`. A tag
  on the rule, `[bar: passed]` or `[bar: strong]`; a rule with no tag takes the project's gate
  as its bar, so `passed` at the gate `passed` and `strong` at `strong` and at `signed`. The
  bar decides what the rule must clear, whether the AI audit runs on it and whether it needs a
  signature. It is bound into a signature, so a bar re-tag stales one.
- **cleared its bar**: a rule whose bar is `passed` and whose passed cell is met, or whose bar
  is `strong` and whose strong cell is met.
- **signable**: a rule that has cleared its bar, needs a signature and does not have a counting
  one. The board's `Signable` column counts them and the `Sign` list holds them.
- **AI audit**: the model review inside an audit. It runs on every rule whose bar is `strong`
  and on no other, and it says what it saw the test observe and whether it could settle the
  question.
- **signature**: a named person's attestation that a rule, its proof, its test and the audit
  that read them belong together, a committed file. It binds an **audit hash** beside the
  triple, taken over the brief's strength, its observations sorted and whether it settled, so a
  re-audit that observes something different stales it. **signer list**: `signers` in
  `.purlin/config.json`, changed by pull request, so who could sign and when is in git history.
  **hold**: a person's committed statement that the test does not prove the proof, with the
  missing case; a hold binds no audit hash, and it wins in the strong cell whatever the tests
  are doing. **note**: the one line a signer writes for a rule reading `manual test` or
  `unsettled`.
- **manual test**: the strong cell's word for a rule whose proofs are `@manual`. No test can be
  written, so a person runs it and a signature with a note records what they saw.
- **not audited**: the strong cell's word for a rule whose bar is `strong` and over whose
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
- **`sign_at`**: which rules need a signature at the gate `signed`. `strong`, the default,
  asks for one on every rule whose bar is `strong`; `all` asks for one on every rule.
  `purlin:init` sets it.
- **origin**: tag on every rule naming its owner: `pm`, `design`, `qa`, `eng`. Default `eng`;
  required under `signed`. Drift routes changes by origin.
- **criterion**: optional tag linking a rule to an upstream acceptance-criterion id.
- **rollup**: rules meeting the gate out of rules total, plus one count per bucket.
- **anchor**: a spec for something shared across features. **local anchor**: in the project.
  **anchor repo**: an optional separate repository holding anchors and designs for one or more
  projects. **pinned anchor**: the project's local copy of an anchor from an anchor repo,
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
  evidence. `remote` is one that does not, and there `purlin:sign` refuses a rule whose tests
  have no `ci` record for the commit being signed.
- **tag run**: the CI run a pushed `signed/<version>` tag starts. It writes nothing: it reruns
  the tagged tests on a clean machine and ends with `gate_check.py --check --verify`, which
  checks every committed signature and hold against this code and every `ci/` file against the
  runner's own identity.
- **protected branch**: the branch a change merges into, and the branch a signature's commit
  has to reach before it counts under `signed`.
- **push**: `git push`. It is free, to any branch, and nothing runs at push time: no hook is
  installed at all. No skill pushes and none opens a pull request; a command commits, prints
  `Run: git push` and stops. That an agent does not push is an instruction in
  `agents/purlin.md`, not a mechanism.
- **tag**: the marker of proven code. `purlin:sign` writes the annotated tag `signed/<version>`
  when every rule meets the gate, naming the commit and the gate, and a person pushes it.
- **remote run**: `purlin:test --remote`, the one case in which Purlin pushes. **run branch**:
  `run/<branch>-<sha7>`, the branch a remote run creates, waits on, pulls the records back from
  and deletes. The branch you are working on is never pushed.

## The chain

For one rule, top to bottom. Each row is a cell; the gate decides how many rows exist.

| Level | Met when | Words the cell can read |
|-------|----------|-------------------------|
| spec | a proof line names the rule | `drafted`, `ready` |
| passed | every proof has a passing test from either source, on every platform a counting run covered, and that pass is current | `passed`, `partial`, `failed`, `no test`, `not run`, `code changed` |
| strong | passed, an audit measured it, the strength at or above `min_strength`, and where the bar is `strong` a brief for the current triple that observed nothing and settled, no hold | `strong`, `weak`, `not audited`, `unsettled`, `manual test`, `held` |
| signed | a counting signature for the current rule, proof, test, bar and audit hashes, where the rule needs one | `signed`, `unsigned`, `stale`, `held` |

A rule's **bucket** is the one tile it is counted in: `untested`, `failing`, `partial`, `passed`,
`strong`, `signed`. Two flags are counted beside the buckets, never instead of them: `stale` and
`held`.

## Where each is defined

| Term | Where the authority lives |
|------|---------------------------|
| spec, rule, proof, tier | `references/formats/spec_format.md` |
| proof marker, proof file | `references/formats/proofs_format.md` |
| anchor spec, pinned anchor | `references/formats/anchor_format.md` |
| record, source, test strength | `references/formats/record_format.md` |
| test results, the table | `references/formats/tests_format.md` |
| signature, hold, note | `references/formats/signature_format.md` |
| the gate, which records count, the signer list | `references/hard_gates.md` |
| drift, the four role views, config field ownership | `references/drift_criteria.md` |
| the hints the audit reads, the two lists, the brief's layers, what the brief reports | `references/review_criteria.md` |
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
| needs a person, needs-a-person, `needs_person` | `manual test` where the proofs are `@manual`, `unsettled` where the AI audit could not settle, `held` where a person holds the rule. The one surviving use is the review list's header, `<n> rules need a person` |
| risk, the `[risk: ...]` tag, the three levels | the **bar**, `passed` or `strong`, tagged `[bar: ...]`. `high` and `medium` map to `[bar: strong]`, `low` to `[bar: passed]` |
| manual audit | `not audited` where the bar is `strong` and no audit has run over this code, `unsettled` where the AI audit ran and could not settle. The flags and rollup keys are `not_audited` and `unsettled` |
| not required | removed. A rule that needs no signature carries `required` false on its signed cell, and the cell reads `signed` or `unsigned` like any other |
| `ai_review_at` | removed. The AI audit runs on every rule whose bar is `strong` |
| `sign_at: high`, `medium`, `low` | `sign_at: strong` or `sign_at: all` |
| the free checks, and every finding name they carried | the **hints** the audit reads, written as plain sentences inside the brief. No name reaches a cell, a list or the board |
| `pre_push`, the pre-push hook, the hook shim and the delegator | removed. Nothing runs at push time and nothing runs at commit time; a push is free |
| `record/<name>` tags, `purlin:audit --tag` | the tag `purlin:sign` writes, `signed/<version>` |
| the pull request run, the pull request comment, the `purlin-dashboard` artifact | CI runs on a run branch and on a `signed/*` tag and nowhere else, and writes no comment and no artifact |
| the branch rulesets `purlin:init` printed | removed. The gate's marker is the tag, and a tag is a marker rather than a barrier |

`audit` is not retired. It means one thing: the level-2 run, which proves a rule strong or weak.
The grading scores the old `purlin:audit` printed stay retired, in the table below.

### Retired earlier

| Retired | Use instead |
|---------|-------------|
| gauge, Proof Design, Proof Integrity | removed. Both grading scores are gone |
| `PROVABLE`, `LOOSE`, `UNPROVABLE`, `STRUCTURAL` | removed with Proof Design |
| `STRONG`, `WEAK`, `HOLLOW`, `EXCLUDED` | removed with Proof Integrity |
| receipt, vhash, `*.receipt.json` | record: `.purlin/records/<source>/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json` |
| `verify:` as a commit prefix | `purlin: record for <commit7>` |
| platform registry, `@on(<id>)`, `--platform` | `@env(windows)`, `@env(macos)`, `@env(linux)`, and the CI matrix. **`platform` itself is not retired**: it means one operating system a counting run covered, and the passed cell lists them under `platforms` |
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
| the source `developer`, a record a person commits | removed. A record's source is its folder, `ci` or `local`; `purlin:audit` writes into `local/` and a person's own test run is the test results `purlin:test` commits |
| `purlin:audit --commit` | removed. `purlin:audit` always writes and commits its record; `purlin:test` commits the test results |
| `purlin:audit --remote` | `purlin:test --remote`: a remote runner runs the tests |
| `purlin_run.py --record` | `purlin_run.py --audit`, and `--ci` for the CI job's arm |
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
