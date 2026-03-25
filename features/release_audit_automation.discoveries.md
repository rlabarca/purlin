# User Testing Discoveries: Release Audit Automation

### [BUG] M41: verify_zero_queue reads critic.json directly (Discovered: 2026-03-23)
- **Observed Behavior:** `verify_zero_queue` reads `critic.json` directly from the filesystem.
- **Expected Behavior:** Spec requires running `scan.sh` to obtain the critic queue state rather than reading the JSON file directly.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Replaced `load_feature_status()` to use scan.sh JSON output (via `status_data` parameter or by running scan.sh / reading cached `.purlin/cache/status.json`) instead of iterating `tests/*/critic.json` files directly.
- **Source:** Spec-code audit (deep mode). See release_audit_automation.impl.md for full context.

### [BUG] M42: Contradiction detection heuristic-only (Discovered: 2026-03-23)
- **Observed Behavior:** Contradiction detection relies entirely on heuristic text matching with no structural analysis of rule subjects and objects.
- **Expected Behavior:** Contradiction detection should include structural analysis of rule subjects and objects in addition to heuristic matching for more reliable detection.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Added structural section-level analysis via `_parse_sections()`, `_heading_similarity()`, and `_check_structural_contradictions()` in `instruction_audit.py`. The structural analyzer matches override sections to base sections by heading similarity, then checks imperative rules within matched sections for negation patterns. Findings from both approaches are deduplicated.
- **Source:** Spec-code audit (deep mode). See release_audit_automation.impl.md for full context.
