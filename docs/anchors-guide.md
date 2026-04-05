# Anchors and External References

Anchors are specs whose rules apply to other features. They define cross-cutting constraints -- standards that multiple features must follow. Optionally, an anchor can reference an external source (a git repo, Figma file, or compliance document) to stay in sync with standards defined outside your project.

## Anchors

An anchor is a regular spec that defines rules other features must follow. Anyone on the team can create and edit them.

### Example

```markdown
# Anchor: api_rest_conventions

> Description: REST API conventions for all endpoints.
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

> Description: CRUD operations for user accounts.
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

Some rules define what code must **never** do. These are "FORBIDDEN patterns" -- and they're just rules with negative proofs.

### Example: security anchor with FORBIDDEN patterns

```markdown
# Anchor: security_input_handling

> Description: Input handling security standards. Prevents common injection attacks.
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

A FORBIDDEN pattern is a rule that says "X must not exist." The proof is a negative assertion -- verify the thing is absent:

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

The key insight: **there is no special FORBIDDEN mechanism in Purlin.** A FORBIDDEN pattern is just a rule with a proof that asserts absence. The proof system handles it identically to any other rule -- if the proof passes, the pattern is absent. If it fails, the violation is visible in `sync_status`.

For more on writing effective rules, proofs, and anchors, see the [Spec Quality Guide](../references/spec_quality_guide.md).

---

## Anchors with External References

An anchor can optionally reference an external source. When it does, Purlin can sync the anchor's content from that source. The anchor file remains locally editable -- but if local rules conflict with the external source, `purlin:anchor sync` flags the conflicts as PM action items (drift).

### Where they live

Anchors with external references live in `specs/_anchors/`:

```
specs/_anchors/
  design_brand.md          # Design system tokens
  api_v3_contract.md       # API contract from another team
  security_owasp.md        # Security requirements
```

### Format

Same 3-section format as regular anchors, plus source metadata:

```markdown
# Anchor: design_brand

> Description: Color tokens from the design system.
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

- **`> Source:`** -- git repo URL or Figma URL
- **`> Path:`** -- file path within the source repo
- **`> Pinned:`** -- commit SHA (git) or lastModified timestamp (Figma)

Full format: [references/formats/anchor_format.md](../references/formats/anchor_format.md)

### Syncing from external sources

**Git-sourced (all types):**

```
purlin:anchor sync api_v3_contract
```

Compares `> Pinned:` SHA to remote HEAD. If different, pulls the updated file and updates the SHA. If local rules conflict with the external source, the sync flags the conflicts as drift -- PM action items to resolve.

**Figma-sourced (design type):**

```
purlin:anchor sync figma figma.com/design/abc123/Brand-System
```

Reads the Figma file via MCP. Creates a thin anchor with one visual match rule per viewport and a screenshot comparison proof. Behavioral annotations from the design are documented as context but go into feature specs as rules, not the anchor. See [references/figma_extraction_criteria.md](../references/figma_extraction_criteria.md) for the full extraction criteria.

**CI staleness check:**

```
purlin:anchor sync --check-only
```

Compares all anchors' `> Pinned:` to remote sources without pulling. Fails if stale. Use in CI before `purlin:verify --audit`.

### Sync reliability

External sources can be unavailable (network failures, expired credentials, deleted repos). Handle this in CI:

```yaml
# GitHub Actions example
- name: Check anchor staleness
  run: |
    purlin:anchor sync --check-only || {
      echo "WARNING: anchor sync check failed -- external source may be unavailable"
      # Decide: fail the build, or warn and continue
      exit 1
    }
```

**Error handling guidance:**
- **Network failure** -- retry with backoff, then fail. Do not silently skip.
- **Expired credentials** -- fail with a clear message pointing to credential setup.
- **Deleted source repo** -- fail. The anchor's `> Source:` needs to be updated by a PM.
- **Source file moved** -- fail. Update the anchor's `> Path:` field.

### Local rules vs external reference conflicts

When you run `purlin:anchor sync`, the external source may have changed. If local rules conflict with the updated external content, the sync does not silently overwrite your local rules. Instead, it flags the conflicts as drift items:

```
purlin:anchor sync design_brand

