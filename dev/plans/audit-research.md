# How the audit should plant a bug: the research

Written 2026-10-01 for decision 123. This file is the source for the reasoning section of
`docs/audit.md`. Every paper below was read from its PDF, not from a summary. Every quote was
copied from the PDF's extracted text and checked against it by script; a page is the PDF's page.
Where a paper was read in part, its entry says which part.

The owner's question: "do any papers describe how to break the code in a non-biased way?"

What Purlin does today: one request per rule holds the criteria, the rule, its proofs, each
test's source, the spot tests' findings and every file the spec covers, and asks the model to
"make the smallest change to one of the files below that would break what that proof says, so
that a test checking the proof fails." The model sees the test and is told nothing about it.

## 1. The answer in short

1. **No paper studies Purlin's case.** None gives a model a written requirement and existing
   code, asks for one small change that breaks that requirement, and judges one existing test by
   it. Everything below is the nearest evidence.
2. **No way of choosing the bug is unbiased.** A bug chosen without the test is mostly caught,
   and a caught one says little. A bug chosen to get past the test is a sharper probe, and some
   of what survives is no real bug. The papers that name the bias (Inozemtseva and Holmes; the
   ISSTA 2016 threats paper) say the two run in opposite directions.
3. **Today's request is the one form the evidence is against.** Tests in the request with no
   instruction about them gave no better bugs and cost twice the tokens (Wang et al., section
   4.1). Kiele et al. cite that result as the reason to instruct the model.
4. **Telling the model to get past the test finds far more gaps in one request**: 87.8% against
   12.2% of requests ended in a gap shown real (Kiele et al.). That was against thin tests and
   with a hidden test suite to check each survivor, which Purlin does not have.
5. **A survivor needs a guard, and a model's word is a poor one.** A model asked whether two
   versions behave the same scored F1 54% (Tian et al.); a model that called a change equivalent
   was right about 6% of the time (Straubinger et al.). The guards that worked were code or a
   test run: drop a change that only touches comments (ACH: 0.95 precision, 0.96 recall with
   that step), and count only a test that ran and failed.
6. **One request can ask for several bugs.** Three per request gave three, with 2.1% duplicates
   (LLMorpheus). No paper says how many make one test's result stable.
7. **Which bug comes back is not repeatable** on most hosted models, even at temperature 0
   (LLMorpheus; Atil et al.). A kept result is what holds it still.
8. **Three claims on today's audit page need rewording**: section 5.

## 2. A trial on Purlin's own case

The papers leave Purlin's case open, so the candidate requests were tried once, on 2026-10-01,
on the sample lab project the earlier measurement used (`labconnect-intake`: 8 rules, 12 proofs,
12 tests, of which 3 were written weak on purpose: PROOF-5, PROOF-7, PROOF-11). One call per
rule, the model started bare as the audit starts it (`claude-opus-5-5`), each bug planted in a
copy and only the proof's own test run. Each request was run twice: 48 calls, none failed.

The three requests:

- **Today's**: the tests are shown; "make the smallest change ... that would break what that
  proof says, so that a test checking the proof fails."
- **Blind**: no test in the request; "the smallest change ... after which what that proof says
  no longer holds: the case the proof names gives a different result from the one it names."
- **Both**: the tests are shown, and two bugs are asked for each proof. `plain` is the blind
  wording. `past the test` is "a second, different change after which what the proof says no
  longer holds, and which the proof's test, as it is written above, would still pass", with a
  guard: the model must write the proof's case, the result the proof names and the result the
  changed code gives, or write `none` and why.

| Per run of 12 proofs | Today's | Blind | Both: `plain` | Both: `past the test` |
|---|---|---|---|---|
| Of the 3 weak tests, found (run 1, run 2) | 3, 3 | 3, 3 | 2, 3 | 3, 3 |
| Of the 9 sound tests, a bug survived (run 1, run 2) | 0, 0 | 1, 1 | 0, 0 | 1, 4 |
| The model wrote `none` | | | | 6, 5 |
| Bug that could not be planted | 0 | 0 | 0 | 0 |
| Seconds per call, mean | 4.4 | 4.6 | 7.9 (both parts) | |
| Words the model wrote, relative to today's | 1 | 1.1 | 2.3 (both parts) | |

What the survivors on sound tests were:

- **Blind, PROOF-12, both runs.** The bug kept a barcode on record only for an accepted sample.
  The proof's case hands in an accepted sample twice, so the proof still held. The bug broke the
  rule somewhere the proof does not go. This is the kind the earlier measurement called
  irrelevant (1 of 93 there), and the blind request made it though it was told the proof's case
  must change.
- **Past the test, PROOF-3 (both runs), PROOF-6, PROOF-8, PROOF-9 (run 2).** All one idea. The
  proofs say a sample "is stored" with a status. The tests read the status from the record the
  call hands back. The bug hands back the right record and stores nothing, or stores another
  status. By the letter of the proof the test does not check storage. A person may call that a
  real gap or a reading too literal. The hidden-suite study has the same class and counts it
  apart: "ambiguous faults", 7 of 65.
- **Today's and `plain`: none.**

What the trial shows and does not:

- All three requests found the three weak tests. On tests this plainly weak the choice of
  request does not change what is found.
- The earlier measurement missed PROOF-5 with today's request; this time today's request found
  it twice. `plain` missed it once of twice. So a miss is partly chance: the bug that exposes
  PROOF-5 is one in the helper the test also calls, and the model does not always pick it.
  `past the test` picked it both times, because the request sends it there.
- `past the test` raised a flag on 1 and then 4 of 9 sound tests, and which ones changed between
  two runs. Every one was a literal reading of the proof, none a change that did nothing.
- 12 proofs, one project, one model, Python, two runs. It supports "the aimed request is the
  one that reliably reaches the subtle weak test, and it is the one that raises the most flags a
  person must judge". Nothing finer.

The prompts, the replies and the results are under the session's scratch folder, `pilot/`; they
are not kept in the repository.

## 3. The four approaches against the evidence

| | Finds a test that would miss a real mistake | What it takes to run | Evidence |
|---|---|---|---|
| 1. Blind | Weak tests that are plainly weak: yes. A subtle one: by chance. A caught bug says little: thin tests caught 68% to 87% of blind bugs (Kiele); Google's tests kill 87.5% of bugs made without them | One request, one test run per proof. The request is shorter: no test in it. The reading then needs the test in a second request, or loses it | The real-fault studies (Just; Papadakis 2018) all used blind bugs. Survivors can be off the proof's case (trial: 1 of 9; measurement: 1 of 93) |
| 2. Aimed past the test, with a guard | The most gaps per request: 7 times blind in one shot (Kiele). Reached the subtle weak test both times in the trial | One request, one test run per proof. The reply is longer | One study, on small problems with thin tests and a hidden suite. Survivors that are no bug: 13.8% (Kiele, of those the hidden suite passed), 20% (LLMorpheus), 36% (ACH, before its filter). Trial: flags on 1 and 4 of 9 sound tests, all literal readings. `strong` then needs a rule for `none` |
| 3. Both in one request | Blind's floor and the aimed probe together; the two results are shown apart | One request, two test runs per proof. About twice the reply | No study. The classical papers argue the two answer different questions and should be reported apart |
| 4. Several, keep one | More chances to reach the bug that matters: a real fault is tied to very few bugs (Just: 2 on average, none 40% of the time) | One request, a test run per candidate | One request can carry three (LLMorpheus). Candidates from one prompt overlap (Round-Trip: 4 in 5). No paper says how many are enough |

## 4. What a guard can and cannot be

- **Can be code.** Refuse a change that leaves the file as it was, that touches only comments or
  blank lines, or that touches a test file. ACH's equivalence check went from recall 0.47 to 0.96
  with the comment step alone. Purlin already refuses the first and the last.
- **Can be a test run.** Only a test that ran and failed is a caught bug. A test that errors is
  not (Round-Trip: 29% to 48% of rewritten mutants were "killed" by crashing).
- **Can be the proof.** The proof names one case and its result. Asking the model to write that
  case and the two results does not prove the bug real, and it gives the person reading a
  survivor the one line they need to judge it. In the trial it removed the bug that did nothing;
  it did not remove the literal reading.
- **Cannot be the model's verdict alone.** Tian et al., Straubinger et al. and the judge study
  (repeatable, moderately right) all say so.
- **Is in the end a person.** Kiele et al.: a survivor is "concrete suggestions for stronger
  tests and developer inspection rather than automatically validated defects." Google: a "Not
  useful" button. Purlin already shows a surviving bug with its proof and blocks nothing.

## 5. Claims on today's audit page that need rewording

| The page says | What the paper supports |
|---|---|
| "Planting bugs is the most reliable test of a test." | No paper read makes or tests this. Supported: suites that catch more planted bugs tend to catch more real faults (Just et al.), and the link is weak once the number of tests is held equal (Papadakis et al. 2018) |
| "Tests that catch small planted bugs tend to catch real ones (Just et al.)" | Holds for whole suites over many bugs, with coverage held equal. 17% of real faults had no planted-bug counterpart. Not shown for one test and one bug |
| "Code coverage ... does not predict that (Inozemtseva and Holmes)" | Overstated. They found a low to moderate link once the number of tests is held equal, and measured it with planted bugs, not real faults. Just et al., section 3.3, is the citation for real faults |
| "A bug in the code is then copied into the test (Konstantinou et al.)" | An inference. Measured: shown buggy code, the model more often rejects the correct expected answer (a drop of 8 to 9 points). One model, GPT-3.5 |
| "models judge inconsistently (judge study, 2026)" | The opposite on repetition: judges repeat themselves (0.943) and agree only moderately with people (kappa 0.376 to 0.511); the verdict changes with the order shown (0.099 to 0.173). The study is of chat answers, not tests |
| "AI-written bugs look more like real ones than tool-made ones (LLMorpheus)" | LLMorpheus shows four cases. The measured comparison is Wang et al.: real-bug detection 85.0% for a model's bugs against about 42% to 44% for rule tools (the paper gives both figures) |
| "Meta has a model write a few targeted ones (ACH)"; "Google plants bugs only in changed code and shows developers the few their tests missed" | Both hold |
| "At Meta, AI-written tests ship only after a measured check (Alshahwan et al.)" | Holds. The check is: builds, passes five times, adds line coverage; then a person reviews |

LLMorpheus exists in two versions with slightly different counts: the arXiv version read in part
A gives 105 of 517 surviving mutants equivalent (20%) and 5 of 430 (1%) for the rule tool; the
journal version read in part C gives 106 of 524 (20%) and 20 of 430 (5%). The docs should cite
one version and its own figures.

One thing to know: while looking for an author copy of the ISSTA 2016 paper, a reading agent
passed the owner's email address to the Unpaywall API as its contact parameter, once.

## Part A. The four papers on a model that writes the bug

Each was read in full from the PDF. A quote is word for word, with line-break hyphens joined.

### A1. Kiele, Saad, Wang, Drew, Ebrahimi Kahou. Beyond Rule-Based Mutation Testing: Test-Aware Mutant Generation Using Large Language Models. ESEM 2026.

Link: https://arxiv.org/abs/2609.35841 (PDF: https://arxiv.org/pdf/2609.35841)

**What it did.** One prompt per problem, one mutant per prompt, no feedback loop. The model gets the
problem statement and the reference solution, and in the test-aware variant the base tests too, with
the instruction that the mutant must pass every one of them. A mutant that passes the base tests is
then run against a far larger hidden suite (EvalPlus, 80 times the tests on HumanEval and 35 times
on MBPP). Passing the base tests and failing the hidden suite is a "verified fault". Five models,
164 HumanEval and 378 MBPP problems, two prompt families, each in a test-aware and a matched
test-blind form, and `mutmut` as the rule-based baseline.

**The numbers.**

| | HumanEval | MBPP |
|---|---|---|
| Test-aware, best model (Gemini 3.1 Pro, `agent1-ta`) | 87.8% verified (144 of 164) | 79.1% (299 of 378) |
| Test-blind, same model and prompt | 12.2% (20 of 164) | 23.0% (87 of 378) |
| `mutmut` | 4.4% (126 of 2,841) | 5.7% (195 of 3,427) |
| Test-blind mutants the base tests caught (`agent1-tb`, all models) | 68% to 87% | 54% to 78% |
| Base tests per problem | 7.7 on average | 3 |

- The abstract gives 87.7% for HumanEval; section 4.1 and Figure 4 give 87.8%, and 144 of 164 is
  87.8%.
- Test-aware mutants that passed the base tests and the hidden suite, for the best setting: 65 (9
  HumanEval, 56 MBPP). One author read all 65: 9 (13.8%) equivalent, 49 (75.4%) real faults the
  hidden suite missed, 7 (10.8%) faults only under an underspecified task.
- With up to 2 retries on feedback, test-blind rises from 12.2% to 83.5% and test-aware reaches
  98.2% (HumanEval, Gemini 3.1 Pro, `agent1`): 1.19 to 1.24 attempts per problem test-aware, 2.27
  to 2.46 test-blind.
- The weakest model test-aware (GPT 4.1 Mini, `agent2-ta`) did worse than the two best test-blind
  settings.

**Quotes.**

- Abstract, p. 1: "most remain test-blind: The model sees only the source code and cannot reason
  about what existing tests already cover."
- Abstract, p. 1: "Test-aware prompting yields verified fault rates of 87.7% (HumanEval) and 79.1%
  (MBPP), meaning these mutants pass all base tests but are caught by the oracle. This vastly
  outperforms the matched test-blind prompting (which yields only 12.2% and 23.0%, respectively)
  and the traditional rule-based tool mutmut (4.4% and 5.7%)."
- Section 2, p. 3, on Wang et al.'s study: "Interestingly, while one of their prompts includes
  existing unit tests, it performs slightly worse than the variant that omits them. We hypothesize
  that this performance drop occurs because LLMut only appends the tests as passive context. In
  contrast, our approach succeeds by explicitly structuring the prompt as an adversarial task,
  instructing the model to bypass the provided tests to produce high-quality, targeted mutants."
- The prompt, p. 7: "Your objective is to exploit a semantic blind spot in the Base Tests. The
  mutated code MUST pass all the provided Base Tests, but it should fail on broader edge cases or
  uncommon inputs." And its constraint 5: "The bug MUST manifest on VALID inputs that adhere to
  the problem description."
- Section 4, p. 9: "This confirms that without visibility of the base tests, LLMs introduce
  changes that existing assertions already cover."
- Section 4.2, p. 13: "Out of the 65 Undetected mutants, we found that only 9 (∼13.8%) are
  equivalent mutants and a vast majority (49/65, ∼75.4%) present serious edge-case bugs that
  slipped through the extended test cases."
- Section 5, p. 16: "An LLM can only exploit shortcomings that are actually expressed in the
  provided tests. Because we did not systematically vary base-test quality or coverage, this study
  does not establish exactly how performance changes as the initial suite becomes stronger or
  weaker."
- Section 5, p. 16, "No Oracle in the Real World": "In practice, a surviving mutant would not
  automatically come with a ground-truth label; instead, it would signal that the current test
  suite may be missing a behavior worth checking." And: "In real workflows, these mutants should
  be interpreted primarily as concrete suggestions for stronger tests and developer inspection
  rather than automatically validated defects."

**Where the first pass was wrong or loose.** The 87.7% and 12.2% are not how often each kind of
prompt writes a real bug. They are how often its one mutant gets past the base tests and is then
shown real by the hidden suite. A test-blind mutant is mostly a real bug too: the base tests
simply catch it. So the figures measure which prompt finds a gap in the tests, which is Purlin's
question.

**What it means for Purlin.**

