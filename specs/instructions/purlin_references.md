# Feature: purlin_references

> Requires: schema_spec_format, schema_proof_format
> Scope: references/spec_quality_guide.md, references/hard_gates.md, references/commit_conventions.md, references/purlin_commands.md, references/drift_criteria.md, references/audit_criteria.md, references/supported_frameworks.md, references/remote_verification.md, references/formats/spec_format.md, references/formats/proofs_format.md, references/formats/anchor_format.md, references/formats/receipt_format.md, references/proof_plugin_contract.md, references/legacy_features_migration.md
> Stack: markdown (reference documentation)
> Description: Fourteen reference documents that define Purlin's formats, conventions, and quality standards. These are the authoritative source that skills and agents reference, ensuring structural consistency across the framework.

## Rules

- RULE-1: `spec_format.md` documents the 2 required sections (`## Rules`, `## Proof`), the `> Description:` metadata field, and the RULE-N/PROOF-N numbering convention
- RULE-2: `proofs_format.md` documents the proof JSON schema with all 7 required fields, the
  scoped-file eighth field `platform`, and the write-scoped overwrite merge behavior keyed by
  `(feature, tier, platform, test_file)`. The three-part `(feature, tier, test_file)` appears
  only where the file names it as the key the current one grew from, never as the key itself:
  a format file that still states the three-part key tells a plugin author to address an entry
  without its platform, which is a run on one platform clobbering another platform's file
- RULE-3: `proofs_format.md` documents the proof marker of every shipped framework: one `###`
  subsection per framework under `## Proof Markers by Framework`, and a `### Feature-name token`
  table in that same section whose rows name the framework id, the marker subsection that
  documents it, and the exact literal in which the feature name sits. The table's
  marker-section set equals the set of the section's other `###` headings, so a framework
  documented without a token row, or a token row naming a subsection that is not there, fails.
  That table is the one written record of what a rename has to rewrite: `skills/rename/SKILL.md`
  cites it rather than restating markers, and a framework absent from it is a framework whose
  markers a rename silently walks past
