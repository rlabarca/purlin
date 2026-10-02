# Prompt for the next session: decide how the audit plants a bug, then build decision 122

Paste everything below the line into a new session opened in `/Users/richlabarca/LocalCode/purlin`.

---

You are continuing Purlin 0.10.0, a Claude Code plugin for spec-driven development that uses
itself. Local `main` is green: 433 rules, every one passing on committed evidence, the Windows
rules included. Nothing is signed, tagged or pushed. Two things are open, and they are done in
this order: first you and the owner decide how the audit should plant a bug, from the research;
then you build that together with the fix round already planned as decision 122.

## Read first, in this order

1. `dev/plans/handoff.md`: the top section, "Where it stands".
2. `dev/plans/three-levels.md`: decisions 100 to 122 (search `100. **`); later wins. Decision 44
   is the clean release.
3. `CLAUDE.md`, `references/writing_style.md` (its section "Short and plain": the deck is the
   model for wording), `references/spec_quality_guide.md`, `references/review_criteria.md`.
4. `docs/audit.md`, `skills/audit/SKILL.md`, `specs/review/ai_audit.md`,
   `specs/review/planted_bug.md`, `specs/review/plain_checks.md`, `scripts/review/ai_audit.py`
   (`model_prompt` builds the one request a rule is sent), `scripts/review/audit_run.py`,
   `scripts/review/targeted_break.py`.
5. `dev/plans/d120-reports/audit-measure.md` (the planted bug measured on 46 rules) and
   `dev/plans/qa-real-skills.md` (three real sessions using the plugin; section 7 is the audit).
6. `dev/plans/d122-plan.md`: the fix round, planned and not started.

## How the owner works

- Decisions close before anything launches. Ask with the question UI, one decision at a time,
  from the root: what the thing is for, in plain words, no file or function name, no unexplained
  term, the recommended option first, and everything needed to answer inside the question.
- While a plan is being discussed, put it in the reply and stop there. Do not start the build
  until the owner says to.
- Short and plain. No statement about cost in anything that ships: no dollar figure and no count
  of model calls in a doc, a skill, a reference, the release notes, a slide or the audit's output
  (decision 122). Cost and speed are still things YOU weigh when comparing approaches, and you
  may measure them for the owner; the numbers stay in `dev/plans/`.
- Local agents only, cut by file ownership, each in its own worktree. No cloud sessions.
- No push, no tag, no `purlin:sign` against this repository. `purlin:audit` runs against this
  repository only where the owner asked for it (Step 4).
- Look at anything visual with playwright from the `.venv` before saying it is done.

## Step 1: read the research in detail (you, before any question)

The question the owner asked: "do any papers describe how to break the code in a non-biased
way?" Today the audit sends the model one request per rule holding the criteria, the rule, its
proofs, each test's source, the spot tests' findings and every file the spec covers, and asks:
"make the smallest change to one of the files below that would break what that proof says, so
that a test checking the proof fails." The model sees the test before it picks the bug, and the
request does not say whether to use that. A first pass over the literature, from page summaries
only, found two deliberate designs and that Purlin's request is neither:

- **The model never sees the tests.** Classic mutation testing, and LLMorpheus: the prompt holds
  the code with a placeholder; a separate tool runs each changed version against the tests.
- **The model sees the tests and is told to get past them.** Meta's ACH (the fault prompt holds
  the class, the existing test class and the concern; only faults that build and pass are kept,
  then an equivalence detector filters them), and Kiele et al. (ESEM 2026), which reports
  test-aware prompting giving verified faults 87.7% and 79.1% of the time on two benchmarks
  against 12.2% and 23.0% for test-blind.
- **The known risk of the second:** a change that alters nothing a test could observe, which
  then looks like a missed bug. LLMorpheus reports 20% of 517 surviving LLM mutants were
  equivalent; ACH reports its detector's precision and recall.

Read each paper itself, in full, not a summary: fetch the PDF or the HTML, and take exact quotes
with their section or page. Where a claim above does not hold on reading, say so. Start with:

- LLMorpheus: Mutation Testing using Large Language Models. https://arxiv.org/abs/2404.09952
- Mutation-Guided LLM-based Test Generation at Meta (ACH). https://arxiv.org/abs/2501.12862
- Beyond Rule-Based Mutation Testing: Test-Aware Mutant Generation Using Large Language Models.
  https://arxiv.org/abs/2609.35841
- Test vs Mutant: Adversarial LLM Agents for Robust Unit Test Generation.
  https://arxiv.org/abs/2602.08146
- Threats to the Validity of Mutation-Based Test Assessment.
  https://dl.acm.org/doi/pdf/10.1145/2931037.2931040
- Are Mutation Scores Correlated with Real Fault Detection?
  https://coinse.github.io/publications/pdfs/Papadakis2018hi.pdf
