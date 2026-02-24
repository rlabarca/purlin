# Implementation Notes: Critic Coordination Engine

*   This policy governs buildable tooling constraints (the Critic tool itself), not process rules. It is valid under the Feature Scope Restriction mandate.
*   The `critic_gate_blocking` flag is deprecated as a no-op. The coordination engine model replaces blocking gates with advisory action items per role. The config key is retained for backward compatibility with existing `.purlin/config.json` files.
*   FORBIDDEN patterns are optional. Not all anchor nodes need to define them.
*   The CDD decoupling (Invariant 2.10) means the CDD dashboard shows role-based columns (Architect, Builder, QA) derived from `role_status` in on-disk `critic.json` files. CDD does not compute these statuses; it reads pre-computed values from the Critic's output.
*   **[CLARIFICATION]** `Action Required: Architect` BUG routing override (Section 2.4): The `parse_discovery_entries()` function already parsed the `action_required` field but the routing logic in `generate_action_items()` did not use it. Fixed by adding a conditional check on the field value before appending to `architect_items` vs `builder_items`. When `action_required` is "architect" (case-insensitive), the BUG routes to Architect with a description prefix "Fix instruction-level bug". Default routing to Builder is unchanged. (Severity: INFO)
