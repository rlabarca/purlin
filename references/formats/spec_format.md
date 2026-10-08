> Format-Version: 25

# Spec format

The 2-section format every spec uses. A spec opens with `# Feature: <name>` or
`# Anchor: <name>`, where `<name>` is the file name without `.md`. The file
name is the spec's name, whatever the first line says; `# Anchor:` makes a spec
an anchor wherever it is kept. A first line of either form naming another
feature is warned of.

## Location

```
specs/<category>/<name>.md
```

A spec is known by `<name>` alone. A name holds letters, digits, `_` and `-`,
and does not start with `-`. This section is the one home of what a name holds:
a test comment, an anchor's `--name` and the upgrade from 0.9.5 read the same
name.

A spec whose name holds any other character is still read, and no test comment
can name it. The status warns of it in one line, with the `git mv` that renames
its file. The new name is the old one with each such character, and a leading
`-`, written `_`:

```
sample.age: spec name not allowed. A name holds letters, digits, _ and -. Run git mv specs/intake/sample.age.md specs/intake/sample_age.md.
```

Two specs with one name in different folders are warned of: only one is read,
and the warning names both files and the `git mv` that renames the other.

## Template

```markdown
# Feature: <name>

> Description: Plain-language summary of what this feature does
>   and why it exists. It can span continuation lines.
> Scope: <comma-separated file paths this feature touches>
> Stack: <language>/<framework>, <key libraries>, <patterns>
> Highest-Rule: <the highest rule number the spec has held>
> Highest-Proof: <the highest proof number the spec has held>

## Rules

- RULE-1: <Testable constraint>
- RULE-2: <Another testable constraint>

## Proof

- PROOF-1 (RULE-1): <Observable assertion> @env(linux)
- PROOF-2 (RULE-2): <Observable assertion>
```

## Required sections

Every spec has these two sections, matched case-insensitively:

1. `## Rules`: numbered constraints, `RULE-N: description`
2. `## Proof`: numbered proof blueprints, `PROOF-N (RULE-N): description`

These two are the whole structure. A spec carrying some other heading still
parses and nothing reads that heading; new specs should not add one. What the feature does
belongs in `> Description:`, which the dashboard displays.

## Metadata fields

| Field | Required | Description |
|-------|----------|-------------|
| `> Description:` | No | Plain-language description. Continuation lines start with `>` and are not themselves `> Field:` lines. Displayed in the dashboard. |
| `> Scope:` | No | Comma-separated paths this feature touches: a file, a directory, or a glob holding `*`, `?` or `[`. The evidence carries a fingerprint of the tracked files they reach, which is what tells a code change from a rule change. A feature spec with none, or one that reaches no tracked file, is reported as naming no files (`incomplete` in the payload), and its tests run on every `purlin:test`. Entries naming files git does not have yet are reported as information, not warned of; see "A scope naming a file not yet written". An anchor carries none: its rules cover the whole project, and a `> Scope:` line on an anchor is warned of and not read. |
| `> Stack:` | No | Technology choices: `language/framework, key libraries, patterns` |
| `> Highest-Rule:` | No | The highest rule number the spec has ever held, as a whole number. A new rule takes the next number above it, so a deleted number is never used again. It changes no fingerprint and no count |
| `> Highest-Proof:` | No | The highest proof number the spec has ever held, as a whole number. A new proof takes the next number above it, so a deleted number is never used again. It changes no fingerprint and no count |
| `> Source:` | No | Anchors only. A git URL plus a path in that repo. See the anchor format |
| `> Pinned:` | No | Anchors only. The commit sha of the source |
| `> Path:` | No | Anchors only. The path in the source repo, when `> Source:` carries the URL alone |

### Multi-line description

```markdown
> Description: One settings file, `.purlin/config.json`, committed
>   with the project. The resolver reads it whole and the settings
>   tool writes one key into it.
> Scope: scripts/mcp/config_engine.py
```

### A scope naming a file not yet written

