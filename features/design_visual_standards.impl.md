# Implementation Notes: Common Design Standards

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (none active) | | | |

*   Consumer projects MAY override these standards in their own `design_*.md` anchor node.
*   The standalone logo SVG (`assets/purlin-logo.svg`) uses dark-theme hex defaults. When embedded inline in tool HTML, the SVG elements use CSS classes that respond to the `data-theme` attribute for theme-responsive colors.
*   The FOUC prevention script must be placed before any `<link>` stylesheet tags to ensure the correct theme is applied before CSS renders.
*   **Structured FORBIDDEN Patterns (Section 2.7):** `policy_check.py` now parses the `### FORBIDDEN Patterns` section format with `**Grepable pattern:**` and `**Scan scope:**` sub-fields, in addition to inline `FORBIDDEN:` markers. Scoped patterns are scanned against their declared file glob (via `resolve_scan_scope()`), while unscoped patterns use discovered implementation files. Brace expansion (`{py,html,css,js}`) is handled manually since Python's `glob` doesn't support it natively.

### Audit Finding -- 2026-03-23

[DISCOVERY] 246 FORBIDDEN pattern violations in shared CDD codebase. Acknowledged. **RESOLVED:** CDD Dashboard (serve.py) and all affected CDD features deleted in CDD/Critic removal. Remaining violations in graph.py (16 hardcoded hex colors in SVG generation) are the only active issue.

**Source:** /pl-spec-code-audit --deep

**Severity:** LOW (reduced from HIGH — bulk of violations in deleted code)

**Remaining:**

-   scripts/mcp/graph_engine.py lines 250-265: 16 hardcoded hex colors in SVG generation
