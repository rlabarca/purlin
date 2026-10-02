# How Purlin works

For anyone meeting Purlin for the first time, and for anyone who has to explain it. This is the
shortest description of the whole thing: one rule, its proof and its test, two facts, and who
takes each step.

- A **rule** is one line in a spec saying what the software must do.
- A **proof** says in plain language how that is shown.
- A **test** is any test in your own suite with one comment above it naming the proof:
  `# purlin: login PROOF-4`.

Purlin runs your own test command and reads its report. It says which rules pass on the code as
it is now.

Purlin keeps two things: the evidence of what the tests saw, and a person's sign-off over it.
It shows them as two facts, in the terminal and on the dashboard:

```
Tests: met
Sign-off: signed 0.1.0 at a1b2c3d
```

**Tests** reads `met` when every rule's tests pass on the committed evidence, and `not met`
otherwise.

**Sign-off** reads one of three things:

- `signed 0.1.0 at a1b2c3d` when a person signed this code;
- `signed 0.1.0, 4 commits since` when the code moved on after the last sign-off;
- `not signed` when nobody has signed.

Everything else Purlin prints is information.

```mermaid
flowchart TD
    T{"purlin:test<br>every rule passes?"}
    L(["Left to do,<br>with the command that does it"])
    C["purlin:test --all --commit<br>Tests: met"]
    S["purlin:sign<br>the evidence package,<br>the hand checks, one signature"]
    G(["signed/#lt;version#gt;"])
    T -->|no| L
    T -->|yes| C
    C --> S
    S --> G
```

[evidence_and_signoff.md](../references/evidence_and_signoff.md) is the one definition of the
two facts, of which evidence counts for a sign-off and of what `signed/<version>` means.

## The loop, and where it runs

The loop is `purlin:spec`, `purlin:build`, `purlin:test`, and `purlin:audit` where you want it.
Then `git push`. Every step runs on your own machine.

Nothing is signed while the work goes on. Product, QA and developers improve rules, proofs and
tests together. `Left to do` lists the work, with the command for each line.

When the tests are met, a person runs `purlin:sign` whenever the team chooses.

One person on one laptop is the ordinary case. You write the rule, you build it, you run the
tests, you sign, and you push the tag.

## Four words

**A push is `git push`, typed by you.** Any branch, any time. A command writes, commits where
you asked it to, and stops. No command pushes.

**The evidence is what runs saw.** It is one file per feature per source,
`.purlin/evidence/<source>/<feature>.json`, with one section per operating system. Your runs
write into `.purlin/evidence/local/`.

- `purlin:test` writes the file and commits nothing.
- `purlin:test --commit` commits the specs, the marked tests and the settings the results
  describe. Then it commits the evidence, as `purlin: evidence at <sha7>`.
- A section goes `out of date` when the spec, the tests or the code the spec covers
  (`> Scope:`) change. The next run clears it.

The developer's hand-off is run and commit: `purlin:test --all --commit`, and your project's
own run for a proof tagged for another operating system.

**An audit writes into the same evidence.** For each rule it says what it found: `strong`,
`weak` or `spot-checked`, with each finding and each bug it planted. You run `purlin:audit` when
you want it, and nothing waits on it. [audit.md](audit.md) says what it checks and why.

**A sign-off is a person's signature over the evidence package.** `purlin:sign` reads the
committed evidence and builds the package, `.purlin/evidence/package/<version>.json`. It stops
at each hand check and takes one signature in a signed commit. The first sign-off of a version
writes the signed tag `signed/<version>`. Later sign-offs are added after it. The sign-off
records what the signer was shown and each note they typed, and no judgment.
[sign-off.md](sign-off.md) is the walk in full.

| File | Written by | Where it lands |
|------|-----------|----------------|
| evidence | `purlin:test`, `purlin:audit`, a project's own run on another system | `.purlin/evidence/local/<feature>.json`, `.purlin/evidence/ci/<feature>.json` |
| evidence package | `purlin:sign` | `.purlin/evidence/package/<version>.json` |
| sign-off | `purlin:sign` | `.purlin/evidence/package/<version>.signoffs/` |

## Testing on another system

