# User Testing Discoveries: CDD Status Monitor

### [BUG] H3: CDD_PORT env var priority chain (Discovered: 2026-03-23)
- **Observed Behavior:** serve.py never reads the CDD_PORT environment variable; start.sh passes --port directly. The spec-defined priority chain (CDD_PORT env var > config > default) is not implemented.
- **Expected Behavior:** Port selection should follow the priority chain: CDD_PORT environment variable takes highest priority, then config file value, then default port.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See cdd_status_monitor.impl.md for full context.

### [BUG] M6: delivery_plan_gating fully_delivered_features (Discovered: 2026-03-23)
- **Observed Behavior:** The `fully_delivered_features` field is always an empty array; the code never computes which features are eligible.
- **Expected Behavior:** `fully_delivered_features` should be computed by identifying features that have completed all delivery phases.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See cdd_status_monitor.impl.md for full context.
