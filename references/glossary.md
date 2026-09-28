# Glossary

The one list of the words this repository uses for its own concepts. A word here is the
spelling every doc, skill, agent definition and reference uses, with its one definition; every
other page points here rather than defining it again.

## The words

- **spec**: one Markdown file under `specs/<category>/<name>.md`, with a `## Rules` section and
  a `## Proof` section. **feature**: what a spec describes, named by its file. **scope**: the
  `> Scope:` line, the files the feature's code lives in. It is optional below the gate
  `signed` and required at `signed`, where a rule of a spec that names no files cannot be
  signed.
- **rule**: one line in a spec saying what must be true, `RULE-<n>`.
- **proof**: one line in a spec saying in plain language how a rule is shown to hold,
  `PROOF-<n> (RULE-<n>)`. QA writes and reviews proofs, and AI may draft them against the
  guideline in `references/spec_quality_guide.md`. Proofs are optional at the gate `passed` and
  required from `strong` up. **`@manual`**: a proof a person carries out by hand, with no test.
  **`@env(<os>)`**: a proof that can only be shown on `windows`, `macos` or `linux`.
- **test**: any test in the project's own suite that carries a marker. **marker**: one comment
  above a test, in the language's own comment syntax, `purlin: <feature> PROOF-<n>`, or
  `purlin: <feature> RULE-<n>` where the rule has no proof. A test with no marker runs as it
  always did and Purlin ignores it.
- **suite**: one entry of the `tests` setting: the project's own test command, where its
  **report** lands, the report's format and the globs its test files live under.
- **level**: how far one rule must go, in the gate's own words. `passed`: its tests pass.
  `strong`: its tests pass and the audit found them sound. `signed`: both, and a person signed.
  A rule is marked with `[level: passed]`, `[level: strong]` or `[level: signed]` at the end of
  its line; an unmarked rule takes the gate.
- **gate**: the one project setting, `passed`, `strong` or `signed`: how far the project asks
  every rule to go. It is the ceiling, so a mark above it is read as the gate. A rule **meets
  the gate** when every cell up to its level is met.
- **cell**: the answer to one level for one rule. It reads one word and carries its reasons,
  and exists only at or below the gate. The words each cell can read are in the chain below.
- **run**: one execution of the project's suites by `purlin:test` or `purlin:audit`.
- **evidence**: what runs saw, one file per feature per source,
  `.purlin/evidence/<source>/<feature>.json`, with one **section** per operating system and,
  once the audit has read the feature, what the audit found. A run writes it; `--commit`
  commits it as `purlin: evidence at <sha7>`. **source**: the folder the file sits in, `local`
  (a person's own run) or `ci` (a remote runner's). Both count at every gate. **the table**:
  `.purlin/tests.md`, one row per feature, written with the evidence.
- **platform**: one operating system a counting run covered. **partial**: the passed cell's
  word when a rule's tests passed on some platforms and failed or did not run on others. It is
  not met.
- **fingerprint**: a hash over the spec, the covered code and the tests, taken when a run
  writes a section. **current**: a section whose fingerprint matches the tree now. **out of
  date**: the passed cell's word when the newest section is not current, naming what changed,
  `code changed since <sha7>`, `spec changed since ...` or `tests changed since ...`. The next
  run clears it. `purlin:test` with no feature named runs the features that are out of date or
  have no run on this operating system.
- **audit**: `purlin:audit`: the tests, the breaks where mutation testing is on, then the AI
  audit, written into each feature's evidence. **AI audit**: one model call per rule, reading
  the rule, its proofs and its tests against `references/review_criteria.md`. Each answer names
  the model that gave it. **finding**: one sentence the AI audit wrote about a gap. A finding
  makes the rule `weak`, and from the gate `strong` up a weak rule does not meet the gate.
- **mutation testing**, **the breaks**: deliberate changes to the code, to see whether the tests
  catch them. Optional, off by default, set by `mutation_engine`. **test strength**: the share
  of the breaks the tests caught, as a percentage, compared with `min_strength`.
- **queue**: the one list of the rules that wait on a person, at the gate `strong` and above.
  `purlin:sign` walks it and the dashboard's Queue tab shows it. Each row **needs** one of two
  things: a **hand check**, a rule whose proofs are `@manual`, which a person signs with a
  **note** saying what they saw; or a **signature**, a rule whose level is `signed` whose tests
  and audit are met.
