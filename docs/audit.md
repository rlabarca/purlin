# The audit: would your tests catch a bug?

A passing test is not proof that it checks anything. The audit tries to make each test fail.

## How it works

**1. Heuristic spot tests.** Purlin flags tests that check nothing, check the code against
itself, or never check the result the proof expects. It reads the tests as text. No AI is asked
and no test runs, so this step is free. The six checks are in
[the heuristic spot tests reference](../references/review_criteria.md#heuristic-spot-tests).

**2. Plant one bug.** For each proof, an AI puts one small bug in a throwaway copy of your code,
such as a sample age off by one hour. The bug is aimed at what the proof says. The AI is asked
once for each rule.

**3. Run that proof's test.** The test fails: the bug was caught. The test still passes: the
rule is `weak`, and you see the bug it missed:

```
PROOF-1: the test still passes when src/age.py:12 reads "return minutes + 60"
```

A rule reads `strong` when the spot tests found nothing and a planted bug was caught. Where
no bug could be planted, the rule reads `spot-checked`, and the audit says why:

```
The spot tests found nothing. No bug was planted: PROOF-3 needs Windows, and this machine is macOS.
```

One caught bug makes a rule `strong`. Each of its proofs with no caught bug is named under it,
with the reason.

**4. `purlin:audit`.** Run it whenever you like. Or tell the agent:

> Build and audit until 80% of rules are strong.

The agent strengthens the weak tests and audits again until 80% of rules are strong. Every audit
ends on that share:

```
The audit found 42 of 50 rules strong (84%): 42 strong, 8 weak.
```

## What you can count on

- **Your code is never changed.** Every bug is planted in a copy, and the copy is thrown away.
- **Nothing waits on it.** A weak rule is work to do, listed as `to strengthen`. The tests still
  read `met`, and a sign-off goes ahead.
- **`strong` means a bug was caught.** If the AI cannot be reached, a rule the spot tests flag
  is still `weak`. Every other rule reads `spot-checked`, with the reason, and the next
  `purlin:audit` reads it again.
- **A result goes out of date.** When a rule, its proof, its test or the code it covers changes,
  the rule reads `out of date`, with its last result and date, until the audit reads it again.
- **The AI is given no tools.** It is started with no tools, no plugins and none of your
  settings, in an empty folder. It can read and change nothing.
- **It stays fast.** Only proofs whose test or code changed since the last audit get a new bug.
- **Nothing to install.** Any test Purlin can run, it can audit. No extra tool per language.
- **What it found is kept.** Each finding and each planted bug goes into the evidence. The
  signer can read the findings at sign-off.

## What it does not do

- It does not prove your tests catch every bug. It tests what each proof says, one bug at a time.
- It reads only rules whose tests pass. A failing test is fixed first.
- It plants no bug for an anchor's rule, so an anchor's rule reads `spot-checked`, never
  `strong`.
- It plants no bug for a proof tagged for another system. The test cannot show it on this
  machine.
- A test that is skipped, cannot be collected, runs past its limit or ends in an error with the
  bug in place decides nothing. Only a test that ran and failed caught the bug.
- A rule with no proof has nothing to plant a bug against.

## Why this works

**AI-written tests often check what the code does, not what was asked.** A model tends to take
a test's expected answer from the code as written. A bug in the code is then copied into the test
([Konstantinou, Degiovanni and Papadakis, 2024](https://arxiv.org/pdf/2410.21136)). Model-written
tests also often check nothing at all
([Siddiq et al., EASE 2024](https://arxiv.org/pdf/2305.00418)) and lean on mocks
([an empirical study of coding agents, 2026](https://arxiv.org/pdf/2602.00409)). The spot tests
catch these. The expected answer comes from the proof, which a person wrote.

**Planting bugs is the most reliable test of a test.** Tests that catch small planted bugs tend
to catch real ones
([Just et al., FSE 2014](https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf)).
Code coverage, how much code the tests run, does not predict that
([Inozemtseva and Holmes, ICSE 2014](https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf)).

**Big companies plant a few targeted bugs, not thousands.** Google plants bugs only in changed
code and shows developers the few their tests missed
([Petrović et al., TSE 2021](https://arxiv.org/pdf/2102.11378)). Meta has a model write a few
targeted ones ([Foster et al., FSE 2025](https://arxiv.org/pdf/2501.12862)). AI-written bugs look
more like real ones than tool-made ones
([Tip et al., LLMorpheus](https://arxiv.org/pdf/2404.09952)). Purlin follows both: one bug per
proof.

**An AI's opinion alone is not enough.** Asking a model whether a test looks good is the weakest
check, because models judge inconsistently
([a large-scale evaluation of model judges, 2026](https://arxiv.org/pdf/2606.19544)). At Meta,
AI-written tests ship only after a measured check
([Alshahwan et al., FSE 2024](https://arxiv.org/pdf/2402.09171)). In Purlin the AI plants the
bug. The test run decides.

## Fast enough to run every day

| How to judge a test | Cost | What it shows |
|---|---|---|
| An AI reads it | Fast | An opinion |
| Plant bugs everywhere | Minutes to hours, and a tool per language | Objective, across all the code |
| **Spot tests, then one planted bug per proof** | **Free, then one AI call per changed rule and one test run per changed proof** | **Objective, aimed at what the proof says** |

Purlin takes the last row. The audit prints how many AI calls it will make before it starts, and
what the run cost when it ends.

## Sources

Each paper is linked. The six checks are in
[the heuristic spot tests reference](../references/review_criteria.md#heuristic-spot-tests).

**The audit as a whole**

- Konstantinou, Degiovanni and Papadakis, [Do LLMs generate test oracles that capture the actual or the expected program behaviour?](https://arxiv.org/pdf/2410.21136), 2024
- Siddiq et al., [Using Large Language Models to Generate JUnit Tests: An Empirical Study](https://arxiv.org/pdf/2305.00418), EASE 2024
- [Are Coding Agents Generating Over-Mocked Tests? An Empirical Study](https://arxiv.org/pdf/2602.00409), 2026
- Just et al., [Are Mutants a Valid Substitute for Real Faults in Software Testing?](https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf), FSE 2014
- Inozemtseva and Holmes, [Coverage Is Not Strongly Correlated with Test Suite Effectiveness](https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf), ICSE 2014
- Petrović, Ivanković, Fraser and Just, [Practical Mutation Testing at Scale: A view from Google](https://arxiv.org/pdf/2102.11378), TSE 2021
- Foster et al., [Mutation-Guided LLM-based Test Generation at Meta](https://arxiv.org/pdf/2501.12862), FSE 2025
- Tip, Bell and Schäfer, [LLMorpheus: Mutation Testing using Large Language Models](https://arxiv.org/pdf/2404.09952)
- [Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models](https://arxiv.org/pdf/2606.19544), 2026
- Alshahwan et al., [Automated Unit Test Improvement using Large Language Models at Meta](https://arxiv.org/pdf/2402.09171), FSE 2024
- Schäfer, Nadi, Eghbali and Tip, [An Empirical Evaluation of Using Large Language Models for Automated Unit Test Generation](https://arxiv.org/pdf/2302.06527), IEEE TSE 2024

**The heuristic spot tests**

- Peruma et al., [tsDetect: An Open Source Test Smells Detection Tool](https://2020.esec-fse.org/details/esecfse-2020-tool-demos/4/tsDetect-An-Open-Source-Test-Smells-Detection-Tool), ESEC/FSE 2020
- Schuler and Zeller, [Assessing Oracle Quality with Checked Coverage](https://www.st.cs.uni-saarland.de/publications/files/schuler-icst-2011.pdf), ICST 2011
- Barr, Harman, McMinn, Shahbaz and Yoo, [The Oracle Problem in Software Testing: A Survey](https://discovery-pp.ucl.ac.uk/id/eprint/1471263/1/06963470.pdf), IEEE TSE 2015
- Spadini, Aniche, Bruntink and Bacchelli, [To Mock or Not To Mock? An Empirical Study on Mocking Practices](https://repository.tudelft.nl/file/File_dcb7ec41-615b-457c-9b5f-e6c6de2dea7e?preview=1), MSR 2017
- Panichella, Panichella, Fraser, Sawant and Hellendoorn, [Test Smells 20 Years Later: Detectability, Validity, and Reliability](https://pure.tudelft.nl/ws/portalfiles/portal/137994226/s10664_022_10207_5.pdf), EMSE 2022