- Mutation Testing Advances: An Analysis and Survey. https://mutationtesting.uni.lu/survey.pdf
- Every paper `docs/audit.md` already cites under `Sources` (Just et al., FSE 2014; Petrović et
  al., TSE 2021; Inozemtseva and Holmes, ICSE 2014; Konstantinou et al., 2024; the 2026
  evaluation of model judges).

Then search for what is missing, and read what you find: how many LLM-made mutants per target
are needed before the result is stable; how equivalent mutants are detected or avoided cheaply;
whether one request can ask for several candidates; studies of which context in the prompt
changes the mutants (code only, code and tests, code and a specification, few-shot real bugs);
and anything on planting a fault from a written requirement rather than from the code, which is
Purlin's case: the proof is a sentence saying what must hold.

Write what you learn to `dev/plans/audit-research.md`: one entry per paper with the link, what
it did, the numbers, the exact quotes you will use, and what it means for Purlin. This file is
the source for the docs in Step 3.

## Step 2: discuss the approach with the owner, and iterate

Bring the owner a short comparison of the approaches the research supports, judged on three
things together: how well it finds a test that would miss a real mistake, what it costs to run,
and how long it takes. Say plainly what the evidence is for each and where there is none. At
least these are on the table:

1. Test-blind: the bug is chosen from the proof and the code alone.
2. Test-aware and told to get past the test, with a guard against changes that do not really
   violate the proof.
3. Both in one request: one ordinary violation and one aimed past the test; `strong` needs both
   caught.
4. Several candidates per proof, the cheapest that survives kept.

Things already decided that the approach must keep unless the owner reopens them (decision 121):
the result is `strong`, `weak`, `spot-checked` or not audited; a result reads `out of date` once
its rule, proof, test or code changes; only a test that ran and failed is a caught bug; no bug is
planted for an anchor's rule or for a proof tagged for another system; a rule is `strong` when at
least one proof had a bug caught and no spot test fired, each other proof named with its reason;
the model is started bare, with no tools, from an empty folder; the audit blocks nothing; a
surviving bug is shown to the person with the proof.

Give a recommendation. Expect to iterate: the owner may take several turns. When the approach is
settled, record it as decision 123 in `three-levels.md`, in the shape of the others, with the
owner's own words where they decided something.

## Step 3: what the docs must hold (the owner's requirement, word for word)

"Once we decide on the approach, it MUST include references and logic in our docs. The audit
page should stay simple at the top, but a detailed explanation of the reasoning behind the
approach with citations and quotes must be at the bottom."

So `docs/audit.md` opens as it does now, short and plain, in the deck's words, for a reader who
wants to know what the audit does and what its results mean. Below that, a section gives the
reasoning: what the choices were, what each paper found, the exact quotes, why Purlin does what
it does, and what it does not claim. Every source is linked and listed under `Sources`
(`purlin_docs RULE-15` holds this with proofs; keep them passing and extend them if the page
gains sources). `references/review_criteria.md` is the one home of what the model is sent; the
deck's `audit` slide and the `why` slide's audit row agree with whatever is decided.

## Step 4: the build

One build, local lanes, for two things together:

- **Decision 123**, the audit's approach, once settled: its rules and proofs, the request the
  model is sent, the docs of Step 3.
- **Decision 122**, `dev/plans/d122-plan.md`: findings 1 to 13 and 17 of the real-skills check,
  and the audit printing and recording no cost and no count of calls. The owner settled its two
  questions: a change to a spec reruns that whole spec's tests, said in one docs sentence; and
  "one model call for each rule" leaves the pages, which say instead that the model is asked for
  a small bug for each proof and for its reading. Its lane `run` owns the audit's code: fold
  decision 123's code into that lane or cut a lane `audit` out of it, and fix the contracts
  before the lanes start. Recount every `> Highest-*` and total against `main` first; the plan
  was read at `8d55f7010`.

Then integration on `main`, by one agent: the merges; `bash dev/run_tests.sh` to 0 failed;
`python3 scripts/run/purlin_run.py --test --all --commit` to the clean state; the dashboard
looked at in both themes; `python3 dev/windows_run.py` for the Windows rules; the handoff.

Then the audit of Purlin itself, once, on the final code, as the owner asked ("pick the next
best set of audits to do and do those. Make it a reasonably small job"): the specs `signatures`,
`package`, `evidence`, `evidence_writer`, `ai_audit`, `planted_bug`, `plain_checks`, then
`run_script`, `reports` and `specs`. Each feature takes its own `--feature`. Commit the results,
and look at the dashboard's `Audit` box, `Strong` column and a rule's `Audit` panel.

Last: bring `dev/plans/deck/build_deck.py` in step with what was built (read the live deck
first, https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is: the owner edits it), and remove the
plan files of finished rounds from `dev/plans/`, keeping `three-levels.md`, `handoff.md`,
`audit-research.md` and the deck. The owner approved that removal on 2026-10-01.

## Then stop and report

The sweep's and the run's numbers, the audit's results, every line a person reads that a lane
chose, anything left unbuilt, and the calls left for the owner.
