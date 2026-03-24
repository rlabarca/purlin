# User Testing Discoveries: Release Audit Automation

### [BUG] M41: verify_zero_queue reads critic.json directly (Discovered: 2026-03-23)
- **Observed Behavior:** `verify_zero_queue` reads `critic.json` directly from the filesystem.
- **Expected Behavior:** Spec requires running `status.sh` to obtain the critic queue state rather than reading the JSON file directly.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See release_audit_automation.impl.md for full context.

### [DISCOVERY] M42: Contradiction detection heuristic-only (Discovered: 2026-03-23)
- **Observed Behavior:** Contradiction detection relies entirely on heuristic text matching with no structural analysis of rule subjects and objects.
- **Expected Behavior:** Contradiction detection should include structural analysis of rule subjects and objects in addition to heuristic matching for more reliable detection.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See release_audit_automation.impl.md for full context.
