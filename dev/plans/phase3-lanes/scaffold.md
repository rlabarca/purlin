# Lane `scaffold`

You are lane `scaffold` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/scaffold`, branch `lane/scaffold`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/scaffold -b lane/scaffold main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-scaffold`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q9, Q14, Q15, Q16, Q37, Q60, Q65 and report questions 14, 15, 16, 47, 60; the
   report's "Test files that skip on Windows today" (line 3007); `skills/init/SKILL.md` whole.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/init/scaffold.py`
- `templates/config.json` (P1 changed it; leave it), `templates/gitignore.purlin`, `templates/evidence-readme.md`
- `specs/init/scaffold.md`, `dev/test_init_scaffold.py`
- `dev/test_init_e2e_wiring.sh`, `dev/test_init_e2e_gates.sh`, `dev/init_e2e_walk.sh`,
  `dev/test_e2e_build_changeset.sh`, `dev/run_tests.sh`, `dev/windows_skip.sh`
- `skills/init/SKILL.md` (195 of 250 lines), `specs/skills/skill_init.md`, `dev/test_skill_init.py`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q14** (decisions 70, 80): a later run of setup asks nothing before each file: the per-file
   `[Y/n]` goes (`Console.confirm`, `Plan.gated`, `Plan.allowed`, the comment around lines 573 to
   575). New proof: a second run at `--gate signed` on a project set up at `passed` asks no
   question and writes `gate: signed`. `skills/init/SKILL.md` lines 61 to 65 stop saying a later
   run asks before each write.
2. **Q15:** RULE-37 loses "an install from the marketplace leaves no file in the project naming
   the install"; PROOF-97 is re-pointed to RULE-21; RULE-21 holds both starting situations (this
   checkout at `strong`, a marketplace copy at `passed`).
3. **Q16:** `dev/test_init_e2e_gates.sh` and `dev/init_e2e_walk.sh` are deleted; the
   `E2E Init (gates)` line of `dev/run_tests.sh` goes; `dev/windows_skip.sh`'s header speaks of
   one test.
4. **Q60:** `dev/test_e2e_build_changeset.sh` is deleted with its `E2E Build Changeset` line in
   `dev/run_tests.sh`.
5. **Decision 94, setup's flag for adding a tool goes:** `--add` leaves `scaffold.py` (docstring
   line 5, `parse_args` around line 493, `resolve_tests` keeps only "an existing `tests` is
   kept", the names behind `Suites %s`); RULE-32, PROOF-32 and PROOF-98 go with their tests
   (around lines 1157 to 1175); `skills/init/SKILL.md` lines 59 and 67 to 68 go;
   `specs/skills/skill_init.md` RULE-2 drops `--add`, PROOF-23 is reworded, PROOF-8 goes;
   `dev/test_skill_init.py` around lines 122 and 376 to 386. The skill's lines 76 to 78 say the
   first test run suggests a command for each test tool it recognises, confirmed together
   (**PENDING OQ5**: it prints
   `Suggested tests setting: <the entries as one JSON array on one line>`, which the agent
   writes).
6. **Decision 94 and Q37, a tool that cannot run here counts as none** (C1.3): `engine_for` and
   `resolve_mutation` ask `mutation.runs_here(engine)`; on Windows a pytest project is not asked
   the breaking question and, in place of `NO_ENGINE` (which would say no engine breaks pytest
   code, untrue there), prints C3.2's setup line (**PENDING OQ12**):
   `Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.`
   With OQ12's second option it prints `Mutation testing is off: mutmut does not run on Windows.`;
   with its removal option it prints no mutation line for such a project. P2 landed the sentence
   as `scaffold.NO_ENGINE_HERE` (C1.11); print that constant. New proof with the system given as
   Windows. `_STRYKER_NOTE` stays as it reads (decision 96).
