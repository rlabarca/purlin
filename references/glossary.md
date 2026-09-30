# Glossary

The one list of the words this repository uses for its own concepts. A word here is the
spelling every doc, skill, agent definition and reference uses, with its one definition; every
other page points here rather than defining it again.

## The words

- **spec**: one Markdown file under `specs/<category>/<name>.md`, with a `## Rules` section and
  a `## Proof` section. **feature**: what a spec describes, named by its file. **scope**: the
  `> Scope:` line, the files the feature's code lives in. It is optional below the gate
  `signed` and required at `signed`, where a rule of a spec that names no files is signed and
  its signature does not count.
- **rule**: one line in a spec saying what must be true, `RULE-<n>`.
- **proof**: one line in a spec saying in plain language how a rule is shown to hold,
  `PROOF-<n> (RULE-<n>)`. QA writes and reviews proofs, and AI may draft them against the
  guideline in `references/spec_quality_guide.md`. Proofs are optional at the gate `passed` and
  required from `strong` up. **`@manual`**: a proof a person carries out by hand, with no test.
  **`@env(<os>)`**: a proof that can only be shown on `windows`, `macos` or `linux`.
- **system**: an operating system. A spec, the evidence and a signature store it as `windows`,
  `macos` or `linux`, and every system that is not Windows or macOS is `linux`. A person reads
  it as `Windows`, `macOS` or `Linux/Unix`, and in the dashboard's small boxes as `Win`, `Mac`
  or `Lin`.
- **test**: any test in the project's own suite that carries a marker. **marker**: one comment
  above a test, in the language's own comment syntax, `purlin: <feature> PROOF-<n>`, or
  `purlin: <feature> RULE-<n>` where the rule has no proof. A test with no marker runs as it
  always did and Purlin ignores it.
- **suite**: one entry of the `tests` setting: the project's own test command, where its
  **report** lands, the report's format and the globs its test files live under. Setup leaves
  the setting empty; the first test run suggests an entry for each test tool it recognises, and
  they are written together once a person confirms them.
- **step**: `passed`, `strong` or `signed`, in that order, each containing the one before.
  `passed`: every test tied to the rule ran and passed. `strong`: those tests passed and the
  audit found them sound. `signed`: both, and a person signed the rule.
- **gate**: the one project setting, `passed`, `strong` or `signed`: the last step every rule
  must reach before a version is finished. Every rule is asked what the gate asks.
- **cell**: the answer to one step for one rule. It reads one word and carries its reasons,
  and exists only at or below the gate. The words each cell can read are in the chain below.
- **summary**: the sentence every run, every audit and `purlin:status` end on, one count per
  step up to the gate: `40 rules. 35 pass their tests. 30 are strong. 20 are signed.` A rule
  is counted once, under the feature that owns it.
- **Left to do**: the list under the summary, one line per kind of remaining work, in the order
  the work is done, each with its count and the command that does it; a kind at zero is left
  out. The first line is the next step. The kinds, as printed: `to write a proof for`,
  `to correct`, `to fix`, `to write a test for`, `to test`, `to test on <systems>`,
  `to test by hand`, `to audit`, `to measure`, `to strengthen`, `to tie to its files`,
  `to sign` and `the version to tag`.
  `references/hard_gates.md` says when each applies. **finished**: a version with nothing left
  to do.
