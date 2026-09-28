# Handoff, 2026-09-28

For the session that continues Purlin 0.10.0. Read this, then `dev/plans/three-levels.md`
decisions 31 to 58 (together they are the product as the owner settled it), then
`dev/plans/morning-list.md` (every choice made on the owner's behalf, one line each).

## Where the tree is

- `main` is local only. Nothing has been pushed, tagged, audited or signed. The owner pushes;
  no agent does, except the one temporary branch `purlin:test --remote` sends.
- Full sweep on `main`: **1088 passed across 7 suites, 0 failed.** `bash dev/run_tests.sh`.
- This repository through its own tool: 994 of 994 markers tied to a test, **566 of 566 rules
  pass their tests**, 94 of 566 meet the gate `signed`. The 94 are rules marked
  `[level: passed]`. The other 472 wait for an audit and a signature, which the owner has said
  not to run yet.
- The evidence of that run is committed (`purlin: evidence at 98fc3cb`), under
  `.purlin/evidence/local/`.
- `.purlin/config.json` here: gate `signed`, `trust: local`, mutation testing on.
- No branch but `main` is left on this machine, and no worktree. The remote still carries old
  branches and the tag `pre-instruction-optimization`; those are the owner's to delete.
- The slides: https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is, six of them, built by
  `dev/plans/deck/build_deck.py`.

## The model in one paragraph

A rule says what must be true. A proof says in plain language how that is shown. A test is
any test in the project's own suite with one comment above it, `purlin: <feature> PROOF-<n>`.
Three levels: `passed` (`purlin:test`), `strong` (`purlin:audit`, a model reading each test
against its proof, with optional mutation testing), `signed` (`purlin:sign`). The gate is how
far every rule is asked to go; a rule may be marked lower with `[level: ...]`, and a column a
rule is not asked shows nothing. Evidence is one file per feature, written by a run and
committed with `--commit`; it goes out of date when the spec, the covered code or the tests
change, and a run with no feature named runs only what changed. `purlin:sign` walks one queue
and, at the gate `signed`, writes the evidence package and the signed tag. Purlin makes no
claim of compliance: it hands evidence to a system of record.

## What is left, in order

1. **Sanity check 2: a new user follows the docs**, then **every required proof is rewritten
   to the guideline.** A fresh agent with fresh context; the prompt is
   `dev/plans/next-agent-prompt.md`. Part 1, the check, is done with only the README and the
   docs in hand, changes nothing here, and ends in a report. Part 2 rewrites the 558 proofs on
   rules whose level asks for the audit, across 30 specs, to
   `references/spec_quality_guide.md`, "Writing proofs", keeping every id, rule and marker,
   and closes the test gaps that exposes. Both parts are run highly parallel, which the
   owner asked for: the seven paths of the check at once, then one agent per spec for the
   rewrite, all thirty at once, then one agent per test file for the gaps. The prompt cuts
   the stages so that no two agents running together write the same file; for this task the
   limit of two writers below does not apply.
2. **Put its findings to the owner as questions**, in plain words, most basic first, then
   apply the answers: one Opus agent per closed decision, in its own worktree under
   `/Users/richlabarca/LocalCode/purlin-wt/<name>`, merged by fast-forward.
3. **Windows.** The owner decided that Windows and Mac matter and Linux does not, and that
   Windows is shown by a remote runner. Still open, and the owner's to answer: which proofs
   must hold on Windows. Then: mark them `@env(windows)`; make the init walk really run on
   Windows, since today its Windows skip exits 0 and would be read as a pass; have
   `purlin:init` rewrite this repository's runner file for Windows; run `purlin:test --remote`
   once, which also proves the remote run against GitHub for the first time.
4. **More sanity checks**, each its own fresh agent, in the order the owner picks: a QA person
   writes proofs; an upgrade from a real 0.9.5 project; a hostile reviewer who tries to make an
   unproven rule read as proven.
5. **Every page is read again against the code**, which the owner asked for on 2026-09-28. It
   comes after every decision from the sanity checks and the dashboard is applied, since each
   of those changes what a page must say. One agent per page of `README.md` and `docs/`, each
   checking every sentence, command, sample of output and file name against what the product
   does, in the words of `references/writing_style.md`. It covers: what Purlin needs installed
   (git, Python and its lowest version, Claude Code), checked and not copied; the findings of
   `dev/plans/sanity-2-new-user.md` sections 2 and 3; the sentence `N of M rules meet the gate`,
   which leaves every page; the queue's words. The three screenshots in `docs/images/` are
   retaken last with `dev/capture_doc_screenshots.py`, from the rebuilt dashboard, and looked
   at before they are committed.
6. **The owner's review**: `RELEASE_NOTES.md` 0.10.0, `README.md`, `docs/getting-started.md`,
   `docs/regulated-workflow.md`, the rest of `docs/`, the slides, the diagrams.
7. **The handover to the work machine**: delete `dev/plans/` (it is history, and it ships);
   push the work as a branch; on the work machine run `dev/manual/check_azure_remote.py` and
   `dev/manual/check_azure_provenance.py` against a real Azure DevOps project, then
   `purlin:audit`, `purlin:sign`, the push of the tag, the release.

## Small things known and not fixed

- `purlin:init` without `--yes`, run with its output piped, hung once in a scratch Go project.
  Not looked into. With `--yes` it is fine.
- The rule's own screen still shows the `purlin:sign` panel for a rule whose signed column
  reads `waiting`.
- Proofs outside `drift`, `upstream` and `config_engine` are still written in the test's own
  words. Part 2 of the next session rewrites the required ones.
- Vitest 4 would not install on this machine; version 3 is proven.
- Text on a solid coloured badge measures under 7 to 1. The owner chose to leave it.
- A hand check may be signed without a note. The owner chose to leave it.

## How to work, as the owner settled it

- **Decisions close before anything launches.** Ask with the question UI, with options and
  consequences, and wait.
- **Ask from the root.** Say what a thing is for in plain words before asking about it. No
  function names, no file names, no term that has not been explained. Offer the option that
  removes the mechanism. The owner is simplifying Purlin with every answer.
- **One Opus agent per closed decision**, own worktree, fast-forward merge, two writing at
  once at most and only where their files do not overlap.
- **No push, no pull request, no tag, no audit and no signing by any agent.**
- **Acceptance is the full sweep**, `bash dev/run_tests.sh`, plus this repository run through
  its own tool with every marker tied. Never edit a number to make a sweep green.
- **Look at anything visual** with playwright from the `.venv`, at 1500, 1280, 1024, 768 and
  390 pixels, dark theme, before telling the owner it is done. A value never breaks inside
  itself; neutral text measures at least 7 to 1.
- **A clean release.** Nothing that represents earlier functionality stays: no compatibility
  reader, no test that a removed thing is absent, no table of removed words.
  `RELEASE_NOTES.md` is the one place history is kept, and what an upgrade from 0.9.5 needs is
  the one exception in code.
- **A page says what is**, checked against the code, in the words of
  `references/writing_style.md`.
