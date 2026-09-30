# Handoff, 2026-09-30

For the session that continues Purlin 0.10.0. Read this, then `dev/plans/three-levels.md`
decisions 60 to 100 (together with this file they are the product as the owner settled it), then
`dev/plans/next-agent-prompt.md`, the prompt that session is given.

## Where the tree is

- `main` is local only, at the commit of this file, after `b46c93f01 purlin: evidence at
  5f002e0`. Nothing on it is pushed, nothing is tagged, and no audit or signing has been run
  against this repository. The only pushes any agent made were the
  temporary run branches of the remote runs on Windows. The owner pushes `main`; no agent does.
- Decision 99 is built: the five answers to the open questions, by five lanes merged into
  `main` and one integration (`phase4-interfaces.md`, "Decision 99": the ids, the words chosen
  and the calls left).
- Full sweep on `main` at `094f811d5`, `bash dev/run_tests.sh`: **2291 passed, 3 skipped in
  729.29s**, `>>> All Pytest Tests: PASSED`, `Suites: 5 passed, 0 failed`; the four shell suites
  passed. The 3 skips are the Windows-only tests.
- This repository through its own tool, `python3 scripts/run/purlin_run.py --test --all` at
  `5f002e00e`, exit 0: `Markers: 2333 tied to a test, 0 not tied.`, `Ran pytest, shell on 36
  features.`, `86 proofs need Windows; this machine is macOS. Run purlin:test --remote.`, then
  `891 rules. 891 pass their tests. 0 are strong. 0 are signed.` and `Left to do:` /
  `  891 rules to audit: purlin:audit` (at `6ea879147 purlin: evidence at e38956f`, after the
  remote run below).
  No rule reads `partial`, `failed` or `no test`, and no warning prints. With `--commit` the
  same lines, `Evidence committed.` after the evidence line, and one commit,
  `b46c93f01 purlin: evidence at 5f002e0`. 2333 proofs, each one case of at most 60 words with
  a test of its own. The audit and the signing are the owner's to run.
- The remote run on Windows after decision 99 came home as `e38956f11 purlin: evidence at
  c98fe7b`: every rule tagged for Windows passes there. The run before it found a fault in
  `purlin:test --remote`: it looked up the run to wait on by its branch alone, so when this
  repository's other workflow, the version check, registered first, it waited on that, pulled
  nothing and deleted the run branch while the Windows job still ran. The lookup now names the
  workflow file too (`03005dd8a`; host RULE-12, PROOF-66).
- Decision 100 (anchors are global) is closed and not built: "What is left", item 1.
- The runner file, `.github/workflows/purlin.yml`, was written by setup from the templates of
  phase 4 and committed by setup (`8008d9de6 chore(init): set up Purlin at the gate signed`).
  It runs on `windows-latest` alone: 86 proofs are tagged `@env(windows)`, and the 13 tagged
  `@env(macos)` are proven on this Mac, which wrote the file.
- The first real remote run on Windows passed 84 of the 86 rules that wait for Windows, and
  the second passed all 86. A diagnostic run of the whole suite on the same runner showed 78 of
  1979 tests failing on Windows that no rule is tagged for: `75 failed, 1901 passed, 2 skipped,
  3 errors`. The runner's log names 16 of them;
  `dev/plans/windows-untagged-failures.txt` holds them and says how to name the rest. Decision
  95 runs on Windows only the tests of tagged proofs, so none of the 78 fails a remote run.
- `.purlin/config.json` here: gate `signed`, mutation testing on.
- Phase 4 applied sanity check 3 (`sanity-3.md`) and decision 98: `phase4-plan.md` is the plan,
  `phase4-contracts.md` the contracts, `phase4-interfaces.md` what was built, with "The pages"
  at its end for the docs. Every page under `docs/` and `README.md` was read again against the
  code; the two screenshots were retaken from the rebuilt page (`b54a9def4`).
