# Anchors & Invariants Guide

Anchors and invariants are specs whose rules apply to other features. They define cross-cutting constraints — standards that multiple features must follow.

## Anchors vs Invariants

| | Anchor | Invariant |
|-|--------|-----------|
| **Location** | `specs/<category>/<prefix>_name.md` | `specs/_invariants/i_<prefix>_name.md` |
| **Editable?** | Yes — locally owned | No — gate-protected, synced from external source |
| **Source** | Your team | External (git repo, Figma, compliance doc) |
| **Prefixes** | `design_`, `api_`, `security_`, `brand_`, `platform_`, `schema_`, `legal_`, `prodbrief_` | Same, with `i_` prefix |
| **Use case** | Team-defined standards | External standards you must conform to |

Both use the same 3-section spec format. Both are referenced via `> Requires:` in feature specs. The only difference is ownership: you control anchors, external sources control invariants.

---

## Anchors

An anchor is a regular spec that defines rules other features must follow. Anyone on the team can create and edit them.

### Example

```markdown
# Anchor: api_rest_conventions

> Scope: src/api/
> Stack: node/express, REST/JSON

## What it does
REST API conventions for all endpoints.

## Rules
- RULE-1: All endpoints return JSON with {data, error, meta} envelope
- RULE-2: Error responses use standard HTTP status codes (400, 401, 403, 404, 500)
- RULE-3: List endpoints support cursor-based pagination via ?cursor= parameter

## Proof
- PROOF-1 (RULE-1): GET /users returns {data: [...], error: null, meta: {}}
- PROOF-2 (RULE-2): POST /users with invalid body returns 400 with {error: "validation_failed"}
- PROOF-3 (RULE-3): GET /users?cursor=abc returns next page with meta.next_cursor
```

### Using anchors

Feature specs reference anchors in `> Requires:`:

```markdown
# Feature: user_api

> Requires: api_rest_conventions
> Scope: src/api/users.js
```

`sync_status` includes the anchor's rules in the feature's coverage report. Tests for `user_api` must prove both its own rules and `api_rest_conventions` rules.

### Anchor type prefixes

| Prefix | Domain | Example |
|--------|--------|---------|
| `api_` | API contracts, REST conventions | `api_rest_conventions.md` |
| `security_` | Auth, access control, secrets | `security_auth_standards.md` |
| `design_` | Visual standards, layout | `design_component_library.md` |
| `brand_` | Voice, naming, identity | `brand_copy_standards.md` |
| `platform_` | Platform constraints, browser support | `platform_accessibility.md` |
| `schema_` | Data models, validation | `schema_user_model.md` |
| `legal_` | Privacy, data handling, compliance | `legal_data_retention.md` |
| `prodbrief_` | User stories, UX requirements | `prodbrief_checkout_flow.md` |

---

## Forbidden Patterns (negative rules)

Some rules define what code must **never** do. These are "FORBIDDEN patterns" — and they're just rules with negative proofs.

### Example: security anchor with FORBIDDEN patterns

```markdown
# Anchor: security_input_handling

> Scope: src/

## What it does
Input handling security standards. Prevents common injection attacks.

## Rules
- RULE-1: No eval() in user-facing code
- RULE-2: All SQL queries use parameterized statements, never string concatenation
- RULE-3: User input is HTML-escaped before rendering

## Proof
- PROOF-1 (RULE-1): Grep src/ for eval(); verify zero matches
- PROOF-2 (RULE-2): Grep src/ for string concatenation in SQL queries; verify zero matches
- PROOF-3 (RULE-3): Render user input containing <script>alert(1)</script>; verify it appears escaped in output
```

### How to write FORBIDDEN proofs

A FORBIDDEN pattern is a rule that says "X must not exist." The proof is a negative assertion — verify the thing is absent:

```python
@pytest.mark.proof("security_input_handling", "PROOF-1", "RULE-1")
def test_no_eval_in_source():
    """FORBIDDEN: no eval() in user-facing code"""
    import subprocess
    result = subprocess.run(
        ["grep", "-rn", "eval(", "src/"],
        capture_output=True, text=True
    )
    assert result.stdout == "", f"Found eval() in:\n{result.stdout}"
```

```python
@pytest.mark.proof("security_input_handling", "PROOF-3", "RULE-3")
def test_xss_prevention():
    """FORBIDDEN: unescaped user input in HTML"""
    response = render_template("profile", name="<script>alert(1)</script>")
    assert "<script>" not in response
    assert "&lt;script&gt;" in response
```

The key insight: **there is no special FORBIDDEN mechanism in Purlin.** A FORBIDDEN pattern is just a rule with a proof that asserts absence. The proof system handles it identically to any other rule — if the proof passes, the pattern is absent. If it fails, the violation is visible in `sync_status`.

For more on writing effective rules, proofs, and anchors, see the [Spec Quality Guide](../references/spec_quality_guide.md).

---

## Invariants

Invariants are read-only specs from external sources. Your project must conform to them — you can't change them locally.

### Where they live

```
specs/_invariants/
  i_design_brand.md          # Design system tokens
  i_api_v3_contract.md       # API contract from another team
  i_security_owasp.md        # Security requirements
```

All invariant files use the `i_` prefix.

### Format

Same 3-section format as anchors, plus source metadata:

```markdown
# Invariant: i_design_brand

> Type: design
> Source: git@github.com:acme/design-system.git
> Path: tokens/colors.md
> Pinned: a1b2c3d4

## What it does
Color tokens from the design system.

## Rules
- RULE-1: Primary color is #1a73e8
- RULE-2: Error color is #d93025

## Proof
- PROOF-1 (RULE-1): CSS variable --color-primary equals #1a73e8
- PROOF-2 (RULE-2): CSS variable --color-error equals #d93025
```

- **`> Source:`** — git repo URL or Figma URL
- **`> Path:`** — file path within the source repo
- **`> Pinned:`** — commit SHA (git) or lastModified timestamp (Figma)

Full format: [references/formats/invariant_format.md](../references/formats/invariant_format.md)

### Write protection

The gate hook blocks all writes to `specs/_invariants/i_*`. If you try to edit one:

```
BLOCKED: Invariant files are read-only. Use purlin:invariant sync to update from the external source.
```

This is the **only** hard write block in Purlin.

### Syncing from external sources

**Git-sourced (all types):**

```
purlin:invariant sync i_api_v3_contract
```

Compares `> Pinned:` SHA to remote HEAD. If different, pulls the updated file and updates the SHA.

**Figma-sourced (design type):**

```
purlin:invariant sync figma figma.com/design/abc123/Brand-System
```

Reads the Figma file via MCP, extracts design constraints as rules. `> Pinned:` is the Figma `lastModified` timestamp.

**CI staleness check:**

```
purlin:invariant sync --check-only
```

Compares all invariants' `> Pinned:` to remote sources without pulling. Fails if stale. Use in CI before `purlin:verify --audit`.

### Build time vs test time (Figma)

During `purlin:build`, the agent reads Figma directly via MCP for full visual context (screenshots, layout, tokens). During `purlin:verify`, the system just runs tests against the extracted rules — never touches Figma. Build time is creative; test time is mechanical.

---

## Using Anchors and Invariants in Features

Both are referenced the same way in `> Requires:`:

```markdown
# Feature: color_picker

> Requires: i_design_brand, design_component_library
> Scope: src/components/ColorPicker.js
```

`sync_status` includes all required rules in the feature's coverage report. Tests must prove both the feature's own rules and all required anchor/invariant rules.
