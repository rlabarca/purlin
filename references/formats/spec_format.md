> Format-Version: 3

# Feature Spec Format

The canonical 3-section format for feature specs.

## Location

```
specs/<category>/<name>.md
```

## Template

```markdown
# Feature: <name>

> Requires: <comma-separated spec names or invariant names>
> Scope: <comma-separated file paths this feature touches>
> Stack: <language>/<framework>, <key libraries>, <patterns>

## What it does

<One paragraph: what this feature is and why it exists.>

## Rules

- RULE-1: <Testable constraint>
- RULE-2: <Another testable constraint>

## Proof

- PROOF-1 (RULE-1): <Observable assertion description>
- PROOF-2 (RULE-2): <Observable assertion description>
```

## Required Sections

Every spec MUST have these 3 sections (case-insensitive heading match):

1. `## What it does` — prose description of the feature
2. `## Rules` — numbered constraints (`RULE-N: description`)
3. `## Proof` — numbered proof blueprints (`PROOF-N (RULE-N): description`)

## Metadata Fields

| Field | Required | Description |
|-------|----------|-------------|
| `> Requires:` | No | Comma-separated list of other spec names or invariant names whose rules also apply |
| `> Scope:` | No | Comma-separated file paths this feature touches (used for manual proof staleness) |
| `> Stack:` | No | Technology choices: `language/framework, key libraries, patterns` (helps rebuild from spec) |
| `> Visual-Reference:` | No | Visual source for build-time reference. Figma: `figma://fileKey/nodeId`. Image: `./designs/modal.png`. HTML: `./designs/modal.html`. URL: `https://staging.app.com/modal`. See invariant format for full syntax. |

## Rules Format

Each rule is a line under `## Rules`:

```
- RULE-N: <description>
```

Rules MUST be numbered sequentially: `RULE-1`, `RULE-2`, etc. The `sync_status` MCP tool parses these and tracks coverage. Unnumbered lines under `## Rules` trigger a WARNING.

### Good Rules

- Specific, testable constraints: "Return HTTP 400 when input is missing required fields"
- Observable behavior: "Log a warning when retry count exceeds 3"
- Boundary conditions: "Reject passwords shorter than 8 characters"

### Bad Rules

- Vague goals: "Handle errors properly"
- Implementation details: "Use a try-catch block around the API call"
- Untestable statements: "Be performant"

## Proof Format

Each proof is a line under `## Proof`:

```
- PROOF-N (RULE-N): <observable assertion description>
- PROOF-N (RULE-A, RULE-B, RULE-C): <multi-rule assertion — for Level 3 lifecycle tests>
```

Proofs describe what a test should assert, not how to implement it. Each rule must have at least one proof. Multiple proofs can reference the same rule. A single proof can reference multiple rules when it tests a flow that exercises several rules in sequence (common in Level 3 E2E tests).

### Tier tags

Append a tier tag to proofs that aren't default:

```
- PROOF-1 (RULE-1): Parse config and return default values
- PROOF-2 (RULE-2): POST to /api/users with database; verify 201 response @slow
- PROOF-3 (RULE-3): Load checkout page in browser; verify 3-click flow @e2e
- PROOF-4 (RULE-4): Review error messages against brand voice guide @manual
```

| Tag | When to use |
|-----|------------|
| (none) | Pure logic, in-memory, grep on local files |
| `@slow` | Needs database, network, filesystem, or external service |
| `@e2e` | Needs browser, full app stack, or UI rendering |
| `@manual` | Requires human judgment |

### Manual proofs

For rules that require manual verification, append `@manual`:

```
- PROOF-3 (RULE-3): Visual layout matches design spec @manual
```

After manual verification, the stamp is added by `purlin:verify --manual`:

```
- PROOF-3 (RULE-3): Visual layout matches design spec @manual(dev@example.com, 2026-03-31, a1b2c3d)
```

## FORBIDDEN Patterns (negative rules)

Some rules define what code must **never** do. These are just regular rules with negative proofs — no special syntax needed:

```markdown
## Rules
- RULE-3: No eval() in user-facing code
- RULE-4: All SQL queries use parameterized statements

## Proof
- PROOF-3 (RULE-3): Grep src/ for eval(); verify zero matches
- PROOF-4 (RULE-4): Grep src/ for string concatenation in SQL queries; verify zero matches
```

The test asserts absence:
```python
@pytest.mark.proof("security_input", "PROOF-3", "RULE-3")
def test_no_eval():
    result = subprocess.run(["grep", "-rn", "eval(", "src/"], capture_output=True, text=True)
    assert result.stdout == "", f"Found eval() in:\n{result.stdout}"
```

See the [Anchors & Invariants Guide](../../docs/invariants-guide.md) for more examples of FORBIDDEN patterns in security anchors.

## Requires Behavior

When a spec declares `> Requires: i_design_tokens, api_contracts`, the `sync_status` tool merges rules from those specs into the coverage report. The feature's tests must prove both its own rules and the required rules (or the required specs must have their own proofs).
