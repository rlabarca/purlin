# Specs and anchors

For anyone who writes rules: product, developers and QA.

A spec is one file per feature. It holds what the software must do and how each claim is shown.

- A **rule** is one claim, one line.
- A **proof** says in plain language how that claim is shown.
- A **test** is any test in your own suite with a marker: one comment naming the proof,
  `# purlin: login PROOF-2`. [marker_format.md](../references/formats/marker_format.md) is the
  one home of the marker.

Those three are the whole model. Everything else Purlin does reads them.

The format is versioned. [spec_format.md](../references/formats/spec_format.md) is the
contract, and its first line, `> Format-Version: <n>`, says which version this release ships.
This page explains the format. That file settles it.

## The file

```
specs/<category>/<name>.md
```

A name holds letters, digits, `_` and `-`.

```markdown
# Feature: login

> Description: Email and password sign-in with a lockout after repeated failures.
> Scope: src/auth.py, src/session.py
> Stack: python/flask, bcrypt
> Highest-Rule: 3
> Highest-Proof: 4

## Rules

- RULE-1: Return 200 and a session cookie for a correct email and password
- RULE-2: Return 401 for a wrong password
- RULE-3: Lock the account for 15 minutes after 5 consecutive failures

## Proof

- PROOF-1 (RULE-1): A known user signs in with the right password; the answer is `200` and it sets a session cookie
- PROOF-2 (RULE-2): A known user signs in with a wrong password; the answer is `401` and it sets no cookie
- PROOF-3 (RULE-3): After 5 wrong passwords in a row, the right password is refused with `423`
- PROOF-4 (RULE-3): 15 minutes after the fifth wrong password, the right password is answered with `200`
```

You do not type this by hand. Say in your own words what must be true, and `purlin:spec` writes
the rules for you, one line each. It takes a sentence in chat, a ticket, a product description,
pasted acceptance criteria or a screenshot. It prints each rule with its proofs under it, and
asks whether to change any before it saves.

`purlin:spec <name>` edits an existing spec in place and never renumbers it. `purlin:spec`
commits the spec on its own and ends on one line:

```
Spec saved: login. Next: purlin:build login
```

A change to a spec, even to one rule's words, puts every rule of that spec out of date. Its
results are held under one fingerprint of the whole spec. `purlin:test` runs that spec's tests
again.

`## Rules` and `## Proof` are the only two sections anything reads. They are matched without
regard to case, so `## rules` reads as `## Rules`. A spec with some other heading still parses,
and nothing reads that heading. What the feature does belongs in `> Description:`.

### Metadata

Every metadata line starts with `>`, and every one is optional.

| Field | What it does |
|-------|--------------|
| `> Description:` | Plain-language summary. Continuation lines start with `>`. The dashboard shows it beneath the spec's row when the row is opened |
| `> Scope:` | The files this feature's code lives in: a file, a folder, or a glob holding `*`, `?` or `[`. An anchor carries none: its rules cover the whole project, and a `> Scope:` line on an anchor is warned of and not read |
| `> Stack:` | Language, framework and the libraries that matter, read as one line |
| `> Highest-Rule:` | The highest rule number the spec has ever held |
| `> Highest-Proof:` | The highest proof number the spec has ever held |

**`> Scope:` tells Purlin when a result stops counting.** The evidence carries a fingerprint of
the files the line names. When one of them changes, the rule's passed cell reads `out of date`,
with the reason `code changed since <sha7>`, until the next run clears it. `purlin:test` with
no feature named runs this feature again.

A spec names no files when it has no `> Scope:`, or when its entries reach no file git tracks.
`purlin:test` runs its tests every time, and the status names it:

```
1 spec names no files, so its tests run every time: export. Run purlin:spec export to add its > Scope: line.
```

Writing a spec before its code is the normal order. A `> Scope:` may name files git does not
have yet. The status reports that in one line per spec, as information. The line names the
build first and the spec second, since Purlin cannot tell a file not yet written from a
mistyped path:

```
login: 1 file its scope names is not written yet: src/gone.py. Run purlin:build login, or correct the path with purlin:spec login.
```

## Rules

One claim per line, in the present tense. It says what the software does, not how.

```
- RULE-N: <claim>
```

The rule line carries the claim and nothing else. Its text is everything after the id,
bracketed text at the end included.

**Numbers are never reused.** A new rule takes one more than the highest of `> Highest-Rule:`
and every rule number in the spec, and `> Highest-Rule:` is raised to it. Proofs work the same
way with `> Highest-Proof:`. `purlin:spec` reads both copies of the spec for both numbers: the
working copy and `origin/main`'s. In a spec that has neither line, both go after the last `>`
line of the header, `> Highest-Rule:` first.

A deleted rule leaves its number vacant, and every other rule keeps the number it had. A gap in
the sequence is legal and nothing reports it. Renumbering would repoint every test marker that
already names the old id.