- RULE-4: `anchor_format.md` documents anchor file location (`specs/_anchors/`), metadata fields (`> Source:`, `> Pinned:`, `> Global:`), sync protocol, and global anchor behavior
- RULE-5: `anchor_format.md` documents all 8 type values: `design`, `api`, `security`, `brand`, `platform`, `schema`, `legal`, `prodbrief`
- RULE-6: `hard_gates.md` documents exactly 1 gate: proof coverage. A project's own CI gate is documented there as project policy layered on that one gate, in a section that is not a `## Gate N` heading, so the framework's count cannot be inflated by describing what a project configures for itself
- RULE-7: `commit_conventions.md` documents all 8 commit prefixes: spec, feat, fix, test, verify, anchor, chore, docs, and carries the `chore(update):` prefix row for a migration commit. Its `verify:` format is `verify: [Complete:all] features=N/T anchors=A/B vhash=<combined-hash>`: features and anchors are counted separately and never summed, because a run that receipted every anchor and half the features is not the same result as the reverse, and one merged fraction cannot say which happened. `skills/verify/SKILL.md` and `dev/issue_receipts.py` carry the same two counts, so the number in the commit message is copied from the issuer rather than recounted by hand
- RULE-8: `purlin_commands.md` lists all 12 skills grouped by category (Authoring, Building, Quality, Reporting, Project)
- RULE-9: `spec_quality_guide.md` includes guidance on writing rules (rebuild test, contract boundaries, coverage dimensions), proof descriptions, tier assignment, and FORBIDDEN patterns. Its coverage-dimension guidance carries a `### Data contract extraction` subsection holding the per-category procedure for the five contract boundaries, so `skills/spec-from-code/SKILL.md` names the five categories and points here instead of restating what to trace in each
- RULE-10: `spec_quality_guide.md` includes test failure diagnosis guidance with the three categories (code bug, test bug, spec drift) and assertion integrity rules
- RULE-11: `spec_quality_guide.md` includes audience-appropriate language guidance mapping artifacts to their intended readers
- RULE-12: `drift_criteria.md` documents file classification order, NO_IMPACT patterns, behavioral directory exclusions, significance mapping, structural-only drift indicators, and precomputed drift flags
- RULE-13: `spec_quality_guide.md` documents E2E proof descriptions as observable flows (arrange → act → observe through the real running app), forbids naming source files or internal functions in proof descriptions, and requires descriptions to stay tool-agnostic (executable by any e2e runner)
- RULE-14: `audit_criteria.md` defines E2E Proof Tier Integrity criteria — tier mismatch (an `@e2e` test that never drives the real UI) and source-constant assertion (asserting a config constant where the rule describes runtime behavior) — applying to ALL `@e2e` proofs, not just design anchors
- RULE-15: `supported_frameworks.md` documents end-to-end (browser) proofs: no dedicated e2e proof reporter ships, `@e2e` proofs are tool-agnostic, and proof emission wires through the existing plugins (Vitest/Jest markers or shell `purlin_proof` wrappers)
- RULE-16: `audit_criteria.md` defines both gauges — Proof Design (PROVABLE/LOOSE/UNPROVABLE/STRUCTURAL, graded from the proof description with no test code) and Proof Integrity (STRONG/WEAK/HOLLOW/EXCLUDED/MANUAL, graded from test code) — with a scoring formula for each, and marks the Integrity criteria that are comparisons against the proof description so a reader knows which ones a vague description disables. `spec_quality_guide.md` labels its proof-description sections with the Design level each defect is graded as
- RULE-17: `hard_gates.md` states that receipts are issued for features reported PASSING and explains that VERIFIED is the post-receipt state, so requiring it would deadlock the first receipt. Its "What Is NOT a Gate" list records that a low Proof Design or Proof Integrity score is advisory by default and never blocks unless the project declares `quality_gate`, and names that field as the opt-in that makes the deterministic half of the two gauges a CI failure while the LLM half stays advisory. The same list records the pending-migration refusal: while a `legacy-*` migration stands, `purlin:verify` issues no receipt for any feature, because the legacy alias makes coverage a guess, and the list says that this blocks nothing and that clearing the migration restores receipts. `skills/verify/SKILL.md` cites the list rather than saying `hard_gates.md` gains no entry, which is what it said while the behaviour went unrecorded anywhere a reader counting gates would look. A reader counting gates has to find both the opt-in and the refusal in the same list that tells them the gauges do not block, or the first project that meets either reads it as a second framework gate
- RULE-18: `remote_verification.md` documents the remote-execution loop for platform-declared proofs: that it lives in `purlin:test` because `purlin:verify` is read-only, the four ordered operations, the 3-round bound, and a GitHub Actions workflow template parameterized by `<platform-id>` and `<runs-on>`. The template block itself carries every element a copy of it needs to work: the `name: purlin-<platform-id>-proofs` workflow name; a `paths-ignore` entry matching `**/*.proofs-*@<platform-id>.json` and a `workflow_dispatch` trigger; `permissions: contents: write`; a job `env` setting `PURLIN_PLATFORM: <platform-id>`; a checkout with `persist-credentials: true`; a "Locate Purlin tooling" step publishing `PURLIN_PLUGIN_ROOT=$RUNNER_TEMP/purlin` into `$GITHUB_ENV` rather than setting it in the job `env`; an "Install Purlin tooling" step cloning this repository at a pinned `v<VERSION>` tag into `$PURLIN_PLUGIN_ROOT`; a "Preflight" step running `migrate.py --check` from `$PURLIN_PLUGIN_ROOT`; a per-framework setup block; the test command; `shell: bash` on every `run:` step; a `git add` narrowed to `**/*.proofs-*@<platform-id>.json`; a `git diff --cached --quiet` guard; a commit carrying `[skip ci]`, a `Purlin-Runner:` trailer and a `Purlin-Platform:` trailer; and a pull-rebase-retry loop of three attempts that exits 1 after them. A template copied without any one of these produces an infinite trigger loop, a proof whose runner or platform is unrecorded, a runner's agnostic results overwriting the developer's, a mangled path under PowerShell, or a job that goes red because two platform runners raced for one branch
- RULE-19: `remote_verification.md` states the declaration/enforcement split for the `remote_verification` config field: the field declares the mode, and branch protection marking the gate job a required check is the enforcement. It gives the reason rather than only the rule, citing that the field is in the tree where the agent can edit it. It also records that neither quality gauge travels with a branch, because both caches are gitignored, and recommends recomputing Design in CI (deterministic and free) while recomputing Integrity only where `audit_llm` is configured
- RULE-20: `drift_criteria.md`'s Config Field Ownership table names every field `templates/config.json` carries and every one of the six optional fields the docs name that a full init never writes (`audit_llm`, `audit_llm_name`, `audit_criteria`, `audit_criteria_pinned`, `platforms`, `quality_gate`). A field stamped into new projects, or read by a skill, with no row here has no recorded owner and no recorded default, which is how `digest` went unlisted. A row for a field the template no longer carries is the same defect from the other side, a documented owner for a setting nothing reads, so a retired key (`skill_init` RULE-76) leaves the table in the commit that retires it
- RULE-21: `receipt_format.md` is the verification receipt contract: it carries its own `> Format-Version:` line, documents every version 2 field (`feature`, `vhash`, `vhash_version`, `commit`, `timestamp`, `rules`, `rule_hashes`, `proofs`, `manual`, `evidence` with `test_run` and `proof_files`, and `awaiting_runner`) with the `proof_files` row keys (`file`, `tier`, `platform`, `commit`, `committed_at`, `runner`, `executed_in_test_run`), states what the vhash binds and what it does not, documents the version 1 shape as historical, and states that `evidence.test_run` is null for a receipt issued without a run marker. Its `evidence.test_run` paragraph also names who writes the run marker: the proof plugins in a consumer project and `dev/run_tests.sh` here, with the `sweep`, `runs` and `skipped_proofs` keys documented, `skipped_proofs` described as one `{feature, id, test_file, test_name, reason}` object per marked test the run skipped and as the mark of an entry kept from an earlier commit rather than re-proved. A consumer reading only the older paragraph concludes that a project without a sweep script can never record a run, and reaches for `--no-run-check`: a null `test_run` is the difference between a receipt that observed a run and one that only read files
- RULE-22: Every CI workflow template under `references/` and `docs/` that invokes a Purlin `scripts/` path invokes it through `$PURLIN_PLUGIN_ROOT` and installs that root by cloning the plugin at a pinned `v<VERSION>` tag. A consumer project's checkout holds specs, proofs, receipts and `.purlin/`, and no Purlin `scripts/`, so a template with a bare `scripts/` path is one that cannot run anywhere but in this repository; an unpinned clone changes what the template enforces between one run and the next. This repository's own workflows are the stated exception: they set `PURLIN_PLUGIN_ROOT` to `.` and skip the install step, because this repository is the plugin
- RULE-23: `supported_frameworks.md` carries a non-empty **Runner setup** cell and a non-empty **Installed as** cell for every framework it lists, in both the built-in and the additional-plugin tables, and names each column as what reads it: `purlin:test` when it scaffolds a runner workflow, and `purlin:init` and `purlin:init --update` when they write and refresh a project's plugin copies. A listed framework with no recorded setup is one a scaffolded workflow installs nothing for and cannot run; one with no recorded installed name is one whose copy neither script can name, and the **Installed as** cell holds one backticked basename per `scripts/proof/` file in the same row's **Plugin file** cell, in the same order, so a framework shipping two files records two names