- A bug chosen without the test is usually caught, even by tests known to be thin: the base tests
  caught 68% to 87% of test-blind mutants. A caught test-blind bug says little about the test.
- A bug aimed past the test is where the gaps show: 7 times as many found in one request.
- Sending the test without saying what to do with it, which is what Purlin's request does today,
  is the form the paper cites as no better than leaving the test out.
- Nothing here checks a surviving bug in a real project. The paper says a survivor is a suggestion
  for a person to look at. Purlin already shows it to a person and blocks nothing.
- Its guard against a bug that is no bug is a hidden suite Purlin does not have. Purlin has the
  proof, a sentence naming one case and its result; the paper's problem statement plays that part
  and the prompt holds the mutant to "VALID inputs that adhere to the problem description".
- Not shown: how test-aware prompting behaves against a strong test. The base tests were few.

### A2. Foster, Gulati, Harman, Harper, Mao, Ritchey, Robert, Sengupta. Mutation-Guided LLM-based Test Generation at Meta (ACH). FSE Companion 2025.

Link: https://arxiv.org/abs/2501.12862 (PDF: https://arxiv.org/pdf/2501.12862)

**What it did.** ACH takes a plain-text concern (here, past privacy faults), has a model write a
fault in a Kotlin class that is like that concern, keeps only faults that build and that every
existing test passes, drops the ones a second model judges equivalent to the original, and has a
third model write a test that catches each one left. Run on 7 Meta platforms from October to
December 2024, with Llama 3.1 70Bn for all three agents.

**The numbers.**

- 10,795 classes, 31,677 mutants written, 9,095 (29%) built and passed the existing tests.
- Of the 9,095: 2,246 (25%) identical to the original, 1,016 (11%) judged equivalent, 1,173 (13%)
  no answer, 4,660 (51%) judged not equivalent. 571 tests were written from them.
- Engineers accepted 73% of 191 tests reviewed and judged 36% relevant to privacy.
- By hand on 381 sampled mutants: 137 (36%) were equivalent. The equivalence agent alone: precision
  0.79, recall 0.47. With identical code and added comments stripped first: 0.95 and 0.96.
- 61% of the equivalent mutants differed only by a comment the model added, such as "Introduce a
  bug by not checking ...", with no code changed.

**Quotes.**

- Table 1, p. 3, the fault prompt: "CONTEXT: {context_about_concern} INSTRUCTION: Here is a Kotlin
  class and a test class with some unit tests for the class under test ```{class_under_test}```.
  ```{existing_test_class}```. Write a new version of the class under test in which each method is
  replaced by a new version of that method that contains a typical bug that introduces a privacy
  violation similar to {diff}."
- Section 1, p. 1: "our key insight is to construct mutants that denote faults that are both
  relevant to the issue of concern and also currently not caught (unkilled) by any existing test
  case"
- Section 3, p. 4: "Although the language model approach generates fewer and more specific mutants
  than rule-based approaches, we found that it also generates more equivalent mutants."
- Section 5.1, p. 6: "For the application of mutation-guided test generation, the equivalent mutant
  problem has no direct impact on engineers. Our workflow requires only that engineers review test
  cases, not mutants."
- Section 5.3, p. 7: "we cannot claim that these surprisingly good results arise because the mutant
  equivalence detector agent is excellent at determining program equivalence. Rather, they are more
  reflection of the kind of mutants the detector needs to judge for equivalence. That is, the
  mutant generation agent tends to make changes that either obviously introduce semantic changes,
  or are obviously equivalent (such as those that only change comments)."
- Section 8, p. 10: "in some cases, anecdotally, looking at the faults generated, it seemed that
  the mutant was related to the general class of fault simulated, but was not an example of the
  specific instance. One difficulty here is that we have no way to consistently and reliably
  measure problem similarity or relevance."

**Where the first pass was wrong or loose.** ACH's prompt holds the existing tests and does not
tell the model to get past them. Getting past them is done afterwards, by a filter: a fault is
kept only when it builds and every test passes. So ACH is "test in the request, selection by
running", not "told to get past the test". Only 29% of its faults survived that filter.

**What it means for Purlin.**

- ACH is the one system here that writes the fault from a sentence about what must not happen,
  which is Purlin's case. It reports that some faults matched the general concern and not the
  specific one, and that it has no measure of that.
- A third of the faults that got past the tests changed nothing. ACH can afford that because a
  person never sees a fault, only a test. In Purlin the person is shown the surviving bug, so a
  bug that changes nothing is a false `weak`. A guard is needed, and the cheap part of ACH's guard
  is code, not a model: drop a change that only touches comments or leaves the file as it was.
- ACH's use of the fault differs: it writes a new test for it. Purlin reports it and leaves the
  test to `purlin:build`.

### A3. Tip, Bell, Schäfer. LLMorpheus: Mutation Testing using Large Language Models. IEEE TSE 2025.

Link: https://arxiv.org/abs/2404.09952 (PDF: https://arxiv.org/pdf/2404.09952)

**What it did.** A tool marks places in JavaScript and TypeScript code (conditions, loop headers,
call arguments), replaces one with `<PLACEHOLDER>`, and asks a model for three buggy replacements,
each with a reason. The prompt holds the code around the place, up to 200 lines, and the original
fragment. It holds no test. A modified StrykerJS then runs each mutant against the tests. 13
packages, five models.

**The numbers.**

- 3,376 prompts gave 9,967 candidates; 29.0% were not valid code, 1.6% identical to the original,
  2.1% duplicates; 6,712 mutants were left. 48.2% were killed, 47.0% survived, 4.8% timed out.
- Of 517 surviving mutants read by two authors: 403 (78%) not equivalent, 105 (20%) equivalent, 9
  (2%) unknown. For StrykerJS's own rule-made mutants: 395 of 430 (92%) not equivalent, 5 (1%)
  equivalent.
- Asking for one replacement and not three: 2,333 mutants against 6,712.
- At temperature 0, `codellama-34b-instruct` gave the same mutants in all 5 runs for 89.29% to
  98.89% of them. Three other models at temperature 0: 28% to 59%.
- Four real bugs from Bugs.js: for each, a mutant identical to the bug or failing the same tests.

**Quotes.**

- Section 3, p. 5, the system prompt: "Your job is to make small changes to a project's code in
  order to find weaknesses in its test suite. If none of the tests fail after you make a change,
  that indicates that the tests may not be as effective as the developers might have hoped"
- Section 4.4, p. 8: "Determining mutant equivalence requires a deep understanding of the
  program's intended behavior, as a mutant might change the behavior of the program but within
  bounds that are valid to the program's specification."
- Section 4.4, p. 8: "Of the 517 mutants under consideration, the majority 403 (78%) are "not
  equivalent", 105 (20%) are "equivalent", and remaining 9 (2%) are classified as "unknown"."
- Section 4.4, p. 9: "LLMorpheus produces significantly more "equivalent" mutants than StrykerJS."
- Section 4.6, p. 9: "using onemutation dramatically reduces the number of mutants from 6,712 to
  2,333, demonstrating that it is helpful to request multiple suggestions"
- Section 4.6, p. 10: "We infer that prompting for multiple mutants can result in the LLM
  suggesting more significant code changes than it would otherwise have."
- Section 4.7, p. 11: "we also analyzed the variance of the number of mutants killed and survived,
  finding that, despite the diversity of mutants across trials, the mutation score was relatively
  stable."
- Section 5, p. 14: "One of the key evaluation criteria used in previous work on mutation testing
  is "coupling", i.e., determining whether a test suite that detects particular mutants also
  detects particular real faults". The authors could not run that study; the four bugs are a case
  study.

**Where the first pass held.** The model never sees the tests; a separate tool runs them. 20% of
517 surviving mutants were equivalent. Both hold.

**What it means for Purlin.**

- The test-blind design at its plainest: the model cannot lean on a test it never saw.
- A surviving bug from a model is equivalent about 1 time in 5 here, against 1 in 100 for
  rule-made ones. "Equivalent" depends on what the program is meant to do. Purlin's proof says
  what that is for one case.
- One request can ask for three candidates. Asking for three gives about three times as many, and
  somewhat larger changes.
- Which bug comes back varies from run to run with most models, even at temperature 0, while the
  share caught stays steady across thousands of mutants. Purlin plants one or two per proof, so a
  proof's result can differ between two audits of the same code. Purlin keeps a result until the
  test or code changes, which holds it still.

### A4. Chang, Fang, Chen, Shi, Shen, Gu. Test vs Mutant: Adversarial LLM Agents for Robust Unit Test Generation (AdverTest). ISSTA 2026.

Link: https://arxiv.org/abs/2602.08146 (PDF: https://arxiv.org/pdf/2602.08146)

**What it did.** Two model agents take turns. One writes tests. The other writes mutants, first
from the code alone, then aimed at lines the tests do not run and at places where an earlier
mutant survived. The mutant agent is never shown the tests' text; it gets the list of survivors
and the coverage. Scored by whether the final tests fail on the real buggy version of 247 Java
bugs (Defects4J, GrowingBugs) and 12 Python issues.

**The numbers.**

- Fault detection 66.63% on Defects4J against 61.38% for the best model baseline (HITS) and 44.36%
  for EvoSuite.
- The mutant agent's output: 90.3% compiled, 36.2% of valid mutants survived, 3.45% equivalent.
- Ablation on 50 bugs: full loop 54.00%; no loop 26.00%; rule-made mutants (MAJOR) in place of the
  model's 46.00%; coverage feedback only 34.00%.
- 50 or more mutants per method each turn (`max(2 line_num, 50)`), up to 5 turns.

**Quotes.**

- Section 3.3, p. 6: "we enforce a single-line modification constraint."
- The mutant prompt's requirement 5, p. 7: "No meaningless mutants: Do not generate mutants that
  result in identical execution behavior to the original."
- Section 3.6, p. 9: "Even when a line of code is covered, it may still conceal faults. For
  example, when a test case executes a statement without asserting its effects, behavioral
  deviations remain undetected."
- Section 5.2, p. 15: "Substituting the LLM mutator with the rule-based MAJOR tool (w/ MAJOR) loses
  8 pp FDR (from 54.00% to 46.00%) while coverage remains nearly intact"
- Section 5.1, p. 14: "Agent M's output achieves a 90.3% compile rate, 36.2% survival rate among
  valid mutants, and an equivalent-mutant rate of 3.45%"

**What it means for Purlin.**

- It is test-aware by feedback, not by reading the test: what survived tells the mutant agent
  where to aim next. That takes several rounds and many mutants, which Purlin's one request per
  rule does not have.
- It supports aiming at what the test misses, and a model writing the bug over a rule tool.
- Its low equivalent rate (3.45%) came with a one-line limit and an instruction not to write a
  change with the same behaviour. How the 3.45% was measured is not described beyond the figure.
- It measures tests a model wrote in the loop, not a fixed test a person or an earlier build wrote.

## Part B. The classical papers on planted bugs

Six papers, each read in full from the extracted PDF text in the session's scratch folder. Every quote
below was copied from that text, with only line-break hyphenation, ligatures and extraction
spacing repaired, and then checked by script against the `.txt` file; the page given is the PDF
page (`===== PAGE n =====`), not the printed page number. `[sic]` marks an error that is in the
paper. Reference numbers in square brackets inside a quote are the paper's own.

The four approaches under decision:

1. Test-blind: the model sees the requirement and the code only.
2. Test-aware: the model sees the test and is told to get past it.
3. Both.
4. Several candidates per proof.

A limit that applies to all six papers: every one measures a test suite against many mutants and
reports a score or a correlation. None studies one planted bug per test, a bug chosen by something
that has read the test, or a bug derived from a plain-language requirement. What they say about
those cases is by inference, and each entry says where.

---

### 1. Papadakis, Shin, Yoo, Bae: Are Mutation Scores Correlated with Real Fault Detection?

- Authors: Mike Papadakis, Donghwan Shin, Shin Yoo, Doo-Hwan Bae
- Venue: ICSE 2018. The PDF read is the authors' preprint (12 pages, header "Conference'17").
- Link: https://doi.org/10.1145/3180155.3180183 (DOI recalled, not printed in the preprint)
- Text read: `papadakis2018.txt`, pages 1 to 10 in full; pages 11 and 12 are references.

#### What it did

It asked whether a test suite's mutation score predicts whether the suite detects a real fault,
once the number of tests in the suite is held constant. It used real faults from CoREBench (C)
and Defects4J (Java), with developer tests enlarged by KLEE, Randoop and EvoSuite. For each fault
it sampled 10,000 test suites, first of random size and then of fixed size, and measured the
correlation between mutation score and fault detection. It also compared the fault detection of
the top-scoring 25% and 10% of suites against all suites of the same size. Last, it measured how
closely each single mutant's kill pattern matches the real fault's.

#### The numbers

- 9 programs: 4 C, 5 Java. 68 of 70 CoREBench faults and 231 of 357 Defects4J faults were used;
  126 Defects4J faults were dropped for run time.
- Correlation of mutation score with real fault detection, suite size not controlled: most values
  0.35 to 0.75. Suite size controlled: about 0.05 to 0.20.
- Top 10% of suites by mutation score against random suites of the same size: a significant
  improvement for 138 of 231 Defects4J faults and 59 of 68 CoREBench faults; none shown for 93
  and 9.
- Average improvement in fault detection for the top 25% and top 10% of suites: 8% and 11%
  (Defects4J), 18% and 46% (CoREBench).
- About 1% of all mutants have a behaviour similarity above 0.5 with the real fault. For half the
  faults the single most similar mutant has a similarity of at least 90%.

#### Quotes

- "In contrast, our study shows that correlations are the results of the confounding effects of the test suite size." (Abstract, PDF p. 1)
- "For instance, the study of Just et al. [24] did not control for the size of the test suites, which is a strong confounding factor in software testing experiments [21, 27]." (Section 1, PDF p. 1)
- "However, these mutants are very few (less than 1% of the involved mutants)." (Section 1, PDF p. 2)
- "However, their identification is done manually as it is an instance of an undecidable problem [2]." (Section 2, PDF p. 2)
- "These correlations become relatively weak (approximately within the range 0.05 to 0.20) when the suite size is controlled (i.e., the influence of size disappears)." (Section 4.3, PDF p. 7)
- "These results suggest that a major part of the association between mutation score and fault detection is simply an effect of size." (Section 4.3, PDF p. 7)
- "Specifically, the average improvements on fault detection for the top ranked 25% and 10% of the test suites are 8% and 11% for Defects4J and 18% and 46% for CoreBench." (Section 4.4, PDF p. 8)
- "This implies that some mutants simulate well the behaviour of the faults, while the majority of them do not (we measure approximately 1% of all mutants have behaviour similarities above 0.5)." (Section 5.1, PDF p. 8)
- "Other threats might be attributed to the way we handled equivalent mutants, which was based on the composed test pools." (Section 6, PDF p. 10)
- "Our data show that when controlling the test suite size (decouple mutation score from test suite size) all correlations become weak or moderate in the best case." (Section 7, PDF p. 10)

#### What it means for Purlin

- **Does a caught mutant predict catching real faults?** Weakly, as a correlation. Once suite size
  is fixed the correlation is 0.05 to 0.20. The paper's positive finding is narrower: suites at
  the top of the mutation-score ranking detect real faults more often than same-size suites,
  by 8% to 46% on average. It reads mutants as good guidance for improving tests and a poor
  stand-in for real faults.
- **Suite-size confound.** This is the paper's main point, and it is aimed at Just et al. (entry
  4). Purlin runs one proof's test against one bug, so suite size does not vary inside a single
  check; the confound returns as soon as results are added up across a feature or a project.
