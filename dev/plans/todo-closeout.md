<!-- Checked-in working plan. This copy is authoritative: it travels with the branch and a new
     context on this machine resumes from it alone. Update the DONE section of each item in the
     same commit as that item's work, the way dev/plans/platform-generic-remote-verification.md
     does. No em-dashes or en-dashes in this file. -->

# Closing the "TODO before pushing main" list

Continuation of `dev/plans/platform-generic-remote-verification.md` (Phases 6 to 11 DONE at
`50638cb5`, plan finalized at `49ba38b5`). That plan's "TODO before pushing main" list and its
Backlog table are the input to this one. `dev/plans/ado-runner-provider.md` is the output side:
it runs on the work machine and is not started here.

Branch: `two-gauges-remote-verification`. HEAD at the start of this plan: `5f6b0cb8`.

## Context

This session closes the TODO list that Phase 11 left open on this machine: it runs both halves of
the Proof Design gauge for real over the whole repository (Pass D1 free and deterministic, Pass D2
batched per feature), installs the php and dotnet toolchains so the two proof-plugin suites that
have never executed anywhere finally execute here, spends the agent-test budget once so
`skill_spec` and `skill_build` get their `claude-cli` witness and stop reading as evidence that no
run recorded, decides and implements the "either" satisfaction semantics that `skill_audit`
PROOF-9 to PROOF-13 have been waiting on, adds the host row the Integrity modal is thin without,
tightens the one paragraph-scoped docs rule, and schedules every remaining Backlog row: a spec for
the pre-commit hook, the MCP hot-reload gate, the plugin-pinning guidance, and the consumer run
marker written by all eight proof plugins. It also builds the committed consumer-CI fixture and
dry-run script that the templates have never been exercised against. What it hands to the ADO
plan is a branch whose only open witnesses are `figma_web` (no Figma MCP server on this machine)
and the Integrity gauge (deliberately deferred until after the ADO work), plus a reusable
`dev/fixtures/consumer-ci/` the ADO machine can copy for an Azure DevOps scratch project instead
of writing a third project builder. `main` is still neither merged nor pushed, and VERSION stays
`0.10.0`.

## Decisions (binding; the user's words)

| # | Decision |
|---|---|
| 1 | "run Pass D1 (free, deterministic) and Pass D2 (LLM, batched per feature, about 43 calls) now for the full repo; Proof Integrity (`purlin:audit` Pass 1+2) is deferred until after the ADO work and stays 'not measured' (honest)". Cost stated honestly: "D1 is a grep-and-parse grader with no model call; D2 is a model reading each PROVABLE description against its rule; the model is Claude subagents on the user's account (no `audit_llm` configured)." |
| 2 | "If Design falls below the gate (at or above 91%, zero UNPROVABLE): fix in session via `purlin:spec` rewrites, mutation-checked, until the bar holds." |
| 3 | "run the agent test here (`PURLIN_PLATFORM=claude-cli PURLIN_E2E_AGENT=1 python3 -m pytest dev/test_e2e_build_agent.py`, real `claude -p` sessions, about $1 to $3) and commit the rewritten `@claude-cli` scoped files with `-m \"Purlin-Runner: <user>@<host>\" -m \"Purlin-Platform: claude-cli\"` ... closing skill_spec and skill_build's claude-cli proofs. figma_web stays awaiting: this machine has no Figma MCP server the test can drive; record the exact command for a host that has it." |
| 4 | "a proof declared `@on(...)` whose id also has an agnostic (platform None) local result counts as proved locally, and a platform result is reported as an additional witness when present; AWAITING RUNNER is reported only when neither exists." Plus: "the rule must require the agnostic result to be from a run of the SAME test (same test_file and test_name) AND must keep the platform gap visible", and "recommend that 'either' applies only to environment-kind platforms (`kind: environment`), never to OS platforms, and say why." |
| 5 | "install the toolchains here (`brew install php`, `brew install --cask dotnet-sdk` or the official installer; record versions), run `dev/test_multilang_proof_plugins.py` (whole file) so the php and xunit proofs execute, commit, and check the sweep counts change from 27 skipped accordingly; if the runner-side equivalents are needed (`PURLIN_PLATFORM`), say they are not because these plugin proofs are agnostic." |
| 6 | "Host row in the Integrity modal: add it (purlin_report next-free rule, Playwright proof, `platforms.summary` gains a row for the detected host covering agnostic results, badged host; report_data rule for the payload)." |
| 7 | "VERSION stays 0.10.0, no bump, no tag; the Unreleased RELEASE_NOTES section folds into the 0.10.0 notes when main is pushed and the official GitHub release is cut. `purlin_version` RULE-9 keeps the counts line honest meanwhile." |
| 8 | "reuse `init_project` from dev/test_init_e2e.sh (do not write a third builder; there is no gh scratch-repo tooling anywhere in the repo), produce a committed fixture `dev/fixtures/consumer-ci/` ... a script `dev/consumer_ci_dryrun.sh` ... a rule and proof ... that the fixture's workflows equal the reference templates after substitution (so the fixture cannot drift from the docs), with the live dry run itself as a manual proof ... or an `@on(github-actions)` environment proof; pick one and justify." |
| 9 | "tighten `purlin_docs` RULE-1's `@windows` exemption to a named section of the migration docs (rule and proof change, mutation: put `@windows` in an unrelated paragraph containing 'legacy')." |
| 10 | Backlog rows, all scheduled now: "(a) spec for scripts/hooks/pre-commit.sh ... (b) MCP hot-reload: gate on `PURLIN_DEV_RELOAD=1`, log the traceback to stderr, `mcp_transport` spec rule and proof; (c) plugin pinning guidance ... (d) consumer run marker: every plugin writes/merges `.purlin/runtime/test_run.json` ... Order (d) last; it is the largest." |
| 11 | "Remaining TODO items: CI green at head (check), backlog triage (this plan is the triage), figma_web witness (deferred with the command), anything new a subagent defers (append)." |

