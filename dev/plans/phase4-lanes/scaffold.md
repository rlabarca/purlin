# Lane `scaffold` (phase 4, fan-out 1)

You are lane `scaffold` of phase 4 of Purlin 0.10.0: sanity check 3 applied, with the owner's
answers of decision 98. Purlin is a Claude Code plugin for spec-driven development that uses
itself. This brief is complete in itself; the files below are where its words come from. No
reviewer follows you: you check your own work with the self-check at the end and report.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-scaffold`, branch `p4/scaffold`, created
  from `main` after P1 merged:
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/p4-scaffold -b p4/scaffold main`.
- Scratch folder: `<the scratchpad directory your session gives>/p4-scaffold`.
  Nothing of yours goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`,
   `references/glossary.md`.
2. `dev/plans/three-levels.md` decisions 94 to 98 (decision 98 holds the answers of sanity check
   3); a later decision amends an earlier one.
3. `dev/plans/phase4-plan.md` sections 1, 4 (your row), 5, 6 and 11, and
   `dev/plans/phase4-contracts.md` whole: every line you print or quote is there, word for word.
4. `sanity-3.md` section 6 items 1, 2, 11, 13, 14, 28, 29, 36, 39 and 45; section 7 faults 6,
   10, 11, 12, 13, 14 and 20; section 8 items 2 and 9; section 11 question 10; section 5 rows 2,
   8, 12 and 35 and groups 1, 2, 3 and 29.
5. `scripts/init/scaffold.py` whole; `skills/init/SKILL.md` whole.

Section references such as "§6 item 5" are to `dev/plans/sanity-3.md`; "A<n>" is the owner's
answer <n> of decision 98; K-numbers are sections of the contracts.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/init/scaffold.py`
- `templates/config.json`
- `templates/gitignore.purlin`
- `templates/evidence-readme.md`
- `specs/init/scaffold.md`
- `dev/test_init_scaffold.py`
- `dev/test_init_e2e_wiring.sh`
- `dev/run_tests.sh`
- `dev/windows_skip.sh`
- `skills/init/SKILL.md`
- `specs/skills/skill_init.md`
- `dev/test_skill_init.py`

## The work

Build every item. Each names its source and the change; where it names a contract, the contract
is the words.

1. **Setup asks whether it may commit** (A10; K3.9; call 5). After the lines naming each file,
   and only when it wrote or changed a file git does not ignore, setup asks K3.9's question,
   commits on yes with `git add -- <paths>` and
   `git commit -m "chore(init): set up Purlin at the gate <gate>" -- <paths>`,
   and prints the lines of K3.9. `--yes` commits without asking. New rules in
   `specs/init/scaffold.md`: the question and its default; `--yes` commits; only setup's files
   go in (another staged file stays staged); a project with no commit yet gets the commit; git
   refusing prints the staged line. One proof each. Setup RULE-24 (no hooks) holds. The row
   "Setup commits none of the files it writes" of §5 is replaced by these rules.
2. **The init skill** (A10; §8 item 9; K5.6). "The questions" lists three; "Run it" gives K5.6's
   sentence; the `--yes` row reads as K5.6 gives it. skill_init's rules and proofs that read the
   questions and the flags follow; one new proof reads the commit question and one the sentence
   on passing `--mutation` and `--yes`. Within 250 lines.
3. **The breaking tool's folders** (fault 6; call 7). `mutmut_paths` finds the tests folder at
   any depth and keeps benchmarks and docs out. scaffold RULE-39 says so; new proofs: a project
   with `pkg/tests/test_a.py` and `bench/test_b.py` wires `pkg/tests` as the tests; a project
   with `doc/conf.py` and `examples/x.py` names neither as source.
4. **The Stryker line** (fault 10; K2.9 scaffold-5; call 6). Printed only where the engine is
   not installed, from the engine modules' constants; RULE-9 and PROOF-9, 105, 106 follow; one
   proof that an installed engine prints no line.
5. **The default shown once** (fault 11; scaffold-6). The breaking question is one line ending
   `[y/N] `; `MUTATION_QUESTION` loses its `[y/N]` and the prompt adds it, so the skill's
   quote still reads the same. RULE-45, PROOF-46 and the `asked()` helper follow.
