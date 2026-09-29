# Handoff, 2026-09-29, evening

For the session that continues Purlin 0.10.0. Read this, then `dev/plans/three-levels.md`
decisions 31 to 58 (together they are the product as the owner settled it), then
`dev/plans/morning-list.md` (every choice made on the owner's behalf, one line each).

## Where the tree is

- `main` is local only. Nothing has been pushed, tagged, audited or signed. The owner pushes;
  no agent does.
- Full sweep on `main`: **2112 passed across 7 suites, 0 failed.** `bash dev/run_tests.sh`.
- This repository through its own tool: 2057 of 2057 markers tied to a test, **564 of 564
  rules pass their tests**, 0 are strong, 0 are signed. It prints `564 rules. 564 pass their
  tests. 0 are strong. 0 are signed.` and `Left to do: 564 rules to audit: purlin:audit`.
  2056 proofs, each one case of at most 60 words with a test of its own. The
  audit and the signing are the owner's to run.
- The evidence of that run is committed (`purlin: evidence at 28c049a`).
- `.purlin/config.json` here: gate `signed`, mutation testing on. No runner file: no rule names
  another operating system yet (decision 82).
- No branch but `main` is left on this machine, and no worktree.
- The slides: https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is, ten of them, built by
  `dev/plans/deck/build_deck.py`. The owner edits them in place: read each slide from the deck
  before publishing it, and take the owner's words into the builder.
- Decisions 85 to 93 were made on 2026-09-29; the proofs were split and the dashboard
  changed to them, and `phase2-report.md` is what the lanes brought back: 79 questions for the
  owner, the product faults left for the owner, and the list of 90 rules for Windows.
- Decisions 60 to 84 were made on 2026-09-28 and are in `three-levels.md`. The product changes
  they ask for are done: `phase1-plan.md` is the plan, `phase1-interfaces.md` and
  `phase1-lanes-report.md` what was built. Sanity check 2 is `sanity-2-new-user.md`; the first
  rewrite of the proofs is `proofs-rewritten.md`.

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

The prompt for the next session is `dev/plans/next-agent-prompt.md`.

1. **Decisions 94 and 95 are built**: the answers to the second fan-out's questions, the 55
   readings of `phase2-questions.md`, and Windows. The owner sees the final Windows list before
   any rule is marked (decision 82).
2. **Windows is run for real**: setup writes the runner file, and `purlin:test --remote` is
   run once, which also proves the remote run against GitHub for the first time. The owner is
   asked before the first remote run.
3. **Sanity check 3** (decision 64): the docs against the rules, and `purlin:spec-from-code`
   run for real on three small projects at each gate, held to decisions 66 and 81.
4. **More sanity checks**, each its own fresh agent, in the order the owner picks: a QA person
   writes proofs; an upgrade from a real 0.9.5 project; a hostile reviewer who tries to make an
   unproven rule read as proven.
5. **Every page is read again against the code** (decision 63), with the screenshots retaken
   last. Three pages still say `n/a`; the ten-minute path still types its rules by hand.
6. **The owner's review**: `RELEASE_NOTES.md` 0.10.0, `README.md`, `docs/`, the slides.
7. **The handover to the work machine**: delete `dev/plans/` (it is history, and it ships);
   push the work as a branch; on the work machine run `dev/manual/check_azure_remote.py`
   against a real Azure DevOps project, then `purlin:audit`, `purlin:sign`, the push of the
   tag, the release.

## Words for the owner to read

Chosen by an agent where no decision gave them. The owner accepted them on 2026-09-29
(decision 96), changed the line for the git host, which is still to be built, and left the
rest to sanity check 3.

| Where | What it says |
|---|---|
| The signed panel on a rule's page | `Signed by <name>, <email>, on <date> <time> UTC with the key ending ...<last 4>.` then, per system, `On <System> the tests ran on <machine>.` |
| A hand check, explained on the dashboard | `A hand check is you checking the rule and signing it in one act; purlin:sign asks what you saw and records it.` |
| Under the filter buttons | `Type <command> in Claude Code.` |
| Signing with nothing waiting | `Nothing is waiting for someone to test by hand or to sign.` |
| Signing a name that is not a rule | `<feature> <RULE-N> is not a rule any spec has.` |
| A run started by a pushed signed tag | `Tag run: nothing is written. This run reruns the tests on <ref>.` |
| Setup, when no remote runner is needed | `every proof runs on this operating system, so nothing has to run remotely` |
| Setup, with no git host | `No git host found.` (decision 96, to be built) |
| Setup, with a git host Purlin cannot use | `This git host cannot run tests remotely. Everything on this machine works.` (decision 96, to be built) |
| Setup, with no tool for breaking code | `Without it test strength is not measured.` |
| A comment that is nearly right | `` `purln` is one letter from `purlin`. `` |
| The evidence package refusing a tag | `the committed evidence still has work left to do` |
| The warning for a minimum that is not a number | `no minimum applies` |

Two small things seen and not changed: the warning `1 spec files carry tags` has its plural
wrong, and at 1500 pixels the board shortens `security_no_dangerous_patterns` with an ellipsis.

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
- **Maximum parallelization, cut by ownership of files.** Each agent is Opus, has its own
  worktree and its own scratch folder, and owns files no other agent writes. What one produces
  and another consumes is fixed word for word before they start. Merges are fast-forward.
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
