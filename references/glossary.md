# Glossary

The one list of the words this repository uses for its own concepts. A word here is the
spelling every doc, skill, agent definition and reference uses, with its one definition; every
other page points here rather than defining it again.

## The words

- **spec**: one Markdown file under `specs/<category>/<name>.md`, with a `## Rules` section and
  a `## Proof` section. **feature**: what a spec describes, named by its file. **scope**: the
  `> Scope:` line, the files the feature's code lives in. It is optional; a spec without one
  runs on every `purlin:test`.
- **rule**: one line in a spec saying what must be true, `RULE-<n>`.
- **proof**: one line in a spec saying in plain language how a rule is shown to hold,
  `PROOF-<n> (RULE-<n>)`. QA writes and reviews proofs, and AI may draft them against the
  guideline in `references/spec_quality_guide.md`. Proofs are optional at the gate `passed`; at
  `signed` a rule without one is left to do as `to write a proof for`. **`@manual`**: a proof a
  person carries out by hand, with no test.
  **`@env(<os>)`**: a proof that can only be shown on `windows`, `macos` or `linux`.
- **system**: an operating system. A spec, the evidence and the package store it as `windows`,
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
- **gate**: the one project setting, passed or signed. passed: every rule's tests pass on the
  evidence committed at the release commit. signed: the same, and at least one person signs the
  evidence package.
- **cell**: one of the two answers every rule carries at both gates. The **passed** cell says
  whether every test tied to the rule ran and passed; a release waits on it. The **strong** cell
  says what the audit found; nothing waits on it. A cell reads one word and carries its reasons.
  The words each cell can read are in the chain below.
- **summary**: the sentence every run, every audit and `purlin:status` end on:
  `40 rules. 35 pass their tests.`, and, where the audit has read a rule that passes,
  `40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.` A rule is counted once,
  under the spec that owns it.
- **Left to do**: the list under the summary, one line per kind of remaining work, in the order
  the work is done, each with its count and the command that does it; a kind at zero is left
  out. It lists only work. The first line is the next step. The kinds, as printed:
  `to repair`, `to write a proof for`, `to correct`, `to fix`, `to write a test for`, `to test`,
  `to test on <systems>` and `to strengthen`. `references/hard_gates.md` says when each applies
  and which stop a release. **finished**: a version with nothing left to do.
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
  makes the rule `weak`, and a weak rule is left to do as `to strengthen`; it never stops a
  release. A proof longer than the standard, or holding two cases, is written among the audit's
  notes and does not make the rule weak. **strong**: what the AI audit found a rule's tests to
  be. A tool: nothing waits on it. **waiting**: the word the strong cell reads while the passed
  cell is not met, `waiting for its tests to pass`, and the neutral one on every surface. It is
  not `weak`.
- **mutation testing**, **the breaks**: deliberate changes to the code, to see whether the tests
  catch them. Optional and off by default at either gate, set by `mutation_engine`; setup asks
  about it at the gate `signed` alone. **test strength**: the share of one feature's breaks the
  tests caught, as a percentage, shown on each rule of the feature as `strength 84%`.
  `references/hard_gates.md`, under "The two gates", says how it reaches a rule.
- **hand check**: a proof marked @manual, which no test runs; at the gate signed a person checks
  it in the sign-off walk and types what they saw. What they type is a **note**, kept in the
  sign-off. At the gate `passed` the package lists the rule as not checked.
- **version**: the name of what is released, read from the `VERSION` file at the project root,
  then from the version the project's package description states; `--release <version>` names
  it instead.
- **release**: a commit, its evidence package and a tag, made by purlin:test --release on a
  release branch.
- **release branch**: the branch a version is released on, cut from the default branch once
  that version's specs are done.
- **tag**: `passed/<version>`, written unsigned by `purlin:test --release` at the gate `passed`,
  or `signed/<version>`, written as a signed tag by the first sign-off at the gate `signed`. It
  never moves. `references/hard_gates.md`, "What the tags mean", gives both at length. A person
  pushes it.
- **to repair**: the kind of `Left to do` for a spec that writes a rule or proof number twice or
  holds a line left from a merge conflict, `<n> specs to repair: purlin:spec`. Every rule of such
  a spec reads `failed` with the reason, and a release is refused until it is fixed.
