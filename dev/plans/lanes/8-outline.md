# Phase 8 outline: the documentation set for 0.10.0

Every doc opens with one line saying who it is for. Plain voice per `design/readme.md`
"Content fundamentals": short sentences, second person for the reader, third person for
the system, exact numbers, limits stated, no superlatives, no emoji. Commands, ids, paths
and shas in backticks. Diagrams are mermaid with the shared init block from
`docs/_mermaid.md` pasted at the top of each diagram; no images except the dashboard
screenshots lane 6 produced under `docs/images/`. Every doc links the next one a reader
would want. Nothing cites `dev/` or this repository's own `specs/`.

Length is a ceiling, not a target. Each doc is one sitting's read.

## Lane 8A: the front door

- `README.md` (under 120 lines): five sentences on what Purlin is (A1's rule, proof, test,
  record, approval); the three processes in one table (A2); install (marketplace and
  `--plugin-dir`); the first session traced (A10 "Solo start"); the logo from
  `design/assets/logo.svg`; links to `docs/index.md`. Delete `assets/purlin-logo.svg` once
  the README no longer names it.
- `docs/index.md` (under 60 lines): the map of every doc with one line each, grouped by
  reader (everyone, engineer, PM, designer, QA, admin).
- `docs/getting-started.md` (under 200 lines): install, `purlin:init` and its one
  question, the first spec, build, test, verify, what the status table shows, the next
  step line; ends by pointing at the process doc that fits.
- `docs/solo-workflow.md` (under 160 lines): gate `tested` end to end, the developer's own
  record commit, what the pre-push hook does, when to raise the gate.
- `RELEASE_NOTES.md`: 0.10.0 rewritten as the one-step transition for v0.9.5 users: what a
  v0.9.5 user does (`purlin:init --update`), what changed by concept (vocabulary, gate,
  records, approvals, engines, `@env`, the dashboard, the tools), what was removed (one
  paragraph, in current vocabulary: the LLM grading scores, the runner registry, the
  committed verification files, the committed dashboard data, C and PHP); the two-gauges
  development notes reduced to one "never shipped" paragraph; earlier releases' notes kept
  as they are below. The counts line the version check reads stays in the shape
  `dev/test_purlin_version.py` expects (read that test).
- `CLAUDE.md` (this repository's own instructions, under 110 lines): the current sections
  brought to 0.10.0 (format files list: `spec_format.md`, `anchor_format.md`,
  `proofs_format.md`, `record_format.md`, `approval_format.md`; the authoritative
  references list; the release procedure unchanged; tool folder separation unchanged) plus
  one new section: every visual surface and all copy follow `design/readme.md`.

## Lane 8B: the two higher gates

- `docs/team-workflow.md` (under 220 lines): gate `recorded`; CI as the writer of the record
  that counts; the PR comment and the dashboard artifact; the PM, designer, QA and
  engineer entry points (A6) in one traced sprint; concurrency (A9) in one paragraph.
- `docs/regulated-workflow.md` (under 240 lines): gate `approved`; the approver list; the
  signed commit; risk and origin required; auto-approval of low risk; Stale and re-verify
  pending; the validation tag; what an auditor-free evidence trail looks like in git
  history (the folder's log, the approval files, the tag); `@manual` proofs as an approval
  file with a note.
- `docs/review-and-approval.md` (under 200 lines): the review list, the brief and its
  layers, `purlin:review`'s walk, `purlin:approve`, batch approval, what makes an approval
  count, what stales it, the AI review and when it runs.
- `docs/raising-the-gate-and-upgrading.md` (under 200 lines): `purlin:init --gate` both
  ways, the setup trace table (phase 5, in prose), `purlin:init --update` from v0.9.5 and
  from the 0.10 development layout, what the update asks and backs up.

## Lane 8C: specs, anchors, design

- `docs/specs-and-anchors.md` (under 240 lines): the spec format at Format-Version 11
  (rules, proofs, tags, tiers, `@env`, `@manual`, `> Scope:`, `> Requires:`), local
  anchors, the anchor repo option with `add`, `sync`, `propose`, pins as commits, the
  upstream check job, id allocation and `--resolve` after a merge.
- `docs/design-in-specs.md` (under 160 lines): `designs/<feature>/`, design anchors with
  `> Source:` globs and `> Pinned:` file hash, `origin: design` rules, e2e observables not
  selectors, captures under `.purlin/runtime/attachments/`, mock beside screenshot in the
  brief, a new export stales approvals; the designer's two ways in.
- `docs/working-together.md` (under 200 lines): the roles (A6) each in one section: what
  they need (a checkout or not), what they run, what they see; the PM tool and the QA tool
  in Claude Desktop; the owner rule; drift per role (A3).
- `docs/spec-from-code.md` (under 120 lines): once on an existing codebase, what it writes,
  what it tags, what to do next.

## Lane 8D: running, records, dashboard

- `docs/running-and-records.md` (under 260 lines): `purlin:test`, `purlin:verify` local
  and `--remote`, CI defined once (the workflow, the matrix from `@env`, the API commit,
  the forked-PR case), records (shape by field, the name, the label from git, retention,
  validation tags), test strength (the one place "mutation testing" is named, with the
  three engines and the two languages that have none), `sql_engine`, exit codes, the two
  loud failures.
- `docs/dashboard.md` (under 160 lines): the local page and the CI artifact, the three
  screens with the five screenshots, filters, columns that appear as artifacts exist, both
  themes, `scan.py` for anyone with a repo URL.
- `docs/_mermaid.md` (under 30 lines): the shared init block (navy ground, cream text,
  copper accent, hairline borders) and the one-line instruction to paste it per diagram.
- Delete `docs/lifecycle-guide.md`, `testing-workflow-guide.md`, `collaboration-guide.md`,
  `dashboard-guide.md`, `regulated-environments.md`, `installation-guide.md`,
  `anchors-guide.md`, `spec-from-code-guide.md` (its replacement is 8C's; delete it here
  after 8C's lands, or in 8C if that lane is asked to). Every deleted doc's replacement
  must exist in the tree at the same commit or a later one.

## Diagrams (mermaid, one per doc at most, only where the picture shows a mechanism)

- getting-started: the loop spec → build → test → verify → push.
- team-workflow: push → CI verify → record commit → PR comment and artifact → merge.
- regulated-workflow: the seven states as a state diagram with the re-verify pending flag.
- specs-and-anchors: anchor repo → pin → project, with `sync` and `propose`.
- running-and-records: the run script's flow with the two loud failures.

## Cross-lane rules

- Four lanes write four disjoint file sets; `docs/index.md` (8A) links every doc by the
  names above, so no lane renames a doc.
- Each lane removes its files from `_PENDING_REWRITE` in `dev/test_vocabulary.py` and runs
  that test; 8A also removes `README.md`, `CLAUDE.md`, `RELEASE_NOTES.md`,
  `assets/purlin-logo.svg`; 8D removes `docs/` last (its deletions land after 8A, 8B, 8C
  in the landing order; if `docs/` is one entry, 8D removes it and the orchestrator lands
  8D last).
