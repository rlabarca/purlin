<!-- Checked-in working plan. This copy is authoritative: it travels with the branch and a new
     context on this machine resumes from it alone. Update the DONE section of each item in the
     same commit as that item's work. No em-dashes or en-dashes in this file. -->

# Platforms, environments, prerequisites: one defensible rule set

Companion to `dev/plans/todo-closeout.md`, written 2026-09-12 in the same session, after the
user asked why `claude-cli` and `figma-mcp` are listed as platforms while GitHub and Azure DevOps
are not. Its items interleave with the closeout's remaining groups (see "Groups, in order"). The
closeout's item E ("either" satisfaction semantics) is replaced by item E' here; every other
closeout item stands, with the renumbering noted under item F.

Branch: `two-gauges-remote-verification`. HEAD at the time of writing: `7c80e87f`.

## Context

`@on(<id>)` on a proof means the proof is evidence only when observed on `<id>`. The registry in
`.purlin/config.json` has two kinds of entry: an OS entry (`windows-2022`), satisfied by host
detection or by a runner that a `runner.provider` (github today, ado next) dispatches to; and an
`environment` entry (`figma-mcp`, `gemini-cli`, `claude-cli`), added in Phase 10.6 with no `os`,
satisfied only by someone setting `PURLIN_PLATFORM` by hand. The environment kind exists for one
reason: the four suites this machine cannot run needed to read AWAITING instead of silently
skipping, and the platform machinery (scoped proof files, both trailers, per-file provenance) was
the only mechanism that could carry who ran them, where and when. GitHub and ADO are correctly not
platforms: a proof never depends on GitHub, it depends on `windows-2022`, and GitHub happens to host
that runner. What is inconsistent is that the same situation, "this test needs something this host
lacks", is handled three ways: php, dotnet, node, gcc, tsc and sqlite3 skip silently with the
committed entry kept and nothing in the report saying the proof did not run here; figma-mcp,
gemini-cli and claude-cli are gated by an env var and modelled as "platforms"; windows-2022 is a
real platform with a runner. The line was drawn by which suites happened to carry an env-var gate,
and the word "platform" on a CLI tool reads wrong.

A second defect sits inside the closeout's decision 4 (the "either" rule). It required the local
agnostic result to come from the same test file and test name as every other result for the proof
id. `skill_audit` PROOF-9 to PROOF-13 are claimed by two different tests, a local grep in
`dev/test_skill_specs.py` and the gemini run in `dev/test_e2e_cross_model_audit.sh`, so the day a
gemini host commits its scoped file the local witness would stop counting and the feature would
drop to 17/17 anyway. The rule protected against the wrong failure.

## Decisions (binding; the user's words)

| # | Decision |
|---|---|
| 13 | "do the clean fix": `skill_audit`'s local grep proofs keep their ids with no `@on`; the gemini suite gets NEW proof ids tagged `@on(gemini-cli)`; no "either" satisfaction rule and no `witness` field are built. Closeout decision 4 is superseded; closeout item E becomes item E' below. |
| 14 | "implement a plan to create the defensible rule set.. use subagents and worktrees where possible.. subagents are opus 5": the three-category rule set in the next section becomes reference text with rules and proofs, the report renders environments as environments, and prerequisites become visible in the run record. |
| 15 | "also include a full scan of the documents and readme and updates to clean/simplify the language and add this new defensible rule set in. This includes a scan of the regulated environments statements and an update based on all the recent additions to our audit and platform/remote runners as well as mutation testing": item T4, sequenced last. |

## The rule set (reference text; single home `references/remote_verification.md`, section "Platforms, environments and prerequisites")

A proof can depend on three different things, and each gets a different mechanism. The test for
membership is the question in bold.

**Platform** (registry `kind` absent, an `os` present; ids `windows-2022`, `macos-14`, the family
ids `windows`, `macos`, `linux`, later `ios` and `android`). **Would the same test passing on a
different OS be evidence for this claim?** No: the identity of the execution target changes the
behaviour being proved. A platform is satisfied by host detection (the machine running the sweep
is that platform) or by a runner. A `runner.provider` (`github`, `ado`) is transport to reach a
platform and is never itself a platform: no proof depends on GitHub. Evidence is per platform; a
result elsewhere is never evidence.