- The lane branches and worktrees of phases 3 and 4 are still on this machine, 28 worktrees
  under `/Users/richlabarca/LocalCode/purlin-wt/` with their `lane/*` branches, every one
  merged into `main`. None was deleted; they can go once the owner says so.
- The slides: https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is, ten of them, built by
  `dev/plans/deck/build_deck.py`. The owner edits them in place: read each slide from the deck
  before publishing it, and take the owner's words into the builder.

## The model in one paragraph

A rule says what must be true. A proof says in plain language how that is shown: one case, in at
most 60 words. A test is any test in the project's own suite with one comment above it,
`purlin: <feature> PROOF-<n>`. Three steps: `passed` (`purlin:test`), `strong` (`purlin:audit`,
a model reading each test against its proof, with optional mutation testing), `signed`
(`purlin:sign`). The gate is the last step every rule must reach, and every rule is asked what
the gate asks: no rule carries a level of its own. Evidence is one file per feature per source,
written by a run and committed with `--commit`; it goes out of date when the spec, the covered
code or the tests change, and a run with no feature named runs only what changed. Each proof is
proven where its tag says: this machine proves every untagged proof and every proof tagged for
its own system, and a remote runner proves only the proofs tagged `@env` for its system, which
this machine is not. Every run ends on the summary and `Left to do`, one line per kind of work
with its command; there is no queue, and `to test by hand` and `to sign` are two of its lines.
A spec's `> Requires:` names anchors only, the project's own or pinned ones, whose rules then
apply to it. `purlin:sign` walks the rules left `to test by hand` or `to sign` and, at the gate
`signed`, when nothing else is left and every result came from committed work, writes the
evidence package and the signed tag. Purlin makes no claim of compliance: it hands evidence to
a system of record, which decides who was entitled to sign.

## What is left, in order

The prompt for the next session is `dev/plans/next-agent-prompt.md`.

1. **Decision 100 is built**: an anchor is a set of rules for the whole project. It is closed
   and nothing of it is built. It changes how rules are counted, what an anchor's signature
   covers, the spec and anchor formats, the evidence package, the dashboard, the terminal,
   signing, the upgrade from 0.9.5, the instructions, the docs and one slide. The owner asked
   for a plan first: a planning agent writes the lanes and every line a person would read, the
   owner reads it and answers what it raises, and then it is built. The branch
   `lane/anchors-section` (worktree `purlin-wt/anchors-section`, two commits, not merged, its
   sweep not confirmed) holds a first build of the dashboard's `Anchors` section, made before
   decision 100: it keeps the per-feature counts, so it is a start and not the answer. A
   remote run on Windows follows the build.
2. **The further sanity checks**, each its own fresh agent, in the order the owner picks. The
   next one runs `purlin:spec-from-code` on project copies of which one carries a test that
   fails before the run, so decision 66's clause about failing tests is tried, and the agents
   count existing tests one way (`sanity-3.md` section 9). Then: a QA person writes proofs; an
   upgrade from a real 0.9.5 project; a hostile reviewer who tries to make an unproven rule
   read as proven. Decision 64 repeats the docs-against-rules reading by a fresh agent before
   every release.
3. **The owner's review**: `RELEASE_NOTES.md` 0.10.0, `README.md`, `docs/`, the slides, the
   words below and the 55 readings of `phase2-questions.md`.
4. **The handover to the work machine**: delete `dev/plans/` (it is history, and it ships);
   push the work as a branch; on the work machine run `dev/manual/check_azure_remote.py`
   against a real Azure DevOps project, then `purlin:audit`, `purlin:sign`, the push of the
   tag, the release.

## Words for the owner to read

Chosen by an agent where no decision gave them, gathered from `phase3-interfaces.md` ("Words
chosen for the owner to read") and `phase4-interfaces.md` ("Words chosen for the owner to read",
"Words chosen by a lane, word for word", and "The pages"). `<...>` is filled in. Words the
owner already accepted in decision 96 are not repeated.