6. **Each path named once** (fault 12; scaffold-13): a proof that setup with the breaks on names
   `.gitignore` on exactly one line.
7. **The runner lines** (faults 13, 14; §6 item 2; scaffold-8 to scaffold-11). The heading
   `A remote runner is written because:` and its reasons print only when the
   runner file is written; `No remote runner:` goes and the one line is
   `skipped the runner file (<reason>)`; `runner_label` goes; the note under a
   written file is scaffold-11. RULE-13 and RULE-53 say so; PROOF-13, 44, 66 follow; new proofs:
   no remote prints no heading; a missing prerequisite prints no heading.
8. **Not a repository** (§6 item 1; scaffold-1): PROOF-31's test quotes the whole line.
9. **The gate question** (§6 item 28; scaffold-2): PROOF-1, 53, 3 and skill_init PROOF-5, 33
   follow. Lane `words` quotes it in `references/hard_gates.md`.
10. **The gate refusal** (§6 items 11, 39; K3.4; scaffold-3, scaffold-4). `NOT_A_GATE` is K3.4's
    typed-answer line; `--gate` takes any word and refuses one that is not a gate with
    scaffold-4 on stderr, exit 2, nothing written. RULE-4 and PROOF-4 follow; one new proof for
    the flag. Lane `update` prints `NOT_A_GATE` (K6).
11. **`copied ... to ...`** (§6 item 36; scaffold-12): the `summary_paths` helper
    splits on ` to `; PROOF-18, 108, 109 hold.
12. **The evidence README** (fault 20; decision 50; call 16). `templates/evidence-readme.md` as
    K2.9 gives it; PROOF-47 compares bytes and holds; one new proof: at `passed` the file setup
    writes names no audit.
13. **The ending** consumed from P1: nothing to do but keep P1's proofs green.
14. **`.gitignore` names both** (§5 row 8): a proof that a new project's `.gitignore` names
    `/purlin-report.html` and one that it names `.purlin/runtime/`.
15. **`every test` at `passed`** (§5 row 12): a proof at `--gate passed` quoting
    `skipped the runner file (every test runs on this operating system, so nothing has to run remotely)`.
16. **`--plugin-dir`** (§5 row 35): a proof that setup run from a checkout of the plugin (not a
    marketplace copy) writes no file naming that checkout's folder.
17. **The gate question's choices, and the lines under a written runner file** (§5 groups 1, 2,
    3): one proof per line, each quoted as printed: the three choices, the skip line with no
    remote, scaffold-11 and
    `  it runs on a push to a run/* branch and on a push of a signed/* tag.`
18. **The templates' words** (§5 group 29, setup's part): proofs quoting the comments of
    `templates/gitignore.purlin` and the evidence README's first sentence.
19. **Adjust to `host`** (K6): PROOF-64, 129, 65, 51 and their tests quote host-10 and host-11.
20. **`> Highest-Rule:`** (K4.2) in `specs/init/scaffold.md` and
    `specs/skills/skill_init.md`.

**You produce** for other lanes: scaffold-1 to scaffold-13 (K2.9), K3.9, `NOT_A_GATE` (K3.4),
K5.6.

**You consume**: P1's `status.no_spec_lines`; host-10 and host-11 (K6); the engine constants of
`scripts/run/mutation/`.

## How to number, split and write proofs (contracts K7)

- A new id is one more than the highest the spec has ever held: the larger of its
  `> Highest-Rule:` and the highest of its own `RULE-`/`PROOF-` ids in
  `git log -p --follow -- <spec>` (its own lines only, not ids a proof or another
  spec names). A deleted number is never reused. Every spec you own carries
  `> Highest-Rule: <n>` after its last other `>` line, raised with every rule you add.
