# Architectural Policy: Critic Coordination Engine

> Label: "Policy: Critic Coordination Engine"
> Category: "Quality Assurance"

## 1. Purpose
This policy defines the invariants and constraints governing the Critic -- the project coordination engine that validates specification-implementation quality AND generates role-specific action items for each agent. The Critic is the single source of truth for what each agent should work on next.

## 2. Invariants

### 2.1 Dual-Gate Principle
Every feature MUST be evaluable through two independent gates:

*   **Spec Gate (Pre-Implementation):** Validates that the feature specification itself is structurally complete, properly anchored to architectural policies, and contains well-formed Gherkin scenarios. This gate can run before any code exists.
*   **Implementation Gate (Post-Implementation):** Validates that the implementation aligns with the specification through traceability checks, policy adherence, builder decision audit, and (optionally) LLM-based logic drift detection.

Neither gate alone is sufficient. A feature that passes the Spec Gate but fails the Implementation Gate has a code problem. A feature that passes the Implementation Gate but fails the Spec Gate has a specification problem.

### 2.2 Traceability Mandate
Every automated Gherkin scenario in a feature file MUST be traceable to at least one automated test function. Traceability is established through keyword matching between scenario titles and test function names/bodies.

*   The traceability engine uses a keyword extraction and matching approach (2+ keyword threshold).
*   Manual scenarios are EXEMPT from traceability but are flagged if automated tests exist for them.
*   Explicit `traceability_overrides` in Implementation Notes allow manual mapping when keyword matching is insufficient.

### 2.3 Builder Decision Transparency
The Builder MUST classify every non-trivial implementation decision using structured tags in the `## Implementation Notes` section:

| Tag | Severity | Meaning |
|-----|----------|---------|
| `[CLARIFICATION]` | INFO | Interpreted ambiguous spec language. The spec was unclear; Builder chose a reasonable interpretation. |
| `[AUTONOMOUS]` | WARN | Spec was silent on this topic. Builder made a judgment call to fill the gap. |
| `[DEVIATION]` | HIGH | Intentionally diverged from what the spec says. Requires Architect acknowledgment. |
| `[DISCOVERY]` | HIGH | Found an unstated requirement during implementation. Requires Architect acknowledgment. |
| `[INFEASIBLE]` | CRITICAL | Feature cannot be implemented as specified. Builder has halted work. Requires Architect to revise the spec. |

**Constraint:** A feature with unacknowledged `[DEVIATION]` or `[DISCOVERY]` entries generates HIGH-priority Architect action items in the Critic report. A feature with `[INFEASIBLE]` generates a CRITICAL-priority Architect action item and the Builder skips the feature entirely.

### 2.4 User Testing Feedback Loop
The QA Agent records findings during manual verification using three discovery types:

| Type | Meaning |
|------|---------|
| `[BUG]` | Behavior contradicts an existing scenario. |
| `[DISCOVERY]` | Behavior exists but no scenario covers it. |
| `[INTENT_DRIFT]` | Behavior matches the spec literally but misses the actual intent. |
| `[SPEC_DISPUTE]` | User disagrees with a scenario's expected behavior. The spec itself is wrong or undesirable. |

**Constraint:** Discoveries follow a lifecycle: `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`. OPEN discoveries generate role-specific action items in the Critic report (BUGs route to Builder; DISCOVERYs, INTENT_DRIFTs, and SPEC_DISPUTEs route to Architect). A SPEC_DISPUTE **suspends** the disputed scenario -- QA skips it until the Architect resolves the dispute.

### 2.5 Policy Adherence
Architectural policy files (`arch_*.md`) MAY define `FORBIDDEN:` patterns -- literal strings or regex patterns that MUST NOT appear in the implementation code of features anchored to that policy.

*   The Critic tool scans implementation files for FORBIDDEN pattern violations.
*   Any violation produces a FAIL on the Implementation Gate.

### 2.6 Agent Startup Integration
Every agent (Architect, Builder, QA) MUST run the Critic at session start. The Critic report provides each agent with its role-specific action items, ensuring immediate alignment with project health and priorities.

### 2.7 Role-Specific Action Items
The Critic MUST generate imperative action items categorized by role (Architect, Builder, QA). Action items are derived from existing analysis gates (spec gate, implementation gate, user testing audit) and are prioritized by severity. Each action item identifies the target feature and the specific gap to address.

### 2.8 CDD Decoupling
The Critic is an agent-facing coordination tool. CDD is a lightweight state display for human consumption. CDD shows what IS (per-role status). The Critic shows what SHOULD BE DONE (role-specific action items). CDD does NOT run the Critic. CDD reads the `role_status` object from on-disk `critic.json` files to display Architect, Builder, and QA columns on the dashboard and in the `/status.json` API. CDD does NOT compute role status itself; it consumes the Critic's pre-computed output.

## 3. Configuration

The following keys in `.agentic_devops/config.json` govern Critic behavior:

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `critic_llm_model` | string | `claude-sonnet-4-20250514` | Model used for logic drift detection. |
| `critic_llm_enabled` | boolean | `false` | Whether the LLM-based logic drift engine is active. |
| `critic_gate_blocking` | boolean | `false` | **Deprecated (no-op).** Retained for backward compatibility. Status transitions are not gated by critic results. |

## 4. Output Contract
The Critic tool MUST produce:

*   **Per-feature:** `tests/<feature_name>/critic.json` with `spec_gate`, `implementation_gate`, `user_testing`, `action_items`, and `role_status` sections.
*   **Aggregate:** `CRITIC_REPORT.md` at the project root summarizing all features.

## Implementation Notes
*   This policy governs buildable tooling constraints (the Critic tool itself), not process rules. It is valid under the Feature Scope Restriction mandate.
*   The `critic_gate_blocking` flag is deprecated as a no-op. The coordination engine model replaces blocking gates with advisory action items per role. The config key is retained for backward compatibility with existing `.agentic_devops/config.json` files.
*   FORBIDDEN patterns are optional. Not all architectural policies need to define them.
*   The CDD decoupling (Invariant 2.8) means the CDD dashboard shows role-based columns (Architect, Builder, QA) derived from `role_status` in on-disk `critic.json` files. CDD does not compute these statuses; it reads pre-computed values from the Critic's output.