## How to work

- **Opus subagents on every `Agent` call.** Pass `model: "opus"` explicitly; do not inherit. A
  `fork` when the agent needs this plan's reasoning, `purlin:purlin-auditor` for the D2 batches,
  `general-purpose` otherwise.
- **Worktree parallelization, with this exact rule set.**
  - A worktree agent gets its own `git worktree` on its own branch, named `closeout/<item-id>`.
  - It commits **only the files its item owns**, listed in the item table. Nothing else, ever.
  - It runs **only its own tests**: the test files its item adds or amends, whole file.
  - It **never** runs `bash dev/run_tests.sh`, never runs `python3 dev/issue_receipts.py`, never
    writes a `verify:` commit, never regenerates `.purlin/report-data.js`.
  - It reports back under 300 words: files changed, rules and proofs added at the numbers this
    plan allocated, its own test result, and the mutation it ran and restored.
  - The **integrator** (the main context) cherry-picks each worktree commit onto the main tree in
    the order the item table gives, sweeps **once** at the end of the group, runs the receipt
    issuer, writes the `verify:` commit, and fills in that item's DONE section.
- **Sequential in the main tree, never a worktree:** any item touching
  `scripts/mcp/purlin_server.py` or `specs/mcp/sync_status.md`. Those two are the contention
  points for every phase of the parent plan and a cherry-pick into either costs more than the
  parallelism buys.
- **Rule and proof numbers are pre-allocated in the item table below** and were verified against
  the specs at `5f6b0cb8`. A worktree agent takes only the numbers its row gives it, even when the
  spec file it opens would suggest a lower next-free number (another item in the same group may
  hold it). Two items appending rules to the same spec file (E and F both append to
  `specs/dashboard/purlin_report.md`) will conflict at the tail of the Rules list on cherry-pick;
  the integrator resolves by keeping both, in number order.
- **Sweeps run in the foreground.** A background sweep was killed by the OS for memory during
  Phase 6.2 and churned the proof files.
- `PYTHONDONTWRITEBYTECODE=1` in the environment for every test run, so no `__pycache__` lands in
  a temp fixture that a byte-identity proof then reads.
- `command grep`, never bare `grep`: `grep` here is aliased to `ugrep --ignore-files` and its
  `--include` globs silently miss files.
- **Never `git checkout -- specs/`** to undo proof churn: it reverts the spec `.md` edits with it.
  Use `git checkout -- 'specs/**/*.proofs-*.json'`.
- `git pull --ff-only` after every push. Three workflows commit back to this branch.
- No em-dashes and no en-dashes in anything written this session.
- `mutation_checks` is `true` in this repo's `.purlin/config.json`, so every new or amended proof
  gets its mutation run and the mutation is recorded in the commit body and in the DONE section.
- Commit rhythm, unchanged from the parent plan: code plus spec rules plus proofs in one
  `feat(...)`/`fix(...)`/`test(...)` commit, `python3 dev/issue_receipts.py`, then a separate
  `verify:` commit. Check `git diff --stat specs/` before each commit.

## Items

