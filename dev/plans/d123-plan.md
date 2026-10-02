# Decisions 122 and 123: the build

Written by the coordinator on 2026-10-02 against `main` after the base commit. Decision 122's
plan is `dev/plans/d122-plan.md` and stands, with the changes of section 1 here. Decision 123 is
in `dev/plans/three-levels.md`; its research is `dev/plans/audit-research.md`; the audit page,
`docs/audit.md`, is already written for it and is the model for its words.

Seven lanes, all local, each in its own worktree. Nothing is pushed, tagged or signed.

## 1. What changes in decision 122's plan

A seventh lane, `audit`, is cut out of `run` and `words`. No two lanes own one file.

| File | Was | Now |
|---|---|---|
| `scripts/review/audit_run.py`, `scripts/review/ai_audit.py`, `dev/fake_claude.py`, `specs/review/ai_audit.md`, `dev/test_ai_audit.py` | `run` | `audit` |
| `references/review_criteria.md`, `docs/audit.md`, `skills/audit/SKILL.md`, `dev/test_skill_audit.py`, `specs/skills/skill_audit.md` | `words` | `audit` |
| `scripts/review/targeted_break.py`, `specs/review/planted_bug.md`, `dev/test_planted_bug.py`, `dev/test_ai_audit_tests_named.py` | nobody | `audit` |

- Section 2.9 of the d122 plan (no cost, no call count) is the `audit` lane's, with the grep of
  the `run` lane's acceptance that goes with it. `ai_audit` RULE-45 and PROOF-121 go with their
  test.
- Section 6.7's edits to `skills/audit/SKILL.md` and `references/review_criteria.md` are the
  `audit` lane's. Its edit to `docs/audit.md` is already made. Its edits to
  `docs/running-and-evidence.md`, `references/purlin_commands.md` and `RELEASE_NOTES.md` stay
  with `words`.
- The owner answered d122's question 2 with B: "one model call for each rule" leaves every page.
  A page says the model is asked for a small bug for each proof and for its reading, with no
  number. The `audit` lane applies this in its three pages, `words` in every other.
- The owner answered d122's question 1 with A, as the plan builds.
- `words` also brings every other page that says how the bug is chosen in line with section 3
  here: grep `docs/`, `skills/`, `references/`, `agents/purlin.md`, `README.md` and
  `RELEASE_NOTES.md` for `planted`, `plants` and `bug`. `RELEASE_NOTES.md` 0.10.0 gains one
  sentence: `The audit aims each planted bug past its proof's test, and shows the case the AI
  says a surviving bug breaks.`
- The formats: `evidence_format.md` and `package_format.md` gain the two fields of section 2 at
  integration, by the coordinator, each one version above what d122's lanes leave. No lane
  writes them for decision 123.
- Merge order: `setup`, `run`, `audit`, `collision`, `signoff`, `surfaces`, `words`.

## 2. Decision 123's contract (lane `audit`)

Nothing outside the lane's files changes for it. A planted bug's entry under `breaks` is handed
through the evidence, the payload and the package as it is, and every surface prints the strings
of `findings`, so the two new fields and the one new finding need no other lane.

**The request** (`ai_audit.REQUEST_BUGS`), in place of today's three lines:

```
Plant one bug for each of: PROOF-1, PROOF-2.
Each proof's test is shown above. For each proof, make the smallest change to one of the files
below after which what the proof says no longer holds: the case the proof names gives a
different result from the one it names. Choose the change the proof's test, as it is written,
is most likely to miss: a value it never compares, a case other than the proof's, an expected
value taken from the code. Where the test checks the proof's case and its result, make the
plainest such change. Never a change that leaves the proof's case as it was, and no comment
about the bug.
```

**The reply's part for a proof** (`ai_audit.REPLY_PARTS`, `targeted_break.parse_answer`):

```
=== PROOF-1 ===
aim: past the test
case: <the proof's case; the result the proof names; the result the changed code gives>
file: src/age.py
before:
<the exact lines>
after:
<the lines>
```

- `aim:` is `past the test` or `plain`. Any other word, or no `aim:` line, is recorded `plain`.
- `case:` is one line. It is kept as written, outer spaces cut, at most 300 characters.
- `no break: <why>` stands as today, for a proof no change to those files can break.
- A part that names a change and no `case:` line, or an empty one, is not planted:
  `not made`, `why` exactly `the answer named no case of the proof`, cause `answer unusable`.
- A change that differs from the lines it replaces only in blank lines and comment lines is not
  planted: `not made`, `why` exactly `the change touches only a comment`, cause `answer
  unusable`. A comment line is one whose first characters after its indent are `//` in any file,
  or `#` in a file ending `.py`, `.sh`, `.bash`, `.rb`, `.yml`, `.yaml` or `.toml`.
