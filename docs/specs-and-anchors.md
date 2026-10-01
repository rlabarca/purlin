# Specs and anchors

For anyone who writes rules: product, developers and QA.

A spec is one file per feature. It holds the claims the software must satisfy and how each
claim is shown. A **rule** is one claim, one line. A **proof** says in plain language how that
claim is shown. A **test** is any test in your own suite that carries a marker, one comment
naming the proof: `# purlin: login PROOF-2`. Those three are the whole model, and everything
else Purlin does reads them. `references/formats/marker_format.md` is the one home of the
marker.

The format is versioned. `references/formats/spec_format.md` inside the plugin is the
contract, and its first line, `> Format-Version: <n>`, says which version this release ships;
this page explains the format and that file settles it.

## The file

```
specs/<category>/<name>.md
```

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

You do not type this by hand. `purlin:spec` writes it from a sentence in chat, a ticket, a
product description, pasted acceptance criteria or a screenshot, prints each rule with its
proofs under it, and asks whether to change any before it saves. `purlin:spec <name>` edits an
existing spec in place and never renumbers it. `purlin:spec` commits the spec on its own and
ends on one line:

```
Spec saved: login. Next: purlin:build login
```

`## Rules` and `## Proof` are the only two sections anything reads, matched without regard to
case, so `## rules` reads as `## Rules`. A spec carrying some other heading still parses, and
nothing reads that heading. What the feature does belongs in `> Description:`.

### Metadata

Every metadata line starts with `>`, and every one is optional.

| Field | What it does |
|-------|--------------|
| `> Description:` | Plain-language summary. Continuation lines start with `>`. The dashboard shows it beneath the spec's row when the row is opened |
| `> Scope:` | The files this feature's code lives in: a file, a folder, or a glob holding `*`, `?` or `[`. An anchor carries none: its rules cover the whole project, and a `> Scope:` line on an anchor is warned of and not read |
| `> Stack:` | Language, framework and the libraries that matter, read as one line |
| `> Highest-Rule:` | The highest rule number the spec has ever held |
| `> Highest-Proof:` | The highest proof number the spec has ever held |

`> Scope:` earns its place. The evidence carries a fingerprint of the files it names, so a
change to one of them is told from a change to a rule. When the code changes, the rule's passed
cell reads `out of date` with the reason `code changed since <sha7>` until the next run clears
it, and `purlin:test` with no feature named runs this feature again.

A spec with no `> Scope:`, or one whose entries reach no file git tracks, names no files.
`purlin:test` runs its tests every time, and the status names it:

```
1 spec names no files, so its tests run every time: export. Run purlin:spec export to add its > Scope: line.
```

Writing a spec before its code is the normal order. A `> Scope:` that names files git does not
have yet is reported in one line per spec, as information, with the build first and the spec
second, since Purlin cannot tell a file not yet written from a mistyped path:

```
login: 1 file its scope names is not written yet: src/gone.py. Run purlin:build login, or correct the path with purlin:spec login.
```

## Rules

One claim per line, in the present tense, saying what the software does rather than how.

```
- RULE-N: <claim>
```

The rule line carries the claim and nothing else. Its text is everything after the id,
bracketed text at the end included.

Rule numbers are never reused. A new rule takes one more than the highest of `> Highest-Rule:`
and every rule number in the spec, and `> Highest-Rule:` is raised to it, so a deleted number is
never used again. Proof numbers are never reused either: a new proof takes one more than the
highest of `> Highest-Proof:` and every proof number in the spec, and `> Highest-Proof:` is raised
to it. `purlin:spec` reads both copies of the spec, the working copy and `origin/main`'s, for
both numbers. A deleted rule leaves its number vacant and every other rule keeps the number it
had; a gap in the sequence is legal and nothing reports it. Renumbering would repoint every test marker that
already names the old id.

A rule number written twice is warned of, and the rule is read once, with the text of its
second line:

```
login: RULE-2 is written twice; the second is read. Run purlin:spec login.
```

A rule about what the software must never do is an ordinary rule whose proof shows the
absence:

