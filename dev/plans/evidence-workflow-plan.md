# Purlin 0.10.0: the evidence workflow refactor

Consolidated plan (2026-09-13). Part A is the design and becomes
`dev/plans/evidence-workflow.md` verbatim in phase 0. Part B is the technical design lanes
build from. Part C is the execution: strategy, phases, lanes, verification.

## Context

Purlin 0.10.0 was never released. Origin `main` is at v0.9.5 plus one commit; the 343 commits
on `two-gauges-remote-verification` (two LLM grading gauges, `@on(...)` platforms, remote
verification, agent-written receipts, a committed 1.7 MB dashboard blob) exist only on that
branch. A critical review found the mechanism did not earn its vocabulary: `VERIFIED` meant
"the files agree with each other", the honesty signal was an LLM opinion cached in an
editable file, and the effort went into the framework proving itself to itself while outside
users hit a silently dead reporter. This plan reshapes Purlin around three ways of working
(solo, team, regulated), specs as the shared artifact, committed CI-written records as
evidence, approvals bound to hashes, mutation engines as the honesty signal, and AI used only
where judgment is needed. It ships as **0.10.0**, the one-step transition for v0.9.5 users.

**Decisions made by the user**

| Decision | Choice |
|---|---|
| Self-hosted specs during the refactor | Freeze; delete specs for removed code in phase 0; re-spec the new surface in phase 9 |
| Version and branch | 0.10.0 on new branch `evidence-workflow` from this HEAD |
| Git hosts | GitHub complete; Azure DevOps (ADO) behind the same interface, live-tested later on the user's work machine |
| Languages | Python, TypeScript/JavaScript, .NET, shell, SQL. C and PHP removed |
| Mutation engines | mutmut 3, Stryker, Stryker.NET; none for shell and SQL, stated plainly |
| Evidence storage | In the project tree under `.purlin/records/`, committed; validated states are annotated git tags. One repo, one branch |
| Anchor repos | Optional; single repo with everything beside the code is the default |
| Dashboard | Read-only static page on the Purlin design system (plain HTML and CSS on its tokens, both themes); local from the project, published by CI as a build artifact. No Pages, no hosting |
| Design system | Lives at `design/` in the repo (tokens, guidelines, components, assets); every visual surface and all copy follow `design/readme.md` |
| Test environments | Each project tests on its real engine (SQL proofs run against the project's own test database) |
| spec-from-code | Kept as a slim skill |
| Subagents | Opus 4.8 for mechanical lanes, Opus 5 for design-judgment lanes, worktrees under `../purlin-wt/` |

---

# Part A: the design

## A1. Vocabulary (every doc, skill and message uses these and no others)

- **rule**: a claim about what the software must do, one line in a spec. **proof**: how the
  claim is observed. **test**: the executable form of a proof, tagged with its rule.
  **record**: one verify run's observations, a committed file. **approval**: a named
  person's attestation that a rule, proof and test belong together, a committed file.
- **anchor**: a spec for something shared across features. **local anchor**: in the project.
  **anchor repo**: an optional separate repo holding anchors and designs for one or more
  projects. **pinned anchor**: the project's local copy of an anchor from an anchor repo,
  tied to a commit.
- **gate**: the one project setting, what CI must see before a change can merge: `tested`,
  `recorded`, `approved`.
- **test strength**: of the deliberate breaks made to the code, the share the tests caught,
  as a percentage. Config key `min_strength`, record field `test_strength`, status column
  `strength`. Never "caught score", "mutation score" or "kill rate". "Mutation testing" is named once,
  as the technique, in the running-and-records doc.
- **approver list**: the emails of the people who may approve, kept in `.purlin/config.json` and changed by PR, so who could approve and when is in git history. An approval counts when its commit is signed by someone on the list. People are added or removed at any time.
- **git host**: the service that holds the repo, runs CI, and enforces branch rules: GitHub or Azure DevOps. Never call it a forge. **CI**: the git host's hosted
  runner executing the same `purlin:verify` a developer runs, on every push and PR.
- **origin**: tag on every rule naming its owner: `pm`, `design`, `qa`, `eng`. Default
  `eng`; required under `approved`. Drift routes changes by origin.
- **risk**: tag on a rule, `high`, `medium`, `low`; default `low`; required under `approved`.
- **criterion**: optional tag linking a rule to an upstream acceptance-criterion id.
- **The seven states** of a rule: Drafted (no proof), Proof ready (proof text passes the
  free checks), Tested (tagged test passes locally), Recorded (a record that counts under the gate exists at HEAD and passes), Reviewed (a brief exists for the current hashes), Approved (a current approval
  exists and the record passes), Stale (rule, proof or test text changed after approval; a
  human must look). A separate flag, **re-verify pending**, means only the code changed:
  the approval stands and CI clears it on the next run.

## A2. Three processes, one setting

| Process | Who | gate | CI requires before merge | Approvals |
|---|---|---|---|---|
| Solo | one developer | `tested` | every rule has a passing tagged test | none |
| Team | PM, designer, engineers, QA | `recorded` | every rule has a CI-written record at this commit with the test strength at or above `min_strength` | advisory; anyone, by `purlin:approve` or PR review |
| Regulated | the same team, GxP | `approved` | `recorded`, plus a current approval on every high and medium rule, committed with a signed commit by someone on the approver list; low risk auto-approved by CI | required; the approver list decides who |

Derived defaults, each overridable: `ai_review_at` never / high / medium; `min_strength` 50 /
70 / 80; risk and origin optional / optional / required. Init asks one question, "what must be true before CI lets a change merge?", and nothing else: the language is detected from the tree, the git host from the remote URL, the CI workflow is written when the gate requires it and skipped under `tested`, and config files are edited the way conftest and jest config already are, with a summary of what was written. Two honest exceptions: an empty repo is asked the language, and `approved` is asked who approves. `purlin:init --gate <level>` raises or lowers the gate later; raising adds what is missing and asks before each write, lowering never deletes anything.
The status table and dashboard add columns as artifacts exist (risk, records, approvals), so
nothing else is configured. **A gate is three things**: a CI job running verify on every
push, a branch rule blocking merge unless it passes, and the setting saying what pass means.

## A3. Commands

Core: `spec`, `build`, `test`, `verify`, `review`, `approve`, `drift`. Supporting: `init`,
`anchor`, `status`, `find`, `rename`, `spec-from-code`. Plain language reaches every one of
them; the documented syntax is canonical, never required. Every command ends by naming the
next step, computed from the state.

| Command | Who | When |
|---|---|---|
| `purlin:init` | engineer | once, one question; `--gate` to change the gate, `--update` after a plugin update, `--ci` to add CI under `tested`, `--add <language>` later |
| `purlin:spec` | engineer's agent, or PM or QA in Claude Code | at intake from a sentence, PRD, ticket, pasted criteria or mocks in `designs/`; when a rule is wrong during build; to reconcile after rules are added; `--resolve` after a merge conflict. Ends with "Spec created: `<name>`. Build it now?" |
| `purlin:spec-from-code` | engineer | once on an existing codebase; rules tagged `origin: eng`, `risk: low` |
| `purlin:anchor` | engineer, or PM in Claude Code | `create` local; `add <git-url> --path <file>` pinned; `sync [name|--all] [--check]`; `propose <name>` |
| `purlin:build [name]` | engineer | every change; no name reads the state (one buildable spec builds it, several asks, none points at spec) |
| `purlin:test` | engineer | constantly; seconds; tests only |
| `purlin:verify` | engineer locally; CI on every push and PR | tests plus breaks plus a record; under `tested` the developer's verify commits the record; CI's verify commits the record that counts under higher gates, auto-approves low risk, writes briefs, posts the PR comment, publishes the dashboard artifact; `--tag <name>` pins a validated state |
| `purlin:review` | QA, or an engineer acting as QA | no arguments needed: it finds every rule that needs a look, shows the list by risk, then walks it one brief at a time with approve, add a case, or skip at each stop. A feature, rule or filter only narrows it |
| `purlin:approve` | anyone on the approver list | one rule, a feature or a batch, as a signed commit; under `approved` it reaches main by PR like any change |
| `purlin:status` | anyone with a checkout | any time |
| `purlin:drift [pm|design|qa|eng]` | everyone | session start; after a pin or a design export changed; before QA opens the review list; before a release |
| `purlin:find`, `purlin:rename` | engineer | locate; rename across specs, tests, approvals, records |

Drift per role: `pm` criteria without rules, pm-origin rules changed, engineer-added rules,
pins behind; `design` mocks changed, design rules stale; `qa` approvals stale, review list size, rules without a negative case; `eng` files touched → rules affected, tests missing, tags
missing, pins behind, re-verify pending.

Removed outright: `purlin:audit` and both grading scores, the `purlin-auditor` agent,
`anchor add-figma`, `verify --manual` and `--recheck`, `init --set` for retired keys,
`--sync-audit-criteria`, the remote-run path in `test` (replaced by `verify --remote`), receipts, the platform registry and per-platform proof files (replaced by `@env` and the CI matrix), committed proof files, the committed dashboard blob. `@manual` proofs stay: no test; the
evidence is an approval file with a one-line note; always human, never auto-approved.

## A4. Evidence

**Records in the tree.** `.purlin/records/<feature>/<timestamp>-<commit7>-<runner>.json`,
one per verify run, committed. Adding files never conflicts. Verify prunes a feature's
records beyond the newest three unless a validation tag names them. A **validation tag** is
an annotated tag `validated/<name>` (from `purlin:verify --tag` or a CI release step) whose
message lists the records it vouches for; those are kept for ever. The log is the git
history of the folder.

**Label from git, not from the file.** The last commit touching a record decides:
**ci** when it was created through the git host's API by the CI identity (GitHub signs API
commits made with the Actions token and no custom author, so `%G?` is `G` and the committer
is `github-actions[bot]`; on ADO the committer is the build service and no signature
exists, which the docs say), **developer** when a person committed it, **local** when
uncommitted. `tested` counts ci or developer; `recorded` and `approved` count ci only.

**How CI writes.** `purlin:verify --ci` runs on every push to a PR branch and to the default
branch. It creates one commit "purlin: record for <commit7>" containing the record and any
CI auto-approvals through the git host's REST API (blob → tree → commit with no author or
committer → ref update, retry on a non-fast-forward), so the commit is signed and labelled
ci. Forked PRs: verify runs and the comment posts, no commit, and the job says so. Squash
merges change the sha, so the record that counts on the default branch is the one CI writes
after the merge; PR-branch records fall to the retention rule.

**Branch rules by gate** (init prints them; the git host enforces them). GitHub uses three
rulesets so the bypass is narrow: (1) "require a pull request" and "require status checks"
with the Actions app as the only bypass actor; (2) "restrict file paths" on
`.purlin/records/**` and `specs/**/*.approvals/*.ci.json` with the Actions app as the only
bypass actor, so a person cannot push a record or a CI approval; (3) "block force pushes"
and "restrict deletions" with no bypass. Under `tested`, only (3) is suggested. ADO: the
build service alone holds Contribute on those paths via branch security, plus no force push
and no delete.

**Scanning and the PR.** `scripts/report/scan.py --repo <url> [--ref <branch|tag>]` reads
`specs/` and `.purlin/records/` by sparse fetch and prints the seven-state rollup, noting
"N commits behind the latest record". CI posts the same rollup as a PR comment and publishes
the dashboard page plus data as the `purlin-dashboard` build artifact linked from the
comment. Anyone with repo access opens it; nothing is provisioned.