Numbers below are the next free number in each spec at `5f6b0cb8`, computed per spec with
`command grep -o "^- RULE-[0-9]*" <spec> | sort -t- -k3 -n | tail -1` (see Traps: the parent
plan's `-k2` key sorts on the wrong field and reports the last line in the file, not the highest
number).

| id | what | files owned | tree | depends on | rules / proofs | mutation |
|---|---|---|---|---|---|---|
| A | Pass D1 repo-wide, then Pass D2 batched per feature (43 features, one call each) on Opus `purlin:purlin-auditor` subagents; write both caches; record Design % with its coverage denominator. Integrity stays not measured | `.purlin/design_cache.json`, `.purlin/audit_cache.json` (unchanged), `dev/plans/todo-closeout.md` | main | none | none (an audit adds no rules) | n/a |
| B | Design remediation, only if A lands below the gate: `purlin:spec` rewrites of every UNPROVABLE and enough LOOSE to reach 91%+ | the spec `.md` files named by A's findings | main | A | none new; amended descriptions only | each rewritten description regraded under `--check-proof-design`; the proof behind it re-run |
| C | `brew install php`, `brew install --cask dotnet-sdk`; record both versions; run `dev/test_multilang_proof_plugins.py` whole file; commit the php and xunit proof entries | `specs/proof/proof_plugins_php.proofs-unit.json`, `specs/proof/proof_plugins_xunit.proofs-unit.json`, `specs/_anchors/proof_common.proofs-*.json`, `RELEASE_NOTES.md` counts line | worktree | none | none new (the rules exist; only the entries were missing) | drop the `platform` stamp from `phpunit_purlin.php` and `xunit_purlin`'s writer; each scoping test must fail |
| D | New `specs/hooks/pre_commit_hook.md`: the three fail-open paths made explicit and logged, the `git add` of the digest stated, `PURLIN_SKIP_DIGEST` specced, and the plugin-root resolver shared with `pre-push.sh` | `specs/hooks/pre_commit_hook.md`, `specs/hooks/pre_commit_hook.proofs-*.json`, `scripts/hooks/pre-commit.sh`, `dev/test_pre_commit_hook.py`, `dev/run_tests.sh` | worktree | none | `pre_commit_hook` RULE-1 to RULE-6, PROOF-1 to PROOF-8 (new spec) | remove one fail-open `echo` and its proof must fail naming the branch |
| E | "Either" satisfaction semantics in `_platform_results`/`_awaiting_runner`; report the witness; then tag `skill_audit` PROOF-9 to PROOF-13 `@on(gemini-cli)` and delete the TODO note | `scripts/mcp/purlin_server.py`, `specs/mcp/sync_status.md`, `specs/mcp/report_data.md`, `specs/dashboard/purlin_report.md`, `specs/skills/skill_audit.md`, `dev/test_mcp_server.py`, `dev/test_report_data.py`, `dev/test_dashboard_visual.py` | main | none | `sync_status` RULE-63 / PROOF-102; `report_data` RULE-41 / PROOF-42; `purlin_report` RULE-46 / PROOF-50 | drop the `(test_file, test_name)` equality clause and PROOF-102 must fail on the different-test fixture; drop the `kind == environment` guard and PROOF-102 must fail on the `@on(windows-2022)` plus macOS-agnostic fixture |
| F | Host row in `platforms.summary` and the Integrity modal: a row for the detected host covering the agnostic results, badged as the host | `scripts/mcp/purlin_server.py` (summary builder only), `specs/mcp/report_data.md`, `specs/dashboard/purlin_report.md`, `tools/purlin-report.html`, `dev/test_report_data.py`, `dev/test_dashboard_visual.py` | worktree | E (numbering, and the witness field it adds) | `report_data` RULE-42 / PROOF-43; `purlin_report` RULE-47 / PROOF-51 (Playwright) | drop the host badge from the row and PROOF-51 must fail; count a scoped result into the host row and PROOF-43 must fail |
| G | Tighten `purlin_docs` RULE-1's `@windows` exemption to a **named section** of the migration docs rather than any paragraph containing `legacy` | `specs/instructions/purlin_docs.md`, `specs/instructions/purlin_docs.proofs-unit.json`, `dev/test_purlin_docs.py`, the migration docs whose headings the rule now names | worktree | none | `purlin_docs` RULE-1 amended, PROOF-2 amended, PROOF-12 new (the discriminating case) | put `@windows` in an unrelated paragraph that contains the word `legacy`; PROOF-2/PROOF-12 must fail naming that file and paragraph |
| H | MCP hot-reload: gate the reload on `PURLIN_DEV_RELOAD=1`, log the traceback to stderr instead of `except Exception: pass` | `scripts/mcp/purlin_server.py` (`main()` only), `specs/mcp/mcp_transport.md`, `specs/mcp/mcp_transport.proofs-integration.json`, `dev/test_mcp_transport.py` | worktree | E, F (both touch `purlin_server.py`; H is the last to land) | `mcp_transport` RULE-8 / PROOF-8 | raise inside the reload block with the env set; stderr must carry the traceback and the server must still answer the request |
| I | Plugin pinning guidance: `docs/regulated-environments.md` gains an integration point naming "pin the plugin by tag in the marketplace config" and "minimum Python 3.11" | `docs/regulated-environments.md`, `specs/instructions/purlin_docs.md`, `specs/instructions/purlin_docs.proofs-unit.json`, `dev/test_purlin_docs.py` | worktree | G (same spec file) | `purlin_docs` RULE-8 / PROOF-13 | delete the Python-version sentence; PROOF-13 must fail naming it |
| J | Consumer-CI fixture and dry run: `dev/fixtures/consumer-ci/` built through `init_project` from `dev/test_init_e2e.sh:43`, plus `dev/consumer_ci_dryrun.sh`, plus a new spec | `specs/ci/consumer_ci.md`, `specs/ci/consumer_ci.proofs-*.json`, `dev/fixtures/consumer-ci/**`, `dev/consumer_ci_dryrun.sh`, `dev/test_consumer_ci.py`, `dev/run_tests.sh` | main | none | `consumer_ci` RULE-1 to RULE-3, PROOF-1 / PROOF-2 unit, PROOF-3 `@manual` | change one line of the fixture's `purlin-ubuntu-24-proofs.yml`; PROOF-1 must fail naming the line |
| K | Agent witness run: `PURLIN_PLATFORM=claude-cli PURLIN_E2E_AGENT=1 python3 -m pytest dev/test_e2e_build_agent.py`, then commit the rewritten `@claude-cli` scoped files with both trailers in one `-m` | `specs/skills/skill_spec.proofs-*@claude-cli.json`, `specs/skills/skill_build.proofs-*@claude-cli.json` | main | none | none new (the proofs exist and are declared; only the witness was missing) | n/a: this is a witness run, not a behaviour change |
| L | Consumer run marker: every plugin writes or merges `.purlin/runtime/test_run.json` (`at`, `commit`, `test_files` it collected, counts) so a consumer receipt carries `evidence.test_run`; `dev/issue_receipts.py` and `purlin:verify` Step 3 read it | `scripts/proof/*` (all 8), `.purlin/plugins/*` (the 4 copies), `specs/_anchors/proof_common.md`, `specs/skills/skill_verify.md`, `references/formats/receipt_format.md`, `specs/instructions/purlin_references.md`, `skills/verify/SKILL.md`, `dev/issue_receipts.py`, `dev/test_multilang_proof_plugins.py`, `dev/test_proof_plugins.sh`, `dev/test_skill_specs.py` | main | C (php and dotnet must be installed so all 8 plugins can be proved) | `proof_common` RULE-19 / PROOF-25 (one description, one test per plugin); `skill_verify` RULE-15 / PROOF-15; `purlin_references` RULE-23 amended (`receipt_format.md` content) | drop one plugin's marker write; PROOF-25 must fail naming that plugin |