Sync complete. 2 conflicts detected:

  RULE-1: Local says "#1a73e8", external says "#0d47a1"
  RULE-3: External added new rule "Secondary color is #424242"

These are PM action items. Run: purlin:drift pm
```

The PM reviews the drift report and decides whether to accept the external changes, keep the local rules, or merge them. This keeps the PM in control while ensuring external updates are never silently lost.

### The thin anchor model

Figma design anchors are thin -- one rule per viewport saying "match the design," one screenshot comparison proof per rule:

```markdown
# Anchor: design_feedback_modal

> Description: Visual design constraints for the feedback modal, sourced from Figma.
> Type: design
> Source: figma.com/design/ABC123/Feedback-Modal
> Visual-Reference: figma://ABC123/0-1
> Pinned: 2026-04-03T00:00:00Z

## What it does
Visual design constraints for the feedback modal, sourced from Figma.

## Rules
- RULE-1: Implementation must visually match the Figma design at the referenced node

## Proof
- PROOF-1 (RULE-1): Render component at same viewport size as Figma frame, capture screenshot, compare against Figma screenshot; verify visual match at design fidelity @e2e
```

The anchor doesn't extract granular CSS values. The LLM reads Figma directly during build for full fidelity. The screenshot comparison proof catches drift.

Behavioral annotations from the Figma design (interactions, validation, state changes) are documented in the anchor's "What it does" section but become rules in the feature spec that requires the anchor.

### Build time vs test time (Figma)

During `purlin:build`, the agent reads Figma directly via MCP for full visual context -- the visual reference IS the spec. During `purlin:verify`, the system renders the component, captures a screenshot, and compares it against the Figma reference. Build time is creative; test time is mechanical.

---

## Global Anchors

A global anchor is an anchor with `> Global: true` metadata. Its rules automatically apply to **every** non-anchor feature spec -- without needing `> Requires:`.

### When to use global anchors

Global anchors are for project-wide constraints that should apply everywhere -- security baselines, coding standards, or compliance requirements that no feature should be able to opt out of.

### Example

```markdown
# Anchor: security_no_eval

> Description: Prohibits use of eval() and equivalent dynamic code execution across the entire codebase.
> Type: security
> Source: git@github.com:acme/security-policies.git
> Path: standards/no-eval.md
> Pinned: a1b2c3d4
> Global: true

## What it does
Prohibits use of eval() and equivalent dynamic code execution across the entire codebase.

## Rules
- RULE-1: No eval() calls in source code
- RULE-2: No new Function() constructor with string arguments

## Proof
- PROOF-1 (RULE-1): Grep src/ for eval(); verify zero matches
- PROOF-2 (RULE-2): Grep src/ for new Function(; verify zero matches outside test files
```

### How global anchors appear in sync_status

Global anchor rules are included in every feature's coverage with a `(global)` label:

```
login: 5/7 rules proved
  RULE-1: PASS (own)
  RULE-2: PASS (own)
  RULE-3: NO PROOF (own)
  security_no_eval/RULE-1: PASS (global)
  security_no_eval/RULE-2: PASS (global)
```

Features do NOT need `> Requires:` for global anchors -- they apply automatically. If a feature explicitly lists a global anchor in `> Requires:`, its rules appear as `(required)` instead of `(global)` -- the coverage is the same either way.

### Writing proofs for global anchor rules

Use the **anchor's feature name** in the proof marker, not your own feature name:

```python
@pytest.mark.proof("security_no_eval", "PROOF-1", "RULE-1")
def test_no_eval_in_source():
    result = subprocess.run(["grep", "-rn", "eval(", "src/"], capture_output=True, text=True)
    assert result.stdout == "", f"Found eval() in:\n{result.stdout}"
```

---

## Using Anchors in Features

Anchors are referenced in `> Requires:`:

```markdown
# Feature: color_picker

> Description: Color selection component with palette and custom input.
> Requires: design_brand, design_component_library
> Scope: src/components/ColorPicker.js
```

`sync_status` includes all required rules in the feature's coverage report. Tests must prove both the feature's own rules and all required anchor rules.
