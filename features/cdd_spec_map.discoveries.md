# User Testing Discoveries: CDD Spec Map

### [BUG] H5: Hardcoded hex colors in Mermaid classDef (Discovered: 2026-03-23)
- **Observed Behavior:** graph.py lines 250-265 use hardcoded hex color literals in Mermaid classDef declarations.
- **Expected Behavior:** Hex color literals are FORBIDDEN by design_visual_standards. Colors must be sourced from the design token system, not hardcoded as hex values.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (deep mode). See cdd_spec_map.impl.md for full context.