- **How many mutants.** Not studied as a count. The relevant finding is that about 1% of mutants
  behave like a given real fault. One mutant drawn without aim at a proof is therefore unlikely
  to be one that stands for a real fault. That argues for choosing the bug with care (approaches
  1 and 2 both do, in different ways) and for more than one candidate (approach 4). This is an
  inference; the paper does not test it.
- **Equivalent mutants.** No rate reported. They were handled by treating what the pooled tests
  could not kill as not killable, which the authors list as a threat and call undecidable in
  general.
- **Bias from choosing mutants with knowledge of the tests.** Silent. The only overlap is that
  the same test pool both judges and defines which mutants count.
- **Mutation from a specification.** Silent.

---

### 2. Papadakis, Kintis, Zhang, Jia, Le Traon, Harman: Mutation Testing Advances: An Analysis and Survey

- Authors: Mike Papadakis, Marinos Kintis, Jie Zhang, Yue Jia, Yves Le Traon, Mark Harman
- Venue: Advances in Computers, volume 112, 2019. The PDF read is the preprint dated
  December 14, 2017.
- Link: https://doi.org/10.1016/bs.adcom.2018.03.015 (DOI recalled, not printed in the preprint)
- Text read: `survey.txt`, pages 1 to 82 in full, which is the whole body. Pages 82 to 153
  are the reference list (405 entries) and were not read.

#### What it did

It surveys mutation-testing research from 2008 to 2017: 502 papers from the main software
engineering venues. It walks the mutation process step by step (select mutants, create them,
remove equivalent and redundant ones, generate tests, execute, score, reduce tests, decide when
to stop, write oracles, debug). It then covers mutation of models, security policies and other
artefacts, lists 76 tools, and ends with the threats to validity when mutants are used to compare
test techniques, as a seven-point checklist.

#### The numbers

All of these are results the survey reports from other papers.

- Random sampling of mutants: keeping 10%, 20%, 30%, 40%, 50%, 60% loses about 26%, 16%, 13%,
  10%, 7%, 6% of fault detection.
- Killing a random sample of more than 50% of mutants kills more than 99% of all mutants.
- A random 5% of the selective-operator mutants predicts the mutation score of that set.
- The most that selecting by operator can gain over random sampling: 13%.
- Trivial Compiler Equivalence finds at least 30% of equivalent mutants, and removes 21% of C
  mutants and 5.4% of Java mutants as duplicates.
- Share of mutants that are not redundant: about 9% (disjoint), 1.2% (minimal), 4% in three
  studies; the survey's own summary is about 5% practically useful.
- Second-order mutants cut equivalent mutants by 80% to 90% for about 10% or less loss of test
  effectiveness.
- Redundant mutants have a better than 60% chance of changing an experiment's conclusion.
- Strong-mutation-adequate suites reveal at least 90% of faults in one study (Chekam et al.).
- Of the 502 papers, 186 are on code-based mutation and 40 on model-based mutation.

#### Quotes

- "In practice using mutation score as adequacy measure, implicitly assumes that all mutants are of equal value. Unfortunately, this is not true [36]." (Section 2, PDF p. 9)
- "Papadakis and Malevris [53] report that randomly selecting 10%, 20%, 30%, 40%, 50% and 60% of the mutants results in a fault loss of approximately 26%, 16%, 13%, 10%, 7% and 6% respectively." (Section 5.1.2, PDF p. 23)
- "Recently, Gopinath et al. [113] used large open source programs and found that a small constant number of randomly selected mutants is capable of providing statistically similar results to those obtained when using all mutants." (Section 5.1.2, PDF p. 23)
- "Empirical results suggest TCE is surprisingly effective, being able to identify at least 30% of all the equivalent mutants." (Section 5.3.1, PDF p. 29)
- "This means that there is a strong connection between mutation score and fault revelation only at higher mutation score levels (above a specific threshold). However, below that level, the mutation score is completely disconnected from fault-revelation." (Section 5.8, PDF p. 42)
- "Unfortunately, when assessing testing methods, one test technique might achieve a significant advantage over another by killing redundant than non-redundant mutants." (Section 9.3, PDF p. 70)
- "Computing the true disjoint mutant set is impossible and thus, in the context of controlled experiments, it is approximated by a test suite." (Section 9.3, PDF p. 71)
- "It is a common practice to apply tools and test techniques on the original program and then check their fault-revealing power by executing tests on the mutants." (Section 9.6, PDF p. 75)
- "Overall, the current research results show that only few of the mutants produced (approximately 5%) is practically useful." (Section 11.1, PDF p. 80)
- "Trakhtenbrot [305] introduced a semantic mutation approach that introduces mutants related to the intended meaning of the requirements (requirements expressed by predifined [sic] patterns) by altering the pattern of the requirements." (Section 7.1, PDF p. 53)

#### What it means for Purlin

- **How many mutants are needed.** The survey gives no number for a single test. Its evidence is
  about sampling from a full set: a 10% sample already loses about a quarter of fault detection,
  and one cited study finds a small constant random sample gives statistically similar scores to
  the full set. The survey does not state what that constant is. Against that, it warns
  (Section 5.1.2, p. 24 to 25) that all these sampling results used the all-mutants score, and
  that sampling and operator selection perform poorly when judged against subsuming mutants only.
  For Purlin: one bug per proof is far below anything these studies sampled, so the classical
  record cannot say it is enough. It supports approach 4 only in the general sense that more
  candidates lose less.
- **Redundant mutants.** About 95% of generated mutants are killed whenever some other mutant is
  killed. A bug chosen blind is likely to be one of those: easy, and caught for reasons that say
  little about the test. This is the survey's strongest point against a naive test-blind bug.
- **Equivalent mutants.** Undecidable in general (Section 5.3.1). Static compiler comparison
  finds at least 30% of them; the rest need a person or a heuristic. The survey gives no overall
  rate. It says equivalent mutants pull the true score down and redundant ones push it either
  way (Section 5.8, p. 43). For Purlin: a planted bug that survives is either a weak test or an
  equivalent bug, and the classical tools cannot tell which automatically. This matters most for
  approach 2, where the model is pushed towards changes the test does not see.
- **Bias when the tests that judge also pick the mutants.** The survey does not name this as a
  bias. It does say the set of non-redundant mutants cannot be computed and is approximated by
  the test suite in hand, so which mutants count is always relative to the tests used. The
  nearest thing to a test-aware adversary is the mutation game it describes (Section 6, p. 47):
  an attacker writes subtle, non-equivalent mutants and a defender writes tests to kill them. It
  reports that as useful for teaching and motivation and gives no measurement of bias.
- **Clean program assumption.** This is a different matter from test-blind versus test-aware. It
  is the practice of building or measuring tests on the correct program and then judging them on
  mutants. The survey says (Section 9.6, p. 76) that one study showed the assumption does not
  hold and can change an experiment's outcome. Purlin's audit does exactly this by design: the
  test was written for the correct code and is then run on the bugged code. That is the intended
  question for Purlin (does this test notice this break), so the threat applies to research
  comparisons, less to the audit; it is worth one sentence if the docs claim more than that.
- **Does a caught mutant predict real faults.** The survey calls the supporting evidence
  preliminary and contradicted by other studies (Section 9.1, p. 68), names test suite size as a
  confounding factor to control (Section 9.4, p. 73), and reports a threshold effect: the link to
  real faults appears only at high scores.
- **Mutation from a specification.** Section 7.1 covers mutation of models: state machines,
  feature models, timed automata, Simulink, Alloy. One cited approach mutates natural-language
  requirements written in fixed patterns. The open-problems section (p. 81) says model-based
  mutation has not been researched much compared with code-based mutation. Nothing covers
  planting a code bug derived from a free-text requirement. Of the six papers this is the only
  one that touches the subject, and it gives no effectiveness figures for it.

---

### 3. Papadakis, Henard, Harman, Jia, Le Traon: Threats to the Validity of Mutation-Based Test Assessment

- Authors: Mike Papadakis, Christopher Henard, Mark Harman, Yue Jia, Yves Le Traon
- Venue: ISSTA 2016
- Link: https://doi.org/10.1145/2931037.2931040; author copy read from
  https://orbilu.uni.lu/bitstream/10993/28927/1/ISSTA16.pdf
- Text read: `threats2016.txt`, pages 1 to 10 in full; pages 11 and 12 are references.

#### What it did

It asked how much the usual mutation score is distorted by subsumed mutants: mutants that are
killed whenever some other mutant is killed. On five C utilities it found which mutants are
subsuming with respect to the available tests, then compared the score over all mutants (MS)
with the score over subsuming mutants only (MS*). It simulated experiments that compare two test
techniques and counted how often a significant difference in MS is not a significant difference
in MS*. It also surveyed two years of ISSTA, FSE and ICSE papers for exposure to the problem.

#### The numbers

- 5 programs (Grep, Sed, Flex, Make, Gzip), 5,048 to 20,461 lines, 111 to 500 tests, 4,330 to
  22,023 non-duplicated mutants each.
- Subsuming mutants as a share of killed, non-duplicate mutants: Grep 1.7%, Sed 3.2%, Flex 4.8%,
  Make 0.4%, Gzip 2.5%.
- Tests that kill a random 0.5% of mutants score at least 50% on MS, and about 10% (30% at best)
  on MS*.
- Tests that kill a random 8% of mutants score above 90% on MS, and at most 50% on MS*.
- Correlation between MS and MS*: mostly 0.2 to 0.6.
- Chance of a Type I error in a simulated comparison of two techniques: about 62% on average.
  Errors remain when the two differ by 10% in MS with equal suite sizes.
- 389 papers read; 91 on testing; 25 used mutation; 17 of the 25 (68%) used it to assess tests
  and none of the 17 handled subsumption.
- From other work it cites: 21% of mutants are duplicates removable by compiler comparison;
  sampling 10% to 60% of mutants loses 26% to 6% of fault detection.

#### Quotes

- "Our findings indicate that Type I errors occur, for arbitrary experiments that fail to take countermeasures, approximately 62% of the time." (Abstract, PDF p. 1)
- "We found that fewer than 5% of all mutants are subsuming (and not subsumed themselves). The remaining 95% of mutants are subsumed by some other mutants." (Section 1, PDF p. 2)
- "These mutants are called equivalent mutants and must be removed from consideration when using mutation as a test assessment metric." (Section 2.2, PDF p. 2)
- "Given a test suite, a mutant subsumes another one, if it is killed by a subset of the test cases the [sic] kill the other." (Section 2.2, PDF p. 2)
- "Our results show that only a tiny proportion, ranging from 0.4% to 4.8% (GREP 1.7%, SED 3.2%, FLEX 4.8%, MAKE 0.4%, GZIP 2.5%), of mutants is actually needed for performing mutation analysis." (Section 5.1, PDF p. 5)
- "Our results demonstrate that killing a random 0.5% of all the mutants results in an effectiveness measure of at least 50%, according to MS, while in some cases, this measure is close to or above to 90%." (Section 5.2, PDF p. 6)
- "When mutation is used to guide the test generation process, the consequences of this issue, apart from the misleading measurement, does not seem to be important." (Section 5.3, PDF p. 6)
- "Moreover, subsuming mutants form a measure free of redundant requirements, with respect to the used test suite." (Section 6.2.1, PDF p. 8)
- "Although manually seeded faults are typically much fewer and hence less likely to have severe subsumption problems, the quality of these faults depends on the knowledge and expertise of the person that makes the seeding." (Section 7, PDF p. 9)
- "For instance, the study of Hutchins et al. [20] only aimed at seeding faults that were revealed by a small fraction of tests and thus, completely ignored the subsumed mutant threat." (Section 7, PDF p. 9)

#### What it means for Purlin

- **Easy bugs inflate the result.** This is the paper's whole finding and it bears directly on
  approach 1. If the planted bug is the kind almost any test catches, the fact that the test caught it says
  little. Roughly 95% of tool-generated mutants are of that kind. A test-blind model is not a
  mutation tool and may do better, but nothing in this paper says so.
- **Bias when the judging tests also pick the mutants.** The paper does this itself and says so
  only in passing: subsumption is defined "Given a test suite", and the result is free of
  redundancy "with respect to the used test suite". It does not measure what that circularity
  costs, and its internal-validity section admits only that the tests were not adequate. So the
  paper is evidence that picking the hard mutants by looking at the tests is accepted practice
  and gives a sharper measure; it is not evidence about the bias of doing so.
- **Hand-seeded faults.** The closest classical analogue to an LLM planting one bug. The paper
  says such faults are fewer, so subsumption is less of a problem, and that their quality rests
  on the seeder's skill. It also records one earlier study (Hutchins et al.) that kept only
  seeded faults few tests revealed, which is selection with knowledge of the tests, and faults
  it for ignoring subsumption, not for the selection.
- **Guidance versus measurement.** The paper says the distortion matters when scores are used to
  compare techniques and matters little when mutants are used as targets for writing tests.
  Purlin's audit is closer to the second use: one bug, one test, a yes or no. The distortion
  returns if Purlin reports a rate across proofs or compares projects by it.
- **How many mutants.** Only the cited sampling loss (26% at a 10% sample to 6% at 60%). No
  per-test figure.
- **Equivalent mutants.** No rate. They must be removed, identifying them is undecidable, and the
  paper removed everything the tests did not kill.
- **Real faults.** Not studied; the paper compares two mutant-based scores. It plans validation
  on real data as future work.
- **Mutation from a specification.** Silent, apart from one line noting mutation has been applied
  to behavioural models.

---

### 4. Just, Jalali, Inozemtseva, Ernst, Holmes, Fraser: Are Mutants a Valid Substitute for Real Faults in Software Testing?

- Authors: René Just, Darioush Jalali, Laura Inozemtseva, Michael D. Ernst, Reid Holmes,
  Gordon Fraser
- Venue: FSE 2014
- Link: https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf
- Text read: `just2014.txt`, pages 1 to 10 in full; pages 11 and 12 are references. PDF
  page 1 is printed page 654.

#### What it did

It isolated 357 real, developer-fixed faults in five Java projects (the set that became
Defects4J). For each fault it built pairs of developer test suites that differ by the one test
that exposes the fault, and asked whether the suite that catches the fault also kills more
mutants: whether the fault is "coupled" to at least one mutant. It inspected by hand every fault
that was coupled to none. It then generated 35,141 test suites with EvoSuite, Randoop and
JCrasher and measured the correlation between mutation score and real fault detection, with and
without controlling for statement coverage.

#### The numbers

- 5 programs, 321,000 lines, 357 real faults, 230,000 mutants, 480 developer test-suite pairs,
  35,141 generated suites that detect 198 of the 357 faults.
- Mutation score rose with the fault-exposing test in 362 of 480 pairs (75%). Statement coverage
  rose in 222 of 480 (46%).
- Where coverage did not rise (258 pairs): mutation score rose in 153 (59%); 40% of those tests
  killed no extra mutant; 45% killed 1 to 3; the average was 2 extra mutants.
- Where coverage rose (222 pairs): mutation score rose in 209 (94%); the average was 28 extra
  mutants.
- 73% of real faults are coupled to at least one mutant. 95 of 357 (27%) are not: 25 need a
  stronger operator, 7 need a new operator, and 63 (17%) have no plausible operator; 37 of the
  63 are algorithm changes.
- Correlation analysis used 194 faults. With coverage controlled, the suites that detect the
  fault have a significantly higher mutation score for 21 of 22 (Chart), 27 of 32 (Closure),
  76 of 80 (Math), 18 of 18 (Time), 40 of 42 (Lang) faults; average effect size 0.66 to 0.81.
- Mutants were generated only in the classes the bug fix changed.