Writing a spec before its code is the normal order, so a `> Scope:` naming files
git does not have yet is no mistake. The status prints one line per spec, as
information, naming the files, the build first and the spec second, since
Purlin cannot tell a file not yet written from a typo:

```
login: spec ahead of its code. src/gone.py is not written yet. Run purlin:build login, or purlin:spec login to correct the path.
states: spec ahead of its code. 3 files are not written yet, the first facts.py. Run purlin:build states, or purlin:spec states to correct the path.
```

The line clears once git has every file the scope names. An anchor's scope is
never read, so it gets no such line.

### Fields 0.9.5 wrote

`> Visual-Reference:` and `> Visual-Hash:` are not part of the format. A spec
that still carries one parses; the field is ignored and the file is named once
in the run's warnings, and `purlin:init --update` removes it.

`> Requires:` and `> Global:` are not part of the format either, because every
anchor covers the whole project. A spec that still carries one parses; the line
is not read, and every status and test run warns of it with its fix:
`login: line not read. Every anchor covers the whole project, so > Requires: is not read. Run purlin:spec login.`
`purlin:init --update` removes both.

## Rules format

```
- RULE-N: <description>
```

Rule ids are assigned in increasing order and never reused. A retired rule
leaves its number vacant and the rules that remain keep the numbers they had,
so a gap in the sequence is legal and the parser reports nothing for it.
Renumbering by hand would silently repoint every test comment that already
names the old id.

A new rule takes one more than the highest of `> Highest-Rule:` and every
rule number the spec holds. `> Highest-Rule:` is raised to that number, so a
number is never used again. In a spec that has neither `> Highest-Rule:` nor
`> Highest-Proof:`, both go after the last `>` line of the header,
`> Highest-Rule:` first.

Two branches can take the same number. The rule or proof already on the
default branch keeps it. The one from the branch not yet merged moves to the
next free number, and a moved rule's audit is read again. `purlin:spec`
renumbers it and its test comments when you say yes.

Unnumbered lines under `## Rules` are reported. A rule id written twice is
warned of; the rule is read once, with the text of its second line, and every
rule of the spec reads `failed`, with the reason `RULE-N is written twice in the
spec`, until one of the two lines is renumbered.

A line left from a merge conflict, one opening with seven `<`, `=`, `>` or `|`
followed by a space or the line's end, is warned of with its line number, and
every rule of the spec reads `failed`, with the reason `the spec holds a line
left from a merge conflict`, until it is taken out. A line of eight `=` is not
one. The spec is otherwise read as written, both sides' lines included.

A rule line carries no tag. Its text is everything after the id, bracketed
text at the end included. The rule text hash is taken over that text with runs of whitespace
normalised to one space, so reflowing a line leaves the hash the same.

A rule no proof line names is read from a test marked with the rule's own id,
`purlin: <feature> RULE-<n>`; with no such test its passed cell reads `no test`,
with the reason `no proof written`, and `Left to do` counts it as a rule to
write a test for.

`references/spec_quality_guide.md`, "Writing rules", says what makes a rule
worth writing.

## Proof format

```
- PROOF-N (RULE-N): <observable assertion>
- PROOF-N (RULE-A, RULE-B, RULE-C): <a flow that exercises several rules in order>
```

A proof describes what a test asserts, not how it is written. A rule whose
test passes and that has no proof counts under `Left to do` as a rule to write
a proof for, which does not stop the tests reading `met`, and reads `no proof`
in its strong cell, with the reason `the rule has a test and no proof`. Several proofs can name the same rule, and one proof can name
several rules when it drives a flow through all of them.

A tag stands at the end of the proof line, after the text, never before the
rule ids:

```
- PROOF-7 (RULE-7): A technician reads the rejection message and finds it clear @manual
- PROOF-8 (RULE-8): A batch of 500 samples is taken in; every sample has a result @slow
```

A list item under `## Proof` of any other form is not read as a proof. The
status warns of it in one line that gives the reason and quotes the line's first 4 words.
Where `@manual`, `@slow`, `@ai`, `@graded` or `@env(` stands between `PROOF-N` and the rule ids:

```
login: proof line not read. A tag goes last: "- PROOF-7 @manual (RULE-7): ...". Run purlin:spec login.
```

For any other line:

```
login: proof line not read. It is not `- PROOF-N (RULE-N): <text>`: "- PROOF-7: no rule ...". Run purlin:spec login.
```

A proof id written twice is warned of; the proof is read once, with the text of
its second line, and every rule of the spec reads `failed`, with the reason
`PROOF-N is written twice in the spec`, until one of the two lines is
renumbered. A line left from a merge conflict fails the spec wherever it stands
in the file, as "Rules format" says.

Proof ids are never reused either. A new proof takes one more than the highest of `> Highest-Proof:` and every proof number the spec holds, and `> Highest-Proof:` is raised to it, so a number is never used again.
A spec whose `> Highest-Proof:` reads `12` and whose `PROOF-10` to `PROOF-12` were deleted, leaving `PROOF-9` its highest, gives its next proof `PROOF-13`.
A spec with no `> Highest-Proof:` line whose proofs run to `PROOF-9` gives its next proof `PROOF-10`.

### The manual tag

Append `@manual` to a proof that no test can settle, where a person's judgment
is the only instrument. A proof with no tag is settled by a marked test,
whatever that test needs to run.

```
- PROOF-3 (RULE-3): Read the error messages against the brand voice guide @manual
```

No test runs for it, so the rule reads `checked at sign-off` in its strong
cell, and in its passed cell where its every proof is `@manual`. A person
checks it in the sign-off walk of `purlin:sign`;
`references/evidence_and_signoff.md` says what the sign-off records of it and
what the cell then shows.

`@manual`, `@slow`, `@env`, `@ai` and `@graded` are the only tags a proof line
carries, at most one of each, in any order, at the end of the line. Any other trailing `@<name>` is not a tag: it stays
in the proof text.

### The slow tag

Append `@slow` to a proof whose test takes a long time, like an integration
test:

```
- PROOF-4 (RULE-4): A cart of three items is checked out against the payment sandbox, and the order reads `paid` @slow
```

It is a proof like any other: one test, one comment above it, and nothing in
the test changes. The tag changes only when its test starts:
`references/purlin_commands.md` says which run starts it, and
`references/glossary.md` defines a slow proof. Until a run that starts it has
passed it, the proof reads `not run`, its rule's passed cell reads `not run`
with the reason `slow: runs with purlin:test --all`, and `Left to do` counts
it as `1 slow proof to run: purlin:test --all`. Its result goes out of date as
any other does. An anchor's proof takes the tag the same way.

`@slow` may stand with `@env(...)`. With `@manual` it is a mistake: a hand
check has no test to leave out, so the proof is read as `@manual` and the
status warns `<spec> PROOF-N (RULE-N): tags that conflict. It is read as
@manual, not @slow. Run purlin:spec <spec>.`

Adding or removing `@slow` is no change of a proof's wording, so it names no
test comment as one to correct.

### The AI tags

`@ai(...)` marks a proof about what an AI does with a prompt or a skill, and
names the models the proof is shown on. `@graded(...)` beside it says a model
grades the output against the proof's own sentence, and names that model:

```
- PROOF-4 (RULE-2): With the sample report, the reply names the three findings by their ids @ai(claude-opus-5-5)
- PROOF-5 (RULE-3): The summary states no fact the sample report does not hold @ai(claude-opus-5-5) @graded(claude-haiku-4-5-20251001)
- PROOF-6 (RULE-4): Asked for a refund over the limit, the reply refuses and names the limit @ai(claude-opus-5-5, claude-sonnet-5-5, runs=10)
```

| Tag | Value | What it says |
|-----|-------|--------------|
| `@ai(<model>, ...)` | One model or several, separated by commas, and at most one `runs=<n>`, `<n>` a whole number from 1 up | The proof's test runs on each model named, in the order written, and the proof passes when it passes on every one. `runs=<n>` is how many times the test runs on each model. Without it the `runs` setting of `.purlin/config.json` says, and 3 where that is not set |
| `@graded(<model>)` | One model | That model grades the output. `@ai` names the model tested, so `@graded` always stands beside an `@ai` |