### E: the exact "either" semantics to write

A proof `P` declared `@on(D1, ..., Dn)` is satisfied on `Di` when **either** of these holds:

1. **Platform witness.** A scoped result exists whose result platform satisfies `Di` under the
   existing `_result_satisfies` (equality, or `Di` is a family id and the registry entry's `os`
   matches). Unchanged from today.
2. **Local witness, environment platforms only.** `Di` has `kind: "environment"` in the registry
   (`config_engine` RULE-12), **and** an agnostic result (`platform` is `None`) exists for `P`,
   **and** that agnostic entry's `(test_file, test_name)` equals the `(test_file, test_name)` of
   every other result entry for `P` in the project. A proof id whose results disagree about which
   test produced them gets no local witness on any platform: the agnostic result is then evidence
   about a different test, not about this declaration.

`AWAITING RUNNER` is reported only when **neither** holds. When both hold, the platform witness is
reported as an additional witness alongside the local one, with its runner provenance.

The per-platform record keeps the gap visible in every case. `platforms.<id>` gains a `witness`
field: `"platform"`, `"local"`, or `"both"`. When `witness` is `"local"` the `Platforms:` block,
the dashboard chip and `verify_gate.py --check`'s By-platform section all read
`proved locally, not yet proved on <id>`, never a bare `PROVED`. The counts the summary reports
are unchanged in total; what moves is that a locally witnessed proof leaves `proofs_awaiting` and
enters a new `proofs_proved_locally`, so the platform gap is a number, not an absence.