- Both checks come before the copy is made and before any test runs.

**The entry under `breaks`** gains `aim` and `case`, strings, beside `file`, `line`, `before`,
`after`, `result`, `why` and `break_key`. An entry kept from an earlier audit that carries
neither reads `plain` and `''` wherever it is read.

**The findings.** A bug that survived adds two strings to the rule's `findings`, in this order:

```
PROOF-2: the test still passes when src/auth.py:12 reads "return 200"
PROOF-2: the AI says this breaks: a wrong password; the proof says 401; the changed code gives 200
```

The second is `targeted_break.AI_SAYS = '%s: the AI says this breaks: %s'`. It is added only
where `case` is not empty, and a kept `survived` result adds both again from its entry. The
audit prints each as it prints any finding. No verdict rule changes: decision 121 holds.

**What goes** (d122 section 2.9): the two printed lines, `.purlin/runtime/audit_run.json`,
`write_costs`, `_cost`, `cost_usd`, `seconds`, `spent`, `EXPERIMENTAL`, the fake's `cost`,
`ai_audit` RULE-45 and PROOF-121 with the test. The docstrings say what is.

**`references/review_criteria.md`** is sent to the model verbatim, so it is rewritten with care:

- "The planted bug" and "What the model is sent, and what it decides" say what this section
  says: the aim, the case, the two refusals, the second finding. `One call per rule` leaves the
  page as a count; the page says the model is asked for a small bug for each proof and for its
  reading. The command block stays.
- "What the audit reports" loses its two bullets on calls and cost and the sentence on
  `.purlin/runtime/audit_run.json`.
- Checks 4 and 6, "Why": `Model-written tests tend to capture what the code actually does
  rather than what it should do` and `model-written tests drift to the code's actual behaviour`
  each become a sentence saying what Konstantinou et al. measured: shown buggy code, a model
  more often rejects the right expected answer. Nothing else under "Heuristic spot tests"
  changes.

**`skills/audit/SKILL.md`**: step 2 of its list reads `The model is asked for a small bug for
each proof, aimed past that proof's test, and for its reading.`; Step 2's block and bullets are
d122 section 6.7's, with the second finding line added and one bullet for it: a line
`PROOF-N: the AI says this breaks: ...` is the model's claim about which case the bug breaks;
read it to judge the finding. The front matter's `description` is d122 section 6.9's.

**`docs/audit.md`** is already written. The lane checks it against what it builds, corrects
any line the code does not print as shown, and keeps the page's four tests passing.

**The rules and proofs.** The lane writes them, by `references/spec_quality_guide.md`, into
`specs/review/ai_audit.md` (next rule 46, next proof 125) and `specs/review/planted_bug.md`
(next rule 15, next proof 22), and reports each word for word. They hold at least:

- the request's instruction, by the sentences a reader can find in it;
- the reply's `aim:` and `case:` lines and what each reads as when missing;
- the two refusals, each with the reason printed;
- `aim` and `case` in the entry under `breaks`;
- the second finding, directly after the first, for a bug planted now and for a kept one;
- that a caught bug adds no finding.

Reword any rule or description that still says how the bug is chosen in the old way
(`planted_bug`'s description, `ai_audit` RULE-2, RULE-4 and their proofs where they count
calls as a fact a person reads). A rule that holds the call as a mechanism (RULE-3, RULE-4's
one request per rule) stays: it is how the code works, not a statement in a doc.

**The tests run on sample projects.** In the owner's words: "use sample projects as the tests
for the actual proofs for the rules." Each new proof's test builds a small project at test
time, runs the audit there with the fake `claude`, and reads what the audit printed and wrote.
No test audits Purlin's own code and none reaches a real model. One helper builds the sample
lab project of the trial (`dev/plans/audit-research.md`, section 2): the spec `sample_intake`
with its 8 rules and 12 proofs, `src/intake.py`, and `tests/test_intake.py` with its three weak
tests. The source is under
`/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/0b911df6-a4da-4d86-9e09-dc4ed8c6bce2/scratchpad/audit-measure/labconnect-intake/`;
copy its three files' text into the helper, since that folder is not kept. At least these
proofs use it, with the fake answering what the real model answered in the trial:

- PROOF-5's test takes its expected age from the code's own helper. The reply rounds that
  helper to the nearest hour, `aim: past the test`, with its case. The bug survives, the rule
  reads `weak`, and both findings are printed.
- PROOF-6's test checks the proof's case. The reply sets the limit to 73, `aim: plain`. The bug
  is caught and the rule reads `strong`, with no finding.