- Every proof you write or reword holds one case (one starting situation, one action, what is
  seen) in at most 60 words; a list of like inputs sharing one action and one kind of result is
  one case. It names no source file, no test and no test framework; a library's public names and
  error types may appear. It has a test of its own with `# purlin: <feature> PROOF-<n>`
  (in the file's comment syntax) directly above it.
- A statement of `sanity-3.md` section 5 gets a rule and one proof per line or case, each
  quoting the printed line character for character as the code prints it after your change.
- Split a rule of yours where its text states two claims whose proofs fall into groups each
  showing one: the first claim keeps the id, each other claim takes a new id, proofs keep their
  ids and text and only their `(RULE-N)` changes. List each split.
- Delete outright what is retired: no test that a removed thing is absent, nothing added to
  `dev/test_vocabulary.py`.
- A format you change updates its file under `references/formats/` in the same commit, with the
  Format-Version K4 names (none but the spec format changes number).

## How to test

```
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH
cd /Users/richlabarca/LocalCode/purlin-wt/p4-scaffold
.venv/bin/python -m pytest dev/test_init_scaffold.py dev/test_skill_init.py -q
bash dev/test_init_e2e_wiring.sh
bash dev/run_tests.sh --fast
```

If `.venv` is missing in the worktree, use
`/Users/richlabarca/LocalCode/purlin/.venv/bin/python`. Do not run the full sweep; integration
runs it once. A failure in a test file you do not own: check the contracts' K6. If K6 predicts
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that
file.

## Limits

- Commit on `p4/scaffold` only, with the prefixes of `references/commit_conventions.md`, each
  message ending with the attribution lines your session gives. Push nothing, tag nothing, open
  no pull request.
- Run no `purlin:audit` and no `purlin:sign`; never start the real `claude` program, a real git
  host, `gh`, `az` or any network service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`,
  `.github/workflows/purlin.yml`, `docs/images/**`.
- Keep each skill and `agents/purlin.md` within its line ceiling (status 100, test 120, build
  130, init 250, audit 105, sign 185, export 90, spec 210, spec-from-code 130, drift 150, anchor
  160, agent 135): a change cuts as many lines as it adds.
- A call no decision or contract makes: build the rest, leave that thing as it is, report it. A
  word a person reads that the contracts do not give: do not choose it; leave the line as it is
  and report it.
- Do not touch `/Users/richlabarca/LocalCode/purlin-wt/winfix-1`, `docs/` or `README.md`.
- Before you finish: `git rebase main`, rerun your files and `--fast`, fix your own files
  where a lane merged earlier changed a result K6 predicts.

## Self-check (run it, then report each result)

1. Every proof you wrote or reworded: one case, at most 60 words (count them), and a test of its
   own with its marker directly above it. List any that fails.
2. Every printed line you built or quote: character for character as K2 and K3 give it. Grep
   your files for each old form in K2 for your lane; none remains.
3. No generated file is staged: `git diff --cached --name-only main` names none of
   `scripts/report/purlin-report.html`, `purlin-report.html`, `.purlin/evidence/**`,
   `.purlin/tests.md`, `.purlin/report-data.js`, `.github/workflows/purlin.yml`,
   `docs/images/**`.
4. No id reused: for each spec you own, every RULE and PROOF id you added is above the highest
   that spec had ever held before you began (K7), and its `> Highest-Rule:` is its highest
   rule number now.
5. Break each of these on purpose, one at a time, run its test, see it fail, then restore the
   file with `git checkout -- <file>` (never `git checkout -- specs/`): (a)
   let `--yes` skip the commit: the `--yes` commits proof fails; (b) print the remote heading
   before the prerequisites are checked: the no-heading proof fails; (c) take `bench/` as the
   tests again: the nested-tests proof fails.

## Report, as your final message

- The branch and its commits (sha and subject).
- For each spec you own: its highest RULE and PROOF id, its `> Highest-Rule:`, and its rule
  and proof counts before and after.
- Tests in your files before and after, and the `--fast` result.
- Each item of "The work": done, or left and why.
- Every split, as
  `<spec> RULE-<old> -> RULE-<a> (<claim>), RULE-<b> (<claim>)`, and every
  proof deleted, moved or re-pointed.
- Every word a person reads that you had to write and the contracts did not give.
- Every failure in a file you do not own.
- The self-check: each of its five results, and for the breaks, the test that failed.