- **run**: one execution of the project's suites by `purlin:test` or `purlin:audit`.
- **evidence**: what runs saw, one file per feature per source,
  `.purlin/evidence/<source>/<feature>.json`, with one **section** per system and, once the
  audit has read the feature, what the audit found. Each section names the **machine** it ran
  on: the host's name for a person's run, `remote runner, <system>` for a remote runner's. A
  run writes it; `--commit` commits it, after a commit of the specs, tests and settings it
  describes. **source**: the folder the file sits in, `local` (a person's own run) or `ci` (a
  remote runner's). Both count at every gate. **the table**: `.purlin/tests.md`, one row per
  feature, written with the evidence.
- **platform**: one system a current section covered. **partial**: the passed cell's word when
  a rule's tests passed on one system and failed on another. It is not met. A system that has
  not run reads `not run`.
- **fingerprint**: a hash over the spec, the covered code and the tests, taken when a run
  writes a section. **current**: a section whose fingerprint matches the tree now. **out of
  date**: the passed cell's word when the newest section is not current, naming what changed,
  `code changed since <sha7>`, `spec changed since ...` or `tests changed since ...`. The next
  run clears it. `purlin:test` with no feature named runs the features that are out of date or
  have no run on this system.
- **audit**: `purlin:audit`: the tests, the breaks where mutation testing is on, then the AI
  audit, written into each feature's evidence. **AI audit**: one model call per rule, reading
  the rule, its proofs and its tests against `references/review_criteria.md`. Each answer names
  the model that gave it. **finding**: one sentence the AI audit wrote about a gap. A finding
  makes the rule `weak`, and a weak rule is left to do as `to strengthen`. A proof longer than
  the standard, or holding two cases, is written among the audit's notes and does not make the
  rule weak. **waiting**: the word a cell reads while the cell below it is not met, and the
  neutral one on every surface: the strong cell `waiting for its tests to pass`, and the signed
  cell `waiting for the audit`. It is never met and it is not `weak`.
- **mutation testing**, **the breaks**: deliberate changes to the code, to see whether the tests
  catch them. Optional, off by default, asked about only at the gates `strong` and `signed`,
  set by `mutation_engine`. **test strength**: the share of one feature's breaks the tests
  caught, as a percentage, compared with `min_strength`. `references/hard_gates.md`, under the
  gate table, says how it reaches a rule.
- **hand check**: the check of a rule with a `@manual` proof. A person carries the proof out
  and signs the rule with `purlin:sign`, at any gate, with a **note** saying what they saw when
  they give one. That one act stands for the test, the audit and the signature of the rule.
  Until it is done the rule is left to do as `to test by hand`.
- **signature**: a person's attestation, for one rule in one feature, that the rule, its proof,
  its test, the code the feature lists, what the audit found, and the machine the tests ran on
  for each system belong together. One file under `specs/<category>/<feature>.signatures/`, committed in a signed
  commit by `purlin:sign`. It records the signer's name and email as git holds them, the time
  and the key's fingerprint, and not the machine it was signed on. **audit hash**: the hash over
  what the audit found. **counting signature**: one whose commit carries a signature, made with
  any key, and whose hashes still match. A change to anything it covers ends it, with no
  message, and the rule is left to do as `to sign`; a result from a system it did not cover
  ends nothing. An anchor's rule is signed once in each feature it applies to.
- **version**: the name of what is tagged, read from the `VERSION` file at the project root,
  then from the version the project's package description states; `purlin:sign` asks for one
  when neither gives it.
- **tag**: `signed/<version>`, the signed tag `purlin:sign` writes at the gate `signed` when
  nothing is left to do and every result came from committed work, on the commit that carries
  the evidence package. Below `signed` no tag is written. `references/hard_gates.md` gives it
  at length. A person pushes it.
- **evidence package**: one data file describing one version,
  `.purlin/evidence/package/<version>.json`: every rule's words, proofs, tests, results, what
  the audit found and who signed, the count at each step, what is left, the state `finished`
  or `not finished`, and a fingerprint of its own bytes. `purlin:export` writes it at any gate,
  and at the gate `signed` `purlin:sign` commits it just before the tag. It is what a person
  hands to a regulated document and sign-off system.
- **git host**: GitHub or Azure DevOps. With neither, the settings say `ci: none`, and
  everything on a person's own machine still works. **remote runner**: the git host's CI
  running the same run script a person runs. A project has one for one reason: a proof tagged
  `@env` for a system this machine is not. What it runs is in `references/hard_gates.md`,
  "Where a runner runs". **remote
  run**: `purlin:test --remote`, which pushes a **run branch**, `run/<branch>-<sha7>`, waits
  for the runner and pulls its evidence back. **runner file**: the file setup writes for the
  git host, `.github/workflows/purlin.yml` or `azure-pipelines.yml`, with one job for each
  system a proof is tagged `@env` for that the machine running setup is not. **tag run**: the run a pushed `signed/*` tag
  starts, which runs the tests and nothing else.
- **drift**: `purlin:drift`, the facts your last pull, merge, rebase, checkout, clone or reset
  brought in, in one view per role: `pm`, `eng` or `qa`.
- **role**: product, developer or QA. There are no others.
- **anchor**: a spec for something shared across features, under `specs/_anchors/`, a folder
  created with the first anchor. A feature spec names the anchors whose rules apply to it with
  `> Requires:`; `> Requires:` names anchors only. **pinned anchor**: a local copy of an anchor from another
  repository, tied to a commit by `> Pinned:`. **anchor repo**: a repository that holds anchors
  for one or more projects.

## The chain

For one rule, top to bottom. Each row is a cell; the gate decides how many rows exist.

| Step | Reached when | Words the cell can read |
|------|--------------|-------------------------|
| passed | every proof of the rule, or the rule itself where it has no proof, has a test in a current section, and every test tied to it ran and passed, each current section answering for the proofs it lists | `passed`, `partial`, `failed`, `no test`, `not run`, `out of date` |
| strong | passed, and an AI audit of the current rule, proof and test found nothing, with the test strength at or above `min_strength` where mutation testing is on | `strong`, `weak`, `waiting`, `not audited`, `manual test`, `no proof` |
| signed | a counting signature for the current rule, proof, test, code, audit and machines | `signed`, `unsigned`, `waiting` |

A rule with neither a proof nor a marked test reads `no test` with the reason
`no proof written`. From `strong` up, a rule with a test and no proof reads `no proof`. A rule
with a `@manual` proof counts among those that pass their tests only once it is checked by
hand.

## Where each is defined

| Word | Where the authority lives |
|------|---------------------------|
| spec, rule, proof, scope | `references/formats/spec_format.md` |
| marker, suite, report | `references/formats/marker_format.md` |
| anchor, pinned anchor | `references/formats/anchor_format.md` |
| evidence, source, section, machine, fingerprint, test strength, the table | `references/formats/evidence_format.md` |
| signature, note, audit hash | `references/formats/signature_format.md` |
| evidence package | `references/formats/package_format.md` |
| the gate, the summary, `Left to do`, which evidence counts, when a signature counts, what `signed/<version>` means | `references/hard_gates.md` |
| drift, where its range starts, the three role views | `references/drift_criteria.md` |
| what the AI audit looks for | `references/review_criteria.md` |
| a good rule, a good proof | `references/spec_quality_guide.md` |
| every command's syntax and purpose sentence, and the exit codes | `references/purlin_commands.md` |
| every commit message shape | `references/commit_conventions.md` |
| how Purlin writes, and the words for each system | `references/writing_style.md` |