Purlin runs your tests where you are. Reaching another platform is your project's own setup,
and Purlin keeps the evidence. Purlin itself only works locally. It drives no remote pipeline
and adds none to your repository. A proof tagged `@env(windows)` is proven only by a run on
Windows, which your project sets up for itself;
[running-and-evidence.md](running-and-evidence.md#testing-on-another-system) has one worked
example.

## Questions every developer asks

**What does a run end on?** The status. It has three opening lines: `Purlin status: <project>,
plugin <version>`, `Tests:` and `Sign-off:`. Then come the table, the sentence, such as
`3 rules. 2 pass their tests.`, and `Left to do`. `Left to do` has one line per kind of work
left, with its count and its command. Its first line is the next step. Where the tests are met
and this code is not signed, the last line reads
`Every rule passes its tests on the committed evidence. To sign it: purlin:sign`.
[getting-started.md](getting-started.md) shows both endings from a real run.

**Do my tests run on my machine, or somewhere else?** On your machine. `purlin:test` runs the
marked tests of what changed and writes what they saw. `purlin:test --all` runs every feature.
`purlin:audit` runs there too. A test needs another machine only where its proof is tagged for
an operating system yours is not.

**When does `purlin:test` exit 1?** In any of these cases:

- a tied test failed or did not run;
- a spec writes a number twice or holds a merge-conflict line;
- evidence is missing;
- a comment above a test names nothing a spec has;
- the settings file is missing or cannot be read;
- the project was set up by Purlin 0.9.5 and not upgraded;
- no test command is set.

What the audit found never makes it exit 1.

**What keeps the tests from reading `met`?** Each of these is a line of `Left to do`, with the
command that clears it:

- a failed test;
- a rule with no test;
- a result that is `out of date`;
- a rule whose tests passed on one operating system and failed on another;
- a system that has not run its tests;
- a slow test that has not passed;
- a spec to repair;
- a test comment to correct;
- results that are written and not committed.

Two more lines are work that does not stop the tests reading `met`: a rule the audit found
weak, left to do as `to strengthen`, and a rule with no proof, left to do as a rule to write a
proof for.

**What if a rule has no proof?** A test may carry the rule's own id, `# purlin: login RULE-2`.
The rule reads `no test`, with the reason `no proof written`, only when neither a proof nor a
marked test names it. A rule whose tests pass and that has no proof is left to do as a rule to
write a proof for, with `purlin:spec`.

**What do `strong`, `weak`, `spot-checked` and `not audited` mean?**

- `strong`: the spot tests found nothing, and a planted bug was caught by the proof's test. An
  AI writes the bug: the one small change that test is most likely to miss.
- `weak`: a spot test fired on one of the rule's tests, or a planted bug was not caught. A
  surviving bug is shown with the case the AI says it breaks. The rule is left to do as
  `to strengthen`, with `purlin:build`, which strengthens the test and settles the finding with
  a test run. [audit.md](audit.md#what-to-do-with-a-finding) says how it ends.
- `spot-checked`: the spot tests found nothing, and no bug was planted and caught. The audit
  says why.
- `not audited`: no audit has read the rule. `purlin:audit` reads it when you run it.
- `out of date`: the rule, its proof, its test or its code changed since the audit read it. Its
  last result stays on screen.
- `waiting`: the rule's tests have not passed, so it reads neither.

**What is a hand check?** A proof tagged `@manual`: a judgment call, which only a person can
make. It has no test. A rule checked by hand alone reads `checked at sign-off` and is counted
as neither passing nor failing. `purlin:sign` stops there, and the signer may type what they
saw. After a sign-off the rule shows its last note, as
`noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`.

**When do I say which operating system a test needs?** On the proof line, with `@env(windows)`,
`@env(macos)` or `@env(linux)`. A proof with no `@env` runs anywhere, and a pass on any
operating system satisfies it. Your machine runs the untagged proofs and the ones tagged for
it. A proof tagged for another system reads `not run`, with a reason such as
`Windows: no run yet`, until that system runs it. The rule is left to do as
`1 rule to test on Windows: run purlin:test on Windows`.

**What does `partial` mean?** A rule keeps one result per operating system a current run
covered. It reads `partial` when two systems that each have a current result disagree.
`partial` is not passing. The rule is left to do as `to fix`.

**What about more than one checkout?** Each checkout of a repository, a worktree included, has
its own results, status and dashboard.
[working-together.md](working-together.md#more-than-one-checkout) says how they meet.

## Read next

- [getting-started.md](getting-started.md) for the first session.
- [working-together.md](working-together.md) for a team.
- [sign-off.md](sign-off.md) for the sign-off, QA's path to it and its use beside a regulated
  system.
