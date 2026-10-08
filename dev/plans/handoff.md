# Handoff, 2026-10-08: decision 135 is built

Local `main` is green and not pushed. Decisions 100 to 135 are built. Nothing is signed or
tagged, and the owner has planned no signing. GitHub holds `main` (far behind local) and the
two `qa/` branches.

## Where it stands

| | Result |
|---|---|
| `bash dev/run_tests.sh` | 1675 passed, 0 failed, 13 skipped; 4 suites passed, 0 failed, run last, after every change |
| `purlin_run.py --test --all --commit` | 1683 markers tied, 0 not tied; 42 specs, 742 rules, every one passing, 1 of them graded by an AI |
| `python3 dev/windows_run.py` | ended `743 rules. 743 pass their tests, 1 of them graded by an AI.`, before one rule was removed |
| The audit | `The audit found 732 of 734 rules strong (99%): 732 strong, 10 spot-checked.` No rule is weak |
| `sign.py --show` | does not refuse; it opens `AI proofs run on claude-opus-5-5: 3 proofs, 3 runs each.` |

Formats: spec 25, anchor 12, marker 6, evidence 18, package 18, signature 18. The
dashboard's data is schema 20. The evidence file's own schema is `purlin-evidence/2`.

## What decision 135 built

A project can test, and keep evidence for, the prompts and skills it produces.

- **An AI proof is a proof like any other**, with an ordinary marked test, tagged with the
  models it is shown on: `@ai(claude-opus-5-5)`, `@ai(a, b, runs=10)`. It is a slow proof.
- **A graded proof carries two tags**: `@ai(<model>) @graded(<grader>)`. The grader is shown
  the proof's sentence, what the AI was given and what it produced, and judges by the
  sentence alone. A rule that passes with one reads `graded`, never `passed`.
