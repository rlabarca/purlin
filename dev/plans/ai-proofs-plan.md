# Decision 135: prompts and skills are tested like anything else; the build plan

Written 2026-10-06. It goes into 0.10.0, before any sign-off. Decision 135 is in
`dev/plans/three-levels.md`.

## 0. What it is for

The owner: "purlin must be able to create formal testing and validation evidence around a
codebase that produces AI prompts and skills as part of its output. it should work for things
like claude projects that create artifacts." And: "make sure we are doing these additions with
the least amount of change, in an elegant way.. dont just bolt this on."

Today a spec can cover a Markdown file, and a test can read it. That proves what a skill
says. Nothing helps a project prove what a skill or a prompt makes an AI do, record which
model it was shown on, or keep what the AI produced.

## 1. The design: one helper, two tags, one setting

A proof about an AI's behaviour is a proof like any other. Its check is an ordinary test, in
the project's own test tool, with the ordinary comment above it. Three things are new.

- **One helper**, `scripts/ai/purlin_ai.py`, which any test in any language can start. It
  runs a skill or a prompt on a sample and hands back a folder holding what came out.
- **Two tags** on a proof line: `@ai` and `@graded`.
- **One setting**, `models`, in `.purlin/config.json`.

Everything else is what Purlin already has, used as it is:

| Need | What already does it |
|---|---|
| Tie a check to a proof | the marker comment above the test |
| Run it rarely, and say when it is due | a slow proof: an `@ai` or `@graded` proof is one |
| Rerun only what changed | the full run's carry forward, and the fingerprint over the spec's files |
| A result per place it must hold | the per-system results of `@env`, here per model |
| Would the check catch a fault? | the audit's planted bug, planted in the kept output |
| Judgment a test cannot settle | `@manual`, as now |
| Keep what was produced | the test output kept with the package (decision 134) |

## 2. The owner's answers, so nobody asks again

| Question | Answer |
|---|---|
| How a prompt or skill is run | Both ways: a real Claude Code session with the skill loaded, and a prompt sent with its instructions as the system prompt. A Claude project's instructions are tested the second way. |
| What counts as passing | It runs several times and all must pass. Every run is recorded, pass or fail. |
| May an AI grade an output | Yes, as a third kind of proof, clearly marked. |
| What a result is tied to | The models the project's settings name: one result per model. |
| What output is kept | Kept on disk while working; committed with the package for a signed version. |
| `purlin:spec-from-code` | It drafts behaviour rules and sample cases for each prompt or skill. A person reads every one. It writes no test. |
| The version | 0.10.0. |
| What the audit plants | A wrong output: a kept output changed so it breaks what the proof says, and the same test run on it. No model runs again. |
| How a graded rule counts | It counts as passing and reads `graded`, never `passed`. |
| The tags | `@ai` and `@graded`. |
| Where the check lives | An ordinary test plus the one helper. No checks written in the spec. |
| When they run | They are slow proofs. |
| The grader's criteria | The proof's own sentence, and nothing else. |

## 3. Each piece

### 3.1 The helper

`scripts/ai/purlin_ai.py`, Python 3.9, standard library only, consumer-facing and stable.

```
purlin_ai.py run --skill <folder> | --plugin <folder> | --instructions <file>...
                 [--project <sample folder>] --input <file> | --say "<text>"
purlin_ai.py grade --feature <name> --proof PROOF-N
```

- **`run`** prints the folder that holds the output and exits 0, or says why it could not run
  and exits 2. The folder holds `reply.md`, the last thing the AI said; `transcript.jsonl`,
  what the session did; and `files/`, every file it wrote or changed in the sample.
  - `--skill` or `--plugin` starts a real Claude Code session, in a copy of `--project`, with
    that skill or plugin loaded and no other. `--instructions` sends those files as the
    system prompt, with no tools, as the audit starts its model.
  - Both go through the `claude` program, as the audit does. No key is asked for.
  - It reads three things the run sets: `PURLIN_AI_MODEL`, the model to use;
    `PURLIN_AI_OUT`, where to write; `PURLIN_AI_REPLAY`, a folder of an earlier output to
    hand back in place of running. A test never reads them.
  - Started by hand with none set, it uses the first model of the settings and a folder
    under `.purlin/runtime/ai/`.
- **`grade`** shows the grader the proof's sentence, read from the spec, and the output
  folder of the last `run` in this test. It prints `accept: <one reason>` and exits 0, or
  `reject: <one reason>` and exits 1. The grader is started bare, as the audit's model is.
  The grader is the model the setting `grader` names, or the first of `models`.

A test for an `@ai` proof calls `run` and asserts on the folder. A test for a `@graded` proof
calls `run`, then `grade`, and asserts it exits 0.

### 3.2 The two tags

On a proof line, beside `@manual`, `@slow` and `@env(...)`:

```
- PROOF-4 (RULE-2): With the sample report, the reply names the three findings by their ids @ai
- PROOF-5 (RULE-3): The summary states no fact the sample report does not hold @graded
```