A rule number written twice is warned of. The rule is read once, with the text of its second
line:

```
login: RULE-2 is written twice; the second is read. Run purlin:spec login.
```

A rule about what the software must never do is an ordinary rule. Its proof shows the absence:

```markdown
- RULE-3: No eval() in user-facing code
- PROOF-3 (RULE-3): Every source file of the app is searched for the call `eval(`, and 0 are found
```

## Proofs

A proof is one sentence saying how a rule is shown, in words a person who cannot read code can
judge. It names an exact result a test can check.
[spec_quality_guide.md](../references/spec_quality_guide.md) is the one home of what a good
proof is.

```
- PROOF-N (RULE-N): <what is done, what is observed, the value>
- PROOF-N (RULE-A, RULE-B): <a flow that exercises several rules in order>
```

Several proofs may name one rule. One proof may name several rules when it drives a flow
through all of them.

A test may carry the rule's own id in place of a proof's, `# purlin: login RULE-2`.

- A rule with neither a proof nor such a test reads `no test`, with the reason
  `no proof written`.
- A rule whose tests pass with no proof reads `no proof` in its strong cell. It is left to do
  as a rule to write a proof for, with `purlin:spec`. The tests read `met` with it.

### Judgment calls

A test can check a result. Only a person can make a judgment call.

A proof is pass or fail: a test checks an exact result, like the message `Account locked`.

A judgment call is not: "It looks good." "It is easy to use." A test cannot decide these, and
neither can an AI.

Tag it `@manual`; no test runs for it. `purlin:sign` stops there; a person checks it and
writes what they saw.

```
- PROOF-5 (RULE-2): Read the error messages against the brand voice guide @manual
```

Not everything needs a rule: look and feel can stay outside Purlin.

A proof a test settles carries no `@manual`, whatever that test needs to run. A test may ask a
model a question with one right answer, such as which commands it offers after an install.

A `@manual` proof is a hand check. Nothing is left to do for it. At the stop the signer may
type, in one line, what they saw.

A rule checked by hand alone reads `checked at sign-off` and is counted as neither passing nor
failing: `10 rules. 9 pass their tests. 1 is checked at sign-off.` It never stops the tests
reading `met`. Once a sign-off notes it, it reads `passed`, with the note. Reword the rule or
the proof and it reads `checked at sign-off` again, with
`the rule's wording changed since its last note`.

A tag stands at the end of the proof line, after the text.

After a sign-off the rule carries its last note, with the version it was signed at and how many
commits have come since:
`noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`.
The reader judges whether it still holds.

### Slow proofs

Tag a proof `@slow`. Its test is skipped while you build and runs when you check the whole
project.

| | |
|---|---|
| Mark it once | Add `@slow` to the end of a proof whose tests take a long time, like integration tests and acceptance tests. |
| `purlin:test` | While you build. It runs what changed and skips every slow test, with a feature named or not. |
| `purlin:test --all` | When you want to check the whole project. It runs everything, slow tests included. |
| Purlin remembers it | When a slow test is due, every status says so: `1 slow proof to run: purlin:test --all` |

```
- PROOF-4 (RULE-4): A cart of three items is checked out against the payment sandbox, and the order reads `paid` @slow
```

A slow proof is a proof like any other: one sentence saying how a rule is shown, and one test
with a comment above it. Nothing in the test changes. The tag changes only when its test runs.

An acceptance test that walks a feature end to end makes a good slow proof. It stays out of
every build run, and `purlin:test --all --commit`, the hand-off before a sign-off, runs it.

A `purlin:test` that skipped the checkout test says so before it runs anything:

```
Left out 1 slow proof: checkout PROOF-4. purlin:test --all runs it too.
```

Until the slow test has passed, its proof reads `not run`, with the reason
`slow: runs with purlin:test --all`. Every status and every run end on:

```
Left to do:
  1 slow proof to run: purlin:test --all
```

**Nothing to remember.** The tests are fully `met` only after every slow test has passed, on
committed evidence. So `purlin:test --all --commit` is the run a developer makes before handing
a version over.

Once a slow test has passed, a plain `purlin:test` leaves its result alone, and it keeps
counting. A slow result a plain run kept is marked `kept` in the evidence, with the commit, the
time, the machine and the person of the run that took it. The status counts it. The sign-off
does not: it asks for `purlin:test --all --commit`. When a file the spec covers changes, the result goes out of date as any other does.
The proof reads `not run` again and the status lists it. A person who never knew the test
existed is told when it is due and which command runs it.

`@slow` may stand with `@env(...)`, and a run on that system runs the slow tests of the proofs
it proves. `@slow` with `@manual` is a mistake the status warns of: a hand check has no test to
skip.
[supported_frameworks.md](../references/supported_frameworks.md#leaving-a-slow-test-out) says
how each test tool skips one test, and the few cases where a slow test runs all the same.

### Operating systems

`@env` says which operating system a proof must be proved on. The values are `windows`,
`macos` and `linux`, and those three are the whole vocabulary.

```
- PROOF-53 (RULE-29): With a report open in one program, deleting it from another is refused with `The report is open in another program`, and the report is still there @env(windows)
```

- At most one `@env` per proof.
- A proof with none is proved by a run on any operating system.
- A proof with one is passed only when a run on that system passes it. A rule with proofs on
  two systems needs both.

On another machine the passed cell reads `not run`, with the reason `Windows: no run yet`,
and your project's own run on that system proves it.
[running-and-evidence.md](running-and-evidence.md#testing-on-another-system) says how that run
is made.

## Ids across branches

`purlin:spec` takes the next rule and proof ids against both the working copy and
`origin/main`'s copy. A number already on `origin/main` is not taken again on a branch.

Two branches can still take the same number before either fetched. The merge then leaves one id
twice. The number already on the default branch keeps it. The rule or proof from the branch not
yet merged moves to the next free number.

- `purlin:drift` names every number written twice and which line moves.
- `purlin:spec` resolves the conflict git left, where both sides only added lines, and shows a
  dry run of the renumbering. It asks `Do it? [y/N]`. A line both sides changed is left for you
  to choose. A moved rule's audit is read again.
- Drift run before the merge is committed says `A merge is in progress and is not committed`.
- A test comment on another branch is named and never touched.

While a number is written twice, or a line git left from the conflict stays in the spec, every
rule of that spec reads `failed` with the reason. The tests read `not met`, and `Left to do`
reads `1 spec to repair: purlin:spec`.

Two branches that advanced the same anchor pin resolve to the newer sha.

A proof reworded after its test was written is caught too. The status, every test run and
`purlin:drift` name each test comment whose proof's wording changed after the test was last
changed, quoting both wordings. `Left to do` counts it as a test comment to correct:

```
tests/test_login.py:1 names login PROOF-4, whose wording changed after the test was last changed in 1cf829e: it read "A" and now reads "B". Run purlin:build login to make the test show it; the line clears once the test changes.
```

Where the old wording now stands under another id, the line ends
`Its old wording is now PROOF-6: move the comment there.`

## Anchors

An anchor is a set of rules for the whole project, proven by tests that run across all of it.
A security policy is one. So is a rule about what the code must never hold.

An anchor lives under `specs/_anchors/`, or opens with `# Anchor: <name>`. It uses the same two
sections and the same rule and proof grammar as any other spec. Each of its rules is counted
and audited once. No spec names an anchor.

There are two kinds:

| | |
|---|---|
| They can be in this project | Write a rule once, such as no secret in the code. Tests across the whole project prove it, and no feature names it. |
| They can be owned elsewhere | Security, GRC / GxP, Design, etc. keep their rules in their own repository. Each project brings in the ones it must follow. This kind is a remote anchor. |

A rule that only some features need goes in those features' own specs.

### What an anchor covers

Every rule of an anchor holds across the whole project, and its tests check the whole project.
The project is every file git tracks, except the records Purlin writes under
`.purlin/evidence/`: the results of a run, the evidence package and its sign-offs.

Any change to the project leaves an anchor's results out of date until the next run. The
settings file counts as it does for a feature: changing a test command in `.purlin/config.json`
ends the results, and changing `version` alone does not.

The audit plants no bug for an anchor's proof. The heuristic spot tests alone judge its tests.

A rule that cannot be checked across the whole project is not an anchor's. Write it in the spec
of each feature that needs it, in that feature's words.

### A rule with nothing to check

Write an anchor's rule as "for every X in the project, Y holds". A project with no X then has
nothing that breaks it.

When its test finds no X, the test skips through the test tool's own skip, with a reason that
starts `nothing to check:`, as in `nothing to check: this project has no screens`. The rule
then reads `passed`. The status, the dashboard and the evidence package carry the reason, so a
signer sees the rule was not exercised:

```
security_no_dangerous_patterns RULE-3 passes with nothing to check here: this project has no screens.
```

Only an anchor's rule passes this way. On a feature's own rule such a skip reads `not run`,
with its reason kept. A remote anchor's rule that fails in this project is a problem to raise
with its authors.

### A long check, and a check by hand

An anchor's test reads the whole project, so it can take a long time. Tag such a proof `@slow`
and it stays out of every build run, as [Slow proofs](#slow-proofs) says.

A rule no test can show takes a `@manual` proof. A person checks it in the sign-off walk.

One anchor with the three forms together, a fast check, a slow one and a hand check:

```markdown
# Anchor: privacy

> Description: What every part of the project owes a person's data.

## Rules

- RULE-1: For every source file in the project, no line writes an email address to a log
- RULE-2: For every table in the project that holds a person's data, deleting the account leaves no row of theirs
- RULE-3: For every screen in the project that asks for a person's data, the words beside the field say why it is asked for

## Proof

- PROOF-1 (RULE-1): Every source file is searched for a logging call handed a value named `email`, and 0 are found
- PROOF-2 (RULE-2): In a fresh database an account with one row in each such table is deleted, and each table then holds 0 rows of that account @slow
- PROOF-3 (RULE-3): Open each such screen and read the words beside each field against the privacy notice @manual
```

[spec_quality_guide.md](../references/spec_quality_guide.md#a-good-anchor) holds the checklist
for a good anchor.

In the status table the anchors stand first, under the line `Anchors`. Every other spec follows
under `Specs`. Each row counts its own rules, and the summary counts each rule once.

A spec that carries `> Requires:` or `> Global:`, or an anchor that carries `> Scope:`, is
warned of, and the line is not read:

```
login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.
security_no_dangerous_patterns: > Scope: is not read on an anchor, because an anchor covers the whole project. Run purlin:spec security_no_dangerous_patterns.
```

### An anchor in this project

Most projects need nothing but `specs/_anchors/`:

```
purlin:anchor create <name>
```

It writes `specs/_anchors/<name>.md`, creating the folder with the first anchor, and commits it
as `anchor(<name>): create`. Anyone who writes specs writes anchors there too. Nothing is
pinned or synced.

Reach for a second repository only when two or more projects must share the same rules. It is
a cost, and one project does not need it.

### A remote anchor

A remote anchor is owned elsewhere. The team that owns the rules keeps them in its own
repository, and your project keeps a copy of the ones it must follow. Your copy is pinned to
one version of its source.

**add** fetches the anchor and writes your copy under `specs/_anchors/`:

```
purlin:anchor add <url> --path <file> [--name <name>]
```

Your copy takes its name from the file. `--name` gives it another, in letters, digits, `_` and `-`.
A name an anchor in the project already holds is refused, and the refusal names
`purlin:anchor sync <name>`. `--path` names a file inside the source: a path that is absolute or
holds `..` is refused.

```
security_baseline: written to specs/_anchors/security_baseline.md, pinned 71abd36
  2 rules. Run purlin:status to see them.
```

Your copy carries two tracking lines the author's own file does not:

```markdown
> Source: https://github.com/acme/policies.git specs/security_baseline.md
> Pinned: 71abd3617078292436107da19ca74db5b96e6255
```

The source is a spec in Purlin's format that holds at least one rule, kept in a git
repository. `add` refuses any other source: a text file, a description in words or a file with
no rule. It writes nothing, and names `purlin:anchor create <name>` to write the rules in this
project instead.

A pin is always a commit, never a branch. A branch moves, and rules that change under a
project with no diff to read are what the pin prevents.

#### Kept in step

`purlin:anchor sync` updates your copy. The status says when the source has moved on.

**sync --check** reports without writing. It prints one line for each anchor whose pin is
behind, and exits 1 when one is:

```
security_baseline: the pin 71abd36 is behind its source, now b3a6387. Run purlin:anchor sync security_baseline.
```

`purlin:status` and `purlin:drift` make the same check. They read the source's head and pull
nothing, so the anchor's file and its pin stay as they were. A pin that has fallen behind shows
at the start of a session without anyone asking. Only `purlin:anchor sync` pulls.

**sync** rewrites your copy from the source, advances the pin and says what moved:

```
security_baseline: RULE-2 changed, RULE-3 added. Pin advanced from 71abd36 to b3a6387. Commit it as anchor(security_baseline): sync (b3a6387), then run purlin:test.
```

It commits nothing. You commit the copy in one commit with that subject, so the diff shows
which rules moved.

#### Read-only

Your copy is never edited in your project. A change is made at the source, by the team that
owns it.

Edit a remote anchor's rule in place and the next sync overwrites it. The change is lost with
no trace. Make the change as a pull request against the source repository. The next sync brings
it here once it merges.

Your copy is written as its source holds it. A `> Requires:`, `> Global:` or `> Scope:` line
in it is warned of, and the warning names the source's owners as the ones to take it out:

```
security_baseline: its source, https://github.com/acme/policies.git, carries > Scope:, which Purlin does not read on an anchor, so the line is read as nothing. Ask the owners of https://github.com/acme/policies.git to take it out, then run purlin:anchor sync security_baseline.
```

A rule that belongs only to this project goes in an anchor of this project when it holds
across the whole project. When it does not, it goes in the spec of each feature it holds for.

## Next

- Running the tests the proofs name: [running-and-evidence.md](running-and-evidence.md)
- Who writes which rule: [working-together.md](working-together.md)
