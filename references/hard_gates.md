# The gate

The gate is the one project setting: what must be true of every rule before a version is
proven. It is defined
here and nowhere else. A skill, a doc or a script that needs it links to this page rather than
restating it, because three copies of this answer drifted into three different answers once
already.

**A gate is two things**, and both must exist for it to mean anything:

1. The setting saying what has to be true of every rule.
2. A marker that says one commit met it, which anyone can check. That marker is the tag:
   `purlin:sign` writes the annotated tag `signed/<version>` when every rule meets the gate,
   and no tag is written while one falls short.

Setting the first without the second is a preference, not a gate. Where a project has a
remote runner, the push of that tag starts a run that reruns the tagged tests on a clean
machine and checks every committed record, brief and signature against the tagged code, so
the tag is a claim someone else can test rather than one you have to take on trust.

## The three levels

A rule answers up to three questions, one per level, and each answer is a **cell**. `gate` in
`.purlin/config.json` says how many of the three the project asks. A rule **meets the gate**
when every cell up to the gate's level is met. `purlin:init` asks the one question that sets it:
what must be true of every rule before a version is proven?

| Gate | Who it fits | Cells that exist | What every rule must have |
|------|-------------|------------------|---------------------------|
| `passed` | One person working alone | spec, passed | Every rule's passed cell is met, on every platform a counting run covered. A pass from either source counts |
| `strong` | A team: PM, designer, engineers, QA | + strong | Every rule whose bar is `strong` has a strong cell that is met: an audit wrote a record, the test strength at or above `min_strength`, nothing unsettled, no hold. A record from either source counts |
| `signed` | The same team under GxP | + signed | Every rule that needs a signature has one, and the signer list is set |

Each level derives defaults you can override:

| Derived | `passed` | `strong` | `signed` |
|---------|----------|----------|----------|
| `min_strength` | unused | 70 | 80 |
| The default bar | `passed` | `strong` | `strong` |
| `sign_at` | n/a | n/a | `strong`, asked by init |
| The breaks | off | on | on |
| Origin tags | optional | optional | required |

`purlin:init --gate <level>` changes the level later. Raising it adds what is missing and asks
before each write. Lowering it deletes nothing.

Under `passed` no strength is measured, no bar is read, no list exists and no signature is
asked for. Raising the gate to `strong` turns the breaks on. The breaks run on a person's
machine and nowhere else: CI reruns the tests and verifies, and a record either source wrote
counts, so measuring the same breaks twice would cost a runner an hour and write the same
number.

## The bar

Every rule carries a **bar**, `passed` or `strong`: the evidence it must have before it can
be signed. A rule tagged `[bar: passed]` or `[bar: strong]` carries what it names, and a rule
with no tag takes the project's gate, so `passed` at the gate `passed` and `strong` at
`strong` and at `signed`.

The bar decides three things and nothing else decides them:

- **What the rule must clear.** A rule has **cleared its bar** when its bar is `passed` and
  its passed cell is met, or its bar is `strong` and its strong cell is met.
- **Whether the AI audit runs on it.** It runs on every rule whose bar is `strong`, and on no
  other.
- **Whether it needs a signature.** At the gate `signed` a rule needs one when `sign_at` is
  `all`, or when its bar is `strong`. `purlin:init` asks which at the `signed` gate; the
  default is `strong`.

A rule is **signable** when it has cleared its bar, needs a signature and does not have a
counting one. That is what the board's `Signable` column counts and what the `Sign` list
holds.

## Which evidence counts

**At `passed` the evidence is the test results.** `purlin:test` runs the tagged tests, writes
`.purlin/tests/<feature>.json` and `.purlin/tests.md`, and commits both itself under the
person's own identity. A teammate reads them on the git host without running anything.

**At `strong` and above the evidence is the record, and an audit writes it.** `purlin:audit`
runs the tests and the breaks, writes one record per feature under
`.purlin/records/local/<feature>/` with its briefs beside it, and commits both under your own
identity. It never pushes. A remote run writes the same files under `.purlin/records/ci/`.

