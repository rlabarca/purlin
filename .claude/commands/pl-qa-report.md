**Purlin command owner: QA**
**Purlin mode: QA**

Legacy agents: If you are not the QA, respond: "This is a QA command. Ask your QA agent to run /pl-qa-report instead." and stop.
Purlin agent: This skill activates QA mode. If another mode is active, confirm switch first.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

Run `${TOOLS_ROOT}/cdd/scan.sh` and read the JSON output to get feature status. Then produce a QA-focused structured summary:

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