- RULE-24: `purlin_commands.md` carries a `## Pending migrations` section, so every skill can point at one anchor (`purlin_commands.md#pending-migrations`) instead of restating the advisory. It states what a skill does when `sync_status` opens with the advisory (stop, print it and its directive, ask whether to run `purlin:init --update` now), that skills which do not call `sync_status` call it first when they would write specs or proofs, and that `purlin:verify` declines to issue receipts while a `legacy-*` migration is pending because the legacy alias makes coverage a guess, framed as a refusal to claim and not as a gate
- RULE-25: `spec_quality_guide.md` carries a `## Mutation check` section: what a mutation check is, the three steps (break the behaviour, run that proof and watch it fail, restore and re-run), when it runs (every new or amended proof, before the commit that carries it), what a surviving mutation means (the fixture cannot tell correct from broken, so the proof is weak and needs the discriminating case), two worked examples, and the value statement `purlin:init` prints before its question. The value statement lives here once and is quoted by reference from the skill, per CLAUDE.md's deduplication rule
- RULE-26: `hard_gates.md` states that no Claude Code hook gates anything: every hook
  `hooks/hooks.json` registers is a post-event hook (`PostToolUse`, `SubagentStop`, `Stop`),
  runs `async`, exits 0 on every path and blocks nothing, so every **NEVER** in
  `agents/purlin.md` is an instruction to the agent rather than a mechanism that stops it,
  and names the enforcement layers that survive an agent ignoring one: the proof-coverage
  gate in the issuer, the pre-push hook, the CI gate job, and branch protection. The one
  registered hook refreshes `.purlin/report-data.js` (`refresh_digest_hook`), which is
  reporting, not enforcement.
- RULE-27: Nothing under `.purlin/cache/` is tracked by git. The gauges are per machine by design
  and `.gitignore` already excludes the directory, so a tracked cache file is a stale number that
  travels: it arrives in every clone, is read before anything recomputes it, and reports a
  measurement taken on somebody else's machine at some earlier commit