**Environment** (registry `kind: "environment"`, no `os`; ids `figma-mcp`, `gemini-cli`,
`claude-cli`). **Does the outcome depend on an external system's real answers, an account, a
model, or money, so that installing a package cannot reproduce it?** Yes. An environment is
satisfied only by an explicit `PURLIN_PLATFORM` equal to its id, set by a person or a runner
asserting the environment is present, and the result is committed with a `Purlin-Runner:` trailer
so provenance is recorded. Every report surface calls it an environment, never a platform, and
never says "runner" for it: the awaiting state reads "awaiting an environment run".

**Prerequisite** (never registered; php, dotnet, node, gcc, tsc, sqlite3). **Would any host with
the tool installed produce the same evidence?** Yes: the toolchain is needed to execute, and does
not change the claim. A prerequisite is a property of the run, not of the proof, so it is recorded
in the run marker (`.purlin/runtime/test_run.json`, `skipped_proofs`) by the plugins that can
observe a skip, and the report shows the kept entry as inherited from the commit that last proved
it, with the reason, rather than as fresh. It never appears in `@on(...)` and never in the
registry. The pytest `skipif` plus the kept entry (proof_common RULE-18) stay the mechanism;
what changes is that the skip becomes visible.

Classification of the current ids: `windows-2022` platform (GitHub runner attached); `figma-mcp`,
`claude-cli`, `gemini-cli` environments; php, dotnet, node, gcc, tsc, sqlite3 prerequisites. A
future ADO runner attaches to a platform id as a second provider and changes nothing above.

## How to work

- **Opus subagents on every `Agent` call.** Pass `model: "opus"` explicitly. A `fork` when the
  agent needs this plan's reasoning, `purlin:purlin-auditor` for regrades, `general-purpose`
  otherwise.
- **Worktree parallelization, the closeout's rule set unchanged.** A worktree agent gets its own
  `git worktree` on branch `taxonomy/<item-id>`, commits only the files its item owns, runs only
  its own test files whole, never runs `bash dev/run_tests.sh`, never `python3
  dev/issue_receipts.py`, never a `verify:` commit, never regenerates `.purlin/report-data.js`,
  reports under 300 words. The integrator (the main context) cherry-picks in item order, sweeps
  once per group in the foreground, issues receipts, writes the `verify:` commit, fills the DONE
  section.