**Why environment-kind only, and what it changes for `@on(windows-2022)`.** An `environment` id
names a tool that either answers on a host or does not (a Figma MCP server, the gemini CLI, the
claude CLI). It is satisfied only by an explicit `PURLIN_PLATFORM` and never by host detection,
precisely because nothing a machine reports about itself shows the tool answers there. So when the
same test produced an agnostic result locally, the tool did answer locally, and the local run is
real evidence about the same code path. An **OS** id names where the code executed, and the entire
reason to write `@on(windows-2022)` is that the OS changes the behaviour. A macOS run of the same
test is positively not evidence about windows-2022. Under this rule, a project declaring
`@on(windows-2022)` with a local macOS agnostic result therefore **stays AWAITING RUNNER**,
exactly as today. If "either" were unrestricted, that declaration would read PROVED off a macOS
run, which is the failure mode this whole decision exists to prevent: a platform requirement made
silently optional by the machine that happens to be running the sweep.

With this in place, `skill_audit` PROOF-9 to PROOF-13 can carry `@on(gemini-cli)` (an
`environment` entry) without dropping the feature from 22/22 to 17/17: `dev/test_skill_specs.py`
supplies the agnostic local witness, and a future gemini run supplies the platform witness. Delete
the parent plan's TODO note in the same commit.

### J: manual proof, not `@on(github-actions)`

Pick the `@manual` stamp, stamped after the live dry run.

An `@on(github-actions)` environment proof would need a scoped proof file written by a run inside
the scratch repo and committed back into **this** repository. That never happens: the scratch repo
is created, dispatched, asserted and deleted, and its proof files belong to it. The proof would
read AWAITING RUNNER forever, which is the opposite of honest. The dry run is a human-initiated,
account-touching, money-adjacent action against a repository that does not persist, and a dated
`@manual` stamp is exactly the record for that. `sync_status`'s manual-staleness machinery already
re-opens the stamp when the files in Scope change, so a template edit re-opens the dry run without
anyone remembering to.

`consumer_ci` RULE-1 (the fixture's `purlin-ubuntu-24-proofs.yml` and `verify-gate.yml` equal the
reference templates after substituting `ubuntu-24`, `ubuntu-24.04` and the tooling pin) and RULE-2
(the fixture is a complete minimal consumer project) are proved by deterministic unit tests, so the
fixture cannot drift from the docs without a red test. Only RULE-3, which is about the live run,
is manual. The tooling clone in both fixture workflows pins
`--branch two-gauges-remote-verification` for now; RULE-1 states that and states that it becomes
`--branch v<VERSION>` when `main` is pushed and the release is cut, so the temporary pin is a
recorded exception rather than a silent one.

## Parallel groups, in order

**Group 1.** Main tree: item A (Pass D1, then the 43 Pass D2 batches), then item B if the gate is
not met. Worktrees in parallel: item C (php and dotnet install, then the plugin suites) and item D
(the pre-commit spec). Integrator cherry-picks C then D, sweeps once, receipts, `verify:`.
C changes the sweep counts, so its commit also updates the RELEASE_NOTES Unreleased counts line
(`purlin_version` RULE-9).

**Group 2.** Main tree: item E ("either" semantics plus the `skill_audit` gemini tags), sequential
because it edits `purlin_server.py` and `sync_status.md`. Worktrees in parallel: item F (host row)
and item G (docs-rule tightening). Cherry-pick F then G, sweep once, receipts, `verify:`. Expect
the `purlin_report.md` tail conflict between E and F and resolve it in number order.

**Group 3.** Main tree: item K (the agent witness run, then the trailered commit) and item J
(the consumer-CI fixture and dry-run script). Worktrees in parallel: item H (MCP hot-reload) and
item I (pinning guidance). H lands after E and F because all three touch `purlin_server.py`.
Cherry-pick H then I, sweep once, receipts, `verify:`.

**Group 4.** Main tree only: item L (the consumer run marker). It touches all eight plugins, the
four copies, the receipt issuer and the verify skill, and it changes the sweep counts again.
No parallel work alongside it.

**Final.** Foreground `bash dev/run_tests.sh`; `python3 dev/issue_receipts.py`; the `verify:`
commit; push; `git pull --ff-only`; confirm CI green; update the parent plan's
"TODO before pushing main" list (tick what closed, leave `figma_web` and the Integrity gauge open
with their reasons, append anything a subagent deferred); update this file's DONE sections.

