# Handoff, 2026-09-30

For the session that continues Purlin 0.10.0. Read this, then `dev/plans/three-levels.md`
decisions 60 to 100 (together with this file they are the product as the owner settled it), then
`dev/plans/next-agent-prompt.md`, the prompt that session is given.

## Where the tree is (2026-10-01, end of the long session)

- `main` is local only. Decisions 100 to 103 are built in code and tests. Decisions 104 to 115 are
  decided and their SPECS are on `main` (408 rules, 823 proofs, after a weight pass from about
  700), but the code and tests are not built: `main`'s specs run ahead of its code, its sweep may
  fail in places, and the dashboard shows many rules with no test and about 1,600 test comments
  to correct. That is expected until the build.
- Decision 115's text is in `three-levels.md`; its four spec rules are Step 1 of
  `next-agent-prompt.md`.
- The audit's heuristic spot tests are official in `references/review_criteria.md`, with their
  research; `docs/audit.md` explains the audit and cites every paper by link.
- The deck (https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is, version 86) has 11 slides for
  decisions 100 to 115, including the comparison with Spec Kit, Kiro, Ketryx and Cucumber and the
  audit slide; built by `dev/plans/deck/build_deck.py`.
- Two QA and product checks ran in the cloud: `sanity-qa-product.md` and `-2.md`. The second
  reached a signed release; decisions 105 to 107 answer it.
- Cloud credits: $127 of $250 were left before the second QA check; they expire 2026-11-05.
- About 50 worktrees under `/Users/richlabarca/LocalCode/purlin-wt/` and many `lane/*` and
  `specs/d110`, `d102/*`, `d103/*`, `sanity/*` branches (some pushed) can be deleted once the owner
  says so.

## What is left, in order

1. `next-agent-prompt.md`: decision 115's specs, the build plan, the build (lanes in the cloud,
   integration local), the cloud sessions archived.
2. The real-skills QA check: three real Claude sessions with the plugin, one feature, one
   collision, run on demand.
3. The remote run on Windows (not run since decision 100), a full reading of the docs pages,
   the owner's review, and the handover to the work machine.

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
An anchor is a set of rules for the whole project, counted, audited and signed once; no spec
names one. `purlin:sign` walks the rules left `to test by hand` or `to sign` and, at the gate
`signed`, when nothing else is left and every result came from committed work, writes the
evidence package and the signed tag. Purlin makes no claim of compliance: it hands evidence to
a system of record, which decides who was entitled to sign.

## What is left, in order

The prompt for the next session is `dev/plans/next-agent-prompt.md`.

0. **After decisions 102 and 103**: the remote run on Windows (`purlin:test --remote`) for the
   84 rules that wait for it; the anchors slide below; a full reading of the docs pages against
   the code, `docs/review-and-signing.md` and `docs/qa-guide.md` among them; a rerun of the QA
   and product check, with separate agents, against the new workflow (the release run and the
   sign-off walk); then the owner's first `purlin:test --release` and `purlin:sign` on a release
   branch for 0.10.0. Left by the lanes for the owner, in `d103-interfaces.md`: the spec
   format's `> Scope:` still required at `signed`, `CLAUDE.md`'s `package_format.md` row, and
   the release run printing the status before its own lines.
1. **After decisions 100 and 101**, in this order: the remote run on Windows
   (`purlin:test --remote`, pushing only its run branch); the slide on anchors, taken into
   `dev/plans/deck/build_deck.py` with these words and published: title `Anchors: rules the
   whole project must follow`; subtitle `An anchor is a set of rules for the whole project,
   proven by tests that run across all of it.`; card 1 `Written in this project`: `Write a rule
   once, such as no secret in the code. Tests across the whole project prove it, and no feature
   names it. A rule only some features need goes in each of those features' own specs.`; cards
   2 and 3 unchanged; card 4 `Design standards too`: `Design publishes its standards as an
   anchor. Tests across every screen prove them; a standard no test here can show is signed as
   not applying, or checked by the team that owns it.`; footer `Each anchor rule is counted,
   audited and signed once. Any change to the project ends its results and signatures, so
   anchors are signed last.`; a full reading of the docs pages against the code; then the QA
   sanity check, which the owner runs in a cloud session. The two docs screenshots were
   retaken at `30c97d29b`.
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

Decision 103's words are in `d103-interfaces.md`: section 7 of `d103-plan.md` under "Words
chosen for the owner to read", and each lane's own under "Words chosen by a lane, word for word".

Decision 102's words are in `d102-interfaces.md`: section 7 of `d102-plan.md` under "Words
chosen for the owner to read", and each lane's own under "Words chosen by a lane, word for word".

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