- **Sequential in the main tree, never a worktree:** anything touching
  `scripts/mcp/purlin_server.py` or `specs/mcp/sync_status.md` (items E' does not; T2 and T3 do).
- **Rule and proof numbers are pre-allocated below** and were verified at `7c80e87f` with
  `command grep -o "^- RULE-[0-9]*" <spec> | sort -t- -k3 -n | tail -1` (and PROOF). Maxima:
  skill_audit RULE-22 / PROOF-22; sync_status RULE-62 / PROOF-101; report_data RULE-40 / PROOF-41;
  purlin_report RULE-45 / PROOF-50 (PROOF-50 was added by closeout item B4, so the closeout's
  allocations for E and F in `purlin_report` are stale); verify_gate RULE-11 / PROOF-11;
  config_engine RULE-12 / PROOF-14; proof_common RULE-18 / PROOF-24; purlin_references RULE-27 /
  PROOF-27; purlin_docs RULE-7 / PROOF-11; skill_verify RULE-14 / PROOF-14; dashboard_visual
  RULE-12 / PROOF-12; proof_plugins_pytest RULE-4 / PROOF-4; proof_plugins_jest RULE-4 / PROOF-5;
  proof_plugins_vitest RULE-2 / PROOF-2; proof_plugins_xunit RULE-6 / PROOF-6.
- `export PATH="/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH"` for every run (the xunit
  fixture targets net8.0); `PYTHONDONTWRITEBYTECODE=1`; `command grep`, never bare `grep`; never a
  subset of one test file; never `git checkout -- specs/`; sweeps in the foreground; specs and
  proofs before receipts; the `verify:` commit separate; `git pull --ff-only` after every push.
- No em-dashes and no en-dashes in anything written. `mutation_checks` is true: every new or
  amended proof gets its mutation, recorded in the commit body and the DONE section.

## Items

| id | what | files owned | tree | depends on | rules / proofs | mutation |
|---|---|---|---|---|---|---|
| E' | The clean fix. `dev/test_e2e_cross_model_audit.sh` emits NEW ids `skill_audit` PROOF-23 to PROOF-27 (one per RULE-9 to RULE-13, `@e2e @on(gemini-cli)`); PROOF-9 to PROOF-13 stay the local proofs from `dev/test_skill_specs.py`, retagged `@unit` because they grep `skills/audit/SKILL.md` (their `e2e:` prefix is dropped and PROOF-11's "Parse external LLM response" wording becomes the grep it is; closeout item B6 found that mismatch). The parent plan's TODO note on 10.6 is closed. No `sync_status` change: an id whose only result is scoped and absent already reads AWAITING, and the local ids stay agnostic, which is the whole point of separate ids | `specs/skills/skill_audit.md`, `specs/skills/skill_audit.proofs-*.json`, `dev/test_e2e_cross_model_audit.sh`, `dev/test_skill_specs.py` (TestSkillAudit only), `dev/plans/platform-generic-remote-verification.md` (tick the 10.6 TODO) | main, sequential (small) | none | `skill_audit` PROOF-23 to PROOF-27 new; PROOF-9 to PROOF-13 amended (tier and wording) | remove the local emit for PROOF-9 and `skill_audit` must read 21/22; PROOF-23's description regraded PROVABLE and the feature must read `awaiting an environment run, 5 proofs` (after T2; before T2 `awaiting runner, 5 proofs`) |
| T1 | The rule set as reference text: new section "Platforms, environments and prerequisites" in `references/remote_verification.md` (the single home; `docs/testing-workflow-guide.md`'s Platforms section gains one pointer sentence and nothing else), the three membership questions verbatim, the classification of the current ids, and the sentence that a `runner.provider` is never a platform. `config_engine` RULE-12 amended to name the membership question for `kind: environment` and to state that a toolchain is never an environment entry | `references/remote_verification.md`, `docs/testing-workflow-guide.md` (one sentence), `specs/instructions/purlin_references.md`, `specs/instructions/purlin_references.proofs-*.json`, `dev/test_purlin_references.py`, `specs/mcp/config_engine.md`, `specs/mcp/config_engine.proofs-*.json`, `dev/test_config_engine.py` | worktree | none | `purlin_references` RULE-28 / PROOF-28 (the section exists, carries all three category names, the three questions and the provider sentence); `config_engine` RULE-12 amended, PROOF-14 extended (a `kind: environment` entry carrying `os` is still an error; the amended text is present) | delete the provider sentence from the section and PROOF-28 must fail naming it; delete the membership question from RULE-12's paragraph in the reference and PROOF-14's text half must fail |
| T2 | Rendering: environment ids read as environments everywhere. `sync_status`: the Platforms block gets a third label, `environment: <id> (N proofs; run with PURLIN_PLATFORM=<id> on a host that has it, commit with a Purlin-Runner trailer)`, replacing the `runner:` line for such ids; the Platforms line segment reads `<id> (environment) ...`; the RULE-58 detail line reads `⚠ <id>: awaiting an environment run, N proofs (...)` for an environment id. `report_data`: `platforms.summary[id]` and `platforms.registry[id]` carry `kind` (`os` or `environment`) so no reader recomputes it. Dashboard: chips for an environment id show the id itself (not an OS abbreviation) with an `env` badge beside the host badge style; the modal rows carry the same badge and the column header reads `Platform / environment`; tooltips say the id is satisfied only by a hand run with `PURLIN_PLATFORM`. `verify_gate.py --check`: By-platform lines read `<id> (environment): ...` | `scripts/mcp/purlin_server.py` (`_platform_dispatch_note`, `_platforms_block`, `_platforms_line`, `_platform_lines`, `_platform_summary`), `specs/mcp/sync_status.md` and proofs, `specs/mcp/report_data.md` and proofs, `scripts/report/purlin-report.html`, `specs/dashboard/purlin_report.md` and proofs, `scripts/ci/verify_gate.py`, `specs/ci/verify_gate.md` and proofs, `dev/test_mcp_server.py`, `dev/test_report_data.py`, `dev/test_purlin_report.py`, `dev/test_verify_gate.py`, `docs/dashboard-guide.md` (the chip bullet) | main, sequential | F (host row: both touch `_platform_summary` and the modal), T1 (vocabulary) | `sync_status` RULE-63 / PROOF-102; `report_data` RULE-42 / PROOF-43; `purlin_report` RULE-47 / PROOF-52 (Playwright); `verify_gate` RULE-12 / PROOF-12 | print `runner:` for an environment id and PROOF-102 must fail; drop `kind` from the summary row and PROOF-43 must fail; render the OS abbreviation for an environment chip and PROOF-52 must fail; drop `(environment)` from the gate line and PROOF-12 must fail |
| T3 | Prerequisites visible. The four plugins that observe a skip (pytest via the skip report and `call.excinfo.value.msg`, jest via `SKIPPED_STATUSES`, vitest via a task with no terminal state, xunit via the `Skipped` outcome and its message) record `{feature, id, test_file, test_name, reason}` for every marked test the run skipped into the run marker under `skipped_proofs`, merged through the helper item L introduces (`reason` is null where the framework carries none). `sync_status` prints per feature `⚠ N proofs not executed on this host (<reason>): entries inherited from <sha7>` (sha from the proof file's provenance) and counts them on the summary line as `inherited`; the payload marks each such proof entry `inherited: true` and the feature carries `inherited_count`; the dashboard renders an amber `inherited` chip in the proof cell; the receipt's `evidence.test_run` carries `skipped_proofs` (Format-Version bump of `receipt_format.md`). `proof_common` RULE-18 is extended (never weakened) with the sentence that a kept entry is recorded in the run marker as skipped with its reason | `scripts/proof/pytest_purlin.py`, `scripts/proof/jest_purlin.js`, `scripts/proof/vitest_purlin.ts`, `scripts/proof/xunit_purlin.cs`, the four `.purlin/plugins/` copies, `specs/_anchors/proof_common.md` and proofs, `scripts/mcp/purlin_server.py`, `specs/mcp/sync_status.md` and proofs, `specs/mcp/report_data.md` and proofs, `scripts/report/purlin-report.html`, `specs/dashboard/purlin_report.md` and proofs, `dev/issue_receipts.py`, `references/formats/receipt_format.md`, `specs/skills/skill_verify.md` and proofs, `specs/instructions/purlin_references.md` (RULE-21 amended for the new field), `dev/test_multilang_proof_plugins.py`, `dev/test_mcp_server.py`, `dev/test_report_data.py`, `dev/test_purlin_report.py`, `dev/test_receipts.py`, `dev/test_skill_specs.py` | main, sequential | L (defines the marker merge helper and the per-plugin write; T3 adds a field to a shape L fixes, so it lands after L rather than inside it: L is already the closeout's largest item and changes the sweep counts, and two mutation-checked commits are reviewable where one is not) | `proof_common` RULE-20 / PROOF-26 (one test per capable plugin), RULE-18 extended; `sync_status` RULE-64 / PROOF-103; `report_data` RULE-43 / PROOF-44; `purlin_report` RULE-48 / PROOF-53; `skill_verify` RULE-16 / PROOF-16; `purlin_references` RULE-21 amended, PROOF-21 extended | drop the reason capture in pytest and PROOF-26 must fail naming `reason`; render nothing for a skipped proof and PROOF-103 must fail; write the receipt without `skipped_proofs` and PROOF-16 must fail |
| T4 | The docs pass (decision 15). (a) Every file under `docs/`, `README.md`, and the user-facing prose of `references/remote_verification.md`, `references/spec_quality_guide.md`, `references/hard_gates.md` and the explanatory parts of `references/audit_criteria.md`, plus `skills/*/SKILL.md` only where a step restates a doc: short sentences, one idea each, no em-dashes or en-dashes in anything rewritten, no "signed", "tamper-evident" or approval vocabulary, the vocabulary of `references/purlin_commands.md`. (b) The platform docs point at the rule set's single home (T1's section) and never restate the membership questions. (c) `docs/regulated-environments.md` rewritten against what now exists: the two gauges and Pass D1/D2 versus Pass 1/2; the audit cache re-keying and auditor identity; the criteria pin; manual stamps counting; evidence older than code; receipt v2 and what the vhash binds; per-platform verification with runners and both trailers; environment ids run by hand; the enforcement layers table by reference; mutation checks as the opt-in authoring standard; `purlin:init --update` and the migration ids; the pre-commit and pre-push hooks with their fail-open and fail-closed paths; the consumer run marker once L lands; the scaffold script. Every statement in that file names the mechanism behind it or is deleted. Then `python3 dev/capture_doc_screenshots.py` in the main tree after cherry-pick | `docs/**`, `README.md`, the four references named, `skills/*/SKILL.md` (prose only), `specs/instructions/purlin_docs.md` and proofs, `dev/test_purlin_docs.py`, `specs/instructions/purlin_references.md` and proofs only if a reference rule's literal moves, `dev/test_purlin_references.py` likewise | worktree; whole-file runs of `dev/test_purlin_docs.py` and `dev/test_purlin_references.py` only | T1, T2, T3 and closeout G and I (it rewrites the files they touch; G takes purlin_docs PROOF-12, I takes RULE-8 / PROOF-13) | `purlin_docs` RULE-9 / PROOF-14 (regulated-environments.md names a mechanism per section: each `##` section carries at least one backticked script, rule id, config field or command name from a fixed list, and the four forbidden phrases stay absent); RULE-10 / PROOF-15 (the platform docs carry the three category names only beside a link to the reference section and never the membership questions); RULE-11 / PROOF-16 (no em-dash or en-dash byte sequence in `docs/`, `README.md` or the four references outside fenced code blocks) | paste an approval sentence with no mechanism into regulated-environments.md and PROOF-14 must fail naming the section; copy one membership question into testing-workflow-guide.md and PROOF-15 must fail; insert one em-dash into README.md and PROOF-16 must fail naming the line. **Reviewer: the controller reads the full diff of `docs/regulated-environments.md` before the cherry-pick.** |

### Renumbering of the closeout's items E and F

Closeout item E took `sync_status` RULE-63 / PROOF-102, `report_data` RULE-41 / PROOF-42 and
`purlin_report` RULE-46 / PROOF-50, and item F was allocated one higher in each. E is replaced by
E', which adds no rule to any of those specs, and closeout item B4 has since taken `purlin_report`
PROOF-50. Item F therefore takes `report_data` RULE-41 / PROOF-42 and `purlin_report` RULE-46 /
PROOF-51, and T2 takes the numbers in the table above. The closeout table is amended in the same
commit that lands E'.

## Groups, in order (interleaved with the closeout)

- **Closeout Group 1** finishes first: B regrade, DONE sections, sweep, receipts, `verify:`,
  push.
- **Group 2.** Main tree: E' (small, sequential; its DONE section amends the closeout's item
  table). Worktrees in parallel: closeout F (host row, renumbered as above), closeout G (docs
  rule tightening), T1 (the reference section and the two rules). Cherry-pick F, G, T1; sweep;
  receipts; `verify:`; push.
- **Group 2b.** Main tree, sequential: T2 (rendering). After F, because both touch
  `_platform_summary` and the modal, and after T1, because the wording T2 renders is T1's. Sweep;
  receipts; `verify:`; push.
- **Group 3.** Main tree: closeout K (agent witness run) and J (consumer-CI fixture, whose
  `init_project` now calls `scripts/init/scaffold.py`). Worktrees: closeout H (hot-reload; lands
  after T2 because both touch `purlin_server.py`) and I (pinning guidance). Sweep; receipts;
  `verify:`; push.
- **Group 4.** Main tree, sequential: closeout L (consumer run marker), then T3 (prerequisites in
  the marker). Sweep after each; receipts; `verify:`; push.
- **Group 5.** Worktree: T4 (docs pass). Cherry-pick after the controller's review of the
  regulated-environments diff; `python3 dev/capture_doc_screenshots.py`; final foreground sweep;
  receipts; `verify:`; push; `git pull --ff-only`; CI green; both TODO lists updated.

## DONE

Each item gets its section filled in as it lands, in the same commit as the item's last work.

## DONE - E': the clean fix for skill_audit

_Placeholder. Record: the five new proof ids and their descriptions; the retagged tiers of
PROOF-9 to PROOF-13; the feature's count before and after (22/22 expected to stay 22/22, status
moving from VERIFIED to PASSING with `gemini-cli: awaiting ..., 5 proofs` until a gemini host
runs the suite); the mutation; the closeout table amendment; the parent plan's TODO tick._