- A reply for PROOF-3 that returns the record without storing it survives, and the second
  finding carries the model's case word for word.

## 3. The words a person reads, decision 123

| Line | Where |
|---|---|
| `PROOF-2: the AI says this breaks: <case>` | the audit, the strong cell's findings, the dashboard's `Audit` panel, the sign-off's list |
| `No bug was planted: the model's answer for PROOF-2 could not be used: the answer named no case of the proof.` | the audit, under a rule |
| `No bug was planted: the model's answer for PROOF-2 could not be used: the change touches only a comment.` | the audit, under a rule |

A page says: an AI reads the proof, its test and the code, and writes the one small bug that
test is most likely to miss; the bug must break the case the proof names; where the test leaves
no way past, the AI writes a plain bug; a surviving bug is shown with the case the AI says it
breaks, and a person judges it.

## 4. The lane brief

Every lane gets this, with its name, and reads in this order: `CLAUDE.md`;
`references/writing_style.md`; `dev/plans/three-levels.md`, decisions 100 to 123 (search
`100. **`); `dev/plans/d122-plan.md` in full; this file in full; `dev/plans/qa-real-skills.md`
where its findings are its own; `references/spec_quality_guide.md` before writing a rule or a
proof.

- **Where.** `git worktree add /Users/richlabarca/LocalCode/purlin-wt/d122-<lane> -b
  lane/d122-<lane> main`, run from `/Users/richlabarca/LocalCode/purlin`. Every edit, run and
  commit happens in the worktree. Never edit the main tree. A scratch folder of your own:
  `/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/789cd831-abdf-4688-a6d0-bc057ca323b9/scratchpad/lane-<lane>/`.
- **What.** Only the files your lane owns (d122 section 5.2, as section 1 here changes it). A
  change you need in another lane's file is not made: build the rest and report it.
- **How.** Each fix starts from a test that fails for the fault it fixes, seen failing first.
  Every rule and proof is written to `references/spec_quality_guide.md`; every `> Highest-*`
  line covers its numbers; a number is never used again. Every line a person reads is the
  plan's, word for word; where the plan gives none, choose one by `references/writing_style.md`
  and report it. Decision 44 binds: what goes is deleted outright with its tests.
- **Formats.** A change to a file under `references/formats/` goes in the same commit as its
  code, with `> Format-Version:` as d122 section 7 says.
- **Tests.** `export PATH=/Users/richlabarca/LocalCode/purlin/.venv/bin:/opt/homebrew/opt/dotnet@8/bin:$PATH`
  first. Acceptance is your lane's in d122 section 5.2 (the `audit` lane's is section 2 here:
  `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, `dev/test_planted_bug.py`,
  `dev/test_plain_checks.py`, `dev/test_skill_audit.py` and `dev/test_purlin_docs.py` pass, and
  `git grep -n -i -E 'cost_usd|total_cost|audit_run\.json|CALLS_|EXPERIMENTAL' -- scripts
  dev/fake_claude.py dev/test_ai_audit.py` is empty), then `bash dev/run_tests.sh --fast`, with
  every failure either yours to fix or named in your report as waiting on another lane. No
  test reaches a real model.
- **Traps.** Never `git checkout -- specs/`. Stage no generated file:
  `scripts/report/purlin-report.html`, `.purlin/evidence/**`, `.purlin/report-data.js`,
  `docs/images/*.png`. No dollar figure and no count of model calls in any line you write. No
  emoji. No push, no tag, no `purlin:sign`, no `purlin:audit` of this repository, no cloud
  session, no subagent.
- **Commits.** Prefixes from `references/commit_conventions.md`, one logical change each, ending:

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01TrC5fNdoZhxzRBgPFJFx6Z
  ```

- **Finishing.** `git rebase main` in the worktree, the acceptance again, `git status` clean.
  Then write `dev/plans/d122-reports/<lane>.md` in the worktree and commit it: what was built;
  each rule and proof added, reworded or deleted, word for word; each `> Highest-*` before and
  after; what was seen failing first; every line a person reads that you chose; every call you
  made that the plan did not; what is left or waits on another lane. End your final message
  with the branch, its head and the acceptance's last line.

## 5. Integration, by the coordinator

d122 section 8, with: the seven merges in section 1's order; the two formats' fields for
decision 123; the audit page's and the dashboard's look, both themes; the Windows run; then the
audit of Purlin itself, once: `signatures`, `package`, `evidence`, `evidence_writer`,
`ai_audit`, `planted_bug`, `plain_checks`, then `run_script`, `reports` and `specs`, each with
its own `--feature`, the results committed; then a sanity check across the project; the deck;
the plan files of finished rounds removed; the handoff.
