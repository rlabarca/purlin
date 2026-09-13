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