## DONE - T1: the rule set as reference text

- Commit `0d529016` on `taxonomy/T1`, cherry-picked as `164852b0`. The section `## Platforms,
  environments and prerequisites` sits in `references/remote_verification.md` directly after
  `## Platforms` (where `@on(...)` is first explained) and before `## Where it lives, and why`. It
  carries the three bold membership questions verbatim, the `**Platform**` / `**Environment**` /
  `**Prerequisite**` labels, the provider sentence and the classification of the current ids.
  `docs/testing-workflow-guide.md`'s Platforms section gained one pointer sentence.
- `purlin_references` RULE-28 / PROOF-28 (`TestPlatformTaxonomyHasOneHome`): every literal is in
  that section and each question occurs exactly once across tracked markdown under `docs/`,
  `references/` and `skills/`. `config_engine` RULE-12 amended with the membership question and
  the sentence that a toolchain is a prerequisite, never a registry entry; PROOF-14 extended with
  the text half (the `env-with-os` error assertion kept). Both PROVABLE.
- Mutations: the provider sentence deleted fails PROOF-28 naming it; the membership question
  deleted from the reference fails PROOF-14 naming the section. `dev/test_purlin_references.py`
  27 to 28 tests.
- Left for T3: the prerequisite paragraph names the run marker as where skipped proofs are
  recorded but not a `skipped_proofs` field, which does not exist until T3.

