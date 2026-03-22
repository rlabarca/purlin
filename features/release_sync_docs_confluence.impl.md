# Implementation Notes: Sync Docs to Confluence

### Test Quality Audit
- Rubric: 6/6 PASS
- Tests: 40 total, 40 passed
- AP scan: clean
- Date: 2026-03-22

### Implementation Decisions

**[CLARIFICATION]** The `docs/` directory currently has a flat structure (no subdirectories),
but the spec defines a subdirectory convention (guides/, reference/). The utility functions
(`derive_section_title`, `derive_page_title`) are implemented per spec and ready for when
subdirectories are introduced. The tests validate the mapping logic independent of directory
structure. (Severity: INFO)

**[CLARIFICATION]** The `confluence_upload_images.py` script lives in `dev/` per spec Section
2.3, which explicitly states it is "specific to the Purlin repository's release process and
is not needed by consumer projects." This exempts it from the submodule safety checklist.
(Severity: INFO)

**[CLARIFICATION]** For interactive-only scenarios (MCP setup, page deletion policy, scope
constraints), tests verify behavior through the `resolve_checklist()` module rather than
reading raw JSON files. This ensures the step is correctly registered and resolved by the
release infrastructure. (Severity: INFO)
