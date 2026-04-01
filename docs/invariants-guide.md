# Invariants Guide

Invariants are read-only specs that define constraints from external sources (design systems, compliance policies, API contracts). They live in `specs/_invariants/` and are protected by a gate hook.

## File Location

```
specs/_invariants/
  i_design_colors.md      # Design system color tokens
  i_api_v2_contract.md    # API contract from external team
  i_compliance_gdpr.md    # Compliance requirements
```

All invariant files use the `i_` prefix.

## Format

Invariants use the same 3-section format as regular specs, plus a `Source:` metadata line:

```markdown
# Invariant: i_design_colors

> Source: figma://file/abc123/Design-System
> Scope: src/styles/, src/components/

## What it does
Color tokens from the design system. All UI components must use these values.

## Rules
- RULE-1: Primary color is #1a73e8
- RULE-2: Error color is #d93025
- RULE-3: Background uses $surface-light token

## Proof
- PROOF-1 (RULE-1): CSS variable --color-primary equals #1a73e8
- PROOF-2 (RULE-2): CSS variable --color-error equals #d93025
- PROOF-3 (RULE-3): Body background uses $surface-light
```

Full format reference: `references/formats/invariant_format.md`

## Write Protection

The gate hook (`scripts/gate.sh`) blocks all writes to `specs/_invariants/i_*` files. This prevents accidental edits — invariants come from external sources, not from the codebase.

If you try to edit an invariant file, you'll see:

```
BLOCKED: Invariant files are read-only. Use purlin:invariant sync to update from the external source.
```

## Updating Invariants

Use `purlin:invariant sync` to pull updates from the external source. This temporarily unlocks the file via a bypass lock in `.purlin/runtime/invariant_write_lock`, writes the update, then removes the lock.

```
purlin:invariant sync i_design_colors
```

The bypass lock is file-scoped — it only unlocks the specific invariant being synced.

## Using Invariants in Feature Specs

Feature specs reference invariants via the `Requires:` metadata line:

```markdown
# Feature: color_picker

> Requires: i_design_colors
> Scope: src/components/ColorPicker.js

## What it does
...
```

When a feature requires an invariant, `sync_status` includes the invariant's rules in the feature's coverage report. Tests for the feature must prove both the feature's own rules and any required invariant rules.

## Session Cleanup

The session start hook (`scripts/session-start.sh`) clears any stale bypass locks from `.purlin/runtime/`. This prevents a lock from persisting across sessions if a sync was interrupted.
