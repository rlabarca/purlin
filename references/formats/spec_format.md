> Format-Version: 11

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

- RULE-1: <Testable constraint> [risk: high] [origin: pm] [criterion: US-12]
- RULE-2: <Another testable constraint>

## Proof

- PROOF-1 (RULE-1): <Observable assertion> @integration @env(linux)
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
| `> Scope:` | No | Comma-separated file paths this feature touches. A record carries the git tree hash of these files, which is what tells a code change from a rule change |
| `> Stack:` | No | Technology choices: `language/framework, key libraries, patterns` |
| `> Source:` | No | Anchors only. A git URL plus a path in that repo, or local file globs. See the anchor format |
| `> Pinned:` | No | Anchors only. The commit sha of a git source, or the hash of the local files |
| `> Path:` | No | Anchors only. The path in the source repo, when `> Source:` carries the URL alone |

### Multi-line description

```markdown
> Description: Two-file configuration that separates shared team
>   defaults from per-user overrides. Resolution merges both files
>   so plugin updates stay visible.
> Scope: scripts/mcp/config_engine.py
```

### Retired fields

`> Visual-Reference:`, `> Visual-Hash:` and `> Global:`-adjacent visual
tracking are retired. A spec that still carries one parses; the field is
ignored and the file is named once in the run's warnings. A design is a
versioned file under `designs/`, pinned by an anchor's `> Source:` and
`> Pinned:`.

## Rules format

```
- RULE-N: <description> [risk: <level>] [origin: <role>] [criterion: <id>]
```

Rule ids are assigned in increasing order and never reused. A retired rule
leaves its number vacant and the rules that remain keep the numbers they had,
so a gap in the sequence is legal and the parser reports nothing for it.
Renumbering would silently repoint every test marker and every approval that
already names the old id. Unnumbered lines under `## Rules` are reported.

### Rule tags

Tags sit at the end of the line and are read off it, so the text that remains
is the claim alone. Re-tagging a rule never stales the approval that binds it.

| Tag | Values | Default | Meaning |
|-----|--------|---------|---------|
| `[risk: ...]` | `high`, `medium`, `low` | `low` | How much a wrong answer costs. Under the `approved` gate, `high` and `medium` need a current human approval and `low` is auto-approved by CI |
| `[origin: ...]` | `pm`, `design`, `qa`, `eng` | `eng` | Who owns the rule. Drift routes a change by origin |
| `[criterion: ...]` | any id | none | The upstream acceptance criterion the rule came from |

Under the `approved` gate, risk and origin are required and a rule without
them is reported.

Tags are read from the end with `\s*\[(risk|origin|criterion):\s*([^\]]+)\]\s*$`,
one at a time, in any order.

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

### Tier tags

Append a tier tag to a proof that is not a unit test:

```
- PROOF-1 (RULE-1): Parse the config and verify the default values
- PROOF-2 (RULE-2): POST /api/users against the database; verify 201 @integration
- PROOF-3 (RULE-3): Load the checkout page in a browser; verify the 3-click flow @e2e
- PROOF-4 (RULE-4): Read the error messages against the brand voice guide @manual
```

| Tag | When to use |
|-----|-------------|
| (none) | Pure logic, in memory, or a grep over local files |
| `@integration` | Needs a database, the network, the filesystem or an external service |
| `@e2e` | Needs a browser, the full stack or a rendered interface |
| `@manual` | Needs human judgment. No test; the evidence is an approval with a one-line note, always human, never auto-approved |

Any `@<name>` other than `@env` is read as a tier, and its results are read
from `.purlin/runtime/proofs/<feature>.<name>.json`. The four above are the
common ones.

### Operating system tags

A tier says what kind of test a proof is. `@env` says which operating system
it must be proved on:

```
- PROOF-53 (RULE-29): Lock a file and verify a second process cannot open it @env(windows)
- PROOF-54 (RULE-30): Verify the default console codec round-trips a non-ASCII path @env(macos)
```

At most one `@env` per proof, and the values are `windows`, `macos` and
`linux`: those three are the whole vocabulary. A proof with no `@env` is
satisfied by a record from any operating system. A proof with `@env` is
Recorded only when a counting record from that operating system passes it; a
rule with proofs on two systems needs both, and the status line says
`windows: no record yet` rather than adding a state.

On a machine that is not the named one, the plugin skips the test and the
status says so.

### Retired tags

`@on(<id>)`, a bare `@windows` tier and a stamped
`@manual(<email>, <date>, <sha>)` are retired. A spec that still carries one
parses; the tag is ignored and the file is named once in the run's warnings.
Rewrite `@on(windows)` as `@env(windows)`.

A tag is recognised only when it does not follow a list connector (`,`, `and`,
`or`), so a description whose prose ends in `@unit, @integration and @e2e` has
no tag and is not truncated.

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
@pytest.mark.proof("security_input", "PROOF-3", "RULE-3")
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