| Where | What it says |
|---|---|
| Setup, the commit question | `Commit the files setup wrote? [y/N] ` |
| Setup, after the commit | `Committed <sha7>, the files setup wrote:` then each path, indented two spaces |
| Setup, when git refuses the commit | `The files setup wrote are staged and not committed: <git's own message>.` |
| Setup's commit | `chore(init): set up Purlin at the gate <gate>` |
| A project with no spec, not set up | `No specs found under specs/.` then `→ Run: purlin:init to set this project up.` |
| A project with no spec, set up over code | `→ Run: purlin:spec-from-code to write the specs this code already implies.` |
| A project with no spec, set up over no code | `→ Run: purlin:spec <name> to write the first spec.` |
| Setup outside git | `This is not a git repository. Run git init, then purlin:init.` |
| Setup, a typed gate it does not take | `<value> is not accepted for gate; it takes passed, strong or signed. Reading it as <gate>.` |
| Setup, `--gate` it does not take | `<value> is not accepted for gate; it takes passed, strong or signed. Nothing was written.` |
| Setup, the gate question | `What must be true of every rule before a version is finished?` |
| Setup, the breaking question | `Measure test strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per run. [y/N] ` |
| Setup, no runner file | `skipped the runner file (<reason>)` |
| Setup, a runner file written | `  it runs on <images>, the systems a proof in specs/ is tagged @env for that this machine is not.` |
| Setup, a file copied | `copied <source> to <rel>` |
| The evidence README | `What a run leaves behind for each feature: each proof's result on each operating system, the commit and the time.` and `` A run on your own machine writes `local/`, and `--commit` commits it under your own git identity. `` |
| The status, a gate it does not take | `<value> is not accepted for gate in .purlin/config.json; it takes passed, strong or signed. Reading it as passed; set it with purlin:init --gate <gate>.` |
| The status, `audit_parallel` it does not take | `<value> is not accepted for audit_parallel in .purlin/config.json; it takes a whole number from 1 to 16. Reading it as 4; fix the file by hand.` |
| The status, a spec naming no files | `1 spec names no files, so its tests run every time: <name>. Run purlin:spec <name> to add its > Scope: line.` and `<n> specs name no files, so their tests run every time: <names>. Run purlin:spec with each name to add its > Scope: line.` |
| The status, a source it cannot read | `<name>: the source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.` |
| A cell's reasons | `<System>: no run yet`, `passed on <Systems>`, `failing: <System>, <source>` |
| The settings tool | `A change needs a key; nothing was saved.`, `<key> is now <value>; saved to .purlin/config.json.`, `No Purlin project root at <root>: .purlin/config.json is not there. That root came from <source>.` |
| A spec's warnings | `` <feature>: 1 line under ## Rules is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec <feature>. `` and `<feature>: > Requires: names <other>, which is not an anchor, so its rules do not apply. Run purlin:spec <feature>.` |
| Evidence ignored | ` Run purlin:test <feature> to write it again.` and ` Run purlin:test --remote to write it again.` after the reason |
| A run's refusals | `purlin: --commit belongs to --test and --audit; a remote run commits on the runner. Run purlin:test --remote without --commit.` and `purlin: no spec named <name> under specs/. Run purlin:status to see the specs this project has.` |
| A run, evidence missing | ` Run purlin:<action> --arm-timeout <seconds> to give it longer.`, ` Check its command and report in the tests setting of .purlin/config.json, then run purlin:test.`, ` Check that its test ran and was not skipped, then run purlin:test.` |
| A run, a suite problem | ` Fix the tests setting in .purlin/config.json, then run purlin:test.` |
| The tests table | `# Tests at <sha7>, with changes that are not committed` |
| Test comments | `<file>:<line> names <feature> <ID> and no test follows it. Put the comment directly above a test, or run purlin:build to repair it.`; `The report's <case> matches <n> tests in <files>, so its result is not counted. Give the tests different names, then run purlin:test.`; `<file>:<line> names <feature> <RULE-N>, which has proofs; a comment names one of its proofs. Correct the comment, or run purlin:build to repair it.` |
| A remote run with no program to wait with | `purlin:test --remote waits for the run with the GitHub CLI, gh, which is not installed, so nothing was pushed. Install gh, then run purlin:test --remote again.` (and the Azure CLI form) |
| A remote run no runner picked up | `No run registered for <branch> within 60 seconds, so the run branch was deleted and nothing came back. Check that the git host runs <workflow path> on a push to run/*, then run purlin:test --remote again.` (and the Azure form) |
| A remote run that failed | `The run failed on the git host. The table below is what came back.` |
| A remote run's refusals | ` Add one with git remote add origin <url>, then run purlin:init.`, ` Make one with git switch -c <name>, then run purlin:test --remote again.`, ` Check that git push origin works from this checkout, then run purlin:test --remote again.` |
| A runner outside its checkout | `<path> is not the project root this job checked out, so no evidence was committed.` |
| Proofs for another system | `Proofs in specs/ are tagged @env for <Systems>, which this machine is not, so only a runner can prove them.` |
| The runner templates | `The matrix holds one job for each operating system a proof in specs/ is tagged @env for that the machine running setup is not, and no other.` and `The run caps each test command at an hour of its own.` |
| The breaking tool | `mutation_engine names "<x>", which is not an engine: set it to none, auto, mutmut, stryker or stryker_net` |
| Drift | ` Run purlin:test <feature>.`, ` Add each to a spec's > Scope: line with purlin:spec.`, ` Run purlin:build.`, ` Run purlin:test.` after its lines |
| Signing | `The signature commit was not made: <git's own message>. Nothing was signed; run purlin:sign again once git can make a signed commit.`; `No tag: <tag> is already written. Run purlin:sign --release <name> to name another.`; `No tag: the committed evidence still has work left to do, so no evidence package was committed. Run purlin:test --commit, then purlin:sign.`; `  <feature> <RULE-N>   does not count until the spec names its files: purlin:spec <feature>` |
| No version | `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.` (and the `purlin:export` form) |
| What the audit found | `No audit has read this rule's text, proof and test yet.`, `Strong. It found nothing.`, `Strong.`, `Weak.`, `Undecided. The AI audit could not decide, so the rule reads weak until its proof or test changes.`, `  Read by <model> at <at>.` |
| Test strength | `Test strength <p>%, against a minimum of <m>%.` |
| No test, terminal and page | `  No test yet. Run purlin:build <feature>.` and `No test yet. Type purlin:build <feature> in Claude Code.` |
| Anchors | `<name>: no anchor named <name> carries a git source. Run purlin:status to see the anchors this project has.`; `  1 rule. Run purlin:status to see it.`; ` Run purlin:status <name> to see its rules.`; ` Commit it as anchor(<name>): sync (<new7>), then run purlin:test.`; `No Purlin project root found. Pass --project-root <dir>.` |
| The dashboard | `Type purlin:sign <feature> <RULE-N> in Claude Code.`, `Back to the board`, the theme button `Dark theme` or `Light theme`, `The working tree has uncommitted changes, so what is on this board is not what a commit would carry.` |
| The references | the glossary's `runner file`, `scope` and `anchor` sentences; the writing style's sentence on capitals; the quality guide's paragraphs on a library's public names and a list of like inputs; the spec-from-code skill's five reasons and what a caller reaches; the spec skill's "Ids"; the test skill's comparison; the command reference's `purlin:init` sentences; the release notes of K5.10 (`phase4-contracts.md` K5) |
| Phase 3's reference prose | the exit-code table of `references/purlin_commands.md`, the `no_scope` row of `hard_gates.md`, the git-host sentence, the package's kinds sentence, the anchor source paragraphs (`phase3-interfaces.md`, "Words chosen for the owner to read", items 1 to 11) |
| The upgrade | `Write <path>, one job per operating system your specs name that this machine is not?` |
| The pages | every sentence the four page lanes wrote, listed per lane in `phase4-interfaces.md`, "The pages" |
| Decision 99 | every sentence, rule and proof listed in `phase4-interfaces.md`, "Decision 99", "Words chosen, word for word": `> Highest-Proof:` in the spec format, the spec skill and the docs; the subject `purlin: specs, tests and settings`; the fixture folders setup leaves out; `Checked by hand.` alone once signed; the export skill's sentence; the evidence format and release-notes sentences integration wrote |
| Integration 2 | the rule and proof texts of "The pages", the table of rules handed over; `is signed and its signature does not count` in `hard_gates.md`, `spec_format.md`, the spec skill and the release notes; the comment `The whole-number part, as every surface shows a share: 69.6 under 70 reads 69%, never the minimum itself.` in `states.py` |