## DONE - T2: environments rendered as environments

- Commit `10c5815b` in the main tree (18 files). `sync_status` RULE-63 / PROOF-102: the Platforms
  block prints `environment: <id> (N proofs; run with PURLIN_PLATFORM=<id> on a host that has it,
  commit with a Purlin-Runner trailer)` instead of a `runner:` line for a `kind: environment` id;
  the Platforms line segment reads `<id> (environment) ...` and its awaiting clause `N proofs
  awaiting an environment run`; the RULE-58 detail line reads `⚠ <id>: awaiting an environment run,
  N proofs (...)`; OS ids are unchanged. Two predicates, `_is_environment` and `_platform_kind`, are
  the only deciders. `report_data` RULE-42 / PROOF-43: `platform_kind` (`os` | `environment`) on
  every `platforms.summary` row and every `platforms.registry` entry (the host row is `os`); item F's
  `kind` (`host` | `declared`) untouched. `purlin_report` RULE-47 / PROOF-52: an environment chip
  shows the id plus an `env` badge styled like the host badge, all three platform tables are headed
  `Platform / environment`, chip and cell tooltips read `environment: satisfied only by a hand run
  with PURLIN_PLATFORM=<id> on a host that has it`. `verify_gate` RULE-12 / PROOF-12: By-platform
  lines read `<id> (environment): ...`. `config_engine` PROOF-14 and `report_data` RULE-31 / PROOF-32
  amended because they asserted the moved literals.
