---
name: qa-report
description: This skill activates QA mode. If another mode is active, confirm switch first
---

**Purlin mode: QA**

Purlin agent: This skill activates QA mode. If another mode is active, confirm switch first.

---

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.

---

Run `${CLAUDE_PLUGIN_ROOT}/scripts/cdd/scan.sh --only features,discoveries,plan` and read the JSON output to get feature status. Then produce a QA-focused structured summary:

**Output format:**

```
## QA Status Report

### TESTING Features (N)
| Feature | Manual Items | Scope | Open Discoveries |
|---------|-------------|-------|-----------------|
| <label> | Nm manual | full | 0 |
| <label> | builder-verified | -- | 1 BUG |

### Open Discoveries (N)
**BUG (N):** <feature>: <title> [OPEN]
**SPEC_DISPUTE (N):** <feature>: <title> [OPEN]

### Completion Blockers
- <feature>: 1 open BUG, 2 unverified scenarios
- <feature>: phase-gated (Phase 2 PENDING)

### Effort Estimate
Total: N items across M features
```

**Section details:**

1.  **Features in TESTING:** List each with manual scenario count, verification scope (full/targeted/cosmetic/dependency-only), and open discovery count.
2.  **Open Discoveries:** All OPEN and SPEC_UPDATED discoveries grouped by type (BUG / DISCOVERY / INTENT_DRIFT / SPEC_DISPUTE). Include feature name, title, and status.
3.  **Completion Blockers:** Per TESTING feature, what blocks `[Complete]`: open discoveries, unverified scenarios, pending delivery phases.
4.  **Delivery Plan Context:** If `.purlin/delivery_plan.md` exists, classify features as fully delivered vs. phase-gated.
5.  **Effort Estimate:** Total manual items across all TESTING features after scope filtering.