## Small things known and not fixed

- `purlin:test --all --commit` prints two blank lines between `86 proofs need Windows; ...`
  and `Evidence written to ...`, where the same run without `--commit` prints one.
- `purlin:audit --commit` prints two blank lines between the committed paths and
  `AI audit: <n> rules to read, <k> at a time.`
- `purlin:anchor add` given a local path that does not end in `.git` writes a `> Source:` line
  that `sync --check` and drift then read as not a spec kept in a git repository.
- A status of a project whose anchor names an `https` source reaches the network; the 0.9.5
  fixture's Figma anchor does, and printed `remote: Not Found` once in phase 4.
- `purlin:sign --all` that signs the last rule leaves `the version to tag`; a second bare
  `purlin:sign` writes the tag.
- The sign skill says `observation` where the audit's lines and the docs say `finding`.
- `specs/instructions/purlin_docs.md` uses RULE-1, RULE-2 and PROOF-1 to PROOF-9, numbers an
  earlier spec of that name held before it was deleted; the new rule took RULE-12.
- The calls each lane of phase 4 and of decision 99 left: `phase4-interfaces.md`, "Calls
  left", "The pages" and "Decision 99".
- Carried from the earlier handoff, not checked again: `purlin:init` without `--yes`, with its
  output piped, hung once in a scratch Go project; Vitest 4 would not install on this machine,
  version 3 is proven; text on a solid coloured badge measures under 7 to 1 (the owner chose to
  leave it); a hand check may be signed without a note (the owner chose to leave it).