#### Quotes

- "The results show a statistically significant correlation between mutant detection and real fault detection, independently of code coverage." (Abstract, PDF p. 1)
- "Major only mutated classes of the source code version V2 that were modified by the bug fix." (Section 2.5, PDF p. 5)
- "We did not eliminate equivalent mutants, which means that the reported mutation scores might be underestimated." (Section 2.5, PDF p. 5)
- "Differences in coverage often dominate other aspects of test suite effectiveness, and a test suite that achieves higher coverage usually detects more mutants and faults for that reason alone [16]." (Section 2.6.1, PDF p. 5)
- "First, 40% of these triggering tests did not detect any additional mutants. Second, 45% of these triggering tests detected only 1–3 additional mutants, suggesting that the number of mutants that are coupled to a real fault is small when accounting for the conflating effects of code coverage." (Section 3.1, PDF p. 6)
- "27% of real faults are not coupled to the mutants generated by commonly used mutation operators. The set of commonly used mutation operators should be enhanced. However, 17% of real faults, mostly involving algorithmic changes or code deletion, are not coupled to any mutants." (Section 3.2, PDF p. 8)
- "Both correlation coefficients lead to the same conclusion: the correlation is positive, usually strong or moderate, indicating that mutation score is indeed correlated with real fault detection." (Section 3.3, PDF p. 8)
- "Mutant detection is positively correlated with real fault detection, independently of code coverage. This correlation is stronger than the correlation between statement coverage and real fault detection." (Section 3.3, PDF p. 9)
- "Moreover, all 5 subject programs are well-tested (see Figure 3). This may limit the applicability of the results to programs that are not well-tested (e.g., programs under development)." (Section 3.4, PDF p. 9)
- "Third, test suite selection, minimization, and prioritization techniques evaluated on mutants might lead to a reduced real fault detection rate of the test suite, even if the mutation score does not decrease." (Section 5, PDF p. 10)

#### What it means for Purlin

- **Does a caught mutant predict catching real faults?** Yes as a correlation between suite-level
  scores, on well-tested Java libraries, with coverage controlled. The paper's own limits: 27% of
  real faults move no mutant at all, and 17% cannot be represented by any mutant, mostly
  algorithm errors and code that should not be there.
- **Suite-size confound.** The paper controls for statement coverage and never for the number of
  tests. Its only mention of test suite size is the test-code line count in Table 1. Papadakis et al. 2018 (entry 1) reran
  this on the same faults, found the correlation falls to 0.05 to 0.20 once size is fixed, and
  says so by name. Any citation of Just et al. as showing that mutants predict real faults should carry that.
- **How many mutants.** Not asked, but the coupling figures are the most useful numbers in the
  six papers for approach 4. With coverage fixed, the one test that exposes a real fault kills on
  average 2 mutants more, and 40% of the time none. A real fault is therefore tied to very few
  specific mutants. One planted bug per proof has a small chance of being one of them; several
  targeted candidates have a better chance. This is an inference from the coupling data.
- **Where to plant.** The study mutated only the classes the fix touched, to keep irrelevant
  mutants from washing out the signal. That supports planting the bug in the code the proof is
  about, which both approaches 1 and 2 do.
- **Equivalent mutants.** Not removed. The authors argue it does not matter for a comparison
  because the same equivalent set sits under both suites. No rate is given. That argument does
  not carry to Purlin, where a single surviving bug is read as a verdict on one test.
- **Bias from choosing mutants with knowledge of the tests.** Silent on choosing mutants that
  way. Its last conclusion is the nearest warning, in the other direction: choosing tests by
  their mutant kills can lower real fault detection with no drop in mutation score.
- **Mutation from a specification.** Silent.

---

### 5. Petrović, Ivanković, Fraser, Just: Practical Mutation Testing at Scale: A view from Google

- Authors: Goran Petrović, Marko Ivanković, Gordon Fraser, René Just
- Venue: IEEE Transactions on Software Engineering. The PDF read is arXiv 2102.11378 version 2,
  dated 26 February 2021, which states it has been submitted to the IEEE.
- Link: https://arxiv.org/pdf/2102.11378
- Text read: `petrovic2021.txt`, all 22 pages, including the appendix of heuristics
  (pages 14 to 22).

#### What it did

It describes the mutation service Google runs inside code review. When a change is sent for
review the service mutates only the changed lines that tests cover, at most one mutant per line,
and skips "arid" code (logging, timeouts, flags, capacity hints and so on) using more than a
hundred hand-written rules built from developer feedback. It runs the tests, and shows the
author and reviewers a limited random selection of the mutants that survived. Developers mark
each one "Please fix" or "Not useful". The paper evaluates how far suppression cuts the number of
mutants, how survival and usefulness vary by operator and language, and whether choosing the
operator from the history of similar code improves both.

#### The numbers

- 16,935,148 mutants generated over 776,740 changelists; 2,110,489 surfaced; 66,798 received
  explicit feedback. More than 24,000 developers, more than 1,000 projects, 10 languages,
  5 operators.
- 87.5% of generated mutants are killed by the existing tests; 12.5% survive.
- Mutants per changelist, median, on a sample of 5,000 changelists: 820 with traditional
  mutation, 77 with one per line, 7 with one per line after arid suppression.
- Surviving mutants per changelist: median 2, 99th percentile 43.
- Mutants reported: at most 7 times the number of files in the changelist.
- Share of surfaced mutants judged productive: 15% at first, 80% after the first three
  suppressions (logging, time, flags), 89% now; 82% over the whole data set with feedback.
- Choosing the operator from history: survival up by more than 40%, the chance of a "Please fix"
  up by almost 50%, against random choice.
- Arid heuristics by kind: 1 uncompilable, 13 equivalent, 16 unproductive but killable,
  2 redundant.

#### Quotes

- "Mutation testing is done incrementally, mutating only changed code during code review, rather than the entire code base" (Abstract, PDF p. 1)
- "To make matters worse, even when applying sampling techniques to substantially reduce the number of mutants, developers at Google initially classified 85% of reported mutants as unproductive." (Section 1, PDF p. 2)
- "An unproductive mutant is either trivially equivalent to the original program or it is detectable, but adding a test for it would not improve the test suite [11]." (Section 1, PDF p. 2)
- "An AST node is eligible for mutation if it is covered by at least one test and if it is not arid" (Section 2, PDF p. 2)
- "Once test results are available, we randomly pick mutants from all surviving mutants to be reported. We limit the number of reported mutants to at most 7 times the number of total files in the changelist" (Section 2.3, PDF p. 3)
- "Furthermore, only a single mutant in a line is ever produced, all others are not considered." (Section 4.1, PDF p. 7)
- "Mutation operators are ordered using this metric rather than uniformly shuffled, and mutagenesis is attempted in that order, to maximize the probability that the mutant will be productive, or at least survive to be reported in the code review." (Section 4.2, PDF p. 7)
- "Surviving the initial test suite is a precondition for surfacing a mutant, but survivability alone is not a good measure of mutant productivity." (Section 5.1, PDF p. 10)
- "Overall, 87.5% of all generated mutants are killed by the initial test suite." (Section 5.3, PDF p. 10)
- "From our experience, reporting equivalent mutants has been a vastly easier problem than reporting unproductive non-reduntant [sic] and non-equivalent mutants." (Section 6, PDF p. 12)

#### What it means for Purlin

- **Nearest thing to test-aware selection.** Google does not show the test to the mutant
  generator. It does choose the operator by how often similar past mutants survived the tests
  and were marked useful, with the stated aim that the mutant survives. That is selection for
  getting past tests, learned from history. It works: more survivors and more useful ones. The
  paper attaches a plain warning that survival alone is not the goal, because a mutant can
  survive by being unimportant (a changed timeout) or equivalent. For approach 2 this is the
  central risk: a model told to get past the test will find changes the test rightly ignores.
  Google's answer is a human "Not useful" button and suppression rules; Purlin needs an
  equivalent filter if it goes test-aware.
- **Test-blind selection is mostly wasted effort.** With arid code already removed, 87.5% of
  mutants are killed and say nothing new. Before suppression, 85% of what was reported was
  judged unproductive. A single blind bug per proof will usually be caught and usually tell
  nothing about how strong the test is.
- **How many mutants.** Google's working answer is one per changed covered line, a median of 7
  per changelist, and a cap on what is shown. It abandoned the mutation score as neither
  computable at its scale nor actionable. It gives no figure for how many are needed for a
  stable measure, because it does not try to measure; it tries to surface a few useful test
  goals. That matches Purlin's framing of one bug per proof as a prompt, and gives no support
  for reading the result as a score.
- **Equivalent mutants.** No rate. They are folded into "unproductive", which started at 85% of
  reported mutants. 13 of the heuristic families exist to stop equivalent mutants being made
  (cache lookups, collection size compared with zero, capacity hints). The authors found
  equivalence the easier problem; mutants that can be killed but are not worth a test were the
  harder one.
- **Does a caught mutant predict real faults.** Not studied here. The measure is developer
  judgement. The paper lists the long-term effect on tests as future work.
- **Mutation from a specification.** Silent on deriving mutants from one. It makes one related
  remark (Section 1, p. 2): a test written to kill an unproductive mutant tests the current
  implementation instead of the specification, and such tests are brittle. That is an argument
  for tying the planted bug to what the proof says must hold, which favours giving the model the
  requirement in either approach.

---

### 6. Inozemtseva and Holmes: Coverage Is Not Strongly Correlated with Test Suite Effectiveness

- Authors: Laura Inozemtseva, Reid Holmes
- Venue: ICSE 2014
- Link: https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf
- Text read: `inozemtseva2014.txt`, pages 1 to 10 in full; the rest is references.

#### What it did

It asked whether code coverage tracks a test suite's effectiveness once the number of test
methods is held constant. For five large Java projects it drew 31,000 random subsets of the
developers' own tests at fixed sizes (3, 10, 30, 100 and so on). For each subset it measured
statement, decision and modified condition coverage, and effectiveness as the share of PIT
mutants killed. Effectiveness was computed two ways: against all non-equivalent mutants, and
against only those in code the subset covers. It did not use real faults.

#### The numbers

- 5 programs, 80,462 to 724,089 lines; 628 to 7,947 test methods; 31,000 suites, 1,000 per size
  per project.
- Mutants per project: 9,552 to 50,302. Share the full test suite did not kill, and which were
  therefore counted as equivalent: Apache POI 35%, Closure 11%, HSQLDB 0.4%, JFreeChart 21%,
  Joda Time 11%.
- Suite size against normalized effectiveness: r from 0.51 to 0.98.
- Coverage against effectiveness, size ignored (Kendall tau): 0.50 to 0.84 normalized, apart
  from HSQLDB at -0.35; 0.79 to 0.95 non-normalized.
- Size controlled: Joda Time falls from 0.80 to 0.85 to about zero; Apache POI, non-normalized,
  falls from 0.94 to between 0.46 and 0.85. In general low for the normalized measure and
  moderate for the non-normalized one.
- The three coverage types correlate with each other at 0.91 to 0.92 (tau), 0.97 to 0.99
  (Pearson).

#### Quotes

- "We found that there is a low to moderate correlation between coverage and effectiveness when the number of test cases in the suite is controlled for." (Abstract, PDF p. 1)
- "Our results suggest that coverage, while useful for identifying under-tested parts of a program, should not be used as a quality target because it is not a good indicator of test suite effectiveness." (Abstract, PDF p. 1)
- "they assume that any mutant that cannot be detected by the master suite is equivalent. While this technique tends to overestimate the number of equivalent mutants, it is commonly applied because it allows the study of much larger programs." (Section 3.3, PDF p. 4)
- "Although the mutants generated by PIT simulate real faults, it is not self-evident that a suite's ability to kill mutants is a valid measurement of its ability to detect real faults." (Section 3.3, PDF p. 4)
- "Controlling for suite size always lowered the correlation between coverage and effectiveness." (Section 4.3, PDF p. 7)
- "This result suggests that coverage alone is not a good predictor of test suite effectiveness; in many cases, the apparent relationship is largely due to the fact that high coverage suites contain more test cases." (Section 5, PDF p. 8)
- "While coverage measures are useful for identifying under-tested parts of a program, and low coverage may indicate that a test suite is inadequate, high coverage does not indicate that a test suite is effective." (Section 5, PDF p. 8)
- "This means that we classified up to 35% of the generated mutants as equivalent (see the final row of Table 2)." (Section 6.1, PDF p. 9)
- "For example, if the developers frequently test for off-by-one errors, mutants that simulate this error will be detected more often and will be less likely to be classified as equivalent." (Section 6.1, PDF p. 9)
- "Our next step is to confirm our findings using real faults to eliminate this threat to validity." (Section 7, PDF p. 10)

#### What it means for Purlin

- **Bias when the judging tests also define the mutant set.** This is the one paper of the six
  that names it. The mutants that count were those the full developer suite kills; everything
  else was called equivalent. The authors say the surviving set is then shaped by what the
  developers chose to test, and list it as a threat to construct validity. The direction of that
  bias is towards agreeing with the tests. For Purlin the lesson runs both ways: a bug chosen
  blind to the test avoids being shaped by it, and a bug chosen to dodge the test is shaped
  against it; neither is a neutral sample of likely faults. That is an argument for approach 3
  as two different measurements, kept apart, not for either one alone.
- **Equivalent mutants.** The only rates in the six papers: 0.4% to 35% of generated mutants were
  left alive by the full suite, and the authors say that overstates true equivalence. So the
  real rate is unknown, but the mutants that survive for an unknown reason can be a third of all mutants.
- **Suite-size confound.** Shown here for coverage: most of coverage's apparent link to
  effectiveness is the number of tests. Papadakis et al. 2018 (entry 1) show the same thing for
  mutation score against real faults.
- **Does a caught mutant predict real faults.** Not tested. The paper assumes it, cites earlier
  work and Just et al. as support, calls it not self-evident, and names real faults as its next
  step.
- **How many mutants.** Silent.
- **Mutation from a specification.** Silent.

---

### The three claims in docs/audit.md

#### "Tests that catch small planted bugs tend to catch real ones (Just et al.)"

Holds as a statement of what Just et al. found, and needs limits to be safe in public.

- Support: "Mutant detection is positively correlated with real fault detection, independently of code coverage." (Section 3.3, PDF p. 9)
- Limit from the same paper: "However, 17% of real faults, mostly involving algorithmic changes or code deletion, are not coupled to any mutants." (Section 3.2, PDF p. 8)
- Limit from Papadakis et al. 2018, on the same faults: "Our data show that when controlling the test suite size (decouple mutation score from test suite size) all correlations become weak or moderate in the best case." (Section 7, PDF p. 10)

Two further points. The finding is about suites and scores over many mutants; it does not show
that a test which catches one planted bug catches real ones. And the same audit.md paragraph
opens "Planting bugs is the most reliable test of a test"; none of these six papers makes or
tests that claim in those words. A wording the papers support: suites that catch more planted
bugs tend to catch more real faults, the link is weaker once the number of tests is accounted
for, and about one real fault in six has no planted-bug counterpart.

#### "Code coverage ... does not predict that (Inozemtseva and Holmes)"

Overstated in two ways.

- The paper found a low to moderate correlation after controlling for suite size, not none. Its
  title says not strongly correlated. For one project the controlled correlation stayed
  between 0.46 and 0.85, which the authors say "can provide useful information".
- "That" in audit.md means catching real faults. The paper measured effectiveness with mutants
  and did not use real faults: "Our next step is to confirm our findings using real faults to eliminate this threat to validity." (Section 7, PDF p. 10)