- **No model is named in the settings.** The settings gain `runs` alone, 3 where not set.
- **The helper**, `scripts/ai/purlin_ai.py`: `run` (a skill or plugin in a real session, or
  instructions as a system prompt), `record` (an output the project's own test made) and
  `grade`. A test reads `PURLIN_AI` to start it.
- **A full run starts each AI proof per model, per model run**, and records every one. A
  model that gives no answer leaves the proof `not run`, never failed, and the warning
  `<model>: model not reached. <why>. Run purlin:test --all.` stays in the status and on the
  dashboard until a run reaches it.
- **Each model run keeps a folder**: `reply.md`, `transcript.jsonl`, `files/`, `input/`
  (what the AI was given) and `purlin.json`. The evidence names it by its sha256, and a
  sign-off commits the folders this machine holds beside the package.
- **The audit plants a wrong output** in a copy of a kept passing output and runs the
  proof's test on it. For a graded proof that tests the grader. A seventh spot test names a
  graded proof's test that never calls `grade`.
- **The sign-off** names each model and each grader, and its list, opened by `To read
  before you sign:`, holds each graded model run with the grader's reason.
- **The docs**: `docs/testing-ai.md` and `docs/graded-by-ai.md`, and a part in each page a
  reader is on. The deck has the slides `ai` and `graded`, published at version 142.
- **Who it is for**, added 2026-10-08: the README's part of that name, slide 3 rewritten
  (deck version 144; the owner edited its closing by hand) and the audit pages saying the
  audit is not a mutation testing package.
- **Purlin on itself**: three AI proofs on `claude-opus-5-5`, `skill_build` PROOF-55 and
  PROOF-56 (graded by `claude-haiku-4-5-20251001`) and `skill_audit` PROOF-64. A full run
  starts real sessions for them when a skill's file changed; `--clean` starts them all.

## The audit of every spec

Every spec was audited in four lanes, each finding worked by the build skill's steps.

- 92 rules were weak on a first read, about 1 in 8. 112 planted bugs got past a test; all
  but the ones named below were caught once the test held the value its proof names. 11
  proofs were settled with `--sound`, each reason recorded. The loose ends fixed after it
  put about 250 rules out of date; they were audited again, and 9 more weak tests were
  strengthened and settled. No code, rule or proof was
  changed to clear a finding, and no strengthened test failed on the code as it stood.
- The tests of pages were the weakest: a test that reads a page's text does not see a
  stylesheet hide it. Next: "nothing else" not held, and standard error not read.

Not strong, and why:

- The 8 rules of the anchor, `spot-checked`: no bug is planted for an anchor's rule.
- `evidence` RULE-32, `spot-checked`: its only proof is a Windows one.
- `planted_bug` RULE-8, `spot-checked`: the model found no bug it may plant.

## What a real session showed

A one-shot session on `claude-opus-5-5`, given a sample with one skill and one prompt and
the goal `Write the rules and tests for this skill and this prompt with Purlin, and get
them passing. Ask me nothing.`, set Purlin up, wrote 13 rules and 16 AI proofs, two of them
graded, wrote their tests and started the full run. All 16 passed 3 of 3 once the run was
let finish: 48 model runs. Two faults, both fixed in the skills on the owner's answers:

- It picked the models itself and did not say so. The spec skill now says: where you may
  not ask, name the model you are running on, pick a grader, and say so first.
- It ended its turn with the run still going. The test skill now says to wait for a full
  run to end before saying anything is done.

## For the owner

1. **Read `docs/testing-ai.md` and `docs/graded-by-ai.md`**: both are new.
2. **One proof, its own model runs.** Sixteen proofs made 48 model runs; proofs do not
   share an output. The owner kept that on 2026-10-07.
3. **A session has its permission checks off and can write outside its copy of the
   sample**, the plugin's own folder included. The docs state the limit.
4. **A changed tag reruns every model it names.** A model not reached, or a raised `runs`,
   reruns what is missing alone.
5. **Purlin holds no rule about leftover processes.** The owner, 2026-10-08: "I don't want
   the rule about leftover processes. That's not for purlin to manage." `purlin_output`
   RULE-3, its proof and its test are gone.
6. **The warning `model not reached` prints twice in one test run**: when the model gives
   no answer, and in the status the run ends on. The owner kept both on 2026-10-08.
7. **`TESTS` labels two rows on a rule's page**: the rule's state, and each proof's list of
   test files. The owner kept both on 2026-10-08.
8. **Left by earlier rounds, unchanged**: a rule can read `strong` while one of its proofs
   has no caught bug; a session runs the scripts directly where a skill names a command;
   a session's status tool keeps the code it loaded when it started.

## Found and not fixed

The ten loose ends the first audit left were fixed on 2026-10-08, on the owner's word, and
their specs audited again. What remains:

- **On Windows the audit ends no process a planted bug left** (`planted_bug` RULE-36 says
  so). A job object would do it. The owner, 2026-10-08: not now; build it in a round that
  changes that code anyway.
- **`run_script` RULE-105 reads `strong` with no bug planted for PROOF-277**: its test does
  not pass in a copy of the project.
- **`_run` in `purlin_run.py` starts every command with `Popen`** since the process-group
  fix. It has passed two Windows runs.
- `specs/instructions/purlin_docs.md` PROOF-22 says every link before `Sources` appears again
  "in the list". The research page gives `audit.md` again in the paragraph under the heading,
  not in a list item; the test holds papers to a list item and the project's own pages to
  anywhere under the heading.
- A change to `README.md` or a page under `docs/` puts the audit of `install` and
  `purlin_docs` (14 rules) out of date. The audit after the 2026-10-08 change found 9 of
  them weak with new bugs; each was settled with a stronger test.

## How to work, as the owner settled it

- **Decisions close before anything launches.** Ask with the question UI, one decision at a
  time, from the root: what the thing is for, in plain words, with everything needed to
  answer inside the question and the recommended option first.
- **The least change.** Before adding a concept, a format or a command, check whether
  something Purlin has already does the job.
- **Maximum parallelization, cut by ownership of files**, each lane in its own worktree
  under `../purlin-wt/` with its own scratch folder. Contracts are fixed word for word
  first.
- **Mind the usage.** The owner asked for it on 2026-10-08. Lanes run only their own tests
  and the project-wide checks; the coordinator runs one sweep at a merge. Use a smaller
  model for a small, exact change. Report at milestones, not at every step.
- **No push, no pull request, no tag and no signing by any agent**, but the run branch
  `python3 dev/windows_run.py` pushes and deletes.
- **Acceptance is the full sweep**, `bash dev/run_tests.sh`, plus this repository run
  through its own tool with every marker tied. Never edit a number to make a sweep green.
- **Run with the project's `.venv` first on PATH.** The system `python3` has no pytest.
- **Look at anything visual** with playwright from the `.venv`, at several widths and both
  themes, before saying it is done.
- **A clean release.** Nothing that represents earlier functionality stays.
- **The docs are short**, and the only pictures are simple flow diagrams.
- **The deck and the docs are changed when their source is.** Pushing waits for the owner.
- **A sign-off is optional**, and every line that names it says so.
- **A prompt for a new session is pasted into the conversation**, never written as a file.
- **No statement about cost** in anything that ships.
- **Any commit puts the sign-off's refusal back**; `purlin:test --all --commit` clears it by
  carrying the results forward. A changed test of a rule with a Windows proof needs a
  Windows run again.
- **Never change a script once the audit is current** unless the round means to audit
  again: the change ends its rules' results.