- This repository now prints three `environment:` lines (claude-cli 4 proofs, figma-mcp 15,
  gemini-cli 4), `runner: windows-2022 (2 proofs; github workflow purlin-windows-2022-proofs)`,
  `⚠ gemini-cli: awaiting an environment run, 4 proofs (PROOF-23 to PROOF-26)` and
  `⚠ claude-cli: awaiting an environment run, 3 proofs (PROOF-17 to PROOF-19)`; the gate reads
  `figma-mcp (environment): 15 proved, 0 awaiting, 0 failing (1 feature)`, exit 0.
- D1: every new description PROVABLE (sync_status 96/2, report_data 35/8, purlin_report 50/2,
  verify_gate 11/1, config_engine 14/0). Tests +1 function in each of test_mcp_server,
  test_report_data, test_verify_gate, test_purlin_report. Mutations: `runner:` printed for an
  environment id fails PROOF-102; `platform_kind` dropped fails PROOF-43 (`KeyError`); the env chip
  inheriting the OS abbreviation fails PROOF-52 (`['macENV ⏳', 'win ⏳']`); `(environment)` dropped
  from the gate line fails PROOF-12.

## DONE - T3: prerequisites visible in the run record

_Placeholder. Record: the `skipped_proofs` shape and which plugins carry a reason; the
sync_status line and summary count; the payload fields; the chip; the receipt field and the
Format-Version bump; the extended RULE-18 text; this repository's real output (expected: the six
`tsc not available` skips in `dev/test_cheat_matrix.py` and `dev/test_proof_stress.py` become
visible as inherited entries); the mutations._

