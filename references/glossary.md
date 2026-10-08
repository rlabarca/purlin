# Glossary

The one list of the words this repository uses for its own concepts. A word here is the
spelling every doc, skill, agent definition and reference uses, with its one meaning. A row
defines the word; the file its last column names, under `references/`, says how the thing
behaves.

## Specs

| Word | Meaning | Detail |
|------|---------|--------|
| spec | One Markdown file, `specs/<category>/<name>.md`, with a `## Rules` section and a `## Proof` section | `formats/spec_format.md` |
| feature | What a spec describes, named by its file | `formats/spec_format.md` |
| name | A spec's file name without `.md`, in letters, digits, `_` and `-` | `formats/spec_format.md`, "Location" |
| scope | The optional `> Scope:` line: the files the feature's code lives in | `formats/spec_format.md`, "Metadata fields" |
| rule | One line in a spec saying what must be true, `RULE-<n>` | `spec_quality_guide.md`, "Writing rules" |
| proof | One line in a spec saying in plain language how a rule is shown to hold, `PROOF-<n> (RULE-<n>)` | `spec_quality_guide.md`, "Writing proofs" |
| `@manual` | The tag of a proof a person carries out by hand, with no test | `formats/spec_format.md`, "The manual tag" |
| `@env(<os>)` | The tag of a proof that can only be shown on `windows`, `macos` or `linux` | `formats/spec_format.md`, "Operating system tags" |
| slow proof | A proof tagged `@slow`, or an AI proof: `purlin:test` never starts its test and `purlin:test --all` does. An anchor's proof may be one | `formats/spec_format.md`, "The slow tag"; `purlin_commands.md` |
| AI proof | A proof tagged `@ai(<model>, ...)`, about what an AI does with a prompt or a skill. It is a slow proof, and it passes on a model when every model run passed | `formats/spec_format.md`, "The AI tags"; `spec_quality_guide.md`, "A proof about what an AI does" |
| model | An AI model, by the name a proof's tag gives it, such as `claude-opus-5-5`. A proof names its own; no setting names one | `formats/spec_format.md`, "The AI tags" |
| model run | One start of an AI proof's test on one model. It is not a run | `formats/spec_format.md`, "The AI tags" |
| output | What the AI produced in one model run, kept as one folder | `purlin_commands.md`, "The helper" |
| helper | `scripts/ai/purlin_ai.py`, the program an AI proof's test starts to make an output, to hand one over, or to have one graded | `purlin_commands.md`, "The helper" |
| graded | Said of an AI proof with `@graded(<grader>)` beside its `@ai`. Also the word such a proof reads where it passes, and its rule's passed cell in place of `passed`; it counts as passing | `formats/spec_format.md`, "The AI tags" |
| grader | The second model, which judges an output by the proof's sentence alone | `purlin_commands.md`, "The helper" |
| anchor | A set of rules for the whole project, kept under `specs/_anchors/` or opening `# Anchor:` | `formats/anchor_format.md` |
| remote anchor | A local copy of an anchor another repository owns, pinned to the commit `> Pinned:` names | `formats/anchor_format.md`, "Part 2: consumer tracking fields" |
| anchor repo | A repository that holds anchors for one or more projects | `formats/anchor_format.md` |
| nothing to check | What an anchor's rule reads when its test finds nothing in this project to check and skips with a reason starting `nothing to check:`. The rule passes | `formats/anchor_format.md`, "Writing a rule that holds where there is nothing to check" |

## Tests, runs and evidence

