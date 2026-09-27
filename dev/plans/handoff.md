# Handoff, 2026-09-27

For the session that continues Purlin 0.10.0 after the three-levels work. Read this, then
`dev/plans/three-levels.md` decisions 23 to 31 (the model as the user settled it; 31 with its
amendments is the latest), `dev/plans/lanes/tl-_rules.md`, and
`dev/plans/lanes/tl-15-findings.md` (the second full review; its nine questions are open).

## Where the tree is

- `main` and `three-levels` both point at the same commit, the integrated stack of lanes 8A
  through 15, merged locally by fast-forward. Nothing has been pushed since decision 25; the
  remote `three-levels` carries three CI record commits the local branch does not, all inert
  old-layout records. The user pushes; no agent does.
- Sweep at that commit: 11 suites, 1169 passed, 0 failed, 6 skipped. `bash dev/run_tests.sh`
  runs it; there is no counts line and nothing to bootstrap.
- `.purlin/config.json` here: gate `signed`, `sign_at: strong`, `trust: local`, one signer.
  This repository's own `.purlin/records/` and `.purlin/briefs/` are still the pre-0.10.0
  layout and are ignored by the reader; `purlin:init --update` moves them, or they are deleted.
- The inert `record/1.0` tag was deleted locally; it was never on the remote.
- The deck: https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is, three gate slides plus an
  optional fourth. Its content is `dev/plans/lanes/tl-14B-slides.md` and has not been
  republished since decision 31.

## What is left, in order

1. **The nine questions in `tl-15-findings.md`**, put to the user before any code moves:
   the signer list below `signed` (Q1); `purlin:sign <feature>` and `--batch` at `strong`
   (Q2); whether `trust: remote` binds the passed cell or only signing (Q3); the drift key
   `rules_without_a_negative_case` (Q4); the protected-branch prerequisite in init (Q5);
   `is_fork()` (Q6); six unread constants (Q7); the free scans' internal names (Q8);
   `--quick` versus `--test` (Q9). Each has its options and consequences in the file.
2. **Apply the answers** in one worktree, one agent, one commit series, fast sweep plus the
   touched files, then one full sweep.
3. **Regenerate the diagrams** (every mermaid fence in `docs/`, rendered and looked at) and
   **republish the deck** from `tl-14B-slides.md`, then check both against the code once
   more. The user's words: simple, clear and direct for developers; the bare workflow is the
   story; remote runners only where the two cases are described.
4. **Closeout by the user**: `purlin:sign` to walk Review then Sign (the list is long because
   no audit with a model has run here yet; `purlin:audit` first), the tag `signed/0.10.0`
   that the walk writes, `git push` of `main` and the tag, a pull request if wanted.

## How to work, as the user settled it this week

- **Decisions close before anything launches.** If a change needs the user, ask with the
  question UI, with options and consequences, and wait. Three lanes were rebuilt this week
  because a decision moved under them.
- **One thread, not lanes.** A decision is applied by one Opus agent in one worktree under
  `/Users/richlabarca/LocalCode/purlin-wt/<name>` across code, board, docs and skills, then
  merged by fast-forward. Two agents at most, split by surface (code and fixtures first,
  then board and docs against the fixtures). No stack of branches.
- **Opus for every agent.** The user asked for it explicitly.
- **No push, no pull request, no tag by any agent.** A push is a person's act (decision 27
  and 31). `purlin:sign` writes the tag; the person pushes it.
- **Acceptance is `bash dev/run_tests.sh --fast` plus the touched test files**; the full
  sweep runs once at integration. Never edit a number to make a sweep green.
- **Look at pages with playwright from the `.venv`**, never the Chrome extension.
- **The vocabulary guard** (`dev/test_vocabulary.py`) fails on retired words in shipped
  prose; the retired table in `references/glossary.md` is the only place they may appear.
- **Format files bump in the same commit as the code** they govern (`CLAUDE.md`).
- Prose per `design/readme.md` "Content fundamentals": plain, declarative, no emoji, second
  person for the reader, third for the system.

## The model in one paragraph

A rule has a spec status (`drafted`, `ready`) and up to three cells, `passed`, `strong`,
`signed`, answered by `purlin:test`, `purlin:audit` and `purlin:sign`. Every rule has a bar,
`passed` or `strong`, from a tag or the gate; a rule that has cleared its bar is signable. The
audit measures test strength and runs the AI audit on bar-`strong` rules; its words are
`strong`, `weak`, `not audited`, `unsettled`, `manual test`, `held`. Local evidence counts at
every gate. A signature locks rule, proof, test, bar and the audit's findings. The gate is
checked when `purlin:sign` writes `signed/<version>`; push is free; a remote runner exists
only for a proof tagged for another operating system or `trust: remote`, and then it runs
on `run/*` branches and `signed/*` tags and verifies the evidence.