## DONE - T4: the docs pass

_Placeholder. Record: every file rewritten with a one-line summary of the change; the
regulated-environments.md section list with the mechanism each names; the three rules and
proofs; the mutations; the screenshot refresh; and the controller's review note on the
regulated-environments diff._

## Verification checklist

- `export PATH="/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH"`; `PYTHONDONTWRITEBYTECODE=1
  bash dev/run_tests.sh` green in the foreground; `.purlin/runtime/test_run.json` reads `ok: true`
  at HEAD and, after T3, carries `skipped_proofs` naming the six tsc skips with their reason.
- `python3 -c "import sys; sys.path.insert(0,'scripts/mcp'); from purlin_server import
  sync_status; print(sync_status('.'))"` shows, after T2, `environment: figma-mcp (15 proofs; ...)`,
  `environment: claude-cli (...)` and `environment: gemini-cli (4 proofs; ...)` in the Platforms
  block, `runner: windows-2022 (2 proofs; github workflow purlin-windows-2022-proofs)` unchanged,
  and `skill_audit` reading `⚠ gemini-cli: awaiting an environment run, 4 proofs (PROOF-23,
  PROOF-24, PROOF-25, PROOF-26)` with 22/22 rules proved (PROOF-27 moved to the local
  `dev/test_e2e_fake_audit_llm.sh` by closeout item B15, since that phase never calls gemini).
- `python3 scripts/ci/verify_gate.py --check --project-root .` exits 0 and its By-platform
  section reads `figma-mcp (environment): ...` for each environment id.
- `python3 scripts/audit/static_checks.py --check-proof-design` over every spec these items
  touch reads zero UNPROVABLE and zero LOOSE among the descriptions they wrote.
- `command grep -rn $'\xe2\x80\x94\|\xe2\x80\x93' dev/plans/platform-taxonomy.md` returns
  nothing; after T4 the same over `docs/`, `README.md` and the four references returns nothing
  outside fenced code blocks.
- `python3 scripts/update/migrate.py --check --project-root .` exits 0 with only `receipt-v1`
  pending until closeout item K lands, then nothing.
- Receipts: `skill_audit` still receipts (platform-partial receipts are allowed, `skill_verify`
  RULE-9) and reads PASSING with the gemini environment awaiting; the count line is otherwise the
  closeout's.
- `bash dev/bump_version.sh --check` exits 0; `VERSION` reads `0.10.0`; no tag; `main` neither
  merged nor pushed.

## Traps

Carried from the closeout plan, all of them, plus:

- **Closeout E is dead.** Do not build `proofs_proved_locally`, `witness`, or any "either" branch
  in `_platform_results`; decision 13 replaced it. Anyone resuming from the closeout plan alone
  must read this file's Decisions table first.
- **`purlin_report`'s next free PROOF is 51, not 50.** Closeout item B4 added PROOF-50 during
  Design remediation; the closeout table's E and F allocations for that spec predate it.
- **A proof id with two claimants is the defect, not a feature.** One proof id, one test. When a
  rule needs a local proof and an environment proof, they are two ids.
- **"environment" is a rendering word, not a new registry kind.** `kind: "environment"` already
  exists (`config_engine` RULE-12); T2 changes what the report says, not what the registry
  accepts. Adding a third kind for prerequisites is exactly the mistake this plan exists to avoid.
- **The run marker is written by `dev/run_tests.sh` today and by the plugins after L.** T3's
  `skipped_proofs` must be written through L's merge helper on both paths, or a dev sweep and a
  consumer run will disagree about the marker's shape.
