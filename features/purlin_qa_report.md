# Feature: QA Status Report

> Label: "Agent Skills: QA: purlin:qa-report QA Status Report"
> Category: "Agent Skills: QA"

[TODO]

## 1. Overview

The QA summary report skill that produces a structured overview of verification state. Shows TESTING features with manual item counts and scopes, open discoveries grouped by type, completion blockers per feature, delivery plan context, and effort estimates.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by QA mode.
- Non-QA agents MUST receive: `"This is a QA command. Switch to QA mode with purlin:mode qa."`

### 2.2 Data Source

- Run the MCP `purlin_scan` tool (with `only: "features,discoveries,plan"`) and read the JSON result to get feature status, discovery state, and delivery plan context.

### 2.3 Output Format

The report MUST use this table-based layout:

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

### 2.4 Section Details

1. **TESTING Features:** List each with manual scenario count, verification scope (`full`/`targeted`/`cosmetic`/`dependency-only`), and open discovery count.
2. **Open Discoveries:** All OPEN and SPEC_UPDATED discoveries grouped by type (BUG / DISCOVERY / INTENT_DRIFT / SPEC_DISPUTE). Include feature name, title, and status.
3. **Completion Blockers:** Per TESTING feature, what blocks `[Complete]`: open discoveries, unverified scenarios, pending delivery phases.
4. **Delivery Plan Context:** If `.purlin/delivery_plan.md` exists, classify features as fully delivered vs. phase-gated.
5. **Effort Estimate:** Total manual items across all TESTING features after scope filtering.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-QA invocation

    Given an Engineer agent session
    When the agent invokes purlin:qa-report
    Then the command responds with a redirect message

#### Scenario: Report shows TESTING features with counts

    Given 3 features are in TESTING state
    When purlin:qa-report is invoked
    Then all 3 features are listed with manual item counts and scopes

#### Scenario: Open discoveries grouped by type

    Given 2 BUG and 1 SPEC_DISPUTE discoveries are open
    When purlin:qa-report is invoked
    Then the Open Discoveries section shows BUG (2) and SPEC_DISPUTE (1)

#### Scenario: Delivery plan gating shown

    Given feature_a is phase-gated in Phase 2
    When purlin:qa-report is invoked
    Then feature_a is listed as phase-gated in Completion Blockers

### QA Scenarios

None.