- Support for a softer wording: "This result suggests that coverage alone is not a good predictor of test suite effectiveness; in many cases, the apparent relationship is largely due to the fact that high coverage suites contain more test cases." (Section 5, PDF p. 8)

A wording the paper supports: coverage is a weak guide to how many planted bugs a suite
catches once the number of tests is accounted for. If the claim must be about real faults, Just
et al. is the better citation: its Section 3.3 finds the mutation-score correlation with real
fault detection stronger than the statement-coverage one, in four of five programs.

#### "Google plants bugs only in changed code and shows developers the few their tests missed (Petrović et al.)"

Holds.

- "Mutation testing is done incrementally, mutating only changed code during code review, rather than the entire code base" (Abstract, PDF p. 1)
- "Once test results are available, we randomly pick mutants from all surviving mutants to be reported. We limit the number of reported mutants to at most 7 times the number of total files in the changelist" (Section 2.3, PDF p. 3)

Detail the sentence leaves out, none of which makes it wrong: only changed lines that a test
covers, at most one mutant per line, never in arid code, and what is shown is a random subset
of the survivors, not all of them. On the citation: the PDF linked is the arXiv preprint of
February 2021, which describes itself as submitted to the IEEE; the journal year was not
checked here.

---

### What bears on the four approaches

- **No paper compares them.** None plants one bug per test, shows the test to the thing choosing
  the bug, or derives the bug from a requirement. The following is inference from adjacent
  findings.
- **Against test-blind alone.** Most mutants made without regard to the tests are caught for
  uninformative reasons: 87.5% killed at Google after filtering; about 95% subsumed in the ISSTA
  study; killing a random 0.5% of mutants already yields a score of 50% or more. A blind bug that
  the test catches is weak evidence the test is strong.
- **For test-blind.** It is the setting all the real-fault evidence comes from. Just et al. and
  Papadakis et al. 2018 both generated mutants without reference to the tests. Whatever link to
  real faults exists was measured on blind mutants only.
- **For test-aware.** Selecting the hard, non-subsumed mutants gives the sharper measure (ISSTA
  2016), and Google's selection for survival raised both survival and developer-judged usefulness.
- **Against test-aware alone.** A bug that survives is either a weak test or a bug that does not
  matter or is equivalent, and equivalence is undecidable. Google states that survival alone is
  not a good measure. Inozemtseva and Holmes left up to 35% of mutants surviving for an
  unknown reason. A model told to get past the test is steered straight at those. It needs a
  filter: the requirement as the standard for whether the change breaks anything that must hold.
- **For both.** The two answer different questions: does the test catch an ordinary break of
  this requirement, and is there a break of this requirement the test misses. The bias named by
  Inozemtseva and Holmes runs in opposite directions for the two, so reporting them apart is
  defensible and merging them into one figure is not.
- **For several candidates.** A real fault is tied to very few mutants: 2 on average with
  coverage fixed, none 40% of the time (Just et al.); about 1% of mutants resemble a given fault
  (Papadakis et al. 2018). Sampling 10% of mutants loses about 26% of fault detection (survey).
  One candidate is a thin sample. None of the papers gives a number of candidates per test that
  is enough.
- **On reporting.** Any rate summed across proofs inherits the suite-size confound and the
  subsumed-mutant inflation. Google's choice was to drop the score and surface individual
  survivors as test goals.

## Part C. The papers the docs already cite, and what a search found

Its entries are numbered A1 to A4 and B1 to B9 as its reader numbered them; "A" and "B" here are this part's own.

