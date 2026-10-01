# The audit: would your tests catch a bug?

A passing test is not proof that it checks anything. The audit tries to make each test fail.

## How it works

**1. Heuristic spot tests.** Purlin flags tests that check nothing, check the code against
itself, or never check the result the proof expects. It reads the tests as text, with no AI and
without running them, so this step is free. The six checks, and the research behind each, are in
[the heuristic spot tests reference](../references/review_criteria.md#heuristic-spot-tests).

**2. Plant one bug.** For each proof, an AI puts one small bug in a throwaway copy of your code,
aimed at what the proof says. If the proof says a sample collected at 08:00 and received at 09:30
is `90` minutes old, the bug might make the age come out an hour off.

**3. Run that proof's test.** The test fails: it caught the bug, and the rule is `strong`. The test
still passes: the rule is `weak`, and you see the bug it missed:

```
sample_age PROOF-1: the test still passes when src/age.py:12 adds an hour.
```

**4. `purlin:audit`.** Run it whenever you like, or give the agent a target:

> Build and audit until 80% of rules are strong.

The agent strengthens the weak tests and audits again until the share reaches 80%. The audit ends
on that share:

```
The audit found 42 of 50 rules strong (84%).
```

## What you can count on

- **Your code is never changed.** Every planted bug lives in a copy that is thrown away.
- **Nothing waits on it.** A weak rule is work to do, not a gate. It never stops a test run or a
  sign-off.
- **It stays fast.** Only proofs whose test or code changed since the last audit get a new bug.
- **Nothing to install.** No extra tool for each language; any test Purlin can run, it can audit.
- **What it found is kept.** It goes into the evidence, and the signer sees it at sign-off.

What it does not do: prove your tests catch every possible bug. It tests the claim each proof
makes, one bug at a time. A rule with no proof has nothing to plant a bug against.

## Why this works

**AI-written tests often check what the code does, not what was asked.** When a model writes a
test, its expected answer tends to come from the code as written, so a bug is copied into the test
([Konstantinou, Degiovanni and Papadakis, 2024](https://arxiv.org/pdf/2410.21136)). Model-written
tests also often check nothing at all
([Siddiq et al., EASE 2024](https://arxiv.org/pdf/2305.00418)) and lean on mocks
([an empirical study of coding agents, 2026](https://arxiv.org/pdf/2602.00409)). The spot tests
catch these, and the proof, written by a person, supplies the expected answer.

**Planting bugs is the most reliable test of a test.** Whether tests catch small deliberate bugs
tracks whether they catch real ones
([Just et al., FSE 2014](https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf)).
Code coverage, how much code the tests run, does not
([Inozemtseva and Holmes, ICSE 2014](https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf)).

**Big companies plant few, targeted bugs, not thousands.** Google plants bugs only in the code a
change touches and shows developers the few their tests missed
([Petrović et al., TSE 2021](https://arxiv.org/pdf/2102.11378)). Meta has an AI write a few bugs
aimed at one concern
([Foster et al., FSE 2025](https://arxiv.org/pdf/2501.12862)), and AI-written bugs look more like
real ones than tool-made ones ([Tip et al., LLMorpheus](https://arxiv.org/pdf/2404.09952)). Purlin
does the same, one bug per proof.

**An AI's opinion alone is not enough.** Asking a model whether a test looks good is the weakest
check: models judge inconsistently
([a large-scale evaluation of model judges, 2026](https://arxiv.org/pdf/2606.19544)). At Meta, AI
tests only ship after a measured check
([Alshahwan et al., FSE 2024](https://arxiv.org/pdf/2402.09171)). In Purlin the AI plants the bug,
but the test run decides.

## Fast enough, safe enough

| How to judge a test | Speed | What it shows |
|---|---|---|
| An AI reads it | Fast | An opinion |
| Plant bugs everywhere (classic mutation testing) | Minutes to hours, a tool per language | Objective, across all the code |
| **Spot tests, then one planted bug per proof** | **Free, then one AI call and one test run per changed proof** | **Objective, aimed at what the requirement says** |

Purlin takes the last row: real evidence where the requirement is, cheap enough to run every day.

## Sources

The research behind Purlin's approach, each linked to the paper itself.

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