| Word | Meaning | Detail |
|------|---------|--------|
| test | Any test in the project's own suite that carries a marker | `formats/marker_format.md` |
| marker, test comment | One comment above a test, `purlin: <feature> PROOF-<n>`, or `purlin: <feature> RULE-<n>` where the rule has no proof | `formats/marker_format.md`, "The marker" |
| test comment to correct | A marker that ties its test to no proof or rule, or names a proof reworded after the test last changed | `formats/marker_format.md`, "What is reported"; `evidence_and_signoff.md`, "What is left to do" |
| suite | One entry of the `tests` setting: the project's own test command, where its report lands, the report's format and the globs its test files live under | `formats/marker_format.md`, "The `tests` setting"; `supported_frameworks.md` |
| report | The file a suite's command writes its results to | `formats/marker_format.md`, "The four report formats" |
| settings | `.purlin/config.json`, which holds `version`, `tests` and `runs`, and nothing else | `drift_criteria.md`, "Config field ownership" |
| system | An operating system: stored as `windows`, `macos` or `linux`, read by a person as `Windows`, `macOS` or `Linux/Unix` | `writing_style.md`; `formats/evidence_format.md` |
| platform | One system a current section covered | `formats/evidence_format.md`, "A platform section" |
| run | One execution of the project's suites by `purlin:test` or `purlin:audit` | `purlin_commands.md` |
| hand-off | What a developer does before a sign-off: `purlin:test --all --commit`, and the project's own run for the proofs tagged for another system | `evidence_and_signoff.md`, "A run on another system" |
| evidence | What runs saw, one file per feature per source, `.purlin/evidence/<source>/<feature>.json` | `formats/evidence_format.md` |
| source | The folder an evidence file sits in: `local`, a person's own run, or `ci`, a project's own run on another system. Both count | `formats/evidence_format.md`, "The two folders" |
| section | The part of an evidence file that holds one system's results | `formats/evidence_format.md`, "A platform section" |
| machine | The host's name a section records for the run that wrote it | `formats/evidence_format.md`, "A platform section" |
| fingerprint | A hash over the spec, the covered code and the tests, taken when a run writes a section | `formats/evidence_format.md`, "The fingerprint" |
| current | Said of a section whose fingerprint matches the tree now | `formats/evidence_format.md`, "The fingerprint" |
| carried | Said of a result an earlier run took and a later run recorded again on its own commit. It counts like any other | `formats/evidence_format.md`, "Carried forward" |
| this version of the code | The code at a commit, whatever Purlin's own records under `.purlin/` say after it | `evidence_and_signoff.md`, "Which evidence counts" |

## Status

| Word | Meaning | Detail |
|------|---------|--------|
| the two facts | What every surface shows first: the tests and the sign-off | `evidence_and_signoff.md`, "The two facts" |
| the tests | `met` when every rule passes its tests on the committed evidence, else `not met` | `evidence_and_signoff.md`, "The two facts" |
| the sign-off, as a fact | `signed <version> at <sha7>`, `signed <version>, <n> commits since` or `not signed` | `evidence_and_signoff.md`, "The two facts" |
| cell | One of the two answers every rule carries: one word, with its reasons | "The chain", below |
| passed | The cell that says whether every test tied to the rule ran and passed | "The chain", below |
| strong | The cell that says what the audit found. Also its word where the spot tests found nothing and a planted bug was caught by its proof's test | `review_criteria.md`, "The verdict" |
| spot-checked | The strong cell's word where the spot tests found nothing and no bug was planted and caught | `review_criteria.md`, "The verdict" |
| weak | The strong cell's word for a rule with a finding. It stops nothing | `review_criteria.md`, "The verdict" |
| waiting | The strong cell's word while the passed cell is not met, with the reason `waiting for its tests to pass`. It is not `weak` | `evidence_and_signoff.md`, "The two facts" |
| partial | The passed cell's word when a rule's tests passed on one system and failed on another. It is not met | `evidence_and_signoff.md`, "What is left to do" |
| out of date | The passed cell's word when the newest section is not current, and the strong cell's when the rule, its proof, its test or its code changed since the audit read it | `formats/evidence_format.md`, "The fingerprint"; `spec_quality_guide.md`, "When a rule is stuck" |
| summary | The sentence every run, every audit and `purlin:status` end on, such as `40 rules. 35 pass their tests.` | `evidence_and_signoff.md`, "What is left to do" |
| Left to do | The list under the summary: one line per kind of remaining work, with its count and the command that does it. The first line is the next step | `evidence_and_signoff.md`, "What is left to do" |
| to repair | The kind of `Left to do` for a spec Purlin cannot count as written, `<n> specs to repair: purlin:spec` | `formats/spec_format.md`, "Rules format" and "The AI tags" |
| information | A line the status and the dashboard print that asks for nothing to be fixed | `writing_style.md`, "A warning's shape" |