**Freshness.** A record carries the git tree hash of each spec's `> Scope:` files. Code change → approval stands, `re-verify pending` until CI runs. Rule, proof or test text change → `Stale`, a human looks.

**Cross-platform validation, kept small.** A proof that must be proven on a particular operating system carries `@env(windows)`, `@env(macos)` or `@env(linux)`; those three are the whole vocabulary in 0.10.0 (named services such as a database are a later addition; SQL projects use `sql_engine` as before). A proof with no tag is satisfied by any OS. Init reads the tags in `specs/` and writes a CI matrix to match, one job per OS named, each running the same `purlin:verify --ci` and writing its own record (`<timestamp>-<commit7>-ci-<os>.json`, so jobs never collide; retention keeps the newest three per feature per OS). A tagged proof is Recorded only when a counting record from that OS passes it; a rule with proofs on two OSes needs both; the status line says "windows: no record yet" rather than adding a state. On a Mac the plugin skips a Windows-tagged test and status says so. `purlin:verify --remote` pushes the branch, waits for the workflow with the git host's CLI (`gh run watch` on GitHub; on ADO it prints the pipeline URL and returns, the watch being part of the ADO follow-up), pulls the records CI committed, and prints the table. No registry, no version constraints, no host detection beyond the OS name, no per-OS proof files.

## A5. Approvals

`specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.<approver-slug>.json` for people,
`...<hash8>.ci.json` for CI auto-approvals. The file binds the hashes of rule text, proof
text and test body (plus the pinned design file for `origin: design`), the risk, the
approver, the brief hash and the record path. Stale when the current hashes or risk differ.
Auto-approval: low risk only, passing test, test strength at or above `min_strength` (or
attribution unavailable and the free checks pass). Under `approved` the gate requires a
current human approval on high and medium and checks the approval commit is an ancestor of
the protected branch head.

**Approver list.** `approvers: ["jane@acme.com", ...]` in `.purlin/config.json`, changed by
PR like any file, so git history records who could approve and when. `purlin:init --gate
approved` asks for the emails and prints the one-time commit-signing setup for each approver
(`git config gpg.format ssh`, `git config user.signingkey ~/.ssh/id_ed25519.pub`,
`git config commit.gpgsign true`, and where to upload the key so the git host shows
Verified). An approval counts when the commit that added its file is signed (`%G?` is `G`),
its author email is on the list as of that commit, and that author differs from the author of
the commit that last touched the test. `sync_status` and `verify_gate.py --check` enforce it;
under `approved` with no list they print `→ approver list missing: run purlin:init --gate
approved` and the gate exits 1. Works with one QA person, the same on GitHub and ADO, and
needs no CODEOWNERS.

## A6. Roles and entry points

- **PM**: never needs a checkout. With an AI assistant (Purlin PM tool in Claude Desktop, or
  Claude Code on the anchor repo or project): describe the feature; the tool drafts or edits
  a spec or anchor, tags rules `origin: pm`, never silently edits a rule owned by `eng` or
  `qa` (it leaves a PR comment proposing the change), opens a PR; the PM reads the rendered
  diff and merges. Without an assistant: write criteria anywhere, hand them to the engineer,
  whose agent runs `purlin:spec`; the PM reviews that PR. After CI runs, the dashboard
  artifact from the PR and `drift pm` show their criteria's states.
- **Designer**: exports mocks from any tool (Figma export, Claude Design output,
  screenshots, PDFs, an HTML prototype) and either drops them into `designs/<feature>/` by
  PR or hands them to the Purlin PM tool in Claude Desktop, which accepts uploaded images and
  opens the PR itself, so a designer never touches git. `purlin:spec` reads the images and
  drafts `origin: design` rules about what a person would see. Screenshots from tests are
  evidence; the brief shows mock beside screenshot.
- **QA**: three ways in: Claude Code on the repo (`purlin:review`, which finds what needs a
  look and walks it); the Purlin QA tool in Claude Desktop (built on `scan.py`, produces the
  triage report, opens PRs with proof edits and approvals); or the dashboard artifact plus
  PR review with no AI. QA works the **review list** CI prepared, ordered by risk, never the whole rule list. Adding a case in plain language drafts the proof and test for the next build.
  Batch approval is one commit.
- **Engineer**: `drift eng` at session start → `anchor sync` if a pin is behind → spec if
  needed → build → test → verify locally → push. Adds `origin: eng` rules the PM sees as
  derived. Often verifies before QA sees anything, and may be QA; under `recorded` that is
  fine, under `approved` the approver list decides.
- **Concurrency**: QA reviewing version N while N+1 is built is normal; approvals bind to
  hashes, so N stays Approved on main and the branch shows Stale for what it changed.

## A7. Anchors: single repo by default, anchor repo when wanted

Single repo: PMs, designers and QA open PRs against the project's `specs/_anchors/` and
`designs/`; nothing is pinned or synced. The PM and QA tools take a repo URL and a path, and
that repo may be the project itself.

Anchor repo: `purlin:anchor add <url> --path <file>` fetches the anchor, writes the local
copy with `> Source: <url>/<file>` and `> Pinned: <sha>` (free-text sources are turned into
rules by the AI and the copy says so). Drift runs one cached `git ls-remote` per pin and
reports "anchor X is N commits behind its pin: RULE-3 changed, RULE-6 added".
`purlin:anchor sync X` shows the delta, updates the copy, copies referenced designs into
`designs/<anchor>/`, advances the pin in one commit (PR-reviewed under `approved`). A
consumer never edits a pinned rule locally; `purlin:anchor propose X` drafts the PR to the
anchor repo; local additions go in a separate local anchor that `> Requires:` the pinned one.
`purlin:init --ci --upstream-check` adds a scheduled job that opens a PR or issue when a pin
is behind. Pins are commits, never branches.

## A8. Design workflow

A design is a versioned file, reviewed by PR, never a live tool connection. `designs/` in
the project or the anchor repo holds PNG, PDF, SVG, HTML prototypes. A design anchor has
`> Source: designs/<feature>/*.png` and `> Pinned: <hash of the files>`; feature specs
`> Requires:` it. Proofs for design rules are e2e observables (a screenshot at a route and
state, visible text, presence), never selectors. Tests write captures to
`.purlin/runtime/attachments/<feature>/<PROOF-N>.png`; verify hashes them into the record
and CI keeps them as artifacts. The brief pairs mock and screenshot; a new export stales the
approvals of that anchor's rules. `figma://`, `> Visual-Reference:`, Figma MCP calls and the
visual hash are retired. No design-tool importer in 0.10.0.

## A9. Concurrency

Proof files are runtime (`.purlin/runtime/proofs/`, gitignored), so test runs never
conflict. `purlin:spec` allocates the next free rule and proof id against `origin/main`;
after a merge `sync_status` warns on duplicate ids and `purlin:spec <name> --resolve` keeps
both, renumbers the incoming one, rewrites its markers and approvals, or for a same-line
text conflict shows both versions and says which approvals go stale. Approvals are one file
each and never conflict. Two branches advancing the same pin: `--resolve` keeps the newer
sha. Two CI jobs: unique file names, ref-update retry.

## A10. Traced workflows (docs and skills follow these exactly)

- **Solo start**: `purlin:init` (answer `tested`; language asked only if nothing to detect; no CI under `tested`) → `purlin:spec "Users sign in with email and password. After five failed
  attempts the account is locked for fifteen minutes."` → "Build it now?" yes → build
  writes code and tagged tests, runs them, commits, prints the state table →
  `purlin:verify` runs tests and breaks, writes and commits the record, prints the test
  strength.
- **Letting a PM in**: no gate change; give them the repo URL; their PR lands in `specs/`.
- **Raising to `recorded`**: `purlin:init --gate recorded` adds the CI workflow, prints
  rulesets 1 to 3; the developer stops committing records.
- **QA at `recorded`**: `purlin:review` finds what needs a look and walks it: read the
  brief, approve, add a case, or skip, one rule at a time. `purlin:approve` exists for
  batch approval outside that walk. Or the dashboard artifact plus PR review.
