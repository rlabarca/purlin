> Format-Version: 17

# Spec format

The 2-section format every spec uses. A spec opens with `# Feature: <name>` or
`# Anchor: <name>`.

## Location

```
specs/<category>/<name>.md
```

## Template

```markdown
# Feature: <name>

> Description: Plain-language summary of what this feature does
>   and why it exists. It can span continuation lines.
> Requires: <comma-separated spec or anchor names>
> Scope: <comma-separated file paths this feature touches>
> Stack: <language>/<framework>, <key libraries>, <patterns>

## Rules

- RULE-1: <Testable constraint> [level: passed]
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
parses and nothing reads that heading, so a spec written against an older
format keeps working; new specs should not add one. What the feature does
belongs in `> Description:`, which the dashboard displays.

## Metadata fields

| Field | Required | Description |
|-------|----------|-------------|
| `> Description:` | No | Plain-language description. Continuation lines start with `>` and are not themselves `> Field:` lines. Displayed in the dashboard. |
| `> Requires:` | No | Comma-separated list of other spec or anchor names whose rules also apply |
| `> Scope:` | At the gate `signed` | Comma-separated paths this feature touches: a file, a directory, or a glob holding `*`, `?` or `[`. The evidence carries a fingerprint of the tracked files they reach, which is what tells a code change from a rule change. Below `signed` it is optional: a feature spec with none, or one that reaches no tracked file, is reported as naming no files (`incomplete` in the payload), its tests run on every `purlin:test`, and nothing blocks. At `signed` such a spec's rules cannot be signed and no tag is written. An anchor never needs one |
| `> Stack:` | No | Technology choices: `language/framework, key libraries, patterns` |
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

### Retired fields

`> Visual-Reference:`, `> Visual-Hash:` and `> Global:`-adjacent visual
tracking are retired. A spec that still carries one parses; the field is
ignored and the file is named once in the run's warnings.

## Rules format

```
- RULE-N: <description> [level: <level>]
```

Rule ids are assigned in increasing order and never reused. A retired rule
leaves its number vacant and the rules that remain keep the numbers they had,
so a gap in the sequence is legal and the parser reports nothing for it.
Renumbering would silently repoint every test marker and every signature that
already names the old id. Unnumbered lines under `## Rules` are reported.

### The rule tag

The one tag sits at the end of the line and is read off it, so the text that
remains is the claim alone: reflowing the whitespace leaves the rule text hash
the same. The level uses the gate's three words and means what the gate means:
tests; tests and audit; tests, audit and signature. A signature records the
level the rule had when it was signed and does not lock it, so re-marking a
rule stales no signature.

| Tag | Values | Default | Meaning |
|-----|--------|---------|---------|
| `[level: ...]` | `passed`, `strong`, `signed` | the project's gate | The evidence the rule must have to meet the gate. `passed` asks for passing tests; `strong` for passing tests and an audit that found them sound; `signed` for both and a signature |

A rule that names no level takes the project's gate, which is an answer
rather than a gap. The gate is the ceiling: a rule's level is the lower of its
tag and the gate, so a tag above the gate is read as the gate and
`purlin:status` says how many rules are marked above it. A value that is not
one of the three words is read as no tag. Any other bracketed text at the end
of the line is not a tag: it stays in the claim.

A rule no proof line names reads `no test` in its passed cell, with the reason
`no proof written`.

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

A proof describes what a test asserts, not how it is written. Every rule needs
at least one proof; several proofs can name the same rule, and one proof can
name several rules when it drives a flow through all of them.

### The manual tag

Append `@manual` to a proof that no test can settle:

```
- PROOF-1 (RULE-1): Parse the config and verify the default values
- PROOF-2 (RULE-2): POST /api/users against the database; verify 201
- PROOF-3 (RULE-3): Read the error messages against the brand voice guide @manual
```

| Tag | When to use |
|-----|-------------|
| (none) | A tagged test settles the proof, whatever it needs to run |
| `@manual` | A person's judgment is the only instrument. No test, so the rule's strong cell reads `manual test`; the evidence is a signature file carrying a one-line note, always written by a person |

`@manual` and `@env` are the only tags a proof line carries. Any other trailing
`@<name>` is not a tag: it stays in the proof text. `purlin:test` runs every
tagged test of the features it runs.

### Operating system tags

`@env` says which operating system a proof must be proved on:

```
- PROOF-53 (RULE-29): Lock a file and verify a second process cannot open it @env(windows)
- PROOF-54 (RULE-30): Verify the default console codec round-trips a non-ASCII path @env(macos)
```

At most one `@env` per proof, and the values are `windows`, `macos` and
`linux`: those three are the whole vocabulary. A proof with no `@env` is
satisfied by a current section from any operating system. A proof with `@env`
meets the passed cell only when a current section from that operating system
passes it; a rule with proofs on two systems needs both, and the cell reads
`not run` with the reason `windows: no run yet` rather than adding a word.

On a machine that is not the named one, the run does not count the proof and
says which operating system it needs.

### Retired tags

`@on(<id>)`, a bare `@windows` and a stamped                         <!-- retired -->
`@manual(<email>, <date>, <sha>)` are retired. A spec that still carries one
parses; the tag is ignored and the file is named once in the run's warnings.
Rewrite `@on(windows)` as `@env(windows)`.                          <!-- retired -->

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
- PROOF-3 (RULE-3): Grep src/ for eval(); verify zero matches
- PROOF-4 (RULE-4): Grep src/ for string concatenation in SQL; verify zero matches
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
those specs are counted with its own: its tests must prove both, or the
required specs must carry their own proofs. An anchor with `> Global: true`
applies to every feature spec without being named.