## DONE

Each item gets its section filled in as it lands, in the same commit as the item's last work.

## DONE - A: Pass D1 and Pass D2 over the whole repository

_Placeholder. Record: the D1 command and its per-level counts across all 43 specs; how many
descriptions went to D2 and in how many batches; the Design score with its coverage denominator;
every UNPROVABLE and LOOSE finding with the feature and proof id; whether the 91% bar held before
any remediation; and the explicit statement that Proof Integrity was not measured and why._

## DONE - B: Design remediation

_Placeholder. Record: each rewritten description with its old and new grade, the proof behind it,
and the re-run result. If A met the bar, record "not needed" and the number that made it so._

## DONE - C: php and xunit toolchains installed, the two plugin suites executed

_Placeholder. Record: `php --version` and `dotnet --version` exactly; the whole-file run of
`dev/test_multilang_proof_plugins.py`; the proof entries that landed for `proof_plugins_php`,
`proof_plugins_xunit` and `proof_common`; the sweep counts before and after (802 passed / 27
skipped at `50638cb5`; 14 of those 27 are the four skipped classes, 2 + 6 + 3 + 3, so expect
roughly 816 passed / 13 skipped and record the real numbers); the RELEASE_NOTES counts line
update; and the statement that no `PURLIN_PLATFORM` runner-side equivalent is needed because
these plugin proofs declare no platforms and write agnostic files._

## DONE - D: spec for the pre-commit hook

_Placeholder. Record: the six rules and what each fail-open path now logs; the shared plugin-root
resolver and where it lives; the `PURLIN_SKIP_DIGEST` rule; the eight proofs and their mutations;
and the `dev/run_tests.sh` line that adds `dev/test_pre_commit_hook.py` to the pytest pool._

## DONE - E: "either" satisfaction semantics, and the gemini tags

_Placeholder. Record: the final rule text; the `witness` field's three values and where each is
rendered; the `@on(windows-2022)` plus macOS fixture that proves an OS platform is never satisfied
locally; the `skill_audit` count before and after tagging PROOF-9 to PROOF-13 (22/22 expected to
stay 22/22); and both mutations._

## DONE - F: host row in the Integrity modal

_Placeholder. Record: the `platforms.summary` host row's shape and what it counts; the badge; the
Playwright assertion; and both mutations._

## DONE - G: `purlin_docs` RULE-1 tightened

_Placeholder. Record: the named section the exemption now points at; the amended PROOF-2 and the
new PROOF-12; and the mutation (an unrelated paragraph containing `legacy`) with the file and
paragraph the failure named._

## DONE - H: MCP hot-reload gated and logged

_Placeholder. Record: the `PURLIN_DEV_RELOAD=1` gate; what stderr carries on a failed reload; that
the request is still answered; and the mutation._

## DONE - I: plugin pinning guidance

_Placeholder. Record: the integration point's wording in `docs/regulated-environments.md`; RULE-8
and PROOF-13; and the mutation._

## DONE - J: consumer-CI fixture and dry run

_Placeholder. Record: what `init_project` produced and what was added by hand; the fixture's file
list; the two workflow files and the substitutions RULE-1 checks; the dry-run script's assertions;
whether the live run was executed and against which scratch repo; the `@manual` stamp date; and
the mutation._

## DONE - K: the claude-cli witness

_Placeholder. Record: the run's cost and duration; the scoped files it rewrote; the commit sha and
that `git log --format='%(trailers:key=Purlin-Runner,valueonly)'` reads it back; the `skill_spec`
and `skill_build` verdicts before and after; and the exact figma_web command left for a host with
a Figma MCP server._

## DONE - L: consumer run marker

_Placeholder. Record: the marker's shape as each of the eight plugins writes or merges it; how
concurrent writers are handled; the four `.purlin/plugins/` copies regenerated and their
byte-identity proofs still green; `receipt_format.md`'s updated `evidence.test_run` paragraph;
`purlin:verify` Step 3's new text; the per-plugin PROOF-25 tests; and the mutation._

## Verification checklist

- `export PATH="$PWD/.venv/bin:$PATH"`; `PYTHONDONTWRITEBYTECODE=1 bash dev/run_tests.sh` green in
  the foreground; `.purlin/runtime/test_run.json` reads `ok: true` at HEAD.
