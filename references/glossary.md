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
  guideline in `references/spec_quality_guide.md`. A rule whose tests pass with no proof is left
  to do as `to write a proof for`. **`@manual`**: a proof a person carries out by hand, with no
  test.
  **`@env(<os>)`**: a proof that can only be shown on `windows`, `macos` or `linux`.
- **slow proof**: a proof tagged `@slow`, whose test takes a long time, like an integration
  test. It is a proof like any other, with one test and its comment; the tag changes only when
  the test starts. `purlin:test` never starts it and `purlin:test --all` does. Until it has
  passed on the spec, code and tests as they stand it reads `not run`, and it is left to do as
  `1 slow proof to run: purlin:test --all`. An anchor's proof may be one.
- **system**: an operating system. A spec, the evidence and the package store it as `windows`,
  `macos` or `linux`, and every system that is not Windows or macOS is `linux`. A person reads
  it as `Windows`, `macOS` or `Linux/Unix`, and in the dashboard's small boxes as `Win`, `Mac`
  or `Lin`.
- **test**: any test in the project's own suite that carries a marker. **marker**, also **test
  comment**: one comment above a test, in the language's own comment syntax,
  `purlin: <feature> PROOF-<n>`, or `purlin: <feature> RULE-<n>` where the rule has no proof. A
  test with no marker runs as it always did and Purlin ignores it.
- **suite**: one entry of the `tests` setting: the project's own test command, where its
  **report** lands, the report's format and the globs its test files live under. Setup leaves
  the setting empty; the first test run suggests an entry for each test tool it recognises, and
  they are written together once a person confirms them.
- **settings**: `.purlin/config.json`, which holds `version`, the Purlin version that set the
  project up, and `tests`, and nothing else.
- **the two facts**: what every surface shows first. **the tests**: `met` when every rule passes
  its tests on the committed evidence, else `not met`. **the sign-off**, as a fact:
  `signed <version> at <sha7>`, `signed <version>, <n> commits since` or `not signed`.
  `references/evidence_and_signoff.md` defines both.
- **cell**: one of the two answers every rule carries. The **passed** cell says whether every
  test tied to the rule ran and passed. The **strong** cell says what the audit found; nothing
  waits on it. A cell reads one word and carries its reasons. The words each cell can read are
  in the chain below.
- **summary**: the sentence every run, every audit and `purlin:status` end on:
  `40 rules. 35 pass their tests.`, and, where the audit has read a rule that passes,
  `40 rules. 35 pass their tests. The audit found 30 of 35 rules strong (85%).` A rule is counted
  once, under the spec that owns it.
- **Left to do**: the list under the summary, one line per kind of remaining work, in the order
  the work is done, each with its count and the command that does it; a kind at zero is left
  out. It lists only work. The first line is the next step. The kinds, as printed:
  `to repair`, `to write a proof for`, `to correct`, `to fix`, `to write a test for`, `to test`,
  `to test on <systems>`, `whose results are not committed` and `to strengthen`.
  `references/evidence_and_signoff.md` says when each applies and which stop the tests being met.
- **test comment to correct**: a marker naming nothing a spec has, or naming a proof whose
  wording changed after the test was last changed. It is left to do with `purlin:build`, and
  clears once the test itself changes.
- **information**: a line the status and the dashboard print that asks for nothing to be fixed,
  such as a spec whose scope names files not written yet.
- **run**: one execution of the project's suites by `purlin:test` or `purlin:audit`.
- **hand-off**: what a developer does before a sign-off: `purlin:test --all --commit`, and
  `purlin:test --remote` for the proofs tagged for another system.
- **evidence**: what runs saw, one file per feature per source,
  `.purlin/evidence/<source>/<feature>.json`, with one **section** per system and, once the
  audit has read the feature, what the audit found. Each section names the commit of the code it
  describes, who ran it and the **machine** it ran on: the host's name for a person's run,
  `remote runner, <system>` for a remote runner's. A run writes it; `--commit` commits it, after
  a commit of the specs, tests and settings it describes. **source**: the folder the file sits
  in, `local` (a person's own run) or `ci` (a remote runner's). Both count.
- **platform**: one system a current section covered. **partial**: the passed cell's word when
  a rule's tests passed on one system and failed on another. It is not met. A system that has
  not run reads `not run`.
- **fingerprint**: a hash over the spec, the covered code and the tests, taken when a run
  writes a section. **current**: a section whose fingerprint matches the tree now. **out of
  date**: the passed cell's word when the newest section is not current, naming what changed,
  `code changed since <sha7>`, `spec changed since ...` or `tests changed since ...`. The next
  run clears it. `purlin:test` with no feature named runs the features that are out of date or
  have no run on this system.
- **this version of the code**: the code at a commit, whatever Purlin's own records under
  `.purlin/` say after it. A result counts for a sign-off only when it was taken on it.
- **nothing to check**: what an anchor's rule reads when its test finds nothing in this project
  to check and skips with a reason starting `nothing to check:`. The rule passes, and the reason
  is shown.
- **audit**: `purlin:audit`, run by hand: the tests, then for each rule that passes the
  **heuristic spot tests**, one **planted bug** per proof, and the **model's reading**, written
  into each feature's evidence. It ends on the share of rules it found strong.
  `references/review_criteria.md` is its one home. **heuristic spot test**: one of six checks
  that read a test as text, with no model, and flag a test that cannot fail. **planted bug**:
  the smallest change to the code that would break one proof, made in a copy of the project to
  see whether the proof's own test catches it. **finding**: one line saying what a spot test
  flagged or which planted bug a test did not catch. A finding makes the rule `weak`, and a weak
  rule is left to do as `to strengthen`; it stops nothing. **explanation**: the model's reading
  of what was found; it decides nothing. **strong**: what the audit found a rule's tests to be.
  **waiting**: the word the strong cell reads while the passed cell is not met,
  `waiting for its tests to pass`. It is not `weak`.