A model's name holds letters, digits, `.`, `_`, `-`, `:` and `/`. A model named
twice in one `@ai(...)` is read once.

A proof that names a model is an AI proof. It is a proof like any other, with
one marked test, and it is a slow proof with or without `@slow`: everything
"The slow tag" says of a slow proof holds for it. `@slow` beside `@ai` is
allowed and adds nothing. `@ai` may stand with `@env(...)`.

The status names each mistake in one line:

| Mistake | The line | How the proof is read |
|---------|----------|-----------------------|
| `@ai` naming no model | `<spec> PROOF-N (RULE-N): spec to repair. @ai names no model. Run purlin:spec <spec>.` | Every rule of the spec reads `failed`, with the reason `PROOF-N carries @ai naming no model` |
| `@graded` naming no model | `<spec> PROOF-N (RULE-N): spec to repair. @graded names no model. Run purlin:spec <spec>.` | Every rule of the spec reads `failed`, with the reason `PROOF-N carries @graded naming no model` |
| `@graded` with no `@ai` beside it | `<spec> PROOF-N (RULE-N): spec to repair. @graded stands with no @ai. Run purlin:spec <spec>.` | Every rule of the spec reads `failed`, with the reason `PROOF-N carries @graded with no @ai` |
| A name holding any other character | `<spec> PROOF-N (RULE-N): spec to repair. A model's name holds letters, digits, ., _, -, : and /. Run purlin:spec <spec>.` | Every rule of the spec reads `failed`, with the reason `PROOF-N carries a model's name that cannot be read` |
| `@ai` or `@graded` beside `@manual` | `<spec> PROOF-N (RULE-N): tags that conflict. It is read as @manual, not @ai or @graded. Run purlin:spec <spec>.` | As `@manual` alone. The line names each of `@slow`, `@ai` and `@graded` the proof carries |
| `runs=` that is not a whole number from 1 up | `<spec> PROOF-N (RULE-N): tag not read. runs=0 is not a whole number from 1 up. Run purlin:spec <spec>.` | With its models and no `runs=` |

A spec to repair stays so until the tag is corrected, as a number written
twice does.

### Operating system tags

`@env` says which operating system a proof must be proved on:

```
- PROOF-53 (RULE-29): With a report open in one program, deleting it from another is refused with `The report is open in another program`, and the report is still there @env(windows)
- PROOF-54 (RULE-30): A file named `café.txt`, listed in a console with no encoding set, is shown as `café.txt` @env(macos)
```

At most one `@env` per proof, and the values are `windows`, `macos` and
`linux`: those three are the whole vocabulary. A proof with no `@env` is
satisfied by a current section from any operating system. A proof with `@env`
meets the passed cell only when a current section from that operating system
passes it; a rule with proofs on two systems needs both, and the cell reads
`not run` with the reason `Windows: no run yet` rather than adding a word.

On a machine that is not the named one, the run does not count the proof and
says which operating system it needs.

### Tags 0.9.5 wrote

A bare `@windows` and a stamped `@manual(<email>, <date>, <sha>)` are not part
of the format. A spec that still carries one parses; the tag is ignored, a
stamped `@manual` still reads as `@manual`, and the file is named once in the
run's warnings. `purlin:init --update` rewrites `@windows` as `@env(windows)`.

A tag is recognised only when it does not follow a list connector (`,`, `and`,
`or`), so a description whose prose ends in `@manual, @env and @word` has no
tag and is not truncated.

## Rules that forbid something

A rule about what code must never do is a regular rule with a proof that
asserts absence. No special syntax:

```markdown
- RULE-3: No eval() in user-facing code
- PROOF-3 (RULE-3): Every source file of the app is searched for the call `eval(`, and 0 are found
```