- RULE-28: `remote_verification.md` carries a `## Platforms, environments and prerequisites`
  section, and that section is the single home of the three-category rule set. It names all three
  categories in bold (`**Platform**`, `**Environment**`, `**Prerequisite**`); it states each
  category's membership question in bold, `Would the same test passing on a different OS be
  evidence for this claim?` for a platform, `Does the outcome depend on an external system's real
  answers, an account, a model, or money, so that installing a package cannot reproduce it?` for
  an environment, and `Would any host with the tool installed produce the same evidence?` for a
  prerequisite; it carries the sentence that a `runner.provider` (`github`, `ado`) is transport to
  reach a platform and is never itself a platform, so no proof depends on GitHub; and it
  classifies the ids in use, `windows-2022` as a platform and `figma-mcp`, `gemini-cli` and
  `claude-cli` as environments, against php, dotnet, node, gcc, tsc and sqlite3 as prerequisites.
  None of the three questions appears in any other tracked markdown file under `docs/`,
  `references/` or `skills/`: a second copy is a second answer the day one of them is edited, and
  the repository already reached the state where one situation, a test needing something this host
  lacks, was handled three different ways. Other files link this section rather than restating it
- RULE-29: No CI workflow template or example in any fenced yaml block under `references/` or
  `docs/` reads the `runner` context inside a `jobs.<id>.env` block. GitHub evaluates job-level
  `env` before a runner is assigned and admits only the `github`, `needs`, `strategy`, `matrix`,
  `vars`, `secrets` and `inputs` contexts there, so a job env carrying `${{ runner.temp }}` is a
  workflow file error: the whole run is refused at startup with "This run likely failed because of
  a workflow file issue", no job is created and no log exists to diagnose it. A per-runner path
  belongs in a step, published through `$GITHUB_ENV` from the runner's own `$RUNNER_TEMP`, which
  is the same directory reached as an ordinary environment variable

- RULE-30: `proof_plugin_contract.md` is the one checklist a proof plugin is written and audited
  against, and its wiring list names every file a new framework has to be wired into: the plugin
  file under `scripts/proof/`, the framework registry `supported_frameworks.md`, the scaffolder's
  detectors and runner wiring in `scripts/init/scaffold.py`, the pre-push gate's known ids in
  `scripts/hooks/pre_push_gate.py` and its runner arm in `scripts/hooks/pre-push.sh`, the init and
  test skills, the marker sections of `docs/testing-workflow-guide.md` and
  `references/formats/proofs_format.md`, the Pass 1 subsection of `audit_criteria.md` and the
  checker dispatch in `scripts/audit/static_checks.py`, the per-plugin spec under `specs/proof/`,
  the plugin test file, `dev/run_tests.sh`, and the five specs that pin those sites. Every path
  the list names exists. A site the list omits is one a new language is wired into from memory or
  not at all, which is how a framework ships selectable in one file and unknown to the hook that
  runs it; a path the list names that does not exist is a checklist that outlived the tree it
  describes and sends the next author to a file that moved
- RULE-32: `proofs_format.md` carries a `## Run marker` section for `.purlin/runtime/test_run.json`:
  the nine top-level fields `proof_common` RULE-19 names (`at`, `commit`, `sweep`, `test_files`,
  `passed`, `failed`, `skipped`, `ok`, `runs`), the RULE-20 `skipped_proofs` key with the shape of
  one object, the merge rule (a run at the same commit merges into the existing marker, any other
  commit starts a new one), and the temp-file-plus-single-replace write. The marker is part of
  what a plugin writes, so a format file that documents only the proof files describes half the
  contract, and a consumer who implements only that half issues receipts whose `evidence.test_run`
  is null forever

- RULE-33: Every framework the per-framework table of `proof_plugin_contract.md` registers has a
  Pass 1 checker in `scripts/audit/static_checks.py`, reached from the `_CHECKERS` dispatch table by
  each of that framework's test extensions, and a cache-key extractor covering those extensions,
  with shell the single documented exception that has none. The table lists all eight shipped
  plugins and its checker cell names the function the dispatch table actually holds. A registered
  framework whose extension reaches no checker is a hole in the deterministic quality gate: a
  tautology in that language is graded `unmeasurable` and passes a gate that fails the same
  tautology in every other language; an extension with no extractor is a grade that survives an edit
  to the very test it graded