Compiled 2026-10-01. Every quote below was copied from the text extracted from the paper's PDF
(the session's scratch folder) and checked by script against that text; the page is the PDF
page. Only line-break hyphenation, ligatures and spaces lost by the extractor around italic words
were repaired. Square-bracket citation numbers inside quotes are the paper's own.

The four approaches under decision:

1. **Test-blind.** The model sees the requirement and the code only.
2. **Test-aware.** The model sees the test and is told to get past it, with a guard against changes
   that do not violate the requirement.
3. **Both in one request.**
4. **Several candidates per proof.**

How much of each paper was read is stated in each entry. "Read in full" means the whole body up to
the reference list.

---

### Part A. Papers the project's docs already cite

#### A1. Do LLMs generate test oracles that capture the actual or the expected program behaviour?

- Authors: Michael Konstantinou, Renzo Degiovanni, Mike Papadakis
- Venue and year: arXiv preprint, 28 October 2024 (v1). No venue is stated in the PDF.
- Link: https://arxiv.org/pdf/2410.21136
- Text file: `2410.21136.txt` (12 pages, read in full)

**What it did.** The authors gave GPT-3.5 Turbo a Java method, sometimes its docstring and class,
and a test with the assertion removed. In one task the model judged whether a given assertion was
correct; in the other it wrote five assertions. They built four cases for the judging task: correct
or buggy code, paired with a correct or a wrong assertion. The buggy code came from the mutation
tool µBERT. They also renamed tests and variables to meaningless names to see what the model
relies on. Data: 24 open-source Java repositories and the Gitbug-Java set.

**Numbers.**

- Judging a correct assertion beside correct code: 40.77%, 46.26%, 45.39% accuracy for the three
  prompt variations (Table I).
- Judging the same correct assertion beside buggy code: 31.94%, 36.80%, 37.01%. The drop is 8.82,
  9.46 and 8.38 points.
- Judging a wrong assertion: 51.06% to 61.84% beside correct code, 79.61% to 84.16% beside buggy
  code.
- Meaningless test and variable names lowered accuracy by up to 16.10 points (prompt variation 1).
- Writing assertions: 57.47% to 60.01% of generated assertions passed on the program under test;
  at least one of the five passed for 89.34% to 93.76% of test prefixes.
- One model only: GPT-3.5 Turbo. 1,000 records per case.

**Quotes.**

- "Our findings show that LLM-based test generation approaches are also prone on generating oracles that capture the actual program behaviour rather than the expected one." (Abstract, p. 1)
- "Interestingly, our results show that LLMs are more likely to generate test oracles that capture the actual program behaviour (what is actually implemented) rather than the expected one, i.e., the intended behaviour." (Section I, p. 2)
- "LLM’s test oracle classification accuracy considerably drops in the presence of buggy code, suggesting that its predictions are derived towards the actual implementation rather than the desired one." (Section IV-A, Conclusion RQ1, p. 6)
- "Hence, although multiple studies use LLMs as if they would extract the expected oracle, our empirical results suggest that the LLM follows the actual code execution to find the test oracle." (Section V-B, p. 8)
- "Taken together, our results corroborate the conclusion that unless having meaningful test or variable names LLMs can mainly be used to capture the actual program behaviour (thus to be used for regression testing)." (Section I, p. 2)
- "Therefore, the LLM could guess better what should be the expected test assertion, regardless the actual code implementation." (Section V-C, p. 9)
- "The accuracy in this case is measured as the ratio between the number of assertions that make the test pass, among all generated assertions." (Section IV-C, p. 7)
- "We chose to use GPT 3.5-turbo [28] for this experiment because it is a state-of-the-art tool and one of the most widely used LLMs." (Section III-A, p. 3)

**Does the docs claim hold?** The docs say: "A model tends to take a test's expected answer from
the code as written. A bug in the code is then copied into the test."

- The first sentence holds. It is the paper's stated finding (Abstract, Section I, Section V-B).
- The second sentence is an inference, and the paper does not measure it. The buggy-code
  experiment is the judging task: the model rejects a correct assertion more often when the code is
  buggy. The writing task (RQ3) scores an assertion as correct when it passes on the program under
  test, as the seventh quote shows, so it cannot show a bug being written into a test. A wording
  the paper supports: "Shown buggy code, the model more often rejects the correct expected answer."
- Limits to state with the claim: one model (GPT-3.5 Turbo, 2024), Java, and overall accuracy
  below 50% even with correct code.

**What it means for Purlin.**

- Test-blind (1): the paper's mechanism applies to the bug planter too. A model shown code and
  asked what should hold leans on the code. Purlin's proof is a sentence a person wrote, and the
  paper's own finding is that human-meaningful names and descriptions pull the model back toward
  the intended behaviour. That supports giving the planter the proof as the authority.
- Test-aware (2): if the test's expected answer was copied from buggy code, a planter shown that
  test inherits the same error as its target. The paper gives no measurement of this.
- Both (3) and several candidates (4): asking for five assertions raised "at least one correct" to
  about 90% while per-assertion accuracy stayed near 60%. Several candidates raise the chance that
  one is usable; they do not raise the quality of each.

---

#### A2. Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models Across Agreement, Consistency, and Bias

- Authors: Justin D. Norman, Michael U. Rivera, D. Alex Hughes (UC Berkeley School of Information)
- Venue and year: arXiv preprint, 17 June 2026 (v1). No venue is stated in the PDF.
- Link: https://arxiv.org/pdf/2606.19544
- Text file: `2606.19544.txt` (25 pages, read in full including the appendices)

**What it did.** The authors ran 21 models from nine providers as judges on three benchmarks of
paired answers (MT-Bench, JudgeBench, RewardBench). They measured agreement with human labels,
repeatability across 3 to 5 reruns, and whether the verdict changes when the two answers swap
places. All runs used temperature 0 with reasoning switched off. Total: 118 runs and about 541,000
judgments. The task is choosing the better of two chat answers. It is not judging tests or code
changes.

**Numbers.**

- Repeatability (Krippendorff's alpha across reruns), mean over the consistency cohort: 0.943 on
  MT-Bench and 0.911 on JudgeBench in the text for 16 judges; Table 6 lists 17 judges with means
  0.944 and 0.913.
- Verdict changes when the order swaps (flip rate): cohort mean 0.099 on MT-Bench and 0.173 on
  JudgeBench (Table 6); highest 0.380 (GPT-4o-mini on JudgeBench).
- Agreement with humans on MT-Bench: raw match 0.788 to 0.851, chance-corrected kappa 0.376 to
  0.511. On JudgeBench kappa runs from 0.271 to 0.875.
- Two judges have repeatability above 0.95 and position bias above 0.10: Qwen 3 8B (0.992, 0.192)
  and Gemini 2.5 Flash (0.988, 0.125).
- The abstract says rankings shift "by up to 14 positions"; Section 4.3 says the largest shift is
  15 positions. The paper is inconsistent here.

**Quotes.**

- "Surveys of LLM-as-Judge (LLMaJ) reliability identify a recurring set of failure modes: inconsistency across prompts and runs, systematic scoring biases, weak domain-specific calibration, and the absence of meta-evaluation standards for comparing judges on equal footing." (Section 1, p. 1)
- "Test-retest studies show substantial temperature sensitivity: same-verdict rates are above 95% when temperature is set to 0, but fall to as low as 70% when temperature is increased to 1 (Stureborg et al., 2024; Haldar and Hockenmaier, 2025)." (Section 2.2, p. 3)
- "Across a range of judge models, flip rates range from 25% to 50% (Wang et al., 2024; Shi et al., 2025)." (Section 2.1, p. 3)
- "Every judge in our study exhibits substantial kappa deflation on MT-Bench: exact match overstates chance-corrected agreement by between 33.8 and 41.3 percentage points across the 21 models, with a cohort mean of 38.6 pp." (Section 4.1, p. 4)
- "Consistent with Hypothesis 6, seven of the sixteen judges evaluated under the consistency protocol show a position flip-rate increase of at least 1.5× from MT-Bench to JudgeBench." (Section 4.6, p. 6)
- "Test-retest reliability follows a similar pattern at the cohort level: the mean test–retest across the 16 judges drops from 0.943 on MT-Bench to 0.911 on JudgeBench." (Section 4.6, p. 6)
- "This result has methodological implications for future teams: test–retest measures the stability of a judge’s outputs, not the correctness of the underlying decision process." (Section 4.7, p. 6)
- "High stability with high bias is a failure mode, not a strength." (Section 5.3, Minimum Viable Validation Protocol, p. 8)
- "Reasoning-enabled evaluations could change agreement, consistency, and bias profiles, and we do not claim our results characterize the thinking-on configuration." (Limitations, p. 9)

**Does the docs claim hold?** The docs say asking a model whether a test looks good is the weakest
check "because models judge inconsistently". **This does not hold as worded.** The paper's own
measurement is the opposite on plain repetition: at temperature 0 the judges repeat their verdicts
(mean alpha 0.943). Its title and main finding are that judges are repeatable without being right.
What the paper does support:

- The verdict changes with the order the two answers are shown: mean flip rate 0.099, rising to
  0.173 on the harder benchmark.
- Agreement with human labels, once chance is removed, is moderate: kappa 0.376 to 0.511 on
  MT-Bench.
- "Inconsistency across prompts and runs" appears only where the paper summarises earlier surveys
  (first quote), and the 70% same-verdict figure at temperature 1 is cited from other work (second
  quote).

A wording the paper supports: "a model judge can give the same answer every time and still be
wrong; its verdict agrees only moderately with people and changes with the order of what it is
shown." The paper studies chat answers, not tests, and says nothing about test quality.

**What it means for Purlin.**

- All four approaches keep the test run as the decider, which this paper supports: a repeatable
  model verdict is not evidence of a correct one.
- Test-aware (2) adds a model judgment that Purlin does not have today: the guard that the change
  "really violates the requirement". This paper is a reason not to let that guard be a bare model
  verdict. A guard that can be run, such as a second test taken from the proof, would not depend
  on it.
- The order effect bears on approach 3. If one request holds both a blind and an aware candidate,
  which comes first may change what the model returns. The paper measures this for verdicts, not
  for generated code.

---

#### A3. Automated Unit Test Improvement using Large Language Models at Meta

- Authors: Nadia Alshahwan, Jubin Chheda, Anastasia Finegenova, Beliz Gokkaya, Mark Harman, Inna
  Harper, Alexandru Marginean, Shubho Sengupta, Eddy Wang (Meta Platforms)
- Venue and year: FSE 2024 (the PDF's own header); arXiv v1, 14 February 2024
- Link: https://arxiv.org/pdf/2402.09171
- Text file: `2402.09171.txt` (12 pages, read in full)

**What it did.** TestGen-LLM asks two Meta models to extend an existing human-written Kotlin test
class. Each candidate test passes three filters in order: it builds, it passes five times in a
row, and it adds line coverage over every existing test in the build target. What survives goes to
an engineer for review. The paper reports an evaluation on Instagram Reels and Stories and three
"test-a-thon" deployments in late 2023.

**Numbers.**

- Reels and Stories evaluation, 86 test classes: 75% had a new test that built, 57% one that also
  passed reliably, 25% one that also added coverage.
- Deployment: 196 of 1,979 test classes improved ("approximately 10%" in Section 4; the abstract
  says 11.5%). 73% of its recommendations were accepted by engineers.
- Per attempt to generate one test: success rate 0.05 on Facebook (490 of 8,996) and 0.04 on
  Instagram (831 of 23,535).
- Facebook test-a-thon: of 280 diffs, 144 accepted, 64 rejected or abandoned, 61 not reviewed, 11
  withdrawn.

**Quotes.**

- "TestGen-LLM verifies that its generated test classes successfully clear a set of filters that assure measurable improvement over the original test suite, thereby eliminating problems due to LLM hallucination." (Abstract, p. 1)
- "Without an automatable test oracle [7], TestGen-LLM cannot automatically determine whether a failing test has found a bug, or whether it merely contains an incorrect test assertion." (Section 2, p. 2)
- "Therefore, TestGen-LLM discards any test case that does not pass on first execution." (Section 2, p. 2)
- "The effect of this filter is to preserve only tests that can be used for regression testing [50]." (Section 2, p. 2)
- "Any test that does not improve coverage is also discarded." (Section 2, p. 2)
- "One diff was abandoned because the test case did not include any assertion." (Section 3.2.1, p. 5)
- "We observed that both LLM1 and LLM2 often generated almost identical tests for the same prompt; different in name only." (Section 5, p. 8)
- "We have taken the simple approach of measuring line coverage as a proxy for improvement, but it is merely an expedient proxy for ‘improvement’." (Section 7, p. 10)
- "Mutation coverage [23] would likely be the best performing criterion." (Section 7, p. 10)
- "it submits, for human review, only test cases that it can guarantee improve on the existing code base." (Section 8, p. 10)

**Does the docs claim hold?** The docs say: "At Meta, AI-written tests ship only after a measured
check." **It holds, with two things worth stating.**

- The measured check is: builds, passes five times, adds line coverage. The paper itself calls line
  coverage "merely an expedient proxy" and names mutation as the better measure.
- A person still reviews each test before it lands. The filters did not stop a test with no
  assertion; an engineer did (sixth quote).

**What it means for Purlin.**

- The paper's design is the one Purlin already follows: the model proposes, a run decides.
- Several candidates (4): the same prompt often returned near-identical output, "different in name
  only", at temperature 0. Asking the same question several times is a weak way to get different
  candidates. The paper got its variety from four prompts and two models; most prompt and model
  pairs contributed tests the others did not.
- The paper keeps a test only if it passes on the current code, so it "preserve[s] only tests that
  can be used for regression testing". That is the weakness A1 describes and the reason a planted
  bug is needed at all.

---

#### A4. Harden and Catch for Just-in-Time Assured LLM-Based Software Testing: Open Research Challenges

- Authors: Mark Harman, Peter O'Hearn, Shubho Sengupta
- Venue and year: FSE Companion 2025 (keynote paper, the PDF's own header); arXiv v2, 14 May 2025
- Link: https://arxiv.org/pdf/2504.16472
- Text file: `2504.16472.txt` (17 pages, read in full)

**What it did.** This is a position paper with definitions, not an experiment. It defines a
"hardening" test (passes now, fails on some future bad change) and a "catching" test (fails on the
change in front of it), each "weak" or "strong" by whether the pass or fail is right according to
what was intended. It reviews Meta's ACH tool in two pages and sets out which test results are safe
to show an engineer. It reports no new measurements.

**What it says on the questions asked.**

- Equivalent mutants: one sentence. ACH only offers a test together with the mutant that test
  kills, so a mutant nobody can kill never reaches an engineer.
- Whether the fault generator sees the tests: the paper does not say. It says the mutant is one
  "not caught by any existing test", which is established by running the tests.
- False positives: treated at length for tests, not for mutants. The target it proposes is recall
  at a fixed precision of 0.8.
- No Meta follow-up titled "Mutation Testing via Iterative Large Language Model-Driven Scientific
  Debugging" exists. A paper of that name is by Straubinger and others at the University of Passau
  and is entry B3.

**Quotes.**

- "The mutation-guided approach ensures that the generated tests find faults that no other test can find." (Section 2.1, p. 2)
- "Furthermore, since our deployment places test generation in a scenario in which the mutant is guaranteed to be killed, we also sidestep the familiar equivalent mutant problem [41, 51, 58, 68, 80]." (Section 2.5, p. 3)
- "As a result, ACH tests accepted by the engineer are strong hardening tests; the engineer confirms that the test correctly passes on the current revision, while the ACH technology automatically generates the assurance that it catches at least one bug (the mutant) not caught by any existing test." (Section 3.3, p. 6)
- "Strictly weak hardening tests are problematic because they introduce a false sense of security; the current revision is wrongly believed to be more correct than it is." (Section 3.3, p. 7)
- "Instead, we can estimate the recall using, for example, mutation testing (to sample the space of potential faults) or leak through of faults into production (to determine a lower bound on the number of false negatives)." (Section 3.5, p. 7)
- "Although we cannot hope achieve perfect precision and recall, unnecessarily low precision can lead to the entire automated testing technology being abandoned due to friction on the engineers who waste their time considering false positives." (Section 3.5, p. 7)
- "Nevertheless, when our goal is to automatically provide a better test plan than ‘YOLO’, we would need to be cautious to ensure that our LLM-based test generation techniques do not become victims to the obvious circularity involved by also using LLMs to infer the code summaries." (Section 6.1, p. 13)
- "For the purpose of oracle extraction, we have to treat executable text (the executable source code) as potentially suspicious, and focus on extraction of intended semantics from non-executable text, so that we can compare intended and actual semantics." (Section 6.4, p. 15)

**What it means for Purlin.**

- The last quote is the closest statement in this literature to Purlin's design: take what was
  intended from text a person wrote, treat the code as suspect, compare the two. It is an argument,
  not a result.
- Purlin's position differs from ACH's in one way that matters for the choice. ACH writes a test to
  kill a mutant, so an unkillable mutant costs nothing. Purlin plants a bug to judge a test that
  already exists, so a planted change that breaks nothing reads as "the test missed it". Purlin
  cannot sidestep the equivalent-mutant problem the way ACH does. That raises the cost of approach
  2 and of any approach that prefers survivors.
- "Sample the space of potential faults": the paper frames a planted bug as one sample. One sample
  per proof gives one bit. That is an argument for approach 4, without numbers.
- The circularity warning applies if the same model reads the test, picks the bug and then judges
  its own bug valid.

---

### Part B. Literature found by search

#### B1. A Comprehensive Study on Large Language Models for Mutation Testing

(Earlier versions were titled "An Exploratory Study on Using Large Language Models for Mutation
Testing".)

- Authors: Bo Wang, Mingda Chen, Ming Deng, Youfang Lin, Mark Harman, Mike Papadakis, Jie M. Zhang
- Venue and year: ACM Transactions on Software Engineering and Methodology, 2025 (the PDF's own
  header); arXiv v5, 22 January 2026
- Link: https://arxiv.org/pdf/2406.09843
- Text file: `2406.09843.txt` (39 pages, read in full)

**What it did.** The authors generated more than 701,400 Java mutants with four older tools (PIT,
Major, LEAM, µBERT) and three LLM methods (BugFarm, LLMorpheus and their own prompt, "LLMut") over
several models. They compared the mutants with 851 real bugs: 605 from Defects4J and 246 from
ConDefects. Their prompt gives the whole method, six real-bug examples, and asks for one mutant
per line, all returned in one JSON reply. Section 4.1 varies what the prompt contains. This is the
only study found that compares "code only" with "code plus its unit tests" in the prompt.

**Numbers.**

- Prompt contents (Table 14, 306 bugs). P1 whole file; P2 method plus its unit tests; P3 method
  only (the default); P4 the target element only; P5 method without the real-bug examples.
  - GPT-4o, P2 against P3: real-bug detection 83.9% against 85.0%; coupling rate 49.7% against
    52.2%; mutation score 0.801 against 0.773; tokens per mutant 218 against 105.
  - DeepSeek-V3, P2 against P3: detection 84.7% against 85.5%; coupling 50.0% against 53.2%;
    mutation score 0.753 against 0.765.
  - The differences among prompts are not statistically significant (Table 16).
  - The study did not measure the equivalent-mutant rate or the share of survivors per prompt, and
    its test-carrying prompt did not ask the model to get past the tests.
- Duplicates when many mutants are asked for in one reply: 7.8% for GPT-4o, 7.5% for DeepSeek-V3,
  37.1% for CodeLlama-13b, 0% for PIT and Major (Table 4). The prompt says "Avoid generating
  duplicate mutants."
- Compilable: 76.4% for GPT-4o against 97% to 100% for the rule-based tools.
- Equivalent mutants, by hand on a sample of about 96 per method: 1.0% PIT, 2.1% Major, 3.1% to
  6.3% for GPT-4o and DeepSeek methods, 10.6% for StarChat (Table 10). 1,437 mutants were labelled.
- Surviving mutants that are not equivalent (Table 13): for the authors' prompt, 54% to 80% sit in
  code no test runs.
- The abstract gives the rule-based real-bug detection rate as 44.15%; the answer to RQ1 gives
  41.64%. The paper is inconsistent on this figure.

**Quotes.**

- "the longest prompt with the whole Java file, performs the worst in most cases, indicating that providing more information does not necessarily help LLMs generate more bug-representative mutants." (Section 4.1.1, p. 26)
- "P2, which adds unit tests to the context compared with P3, shows slightly reduced effectiveness—suggesting that including unit tests does not help the model generate better mutants." (Section 4.1.1, p. 26)
- "The results suggest that on both GPT-4o and DS-671b, although P3 achieves the most balanced overall performance, the differences among prompts are not statistically significant." (Section 4.1.1, p. 27)
- "Therefore, despite variations in few-shot examples, there is no statistically significant evidence indicating superior performance among the prompts." (Section 4.1.3, p. 28)
- "Therefore, based on the given code context, we generate one mutant per line." (Section 2.2.2, p. 7)
- "For all LLM-based approaches, we use the default settings of each model (e.g., token limits and temperature)." (Section 2.5, p. 13)
- "These results indicate that even equipped with the state-of-the-art LLM, these approaches still generate a non-negligible proportion of duplicate mutants." (Section 3.2.2, p. 19)
- "In total, 1437 mutants were labeled, 860 of which were filtered by tests (i.e., killed), and the remaining 577 were manually checked." (Section 3.2.3, p. 19)
- "On average, the rule-based approaches produce about 1.5× more compilable mutants and 4-9× fewer redundant or equivalent mutants than LLM-based approaches." (Answer to RQ2, p. 20)
- "Compared with rule-based approaches, LLM-based approaches tend to generate mutants in code lines that are not covered or not injected by existing test suites, providing valuable guidance for enhancing unit tests." (Answer to RQ5, p. 25)
- "In other words, our study operates under the clean program assumption, which may not fully capture the dynamics of bug detection in practical scenarios." (Section 5, p. 33)

**What it means for Purlin.**

- Test-blind (1) against both-in-context (3): this is direct evidence that putting the tests in the
  prompt, without an instruction about them, does not make the bugs more like real ones, costs
  about twice the tokens, and moves the kill rate in no consistent direction. It matches Purlin's
  present request (requirement, test and code, no instruction about the test). It gives no reason
  to keep the test in the request unless the request says what to do with it.
- Test-aware (2): not tested here. The study's test-carrying prompt never told the model to evade.
- Several candidates (4): one request for many mutants works and is cheap (126 input tokens and
  about 59 output tokens per mutant), at the price of 7% to 8% duplicates with strong models. The
  duplicates are exact text matches and are removed by string comparison.
- No specification was ever in the prompt. The study does not cover Purlin's case of a written
  requirement.

---

#### B2. Large Language Models for Equivalent Mutant Detection: How Far Are We?

- Authors: Zhao Tian, Honglin Shu, Dong Wang, Xuejie Cao, Yasutaka Kamei, Junjie Chen
- Venue and year: ISSTA 2024 (the PDF's own header); arXiv v1, 3 August 2024
- Link: https://arxiv.org/pdf/2408.01760
- Text file: `2408.01760.txt` (13 pages, read in full)

**What it did.** The authors took 3,302 Java pairs of a method and its mutant from MutantBench,
each labelled equivalent or not, and split them in half for training and testing. They compared
ten older detectors with LLM methods of five kinds: a classifier on frozen code embeddings, a
classifier on fine-tuned embeddings, a zero-shot question, a few-shot question, and a model
fine-tuned on the question. The mutants are from rule-based operators, not from an LLM, and
comments were stripped. No requirement or specification is involved: equivalence means "same
behaviour as the original code".

**Numbers** (test set: 249 equivalent, 1,401 not; precision, recall and F1 are macro-averaged).

- Asking the model directly, zero-shot: GPT-4 precision 67.42%, recall 53.76%, F1 53.61%;
  GPT-3.5 Turbo F1 59.44%; Code Llama 7B F1 48.04%.
- Asking with three examples: GPT-4 F1 55.90%; GPT-3.5 Turbo 51.59%.
- Fine-tuned embedding classifier (UniXCoder, 110M parameters): precision 94.33%, recall 81.81%,
  F1 86.58%. Fine-tuned GPT-3.5 Turbo on the question: F1 82.31%.
- Compiler-based check (TCE): F1 39.31% and 50.80%.
- Time per pair: GPT-4 zero-shot 0.58 s; fine-tuned UniXCoder 0.043 s.
- Each method was run once.

**Quotes.**

- "Our findings demonstrate that LLM-based techniques significantly outperform existing techniques (i.e., the average improvement of 35.69% in terms of F1-score), with the fine-tuned code embedding strategy being the most effective." (Abstract, p. 1)
- "Prior research has found that the rate of equivalent mutants in real-world development scenarios might lie between 4% and 39% [51]." (Section 2.2, p. 3)
- "It is noted that natural language comments do not contribute to the equivalent mutant detection task." (Section 3.1, p. 4)
- "Please identify if the two above codes are semantically equal." (Section 3.4, zero-shot prompt, p. 5)
- "Additionally, LLMs based solely on prompting strategies cannot achieve comparable performance." (RQ2 Summary, p. 8)
- "It significantly suggests that LLMs based solely on prompting strategies cannot achieve comparable performance on equivalent mutant detection, further supporting the findings in RQ2." (Section 4.3, p. 9)
- "Hence, we can further investigate the role of CoT prompting in the task of equivalent mutant detection." (Section 5.2, p. 11)
- "Last, due to the limited computational resources and cost, we did not run our studied EMD techniques multiple times to mitigate potential variance and randomness." (Section 5.3, p. 11)

**What it means for Purlin.**

- The cheap guard that approach 2 needs, "ask the model whether the change really differs", scored
  an F1 near 54% to 59% with GPT-4 and GPT-3.5 in 2024. The methods that worked need labelled training data, which Purlin does not have.
- The models are two generations old and reasoning prompts were not tried, so this is a lower
  bound on today's models, not a measurement of them.
- Purlin's question is a different one: "does the change violate the proof?", not "does the change
  behave like the original?". No paper found measures that.

---

#### B3. Mutation Testing via Iterative Large Language Model-Driven Scientific Debugging

- Authors: Philipp Straubinger, Marvin Kreis, Stephan Lukasczyk, Gordon Fraser
- Venue and year: arXiv preprint, 11 March 2025 (v1). No venue is stated in the PDF.
- Link: https://arxiv.org/pdf/2503.08182
- Text file: `2503.08182.txt` (10 pages, read in full)

**What it did.** The authors had gpt-4o-mini write tests to kill 7,380 mutants made by the
rule-based tool Cosmic Ray in ten Python projects. Four ways of asking were compared: once; with up
to ten retries after seeing the test's result; and two "scientific debugging" variants where the
model states a hypothesis, runs an experiment and concludes. At any point the model could declare
the mutant equivalent. The authors then checked a sample of those declarations by hand.

**Numbers.**

- 2,427 of 7,380 mutants were declared equivalent by at least one method. 1,086 of those were
  killed by the same method's own later test. Running every generated test killed 599 more,
  leaving 742.
- Hand check of flagged survivors: 98 could be killed with simple tests, 24 could be considered
  equivalent. The authors project about 146 of the 2,427 as truly equivalent, which is 6%.
- The two scientific variants declared more than 15% of mutants equivalent; the single-request
  baseline declared none.
- Mutation score: about 60% for one request, about 80% for the three iterative methods.
- Section IV-C3 then refers to "The 29 mutants considered equivalent"; the counts given are 24
  flagged and 4 unflagged. The paper is inconsistent by one.

**Quotes.**

- "Additionally, scientific approaches tend to label more mutants as equivalent if no test is found for them, but most of these mutants are not actually equivalent." (Section I, p. 2)
- "Both scientific approaches, however, identified over 15 % of mutants as equivalent." (Section IV-C2, p. 7)
- "Out of the 7,380 mutants, 2,427 were flagged as equivalent by at least one of our methods." (Section IV-C3, p. 7)
- "Of these 2,427 mutants, 1,086 were also killed by one of our approaches when targeted, leaving 1,341 flagged mutants alive." (Section IV-C3, p. 7)
- "For the flagged mutants, we found that in 98 cases, the mutants could be killed with simple tests, while the remaining 24 can be considered equivalent." (Section IV-C3, p. 7)
- "This highlights the limitations of equivalence detection by using Large Language Models." (Summary RQ3, p. 8)
- "A key takeaway from our work is that the specific LLM-based approach used for automated test generation matters less than ensuring that the process is iterative." (Section VII, p. 9)

**What it means for Purlin.**

- A model's statement that a change makes no difference was wrong about 94% of the time here. The
  mirror statement matters for approach 2: the model's own word that its change does make a
  difference is the guard, and this paper gives no measurement of that direction.
- What did work was running something. A flagged mutant was shown to differ by a test that killed
  it. For Purlin the same move is available: the guard on a test-aware bug can be a run (a second
  check derived from the proof fails on the bug) instead of a model's opinion.
- The model is gpt-4o-mini. Stronger models may do better; the paper does not test them.

---

#### B4. LLMorpheus: Mutation Testing using Large Language Models (journal version)

- Authors: Frank Tip, Jonathan Bell, Max Schäfer
- Venue and year: IEEE Transactions on Software Engineering, 2025 (accepted version, DOI
  10.1109/TSE.2025.3562025, from the PDF's own header)
- Link: https://par.nsf.gov/servlets/purl/10596238 (arXiv version: https://arxiv.org/pdf/2404.09952)
- Text file: `kumo.txt` (21 pages; pages 1 to 12 read: introduction, approach, RQ1 to RQ5. RQ6,
  RQ7, threats and related work were not read.)

This paper is already cited by the project's docs for a different claim. It is entered here only
for what it measures on run-to-run variation, on asking for one or three mutants per request, and
on equivalent mutants.

**What it did.** The tool replaces one expression in a JavaScript file with a placeholder and asks
a model for three replacements that behave differently, each with a one-line reason. The prompt
holds up to 200 lines of surrounding code. It holds no tests and no specification. The authors ran
13 packages with five models, four temperatures and six prompt variants, repeating runs five
times.

**Numbers.**

- Same request, five runs, temperature 0, codellama-34b: 89.29% to 98.89% of mutants appeared in
  all five runs.
- Same, by temperature, for Complex.js: 97.04% common to all five runs at 0.0; 18.99% at 0.25;
  6.41% at 0.5; 0.4% at 1.0.
- Same, temperature 0, other models: 34.22% to 50% (mixtral-8x7b), 28.26% to 58.94%
  (llama-3.3-70b), and the same range printed again for gpt-4o-mini.
- One replacement per request against three: 2,333 mutants against 6,712.
- Of 9,967 candidates: 29.0% not valid syntax, 1.6% identical to the original, 2.1% duplicates.
- Surviving mutants checked by hand: 106 of 524 (20%) equivalent for the LLM tool, 20 of 430 (5%)
  for the rule-based StrykerJS.

**Quotes.**

- "on average, 29.0% (2,894/9,967) of candidate mutants are discarded because they are syntactically invalid, 1.6% (156/9,967) are discarded because they are identical to the original code, and 2.1% (205/9,967) are discarded because they are duplicates." (Section IV-C, p. 7)
- "LLMs are nondeterministic, even at temperature 0.0, so a subsequent experiment may produce results that differ from those shown in Table II." (Section IV-C, p. 7)
- "We found that, at temperature 0.0, the results of LLMorpheus are generally stable across runs, with between 89.29% and 98.89% of all mutants being observed in all 5 experiments" (Section IV-C, p. 7)
- "Of the 524 LLMorpheus mutants examined, the majority (418, or 80%) are “not equivalent” and 106 (20%) are “equivalent”." (Section IV-D, p. 9)
- "At temperature 1.0, there are 4,200 distinct mutants, of which 17 (0.4%) are common to all runs, meaning that, effectively, at temperature 1.0, each run produces completely different mutants." (Section IV-E, p. 9)
- "using onemutation dramatically reduces the number of mutants from 6,712 to 2,333, demonstrating that it is helpful to request multiple suggestions" (Section IV-F, p. 10)
- "We infer that prompting for multiple mutants can result in the LLM suggesting more significant code changes than it would otherwise have." (Section IV-F, p. 11)
- "With mixtral-8x7b-instruct, between 34.22%–50% of mutants occur in all five runs" (Section IV-G, p. 11)
- "We also analyzed the variance of the number of mutants killed and survived, finding that the mutation score was relatively stable despite the diversity of mutants across trials." (Section IV-G, p. 11)

**What it means for Purlin.**

- One bug per proof (today, and approaches 1 and 2 as single requests): which bug is planted is
  not repeatable on current hosted models, even at temperature 0. With some models fewer than half
  the mutants recur across five runs. A per-proof verdict that rests on one planted bug can change
  between two audits of the same commit. The paper found the aggregate score stable; it did not
  measure the stability of a verdict on one target.
- Several candidates (4): asking for three in one request gave three with 2.1% duplicates, and the
  second and third were larger changes than a single request would give. This is the best direct
  evidence that one request can carry several candidates.
- A fifth of the survivors were changes that make no difference, four times the rule-based rate,
  with a prompt that told the model to change behaviour. Any approach that looks for survivors
  inherits this.

---

#### B5. Intent-Based Mutation Testing: From Naturally Written Programming Intents to Mutants

- Authors: Asma Hamidi, Ahmed Khanfir, Mike Papadakis
- Venue and year: arXiv preprint, 6 July 2026 (v1). No venue is stated in the PDF.
- Link: https://arxiv.org/pdf/2607.05149
- Text file: `2607.05149.txt` (11 pages, read in full; the appendix lists the 29 task descriptions)

**What it did.** This is the closest paper found to planting a fault from a written requirement.
The requirement is the task description of a HumanEval-x Java problem. One method changes one word
of the description at a time (BERT predicts a replacement for each word in turn) and has GPT-3.5
Turbo write a new implementation from each changed description. A second method leaves the
description alone and asks GPT-3.5 for ten implementations. Any result that fails a test the
reference solution passes counts as a killed mutant. The baseline is µBERT, which changes code
tokens. Each problem has a large test suite taken from HumanEval+.

**Numbers** (29 problems; mean 659 tests per problem; Table II).

- Changed description: 2,357 generated, 2,144 compile (91%), 1,524 killed, 620 survive (29% of
  those that compile).
- Unchanged description, ten implementations: 290 generated, 235 compile (81%), 211 killed, 24
  survive.
- µBERT on the code: 3,608 generated, 996 compile (27.6%), 879 killed, 117 survive.
- Tests chosen to kill one method's mutants, scored on the best mutants of all three: 0.817 for
  changed descriptions, 0.77 for µBERT, 0.66 for unchanged descriptions.
- The paper does not say how many survivors are equivalent to the reference, and does not check
  whether a killed mutant violates the original description.

**Quotes.**

- "In contrast to traditional mutation testing, which changes (mutates) the way programs are written, intent mutation changes (mutates) the behavior of the programs by producing mutations that implement (slightly) different intents than those implemented in the original program." (Abstract, p. 1)
- "The mutations of the programming intents represent possible corner cases and misunderstandings of the program behavior, i.e., program specifications, and thus can capture different classes of faults than traditional (syntax-based) mutation." (Abstract, p. 1)
- "We also show that 55% of the intent-based mutations are not subsumed by traditional mutations." (Abstract, p. 1)
- "We employ GPT-3.5- with 0.8 temperature, to generate code from intents written in natural language." (Section III-C, p. 3)
- "This way we can generate mutants that represent mistakes of the intent done by the LLM." (Section III-C, p. 3)
- "Unfortunately, our test subjects are small and result in very few mutations for many cases." (Section IV-B, p. 4)
- "In fact, the majority (over 80%) of the implementations obtained by intent-based mutation are valid (91% by µINTMUT and 81% by oINTMUT)" (Section V-A, p. 5)
- "Particularely, as we generate multiple mutants for different programs, we believe that the overall outcomes of the study will remain unchanged." (Section VI-A, p. 8)

**What it means for Purlin.**

- Test-blind (1): this is evidence that a fault can be planted from the requirement's words with
  no sight of the tests, and that such faults are different from code-token faults: tests chosen
  for them catch more of everyone's faults (0.817 against 0.77). It is the strongest support found
  for approach 1.
- The method rewrites the whole function from the changed sentence. Purlin makes a small edit to
  existing code. The paper's faults are large (about 69 tokens changed on average) and its
  subjects are single functions with hundreds of tests.
- 29% of the compiled results passed every one of about 659 tests. Either the changed word did not
  matter or the tests missed it. The paper does not separate the two. A Purlin planter working
  from the proof would face the same question, and the paper offers no way to answer it.
- Several candidates (4): the authors rely on many mutants per problem to wash out run-to-run
  differences, and say so, without measuring it.

---

#### B6. Round-Trip Mutation Testing: Translating Code to Natural Language Intent and back

- Authors: Asma Hamidi, Cedric Richter, Ahmed Khanfir, Mike Papadakis
- Venue and year: arXiv preprint, 3 July 2026 (v1). No venue is stated in the PDF.
- Link: https://arxiv.org/pdf/2607.03223
- Text file: `2607.03223.txt` (6 pages, read in full)

**What it did.** For code with no written description, GPT-4o-mini first describes a Python
function in a few sentences, in a "broad" or a "precise" style, and then writes a function from
that description. The differences are the mutants. Two further variants change a word of the
description before writing the code. Subjects are 40 buggy methods from BugsInPy; ten mutants per
method; the baseline is a re-implementation of MutPy's operators.

**Numbers** (Table II and Table III).

- Share of mutants that run and are killed: 70.75% broad, 65.50% precise, 66.50% broad with a
  changed word, 50.50% precise with a changed word, 72.01% rule-based.
- Share that survive every test: 0.25%, 2.00%, 0.00%, 1.50%, against 17.93% rule-based.
- Share that fail with a runtime error ("incompetent"): 28.74%, 32.75%, 33.00%, 47.75%, against
  10.05% rule-based.
- Share killed by a set of tests no other mutant shares: about 20% for the round-trip variants,
  38.44% rule-based.
- Faults found when choosing tests by these mutants: about 4.3 times the rule-based rate with 4
  tests, 1.7 times with 30 tests; the round-trip method tops out at about 44.6%, the rule-based at
  about 74.5% with about 60 tests.
- Only 34.2% of methods in the five projects had a docstring.

**Quotes.**

- "By mutating the program’s described semantics (intent), the approach is more likely to produce semantically dissimilar mutants from the original program that simulate faults arising from a developer’s misunderstanding of the intent of the program." (Section I, p. 1)
- "In fact, only 34.2% of the methods in our evaluated real-world projects contain a docstring, as illustrated in Figure 2." (Section I, p. 1)
- "Mutants are generated on the buggy version of the code and we generate 10 mutants per method using GPT-4o-mini as LLM." (Section IV-A, p. 3)
- "Yet, our experiments show the contrary: the highest fault detection rate at a given test budget is achieved without applying intent mutation." (Section VI, p. 5)
- "We suspect that the problem stems from the fact that intent mutation increases the number of incompetent mutants (15% and 4.26% increase, respectively) in comparison to original generated intents." (Section VI, p. 5)
- "These strategies are motivated by the observation that functions in real projects are often tightly integrated and have complex dependencies that the code generation LLM might not be aware of." (Section VI, p. 5)
- "we observe that more than 38% of traditional mutants are unique, compared to 20% of RTM mutants across all its variants." (Section VI, p. 5)
- "While it may produce different mutants, generating multiple implementations per program helps mitigate this threat and ensure the reproducibility of the overall results." (Section VI, Threats to validity, p. 5)

**What it means for Purlin.**

- Test-blind (1): on real project code, deliberately changing the description made things worse,
  not better: more mutants that crash, lower fault detection. Rewriting a whole function from a
  sentence loses the function's ties to the rest of the project. This limits B5's result to small
  self-contained functions. For Purlin it argues for a small edit to the existing code guided by
  the proof, not a rewrite from the proof.
- A crash is a kill that says nothing about the test. Between 29% and 48% of these mutants were
  killed that way. Purlin should not count a planted bug that makes the code fail to import or
  raise at once as a bug the proof's test "caught".
- Several candidates (4): ten per method, yet about four in five were killed by the same tests as
  another. Ten candidates from one description are not ten independent checks.

---

#### B7. SWE-smith: Scaling Data for Software Engineering Agents

- Authors: John Yang, Kilian Lieret, Carlos E. Jimenez, Alexander Wettig, Kabir Khandpur, Yanzhe
  Zhang, Binyuan Hui, Ofir Press, Ludwig Schmidt, Diyi Yang
- Venue and year: arXiv v2, 21 May 2025. A search result lists it as a NeurIPS 2025 poster; the PDF
  does not state a venue.
- Link: https://arxiv.org/pdf/2504.21798
- Text file: `2504.21798.txt` (46 pages; read: main body pages 1 to 10, Appendix B.1 and B.2 on
  pages 21 and 22, Appendix C.1 yield rates on pages 31 to 33, and the difficulty discussion on
  page 37. The other appendices were not read.)

**What it did.** The goal is training data for coding agents, not test assessment, but the
pipeline is bug planting at scale: 128 Python repositories, about 100,000 candidate bugs, each
kept only if it breaks at least one test that was passing. Two of the four strategies use a model
(o3-mini). "LM Modify" shows the model a function and asks for a subtle bug. "LM Rewrite" removes
the function body, shows the file with the signature and docstring, and asks the model to
implement it, with no mention of bugs. Neither prompt contains tests; functions under test
directories are excluded.

**Numbers** (Table 10).

- LM Modify (asked for a bug, sees the code): 31,950 candidates, 17,887 broke a test: 55.98%.
- LM Rewrite (sees signature and docstring, not asked for a bug): 11,908 candidates, 4,173 broke a
  test: 35.04%.
- Rule-based edits: from 1.88% (shuffle the functions in a class) to 49.44% (invert an if).
- Repositories by yield: 10 below 25%, 31 from 25% to 50%, 60 from 50% to 75%, 27 above 75%.
- Difficulty score (1 easy, 9 hard), 1,000 each: LM Modify 3.304, LM Rewrite 5.272.
- Median lines edited: 3 for LM Modify, 24 for LM Rewrite.

**Quotes.**

- "(2) given only the function header and docstring, ask the LM to rewrite it (“LM Rewrite”)." (Section 2.1, p. 3)
- "We apply each candidate patch to the corresponding repository, run the test suite, and only keep patches that break one or more existing, passing tests (referred to as Fail-to-Pass or F2P test(s))." (Section 2.1, p. 3)
- "Yield rates are limited by either lack of test coverage for the change or because the bug candidate did not actually introduce relevant issues." (Section 2.2, p. 4)
- "it is not explicitly asked for bugs. When requested outright (LM Modify), the yield is higher." (Section 2.2, p. 4)
- "While providing a Fail-to-Pass test case leads to more successful expert trajectories, leaking the evaluation criteria causes the model to skip over writing a reproduction script, which accounts for the performance drop." (Section 4.1, p. 7)
- "Notably, it is important to ask the LM to not generate any inline comments denoting the location of a bug; we observe that without explicitly specifying this, model generation outputs tend to have inline comments pointing out the bug." (Appendix B.1, p. 22)
- "We do not experiment extensively with different prompts or generating multiple buggy rewrites per function." (Appendix B.1, p. 22)
- "We generally observe that lower test coverage correlates with a lower yield rate." (Appendix C.1, p. 33)
- "An open-ended prompt like ours does not actually yield high diversity in terms of mistakes created." (Appendix E, p. 37)

**What it means for Purlin.**

- Test-blind (1), base rate: a model asked for a subtle bug with no sight of the tests broke a
  test 56% of the time across 108 repositories. The other 44% are a mix the paper does not
  separate: no test covers the change, or the change did nothing. That mix is the reason one
  planted bug that survives is weak evidence against a test.
- A bug planted from the docstring alone (LM Rewrite) is the nearest analogue of "from the
  requirement". It gave harder, larger changes and broke a test 35% of the time. The prompt did not
  ask for a bug, so this is the rate of honest mistakes, not of planted ones.
- Open-ended "introduce a bug" prompts gave mostly the same kind of mistake: swapped variable
  assignments. A proof-specific instruction is the lever for variety; several candidates from an
  open prompt are not.
- Purlin already strips or forbids comments; the paper confirms models mark their bugs with
  comments unless told not to.
- The fifth quote is about a different stage (the task text shown to a repair agent) but it is one
  of the few measured cases of "the test was shown, behaviour changed": the model that saw the
  failing test stopped doing its own check.

---

#### B8. BugPilot: Complex Bug Generation for Efficient Learning of SWE Skills

- Authors: Atharv Sonwane, Isadora White, Hyunji Lee, Matheus Pereira, Lucas Caccia, Minseon Kim,
  Zhengyan Shi, Chinmay Singh, Alessandro Sordoni, Marc-Alexandre Côté, Xingdi Yuan
- Venue and year: arXiv v2, 28 October 2025. No venue is stated in the PDF.
- Link: https://arxiv.org/pdf/2510.19898
- Text file: `2510.19898.txt` (24 pages; main body pages 1 to 10 read; the appendices with the
  prompts were not read)

**What it did.** Again the goal is training data. An agent (SWE-agent with Claude Sonnet 4) works
inside each SWE-smith repository with a shell, so it can read and run the tests. In one mode it is
told to plant a bug and to confirm that the change breaks existing behaviour. In the other it is
told to add a feature; when that breaks an existing test, the result is kept as a bug. In both
modes a run counts only if at least one test fails afterwards.

**Numbers.**

- Share of bugs a Claude Sonnet 4 agent then fixes: SWE-smith 65.9%, told-to-plant 54.6%,
  feature-side-effect 41.4% (Table 1).
- Size of the bug patch: 1.3 files and 435 tokens when told to plant; 4.2 files and 4,376 tokens
  for feature side effects (Table 2).

**Quotes.**

- "If the tests fail, then we add this to our dataset of bugs. Otherwise, we ask the model to continue changing the code until the tests fail." (Figure 2 caption, p. 2)
- "Current methods for generating synthetic bugs (e.g. SWE-Smith) work by perturbing the code until the tests break." (Section 3.2, p. 4)
- "We instruct the agent to introduce bugs into the repository by enriching its system prompt with guidance on bug integration techniques and verification steps to confirm that changes break existing functionality." (Section 3.2, p. 4)
- "However, this intentional approach produces bugs that lack diversity and are typically far simpler than real-world bugs, as we demonstrate later." (Section 3.2, p. 4)
- "We evaluate whether a run resulted in a bug by running tests after the agent has submitted and making sure at least one test fails (see Figure 4)." (Section 3.2, p. 5)

**What it means for Purlin.**

- This is a fault generator that sees and runs the tests, steered the opposite way from approach
  2: toward a failing test, not past it. The generator keeps changing code until a test fails, so
  every kept bug is one the tests catch. It shows that selection by test outcome fixes what the
  resulting set can tell you. A set built to fail tests says nothing about what tests miss; by the
  same logic a set built to pass a test says nothing about what that test catches.
- Told-to-plant bugs were simple and alike. The paper's fix, bugs as side effects of a feature, is
  out of scope for an audit that must make one small change per proof.

---

#### B9. Non-Determinism of "Deterministic" LLM Settings

- Authors: Berk Atil, Sarp Aykent, Alexa Chittams, Lisheng Fu, Rebecca J. Passonneau, Evan
  Radcliffe, Guru Rajan Rajagopal, Adam Sloan, Tomasz Tudrej, Ferhan Ture, Zhe Wu, Lixinyu Xu, Breck
  Baldwin
- Venue and year: arXiv v5, 2 April 2025 ("Preprint. Under review.")
- Link: https://arxiv.org/pdf/2408.04667
- Text file: `2408.04667.txt` (15 pages; main body pages 1 to 9 read; appendix not read)

**What it did.** Five models answered eight multiple-choice tasks ten times each at temperature 0,
top-p 1 and a fixed seed. The authors counted how often all ten raw replies, and all ten parsed
answers, were identical. The tasks are question answering, not code.

**Numbers.**

- Accuracy differed by up to 15 points between runs of the same model on the same task.
- All ten raw replies identical (few-shot): from 0% to 86% of questions depending on model and
  task; for GPT-4o, 0% on three of eight tasks.
- All ten parsed answers identical: 50% to 99.6% for GPT-4o.
- A locally hosted Llama3-8b with no serving optimisations was deterministic.

**Quotes.**

- "We see accuracy variations up to 15% across naturally occurring runs with a gap of best possible performance to worst possible performance up to 70%." (Abstract, p. 1)
- "These correlations mean that as an LLM’s output length increases, the instability of the output increases, resulting in more diverse natural language responses as well as the actual multiple choice answer prediction." (Section 7.2, p. 7)
- "In order to support this line of reasoning, we ran Llama3-8b on our local GPUs without any optimizations, yielding deterministic results." (Section 8.1, p. 8)
- "Furthermore, an LLM rarely produces the same response ten times given the same input; however, the parsed answer is often more stable." (Section 9, p. 9)

**What it means for Purlin.**

- A planted bug is a long free-form output, the kind this paper finds least repeatable. Together
  with B4 it says: on a hosted model, temperature 0 does not make "the bug for this proof" a fixed
  thing. Evidence that records which bug was planted is needed for any approach; approach 4 turns
  the variation into coverage instead of noise.
- Longer outputs were less stable. Approach 3 and approach 4 in one request make the reply longer.
  The paper measured short answers, so this is a direction, not a number.

---

### State of the evidence, by question

#### Question 1. Detecting or avoiding equivalent mutants cheaply with an LLM

There is evidence on detection by asking, and it is negative for the models tested. Asking GPT-4
"are these two semantically equal" gave a macro F1 of about 54% on 1,650 labelled Java pairs (B2);
the methods that reached 82% to 87% were fine-tuned on labelled pairs. Letting gpt-4o-mini declare
a mutant equivalent during test writing was right for about 6% of its declarations (B3). There is
evidence on how common the problem is with LLM-made mutants: 3% to 6% of all compilable mutants for
strong models (B1), and 20% of survivors (B4), against 1% to 2% and 5% for rule-based tools. The
one industrial answer found is to avoid the question: ACH only reports a mutant together with a
test that kills it (A4), which Purlin cannot copy because Purlin judges an existing test. There is
no evidence found for current reasoning models, none for chain-of-thought prompting on this task
(B2 lists it as future work), and none at all for the question Purlin has, which is whether a
change violates a written requirement as opposed to whether it differs from the original code. The
ACH equivalence detector and the 2026 multi-language extension of B2 were not read here.

#### Question 2. Which prompt context changes the mutants

There is one controlled comparison, B1 Section 4.1, on two models and 306 bugs: target only, method
only, method plus its unit tests, whole file, and with or without real-bug examples. Adding the
unit tests slightly lowered similarity to real bugs and doubled the tokens; the whole file did
worst; removing the examples cost a little realism and raised the compile rate; none of the
differences were statistically significant. B4 varied instructions, not context: dropping the
instructions or the system prompt changed little, and a bare prompt cut the number of mutants by
four fifths. Different sets of real-bug examples made no significant difference (B1). There is no
study found that puts a written specification or docstring into a code-mutating prompt and compares
it with the same prompt without one. B5 and B6 change the specification instead of the code and so
do not isolate the effect of adding it as context. The SMART paper (retrieved real bugs as examples)
was found and not read.

#### Question 3. How many candidates, variation between runs, several per request

There is evidence that the same request gives different mutants on different runs: at temperature 0,
between 28% and 59% of mutants recurred across five runs for three of five models, and 89% to 100%
for the other two; at temperature 1 almost none recurred (B4). Hosted models are not deterministic
at temperature 0 on other tasks either (B9). There is evidence that one request can carry several
candidates: three per request gave 2.1% duplicates (B4); a whole method's worth in one JSON reply
gave 7% to 8% exact duplicates with strong models and 37% with a small one (B1); and repeating one
prompt for tests gave near-identical output at temperature 0 (A3). There is evidence that several
candidates from one prompt overlap in what they test: about four in five round-trip mutants were
killed by the same tests as another (B6). B4 reports the aggregate mutation score as stable across
runs despite different mutants. There is no evidence found on the question Purlin needs answered:
how many planted bugs per target are needed before the verdict on that one target stops changing.
Every stability figure found is for a score over hundreds of mutants, not for one test judged by
one to five mutants.

#### Question 4. Planting a fault from a written requirement

This is the thinnest area. Two 2026 preprints from one group do it (B5, B6), by changing a word of
the description and regenerating the whole function. On small self-contained functions with
hundreds of tests the resulting faults were valid 91% of the time and complemented code-level
faults (B5). On real project methods the same idea raised the share of mutants that crash and
lowered fault detection (B6). SWE-smith's rewrite-from-docstring strategy is a third data point: no
bug requested, 35% of rewrites broke a test (B7). Harman, O'Hearn and Sengupta argue that intended
behaviour should be taken from non-executable text and the code treated as suspect (A4), without
an experiment. None of these checks that the planted change violates the original requirement, and
none classifies the survivors. No paper was found that gives a model a requirement sentence and
existing code and asks for a small edit that breaks that sentence, which is what Purlin does. No
work on formal specification mutation was read; one tool for Dafny specifications was found and
not read.

#### Question 5. Bias when the fault generator sees the tests it is judged against

Apart from the two papers assigned elsewhere (arXiv 2609.35841 and 2602.08146), no study of this
was found. What exists is indirect. B1 put the unit tests in the prompt with no instruction about
them and saw no significant change, with the kill rate moving in opposite directions on its two
models. B8 and B7 select bugs by test outcome in the other direction (keep only what fails a test),
which shows the mechanism, a set selected by test outcome cannot measure those tests, without
measuring the evading case. B7's side result shows a model changing its behaviour once it has seen
the test it will be judged by. A1 shows a model's view of what is correct shifting toward buggy
code it was shown. There is no measurement found of how often a model told to get past a given test
produces a change that makes no real difference, beyond whatever the two assigned papers report.

---

### What this adds up to for the four approaches

1. **Test-blind.** Best supported. A model asked for a bug without seeing tests breaks a test about
   56% of the time on real repositories (B7); faults drawn from the requirement text are valid and
   different in kind from code-level faults on small functions (B5); adding the tests to the prompt
   without instructions buys nothing (B1). Its weakness is the survivor: 3% to 6% of LLM mutants,
   and about 20% of surviving ones, change nothing (B1, B4), and a single blind bug is not
   repeatable across runs (B4, B9).
2. **Test-aware with a guard.** Least supported by what was read here. Its value depends on the
   guard, and the two measured ways of having a model vouch for a change are poor: F1 near 54% for
   "are these equal" (B2) and about 6% precision for "this one is equivalent" (B3). A repeatable
   model verdict is not a valid one (A2). A guard that is itself a run is the only kind this
   literature supports.
3. **Both in one request.** No study. The nearest result is that tests in context without
   instruction change little (B1). Longer replies are less stable (B9), and order effects are
   measured for verdicts (A2), not for generation.
4. **Several candidates.** Supported as a mechanism: one request can return three or more with 2%
   to 8% duplicates (B1, B4), and later candidates tend to be larger changes (B4). The limit is
   overlap: candidates from one prompt often test the same thing (B6, B7 Appendix E, A3). No paper
   says how many are enough for one target.

---

### Found, not read

These came up in search. Nothing from them is quoted or relied on above.

- Shu and others, "Large Language Models for Multi-Lingual Equivalent Mutant Detection: An Extended
  Empirical Study", arXiv 2607.00511 (extends B2 to C). https://arxiv.org/pdf/2607.00511
- Wang and others, "Boosting LLMs for Mutation Generation" (SMART: retrieved real bugs and
  fine-tuning), arXiv 2603.24560. https://arxiv.org/pdf/2603.24560
- Ibrahimzada and others, "Challenging Bug Prediction and Repair Models with Synthetic Bugs"
  (BugFarm), arXiv 2310.02407. https://arxiv.org/pdf/2310.02407
- "Mutation-Guided Unit Test Generation with a Large Language Model" (MutGen), arXiv 2506.02954.
  https://arxiv.org/pdf/2506.02954
- Sun and others, "SWE-Mutation: Can LLMs Generate Reliable Test Suites in Software Engineering?",
  Findings of ACL 2026. https://preview.aclanthology.org/ingest-acl/2026.findings-acl.1976/ . An
  agent writes mutated solutions meant to get past test suites; likely relevant to question 5.
- "CodeHacker: Automated Test Case Generation for Detecting Vulnerabilities in Competitive
  Programming Solutions", arXiv 2602.20213. https://arxiv.org/pdf/2602.20213
- Hu and others, "Evaluation and Improvement of Fault Detection for Large Language Models", arXiv
  2404.14419. https://arxiv.org/pdf/2404.14419
- Li and others, "Mutation-based Consistency Testing for Evaluating the Code Understanding
  Capability of LLMs", arXiv 2401.05940. https://arxiv.org/pdf/2401.05940
- "Do Coverage and Mutation Scores of LLM-Generated Test Suites Correlate with Their Effectiveness?
  (Replicability Study)", arXiv 2607.22880. https://arxiv.org/pdf/2607.22880
- "Equivalent Mutants in the Wild: Identifying and Efficiently Suppressing Equivalent Mutants",
  ISSTA 2024. https://2024.issta.org/details/issta-2024-papers/53/
- "MutDafny: A Mutation-Based Approach to Assess Dafny Specifications", arXiv 2511.15403.
  https://arxiv.org/abs/2511.15403
- Degiovanni and Papadakis, "µBERT: Mutation Testing using Pre-Trained Language Models", arXiv
  2203.03289; and "Efficient Mutation Testing via Pre-Trained Language Models", arXiv 2301.03543.
- Liu and others, "Is Your Code Generated by ChatGPT Really Correct?" (EvalPlus), arXiv 2305.01210.
- "Beyond Fixed Fault Models: Comparing LLM-Based and Rule-Based Fault Injection in OpenStack",
  arXiv 2609.08681. https://arxiv.org/abs/2609.08681
- "Neuro-Formal Verification: Agentic Language-Agnostic Formal Program Reasoning", arXiv
  2608.21516. https://arxiv.org/html/2608.21516
- "Kumo": a search result describes it as an LLM-based mutation tool for Java with a mutant
  dataset. No paper under that name was located; the link returned was the LLMorpheus journal
  paper (B4).
- Not read by assignment: arXiv 2609.35841 (test-aware mutant generation) and arXiv 2602.08146
  (Test vs Mutant).