- Each is a slow proof without `@slow` being written. `@slow` beside either is allowed and
  adds nothing.
- With `@manual`, either is a mistake, in the shape of the mistake `@slow` with `@manual` is.
- `@graded` without a call to `grade` in its test is named by the spot tests.

### 3.3 The settings

```json
{ "models": ["claude-opus-5-5"], "runs": 5, "grader": "claude-haiku-4-5-20251001" }
```

- `models`: the models these proofs are shown on. With none named and an `@ai` proof in a
  spec, the run stops and says which line to add.
- `runs`: how many times each is run on each model. 5 where it is not set.
- `grader`: optional.
- A change to `models` ends no result. A model with no result reads `not run`.
- The first test run that meets an `@ai` proof with no `models` setting asks, as it asks for
  the test command.

### 3.4 The run

For each `@ai` or `@graded` proof a full run reaches, and for each model named:

1. It starts that proof's own test `runs` times, each with the three variables set, each
   writing to its own folder under `.purlin/runtime/ai/<feature>/<PROOF-N>/<model>/<n>/`.
2. The proof passes on that model when every run passed. One failure fails it.
3. It records, for the proof, one entry per model: the model, how many passed of how many,
   and for each run its outcome and the fingerprint of its output folder.

It prints one line as each starts, `Running login PROOF-4 on claude-opus-5-5, 1 of 5`, since
these take minutes.

### 3.5 What a person reads

Fixed here. A line this plan does not give is chosen by `references/writing_style.md` and
reported.

| Line | Where |
|---|---|
| `    PROOF-4  passed  5 of 5 on claude-opus-5-5  tests/test_report.py::test_names_findings` | a proof under `purlin:status <name>` |
| `    PROOF-4  failed  4 of 5 on claude-opus-5-5  ...` | the same, one run failed |
| `    PROOF-5  graded  5 of 5 on claude-opus-5-5  ...` | a graded proof |
| `graded` | the rule's cell where it passes and any of its proofs is graded |
| `40 rules. 40 pass their tests, 6 of them graded by an AI.` | the closing sentence |
| `3 rules to test on claude-opus-5-5: purlin:test --all` | `Left to do`, a model with no result |
| `2 slow proofs to run: purlin:test --all` | `Left to do`, as for any slow proof |
| `Graded by an AI: 6 proofs, by claude-haiku-4-5-20251001.` | the sign-off's overview |

### 3.6 The audit

- The spot tests read the test as they read any test.
- **The planted bug is a wrong output.** For each `@ai` or `@graded` proof with a kept
  passing output, the model is shown the proof, its test and that output, and asked for the
  smallest change to the output that breaks what the proof says, aimed past the test. The
  change is made in a copy of the output folder, and the proof's test runs with
  `PURLIN_AI_REPLAY` naming it. The test fails: caught. It passes: the rule is `weak`, with
  the finding `PROOF-4: the test still passes when reply.md:12 reads "..."`.
- For a `@graded` proof this tests the grader: a grader that accepts a broken output is a
  weak one.
- A settle works as it does for any planted bug.
- No bug is planted in the prompt or the skill itself. The audit page says so.

### 3.7 The evidence and the package

- Each proof entry of a system's section gains `models`, absent for any other proof:
  `[{model, passed, of, graded, runs: [{result, output}]}]`, `output` the sha256 of the
  run's folder.
- For a graded proof each run also holds `grade`: the grader's model and its one reason.
- The evidence format and the package format each go up by 1, and the spec format for the
  two tags. The dashboard's data carries the same fields and its schema goes up by 1.
- At a sign-off, the output folders of the runs the package counts are committed under
  `.purlin/evidence/package/<version>.outputs/`, by the mechanism that commits the test
  tool's report (decision 134), and the package lists each with its fingerprint.
  `purlin:sign --check` checks them.

### 3.8 The sign-off

- Its opening names the models: `AI proofs run on claude-opus-5-5: 12 proofs, 5 runs each.`
- Its overview counts the graded proofs, and its list of findings can open them: each
  proof, the grader's model and its reason.
- It refuses, as for any result, where a model the settings name has no result recorded on
  the commit it signs.

### 3.9 The skills

- **`purlin:spec`** writes the two tags, and asks which a proof is where the sentence could be
  either: an exact check, a graded one, or a hand check. The quality guide gains the three
  side by side, with one example each.
- **`purlin:build`** writes the test for an `@ai` or `@graded` proof with the helper, and the
  sample it runs on, under the project's own tests folder.
- **`purlin:spec-from-code`**, where it finds prompts, skills, agent definitions or a Claude
  project's instructions: for each it drafts rules saying what the AI must do or produce,
  proofs that each name a sample input and the exact thing to check, and the tag for each. It
  writes no test. It says, as it hands over, that a rule read from instructions says what
  they ask for, not what the AI does.

### 3.10 The docs and the deck

The owner: "make sure you have specific parts in the docs for AI testing and audits and the
evidence and how it fits into the regulated workflow", and "we will also need an additional
slide about how purlin tests and audits AI". The docs are short (decision 133).

