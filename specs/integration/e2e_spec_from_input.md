# Feature: e2e_spec_from_input

> Scope: skills/spec/SKILL.md, scripts/mcp/purlin_server.py
> Stack: python3 (sync_status, regex parsing), shell/bash
> Description: End-to-end validation that specs generated from the four documented input
> scenarios (plain description, PRD, vague description, customer feedback) produce
> structurally correct output that sync_status can parse. Each scenario exercises
> different aspects of the spec skill: explicit rules, bulk extraction, assumption
> tagging, and complaint-to-rule translation.

## Rules

- RULE-1: A spec generated from a plain description contains sequentially numbered RULE-N lines starting at RULE-1 with no gaps
- RULE-2: A spec generated from a plain description contains PROOF-N (RULE-N) lines where every rule has at least one proof
- RULE-3: A spec generated from a plain description contains no (assumed) tags when all values were explicitly stated
- RULE-4: A spec generated from a PRD extracts every testable constraint as a RULE-N line — at least 5 rules for a multi-requirement PRD
- RULE-5: A spec generated from a PRD contains valid metadata: `> Description:`, `> Scope:`, and `> Stack:` fields are present when the PRD mentions files and technologies
- RULE-6: A spec generated from a PRD includes `> Requires:` referencing anchors whose `> Scope:` overlaps with the feature's scope, when such anchors exist in the project
- RULE-7: A spec generated from a vague description adds `(assumed — <context>)` tags to rules where the agent inferred specific values not stated by the user
- RULE-8: Rules with (assumed) tags in a vague-input spec still follow RULE-N: format and are parseable by sync_status
- RULE-9: A spec generated from customer feedback translates complaints into testable RULE-N constraints with specific thresholds or behaviors
- RULE-10: Every proof line across all four scenarios ends with an appropriate tier tag (@integration, @e2e, @manual, or no tag for unit)
- RULE-11: sync_status successfully parses specs from all four scenarios without errors, reporting correct rule counts and UNTESTED status when no proof files exist
- RULE-12: The `## Rules` and `## Proof` sections are both present in specs from all four scenarios
- RULE-13: When a vague-input spec's (assumed) rule is updated with an explicit value, the (assumed) tag is removed and the rule remains valid RULE-N format

## Proof

- PROOF-1 (RULE-1): Create temp project; write a spec with 4 sequentially numbered rules from a plain password-reset description; parse with regex `^- RULE-\d+:`; verify numbers are 1,2,3,4 with no gaps @e2e
- PROOF-2 (RULE-2): In the same spec, parse proof lines with regex `^- PROOF-\d+ \(RULE-\d+`; verify every RULE-N has at least one PROOF referencing it @e2e
- PROOF-3 (RULE-3): In the plain-description spec where all values are explicit (24 hours, POST /reset), grep for `(assumed`; verify zero matches @e2e
- PROOF-4 (RULE-4): Create temp project; write a spec from a multi-requirement PRD (checkout flow with 6 constraints); count RULE-N lines; verify at least 5 @e2e
- PROOF-5 (RULE-5): In the PRD-generated spec, grep for `> Description:`, `> Scope:`, and `> Stack:`; verify all three are present @e2e
- PROOF-6 (RULE-6): Create temp project with an anchor whose scope overlaps with the PRD spec's scope; write spec with `> Requires:` referencing that anchor; run sync_status; verify required rules appear in coverage output @e2e
- PROOF-7 (RULE-7): Create temp project; write a spec from a vague description ("link should expire quickly") with (assumed) tag on the expiry rule; grep for `(assumed — `; verify at least one match @e2e
- PROOF-8 (RULE-8): Run sync_status on the vague-input spec; verify it parses the assumed-tagged rules without errors and reports the correct rule count @e2e
- PROOF-9 (RULE-9): Create temp project; write a spec from customer feedback about slow search and typos; verify rules contain specific thresholds (e.g., "under 500ms") and behaviors (e.g., "fuzzy matching") @e2e
- PROOF-10 (RULE-10): Across all four scenario specs, parse every proof line; verify each ends with @integration, @e2e, @manual, or has no tier tag (implicit unit) @e2e
- PROOF-11 (RULE-11): Run sync_status on each of the four scenario specs (no proof JSON files); verify output contains feature name, correct rule count, and UNTESTED status for each @e2e
- PROOF-12 (RULE-12): For each of the four scenario specs, grep for `## Rules` and `## Proof`; verify both sections exist in each @e2e
- PROOF-13 (RULE-13): Write a spec with an assumed rule; create a corrected version replacing "(assumed — user said quickly)" with explicit "1 hour"; verify the corrected rule matches RULE-N format and no (assumed) tag remains on that rule @e2e
