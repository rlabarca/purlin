# Implementation Notes: Common Design Standards

*   Consumer projects MAY override these standards in their own `design_*.md` anchor node.
*   The standalone logo SVG (`assets/purlin-logo.svg`) uses dark-theme hex defaults. When embedded inline in tool HTML, the SVG elements use CSS classes that respond to the `data-theme` attribute for theme-responsive colors.
*   The FOUC prevention script must be placed before any `<link>` stylesheet tags to ensure the correct theme is applied before CSS renders.
*   **Structured FORBIDDEN Patterns (Section 2.7):** `policy_check.py` now parses the `### FORBIDDEN Patterns` section format with `**Grepable pattern:**` and `**Scan scope:**` sub-fields, in addition to inline `FORBIDDEN:` markers. Scoped patterns are scanned against their declared file glob (via `resolve_scan_scope()`), while unscoped patterns use discovered implementation files. Brace expansion (`{py,html,css,js}`) is handled manually since Python's `glob` doesn't support it natively.

### Audit Finding -- 2026-03-23

[DISCOVERY] 246 FORBIDDEN pattern violations in shared CDD codebase

**Source:** /pl-spec-code-audit --deep

**Severity:** HIGH

**Details:**

-   tools/cdd/graph.py lines 250-265: 16 hardcoded hex colors in SVG generation
-   tools/cdd/serve.py lines 2044-5597: inline style= attributes with hex color/background values
-   tools/cdd/test_cdd.py, tools/test_pl_design_audit.py: hex colors in test fixtures

**Affected features:** cdd_agent_configuration, cdd_branch_collab, cdd_modal_base, cdd_qa_effort_display, cdd_spec_map, cdd_status_monitor, collab_whats_different, release_checklist_ui

**Suggested fix:** Replace hardcoded hex values with var(--purlin-*) CSS custom properties per Section 2.7. Move inline style= attributes to CSS classes. Test fixtures may use hex values if testing the FORBIDDEN detection itself.