- RULE-34: `legacy_features_migration.md` is the one home of the legacy `features/` migration procedure. It names both migration-candidate locations `purlin:spec-from-code` looks in, a legacy `features/` directory at the project root and non-compliant specs globbed from `specs/**/*.md`, and states which of the two it owns. It carries the recursive read that skips the `.impl.md` and `.discoveries.md` companions, the extraction rules for both companions, and the Phase 4 question asked before `features/` is deleted. `skills/spec-from-code/SKILL.md` branches to it and carries no second copy, because a procedure written in two places is one edit away from two answers

## Proof

- PROOF-1 (RULE-1): Grep `references/formats/spec_format.md` for `## Rules`, `## Proof`; verify both appear as required sections. Grep for `> Description:` in the metadata fields table. Grep for `RULE-N` pattern documentation
- PROOF-2 (RULE-2): Grep `references/formats/proofs_format.md` for the 7 field names: `feature`,
  `id`, `rule`, `test_file`, `test_name`, `status`, `tier`; verify all appear, and that
  `platform` appears as the field a scoped file carries. Grep for "write-scoped overwrite"
  and for the merge key `(feature, tier, platform, test_file)`, then take a surrounding
  window of text around every occurrence of the three-part `(feature, tier, test_file)` and
  assert each window says the four-part key grew from it, so the old key survives only as
  history. Replacing the four-part key with the three-part one fails the key assertion and
  the window assertion together
- PROOF-3 (RULE-3): Take the `## Proof Markers by Framework` section of
  `references/formats/proofs_format.md`, collect its `###` headings other than
  `Feature-name token`, and parse the `### Feature-name token` table. Verify `pytest`, `Jest`
  and `Shell` are among those headings; that every table row carries a non-empty framework id
  and at least one token literal containing `<feature>`; and that the set of marker-section
  cells equals the set of those headings. Deleting the Vitest row, or naming a subsection the
  file does not carry, fails the set equality