```markdown
- RULE-3: No eval() in user-facing code
- PROOF-3 (RULE-3): Every source file of the app is searched for the call `eval(`, and 0 are found
```

## Proofs

A proof says what is done, what is observed and the value that settles it, in words a person
who cannot read code can judge. `references/spec_quality_guide.md` is the one home of what a
good proof is.

```
- PROOF-N (RULE-N): <what is done, what is observed, the value>
- PROOF-N (RULE-A, RULE-B): <a flow that exercises several rules in order>
```

Several proofs may name one rule, and one proof may name several rules when it drives a flow
through all of them.

A test may carry the rule's own id in place of a proof's, `# purlin: login RULE-2`. A rule
with neither a proof nor such a test reads `no test` with the reason `no proof written`. A rule
whose tests pass with no proof reads `no proof` in its strong cell and is left to do as a rule
to write a proof for, with `purlin:spec`; the tests read `met` with it.

### Manual proofs

A proof carries no `@manual` when a test settles it, whatever that test needs to run. Tag a
proof `@manual` when only a person's judgment settles it:

```
- PROOF-5 (RULE-2): Read the error messages against the brand voice guide @manual
```

A `@manual` proof is a hand check. It has no test, and nothing is left to do for it. Its
rule's strong cell reads `checked at sign-off`: the walk of `purlin:sign` stops at the rule,
and the signer may type, in one line, what they saw. After a sign-off the rule carries its last
note with the version it was signed at and how many commits have come since, as
`noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`,
and the reader judges whether it still holds.

### Slow proofs

Some tests take a long time, like an integration test that drives a whole checkout. Add `@slow`
to the end of the proof such a test shows, and the test stays out of your way while you build:

```
- PROOF-4 (RULE-4): A cart of three items is checked out against the payment sandbox, and the order reads `paid` @slow
```

A slow proof is a proof like any other: one sentence saying how a rule is shown, and one test
with a comment above it. Nothing in the test changes. The tag changes only when the test runs.

| You run | When | What it does |
|---|---|---|
| `purlin:test` | While you build | Runs what changed and skips every slow test, with a feature named or not |
| `purlin:test --all` | When you want to check the whole project | Runs everything, slow tests included |

A `purlin:test` that skipped the checkout test says so before it runs anything:

```
Left out 1 slow proof: checkout PROOF-4. purlin:test --all runs it too.
```

Purlin remembers it, so you have nothing to remember. Until the slow test has passed, its proof
reads `not run` with the reason `slow: runs with purlin:test --all`, and every status and every
run end on:

```
Left to do:
  1 slow proof to run: purlin:test --all
```

The tests read `met` only after every slow test has passed on committed evidence, so
`purlin:test --all --commit` is the run a developer makes before handing a version over. Once
a slow test has passed, a plain `purlin:test` leaves its result alone and it keeps counting.
When a file the spec covers changes, the result goes out of date as any other does: the proof
reads `not run` again and the status lists it, so a person who never knew the test existed is
told when it is due and which command runs it.

`@slow` may stand with `@env(...)`, and a remote run runs the slow tests of the proofs it
proves. `@slow` with `@manual` is a mistake the status warns of, since a hand check has no test
to skip. [supported_frameworks.md](../references/supported_frameworks.md#leaving-a-slow-test-out)
says how each test tool skips one test, and the few cases where a slow test runs all the same.

### Operating systems

`@env` says which operating system a proof must be proved on. The values are `windows`,
`macos` and `linux`, and those three are the whole vocabulary.

```
- PROOF-53 (RULE-29): With a report open in one program, deleting it from another is refused with `The report is open in another program`, and the report is still there @env(windows)
```

At most one `@env` per proof. A proof with none is proved by a run on any operating system. A
proof with one is passed only when a run on that system passes it, and a rule with proofs on
two systems needs both. On another machine the passed cell reads `not run` with the reason
`Windows: no run yet`, and `purlin:test --remote` sends the proof to a remote runner of that
system. [running-and-evidence.md](running-and-evidence.md#when-a-project-has-a-runner) says
how that run is made.

## Ids across branches

`purlin:spec` takes the next rule and proof ids against both the working copy and
`origin/main`'s copy, so a number already on `origin/main` is not taken again on a branch.

When two branches took the same number before either fetched, the merge leaves one id twice.
When two branches take the same number, the number already on the default branch keeps it, and
the rule or proof from the branch not yet merged moves to the next free number. A moved rule's
audit is read again; `purlin:spec` renumbers it and its test comments when you say yes.
`purlin:drift` names every number written twice and which line moves. `purlin:spec` shows a dry
run first, the spec lines and the test comments in this checkout that would change, and asks
`Do it? [y/N]`; a test comment on another branch is named and never touched.

While a number is written twice, or a line git left from the conflict stays in the spec, every
rule of that spec reads `failed` with the reason, the tests read `not met`, and
`Left to do` reads `1 spec to repair: purlin:spec`. Two branches that advanced the same anchor
pin resolve to the newer sha.

A proof reworded after its test was written is caught the same way. The status, every test run
and `purlin:drift` name each test comment whose proof's wording changed after the test was
last changed, quoting both wordings, and `Left to do` counts it as a test comment to correct:

```
tests/test_login.py:1 names login PROOF-4, whose wording changed after the test was last changed in 1cf829e: it read "A" and now reads "B". Run purlin:build login to make the test show it; the line clears once the test changes.
```

Where the old wording now stands under another id, the line ends
`Its old wording is now PROOF-6: move the comment there.`

## Anchors

An anchor is a set of rules for the whole project, such as a security policy or a rule about
what the code must never hold. It lives under `specs/_anchors/`, or opens with
`# Anchor: <name>`, and uses the same two sections and the same rule and proof grammar as any
other spec. Its tests check the whole project, and each of its rules is counted and audited
once. No spec names an anchor.

### What an anchor covers

Every rule of an anchor holds across the whole project, and its tests check the whole project.
The project is every file git tracks but the records Purlin writes under `.purlin/evidence/`:
the results of a run, the evidence package and its sign-offs. Any change to the project leaves
an anchor's results out of date until the next run. The audit plants no bug for an anchor's
proof: the heuristic spot tests alone judge its tests. A rule that cannot be checked across
the whole project is not an anchor's; write it in the spec of each feature that needs it, in
that feature's words.

### A rule with nothing to check

Write an anchor's rule as "for every X in the project, Y holds", so a project with no X has
nothing that breaks it. When its test finds no X, the test skips through the test tool's own
skip, with a reason that starts `nothing to check:`, as in
`nothing to check: this project has no screens`. The rule then reads `passed`, and the status,
the dashboard and the evidence package carry the reason, so a signer sees the rule was not
exercised:

```
security_no_dangerous_patterns RULE-3 passes with nothing to check here: this project has no screens.
```

Only an anchor's rule passes this way. On a feature's own rule such a skip reads `not run`,
with its reason kept. A pulled rule that fails in this project is a problem to raise with its
authors.

### A long check, and a check by hand

An anchor's test reads the whole project, so it can take a long time. Tag such a proof `@slow`
and it stays out of every build run: `purlin:test` skips it, `purlin:test --all` runs it, and
the status lists it while it is due, as [Slow proofs](#slow-proofs) says. A rule no test can
show takes a `@manual` proof and is checked by a person in the sign-off walk. One anchor with
the three forms together, a fast check, a slow one and a hand check:

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

In the status table the anchors stand first, under the line `Anchors`, and every other spec
follows under `Specs`. Each row counts its own rules, and the summary counts each rule once.

A spec that carries `> Requires:` or `> Global:`, or an anchor that carries `> Scope:`, is
warned of, and the line is not read:

```
login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.
security_no_dangerous_patterns: > Scope: is not read on an anchor, because an anchor covers the whole project. Run purlin:spec security_no_dangerous_patterns.
```

### One repository is the default

Most projects need nothing but `specs/_anchors/`:

```
purlin:anchor create <name>
```

It writes `specs/_anchors/<name>.md`, creating the folder with the first anchor, and commits it
as `anchor(<name>): create`. Anyone who writes specs writes anchors there too, and nothing is
pinned or synced. Reach for a second repository only when two or more projects must share the
same rules: it is a cost, and one project does not need it.

### An anchor repo

When several projects share rules, the rules live in their own repository and each project
keeps a pinned copy of the ones it uses.

**add** fetches the anchor and writes the local copy under `specs/_anchors/`:

```
purlin:anchor add <url> --path <file>
```

```
security_baseline: written to specs/_anchors/security_baseline.md, pinned 71abd36
  2 rules. Run purlin:status to see them.
```

The copy carries two tracking lines the author's own file does not:

```markdown
> Source: https://github.com/acme/policies.git specs/security_baseline.md
> Pinned: 71abd3617078292436107da19ca74db5b96e6255
```

The source is a spec in Purlin's format that holds at least one rule, kept in a git
repository. `add` refuses any other source, a text file, a description in words or a file with
no rule, writes nothing, and names `purlin:anchor create <name>` to write the rules in this
project instead.

A pinned copy is written as its source holds it; a `> Requires:`, `> Global:` or `> Scope:` line
in it is warned of, naming the source's owners as the ones to take it out:

```
security_baseline: its source, https://github.com/acme/policies.git, carries > Scope:, which Purlin does not read on an anchor, so the line is read as nothing. Ask the owners of https://github.com/acme/policies.git to take it out, then run purlin:anchor sync security_baseline.
```

A pin is always a commit, never a branch. A branch moves, and an anchor whose rules changed
under a project with no diff to read is what pinning exists to prevent.

**sync --check** reports without writing, one line for each anchor whose pin is behind, and
exits 1 when one is:

```
security_baseline: the pin 71abd36 is behind its source, now b3a6387. Run purlin:anchor sync security_baseline.
```

`purlin:status` and `purlin:drift` make the same check: they read the source's head and pull
nothing, so the anchor's file and its pin stay as they were. A pin that has fallen behind shows
at the start of a session without anyone asking for it, and `purlin:anchor sync` alone pulls.

**sync** rewrites the local copy from the source, advances the pin and says what moved:

```
security_baseline: RULE-2 changed, RULE-3 added. Pin advanced from 71abd36 to b3a6387. Commit it as anchor(security_baseline): sync (b3a6387), then run purlin:test.
```

It commits nothing: you commit the copy in one commit with that subject, so the diff shows which
rules moved.

Never edit a pinned rule in place: the next sync overwrites it and the change is lost with no
trace. A change to the rule is a pull request against the source repository, and the next sync
brings it here once it merges. A rule that belongs only to this project goes in a local anchor
of its own when it holds across the whole project, and in the spec of each feature it holds for
when it does not.

## Next

- Running the tests the proofs name: [running-and-evidence.md](running-and-evidence.md)
- Who writes which rule: [working-together.md](working-together.md)