AI testing is folded into the pages where a reader already is, each treating an AI proof as
one more kind of proof, and one short page ties them together (the owner, asked: "Both:
folded in, plus one short page").

- **`docs/how-purlin-works.md`**: the kinds of proof side by side: a test, a test on an AI's
  output (`@ai`), graded by an AI (`@graded`), checked by hand (`@manual`).
- **`docs/specs-and-anchors.md`**: the two tags, one row each, with one example proof each.
- **`docs/running-and-evidence.md`**: several runs and all must pass; one result per model;
  what the evidence holds and what is kept.
- **`docs/audit.md`**: the audit plants a wrong output; what that shows about a check and
  about a grader, and what it does not show.
- **`docs/sign-off.md`**: what the signer is shown for graded proofs and models.
- **`docs/regulated.md`**: a part, "When the product is a prompt or a skill": the model is
  part of what was validated, a new model is a change, graded results are marked and a
  person may require a hand check on top, the kept output is what was observed; and the rows
  it adds to the workflow table and to "What your procedures decide".
- **One short new page, `docs/testing-ai.md`**, on the model of `docs/regulated.md`: a prompt
  or skill walked from rule to evidence in one place, with one flow diagram, linking to each
  section above. Listed in the index and in the README's list.
- **A new slide**, `ai`, "How Purlin tests and audits AI", after `audit`: built in
  `dev/plans/deck/build_deck.py`, both layout checks run, looked at, and published to the
  live deck in the same round.

### 3.11 Purlin on itself

Purlin ships ten skills and an agent definition. Three behaviour proofs are added, each on
the lab sample of `dev/sample_lab.py`, to show the feature on a real case:

- `skill_build`: given a weak rule, the session strengthens the test and settles it, and
  leaves the spec unchanged. `@ai`
- `skill_build`: given a proof too loose to write a check from, the session stops and
  proposes a sharper one. `@graded`
- `skill_audit`: asked to audit, the session runs the audit and names `purlin:build` for a
  weak rule. `@ai`

## 4. Limits, stated in the docs

- A claude.ai project cannot be driven from outside. Its instructions are tested as a system
  prompt; what claude.ai itself adds is not.
- Five passes of five show the behaviour held five times. They do not show it always holds.
- A grade is an AI's opinion against one sentence. It is marked as that everywhere.
- The audit tests the check. It does not show the prompt is a good one.
- A proof passes on the models named and says nothing about any other.

## 5. The lanes, cut by ownership of files

Contracts fixed first, by the coordinator, in one commit before any lane starts: the
helper's command line and its three variables (3.1), the evidence fields (3.7), the lines of
3.5, the setting's keys (3.3).

| Lane | Owns |
|---|---|
| `helper` | `scripts/ai/`, a new spec `specs/ai/ai_helper.md`, its tests, a fake of the `claude` program's session output for them |
| `run` | `scripts/run/`, `scripts/mcp/purlin/` (specs, markers, states, summary, status, fingerprint, config), their specs and tests, `references/formats/spec_format.md` and `evidence_format.md`, `references/drift_criteria.md` for the settings |
| `audit` | `scripts/review/` but `sign.py`, their specs and tests, `references/review_criteria.md` |
| `sign` | `scripts/review/sign.py`, `scripts/export/package.py`, their specs and tests, `references/formats/package_format.md` and `signature_format.md`, `references/evidence_and_signoff.md` |
| `dashboard` | `scripts/report/`, `payload.py`, `report_data.py`, `specs/dashboard/`, their tests |
| `skills` | `skills/spec`, `skills/build`, `skills/spec-from-code`, `skills/test`, `skills/audit`, `skills/sign`, `skills/status`, `agents/purlin.md`, `references/spec_quality_guide.md`, `references/glossary.md`, `references/purlin_commands.md`, `references/rule_examples.md`, their specs and tests |
| `docs` | `docs/`, `README.md`, `RELEASE_NOTES.md`, `dev/plans/deck/` |

Order: `helper` and `run` first, together; then `audit`, `sign`, `dashboard` and `skills`;
then `docs`, which describes what was built; then 3.11 by the coordinator.

No test of Purlin's own sweep reaches a real model: the helper's tests use a fake. The three
proofs of 3.11 are slow and reach a real model, as the install test does.

## 6. Then, on `main`

1. The merges. `bash dev/run_tests.sh` to 0 failed.
2. `purlin_run.py --test --all --commit --clean`, `python3 dev/windows_run.py`.
3. The audit of every spec in the project, since the owner held the audit back until this
   round ends, each finding worked by the build skill's steps, until the status reads as it did before the round: every rule passing, the audit
   current, the anchor audited last.
4. A real session, given a sample project that holds one skill and one prompt and the goal
   `Write the rules and tests for this skill and this prompt with Purlin, and get them
   passing. Ask me nothing.`, run as the goal-seek test of decision 130 was: judged from its
   log, with what it did wrong brought to the owner as questions.
5. `sign.py --show` not refusing. The handoff rewritten, the deck published, the memory
   updated.