**The folder is the source.** A record's own `source` field must say the same word as the
folder it sits in, and a file where the two disagree is ignored with one warning naming it.
What keeps the ci folder honest is the tag run: it reads the commit that added each file under
`ci/` and fails the job where the identity is not the runner's own. Nothing on the git host
guards the folder.

| Source | The folder | Counts under |
|--------|------------|--------------|
| `ci` | `.purlin/records/ci/<feature>/`, written by the CI identity through the git host's API | `passed`, `strong`, `signed` |
| `local` | `.purlin/records/local/<feature>/`, written by `purlin:audit` on anyone's machine, and the test results `purlin:test` commits | `passed`, `strong`, `signed` |

**Both sources count at every gate.** What a signature locks is the evidence, not the machine
that produced it: the tests a person ran are the tests CI runs, and the breaks they measured
are the breaks CI would measure. A project that wants CI's word before a signature says so
once, by answering no to init's trust question, and then `purlin:sign` refuses a rule whose
tests have no `ci` record for the commit being signed.

A record describes the checkout while its commit is HEAD or its scope tree still hashes the
same. A CI pass that is no longer current makes the passed cell read `code changed`, and CI
clears it on the next run.

## Where CI runs, and when a project has a runner at all

**A project has a remote runner for two reasons and no others.** A proof in `specs/` is
tagged `@env` for an operating system your machine is not, so only a runner can prove it.
Or you answered no to init's trust question, so the tests a signature rests on run on a
clean machine. A project with neither gets no workflow: `purlin:sign` writes the tag, you
push it, and nothing runs remotely.

Where a workflow exists it triggers on two things and nothing else: a push to a `run/*`
branch, which is the branch `purlin:test --remote` creates and deletes around one run, and
a push of a `signed/*` tag, which is what `purlin:sign` writes. A push to any other branch
starts nothing, and a pull request starts nothing.

| The run | What starts it | What it writes |
|---------|----------------|----------------|
| A remote run | `purlin:test --remote` pushes `run/<branch>-<sha7>` | the tagged tests, and at `strong` and above one record per feature under `.purlin/records/ci/` with the briefs beside it, committed on that branch. `purlin:test --remote` pulls them home and deletes the branch |
| A tag run | a person pushes `signed/<version>` | nothing. It reruns the tagged tests on a clean machine and ends with `gate_check.py --check --verify` |

**What the tag run verifies.** Every signature and every hold must still bind the rule,
proof, test, bar and audit it names, so a tag cannot stand over code that changed after it
was signed. Every file under `.purlin/records/ci/**` and `.purlin/briefs/ci/**` must have
been committed by the runner's own identity, read off the commit that added it, so a person
cannot write a record as CI's. A file that fails either is named under `Evidence` and the
job fails.

No breaks run on CI. Test strength is what `purlin:audit` measures on a person's machine,
and a record either source wrote counts at every gate.

**A push is free.** Nothing runs at push time and no hook stands in front of it: a push is
a person's act, to any branch, and the tag is what says a commit met the gate.
`purlin:test --remote` is the one push Purlin makes, and it pushes a run branch rather than
the branch you are on. No skill opens a pull request.

## Branch rules

None. An earlier release printed three rulesets, because the gate was a required check on a
pull request; the gate is the tag now, and a tag is a marker rather than a barrier. Apply
whatever your organisation asks of any repository.

## The signer list

`signers` in `.purlin/config.json` holds the emails of the people who may sign. It changes by
pull request like any other file, so git history records who could sign and when.

A signature counts under `signed` when all five hold. Under `strong`, where what a signature
clears is a question the machine could not settle, a committed signature from anyone counts.

- The commit that added the signature file is signed and the signature verifies.
- The author's email is on `signers` as of that commit.
- That author is not the author of the commit that last touched the test file.
- The signature's bound hashes still match the current rule text, proof text, test body and
  what the audit found.