- PROOF-4 (RULE-4): Grep `references/formats/anchor_format.md` for `_anchors/`, `> Source:`, `> Pinned:`, `> Global:`; verify all appear
- PROOF-5 (RULE-5): Grep `references/formats/anchor_format.md` for all 8 type values: `design`, `api`, `security`, `brand`, `platform`, `schema`, `legal`, `prodbrief`; verify all appear in the type metadata documentation
- PROOF-6 (RULE-6): Grep `references/hard_gates.md` for "Proof coverage"; verify it appears and no second gate is defined
- PROOF-7 (RULE-7): Grep `references/commit_conventions.md` for the 8 prefixes `spec`, `feat`, `fix`, `test`, `verify`, `anchor`, `chore`, `docs` in its table rows, and for the `chore(update):` row specifically. Then assert the literal `features=N/T anchors=A/B vhash=<combined-hash>` appears in the Verification Receipt Commit section together with the word `separately`, and that the same `features=` and `anchors=` pair appears in the worked example, in `skills/verify/SKILL.md` and in `dev/issue_receipts.py`'s summary line. Dropping `anchors=` from any one of the four fails the proof
- PROOF-8 (RULE-8): Grep `references/purlin_commands.md` for `Authoring`, `Building`, `Quality`, `Reporting`, `Project`; verify all 5 category headers exist. Count skill entries; verify 12
- PROOF-9 (RULE-9): Grep `references/spec_quality_guide.md` for "rebuild test", "contract boundary/boundaries", "Coverage dimensions", "FORBIDDEN", "Tier"; verify the guide covers the rebuild test, contract boundaries, coverage dimensions, forbidden patterns, and tier assignment. Verify the `### Data contract extraction` subsection exists and names all five contract categories, so the section `skills/spec-from-code/SKILL.md` defers to is present rather than assumed
- PROOF-10 (RULE-10): Grep `references/spec_quality_guide.md` for `Code bug`, `Test bug`, `Spec drift`, and `Assertion Integrity`; verify all appear
- PROOF-11 (RULE-11): Grep `references/spec_quality_guide.md` for `Audience-Appropriate Language`; verify the section exists
- PROOF-12 (RULE-12): Grep `references/drift_criteria.md` for `File Classification`, `NO_IMPACT Patterns`, `Behavioral Directory Exclusions`, `Significance Classification`, `Structural-Only Drift`, `drift_flags`; verify all sections present
- PROOF-13 (RULE-13): Grep `references/spec_quality_guide.md` for the "E2E proof descriptions" section; verify it contains arrange → act → observe flow language, the ban on naming source files/internal functions, and tool-agnostic phrasing
- PROOF-14 (RULE-14): Grep `references/audit_criteria.md` for "E2E Proof Tier Integrity", "tier mismatch", and "source-constant"; verify the section applies to all `@e2e` proofs, not only design anchors
- PROOF-15 (RULE-15): Grep `references/supported_frameworks.md` for the end-to-end proofs section; verify it states no dedicated e2e reporter ships, describes tool-agnostic `@e2e` proofs, and documents wiring through existing plugins
- PROOF-16 (RULE-16): Grep `references/audit_criteria.md` for `Pass D`, all four Design levels, both scoring formulas, and the `[relative]` markers; grep `references/spec_quality_guide.md` for the Design-level labels on its proof-description sections and for `Test Quality Rules (Proof Integrity)`
- PROOF-17 (RULE-17): Grep `references/hard_gates.md`; verify it names PASSING as the receipt condition, explains the VERIFIED bootstrapping problem, and lists both gauges as non-gates. In the same "What Is NOT a Gate" list, verify the words `advisory by default` and the field name `quality_gate` both appear, and that the file still carries the promise of exactly 1 hard gate, so the opt-in is recorded where the count is made. In that same list, verify a bullet names `legacy-`, says `purlin:verify` issues no receipt while such a migration is pending, says nothing is blocked, and links `references/purlin_commands.md#pending-migrations`. Then read `skills/verify/SKILL.md` and verify its pending-migrations pre-check no longer carries `gains no entry` and instead names the `What Is NOT a Gate` list, so the skill and the reference agree on where the refusal is written down. Deleting the bullet fails the proof naming the list; restoring `gains no entry` to the skill fails it naming that file
- PROOF-18 (RULE-18): Grep `references/remote_verification.md` for the loop: verify it names `purlin:test` as the owner and `purlin:verify`'s read-only contract as the reason, that all four operations appear (push, dispatch, await, pull), and that the bound is the literal 3. Then extract the fenced yaml workflow template and assert every required element is inside the template block and not merely in the prose around it: `name: purlin-<platform-id>-proofs`, a `paths-ignore` entry for `**/*.proofs-*@<platform-id>.json`, `workflow_dispatch`, `permissions:` with `contents: write`, `PURLIN_PLATFORM: <platform-id>` and `PURLIN_PLUGIN_ROOT` in the job env, `persist-credentials: true`, a `git clone --depth 1 --branch v<VERSION>` of the plugin into `$PURLIN_PLUGIN_ROOT`, `migrate.py --check` run from `$PURLIN_PLUGIN_ROOT`, the per-framework setup block, `shell: bash` on every `run:` step, `git add '**/*.proofs-*@<platform-id>.json'`, `git diff --cached --quiet`, `[skip ci]`, both trailers, and a `git pull --rebase` retry loop of three attempts ending in `exit 1`. Dropping `shell: bash` from the template fails the proof
- PROOF-19 (RULE-19): Grep `references/remote_verification.md` for the declaration/enforcement split; verify it names branch protection as the enforcement and gives the reason (the field is editable in the tree), and that it lists both gauge caches as gitignored and not travelling, with the Design/Integrity recomputation recommendation naming `audit_llm`
- PROOF-20 (RULE-20): Parse the keys of `templates/config.json` and the field column of `drift_criteria.md`'s Config Field Ownership table; verify every template key has a row, and that each of the six optional fields `audit_llm`, `audit_llm_name`, `audit_criteria`, `audit_criteria_pinned`, `platforms` and `quality_gate` has a row, so removing the `platforms` row or the `quality_gate` row fails. Assert the table was actually found and is non-empty, so the proof cannot pass by comparing two empty sets
- PROOF-21 (RULE-21): Read `references/formats/receipt_format.md` and verify it begins with a `> Format-Version:` line whose value is at least 2; that every version 2 field name appears (`feature`, `vhash`, `vhash_version`, `commit`, `timestamp`, `rules`, `rule_hashes`, `proofs`, `manual`, `evidence`, `test_run`, `proof_files`, `awaiting_runner`) along with each `proof_files` row key (`file`, `tier`, `platform`, `committed_at`, `runner`, `executed_in_test_run`); that it carries both a section saying what the vhash binds and a sentence saying what it does not bind; that a version 1 section documents the historical shape; and that it contains the sentence stating `evidence.test_run` is null for a receipt issued without a run marker. Then read the `### `evidence`` section alone and verify it names the marker path `.purlin/runtime/test_run.json`, names both writers (the proof plugins and `dev/run_tests.sh`), points at `proof_common` RULE-19, and documents `sweep`, `runs` and `skipped_proofs` as keys of `evidence.test_run`, with `runs` described as one object per contributing run and `skipped_proofs` as one `{feature, id, test_file, test_name, reason}` object per marked test the run skipped, naming `proof_common` RULE-20 and the five field names. Verify the `> Format-Version:` value is at least 4, the version that added `skipped_proofs`. Removing any one of those field names, the null-marker sentence, either writer, or the `skipped_proofs` row fails the proof
- PROOF-22 (RULE-22): Extract every fenced yaml block from every markdown file under `references/` and `docs/`; for each occurrence of a `scripts/` path in a block, assert it is immediately preceded by `$PURLIN_PLUGIN_ROOT/` or `${PURLIN_PLUGIN_ROOT}/`, and assert that any block cloning the plugin pins a tag matching `--branch v<VERSION>` rather than a branch name. Assert at least one such `scripts/` invocation was found, so the scan cannot pass by matching nothing, and grep the prose for the sentence recording this repository's own workflows as the `PURLIN_PLUGIN_ROOT: .` exception. Rewriting the preflight step to a bare `scripts/update/migrate.py` fails the proof
- PROOF-23 (RULE-23): Parse the markdown tables of `references/supported_frameworks.md` that carry a `Runner setup` column, collect every framework row from both of them, and assert each row's `Runner setup` cell is non-empty after stripping whitespace. Assert the framework set is the same one the Detection section and the plugin file column name, so a framework cannot pass by being dropped from the table, and that at least seven frameworks were found. Emptying one cell fails the proof
- PROOF-34 (RULE-23): Parse the same tables and assert every row's **Installed as** cell holds exactly as many backticked basenames as the row's **Plugin file** cell holds `scripts/proof/` paths, and that each name is a basename with no directory separator. Then import `scripts/init/scaffold.py` and assert `_install_names()` read from the repository equals the mapping the parsed table gives, and import `scripts/mcp/purlin_server.py` and assert `_plugin_copy_sources()` maps every installed name back to the shipped file beside it, `purlin-proof.sh` to `shell_purlin.sh` among them. Emptying the shell row's cell fails the count assertion; changing the cell to a name the scaffolder does not use fails the equality
- PROOF-24 (RULE-24): Grep `references/purlin_commands.md` for a heading that anchors to `#pending-migrations` and verify its section names `purlin:init --update` as the directive, states that the skill stops before its own work, names the skills that see the advisory by construction, and contains the sentence that `purlin:verify` does not issue receipts while a `legacy-*` migration is pending together with the words refusal and gate. Deleting the section or the verify sentence fails the proof
- PROOF-26 (RULE-26): Parse `hooks/hooks.json` and assert no event key is `PreToolUse`,
  `PermissionRequest` or `UserPromptSubmit`, that every registered entry carries `async` true,
  and that every command names a script under `scripts/hooks/` whose source contains no
  `sys.exit(` with a non-zero literal and no `"decision"` or `"continue": false` hook output.
  Then grep `references/hard_gates.md`: verify it names `hooks/hooks.json`, states that no hook
  gates anything, says the NEVERs are instructions, and names all four enforcement layers.
  Adding a single `PreToolUse` entry to `hooks/hooks.json` fails the parse half; deleting the
  enforcement-layer list fails the grep half
- PROOF-27 (RULE-27): Run `git ls-files .purlin/cache` from the project root and assert its
  output is empty. Assert the same command over the repository root returns a non-empty list, so
  the proof cannot pass in a directory where `git ls-files` returns nothing for every path, and
  assert `.gitignore` carries a `.purlin/cache/` line. `git add -f .purlin/cache/status.json`
  fails the proof
- PROOF-25 (RULE-25): Grep `references/spec_quality_guide.md` for a heading that anchors to `#mutation-check` and verify its section contains three numbered steps whose verbs are break, run and restore, the sentence that a surviving mutation means the fixture cannot tell the correct behaviour from the broken one, two worked examples each naming the discriminating case that was added, and a value statement naming what the check catches, that it costs roughly twice the tokens and minutes per proof, and who should turn it on. Verify `skills/init/SKILL.md` quotes that statement by reference rather than restating it, so the file that prints it and the file that owns it cannot disagree
- PROOF-28 (RULE-28): Split `references/remote_verification.md` on its `## ` headings and take the
  body of `Platforms, environments and prerequisites`; assert it is present, and that it carries
  `**Platform**`, `**Environment**` and `**Prerequisite**` as bold labels, each of the three
  membership questions verbatim and in bold, the literal sentence fragment `is transport to reach
  a platform and is never itself a platform`, and a classification naming `windows-2022`,
  `figma-mcp`, `gemini-cli`, `claude-cli`, php, dotnet, node, gcc, tsc and sqlite3. Then read
  every git-tracked markdown file under `docs/`, `references/` and `skills/` and assert each
  question's text occurs in exactly one of them, `references/remote_verification.md`, and exactly
  once in that file, and that `docs/testing-workflow-guide.md` links
  `references/remote_verification.md` and names the section without restating any question.
  Deleting the provider sentence from the section fails the proof naming that sentence; pasting
  one question into `docs/testing-workflow-guide.md` fails the uniqueness half naming that file
- PROOF-29 (RULE-29): Extract every fenced yaml block from every markdown file under `references/`
  and `docs/`, parse each block's `jobs:` mapping by indentation, and for every job collect the
  lines of its `env:` block; assert no such line contains `${{ runner.` (or `${{runner.`), naming
  the file, the job id and the offending line when one does. Assert at least one job `env` block
  was found across the scan, so the proof cannot pass by parsing nothing, and assert the
  `remote_verification.md` template's `Locate Purlin tooling` step carries
  `echo "PURLIN_PLUGIN_ROOT=$RUNNER_TEMP/purlin" >> "$GITHUB_ENV"`. Putting
  `PURLIN_PLUGIN_ROOT: ${{ runner.temp }}/purlin` back into the template's job `env` fails this
  proof naming `references/remote_verification.md` and the job `proofs` @unit

- PROOF-30 (RULE-30): Split `references/proof_plugin_contract.md` on its `## ` headings, take the
  body of the one section whose heading starts `B.`, and collect every backticked token carrying a
  `/` and none of `<`, `>` or `*` (a template such as `proof_plugins_<framework>.md` names no
  single file). Verify the fixed set of 19 wiring sites is a subset of the tokens collected, and
  that every collected token resolves to an existing path under the project root, and that at
  least 19 tokens were collected so the scan cannot pass on an empty section. Dropping
  `scripts/hooks/pre_push_gate.py` from the checklist fails naming that path; leaving a path in the
  list after moving the file fails the existence half naming it @unit
- PROOF-32 (RULE-32): Verify `references/formats/proofs_format.md` opens with a `> Format-Version:`
  of at least 6, split it on its `## ` headings and assert a `Run marker` section exists; verify
  its body names `.purlin/runtime/test_run.json`, carries each of the nine RULE-19 field names as a
  backticked token, documents `skipped_proofs` and gives one object the literal shape
  `{feature, id, test_file, test_name, reason}`, states both halves of the merge rule, and states
  that the marker is written through a temp file named for the writing process and replaced in one
  operation. Renaming the section heading fails on the missing section; dropping a field from the
  table fails naming that field @unit
- PROOF-33 (RULE-33): Drive a marked tautological fixture per extension through `analyze_test_file`,
  the extensions read from the per-framework table in section B of
  `references/proof_plugin_contract.md`. Assert first that the table's framework set is exactly the
  eight shipped ids `pytest`, `jest`, `vitest`, `shell`, `xunit`, `phpunit`, `sql` and `c`; that the
  checker cell of every row names a function `static_checks` defines and that `_CHECKERS` maps each
  of that row's extensions to that same function object; and that the extension set the table
  registers is exactly the set this proof carries a fixture for. Each fixture is written into a temp
  project with the marker that language's own plugin reads and a tautology its checker is documented
  to catch (`assert True`, `expect(true).toBe(true)`, `Assert.True(true)`, `assertTrue(true)`,
  `CASE WHEN 1 = 1 THEN 'PASS'`, a literal `passed` argument for C, and for shell a `purlin_proof`
  pass line with no test logic above it). Assert `analyze_test_file` returns exactly 1 result whose
  `check` is `assert_true`, and that `_extract_test_code` returns a body for every extension but
  `.sh`, for which it returns None and which `_TEST_CODE_EXTENSIONS` omits while its table row states
  the exception. Deleting a row from the table fails the framework-set assertion naming the
  framework; dropping an extension from `_TEST_CODE_EXTENSIONS` fails the extractor half naming it;
  dropping an entry from `_CHECKERS` fails the dispatch half @unit

- PROOF-34 (RULE-34): Read `references/legacy_features_migration.md` and verify it names both candidate locations, the literal `features/` and the glob `specs/**/*.md`, says which one it owns, and carries the three procedure literals that left `skills/spec-from-code/SKILL.md`: "Read all `.md` files recursively (excluding `.impl.md` and `.discoveries.md`", "Active Deviations" and "Remove old features/ directory?". Then read `skills/spec-from-code/SKILL.md` and verify it branches to the file by path and carries none of those three literals itself, so the two files cannot drift into two procedures. Deleting the reference fails the first half; restoring the procedure into the skill fails the second
