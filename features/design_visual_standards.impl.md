# Implementation Notes: Common Design Standards

*   Consumer projects MAY override these standards in their own `design_*.md` anchor node.
*   The standalone logo SVG (`assets/purlin-logo.svg`) uses dark-theme hex defaults. When embedded inline in tool HTML, the SVG elements use CSS classes that respond to the `data-theme` attribute for theme-responsive colors.
*   The FOUC prevention script must be placed before any `<link>` stylesheet tags to ensure the correct theme is applied before CSS renders.
*   **Structured FORBIDDEN Patterns (Section 2.7):** `policy_check.py` now parses the `### FORBIDDEN Patterns` section format with `**Grepable pattern:**` and `**Scan scope:**` sub-fields, in addition to inline `FORBIDDEN:` markers. Scoped patterns are scanned against their declared file glob (via `resolve_scan_scope()`), while unscoped patterns use discovered implementation files. Brace expansion (`{py,html,css,js}`) is handled manually since Python's `glob` doesn't support it natively.
