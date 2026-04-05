# Anchors Guide

## What You Need to Know

Anchors are shared rules that apply to multiple features. Put a spec in `specs/_anchors/` and it becomes an anchor. Features reference it with `> Requires:`, and its rules become part of their coverage.

```
purlin:anchor create <name>                     # Create a local anchor
purlin:anchor add-figma <figma-url>             # Create from Figma design
purlin:anchor sync <name>                       # Pull latest from external source
```

**Key concepts:**
- Any spec in `specs/_anchors/` is an anchor — the directory is what makes it one
- Features must prove anchor rules to reach PASSING status
- Global anchors (`> Global: true`) auto-apply to all features
- Anchors can sync from external sources (git repos, Figma files)

---

## What Is an Anchor

An anchor is a regular spec that lives in `specs/_anchors/`. The directory is what makes it an anchor, not the file name. Anyone on the team can create and edit them.

```
specs/_anchors/
  rest_conventions.md
  input_handling.md
  brand_colors.md
  feedback_modal.md
```

Name anchors whatever makes sense for your team. The optional `> Type:` metadata field (`design`, `api`, `security`, etc.) categorizes them in the dashboard, but it's not enforced.

### Example

```markdown
# Anchor: rest_conventions

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

### Using anchors in features

Feature specs reference anchors in `> Requires:`:

```markdown
# Feature: user_api

> Description: CRUD operations for user accounts.
> Requires: rest_conventions
> Scope: src/api/users.js
```

`purlin:status` includes the anchor's rules in the feature's coverage report. Tests for `user_api` must prove both its own rules and `rest_conventions` rules.

---

## Forbidden Patterns

Some rules define what code must **never** do. These are just rules with negative proofs -- there is no special FORBIDDEN mechanism in Purlin.

### Example

```markdown
# Anchor: input_handling

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

### Writing FORBIDDEN proofs

A FORBIDDEN pattern is a rule that says "X must not exist." The proof asserts absence:

```python
@pytest.mark.proof("input_handling", "PROOF-1", "RULE-1")
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
@pytest.mark.proof("input_handling", "PROOF-3", "RULE-3")
def test_xss_prevention():
    """FORBIDDEN: unescaped user input in HTML"""
    response = render_template("profile", name="<script>alert(1)</script>")
    assert "<script>" not in response
    assert "&lt;script&gt;" in response
```

If the proof passes, the pattern is absent. If it fails, the violation is visible in `purlin:status`. For more on writing effective rules and proofs, see the [Spec Quality Guide](../references/spec_quality_guide.md).

---

## Anchor Scope: Required vs Global

Anchors apply to features in two ways:

### Required anchors (opt-in)

Features explicitly reference the anchor via `> Requires:`. Only features that opt in must prove the anchor's rules.

```markdown
# Feature: user_api

> Description: CRUD operations for user accounts.
> Requires: rest_conventions
> Scope: src/api/users.js
```

In `purlin:status`, required anchor rules appear with a `(required)` label:

```
user_api: 3/5 rules proved
  RULE-1: PASS (own)
  RULE-2: NO PROOF (own)
  rest_conventions/RULE-1: PASS (required)
  rest_conventions/RULE-2: PASS (required)
  rest_conventions/RULE-3: NO PROOF (required)
```

### Global anchors (automatic)

Add `> Global: true` to make an anchor's rules apply to **every** non-anchor feature spec -- without needing `> Requires:`. Use this for project-wide constraints that no feature should opt out of: security baselines, coding standards, compliance requirements.

```markdown
# Anchor: no_eval

> Description: Prohibits eval() and dynamic code execution across the entire codebase.
> Type: security
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

In `purlin:status`, global anchor rules appear with a `(global)` label:

```
login: 5/7 rules proved
  RULE-1: PASS (own)
  RULE-2: PASS (own)
  RULE-3: NO PROOF (own)
  no_eval/RULE-1: PASS (global)
  no_eval/RULE-2: PASS (global)
```

### Writing proofs for anchor rules

Use the **anchor's name** in the proof marker, not the feature name:

```python
@pytest.mark.proof("no_eval", "PROOF-1", "RULE-1")
def test_no_eval_in_source():
    result = subprocess.run(["grep", "-rn", "eval(", "src/"], capture_output=True, text=True)
    assert result.stdout == "", f"Found eval() in:\n{result.stdout}"
```

---

## External References

An anchor can optionally reference an external source (git repo, Figma file, compliance document). Purlin can sync the anchor's content from that source. The anchor file remains locally editable -- if local rules conflict with the external source, `purlin:anchor sync` flags the conflicts as drift.

### Format

Same 3-section format as regular anchors, plus source metadata:

```markdown
# Anchor: brand_colors

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
- **`> Path:`** -- file path within the source repo (git only)
- **`> Pinned:`** -- commit SHA (git) or lastModified timestamp (Figma)

Full format: [references/formats/anchor_format.md](../references/formats/anchor_format.md)

### Syncing

**Git-sourced:**

```
purlin:anchor sync brand_colors
```

Compares `> Pinned:` SHA to remote HEAD. If different, pulls the updated file and updates the SHA.

**Figma-sourced:**

```
purlin:anchor sync figma figma.com/design/abc123/Brand-System
```

Reads the Figma file via MCP. Creates a thin anchor with one visual match rule per viewport and a screenshot comparison proof. Behavioral annotations from the design are documented as context but go into feature specs as rules, not the anchor. See [references/figma_extraction_criteria.md](../references/figma_extraction_criteria.md) for the full extraction criteria.

**CI staleness check:**

```
purlin:anchor sync --check-only
```

Compares all anchors' `> Pinned:` to remote sources without pulling. Fails if stale. Use in CI before `purlin:verify --audit`.

### Conflict resolution

When `purlin:anchor sync` detects that the external source has changed and local rules conflict, it flags the conflicts as drift items instead of silently overwriting:

```
purlin:anchor sync brand_colors

Sync complete. 2 conflicts detected:

  RULE-1: Local says "#1a73e8", external says "#0d47a1"
  RULE-3: External added new rule "Secondary color is #424242"

These are PM action items. Run: purlin:drift pm
```

The PM reviews and decides whether to accept the external changes, keep local rules, or merge.

### Sync reliability

External sources can be unavailable. Handle this in CI:

```yaml
- name: Check anchor staleness
  run: |
    purlin:anchor sync --check-only || {
      echo "WARNING: anchor sync check failed -- external source may be unavailable"
      exit 1
    }
```

- **Network failure** -- retry with backoff, then fail. Do not silently skip.
- **Expired credentials** -- fail with a clear message pointing to credential setup.
- **Deleted source repo** -- fail. The anchor's `> Source:` needs to be updated.
- **Source file moved** -- fail. Update the anchor's `> Path:` field.

### Figma anchors

Figma design anchors are thin -- one rule per viewport, one screenshot comparison proof:

```markdown
# Anchor: feedback_modal

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

The anchor doesn't extract granular CSS values. During `purlin:build`, the agent reads Figma directly via MCP for full visual context -- the visual reference IS the spec. During `purlin:verify`, the system renders the component, captures a screenshot, and compares it against the Figma reference. Build time is creative; test time is mechanical.

Behavioral annotations from the Figma design (interactions, validation, state changes) are documented in the anchor's "What it does" section but become rules in the feature spec that requires the anchor.