- **signature**: a person's attestation that a rule, its proof, its test and what the audit
  found belong together: one file under `specs/<category>/<feature>.signatures/`, committed in
  a signed commit by `purlin:sign`. It records the signer, the time, the machine and its
  operating system, the rule's level, and the hashes it binds, including an **audit hash** over
  what the audit found. **counting signature**: at the gate `signed`, one whose commit is signed
  and verifies and whose hashes still match; below `signed`, any committed one. **stale**: the
  signed cell's word when the hashes no longer match.
- **tag**: `signed/<version>`, the signed tag `purlin:sign` writes on the commit that carries
  the evidence package, once every rule meets the gate and every feature's evidence is committed
  and current. It means that at the tagged commit every rule meets the gate;
  `references/hard_gates.md` gives it at length. A person pushes it.
- **evidence package**: one data file describing one version,
  `.purlin/evidence/package/<version>.json`: every rule's words, proofs, tests, results, what
  the audit found and who signed, with its state and a fingerprint of its own bytes.
  `purlin:export` writes it, and `purlin:sign` commits it just before the tag. It is what a
  person hands to a regulated document and sign-off system.
- **trust**: the setting `trust`, `local` or `remote`, from init's question `Do you trust your
  own machine for the tests and the signing? [y/n]`. Under `remote`, `purlin:sign` refuses a
  rule whose tests have no current `ci` section.
- **git host**: GitHub or Azure DevOps. **remote runner**: the git host's CI running the same
  run script a person runs. A project has one for two reasons and no others: a proof tagged
  `@env` for an operating system this machine is not, or `trust: remote`. **remote run**:
  `purlin:test --remote`, which pushes a **run branch**, `run/<branch>-<sha7>`, waits for the
  runner and pulls its evidence back. **tag run**: the run a pushed `signed/*` tag starts,
  which reruns the tests and ends with the gate check.
- **gate check**: `scripts/ci/gate_check.py`, which reads the committed evidence and
  signatures, lists every rule short of the gate, and exits 0 when the gate is met.
- **drift**: `purlin:drift`, the facts your last pull, merge, rebase, checkout, clone or reset
  brought in, in one view per role: `pm`, `eng` or `qa`.
- **role**: product, developer or QA. There are no others.
- **anchor**: a spec for something shared across features, under `specs/_anchors/`. **pinned
  anchor**: a local copy of an anchor from another repository, tied to a commit by
  `> Pinned:`. **anchor repo**: a repository that holds anchors for one or more projects.
- **bucket**: the one tile a rule is counted in: `untested`, `failing`, `partial`, `passed`,
  `strong` or `signed`. **rollup**: rules meeting the gate out of rules in total, with one count
  per bucket.

## The chain

For one rule, top to bottom. Each row is a cell; the gate decides how many rows exist.

| Level | Met when | Words the cell can read |
|-------|----------|-------------------------|
| passed | every proof of the rule, or the rule itself where it has no proof, has a passing test in a current section, on every platform a current section covers | `passed`, `partial`, `failed`, `no test`, `not run`, `out of date` |
| strong | passed, and where the level is `strong` or `signed` an AI audit of the current rule, proof and test that found nothing, with the test strength at or above `min_strength` where mutation testing is on | `strong`, `weak`, `not audited`, `manual test`, `no proof` |
| signed | a counting signature for the current rule, proof, test and audit | `signed`, `unsigned`, `stale` |

A rule with neither a proof nor a marked test reads `no test` with the reason
`no proof written`. From `strong` up, a rule with a test and no proof reads `no proof`.

## Where each is defined

| Word | Where the authority lives |
|------|---------------------------|
| spec, rule, proof, level, scope | `references/formats/spec_format.md` |
| marker, suite, report | `references/formats/marker_format.md` |
| anchor, pinned anchor | `references/formats/anchor_format.md` |
| evidence, source, section, fingerprint, test strength, the table | `references/formats/evidence_format.md` |
| signature, note, audit hash | `references/formats/signature_format.md` |
| evidence package | `references/formats/package_format.md` |
| the gate, which evidence counts, when a signature counts, what `signed/<version>` means | `references/hard_gates.md` |
| drift, where its range starts, the three role views | `references/drift_criteria.md` |
| what the AI audit looks for | `references/review_criteria.md` |
| a good rule, a good proof, choosing a level | `references/spec_quality_guide.md` |
| every command's syntax and purpose sentence | `references/purlin_commands.md` |
| every commit message shape | `references/commit_conventions.md` |
| how Purlin writes | `references/writing_style.md` |
