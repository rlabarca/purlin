# Output Standards

> Referenced by all Purlin skill instructions. Defines the visual language for consistent, scannable output across every skill and mode.

## Principles

1. **Structure over prose.** Tables, lists, and key-value blocks beat paragraphs. If data has properties, use a table.
2. **Symbols over words.** `✓ PASSED` scans faster than "The test passed successfully."
3. **Weight creates hierarchy.** Bold headers, indented items, dot leaders, and summary footers — no colors available, so use density and typography.
4. **Predictable framing.** Every skill opens and closes the same way. Users learn the pattern once.

## Symbol Reference

| Symbol | Meaning | Use for |
|--------|---------|---------|
| `✓` | Success / passed | Test results, verification, completed items |
| `✗` | Failed / error | Test failures, blocking issues |
| `⊘` | Skipped / blocked | Skipped tests, blocked prerequisites |
| `⚠` | Warning | Non-blocking issues, deprecation notices |
| `▸` | Active / current | Current step, in-progress item |
| `●` | Active item | Selected option, active mode |
| `○` | Pending / inactive | Queued items, unselected options |
| `━` | Heavy rule | Skill banners and summary footers |
| `·` | Inline separator | Summary stats: `3 passed · 1 failed · 0 skipped` |

## Skill Banner

Every skill starts with a banner. The banner is the skill name between heavy rules:

```
━━━ purlin:verify ━━━━━━━━━━━━━━━━━━━━━
```

Format: `━━━ ` + skill name + ` ` + `━` repeated to fill ~40 chars total.

If the skill has a context badge (mode, branch, feature), place it on the next line:

```
━━━ purlin:verify ━━━━━━━━━━━━━━━━━━━━━
QA(dev/0.8.6) | purlin
```

## Context Badge

Format: `Mode(branch) | context`

```
Eng(dev/0.8.6) | purlin
PM(feature-xyz) | purlin
QA(main) | purlin_verify — Phase 2
```

Components:
- **Mode**: `Eng`, `PM`, `QA` (abbreviated)
- **Branch**: current branch or worktree label (e.g., `W1`)
- **Context**: project name, feature name, or step description
- **Separator**: ` | ` between mode/branch and context, ` — ` before step

## Progress Steps

For multi-step protocols, print numbered step markers:

```
[1/4] Scanning features...
[2/4] Checking prerequisites...
[3/4] Running tests...
      ✓ test_build
      ✗ test_merge — assertion failed
      ⊘ test_fixture — prerequisite missing
[4/4] Writing results...
```

Rules:
- Format: `[N/total] Description...`
- Indent sub-results under the step with 6 spaces
- Use status symbols for sub-items

## Result Lists

### With dot leaders (short lists, inline status)

```
  ✓ purlin_build ............. PASSED
  ✗ purlin_merge ............. FAILED — circular dep
  ⊘ file_classification ...... SKIPPED
```

Rules:
- 2-space indent
- Symbol + space + name + space + dots + space + STATUS
- Dot leaders connect the name to the status for scannability
- Failure detail after ` — `

### As tables (structured data, multiple properties)

```markdown
| Feature | Status | Owner | Action |
|---------|--------|-------|--------|
| purlin_build | TODO | Engineer | needs impl |
| purlin_merge | TODO | Engineer | needs impl |
| file_classification | TESTING | QA | needs verification |
```

Use tables when items have 3+ properties. Use dot-leader lists when items have just name + status.

## Grouped Lists

Group items under bold headers. Use status symbols for items:

```
**TESTING** (3)
  ▸ file_classification
  ▸ purlin_resume
  ▸ purlin_worktree_identity

**TODO** (35)
  ○ purlin_build
  ○ purlin_merge
  ○ purlin_complete
  ... and 32 more
```

Rules:
- Bold header with count in parens
- 2-space indent for items
- `▸` for active/in-progress group, `○` for pending group, `✓` for completed group
- Truncate long lists with `... and N more`

## Findings / Issues

Numbered findings let users reference specific items ("fix I1 and I3"):

```markdown
| ID | Severity | Feature | Issue |
|----|----------|---------|-------|
| I1 | ERROR | purlin_build | circular dep: A → B → A |
| I2 | WARN | purlin_merge | companion references stale function |
| I3 | INFO | purlin_sync_system | spec modified after completion |
```

Severity levels:
- **ERROR** — blocks progress, must fix
- **WARN** — should fix, non-blocking
- **INFO** — informational, no action required

When presenting fixes: `Enter IDs to fix (e.g., I1 I3), 'all', or 'none':`

## Decision Prompts

### Multiple choice

```
Choose: (1) targeted  (2) full  (3) regression-only
```

Format: `Choose:` + numbered options in parens, space-separated.

### Yes/No

```
Uncommitted changes in 3 files. Commit first? [y/n]
```

Format: question + ` [y/n]`

### Free input

```
Enter the new version number (suggest: v0.8.6):
```

Format: instruction + suggestion in parens.

## Summary Footer

Close every skill with a summary footer. The footer mirrors the banner weight:

```
━━━ 5 passed · 1 failed · 0 skipped
```

Format: `━━━ ` + stats separated by ` · `

### Key-Value Summary (for richer context)

```
━━━ Results ━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scanned:      42 features
Passed:       38
Failed:       3
Skipped:      1
Duration:     12s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Rules:
- Labels left-aligned, values right-aligned after colon + spaces
- Bookended by heavy rules
- Use for end-of-skill summaries with 3+ metrics

## Recovery Summary

The `purlin:resume` recovery summary uses key-value format:

```
Context Restored
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mode:           Engineer
Branch:         dev/0.8.6
Checkpoint:     found — resuming from 2026-03-28T20:53:16Z

Resume Point:   purlin_verify — Phase 2: run scenarios
Next Steps:
  1. Run remaining scenarios
  2. Record discoveries
  3. Update regression JSON

Action Items:   12 items from scan results
Uncommitted:    none
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Menus

Interactive menus use numbered items with aligned descriptions:

```
━━━ purlin:toolbox ━━━━━━━━━━━━━━━━━━━━

  1. List all tools          purlin:toolbox list
  2. Run tool(s)             purlin:toolbox run <name>
  3. Create a new tool       purlin:toolbox create
  4. Add a community tool    purlin:toolbox add <url>
  5. Manage tools            purlin:toolbox edit|copy|delete
  6. Share a tool            purlin:toolbox push <tool>

Enter a number or command:
```

Rules:
- 2-space indent
- Number + period + 2 spaces + label + spaces + command hint (right-aligned)
- Prompt on its own line after a blank line

## Warnings and Errors

### Inline warning

```
⚠ Tag v0.8.6 already exists. Re-tagging will move it to HEAD.
```

### Blocking error

```
✗ Cannot proceed: 3 features have unresolved circular dependencies.
  Run purlin:spec-code-audit to identify and fix them.
```

Rules:
- Symbol first (`⚠` or `✗`)
- One-line description
- Recovery suggestion indented on the next line

## Anti-Patterns

**Don't do these:**

- Prose paragraphs for structured results — use tables or dot-leader lists
- Bare status words without symbols — `PASSED` alone is less scannable than `✓ PASSED`
- Inconsistent banner widths — always ~40 chars
- Multiple blank lines between sections — one blank line maximum
- Trailing summaries that restate what was just shown — the summary footer is the summary
- Mixing `---` and `━━━` — use `━━━` for skill framing, `---` only in markdown documents