- Under `signed`, the commit is on the protected branch.

**Trust.** `purlin:init` asks `Do you trust your own machine for the tests and the signing?
[y/n]` and writes `trust: local` or `trust: remote`. Under `local`, the default, your own run
is the evidence and `purlin:sign` signs what you ran. Under `remote`, `purlin:sign` refuses a
rule whose tests have no `ci` record for the commit being signed and says to run
`purlin:test --remote` first. `purlin:init --update` asks again.

`purlin:init --gate signed` asks for the emails and prints the one-time signing setup for each
person. Under `signed` with no list, `sync_status` and `scripts/ci/gate_check.py --check` both
print `→ signer list missing: run purlin:init --gate signed` and the check exits 1. This works
with a single QA person, works the same on both git hosts, and needs nothing the git host has to
be configured for.

`sign_at` says which rules need one, and `purlin:init --gate signed` asks for it. `strong`,
the default, asks for a signature on every rule whose bar is `strong`; `all` asks for one on
every rule. A rule that needs none carries `required` false on its signed cell and meets the
level whichever way that cell reads.

## CI writes no signature file

CI runs the tagged tests and, on a run branch, writes the record and the briefs. It signs
nothing. A signature directory holds only files a person wrote, and the tag run checks that
every `ci/` file was committed by the runner itself.

What CI cannot settle it says out loud. A `@manual` proof makes the strong cell read `manual
test`, and an AI audit that could not tell whether the test observes what the proof names
makes it read `unsettled`. A rule whose bar is `strong` that no audit has reached reads `not
audited`, and what moves that one is `purlin:audit`, not a person. A signature file for the
current hashes clears the first two: from anyone under `strong`, from a counting signer under
`signed`. The signer writes the one line with `--note`.

## Holds

A **hold** is how a person who read the brief says the test does not prove the proof as written:

```
purlin:sign <feature> RULE-N --hold "<the missing case>"
```

That commits one file bound to the rule's hashes. While the hold is current both the strong
cell and the signed cell read `held`, whatever the bar and whatever the tests are doing, so the
rule does not meet the gate at `strong` or `signed` and it is on the Review list. A failing
test is work in front of the hold, not instead of it. A signature by a person for the current
hashes outranks the hold. Changing the rule, the proof or the test ends the hold, as it stales
a signature.

## What is not a gate

- Writing code without invoking a skill.
- Writing a test with no proof marker. It runs; `sync_status` does not count it.
- Committing without running an audit.
- A rule whose passed cell reads `code changed`. Only the code changed; the next run clears it.
- A proof tagged `@env` for an operating system this host is not. It is listed as
  `<os>: no record yet`, and a remote run's matrix proves it.
- Pushing a branch. A push is free.

## Platforms

A record and a set of test results each name the operating system they ran on. The passed cell
lists one **platform** per operating system a counting run named, each with its own word, its
source and when it ran, and the cell's own word rolls them up. Where the platforms disagree the
cell reads `partial`: a rule whose tests pass on Linux and fail on Windows is neither passed nor
failed, `partial` is not met, and it blocks the gate exactly as a failure does. A rule tagged for
one platform that has not run there still reads `not run`. Test strength is platform independent,
because the breaks are measured once per feature.

## Nothing runs at push time

No hook is installed, at push time or at commit time. A push is a person's act, free, to any
branch, and Purlin stands nowhere in front of it. `purlin:init --update` removes the pre-push
hook an earlier release installed and says so.

**Nothing in a Claude Code hook gates anything either.** The plugin registers no `PreToolUse`,
no `PermissionRequest` and no `UserPromptSubmit` handler, which are the events through which a
hook could stop or steer a turn. Every NEVER in `agents/purlin.md`, the rule that an agent does
not push among them, is an instruction to the agent and not a mechanism that stops it. What
survives an agent ignoring an instruction runs outside the agent's turn: the tag run, which
reruns the tests on a clean machine and verifies the committed evidence against the tagged
code.