## Open questions for the owner

None. Decision 99 answered the five this section held; the calls its lanes left are in
`phase4-interfaces.md`, "Decision 99", "Calls left".

## How to work, as the owner settled it

- **Decisions close before anything launches.** Ask with the question UI, with options and
  consequences, and wait.
- **Ask from the root.** Say what a thing is for in plain words before asking about it. No
  function names, no file names, no term that has not been explained. Offer the option that
  removes the mechanism. The owner is simplifying Purlin with every answer.
- **Maximum parallelization, cut by ownership of files.** Each agent is Opus, has its own
  worktree and its own scratch folder, and owns files no other agent writes. What one produces
  and another consumes is fixed word for word before they start. Merges are fast-forward.
- **No push, no pull request, no tag, no audit and no signing by any agent**, but the one
  temporary run branch a remote run pushes.
- **Acceptance is the full sweep**, `bash dev/run_tests.sh`, plus this repository run through
  its own tool with every marker tied. Never edit a number to make a sweep green.
- **Look at anything visual** with playwright from the `.venv`, at 1500, 1280, 1024, 768 and
  390 pixels, both themes, before telling the owner it is done. A value never breaks inside
  itself; neutral text measures at least 7 to 1.
- **A clean release.** Nothing that represents earlier functionality stays: no compatibility
  reader, no test that a removed thing is absent, no table of removed words.
  `RELEASE_NOTES.md` is the one place history is kept, and what an upgrade from 0.9.5 needs is
  the one exception in code.
- **A page says what is**, checked against the code, in the words of
  `references/writing_style.md`, and every statement on it is held by a rule, a proof and a
  test (decision 64).
