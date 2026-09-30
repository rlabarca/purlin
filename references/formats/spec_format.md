> Format-Version: 19

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

A spec is known by `<name>` alone. Two specs with one name in different
folders are warned of: only one is read, and the warning names both files and
the `git mv` that renames the other.

## Template

```markdown
# Feature: <name>

> Description: Plain-language summary of what this feature does
>   and why it exists. It can span continuation lines.
> Requires: <comma-separated anchor names>
> Scope: <comma-separated file paths this feature touches>
> Stack: <language>/<framework>, <key libraries>, <patterns>
> Highest-Rule: <the highest rule number the spec has held>

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
| `> Requires:` | No | Comma-separated list of anchor names, the project's own or pinned, whose rules also apply. A name that is a feature's spec and not an anchor is warned of, and its rules do not apply |
| `> Scope:` | At the gate `signed` | Comma-separated paths this feature touches: a file, a directory, or a glob holding `*`, `?` or `[`. The evidence carries a fingerprint of the tracked files they reach, which is what tells a code change from a rule change. Below `signed` it is optional: a feature spec with none, or one that reaches no tracked file, is reported as naming no files (`incomplete` in the payload), its tests run on every `purlin:test`, and nothing blocks. At `signed` such a spec's rules cannot be signed and no tag is written. An entry that finds no file git tracks, where the others reach files, is warned of. An anchor never needs one |
| `> Stack:` | No | Technology choices: `language/framework, key libraries, patterns` |
| `> Highest-Rule:` | No | The highest rule number the spec has ever held, as a whole number. A new rule takes the next number above it, so a deleted number is never used again. It changes no fingerprint and no count |
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

### Fields 0.9.5 wrote

`> Visual-Reference:` and `> Visual-Hash:` are not part of the format. A spec
that still carries one parses; the field is ignored and the file is named once
in the run's warnings, and `purlin:init --update` removes it.

## Rules format

```
- RULE-N: <description>
```

Rule ids are assigned in increasing order and never reused. A retired rule
leaves its number vacant and the rules that remain keep the numbers they had,
so a gap in the sequence is legal and the parser reports nothing for it.
Renumbering would silently repoint every test marker and every signature that
already names the old id.
A new rule takes one more than the highest of `> Highest-Rule:` and every rule number the spec holds, and `> Highest-Rule:` is raised to it, so a number is never used again.
Unnumbered lines under `## Rules` are reported. A rule id written twice is
warned of; the rule is read once, with the text of its second line.

A rule line carries no tag. Its text is everything after the id, bracketed
text at the end included, and every rule is asked for what the project's gate
asks. The rule text hash is taken over that text with runs of whitespace
normalised to one space, so reflowing a line leaves the hash the same.

A rule no proof line names is read from a test marked with the rule's own id,
`purlin: <feature> RULE-<n>`; with no such test its passed cell reads `no test`,
with the reason `no proof written`.

### Good rules

- Specific, testable constraints: "Return HTTP 400 when a required field is missing"
- Observable behaviour: "Log a warning when the retry count exceeds 3"
- Boundary conditions: "Reject passwords shorter than 8 characters"

### Bad rules

- Vague goals: "Handle errors properly"
- Implementation details: "Use a try/except around the API call"
- Untestable statements: "Be performant"

## Proof format

```
- PROOF-N (RULE-N): <observable assertion>
- PROOF-N (RULE-A, RULE-B, RULE-C): <a flow that exercises several rules in order>
```

A proof describes what a test asserts, not how it is written. Proofs are
optional at the gate `passed`, where a rule's passing tests are the whole of its
evidence, and required from `strong` up: there a rule whose test passes and
that has no proof reads `no proof` in its strong cell, with the reason `the rule
has a test and no proof`, and counts under `Left to do` as a rule to write a
proof for. Several proofs can name the same rule, and one proof can name
several rules when it drives a flow through all of them. A list item under
`## Proof` of any other form is not read as a proof and is warned of.

### The manual tag

Append `@manual` to a proof that no test can settle:

```
- PROOF-1 (RULE-1): Started with no settings file, the app reports a request timeout of `30` seconds
- PROOF-2 (RULE-2): A sign-up with an email no account uses is answered with the status `201`, and the email then appears in the list of users
- PROOF-3 (RULE-3): Read the error messages against the brand voice guide @manual
```

| Tag | When to use |
|-----|-------------|
| (none) | A marked test settles the proof, whatever it needs to run |
| `@manual` | A person's judgment is the only instrument. No test, so the rule's strong cell reads `manual test`; the evidence is a signature a person writes with `purlin:sign`, carrying a one-line note of what they saw when one is given |

`@manual` and `@env` are the only tags a proof line carries. Any other trailing
`@<name>` is not a tag: it stays in the proof text. `purlin:test` runs every
marked test of the features it runs.

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
## Rules
- RULE-3: No eval() in user-facing code
- RULE-4: Every SQL query uses a parameterised statement

## Proof
- PROOF-3 (RULE-3): Every source file of the app is searched for the call `eval(`, and 0 are found
- PROOF-4 (RULE-4): Every source file of the app is searched for an SQL statement joined to other text with `+` or `%`, and 0 are found
```

```python
# purlin: security_input PROOF-3
def test_no_eval():
    result = subprocess.run(["grep", "-rn", "eval(", "src/"],
                            capture_output=True, text=True)
    assert result.stdout == "", "Found eval() in:\n" + result.stdout
```

## Requires behaviour

When a spec declares `> Requires: design_tokens, api_contracts`, the rules of
those anchors are counted with its own, labelled `required`, and its tests
must prove them. An anchor's own `> Requires:` brings in the anchors it names
in turn. A name in `> Requires:` that is a feature's spec and not an anchor is
warned of, and its rules do not apply. An anchor with `> Global: true` applies
to every feature spec without being named.