- **hand check**: a proof marked `@manual`, which no test runs. It reads `checked at sign-off`:
  a person looks at it in the sign-off walk and may type what they saw. What they type is a
  **note**, kept in the sign-off; an empty answer is recorded as `no note`.
- **version**: the name of what is signed, read from the `VERSION` file at the project root,
  then from the version the project's package description states; `purlin:sign --version
  <version>` names it instead.
- **tag**: `signed/<version>`, written as a signed tag by the first sign-off of a version. It
  never moves. `references/evidence_and_signoff.md`, "What `signed/<version>` means", defines
  it. A person pushes it.
- **to repair**: the kind of `Left to do` for a spec that writes a rule or proof number twice or
  holds a line left from a merge conflict, `<n> specs to repair: purlin:spec`. Every rule of such
  a spec reads `failed` with the reason, and a sign-off is refused until it is fixed.
- **evidence package**: one data file describing one version of the code,
  `.purlin/evidence/package/<version>.json`: every rule's words, proofs, tests, results and what
  the audit found, who ran the tests, who wrote and last changed each rule, proof and test, the
  hand checks, the counts, what is left, and a fingerprint of its own bytes. `purlin:sign` builds
  it from the committed evidence and commits it with the first sign-off. It is what a person
  hands to a regulated document and sign-off system.
- **sign-off**: one person's signature over an evidence package, a file in a signed commit; the
  first writes `signed/<version>`, and later ones are added beside it. The file,
  `.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, records the package's
  fingerprint, the signer's name and email as git holds them, the time, the key's fingerprint,
  what the **sign-off walk** of `purlin:sign` showed, and every note. It records no judgment.
  It counts when its commit's signature verifies, made with any key, and its package hash is
  the committed package's.
- **git host**: GitHub or Azure DevOps, read from the remote each time. With neither, everything
  on a person's own machine still works. **remote runner**: the git host's CI running the same
  run script a person runs. A project has one for one reason: a proof tagged `@env` for a system
  this machine is not. What it runs is in `references/evidence_and_signoff.md`, "Where a runner
  runs". **remote run**: `purlin:test --remote`, which pushes a **run branch**,
  `run/<branch>-<sha7>`, waits for the runner and pulls its evidence back. **runner file**: the
  file the first remote run writes for the git host, `.github/workflows/purlin.yml` or
  `purlin.azure-pipelines.yml`, with one job for each system a proof is tagged `@env` for that
  this machine is not.
- **drift**: `purlin:drift`, the facts your last pull, merge, rebase, checkout, clone or reset
  brought in, in one view.
- **role**: product, developer or QA. There are no others.
- **checkout**: one working copy of a repository, a **worktree** included. Each has its own
  results, status and dashboard; nothing is shared until the work is merged.
- **anchor**: a set of rules for the whole project, kept under `specs/_anchors/` or opening
  `# Anchor:`. Its tests check the whole project, and each of its rules is counted and audited
  once. No spec names an anchor. **pinned anchor**: a local copy of an anchor from another
  repository, tied to a commit by `> Pinned:`. **anchor repo**: a repository that holds anchors
  for one or more projects.

## The chain

For one rule, top to bottom. Each row is a cell, and every rule has both.

| Cell | Met when | Words the cell can read |
|------|----------|-------------------------|
| passed | every proof of the rule, or the rule itself where it has no proof, has a test in a current section, and every test tied to it ran and passed, each current section answering for the proofs it lists | `passed`, `partial`, `failed`, `no test`, `not run`, `out of date` |
| strong | passed, and the audit of the current rule, proofs and tests found nothing; nothing waits on it | `strong`, `weak`, `waiting`, `not audited`, `checked at sign-off`, `no proof` |

A rule with neither a proof nor a marked test reads `no test` with the reason
`no proof written`. A rule with a test and no proof reads `no proof` in its strong cell. A
`@manual` proof is read out of the passed cell, so a rule whose every proof is `@manual` reads
`passed` and `checked at sign-off`.

## Where each is defined

| Word | Where the authority lives |
|------|---------------------------|
| spec, rule, proof, scope | `references/formats/spec_format.md` |
| marker, suite, report | `references/formats/marker_format.md` |
| anchor, pinned anchor | `references/formats/anchor_format.md` |
| evidence, source, section, machine, fingerprint | `references/formats/evidence_format.md` |
| sign-off, note | `references/formats/signature_format.md` |
| evidence package | `references/formats/package_format.md` |
| the two facts, the summary, `Left to do`, which evidence counts for a sign-off, when a sign-off counts, what `signed/<version>` means | `references/evidence_and_signoff.md` |
| drift, where its range starts, its one view | `references/drift_criteria.md` |
| the heuristic spot tests, the planted bug, what the model is sent | `references/review_criteria.md` |
| a good rule, a good proof | `references/spec_quality_guide.md` |
| every command's syntax and purpose sentence, and the exit codes | `references/purlin_commands.md` |
| every commit message shape | `references/commit_conventions.md` |
| how Purlin writes, and the words for each system | `references/writing_style.md` |