- **evidence package**: one data file describing one release,
  `.purlin/evidence/package/<version>.json`: every rule's words, proofs, tests, results and what
  the audit found, the hand checks, the counts, what is left, the state `finished` or
  `not finished`, and a fingerprint of its own bytes. `purlin:test --release` commits it at the
  release commit, and it is never rewritten after; `purlin:export` writes it at any time. It is
  what a person hands to a regulated document and sign-off system.
- **sign-off**: one person's signature over a release's evidence package, a file in a signed
  commit; the first writes signed/<version>, and later ones are added beside it. The file,
  `.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, records the package's
  fingerprint, the signer's name and email as git holds them, the time, the key's fingerprint,
  what the **sign-off walk** of `purlin:sign` showed, and every note. It records no judgment.
  It counts when its commit's signature verifies, made with any key, and its package hash is
  the committed package's.
- **git host**: GitHub or Azure DevOps. With neither, the settings say `ci: none`, and
  everything on a person's own machine still works. **remote runner**: the git host's CI
  running the same run script a person runs. A project has one for one reason: a proof tagged
  `@env` for a system this machine is not. What it runs is in `references/hard_gates.md`,
  "Where a runner runs". **remote
  run**: `purlin:test --remote`, which pushes a **run branch**, `run/<branch>-<sha7>`, waits
  for the runner and pulls its evidence back. **runner file**: the file setup writes for the
  git host, `.github/workflows/purlin.yml` or `purlin.azure-pipelines.yml`, with one job for each
  system a proof is tagged `@env` for that the machine running setup is not. **tag run**: the
  run a pushed `signed/*` tag starts, which runs the tests and nothing else.
- **drift**: `purlin:drift`, the facts your last pull, merge, rebase, checkout, clone or reset
  brought in, in one view per role: `pm`, `eng` or `qa`.
- **role**: product, developer or QA. There are no others.
- **anchor**: a set of rules for the whole project, kept under `specs/_anchors/` or opening
  `# Anchor:`. Its tests check the whole project, and each of its rules is counted and audited
  once, and signed as part of the release. No spec names an anchor. **pinned anchor**: a local
  copy of an anchor from another repository, tied to a commit by `> Pinned:`. **anchor repo**: a
  repository that holds anchors for one or more projects.

## The chain

For one rule, top to bottom. Each row is a cell, and every rule has both at both gates.

| Cell | Met when | Words the cell can read |
|------|----------|-------------------------|
| passed | every proof of the rule, or the rule itself where it has no proof, has a test in a current section, and every test tied to it ran and passed, each current section answering for the proofs it lists | `passed`, `partial`, `failed`, `no test`, `not run`, `out of date` |
| strong | passed, and the AI audit of the current rule, proof and test found nothing; nothing waits on it | `strong`, `weak`, `waiting`, `not audited`, `manual test`, `no proof` |

A rule with neither a proof nor a marked test reads `no test` with the reason
`no proof written`. A rule with a test and no proof reads `no proof` in its strong cell. A
`@manual` proof is read out of the passed cell, so a rule whose every proof is `@manual` reads
`passed` and `manual test`.

## Where each is defined

| Word | Where the authority lives |
|------|---------------------------|
| spec, rule, proof, scope | `references/formats/spec_format.md` |
| marker, suite, report | `references/formats/marker_format.md` |
| anchor, pinned anchor | `references/formats/anchor_format.md` |
| evidence, source, section, machine, fingerprint, test strength, the table | `references/formats/evidence_format.md` |
| sign-off, note | `references/formats/signature_format.md` |
| evidence package | `references/formats/package_format.md` |
| the gate, the summary, `Left to do`, the release, which evidence counts, when a sign-off counts, what the tags mean | `references/hard_gates.md` |
| drift, where its range starts, the three role views | `references/drift_criteria.md` |
| what the AI audit looks for | `references/review_criteria.md` |
| a good rule, a good proof | `references/spec_quality_guide.md` |
| every command's syntax and purpose sentence, and the exit codes | `references/purlin_commands.md` |
| every commit message shape | `references/commit_conventions.md` |
| how Purlin writes, and the words for each system | `references/writing_style.md` |
