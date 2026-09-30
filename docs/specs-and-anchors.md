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
> Requires: security_baseline
> Scope: src/auth.py, src/session.py
> Stack: python/flask, bcrypt
> Highest-Rule: 3

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

Every metadata line starts with `>`. `> Scope:` is required at the gate `signed`; every other
line is optional.

| Field | What it does |
|-------|--------------|
| `> Description:` | Plain-language summary. Continuation lines start with `>`. The dashboard shows it beneath the spec's row when the row is opened |
| `> Requires:` | The anchors whose rules also apply to this feature, by name. It names anchors only |
| `> Scope:` | The files this feature's code lives in: a file, a folder, or a glob holding `*`, `?` or `[` |
| `> Stack:` | Language, framework and the libraries that matter, read as one line |
| `> Highest-Rule:` | The highest rule number the spec has ever held |

`> Scope:` earns its place. The evidence carries a fingerprint of the files it names, so a
change to one of them is told from a change to a rule. When the code changes, the rule's passed
cell reads `out of date` with the reason `code changed since <sha7>` until the next run clears
it, and `purlin:test` with no feature named runs this feature again. A signature covers the
code as well as the rule, the proof and the test, so a change to any of them ends it, and the
rule is left to do as `to sign`.

A spec with no `> Scope:`, or one whose entries reach no file git tracks, names no files.
`purlin:test` runs its tests every time, and the status names it:

```
1 spec names no files, so its tests run every time: export. Run purlin:spec export to add its > Scope: line.
```

At the gate `signed` a rule of such a spec can be signed, but the signature does not count: the
rule is left to do as `to tie to its files`, and no tag is written until the spec names them.

An entry that finds no file git tracks, where the spec's other entries reach files, is warned
of with the spec's name, the entry and `purlin:spec`.

## Rules

One claim per line, in the present tense, saying what the software does rather than how.

```
- RULE-N: <claim>
```

The rule line carries the claim and nothing else. Its text is everything after the id,
bracketed text at the end included, and every rule is asked what the project's gate asks.

Rule numbers are never reused. A new rule takes one more than the highest of `> Highest-Rule:`
and every rule number in the spec, and `> Highest-Rule:` is raised to it, so a deleted number is
never used again. `purlin:spec` reads both copies of the spec, the working copy and
`origin/main`'s, and takes proof ids one past the highest proof number in either. A deleted rule leaves its
number vacant and every other rule keeps the number it had; a gap in the sequence is legal and
nothing reports it. Renumbering would repoint every test marker and every signature that
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

A proof is optional at the gate `passed`: there a test may carry the rule's own id instead,
`# purlin: login RULE-2`. A rule with neither a proof nor such a test reads `no test` with the
reason `no proof written`. From `strong` up every rule needs a proof, and a rule whose tests
pass with none reads `no proof` in its strong cell.

### Manual proofs

A proof carries no tag when a test settles it, whatever that test needs to run: `purlin:test`
runs every marked test of the features it runs. Tag a proof `@manual` when only a person's
judgment settles it:

```
- PROOF-5 (RULE-2): Read the error messages against the brand voice guide @manual
```

A `@manual` proof has no test. Its rule's strong cell reads `manual test`, and the rule is left
to do as `to test by hand` at every gate until a person checks it and signs it with
`purlin:sign`, adding `--note "<what you saw>"` when they write what they saw.

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
system. Which run proves which proof is in
[hard_gates.md](../references/hard_gates.md#where-a-runner-runs-and-when-a-project-has-one).

## Ids across branches

`purlin:spec` takes the next rule and proof ids against both the working copy and
`origin/main`'s copy, so a number already on `origin/main` is not taken again on a branch.

When two branches took the same number before either fetched, the merge leaves one id twice.
Keep both rules, give the incoming one the next free number, and move its test markers and its
signature filenames with it. Two branches that advanced the same anchor pin resolve to the
newer sha.

## Anchors

An anchor is a spec for something shared across features: a security policy, an API contract,
a data-retention rule. It lives under `specs/_anchors/`, or opens with `# Anchor: <name>`, and
uses the same two sections and the same rule and proof grammar as any other spec.

A feature names the anchors whose rules apply to it with `> Requires: <name>`, and their rules
are counted with the feature's own, labelled `required`: the feature must prove them too. An
anchor's own `> Requires:` brings in the anchors it names in turn. An anchor with
`> Global: true` applies to every feature spec without being named. In the status table a
feature's `Rules` cell counts the rules it owns and then the anchor rules it proves, as
`4 (+2 shared)`; the summary counts each rule once, under the spec that owns it.

`> Requires:` names anchors only. A name that is a feature's spec is warned of, and its rules
do not apply:

```
login: > Requires: names export, which is not an anchor, so its rules do not apply. Run purlin:spec login.
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

A pin is always a commit, never a branch. A branch moves, and an anchor whose rules changed
under a project with no diff to read is what pinning exists to prevent.

**sync --check** reports without writing, one line for each anchor whose pin is behind, and
exits 1 when one is:

```
security_baseline: the pin 71abd36 is behind its source, now b3a6387. Run purlin:anchor sync security_baseline.
```

`purlin:drift` runs the same check, one lookup per source per run, so a pin that has fallen
behind shows at the start of a session without anyone asking for it.

**sync** rewrites the local copy from the source, advances the pin and says what moved:

```
security_baseline: RULE-2 changed, RULE-3 added. Pin advanced from 71abd36 to b3a6387. Commit it as anchor(security_baseline): sync (b3a6387), then run purlin:test.
```

It commits nothing: you commit the copy in one commit with that subject, so the diff shows which
rules moved. A signature on a rule whose text moved ends, and the rule is left to do as
`to sign` again.

Never edit a pinned rule in place: the next sync overwrites it and the change is lost with no
trace. A change to the rule is a pull request against the source repository, and the next sync
brings it here once it merges. A rule that belongs only to this project goes in a separate
local anchor that says `> Requires: <the pinned one>`.

## Next

- A codebase that predates its specs: [spec-from-code.md](spec-from-code.md)
- Who writes which rule: [working-together.md](working-together.md)