- **Sweep counts are expected to change, twice.** The `skipped` count drops when php and dotnet
  are installed and the php and xunit classes stop skipping (item C: 27 skipped at `50638cb5`, of
  which 14 belong to `TestPHPProofPlugin`, `TestXUnitProofPlugin`, `TestPHPPlatformScoping` and
  `TestXUnitPlatformScoping`). The `passed` count rises for C, again for D's eight pre-commit
  proofs, again for J's two unit proofs, and again for L's per-plugin proofs. Every commit that
  moves either number updates the RELEASE_NOTES Unreleased counts line in the same commit, which
  is what `purlin_version` RULE-9 checks against the run marker.
- `python3 scripts/ci/verify_gate.py --check --project-root .` exits **0** and prints the
  enforcement note, the By-platform section, and the new host row.
- `python3 scripts/update/migrate.py --check --project-root .` exits **0**, with the only
  outstanding migration being `receipt-v1` for `figma_web`. Any other pending migration is a
  regression, not an expected leftover.
- `python3 dev/issue_receipts.py` issues every feature and skips only `figma_web`
  (`evidence not in the recorded run`). After item K, `skill_spec` and `skill_build` must no
  longer appear in the skip list.
- **Both audit numbers recorded.** The Design score from item A with its coverage denominator and
  its date, and Proof Integrity written as `not measured` with the reason (deferred until after
  the ADO work; the hand-built cache is invalid by construction since Phase 10.4). Do not let a
  stale Integrity percentage appear anywhere.
- `bash dev/bump_version.sh --check` exits 0 and `cat VERSION` reads `0.10.0`. No tag.
- CI green at HEAD: `gh run list` shows `verify-gate`, `version-check` and
  `purlin-windows-2022-proofs` green, and `git pull --ff-only` brings back nothing new.
- `git ls-files .purlin/cache` is empty; `git ls-files assets/src` lists five `.mmd`;
  `git ls-files dev/fixtures/consumer-ci | wc -l` is non-zero and every file the fixture rule
  names is tracked; `git ls-files '*.proofs-*@claude-cli.json'` lists the files item K committed;
  `git ls-files .purlin/runtime` is empty (the run marker stays gitignored, in this repo and in a
  consumer project).
- `command grep -rn $'—\|–' dev/plans/todo-closeout.md` returns nothing, and the same
  search over every file this plan touched finds nothing new outside `purlin_server.py`'s existing
  output separators. Use zsh's `$'...'` escape form, never the literal characters: the parent
  plan's literal form makes the check find itself and always report a hit, and the system `grep`
  on this machine is BSD grep, which has no `-P`.
- `python3 scripts/audit/static_checks.py --check-proof-design --project-root .` reads zero
  UNPROVABLE across the repository and Design at or above 91%.

## Hand-back to the ADO plan

What the machine that picks up `dev/plans/ado-runner-provider.md` will find:

- **Branch:** `two-gauges-remote-verification`, pushed to `origin`. `git fetch && git checkout
  two-gauges-remote-verification` is the whole handoff. `main` is still neither merged nor pushed.
- **HEAD after this session: unknown at the time of writing.** The final `verify:` commit's sha
  goes here when the session ends. Do not assume `5f6b0cb8`.
- **Two open items, both deliberate.** `figma_web` (15 proofs, `@on(figma-mcp)`) has no witness:
  this machine has no Figma MCP server. On a host that has one, run
  `PURLIN_PLATFORM=figma-mcp PURLIN_E2E_FIGMA=1 python3 -m pytest dev/test_e2e_figma_web.py`
  and commit with `git commit -m "test(figma_web): proofs from a figma-mcp host" -m "$(printf
  'Purlin-Runner: <user>@<host>\nPurlin-Platform: figma-mcp')"`. And **Proof Integrity is not
  measured**: `purlin:audit` Pass 1 and Pass 2 are deferred until after the ADO work, by decision,
  and the gauge says so honestly rather than showing a stale number.
- **A fixture the ADO machine can reuse.** `dev/fixtures/consumer-ci/` is a complete minimal
  consumer project (config with a `platforms` registry entry, one spec with an `@on` proof, the
  pytest plugin copy, a conftest, one test, two workflow files). Copy it, swap the
  `platforms.ubuntu-24` entry for an Azure DevOps entry with `runner.provider: "ado"`, and swap
  the two GitHub workflow files for the ADO pipeline the plan designs. `dev/consumer_ci_dryrun.sh`
  is the GitHub-shaped driver and is the model for the ADO one: create, dispatch, wait, assert
  both trailers on the commit-back, assert the gate, delete unless `--keep`.