7. **Q9:** RULE-35 and PROOF-35 go with the test (around line 1120).
8. **Decision 96, both host lines, in one place** (C3.1 L1 and L2; **PENDING OQ7**): with no
   remote, the summary line reads `Gate <gate>. Suites <names>.` and the next line
   `No git host found.`; with a remote on a git host Purlin cannot use, the summary line reads
   `Gate <gate>. Suites <names>.` and the next line
   `This git host cannot run tests remotely. Everything on this machine works.`
   (`workflow.UNKNOWN_HOST`, which P1 set; print the constant); with GitHub or Azure DevOps it
   reads as today, `Gate <gate>. Suites <names>. Git host <host>.` The words
   `Git host not read from a remote` leave the file. With OQ7's option 2 each line closes the
   summary line instead (`Gate strong. Suites pytest. No git host found.`); with option 3 the
   no-remote case is as in option 1 and the upgrade's line is lane `update`'s; with option 4
   setup prints nothing for no remote and the unknown-host line stays on a line of its own after
   the summary line. RULE-14 and its proofs (PROOF-69, PROOF-70, and PROOF-44's line) quote
   what is printed; `skills/init/SKILL.md` lines 107 to 110 quote the two lines of decision 96.
   `workflow.NO_REMOTE` and `REMOTE_NO_REMOTE` stay.
9. **Q65, setup** (C1.9, C3.4; **PENDING OQ1**): `_existing_config` stops turning an unreadable
   file into "no settings"; setup prints `config_problem`'s sentence, writes nothing, exits 1.
   New rule and proof.
10. **Decision 95, the six tests.** The `gh` test (around line 946): its `os.name == 'nt'` skip
    goes; its search path adds git's own folder instead of a link; its stand-in `gh` and `az`
    have the exec bit on POSIX and are `gh.cmd` / `az.cmd` on Windows (C8). The walks stop
    reporting success where they did not walk: `purlin_skip_on_windows` in
    `dev/windows_skip.sh` prints its two lines and exits 1 on Windows (a suite judged by its
    ending has no "not run", so the file reads failed there). After item 3 the one file that
    sources it is `dev/test_init_e2e_wiring.sh`; the header comment says so. The Python walk in
    `dev/test_init_scaffold.py` keeps its skip. The `@env(macos)` tags on the walk's proofs are
    wave W's (plan section 6), not this lane's.
11. **The walk's fixture** (C8): the gate walk's greeting spec (`GREETING_SPEC`) tags its proof
    `@env(<this machine's system>)`, taken from `evidence.host_os()`, so its `--ci` steps write a
    section before and after lane `run`'s decision 95 work; its other assertions hold (no
    workflow is written for this machine's own system).
12. **The init skill:** the interpreter lookup (C9) at lines 50 and 160, reading
    `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" ...`,
    and the fallback sentence at lines 11 to 12 goes; decision 94: skill_init's rules say what the
    skill tells the agent (RULE-2: "gives the line that runs `scaffold.py`"); PROOF-24 (every flag
    the skill names is in `scaffold.py --help`) and PROOF-32 to 35 and 38 stay; Q40's reason
    (C11, **PENDING OQ13**): skill_init's damaged-copy proofs (about 23) leave the spec, each
    kept in its guarded test; with OQ13's second or third option they stay as they are.
13. **Split by claim and one case per proof** (C11): candidates scaffold RULE-5, 13, 14, 44, 45;
    skill_init RULE-1, 6, 7.

14. **Decision 95, the init skill's "What the runner runs"** (lines 142 to 155; C12, S1): the
    table's `run/*` row says the runner runs the marked tests, and the `signed/**` row reruns
    them. Each cell points at `references/hard_gates.md`, "Where a runner runs", for which tests
    a runner runs, in place of "the marked tests", and restates nothing. Cut as many lines as
    you add (250).

**You consume** P1's `UNKNOWN_HOST`, `NOT_A_GATE`, template and `runs_here`; P2's
`config_problem`. **You produce** C8's walk fixture.


## How to number, split and write proofs

- A new id is one more than the highest the spec file has held since it was last written whole
  (`git log -p --follow -- <spec>`); a deleted number is never reused.
- Every proof you write or reword holds one case (one starting situation, one action, what is
  seen) in at most 60 words, names no file of code, function or test framework, and has a test of
  its own with `# purlin: <feature> PROOF-<n>` directly above it. A proof whose test loops over
  gates, inputs or systems with one expected result becomes one proof per case (Q1, Q8).
- Split by claim (decision 94): split a rule of your specs where its text states two or more
  claims, its proofs fall into groups each showing exactly one, and no proof shows two. The first
  claim keeps the id; each other claim takes a new id; proofs keep their ids and text, only their
  `(RULE-N)` changes; markers do not change. Do not split a rule whose claims share every proof.
- Delete outright what is retired: no test that a removed thing is absent, nothing added to
  `dev/test_vocabulary.py`, no reader of an old spelling.
- A format you change updates its file under `references/formats/` in the same commit, with the
  bump the contracts name.

## How to test

```
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH
cd /Users/richlabarca/LocalCode/purlin-wt/scaffold
.venv/bin/python -m pytest dev/test_init_scaffold.py dev/test_skill_init.py -q      # your own files, whole
bash dev/run_tests.sh --fast                     # the fast sweep, in your worktree
```

If `.venv` is missing in the worktree, use `/Users/richlabarca/LocalCode/purlin/.venv/bin/python`.
Do not run the full sweep; integration runs it once.

Before you break code on purpose to see an assertion fail, confirm the test that runs it uses
`dev/fake_claude.py` or no model at all, that no real `claude` is on its `PATH`, and that it
reaches no real git host, `gh`, `az` or network service. Restore the file with
`git checkout -- <that file>`; never `git checkout -- specs/`.

A failure in a test file you do not own: check `phase3-contracts.md` C7. If the contracts predict
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that file.

## Limits

- Commit on `lane/scaffold` only, with the prefixes of `references/commit_conventions.md`, ending
  each message with the attribution lines your session gives. Push nothing, tag nothing, open no
  pull request.
- Run no `purlin:audit` and no `purlin:sign`, never start the real `claude` program or any real
  service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, screenshots.
- Keep each skill and `agents/purlin.md` within its line ceiling; a change cuts as many lines as
  it adds.
- A call no decision or contract makes: build the rest, leave that thing as it is, report it.
- Before you finish: `git rebase main`, rerun your files and `--fast`, fix your own files where a
  lane merged earlier changed a result the contracts predict.

## Report, as your final message

- The branch and its commits (sha and subject).
- For each spec you own: its highest RULE and PROOF id now, and its rule and proof counts before
  and after.
- Tests in your files before and after, and the `--fast` result.
- Every split, as `<spec> RULE-<old> -> RULE-<a> (<claim>), RULE-<b> (<claim>)`.
- Every proof deleted, moved or re-pointed.
- Every word a person reads that you chose because no decision or contract gave it.
- Every item left as it stands, and why.
- Every failure in a file you do not own.