## Audit

| Word | Meaning | Detail |
|------|---------|--------|
| audit | `purlin:audit`, run by hand: it runs the tests, then says for each rule that passes how much its tests are worth | `review_criteria.md` |
| heuristic spot test | One of seven checks that read a test as text, with no model, and flag a test that cannot fail | `review_criteria.md`, "Heuristic spot tests" |
| planted bug | The one small change that breaks the case a proof names, written by an AI and made in a copy of the project to see whether the proof's own test catches it | `review_criteria.md`, "The planted bug" |
| finding | One line saying what a spot test flagged or which planted bug a test did not catch. It makes the rule `weak` | `review_criteria.md`, "What the audit reports" |
| settle | To decide a surviving bug's finding with a test run, `purlin:audit <feature> RULE-N --settle` | `review_criteria.md`, "Settling a finding" |
| explanation | The model's reading of the rule's tests. It decides nothing | `review_criteria.md`, "What the model is sent, and what it decides" |

## Sign-off

| Word | Meaning | Detail |
|------|---------|--------|
| hand check | A proof marked `@manual`, which no test runs: a person looks at it in the sign-off walk | `formats/spec_format.md`, "The manual tag"; `evidence_and_signoff.md`, "When a sign-off counts" |
| sign-off walk | The steps of `purlin:sign` that show a person the package and stop at each hand check | `evidence_and_signoff.md`, "When a sign-off counts" |
| note | What a person types at a hand check, kept in the sign-off | `formats/signature_format.md`, "Fields" |
| version | The name of what is signed, read from the project or given as `purlin:sign --version <version>` | `evidence_and_signoff.md`, "When a sign-off counts" |
| evidence package | One data file describing one version of the code, `.purlin/evidence/package/<version>.json`, which `purlin:sign` builds from the committed evidence | `formats/package_format.md` |
| sign-off | One person's signature over an evidence package: a file in a signed commit | `formats/signature_format.md`; `evidence_and_signoff.md`, "When a sign-off counts" |
| tag | `signed/<version>`, written as a signed tag by the first sign-off of a version. It never moves, and a person pushes it | `evidence_and_signoff.md`, "What `signed/<version>` means" |

## People and places

| Word | Meaning | Detail |
|------|---------|--------|
| role | Product, developer or QA, the three words for who does the work. Purlin gives no role a permission: any role may edit a spec, and any may sign | this row |
| checkout | One working copy of a repository. Each has its own results, status and dashboard; nothing is shared until the work is merged | this row |
| worktree | A checkout git adds beside the first. It is a checkout like any other | this row |
| git host | Where a project's repository is kept, such as GitHub or Azure DevOps. Purlin calls none | `evidence_and_signoff.md`, "A run on another system" |
| drift | `purlin:drift`: the facts your last pull, merge, rebase, checkout, clone or reset brought in, in one view | `drift_criteria.md` |

## The chain

For one rule, top to bottom. Each row is a cell, and every rule has both.

| Cell | Met when | Words the cell can read |
|------|----------|-------------------------|
| passed | every proof of the rule, or the rule itself where it has no proof, has a test in a current section, and every test tied to it ran and passed, each current section answering for the proofs it lists | `passed`, `graded`, `partial`, `failed`, `no test`, `not run`, `out of date`, `checked at sign-off` |
| strong | passed, the spot tests found nothing and a planted bug was caught; nothing waits on it | `strong`, `weak`, `spot-checked`, `out of date`, `waiting`, `not audited`, `checked at sign-off`, `no proof` |

- A rule with neither a proof nor a marked test reads `no test`, with the reason
  `no proof written`. A rule whose test passes with no proof reads `no proof` in its strong cell.
- A rule whose every proof is `@manual` reads `checked at sign-off` in both cells until a
  sign-off that counts notes it, and `passed` and `checked at sign-off` once one has.
- `graded` is `passed` with one of the rule's proofs graded by an AI: every count of the rules
  that pass takes it in.
- A rule whose AI proof passed on one model and has no result on another reads `not run`, and
  one that failed on any model reads `failed`.

`spec_quality_guide.md`, "When a rule is stuck", says what moves each word.