- **The tooling pin is temporary.** The fixture's workflows clone the plugin at
  `--branch two-gauges-remote-verification`. That becomes `--branch v<VERSION>` when `main` is
  pushed and the release is cut; `consumer_ci` RULE-1 records it so the flip is not forgotten.

## Traps

Carried from the parent plans:

- **Never run a subset of the tests inside one file.** The merge key is per test file, so a
  partial run replaces that file's entries for the features it touched and drops the proofs you
  skipped. Whole files only; finish with `bash dev/run_tests.sh`; check `git diff --stat specs/`.
- **Never `git checkout -- specs/`.** It reverts the spec `.md` edits along with the proof churn.
  Use `git checkout -- 'specs/**/*.proofs-*.json'`.
- **`grep` is aliased to `ugrep --ignore-files` here** and its `--include` globs behave
  differently from GNU grep. Use `command grep` for any search you intend to trust.
- **Sweeps in the foreground.** A background sweep was killed by the OS for memory in Phase 6.2
  and churned the proof files.
- **Receipts reference committed state.** Commit specs and proofs first, run the issuer, then
  commit the receipts as a separate `verify:` commit.
- **`git pull --ff-only` after every push.** Three workflows commit back to this branch.
- pytest is not installed system-wide; use the venv on PATH.
- Do not restore `.claude/settings.json`. `"enabledPlugins": {}` is correct here.

New for this session:

- **The `-m` trailer paragraph.** `git` parses trailers out of the **last paragraph only**, and
  each `-m` is its own paragraph. Two separate `-m` flags leave `Purlin-Runner:` unreadable to
  `git log --format='%(trailers:key=Purlin-Runner,valueonly)'`, and the report then says
  `runner not recorded` after a run that actually happened. Both trailers go in **one** `-m`,
  joined by a newline through `printf`, exactly as the template in
  `references/remote_verification.md` does it. Item K's commit is the one that gets this wrong.
- **The agent test costs money.** `dev/test_e2e_build_agent.py` drives two real `claude -p`
  sessions, about $1 to $3 and 3 to 8 minutes. It is gated behind `PURLIN_E2E_AGENT=1` for exactly
  that reason. Run it once, in the foreground, and do not re-run it to "make sure".
- **`brew install php` and `brew install --cask dotnet-sdk` change system state.** They are not
  repository edits and they are not reversible by `git`. Ask the user in-session before running
  either, and record the versions that landed.
- **`gh repo create <user>/purlin-consumer-ci-scratch --private --source . --push` creates a real
  repository under the user's account**, and `gh repo delete --yes` destroys it. Both need an
  explicit yes from the user at run time, not just the standing decision in this plan. Default to
  `--keep` on the first run so the failure is inspectable, and delete on the user's word.
- **The parent plan's next-free numbers cannot be trusted, and neither can the command it
  suggests.** `sort -t- -k2 -n` splits `- RULE-9` on `-` into `""`, `" RULE"`, `"9"` and keys on
  field 2, which is not numeric, so every line compares equal and `tail -1` returns the **last
  line in the file**, not the highest number. Use `-k3`. Verified maxima at `5f6b0cb8`:
  `sync_status` RULE-62 / PROOF-101, `report_data` RULE-40 / PROOF-41, `purlin_report` RULE-45 /
  PROOF-49, `proof_common` RULE-18 / PROOF-24, `skill_audit` RULE-22 / PROOF-22, `purlin_docs`
  RULE-7 / PROOF-11, `purlin_references` RULE-27 / PROOF-27, `verify_gate` RULE-11 / PROOF-11,
  `mcp_transport` RULE-7 / PROOF-7, `skill_verify` RULE-14 / PROOF-14, `config_engine` RULE-12 /
  PROOF-14, `dashboard_visual` RULE-12 / PROOF-12, `purlin_version` RULE-9 / PROOF-9.
- **Two items appending to one spec file conflict on cherry-pick.** E and F both append rules to
  `specs/dashboard/purlin_report.md`, and G and I both append to
  `specs/instructions/purlin_docs.md`. G and I are in different groups so they serialize; E and F
  are not, so the integrator resolves that one tail conflict by keeping both rules in number
  order. This is why the item table pre-allocates numbers rather than letting each agent compute
  its own.
- **A worktree agent that sweeps or receipts corrupts the run.** The run marker and every receipt
  reference committed state in the main tree. A worktree sweep writes a marker for a tree that
  does not exist upstream, and a worktree receipt binds a vhash to commits nobody else has. The
  rule is absolute: worktree agents commit their own files, run their own tests, and stop.
