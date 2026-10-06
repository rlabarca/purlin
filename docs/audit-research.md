# The research behind the audit

This page gives the evidence for the design of [the audit](audit.md): the choice that was
made, what each paper found in its own words, a trial on Purlin's own case, and what Purlin
does not claim. Every paper was read in full, and every quote is word for word.

## Purlin measures a test with one aimed bug per proof

| How to judge a test | What it takes | What it shows |
|---|---|---|
| An AI reads it | Fast | An opinion |
| Plant bugs everywhere | Minutes to hours, and a tool per language | Measured, across all the code |
| **Spot tests, then one planted bug per proof** | **No AI for the spot tests, then a small bug from the AI and one test run for each changed proof** | **Measured, aimed at what the proof says and at what its test misses** |

Purlin takes the last row.

## The choice is what the AI sees when it writes the bug

A planted bug is chosen by something. How it is chosen decides what a caught bug means. The
research holds two deliberate designs.

- **The AI never sees the test.** Classic bug-planting tools work this way, and so does
  [Tip, Bell and Schäfer's LLMorpheus](https://arxiv.org/pdf/2404.09952): the request holds the
  code, and a separate tool runs the tests.
- **The AI sees the test and is told to get past it.**
  [Kiele et al., ESEM 2026](https://arxiv.org/pdf/2609.35841) give the model the task, the code
  and the tests, and instruct it that the bug "MUST pass all the provided Base Tests".

No paper found an unbiased way. The two designs lean in opposite directions.

**A bug chosen without the test is usually caught, and a caught one says little.**

- At Google, where bugs are planted without regard to the tests: "Overall, 87.5% of all
  generated mutants are killed by the initial test suite."
  ([Petrović et al., TSE 2021](https://arxiv.org/pdf/2102.11378), section 5.3)
- Most planted bugs are caught whenever some other one is: "We found that fewer than 5% of all
  mutants are subsuming (and not subsumed themselves). The remaining 95% of mutants are subsumed
  by some other mutants."
  ([Papadakis et al., ISSTA 2016](https://orbilu.uni.lu/bitstream/10993/28927/1/ISSTA16.pdf),
  section 1)
- With an AI writing the bug and no test in view, tests known to be thin still caught 68% to 87%
  of the bugs on one benchmark and 54% to 78% on the other. "This confirms that without
  visibility of the base tests, LLMs introduce changes that existing assertions already cover."
  ([Kiele et al.](https://arxiv.org/pdf/2609.35841), section 4)

**A bug aimed past the test finds more gaps, and some of what survives is no real bug.**

- "Test-aware prompting yields verified fault rates of 87.7% (HumanEval) and 79.1% (MBPP),
  meaning these mutants pass all base tests but are caught by the oracle. This vastly outperforms
  the matched test-blind prompting (which yields only 12.2% and 23.0%, respectively) and the
  traditional rule-based tool mutmut (4.4% and 5.7%)."
  ([Kiele et al.](https://arxiv.org/pdf/2609.35841), abstract.) "Verified" means a far larger
  hidden set of tests caught the bug. One request, one bug, five models, 542 small Python
  problems.
- The same paper read every bug that got past the hidden tests too: "Out of the 65 Undetected
  mutants, we found that only 9 (∼13.8%) are equivalent mutants and a vast majority (49/65,
  ∼75.4%) present serious edge-case bugs". The other 7 were faults only where the task was
  loosely stated.
- Bugs an AI writes change nothing more often than a tool's do. Of surviving bugs read by hand:
  "Of the 517 mutants under consideration, the majority 403 (78%) are "not equivalent", 105 (20%)
  are "equivalent", and remaining 9 (2%) are classified as "unknown"."
  ([LLMorpheus](https://arxiv.org/pdf/2404.09952), section 4.4.) For the rule-based tool beside
  it, 5 of 430.
- At Meta: "Although the language model approach generates fewer and more specific mutants than
  rule-based approaches, we found that it also generates more equivalent mutants."
  ([Foster et al., FSE 2025](https://arxiv.org/pdf/2501.12862), section 3.) Of 381 bugs read by
  hand, 137 (36%) changed nothing.
- Google's warning about choosing bugs for survival: "Surviving the initial test suite is a
  precondition for surfacing a mutant, but survivability alone is not a good measure of mutant
  productivity." ([Petrović et al.](https://arxiv.org/pdf/2102.11378), section 5.1)

**Showing the test and saying nothing about it is the one form the evidence is against.** A
study of prompts for writing bugs compared the code alone with the code and its unit tests:
"P2, which adds unit tests to the context compared with P3, shows slightly reduced
effectiveness—suggesting that including unit tests does not help the model generate better
mutants." ([Wang et al., TOSEM 2025](https://arxiv.org/pdf/2406.09843), section 4.1.1.) The
request with the tests was about twice the size, and no difference was statistically
significant. Kiele et al. on that result: "We hypothesize that this performance drop
occurs because LLMut only appends the tests as passive context."

## Purlin shows the AI the test, and the test run decides

**The AI is shown the test and told to aim past it.** A gap in a test is what the audit is
for, and the aimed request finds the most gaps in one request. The request never leaves the
test in view without an instruction about it.

**The bug must break the proof's own case.** The papers' guard against a bug that is no bug is
a hidden set of tests. A project has none. It has the proof: one case and the result that
settles it, written by a person. The request holds the bug to that case, as Kiele et al.'s
prompt holds it to the task: "The bug MUST manifest on VALID inputs that adhere to the problem
description." The AI writes the case, the result the proof names and the result the changed
code gives.

**The AI's word is shown, never trusted.** A model asked whether a change makes a difference
is often wrong.

- Asked directly whether two versions behave the same, GPT-4 scored 53.61% (F1) on 1,650
  labelled pairs. "LLMs based solely on prompting strategies cannot achieve comparable
  performance." ([Tian et al., ISSTA 2024](https://arxiv.org/pdf/2408.01760), RQ2)
- A model allowed to call a planted bug harmless used that freely: "scientific approaches tend
  to label more mutants as equivalent if no test is found for them, but most of these mutants
  are not actually equivalent."
  ([Straubinger et al., 2025](https://arxiv.org/pdf/2503.08182), section I.) By hand, about 6%
  of those calls were right.
- A model's verdict can repeat and still be wrong: "High stability with high bias is a failure
  mode, not a strength."
  ([Norman, Rivera and Hughes, 2026](https://arxiv.org/pdf/2606.19544), section 5.3.) Their
  judges gave the same verdict on a rerun (0.943) and agreed only moderately with people (0.376
  to 0.511 once chance is removed).

So Purlin prints the AI's line under a surviving bug as the AI's claim, and the verdict comes
from the test run alone.

**A test run settles a surviving bug.** Kiele et al. say what a survivor is outside a
benchmark: "In real workflows, these mutants should be interpreted primarily as concrete
suggestions for stronger tests and developer inspection rather than automatically validated
defects." Google gives each one a "Not useful" button. In Purlin a weak rule is listed and
blocks nothing. `purlin:build` writes the check the proof names, and the bug is planted again.
The check fails: the finding held. The check passes: the bug did not break what the proof says.
A finding cannot be cleared without either a stronger test or a recorded judgment that the
test was already sound: a settle is refused for a test that is as it was when the bug got
past it, and an audit after a code change plants the same bug again before any new one. Where
`purlin:build` read the test against the proof and left it alone, it says so with `--sound`,
and the evidence records that the test was not changed. Purlin records that judgment and does
not check it.

**The guards that are code.** A change that leaves the file as it was, touches only a comment,
changes a test file, or cannot be applied exactly once is not planted. At Meta, 61% of the
bugs that changed nothing differed only by a comment. Dropping those, and the ones identical
to the original, took the share of harmless bugs found from 0.47 to 0.96
([Foster et al.](https://arxiv.org/pdf/2501.12862), section 5.3). A test that ends in an error
with the bug in place is not a caught bug.

**One bug per proof.** Google plants at most one per changed line that a test covers and shows
a few survivors ([Petrović et al.](https://arxiv.org/pdf/2102.11378)). Meta keeps few and specific ones
([Foster et al.](https://arxiv.org/pdf/2501.12862)). One request can ask for more: "using
onemutation dramatically reduces the number of mutants from 6,712 to 2,333, demonstrating that
it is helpful to request multiple suggestions" ([LLMorpheus](https://arxiv.org/pdf/2404.09952),
section 4.6). No paper says how many bugs make one test's result stable. Purlin aims one bug
and keeps its result.

**A kept result.** Which bug an AI writes is not repeatable. On three of five models, 28% to
59% of bugs came back in all five runs of the same request at the most repeatable setting
([LLMorpheus](https://arxiv.org/pdf/2404.09952), section 4.7; see also
[Atil et al., 2025](https://arxiv.org/pdf/2408.04667)). Purlin keeps a proof's result until its
test or code changes. A bug that survived is planted again after a code change, so a finding
is not replaced by a different bug the test happens to catch.

## In a trial, the aimed request found the subtle weak test and flagged the most sound ones

No paper studies what Purlin does: a written requirement, existing code, one small change, and
one existing test judged by it. So the candidate requests were tried on a small sample
project: a lab's sample intake in Python, with 8 rules, 12 proofs and 12 tests. 3 of the tests
were written weak on purpose and 9 sound.

- **Shown, not told**: the test is in the request and nothing is said about it.
- **Hidden**: no test in the request.
- **Aimed**: the test is in the request, the bug must get past it, and the AI names the case
  it breaks.

Each request ran twice with one model, `claude-opus-5-5`, started as the audit starts it. Each
bug was planted in a copy and only its proof's test ran.

| Per run of 12 proofs | Shown, not told | Hidden | Aimed |
|---|---|---|---|
| Of the 3 weak tests, found (run 1, run 2) | 3, 3 | 3, 3 | 3, 3 |
| Of the 9 sound tests, a bug survived (run 1, run 2) | 0, 0 | 1, 1 | 1, 4 |

What the numbers hide:

- **The subtle weak test.** One weak test takes its expected value from a helper in the code
  under test. Only a bug in that helper gets past it. The aimed request planted that bug both
  times. A plain bug asked for beside it missed once in two runs, and an earlier measurement
  with the shown-not-told request missed it too.
- **The hidden request's survivor** broke the rule somewhere the proof does not go. The proof's
  own case still held, so the test was right to pass.
- **The aimed request's survivors on sound tests** were one idea. The proofs say a sample "is
  stored" with a status. The tests read the status from the record the code hands back. The bug
  hands back the right record and stores nothing. By the letter of the proof the test does not
  check storage. Each was plain from the AI's line, such as "the changed code returns a record
  with status `accepted` but never stores it". Kiele et al. count the same kind apart, as faults
  under a loosely stated task.
- **Which sound tests were flagged changed between the two runs.**

The trial is 12 proofs, one project, one language, one model and two runs. It supports this
much: the aimed request is the one that reaches a subtle weak test every time, and it is the
one that raises the most flags on sound tests.

## Why plant a bug: it measures the test, and an opinion does not

**A test suite that catches more planted bugs tends to catch more real ones.** "Mutant
detection is positively correlated with real fault detection, independently of code coverage."
([Just et al., FSE 2014](https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf),
section 3.3.) Two limits:

- The link is weaker once the number of tests is held equal: "when controlling the test suite
  size (decouple mutation score from test suite size) all correlations become weak or moderate
  in the best case."
  ([Papadakis et al., ICSE 2018](https://coinse.github.io/publications/pdfs/Papadakis2018hi.pdf),
  section 7)
- Some real faults have no planted counterpart: "17% of real faults, mostly involving
  algorithmic changes or code deletion, are not coupled to any mutants."
  ([Just et al.](https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf),
  section 3.2)

Both findings are about whole suites and many bugs. No paper shows that a test which catches
one planted bug catches real ones.

**Code coverage is a weak guide to how many planted bugs the tests catch.** "We found that
there is a low to moderate correlation between coverage and effectiveness when the number of
test cases in the suite is controlled for."
([Inozemtseva and Holmes, ICSE 2014](https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf),
abstract.) They measured planted bugs, not real faults.

**AI-written bugs look more like real ones than tool-made ones.** Measured against 851 real
bugs, an AI's planted bugs stood for 76.47% of them and a rule tool's for 44.15%
([Wang et al.](https://arxiv.org/pdf/2406.09843), abstract). An AI also changes more than a
rule can: a wrong function called, a wrong variable read
([LLMorpheus](https://arxiv.org/pdf/2404.09952), section 2).

**AI-written tests often check what the code does, not what was asked.** A model leans on the
code as written when it decides what a test should expect: "LLM's test oracle classification
accuracy considerably drops in the presence of buggy code".
([Konstantinou, Degiovanni and Papadakis, 2024](https://arxiv.org/pdf/2410.21136), section
IV-A.) Shown buggy code, the model more often rejects the right expected answer, by 8 to 9
points; one model was tested. Model-written tests also often check nothing at all
([Siddiq et al., EASE 2024](https://arxiv.org/pdf/2305.00418)) and lean on mocks
([an empirical study of coding agents, 2026](https://arxiv.org/pdf/2602.00409)). The spot tests
catch these. The expected answer comes from the proof, which a person wrote.

**An AI's opinion alone is not enough.** Asking a model whether a test looks good is the
weakest check, because a model can give the same verdict every time and still be wrong
([Norman, Rivera and Hughes, 2026](https://arxiv.org/pdf/2606.19544)). At Meta, AI-written
tests ship only after a measured check: the test builds, passes five times and adds coverage,
and then a person reviews it
([Alshahwan et al., FSE 2024](https://arxiv.org/pdf/2402.09171)). In Purlin the AI plants the
bug. The test run decides.

## What Purlin does not claim

- **That the choice of bug is unbiased.** An aimed bug is chosen against the test. Its
  survival rate overstates how weak a project's tests are, and a share of rules found `strong`
  is not a score to compare two projects by. Any share of caught bugs carries this:
  "if the developers frequently test for off-by-one errors, mutants that simulate this error
  will be detected more often"
  ([Inozemtseva and Holmes](https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf),
  section 6.1).
- **That a surviving bug is a real fault.** It is a case to settle with a test run. In the
  papers, 14% to 36% of an AI's surviving bugs changed nothing; in the trial, every doubtful
  survivor was a strict reading of the proof.
- **That a caught bug means the test catches real faults.** It means the test noticed this
  change to this case.
- **That the research covers Purlin's case.** Kiele et al. tested small problems with few
  tests: "this study does not establish exactly how performance changes as the initial suite
  becomes stronger or weaker." The trial above is the only measurement of a bug written from a
  proof against one existing test, and it is small.

## Sources

Each paper is linked. What the audit does, and what it found on Purlin's own tests, is on
[the audit page](audit.md). The six checks are in
[the heuristic spot tests reference](../references/review_criteria.md#heuristic-spot-tests).
What a settle does is in
[Settling a finding](../references/review_criteria.md#settling-a-finding).

**How the bug is chosen**

- Kiele, Saad, Wang, Drew and Ebrahimi Kahou, [Beyond Rule-Based Mutation Testing: Test-Aware Mutant Generation Using Large Language Models](https://arxiv.org/pdf/2609.35841), ESEM 2026
- Wang, Chen, Deng, Lin, Harman, Papadakis and Zhang, [A Comprehensive Study on Large Language Models for Mutation Testing](https://arxiv.org/pdf/2406.09843), ACM TOSEM 2025
- Tip, Bell and Schäfer, [LLMorpheus: Mutation Testing using Large Language Models](https://arxiv.org/pdf/2404.09952), IEEE TSE 2025
- Foster et al., [Mutation-Guided LLM-based Test Generation at Meta](https://arxiv.org/pdf/2501.12862), FSE 2025
- Petrović, Ivanković, Fraser and Just, [Practical Mutation Testing at Scale: A view from Google](https://arxiv.org/pdf/2102.11378), TSE 2021
- Papadakis, Henard, Harman, Jia and Le Traon, [Threats to the Validity of Mutation-Based Test Assessment](https://orbilu.uni.lu/bitstream/10993/28927/1/ISSTA16.pdf), ISSTA 2016
- Tian, Shu, Wang, Cao, Kamei and Chen, [Large Language Models for Equivalent Mutant Detection: How Far Are We?](https://arxiv.org/pdf/2408.01760), ISSTA 2024
- Straubinger, Kreis, Lukasczyk and Fraser, [Mutation Testing via Iterative Large Language Model-Driven Scientific Debugging](https://arxiv.org/pdf/2503.08182), 2025
- Atil et al., [Non-Determinism of "Deterministic" LLM Settings](https://arxiv.org/pdf/2408.04667), 2025

**The audit as a whole**

- Just et al., [Are Mutants a Valid Substitute for Real Faults in Software Testing?](https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf), FSE 2014
- Papadakis, Shin, Yoo and Bae, [Are Mutation Scores Correlated with Real Fault Detection?](https://coinse.github.io/publications/pdfs/Papadakis2018hi.pdf), ICSE 2018
- Inozemtseva and Holmes, [Coverage Is Not Strongly Correlated with Test Suite Effectiveness](https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf), ICSE 2014
- Konstantinou, Degiovanni and Papadakis, [Do LLMs generate test oracles that capture the actual or the expected program behaviour?](https://arxiv.org/pdf/2410.21136), 2024
- Siddiq et al., [Using Large Language Models to Generate JUnit Tests: An Empirical Study](https://arxiv.org/pdf/2305.00418), EASE 2024
- [Are Coding Agents Generating Over-Mocked Tests? An Empirical Study](https://arxiv.org/pdf/2602.00409), 2026
- Norman, Rivera and Hughes, [Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models](https://arxiv.org/pdf/2606.19544), 2026
- Alshahwan et al., [Automated Unit Test Improvement using Large Language Models at Meta](https://arxiv.org/pdf/2402.09171), FSE 2024
- Schäfer, Nadi, Eghbali and Tip, [An Empirical Evaluation of Using Large Language Models for Automated Unit Test Generation](https://arxiv.org/pdf/2302.06527), IEEE TSE 2024

**The heuristic spot tests**

- Peruma et al., [tsDetect: An Open Source Test Smells Detection Tool](https://2020.esec-fse.org/details/esecfse-2020-tool-demos/4/tsDetect-An-Open-Source-Test-Smells-Detection-Tool), ESEC/FSE 2020
- Schuler and Zeller, [Assessing Oracle Quality with Checked Coverage](https://www.st.cs.uni-saarland.de/publications/files/schuler-icst-2011.pdf), ICST 2011
- Barr, Harman, McMinn, Shahbaz and Yoo, [The Oracle Problem in Software Testing: A Survey](https://discovery-pp.ucl.ac.uk/id/eprint/1471263/1/06963470.pdf), IEEE TSE 2015
- Spadini, Aniche, Bruntink and Bacchelli, [To Mock or Not To Mock? An Empirical Study on Mocking Practices](https://repository.tudelft.nl/file/File_dcb7ec41-615b-457c-9b5f-e6c6de2dea7e?preview=1), MSR 2017
- Panichella, Panichella, Fraser, Sawant and Hellendoorn, [Test Smells 20 Years Later: Detectability, Validity, and Reliability](https://pure.tudelft.nl/ws/portalfiles/portal/137994226/s10664_022_10207_5.pdf), EMSE 2022