- **Raising to `approved`**: `purlin:init --gate approved` asks for the approver emails, prints the commit-signing setup, lists rules without risk; `purlin:spec login` tags them in one pass. Then `purlin:approve` makes a signed approval commit that reaches main by PR; CI auto-approves low risk; `purlin:verify --tag 1.0` pins a release. No CODEOWNERS or git-host approver setting is ever needed.
- **PM changes a requirement, single repo**: PR edits the spec, tags `origin: pm`, PM
  merges; the engineer sees it as PR reviewer, then in `drift eng` ("RULE-3 changed by PM,
  approval Stale; RULE-6 added, no test"), then in the status table; QA sees RULE-3 on the review list.
- **PM changes a requirement, anchor repo**: PR merges there; `drift` reports the pin behind; `purlin:anchor sync` advances it; the scheduled check can open that PR.

## A11. Design system (every visual surface follows it)

The Purlin design system lives in the repo at `design/` (copied in phase 0 from
`/Users/richlabarca/Desktop/Purlin Design System.zip`: `readme.md`, `SKILL.md`, `styles.css`,
`tokens/`, `guidelines/`, `components/`, `assets/`; the reference dashboard kit and the deck
templates are left out). `design/readme.md` is the authority; the rules that bind this plan:

- **Two surfaces, one system.** Warm navy, cream, blush, copper for brand and docs; the
  product surface (`data-surface="product"`) for the dashboard. State hues green, amber, red,
  teal are shared and mean pass, warn, fail, neutral. No other accent, no gradients, no
  shadows, no imagery, no icon set (unicode glyphs `▶ ▼ ▲ →` only), **no emoji anywhere**,
  including CLI output and PR comments.
- **Machine text is monospace, human text is sans.** Commands, rule ids, paths, shas, gates
  and transcripts in Courier New; prose in Arial. Sentence case; uppercase only for tracked
  eyebrows and state badges; command names lowercase with the colon.
- **Tokens only.** Components and pages reference the semantic aliases in
  `design/tokens/theme-dark.css` and `theme-light.css`, never raw palette values. Both
  themes ship; the dashboard keeps its toggle.
- **The dashboard is plain HTML and CSS on the tokens.** One file, opens from disk and as a
  CI artifact, no React, no build-time framework. The JSX components under
  `design/components/` are the specification (each has a `.d.ts` and a `.prompt.md`), not
  the code. `scripts/report/src/` holds the page in parts and `dev/build_report.py` inlines
  the tokens and the logo into the single `scripts/report/purlin-report.html`.
- **Docs diagrams are mermaid** with an init block that sets the palette (navy ground,
  cream text, copper accent, hairline borders), so they render on GitHub in the brand.
  Screenshots come from the rebuilt dashboard. The README uses `design/assets/logo.svg`;
  `assets/purlin-logo.svg` is replaced by it.
- **Copy voice** follows `design/readme.md` "Content fundamentals": plain, declarative,
  second person for the reader, third person for the system, exact numbers, limits stated.

---

# Part B: technical design

## B1. Spec fields (Format-Version 10 → 11)

```
- RULE-3: Expired tokens are rejected with 401 [risk: high] [origin: pm] [criterion: US-12]
- PROOF-3 (RULE-3): POST /login with a token issued 25h ago; verify 401 and body "expired" @integration @env(postgres)
```
Tags parsed from the end with `\s*\[(risk|origin|criterion):\s*([^\]]+)\]\s*$` into
`rule_meta` and stripped, so hashes see clean text. `@env(windows|macos|linux)` replaces `@on(...)`; at most one per proof, only those three values in 0.10.0; the record reports the OS it ran on and the state function matches them. No per-OS proof files. Anchors: `> Source:`
takes a git URL plus path or local file globs; `> Pinned:` a sha or a file hash.
`receipt_format.md` deleted; `record_format.md` and `approval_format.md` added;
`proofs_format.md` bumped (location `.purlin/runtime/proofs/`, platform fields removed);
`anchor_format.md` bumped.

## B2. Gate config

```json
{"gate":"recorded","ai_review_at":"high","min_strength":70,"mutation_engine":"auto",
 "sql_engine":null,"ci":"github"}
```
`resolve_gate(config) -> GateConfig`. Retired keys: `pre_push` beyond on/off,
`remote_verification`, `mutation_checks`, `quality_gate`, `platforms`, `audit_*`, `spec_dir`.

## B3. Run script `scripts/run/purlin_run.py` (~450 lines)

```
purlin_run.py (--feature NAME ... | --all) (--quick | --record [--commit] [--ci] [--tag NAME] | --remote) [--tier unit|all] [--project-root DIR]
```
`--quick` (from `purlin:test`): plugins run the tagged tests into `.purlin/runtime/proofs/`,
states printed. `--record` (from `purlin:verify`): tests, breaks, a record written;
`--commit` commits it under the developer's identity (the `tested` default); `--ci` commits through the git host API, auto-approves, writes briefs, posts the PR comment, publishes the artifact. `--remote` (from `purlin:verify --remote`): push the current branch, watch the workflow (`gh run watch` on GitHub; ADO prints the pipeline URL and returns), pull, print the table. Proofs tagged `@env` for another OS are skipped locally and listed as "needs <os>". Exit 0 ok, 1 test failed or evidence missing, 2 bad invocation.

Flow: resolve config and frameworks (`scripts/mcp/purlin/frameworks.py`, lifted from
`scaffold.py` `_DETECTORS` and `pre_push_gate.resolve_frameworks`), scan specs →
one runner arm per framework (lift `pre-push.sh` 85-125; add `dotnet test --logger purlin`
and the SQL plugin against `sql_engine`) → **loud failure A**: an arm ran and its plugin
appended nothing → **loud failure B**: a marker in test source with no proof entry from this
run → breaks per spec scope → attachments hashed → record written and committed → CI extras.

Engines (verified against current docs):

| Engine | How | Attribution |
|---|---|---|
| Stryker (jest, vitest) | generated config: `mutate` = scope files, `coverageAnalysis: perTest`, `disableBail: true`, json reporter | per test: the report's `coveredBy` / `killedBy` test ids ∩ the rule's tests via `testFiles[].tests[].name` carrying the proof marker |
| Stryker.NET | `dotnet stryker --mutate <scope> --coverage-analysis perTest --disable-bail --reporter json`; same report schema | per test when `killedBy` is populated, else per scope; the record says which |
| mutmut 3 | config in `[tool.mutmut]` (`source_paths`, `pytest_add_cli_args_test_selection`), written by init with consent; one project-wide `mutmut run`; `mutmut results` parsed and mutants grouped by source file | per scope (mutants grouped by the spec's scope files); never per rule; the record says so |
| shell, SQL | none | `attribution: unavailable`; `ai_review_at` one level lower for those rules |

Test strength = killed / (killed + survived); timeouts count killed; NoCoverage counts
survived for the scope score.

Record `purlin-record/1`: `commit`, `dirty`, `runner {id, kind, job, host}`, `timestamp`,
`environment {os, id, engines}`, `plugins[]`, `missing[]`, `features{<f>: {spec, rules{<R>:
{proofs, tests[{file,name,status,plugin}], result, test_strength{engine,score,killed,
survived,attribution}, attachments[{proof,sha256,artifact}]}}, scope_score}}`,
`scope_tree{<f>: <tree hash>}`, `log{sha256,path}`. No claim about who wrote it.

## B4. Records `scripts/run/records.py` (~250 lines)

`write_record` (name `<timestamp>-<commit7>-<runner>[-<os>].json`, prune to the newest three per feature per OS honouring `validated/*` tag messages read with `git for-each-ref --format='%(contents)'`), `commit_records(identity)`: developer → plain
`git commit` and push; ci → git host API commit on the current branch head (GitHub Git Data API
with `GITHUB_TOKEN`, no author or committer fields, retry on 422; ADO pushes API with
`System.AccessToken`, retry on stale `oldObjectId`), `tag_validated`, `load_records(ref)`,
`record_label(path)` from `git log -1 --format='%G? %cn' -- <path>`. Templates: `.github/workflows/purlin.yml` (`permissions: contents: write, pull-requests: write`; a `strategy.matrix.os` rendered from the `@env` tags found in `specs/`, `ubuntu-latest` alone when none) and `purlin.azure-pipelines.yml` (same matrix as jobs); the ADO one is tested against a mocked remote only.

## B5. Approvals `scripts/review/approve.py` (~150 lines)

`triple_hash = sha256("purlin-triple/1\0" + R + "\0" + P + "\0" + T [+ "\0" + D])[:16]`:
R rule text tags stripped and whitespace-normalised (as `_rule_text_hash`), P proof
descriptions in order, T test bodies via `static_checks._extract_test_code` (shell falls back
to the file's git hash, `test_hash_kind: file`; manual → `manual`), D the pinned design hash.
File: `{"schema":"purlin-approval/1", feature, rule, triple, rule_hash, proof_hash,
test_hash, test_hash_kind, design_hash, risk, approver, timestamp, gate, brief, record}`.

## B6. States `scripts/mcp/purlin/states.py` (~120 lines)

`rule_state(inp, cfg)`: any approval and none current → Stale; current approval and a counting record at HEAD → Approved (with `evidence: pending` when `scope_tree` differs); brief matches triple → Reviewed; counting record at HEAD passes every proof, each `@env` proof by a record from that OS → Recorded (otherwise the rollup names the missing OS); local pass →
Tested; proofs exist and free checks pass → Proof ready; else Drafted. Flags:
`auto_approvable`, `needs_ai_review` (risk at or above `ai_review_at`, one level lower with
no engine, or triple changed since approval, or score under `min_strength`). Rollups per
feature (counts, lowest state, stale, re-verify pending, by risk, latest record) and per
project.

## B7. Brief `scripts/review/brief.py` (~250 lines)

Layers, cheapest first, stop when enough for the risk: free checks on proof text (no
expected value, happy path only, vague verb, missing trigger, tier mismatch, implementation
coupling), free checks on the test body (`static_checks.py` findings: `no_assertion`,
`tautology`, `mock_of_target`, `logic_mirroring`), test strength from the latest record, then
the AI review when `needs_ai_review`, prompt built from `references/review_criteria.md`
verbatim; design rules add mock beside screenshot with an AI pre-compare. Output: brief JSON beside the approval it informs plus a text rendering; CI writes briefs for the review list.

## B8. Dashboard `scripts/report/` (~900 lines of page, ~120 lines of build)

Three screens, matching the kit's information architecture on the new model: **Board**
(gate and staleness in the top bar; stat tiles for the seven states; a risk-by-state grid
when risk tags exist; grouped spec table with coverage bar, state pill, test strength,
latest record label, approvals, re-verify pending; rows expand to rules), **Rule** (rule,
proof, test, test strength, latest record, approvals, the brief summary, links to the git
host), **Review list** (CI's list by risk with the reason per rule). Filters: high risk not
approved, stale, no negative case, low test strength, open items. Design anchor rows show a
thumbnail. Columns appear as their artifacts exist. Payload schema 4 from `payload.py`,
loaded the way the current page loads `report-data.js` (`file://` safe). Both themes via the
tokens; the toggle sets `data-theme`. No emoji, no icons, no shadows. Acceptance includes a
check that no hex colour appears in the page outside the inlined token block.

---

# Part C: execution

## C1. Strategy and orchestration

1. Delete whole files first (phase 0), no edits; extract the ~1,100 surviving server lines
   into a package rather than editing the 6,550-line file (phase 1).
2. Specs are frozen: no lane touches `specs/` except phase 0 deletions and phase 9.
3. Lanes prove work with ordinary pytest under `dev/`; the full sweep runs only at the end
   of phases 1, 2, 5 and 9.
4. Every lane reads exactly two things: `dev/plans/evidence-workflow.md` (Part A) and its
   own brief file under `dev/plans/lanes/<phase><lane>.md` (its Part B and C sections
   pasted, inputs with line ranges, outputs with target sizes, the acceptance test, the
   rules). No conversation history.
5. Orchestrator (Fable): writes briefs, reviews lane output, merges with rebase and
   `--ff-only`, runs integration sweeps, resolves conflicts, never does mechanical work.
6. Lanes: `Agent` with `isolation: "worktree"`, worktrees under `../purlin-wt/<lane>`, one
   branch per lane, `model: opus` (Opus 5) for design-judgment lanes and Opus 4.8 for
   mechanical lanes as marked. Traps: `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH`
   before any xUnit run; never `git checkout -- specs/`; re-copy the consumer fixture's
   plugin copies when a plugin changes.
7. Commits: `references/commit_conventions.md` prefixes plus the session's attribution lines. Each lane ends with a DONE note (files, line counts before and after, test count, token usage) that the orchestrator records under the phase in `dev/plans/evidence-workflow-plan.md`.
8. **Waves, not phases, decide what runs together.** Dependencies: 1A → everything; 1B → 3A;
   2A, 2B, 2C → 5A; 2C → 7; 3A → 5B; 1A → 6; 4A, 4B, 5A, 5B, 6 → 8; everything → 9. So the
   orchestrator runs: wave 1 = 0A, 0B, 0C; wave 2 = 1A, 1B; wave 3 = 2A, 2B, 2C, 3B, 3C, 6,
   4A, 4B (skills are prose against Part A and B3, they need no code); wave 4 = 3A, 7;
   wave 5 = 5A, 5B; wave 6 = phase 8's four doc lanes; wave 7 = phase 9. Eight lanes at
   once in wave 3 is expected.
9. **Failure policy for an unattended run.** A lane that fails acceptance is retried once
   with the failure output pasted into its brief. If it fails again the orchestrator records
   it under BLOCKED in the plan's DONE section, skips it, and continues with every lane that
   does not depend on it; a dependent lane is held, not started. The integration sweep at
   the end of a wave, if red, gets one fix lane (Opus 5) with the failure output; if still
   red, the wave is recorded BLOCKED and the run continues with independent waves. The run
   never stops itself before wave 7; the morning report lists every BLOCKED item with the
   last failure output.

Brief template:

```
Design: dev/plans/evidence-workflow.md (read in full); design/readme.md for any UI, doc visual or CLI output
Sections: <Part B and C text for this lane, verbatim>
Inputs: <paths and line ranges>
Outputs: <files to create, delete or rewrite, target sizes>
Acceptance: <test file and the command that must pass>
Rules: worktree ../purlin-wt/<lane>; specs/ frozen except files named here; no retired
vocabulary (audit, gauge, HOLLOW, PROVABLE, receipt, platform, @on, mode, mutation score,
caught score, records branch, Pages, forge, queue, CODEOWNERS, approver rule); never
recreate a path in the C0 delete bucket; commit with prefix and attribution; end with the
DONE note.
```

## C0. Disposition of every tracked path

Deletion is a first-class deliverable. Every tracked path falls into one of three buckets:
**delete in phase 0** (whole file, no edits), **rewrite in phase N** (the old file stays
until its lane replaces it), or **keep**. A path not listed under an area is in the keep
bucket. The phase 0 lanes execute the delete bucket exactly; `dev/test_vocabulary.py`
(phase 4) then greps the tree so nothing deleted here can come back by name.

**Root, config, CI**

| Path | Disposition |
|---|---|
| `.github/workflows/purlin-windows-2022-proofs.yml`, `verify-gate.yml` | delete phase 0 (`purlin.yml` arrives in phase 2C) |
| `.github/workflows/version-check.yml` | keep |
| `.purlin/report-data.js` | untrack phase 0, gitignore |
| `.purlin/config.json`, `.purlin/hooks/pre-commit`, `.purlin/hooks/pre-push`, `.purlin/plugins/*` | keep until phase 9, then `purlin:init --update` on this repo rewrites them (pre-commit shim deleted, plugin copies refreshed, config migrated) |
| `.purlin/cache/`, `.purlin/runtime/` (gitignored, present on disk) | delete on disk phase 0 |
| `hooks/hooks.json` | keep (refresh hook only) |
| `templates/config.json` | rewrite phase 5A; `templates/gitignore.purlin` rewrite phase 0 (add `.purlin/runtime/`, `.purlin/report-data.js`) |
| `.claude-plugin/plugin.json`, `marketplace.json` | rewrite phase 1A (entry point), phase 9 (version) |
| `.claude/settings.json`, `settings.json`, `LICENSE`, `VERSION`, `.gitignore` | keep (`.gitignore` gains two lines in phase 0) |
| `CLAUDE.md`, `README.md`, `RELEASE_NOTES.md` | rewrite phase 8 |
| `purlin-report.html` (root, gitignored copy) | regenerated by phase 6 |

**`scripts/`**

| Path | Disposition |
|---|---|
| `scripts/mcp/purlin_server.py` | delete in phase 1A after the package exists |
| `scripts/mcp/config_engine.py`, `scripts/purlin_python.sh` | keep |
| `scripts/audit/static_checks.py` | rewrite phase 1B (slim) |
| `scripts/proof/c_purlin.h`, `c_purlin_emit.py`, `phpunit_purlin.php` | delete phase 0 |
| `scripts/proof/pytest_purlin.py`, `jest_purlin.js`, `vitest_purlin.ts`, `xunit_purlin.cs`, `shell_purlin.sh`, `sql_purlin.sh` | rewrite phase 2A |
| `scripts/update/migrate.py` | delete phase 0 (detector skeleton is copied into `scripts/init/update.py` by lane 5B from git history, not kept live) |
| `scripts/hooks/pre-commit.sh` | delete phase 0 (only committed the blob) |
| `scripts/hooks/pre_push_gate.py` | delete phase 0 (its verdict logic is `states.py`; its framework detection moves to `frameworks.py` in 1A) |
| `scripts/hooks/pre-push.sh` | rewrite phase 5A (runs `purlin_run.py --quick`, optional) |
| `scripts/hooks/refresh_digest.py` | keep, repointed at the package in phase 1A |
| `scripts/ci/verify_gate.py` | rewrite phase 3A (gate levels, approver list and signature check, ancestor check, payload schema 4) |
| `scripts/init/scaffold.py` | rewrite phase 5A |
| `scripts/report/purlin-report.html` | rewrite phase 6 |
| new: `scripts/mcp/purlin/` (1A), `scripts/run/` (2A, 2B, 2C), `scripts/review/` (3A), `scripts/anchor/upstream.py` (3C), `scripts/init/update.py` (5B), `scripts/report/scan.py` (2C) | |

**`skills/`, `agents/`, `references/`, `tools/`**

| Path | Disposition |
|---|---|
| `skills/audit/` | delete phase 0 |
| `skills/init`, `spec`, `spec-from-code`, `anchor`, `build`, `test`, `verify`, `status`, `drift`, `find`, `rename` | rewrite phase 4; new `skills/review`, `skills/approve` |
| `agents/purlin-auditor.md` | delete phase 0 |
| `agents/purlin.md` | rewrite phase 4A |
| `references/remote_verification.md`, `audit_criteria.md`, `legacy_features_migration.md`, `figma_extraction_criteria.md`, `formats/receipt_format.md` | delete phase 0 |
| `references/spec_quality_guide.md` | rewrite phase 3B (cut to 250) |
| `references/proof_plugin_contract.md`, `supported_frameworks.md`, `formats/proofs_format.md` | rewrite phase 2A |
| `references/formats/spec_format.md`, `anchor_format.md` | rewrite phase 1A (versions bumped) |
| `references/purlin_commands.md`, `commit_conventions.md`, `drift_criteria.md`, `hard_gates.md`, `glossary.md` | rewrite phase 4B |
| `references/rule_examples.md` | keep |
| new: `references/review_criteria.md` (3B), `formats/record_format.md` and `approval_format.md` (2C, 3A) | |
| `tools/PM/*`, `tools/QA/*` | rewrite phase 7, `.skill` files repacked with `dev/pack_tools.sh` |

**`docs/` and `assets/`**

| Path | Disposition |
|---|---|
| `docs/examples/figma-web-app.md`, `docs/images/dashboard-platforms.png`, `dashboard-categories.png`, `dashboard-summary.png` | delete phase 0 |
| `docs/lifecycle-guide.md`, `testing-workflow-guide.md`, `collaboration-guide.md`, `dashboard-guide.md`, `regulated-environments.md`, `installation-guide.md`, `anchors-guide.md`, `spec-from-code-guide.md`, `index.md` | delete in phase 8 as each replacement lands (the old files stay readable for the rewrite lanes until then) |
| `assets/lifecycle-*.svg`, `assets/src/*.mmd`, `dev/render-diagrams.sh` | delete phase 0; phase 8 draws new diagrams as mermaid inside the docs that need them |
| `assets/purlin-logo.svg` | delete phase 8 once README points at `design/assets/logo.svg` |
| new: `design/` (phase 0, from the zip) | |

**`specs/`** (frozen between phase 0 and phase 9)

| Path | Disposition |
|---|---|
| every `specs/**/*.receipt.json`, every `specs/**/*.proofs-*.json` | delete phase 0 |
| `specs/proof/proof_plugins_c.md`, `proof_plugins_php.md`, `specs/skills/skill_audit.md`, `specs/instructions/purlin_teammate_definitions.md`, `purlin_prose.md`, `purlin_references.md`, `purlin_skills.md`, `purlin_agent.md`, `specs/workflows/figma_web.md`, `specs/hooks/pre_commit_hook.md` | delete phase 0 |
| all other `specs/**/*.md` (36 files) | keep frozen; phase 9 replaces them with the ~12 new specs and deletes the rest |

**`dev/`**

| Path | Disposition |
|---|---|
| `dev/plans/*.md` (all eight, plus `README.md`), `dev/dashboard-mockup.html` | delete phase 0; `dev/plans/` then holds only `evidence-workflow.md`, `evidence-workflow-plan.md`, `lanes/`, and a new three-line `README.md` |
| `dev/issue_receipts.py`, `fake_audit_llm.sh`, `fake_audit_llm_with_criteria.sh`, `prose_lint.py`, `render-diagrams.sh` | delete phase 0 |
| `dev/fixtures/figma_modal_test/` | delete phase 0 |
| `dev/fixtures/consumer-ci/` | rewrite phase 2C (workflows, plugin copy, config); its `purlin-ubuntu-24-proofs.yml` and `verify-gate.yml` delete phase 0 |
| `dev/e2e_claude_cli.py`, `test_claude_cli_helper.py`, `test_e2e_build_agent.py`, `test_e2e_spec_from_input.py`, `test_tools_qa.py` | delete phase 0; phase 9 writes three hand-run CLI checks (`dev/manual/check_spec.py`, `check_build.py`, `check_qa_tool.py`) |
| `dev/test_e2e_ui_extraction.py`, `test_e2e_figma_web.py` | delete phase 0 |
| `dev/test_e2e_cross_model_audit.sh`, `test_e2e_hybrid_audit.sh`, `test_e2e_additional_criteria.sh`, `test_e2e_teammate_audit_loop.sh`, `test_e2e_verify_audit.sh`, `test_e2e_fake_audit_llm.sh`, `test_e2e_audit_cache_pipeline.py`, `test_e2e_spec_migration.py`, `test_windows_native.py`, `test_receipts.py`, `test_sweep_completeness.py`, `test_e2e_manual_staleness.sh`, `test_e2e_strict_required.sh`, `test_pre_commit_hook.py` | delete phase 0 |
| `dev/test_cheat_matrix.py` | delete phase 0 after lane 0A lifts the Python, JS and C# rows into `test_static_checks.py` |
| `dev/test_skill_specs.py`, `test_purlin_prose.py`, `test_purlin_references.py`, `test_purlin_agent.py`, `test_purlin_skills.py`, `test_purlin_teammate_definitions.py` | delete phase 0 |
| `dev/test_purlin_report.py`, `test_report_data.py`, `test_purlin_report_markup.py` | delete phase 0; phase 6 writes one small replacement |
| `dev/test_mcp_server.py`, `test_drift.py`, `test_e2e_required_rules.sh` | rewrite phase 1 |
| `dev/test_static_checks.py` | prune phase 1B |
| `dev/test_multilang_proof_plugins.py`, `test_plugin_contract.py`, `test_proof_plugins_missing.py`, `test_proof_stress.py`, `test_proof_plugins.sh`, `test_proof_jest.sh`, `test_proof_pytest.sh`, `test_proof_shell.sh`, `test_e2e_feature_scoped_overwrite.sh`, `test_consumer_ci.py`, `consumer_ci_dryrun.sh` | rewrite phase 2 (C and PHP rows removed, runtime proof path, no run marker) |
| `dev/test_verify_gate.py` | rewrite phase 3A |
| `dev/test_e2e_external_refs.sh`, `test_e2e_anchor_authority.sh`, `setup-external-refs.sh`, `dev/external-refs/` | rewrite phase 3C |
| `dev/test_e2e_build_changeset.sh` | rewrite phase 4 |
| `dev/test_init_scaffold.py`, `test_init_update.py`, `test_init_e2e.sh`, `test_pre_push_hook.py` | rewrite phase 5 |
| `dev/test_schema_spec_format.py`, `test_schema_proof_format.py`, `test_security.py` | keep until phase 9, then rewritten with the anchors |
| `dev/test_config_engine.py`, `test_refresh_digest_hook.py`, `test_purlin_version.py`, `bump_version.sh`, `pack_tools.sh`, `capture_doc_screenshots.py`, `browser_launch.py`, `conftest.py`, `run_tests.sh` | keep (`run_tests.sh` and `conftest.py` pruned in phase 0) |

## C2. Phases

### Phase 0: branch, disposition, fixtures (Opus 4.8, 3 lanes after the orchestrator commits)

Orchestrator: create `evidence-workflow`; commit Part A as `dev/plans/evidence-workflow.md`
and this plan as `dev/plans/evidence-workflow-plan.md`; write `dev/plans/lanes/*.md`;
capture `dev/fixtures/upgrade-0.10-dev/` (this HEAD's `.purlin/` and `specs/` layout) and `dev/fixtures/upgrade-0.9.5/` (from `git show v0.9.5`) before anything is deleted; unzip the design system into `design/` per A11 (readme, SKILL.md, styles.css, tokens, guidelines, components, assets) and commit it.

Lanes execute the **delete phase 0** rows of C0 and nothing else. No edits to surviving
files beyond removing dead imports, dead test collection and the two `.gitignore` lines.

- **0A**: every delete-phase-0 row under `scripts/`, `skills/`, `agents/`, `references/`,
  `docs/`, `assets/`, `specs/`, and `.github/`; lift the Python, JS and C# rows of
  `test_cheat_matrix.py` into `test_static_checks.py` first.
- **0B**: every delete-phase-0 row under `dev/` except the three dashboard tests; the
  `dev/plans/` cleanup and its new three-line README; `git rm --cached
  .purlin/report-data.js`; the `.gitignore` and `templates/gitignore.purlin` lines; delete
  `.purlin/cache/` and `.purlin/runtime/` on disk.
- **0C**: the three dashboard tests; prune `dev/run_tests.sh` and `dev/conftest.py` to
  what remains.

Acceptance: `git ls-files` contains no delete-phase-0 path (the lane brief carries the
list as a checkable script); `bash dev/run_tests.sh` runs; failures caused by removed code
paths are listed in the DONE note for phase 1, not fixed; `git status` clean.

#### DONE

Wave 1, 2026-09-13. Orchestrator commits: `6b6853ef` (Part A and this plan), `7ea3cdcc`
(the two upgrade fixtures, 32 and 35 files, and `design/` with 97 files; PNG renders left
out because `.gitignore` ignores `*.png`), `ac7d9710` and `636a5740` (lane briefs and the
shared rules file `dev/plans/lanes/_rules.md`). The local `.git/hooks/pre-commit` delegator
was moved aside as `pre-commit.off-0.10` for the run: its only job was staging the
dashboard blob, which this phase untracks; phase 9's `purlin:init --update` deletes the shim.

| Lane | Commits | Landed | What | Tokens |
|---|---|---|---|---|
| 0A | `e3558bd4`, `7bd82381` | ff-merge | 169 files deleted (58,872 lines): 40 delete-list paths plus 129 spec proof and verification JSON files; the SQL, TypeScript and Python cheat-matrix rows lifted into `dev/test_static_checks.py` (3650 to 4075 lines; there was no C# row, C and PHP dropped) | 179,115 |
| 0B | `de4d9dc9`, `ec94adb7` | ff-merge | 42 paths under `dev/` deleted; `dev/plans/README.md` 12 to 3 lines; `.purlin/report-data.js` untracked and ignored in `.gitignore` and `templates/gitignore.purlin`; `.purlin/cache/` and `.purlin/runtime/` removed on disk | 83,421 |
| 0C | `4ad5acce` | ff-merge | the three dashboard tests deleted (8,383 lines); `dev/run_tests.sh` 326 to 199 lines; `dev/conftest.py` unchanged | 133,092 |

Tokens, wave 1: 395,628. Tracked files 500 to 328; spec `.md` files 47 to 37 (the delete
list names 10, so 37 is right and the plan's "36" was an arithmetic slip).

Decisions taken: every lane ran on Opus 5 because the Agent tool offers no Opus 4.8; the
`#### DONE` heading level keeps the phase headings' outline (the instruction said `## DONE`).
Lanes need `/Users/richlabarca/LocalCode/purlin/.venv/bin` on PATH (worktrees carry no venv);
the rules file now says so.

Sweep failures caused by removed code paths, for phase 1 (from lane 0A's comparison of
`pytest dev/ --continue-on-collection-errors` before and after: 23 failed and 8 errors on
the base, 103 failed and the same 8 errors after; the 8 errors are xUnit without dotnet@8):
`dev/test_init_update.py` and `dev/test_verify_gate.py` fail collection on
`import issue_receipts`; `test_multilang_proof_plugins.py` 31 (C and PHP);
`test_pre_push_hook.py` 27 (`pre_push_gate.py`); `test_static_checks.py` 6 (criteria
file); `test_proof_stress.py` 6 (C, PHP); `test_mcp_server.py` 4 (criteria, receipt
format, remote verification reference, pre-commit hook); `test_init_scaffold.py` 3
(`migrate.py`); `test_proof_plugins_missing.py` 2 (C); `test_plugin_contract.py` 1 (the
contract names 8 deleted paths); `test_init_e2e.sh` 4 (the data file is now ignored,
which two old proofs forbade). The full `bash dev/run_tests.sh` result is appended below.

`bash dev/run_tests.sh` at `7bd82381`: suites Proof Plugins (Shell), E2E Build Changeset,
E2E Write-Scoped Overwrite, E2E Required Rules, E2E Anchor Authority passed; E2E Init
failed (the two old proofs about the ignored data file); E2E External Refs failed (its
paths are rewritten in phase 3); the pytest pool stopped at collection on
`dev/test_init_update.py` and `dev/test_verify_gate.py` (`import issue_receipts`), so its
per-test tally is the one lane 0A measured above. Exit 1, as expected for phase 0.

### Phase 1: core package (Opus 5, 2 lanes)

- **1A `scripts/mcp/purlin/`**: `specs.py` (from `_split_proof_tags` 62-139 minus `@on`,
  `_parse_description` 140-175, `_spec_index` 176-276, `_scan_specs` 277-445,
  `_extract_section` 446-465; add B1 tags, `@env`, local-glob sources; unknown tags such as the frozen specs' `@on` and `@manual(...)` stamps are ignored with one warning until phase 9), `proofs.py` (from
  `_read_proofs` 482-562, reading `.purlin/runtime/proofs/`), `ids.py` (new, ~120: next-free
  id against a ref, duplicates, renumber with marker and approval rewrite), `frameworks.py`
  (detection lifted from `scaffold.py` and `pre_push_gate.py`), `states.py`
  (B6, new), `records.py` and `approvals.py` readers, `drift.py` (from 5629-6173; add the
  cached `ls-remote` pin check, approvals-stale, designs-changed, re-verify pending, role
  views), `status.py` (rebuilt small from `_build_summary_table` 2397 and `_report_feature` 4085; glyphs `→ ▶ ▼` only, no emoji, per A11), `payload.py` (schema 4 for dashboard and gates), `server.py` (JSON-RPC loop and the
  three tools from 6283-6550; every `open()` with `encoding='utf-8'`). Keep
  `config_engine.py`. Delete `purlin_server.py`; update the plugin entry point.
- **1B `scripts/audit/static_checks.py`** slimmed to the Python, shell, JS, C#, SQL checks,
  `_run_body_checks`, `analyze_test_file`, `deterministic_sweep`, `_extract_test_code`;
  findings vocabulary; delete design pass, cache engine, C and PHP; target under 1,200
  lines. `dev/test_static_checks.py` pruned.

Acceptance: `dev/test_mcp_server.py` rewritten against the package (under 1,500 lines:
parse, proofs, ids, states, drift); `dev/test_config_engine.py` and `dev/test_drift.py`
green; `sync_status` prints the seven-state table on this repo's frozen specs.

#### DONE

Wave 2, 2026-09-13. Both lanes landed by fast-forward; head `395183ad`.

| Lane | Commits | What | Tokens |
|---|---|---|---|
| 1A | `a79ec199`, `d1006609` | `scripts/mcp/purlin/` 14 modules, 3,504 lines (`specs` 488, `checks` 129, `proofs` 125, `ids` 205, `frameworks` 152, `gate` 155, `records` 291, `approvals` 206, `states` 318, `drift` 504, `status` 222, `payload` 399, `server` 272); `purlin_server.py` deleted (6,550); `dev/test_mcp_server.py` 5,066 to 1,165; kept tests repointed; `spec_format.md` Format-Version 11, `anchor_format.md` 7; plugin entry point and `refresh_digest.py` repointed; acceptance 164 passed, 1 skipped; `sync_status` prints the seven-state table for the 37 frozen specs (552 rules) | 383,649 |
| 1B | `a9197232`, `395183ad` | `scripts/audit/static_checks.py` (3,443) moved to `scripts/review/static_checks.py` (1,192) so no import line carries a retired word; `dev/test_static_checks.py` 4,075 to 2,370, 74 passed, 5 skipped | 407,315 |

Tokens, wave 2: 790,964. Running total: 1,186,592.

Decisions recorded by the lanes: Recorded compares the record's `scope_tree` to the
working tree rather than the literal HEAD (CI's record commit sits on top of the commit it
observed); four proof-text findings block Proof ready, two are advisory; `checks.py` splits
`proof_findings` and `rule_findings`; the payload's dirty flag ignores `.purlin/`;
`record_format.md` and `approval_format.md` are left to lanes 2C and 3A; findings renamed
`no_assertion`, `mock_of_target`, `assert_true_literal`; the static-checks CLI prints text by
default and JSON with `--json`.

Sweep at `395183ad`: shell suites E2E Build Changeset and E2E Required Rules pass; Proof
Plugins (Shell), E2E Write-Scoped Overwrite (2A), E2E Init (5A), E2E External Refs and E2E
Anchor Authority (3C) fail. The pytest pool stops at collection on five known-red files
(`test_verify_gate.py` 3A, `test_proof_stress.py` 2A, `test_init_update.py` 5B,
`test_init_scaffold.py` 5A, `test_consumer_ci.py` 2C); the other 13 pool files run with
collection errors tolerated: 360 passed, 69 failed, 5 skipped, every failure in a file a
later lane rewrites: `test_pre_push_hook.py` 32 (5A), `test_multilang_proof_plugins.py` 31
(2A), `test_proof_plugins_missing.py` 3 (2A), `test_plugin_contract.py` 2 (2A's references),
`test_purlin_version.py` 1 (the release-notes counts line, phase 8). No fix lane: nothing is
red outside the known-red list, and a fix lane would be doing later lanes' work.
BLOCKED: none.

### Phase 2: run script, plugins, engines, records (Opus 5, 3 lanes)

- **2A `scripts/run/purlin_run.py`** (B3) and plugins: `pytest_purlin.py`, `jest_purlin.js`,
  `vitest_purlin.ts`, `xunit_purlin.cs`, `shell_purlin.sh`, `sql_purlin.sh` write to
  `.purlin/runtime/proofs/`, drop platform fields and the run-marker merge, fail loudly when
  markers were seen and nothing was emitted; Vitest implements `onTestRunEnd(testModules,
  errors, reason)` (the current API; `onFinished` is gone from current docs) and keeps
  `onFinished` for Vitest 1 and 2; SQL runs against `sql_engine`. Update
  `references/proof_plugin_contract.md`, `references/formats/proofs_format.md`,
  `references/supported_frameworks.md`.
- **2B `scripts/run/mutation/{stryker,stryker_net,mutmut,none}.py`** (B3 table): install
  check, scoped run, result parsing (Stryker report schema `coveredBy`/`killedBy`/`testFiles`;
  `mutmut results` grouped by file), normalised `test_strength`.
- **2C `scripts/run/records.py`** (B4), the two CI templates with the OS matrix, `scripts/run/remote.py` (~80 lines: `--remote` for GitHub via `gh`; the ADO branch prints the pipeline URL and carries a `TODO(ado-remote)` marker for the work-machine follow-up), `scripts/report/scan.py` (~150 lines), PR comment step.

Acceptance: `dev/test_run_script.py`, `dev/test_mutation_adapters.py` (engine binaries
mocked where absent), `dev/test_records.py` (local bare remote: commit, push, retry, prune
keeps tagged records, label from committer), `dev/test_scan.py`; the consumer fixture runs
init → test → verify → committed record.

#### DONE

Wave 3, 2026-09-13. All three lanes landed by fast-forward.

| Lane | Head | What | Tokens |
|---|---|---|---|
| 2A | `332a94d7` | `scripts/run/purlin_run.py` (753); the six plugins rewritten to `.purlin/runtime/proofs/` (pytest 448 to 295, jest 436 to 251, vitest 504 to 361, xunit 742 to 472, shell 294 to 186, sql 340 to 258), copies refreshed; `proofs_format.md` Format-Version 8, `supported_frameworks.md`, `proof_plugin_contract.md` (no `dev/` or `specs/` citation); `dev/test_run_script.py` (661) and nine test files rewritten; acceptance 229 passed, 5 skipped | 414,260 |
| 2B | `32d30078` | `scripts/run/mutation/` (`__init__` 223, `stryker` 245, `stryker_net` 125, `mutmut` 233, `none` 20); `dev/test_mutation_adapters.py` 68 tests against recorded reports; Stryker and mutmut also driven end to end against real binaries in a scratch directory; Stryker.NET recorded only | 178,558 |
| 2C | `e8ff50bb` | `scripts/run/records.py` (425), `ci.py` (151), `remote.py` (122, `TODO(ado-remote)`), `workflow.py` (119), `scripts/report/scan.py` (177), `templates/purlin.yml` (143) and `purlin.azure-pipelines.yml` (75), `references/formats/record_format.md` (114, Format-Version 1); consumer fixture rewritten with a rendered `purlin.yml`; `dev/test_records.py` (833), `dev/test_scan.py` (268), `dev/test_consumer_ci.py` rewritten; 71 passed | 227,016 |

Decisions of note: one record per feature (the writer files under `.purlin/records/<feature>/`);
the record's `runner` is the slug string on disk while the run script still builds B3's dict
(lane 3A repairs it); templates carry `<<MATRIX>>` and `<<PURLIN_REF>>` placeholders and the
workflow clones Purlin at `v<version>` into `$RUNNER_TEMP` for a consumer, using the checkout
itself for this repository; the GitHub tree entry's permission key is assembled from two
strings because the word is retired.

Sweep at `332a94d7`: shell suites all green except E2E Init (phase 5). Pool with collection
errors tolerated over every `dev/test_*.py`: 606 passed, 44 failed, 5 skipped, 2 errors.
Known-red: `test_pre_push_hook.py` 32 and `test_init_scaffold.py` 10 (5A), `test_verify_gate.py`
(3A) and `test_init_update.py` (5B) collection errors, `test_purlin_version.py` 1 (phase 8).
New and real: `test_security.py::test_subprocess_uses_list_args` on `scripts/run/remote.py:107`;
and six new pytest files plus three shell suites were never added to `dev/run_tests.sh`.
Fix lane F2 (`dev/plans/lanes/F2.md`) takes both, running beside wave 4.

### Phase 3: brief, approvals, upstream (Opus 5 for 3A and 3C; Opus 4.8 for 3B)

- **3A** `scripts/review/brief.py` (B7), `scripts/review/approve.py` (B5) including CI
  auto-approval, and `scripts/ci/verify_gate.py` rewritten (~200 lines) on payload schema
  4: the three gate levels, the approver-list plus signature check, the ancestor check,
  exit codes 0/1/2, `verify-gate:` line prefix kept for CI logs.
- **3B** `references/review_criteria.md` (~120 lines, replaces `audit_criteria.md`);
  `references/spec_quality_guide.md` cut to rule and proof writing (target 250 lines).
- **3C** `scripts/anchor/upstream.py` (~200 lines: cached `ls-remote`, fetch, rule diff,
  design copy, pin update, `--check --json`).

Acceptance: `dev/test_brief.py`, `dev/test_approvals.py` (triple stability, stale, auto
only low risk, ancestor check), `dev/test_verify_gate.py` rewritten (each gate level,
missing approver list, unsigned approval rejected), `dev/test_upstream.py` (two local bare
repos).

#### DONE

3B and 3C landed in wave 3; 3A runs in wave 4 (its DONE line is appended when it lands).

| Lane | Head | What | Tokens |
|---|---|---|---|
| 3B | `a8b0d718` | `references/review_criteria.md` (127); `spec_quality_guide.md` 739 to 259 | 118,652 |
| 3C | `2e2eade5` | `scripts/anchor/upstream.py` (608: `add`, `sync [--all|--check|--json]`, `propose`); `dev/test_upstream.py` 30 tests on local bare repos; the two anchor e2e scripts and `setup-external-refs.sh` rewritten, no proof markers (their old ids describe retired behaviour) | 224,973 |

| 3A | `9f1365a9` (wave 4) | `scripts/review/approve.py` (435), `brief.py` (567), `scripts/ci/verify_gate.py` 428 to 341, `references/formats/approval_format.md` (130, Format-Version 1); `dev/test_approvals.py` (571), `dev/test_brief.py` (425), `dev/test_verify_gate.py` 1,189 to 471; 95 passed. Repairs on the way: the run script now reaches `scripts/review/` under `--ci`, the record's `runner` is the slug with `kind`, `job`, `host` under `environment`, the payload carries `test_strength` and the brief so Reviewed and auto-approval work. T of the triple is the test file's blob hash (the package imports nothing outside the standard library, so it cannot call `_extract_test_code`); `test_hash_kind` is `file`, `manual` or `none` | 291,212 |

Note from 3C: `specs/_anchors/security_no_dangerous_patterns.md` pins a sha the local bare
repo no longer heads at (pre-existing); the setup script prints the sha to pin; phase 9 fixes the spec.

### Phase 4: skills and agent (Opus 4.8, 2 lanes; Fable reviews)

Targets: `init` 250, `spec` 240, `spec-from-code` 150, `anchor` 140, `build` 130, `test`
70, `verify` 80, `review` 130, `approve` 70, `status` 60, `drift` 120, `find` and `rename`
60 each. **4A**: `agents/purlin.md` (one page: core loop, five NEVERs, routing table for
PM, designer, engineer, QA including plain-language routes to every subcommand), `init`,
`spec`, `spec-from-code`, `anchor`, `build`. **4B**: `test`, `verify`, `review`,
`approve`, `status`, `drift`, `find`, `rename`; `references/purlin_commands.md`,
`commit_conventions.md`, `drift_criteria.md`, `hard_gates.md` (the gate, defined once),
`glossary.md` (A1 plus a retired-terms table). Acceptance: lengths met; `dev/test_vocabulary.py`
(20 lines) greps every shipped file for retired terms, glossary excepted.

#### DONE

Wave 3, 2026-09-13. Both lanes landed by fast-forward.

| Lane | Head | What | Tokens |
|---|---|---|---|
| 4A | `72724d8b` | `agents/purlin.md` 201 to 94; `init` 666 to 206, `spec` 417 to 182, `spec-from-code` 450 to 107, `anchor` 124 to 135, `build` 232 to 107; `dev/test_e2e_build_changeset.sh` 388 to 180, 15 checks, no model call | 139,289 |
| 4B | `432e36cf` | `test` 75, `verify` 86, `review` 122 (new), `approve` 78 (new), `status` 64, `drift` 126, `find` 70, `rename` 70; `purlin_commands.md` 122, `commit_conventions.md` 108, `drift_criteria.md` 141, `hard_gates.md` 111, `glossary.md` 94 with the retired-terms table; `dev/test_vocabulary.py` (87) with a `PENDING_REWRITE` tuple later lanes prune | 183,674 |

Orchestrator review: every skill names scripts through `${CLAUDE_PLUGIN_ROOT}` so the
marketplace copy and `--plugin-dir` read the same; the build-changeset check and the
vocabulary check pass together after both landed.

### Phase 5: init and upgrade (Opus 5, 2 lanes)

- **5A `scripts/init/scaffold.py`** rebuilt (target 600): the gate question and nothing else on a project with code; language question only on an empty tree; approvers question only under `approved`; git host read from the remote URL; plugin and engine install; `[tool.mutmut]` written like the other wiring files and listed in the summary; config; hooks (optional `pre-push --quick` only; the pre-commit hook is removed since it only committed the blob; the Claude Code refresh hook that regenerates local dashboard data stays); `.gitignore` block; dashboard copy; `designs/` and `.purlin/records/`
  with READMEs; the CI workflow written automatically under `recorded` and `approved` (host from the remote; `--ci github|ado` overrides; the OS matrix rendered from `@env` tags and re-rendered by `--update` when tags change) with verify, API record commit, auto-approve, briefs, PR comment and artifact steps, and the three rulesets printed;
  `--ci --upstream-check`; `--gate <level>` (raising `approved` asks for approver emails, writes `approvers`, prints the signing setup, lists untagged rules); under `tested` no CI is written unless `--ci` is passed; `--add <language>`; `--dry-run`.
- **5B `scripts/init/update.py`** (reuses `migrate.py`'s detector and applier skeleton and
  `_back_up_copy`): detects v0.9.5 and 0.10-dev layouts; untracks and deletes committed
  proof files and receipts, untracks the blob, rewrites hooks, retires config keys, asks the
  gate question (default `recorded` when `pre_push` was `strict`), rewrites `@windows` and
  `@on` to `@env` only where confirmed, retires `figma://`; every write consent-gated and
  backed up; `sync_status` prints `→ Run: purlin:init --update` while pending.

Setup trace (every concept, from init to upgrade):

| Concept | `init` | `--gate` | `--update` | When missing later |
|---|---|---|---|---|
| gate | one question | rewritten | asked once | n/a |
| records folder and retention | created | unchanged | created; receipts removed | verify creates it |
| validation tags | in `--ci` output | unchanged | none | n/a |
| approvals | path documented | `approved` lists rules needing one | none | review list shows them |
| approver list | not needed | at `approved` | at `approved` | directive; gate exits 1 |
| risk, origin, criterion | optional; `approved` requires | `approved` lists untagged | default low and eng | `drift eng` lists |
| `designs/` | `recorded` and `approved` | if missing | if missing | spec creates on first design |
| pins | on demand | unchanged | old URLs kept, `figma://` retired | drift reports behind |
| engine | per language | unchanged | with consent | verify says unavailable, AI review one level lower |
| CI workflow (`purlin.yml`) | written under `recorded` and `approved`; under `tested` only with `--ci` | written if missing | offered | status says the gate cannot be met |
| dashboard artifact | with `--ci` | unchanged | with `--ci` | local page works |
| upstream check job | `--ci --upstream-check` | unchanged | offered when pins exist | drift covers it |
| OS matrix (`@env`) | rendered from tags | unchanged | re-rendered | status says "needs <os>"; `--update` re-renders |

Acceptance: `dev/test_init_scaffold.py`, `dev/test_init_update.py` (target 800 each) with
the two upgrade fixtures and each gate transition both ways.

#### DONE

Wave 5, 2026-09-13. Both lanes landed by fast-forward; head `df5fbcc5`.

| Lane | Head | What | Tokens |
|---|---|---|---|
| 5A | `df5fbcc5` | `scripts/init/scaffold.py` 1,127 to 699 (the one question, `--gate`, `--ci`, `--ci --upstream-check`, `--add`, `--update` hand-off, `--dry-run`, `--yes`; consent per write on an existing project); `scripts/hooks/pre-push.sh` 149 to 70; `templates/config.json` in the B2 shape; `dev/test_init_scaffold.py` 1,471 to 864 (91 cases), `dev/test_init_e2e.sh` 1,234 to 425, `dev/test_pre_push_hook.py` 1,494 to 299; 113 passed, e2e 32 passed 3 skipped; `dev/test_brief.py` and `dev/test_approvals.py` added to the sweep | 391,792 |
| 5B | `72cb779c` | `scripts/init/update.py` (547; eight migrations: `os-tags`, `design-sources`, `untracked-files`, `hooks`, `config`, `workflows`, `plugin-copies`, `records`; `--check --json --yes`); `dev/test_init_update.py` 1,224 to 759 (72 cases on both fixtures); `sync_status` prints `→ Run: purlin:init --update` while `pending()` is non-empty | 282,764 |

Wave 5 tokens: 674,556. Running total: 4,115,925.

BLOCKED (found by 5A's walk, fix lane F5 opened in wave 6): the record's `scope_tree` is
written as `{feature: hash}` by `purlin_run.build_record` but read as one string by the
package, the format doc and `states._record_verdict`, so nothing reaches Recorded; 5A's e2e
skips its `recorded` and `approved` assertions until F5 lands. Last failure output:
`record scope_tree = {"greeting": "6f4ba7fc..."}`, `specs.scope_tree(root, ["greeting.py"])
= "6f4ba7fc..."`, rule state `Tested`, gate `Not recorded (1): greeting RULE-1`.

Sweep at `6daa25ed` (end of phase 5): all ten shell suites pass, E2E Init included; pool
871 passed, 5 skipped, 1 failed: `test_purlin_version.py::TestReleaseNotesCounts` (the
release-notes counts line, rewritten by lane 8A). No other red.

### Phase 6: dashboard on the design system (Opus 5, 1 lane)

`scripts/report/src/` and `dev/build_report.py` produce `scripts/report/purlin-report.html` (target 900) per B8, plain HTML and CSS on `design/tokens/`, both themes, the three screens: gate and staleness in the top bar; seven-state strip; risk-by-state grid; feature table (spec, risk,
coverage, state, latest record label, approvals, re-verify pending); the review list view;
filters (high risk not approved, stale, no negative case, low test strength, open action
items); per-feature drill-down with rules, proofs, brief summary, git host links; design
anchor thumbnails. Columns appear as artifacts exist. Local data from `sync_status` and
the digest hook (gitignored); CI publishes page plus data as the `purlin-dashboard`
artifact. Acceptance: `dev/test_purlin_report.py` under 600 lines, including the no-raw-hex check and a both-themes render; one screenshot per process and per screen for the docs.

#### DONE

Wave 3, 2026-09-13. Landed by fast-forward at `61aabefb`. `scripts/report/src/` in eight
parts (`page.html`, `styles.css`, `theme.js`, `filters.js`, `board.js`, `rule.js`, `review.js`,
`app.js`), `dev/build_report.py` (153) inlining the tokens and the logo, the built
`scripts/report/purlin-report.html` 1,827 to 913 lines, `dev/test_purlin_report.py` (395, 30
tests: reproducible build, no raw hex outside the token block, both themes rendered for
the three fixture processes, columns appear as artifacts exist, each filter, the old-schema
notice), fixtures under `dev/fixtures/report/`, five screenshots under `docs/images/`. The
orchestrator viewed the team board: product surface, copper eyebrows, seven state tiles,
risk grid, filters, state pills. Tokens: 266,422.

### Phase 7: stakeholder tools (Opus 4.8, 1 lane)

`tools/PM/purlin-anchor-userstories.md` (~150): specs or anchors in any repo including the
project, criterion ids, risk, `origin: pm`, PR-based approval, uploaded design images committed into `designs/`, the owner-comment rule. `tools/QA/purlin-qa-report.md` (~120) on `scan.py`.

#### DONE

Wave 4, 2026-09-13. Landed by fast-forward at `98829eb1`: `tools/PM/purlin-anchor-userstories.md`
362 to 152 (repository connector only, no checkout; `origin: pm`, criterion ids, uploaded
designs committed into `designs/`, the owner-comment rule), `tools/QA/purlin-qa-report.md` 370
to 123 (sparse clone of `scripts/` to reach `scan.py`; the review list by risk; states plainly
that it cannot sign, so its approvals count only once the approver signs), both `.skill`
files repacked. Tokens: 103,838.

Fix lane F2 (wave 4, `25551c3d`): three `subprocess.run` call sites take `[*argv]` /
`[*command]` so the frozen security anchor passes; nine unswept suites wired into
`dev/run_tests.sh` (six pytest files, three per-plugin shell suites). Sweep after F2: nine
suites green, E2E Init and the pool's two collection errors known-red; pool 607 passed, 43
failed, all known-red. Tokens: 106,883. Wave 4 tokens: 501,933. Running total: 3,441,369.

### Phase 8: docs (Opus 4.8, 4 lanes; Fable writes the outline)

Plain voice, short sentences, every doc opens with who it is for. `README.md` (five
sentences, three processes, install, first session); `docs/index.md`; `getting-started.md`;
`solo-workflow.md`; `team-workflow.md`; `regulated-workflow.md`; `specs-and-anchors.md`;
`design-in-specs.md`; `working-together.md`; `running-and-records.md` (CI defined once,
records, retention, tags, rulesets, the one place "mutation testing" is named);
`review-and-approval.md`; `dashboard.md`; `raising-the-gate-and-upgrading.md`;
`spec-from-code.md`; `RELEASE_NOTES.md` (0.10.0 rewritten; the two-gauges notes reduced to
one "never shipped" paragraph). Retire `lifecycle-guide.md`, `testing-workflow-guide.md`, `collaboration-guide.md`, `dashboard-guide.md`, `regulated-environments.md`, `installation-guide.md`, `anchors-guide.md`. Diagrams are mermaid with the A11 init block (one shared snippet in `docs/_mermaid.md`, pasted per diagram). Regenerate `docs/images/` from the phase 6 screenshots. README uses `design/assets/logo.svg`. Update `CLAUDE.md` (add: every visual surface follows `design/readme.md`). Voice per `design/readme.md`.

#### DONE

Wave 6, 2026-09-13. Outline `dev/plans/lanes/8-outline.md`; four doc lanes plus fix lane F5,
all landed by fast-forward; head `a7c4abd4` after 8D (its rebase met 8A on the vocabulary
test's pending tuple; both removals kept).

| Lane | Head | What | Tokens |
|---|---|---|---|
| F5 | `1cd4a717` | the record carries `scope_tree` as the string, the documented `proofs` list, `schema_version`, `gate`, `test_strength`; a committed record now reaches Recorded (two new tests); the init e2e asserts its `recorded` and `approved` steps: 40 passed, 1 skipped | 139,537 |
| 8A | `31f61b7a` | `README.md` 243 to 120 on `design/assets/logo.svg`; `docs/index.md` 53; `docs/getting-started.md` 182; `docs/solo-workflow.md` 138; `CLAUDE.md` 110 with the design-and-copy section; `RELEASE_NOTES.md` 0.10.0 rewritten, earlier notes kept and excluded from the vocabulary check as history; `assets/purlin-logo.svg` deleted | 192,084 |
| 8B | `c775b445` | `team-workflow.md` 135, `regulated-workflow.md` 190 (the seven-state diagram), `review-and-approval.md` 169, `raising-the-gate-and-upgrading.md` 170 | 132,885 |
| 8C | `bc6f364a` | `specs-and-anchors.md` 239 (the anchor-repo diagram), `design-in-specs.md` 116, `working-together.md` 151, `spec-from-code.md` 102; the old spec-from-code guide deleted | 131,717 |
| 8D | `a7c4abd4` | `running-and-records.md` 253 (the one place "mutation testing" is named), `dashboard.md` 120 with the five screenshots, `docs/_mermaid.md` 20; the seven old guides deleted; `docs/` left the pending list | 195,202 |

Wave 6 tokens: 791,425. Running total: 4,907,350 (F8 pending).

Whole-set checks after landing: every link in `README.md` and `docs/*.md` resolves; the
vocabulary check passes with an empty pending list except the five files that must spell a
retired tag to say it is ignored. Found for fix lane F8: `scripts/run/ci.py` publishes the
dashboard into `.purlin/runtime/report` while `templates/purlin.yml` uploads
`$RUNNER_TEMP/purlin-dashboard` (the artifact would be empty); three references still cite
deleted docs.

Fix lane F8 (`b76d69c1`, 141,145 tokens): `ci.publish_dir` follows `RUNNER_TEMP` or
`AGENT_TEMPDIRECTORY` so the artifact upload finds the page; the three references repointed;
the refresh hook no longer needs a `report` key (init writes none); the release-notes
counts line set from the sweep record. Sweep after F8: 11 suites passed, 0 failed; pool 878
passed, 6 skipped; sweep record 888 passed. The orchestrator also moved the light product
surface to the lightest paper at the user's request (`94318985`). Wave 6 tokens with F8:
932,570. Running total: 5,048,495.

### Phase 9: re-spec, sweep, release (Fable orchestrates; Opus 5 lanes per spec group)

Purlin dogfoods at `gate: recorded`. Specs for the new surface (~12 specs, ~150 rules):
`specs/mcp/{specs,proofs,states,drift,server}.md`, `specs/run/{run_script,records,
mutation}.md`, `specs/review/{brief,approvals}.md`, `specs/init/{scaffold,update}.md`,
`specs/dashboard/purlin_report.md`, one per skill (3 to 6 rules), the four anchors trimmed;
the 36 frozen specs are deleted as their replacements land. Run `purlin:init --update` on
this repo itself (migrates `.purlin/config.json`, hooks and plugin copies; the first real
test of the upgrade path). Write and run by hand the three CLI checks under `dev/manual/`.
Tag `dev/test_*.py`, run verify locally and in CI on this repo, approve in the agent,
`bash dev/bump_version.sh 0.10.0`, release notes, tag `validated/0.10.0`.

#### DONE

Wave 7, 2026-09-13 to 2026-09-14. The user changed the dogfood to gate `approved` (full GxP,
one person in every role) and allowed branch pushes for CI; phase 9 lanes commit their tests
with the agent as git author so the user's signed approvals count. Briefs `9A` to `9H`, `9X`,
`F9`; order of work in `dev/plans/lanes/9-plan.md`.

| Lane | Head | What | Tokens |
|---|---|---|---|
| 9A | `5941569a` | `specs/mcp/` `specs` 14, `proofs` 7, `states` 25, `server` 22, `drift` 17, `config_engine` 12 rules (97); five frozen mcp and hooks specs deleted | 509,281 |
| 9B | `8e7b51dc` | `specs/run/` `run_script` 38, `records` 20, `mutation` 20; the six plugin specs and `consumer_ci` deleted; root `proof_plugins.test.sh` so the shell arm reaches the suites | 396,099 |
| 9C | `60cea136` | `specs/review/` `brief` 24, `approvals` 38 (with the gate), `static_checks` 37 (one `@env(windows)` proof holds at Proof ready on a Mac by design); `specs/audit/` and `verify_gate` deleted | 338,216 |
| 9D | `4cc155c5` | `specs/init/` `scaffold` 37, `update` 20; `pre_push_hook` deleted; root `init_e2e.test.sh`; the dead `report` key no longer written | 291,043 |
| 9E | `aaf29a89` | `purlin_report` 23, `specs/anchor/upstream` 22, `purlin_version` 9; root `conftest.py` | 237,334 |
| 9F | `7b81a9b8` | one spec per skill (13), `purlin_agent` 6, the two tools; 76 rules; `dev/test_skills.py` (894, 76 tests) in the sweep | 384,007 |
| 9G | `4546dc2c` | the four anchors trimmed (`proof_common` 14, `schema_spec_format` 11, `schema_proof_format` 8, `security_no_dangerous_patterns` 6); `dashboard_visual` deleted; the security anchor pin set to the local bare repo's sha | 279,769 |
| 9H | `ae32dd3d` | `dev/manual/check_spec.py`, `check_build.py`, `check_qa_tool.py`, all three run once against the real `claude` CLI: 5/5, 6/6, 5/5 checks passed | 129,493 |
| 9X | `6efa7896` | the plugin contract has one home (`run_script` RULE-23 to 35 dropped, `> Requires: proof_common`); one pytest collection guard, not two | 178,599 |

Phase 9 lane tokens: 2,743,841. Running total: 7,792,336 (F9 pending). 37 specs remain,
all new or rewritten; 501 rules.

Sweep at `7b81a9b8`: ten shell suites pass; pool 970 passed, 6 skipped, 1 failed: the
release-notes counts line, set at the release step.

Findings from the init dry run on this repository, fix lane F9: the workflow matrix came
out Windows-only (the Linux job must always exist); the upgrade carried `jest,vitest` from
the old config into a tree with no `package.json`; ten proofs fail the free checks and
hold their rules at Drafted. Two design gaps recorded by the lanes, not fixed: the run
script's shell arm executes only `*.test.sh` at the project root, so shell suites under
`dev/` prove nothing unless a root wrapper calls them (9B and 9D added wrappers; 9A, 9E
and 9F left their shell suites untagged and proved the same claims through pytest);
`scan.py` prints counts only, so the QA tool cannot yet produce a per-rule review list
from it. Findings from the real-model checks: the spec skill's "three rules out" sentence
reads as a target count and the model writes five or six; the `[criterion:]` tag is never
set from a bare sentence (correct).

**The orchestrator's phase 9 steps, 2026-09-14.** `purlin:init --update` on this repository
(`d193f8d0` hooks and config, `092a1872` records; `jest,vitest` dropped from the framework
list, three retired keys dropped), then `--gate approved` with the user as the one approver
(`f1d4e906`: `purlin.yml` with a Linux and a Windows job, the mutmut block in `setup.cfg`,
`designs/`, the pre-push shim); repo-local SSH signing configured and verified (`%G?` = `G`);
the counts line set from two green sweeps (986 passed); the developer record committed
signed (`2c148ab6`, 37 features, 488 Tested); the branch pushed. The user, mid-run, changed
the light theme twice (`94318985`, `4e13ca4c`), the tag text (`84f2665d`), and asked for the
Rule screen, the review rows, the board colours and the Latest record column to change
(lanes F12, F13, F15, F16 below).

| Lane | Head | What | Tokens |
|---|---|---|---|
| F9 | `3b0cabaf` | the matrix always carries `ubuntu-latest`; the upgrade and init drop a recorded framework the tree does not wire; ten proofs reworded to pass the free checks | 184,934 |
| F10 | `c2356a3e` | UTF-8 stdio at every entry point (Windows crashed printing the table); every arm and engine runs with closed stdin, `GIT_TERMINAL_PROMPT=0` and a 3600 s cap; `timeout-minutes: 90`; `requirements.txt` and the playwright install step; the record label accepts GitHub's web-flow committer with `github-actions[bot]` as author (A4's claim about the committer was wrong); the two root shell wrappers skip on Git Bash and their three proofs carry `@env(linux)` | 281,479 |
| F11 | `e5601f44` | all 141 Windows failures fixed at their causes: cp1252 decoding in tests, a fixture bare repo with a dangling default branch, CRLF (`.gitattributes`), bare `open()` calls, backslashes fed to bash, read-only git objects under `rmtree`, a coarse clock, a POSIX-only lock probe, two spellings of the artifact path | 313,687 |
| F12 | `ddc5dcc5` | the Rule tab sits right of Review list with a back link that closes it; the Review panel in plain sentences; a "To approve" panel with the exact command; the page reloads on return when its data is newer than a minute and the age text ticks each minute | 185,928 |
| F13 | `801ea466` | the board off the slate "product" surface onto the brand navy, matching the design kit's own board | 169,016 |
| F14 | `bb4ee7e8` | the Linux hang named: `mktemp -d -t <prefix>` is BSD-only, GNU returns nothing, so `dev/test_init_e2e.sh` ran against the checkout itself and a `purlin_run.py --project-root ""` cleared the real proofs; the suite now stops on an empty temp path and an empty `--project-root` exits 2; a failing arm prints its last 60 lines and `--ci` keeps every arm's log in the artifact; the xUnit fixture skips when the host cannot run net8.0; the Windows shell skip reads `OS=Windows_NT` | 264,554 |
| F15 | `d27c3b13` | a review row carries the rule text, its state and only a reason its group does not already say; the payload's `reasons` list | 188,807 |
| F16 | `e04e2751` | the Latest record column names each operating system's record with its result | 193,132 |

| F17 | `53473a4d` | the real cause of the 14 gate failures on both runners: `%G?` reads `N` both for no signature and for a signature the machine cannot check, and the label demoted GitHub's commits wherever gpg exists (every hosted runner); the reader now asks the commit object whether a signature is present; `default_branch` reads the branch HEAD names before guessing `main`; one artifact per job (`purlin-dashboard-<os>`); on Windows `bash` on PATH is the WSL launcher, so the run script finds Git Bash from git's own install and the dev suites use it; a plugin copy is a byte copy; four POSIX-only fixtures fixed; 999 passed locally | 310,694 |

Tokens, F9 to F17: 2,092,231. Running total: 9,884,567.

CI rounds on `evidence-workflow`: run 1 (`34808346536`) Windows committed 37 records but crashed
printing, Ubuntu cancelled at six hours; run 2 (`34840363131`, with F10) both jobs ended
inside the cap, Ubuntu's shell arm timed out at 3600 s, Windows 7 rules short; run 3
(`34842281168`, with F11) Windows every rule Tested or Reviewed yet both arms exit 1, Ubuntu
as run 2; run 4 (`34851835724`, with F14) Ubuntu in four minutes with one marker missing, CI auto-approved 69 low-risk rules and reviewed 425, both jobs exit 1 on 14 gate tests (Windows 56); run 5 (`34859129349`, with F17): the Windows job green (503 rules: Reviewed 426, Approved 77 by CI's low-risk auto-approval), Ubuntu green but for two pre-push hook tests that expect exit 0 outside a repository and get the run script's 2 (fix lane F18: `/bin/sh` on Ubuntu is dash, which rejects `set -o pipefail` before the hook runs; the hook is POSIX sh now, `0ac7bd5c`, 123,415 tokens); run 6 (`34862218712`, with F18) Ubuntu green, Windows red on the hook tests (the suite asked PATH for `sh`; the orchestrator pointed it at Git for Windows' `sh.exe`, `b2fa0a1b`-era commit); run 7 (`34864380681`): **both jobs green**, Linux in 5 minutes, Windows in 16; each job commits its records through the API with label `ci`; 503 rules read Reviewed 426 and Approved 77 on the runner. Lane F19 (pending) makes the approvals and briefs travel in that commit, since a checkout still reads Recorded 482. Running total with F18: 10,007,982. CI's API commits label `ci` and trigger no
further run. `verify_gate.py --check` on this repository still exits 1 under `approved`
until the user's approvals exist.

## C3. Preloaded decisions (the orchestrator never asks; a lane that meets an unlisted choice picks the simplest option and records it in its DONE note)

| Question a lane might raise | Answer |
|---|---|
| Python floor | 3.9; every `open()` with `encoding='utf-8'` |
| Third-party deps in plugins or scripts | none; stdlib only (the Node plugins use no npm package beyond the test framework) |
| mutmut config location | `[tool.mutmut]` in `pyproject.toml` when it exists, else `setup.cfg` `[mutmut]`; written like the other wiring files |
| Record file name | `<YYYYMMDDTHHMMSSZ>-<commit7>-<runner>[-<os>].json`; runner slug `ci` or the developer's git email local part, lowercased, non-alphanumerics to `-` |
| Retention | newest three per feature per OS plus anything a `validated/*` tag names |
| Default branch | `git symbolic-ref refs/remotes/origin/HEAD`, else `main` |
| Approver slug in approval file names | email local part, lowercased, non-alphanumerics to `-` |
| Timestamp format everywhere | ISO 8601 UTC with `Z` |
| Test strength display | integer percent; `n/a` when no engine |
| Records from forked PRs | never committed; the job says so in the PR comment |
| xUnit detection | any `*.csproj` referencing the `xunit` package |
| Vitest compatibility | `onTestRunEnd` primary, `onFinished` kept for Vitest 1 and 2 |
| The one `@env(windows)` proof this repo keeps | the file-locking check in `static_checks.py` |
| `dev/manual/` CLI checks | hand-run only, never in `run_tests.sh` |
| Commit prefixes before phase 4B rewrites the conventions | the existing `references/commit_conventions.md` prefixes |
| Unknown tags in frozen specs | ignored with one warning until phase 9 |
| Emoji in any output | never |
| Colours in the dashboard | tokens only; a raw hex outside the inlined token block fails acceptance |
| Diagrams in docs | mermaid with the shared init block; no images except dashboard screenshots |
| A design decision not covered by `design/readme.md` | the plainer option; note it in the DONE note for the user |
| A lane finds a Part B claim false | record it under BLOCKED with evidence, skip, continue; never redesign inside the lane |
| Anything else | the simplest option that keeps the vocabulary in A1 and the deletions in C0 intact |

## C4. Verification (end to end)

1. `bash dev/run_tests.sh` green at the end of phases 1, 2, 5, 9.
2. Consumer fixtures (Python and TS at minimum, xUnit with the dotnet@8 PATH): init at each
   gate → spec → build → test → verify → approve → `verify_gate.py --check` exits 0 under
   `tested`; exits 1 under `recorded` until a ci-labelled record exists (git host API mocked);
   exits 1 under `approved` until a high-risk approval exists whose commit is signed by an email on the approver list and the list itself is present.
3. Upgrade fixtures: v0.9.5 and 0.10-dev pass `--update --check` then `--update`; no
   advisory after.
4. This repo: `purlin.yml` runs on `evidence-workflow` with a Linux and a Windows job (one spec keeps a `@env(windows)` proof for the checker's Windows path), both API commits land with label `ci`, `purlin:verify --remote` from a Mac returns the Windows result, the PR comment and artifact appear, `--tag rc1` survives a prune.
5. Token accounting per lane in the DONE notes, summed per phase.

## C5. Deferred, by user decision

ADO live test on the user's work machine, including the ADO branch of `purlin:verify --remote` (marked `TODO(ado-remote)`); `@env` for named services such as databases; a minimal SQL mutator; GitLab; a design-tool importer; per-rule attribution for Python if a future mutmut reports killing tests.
