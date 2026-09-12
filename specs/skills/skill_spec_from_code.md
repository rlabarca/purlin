# Feature: skill_spec_from_code

> Scope: skills/spec-from-code/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:spec-from-code` skill scans codebases and migrates existing specs in any format to the current compliant 3-section format.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `spec-from-code`, matching the directory name
- RULE-4: Skill includes mandatory tier tag review for proof descriptions
- RULE-5: Phase 1 detects existing specs in both `features/` (legacy) and `specs/` (non-compliant) as migration candidates
- RULE-6: Non-compliant specs in `specs/` are detected by checking for: missing `## Rules` section, unnumbered rules, missing `## Proof` section, or missing `> Description:` metadata
- RULE-7: Compliant specs (numbered rules, proofs, proper sections) are left untouched during migration
- RULE-8: Migration preserves the original spec's rules, descriptions, and metadata with minimal loss of fidelity
- RULE-9: Phase 4 offers to remove `features/` after migration but does NOT remove non-compliant specs from `specs/` (they are overwritten in place)
- RULE-10: A spec generated from a plain description contains sequentially numbered RULE-N lines starting at RULE-1 with no gaps
- RULE-11: A spec generated from a plain description contains PROOF-N (RULE-N) lines where every rule has at least one proof
- RULE-12: A spec generated from a plain description contains no (assumed) tags when all values were explicitly stated
- RULE-13: A spec generated from a PRD extracts every testable constraint as a RULE-N line — at least 5 rules for a multi-requirement PRD
- RULE-14: A spec generated from a PRD contains valid metadata: `> Description:`, `> Scope:`, and `> Stack:` fields are present
- RULE-15: A spec generated from a PRD includes `> Requires:` referencing anchors whose scope overlaps with the feature's scope
- RULE-16: A spec generated from a vague description adds `(assumed — <context>)` tags to rules where the agent inferred specific values
- RULE-17: Rules with (assumed) tags still follow RULE-N format and are parseable by sync_status
- RULE-18: A spec generated from customer feedback translates complaints into testable RULE-N constraints with specific thresholds or behaviors
- RULE-19: Every proof line across all four scenarios ends with an appropriate tier tag (@integration, @e2e, @manual, or no tag for unit)
- RULE-20: sync_status successfully parses specs from all four scenarios without errors, reporting correct rule counts and UNTESTED status
- RULE-21: The `## Rules` and `## Proof` sections are both present in specs from all four scenarios
- RULE-22: When a vague-input spec's (assumed) rule is updated with an explicit value, the (assumed) tag is removed and the rule remains valid
- RULE-23: Skill contains data contract extraction mandatory for ALL features (not just UI) with five categories: inbound contracts, outbound contracts, transformation rules, state transitions, and access contracts
- RULE-24: Skill contains a mandatory draft-and-evaluate step that applies rebuild/behavior/overlap tests to every candidate rule, and a rebuild-risk filter that verifies contract coverage across all five categories before presenting specs
- RULE-25: Migration from `features/` reads `.impl.md` companion files and extracts active deviations as rules reflecting actual behavior
- RULE-26: Migration from `features/` reads `.discoveries.md` companion files and converts resolved bugs to regression rules and open bugs to `(deferred)` rules
- RULE-27: `.discoveries.md` Figma/design references are preserved as `> Visual-Reference:` metadata or `@manual` proof references during migration
- RULE-28: Quality guide references coverage dimensions instead of a fixed rule count target
- RULE-29: The taxonomy phase never produces a category folder containing a single spec — single-feature categories are merged into a related category during taxonomy review, or the spec is placed directly at `specs/<name>.md` when no category fits
- RULE-30: The tier review pass (Phase 3 step 7) includes an inverse check: every `@e2e` proof description must read as an observable flow (arrange → act → observe through the real running app) and must not name a source file or internal function; mis-tagged proofs are rewritten as boundary observations or retagged, per `references/spec_quality_guide.md` ("E2E proof descriptions")
- RULE-31: Spec validation (Phase 3 step 11) includes a proof implementation-coupling check that rejects proof descriptions naming source files or internal symbols as the asserted target
- RULE-32: When a category's generated proofs include `@e2e` and no e2e-capable test runner was detected in Phase 1, the skill surfaces a warning in the category review block and in the Phase 4 summary (tool-agnostic — Playwright, Cypress, MCP-driven browser, etc.)

## Proof

- PROOF-1 (RULE-1): Grep `skills/spec-from-code/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/spec-from-code/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `spec-from-code`
- PROOF-4 (RULE-4): Grep `skills/spec-from-code/SKILL.md` for tier review instructions and tier tag references (`@integration`/`@e2e`/unit tier); verify present
- PROOF-5 (RULE-5): Grep SKILL.md for `features/` detection AND `specs/` non-compliant detection in Phase 1; verify both paths exist
- PROOF-6 (RULE-6): Grep SKILL.md for compliance checks: "Missing `## Rules`", "unnumbered", "Missing `## Proof`", "Missing `> Description:`"; verify all four criteria are documented
- PROOF-7 (RULE-7): Grep SKILL.md for "Compliant specs" or "left untouched"; verify compliant specs are explicitly excluded from migration
- PROOF-8 (RULE-8): Grep SKILL.md for "primary input" and "preserve"; verify migration uses old spec as primary input @integration
- PROOF-9 (RULE-9): Grep SKILL.md for `features/` cleanup offer AND "overwritten in place" for specs/; verify both paths exist
- PROOF-10 (RULE-5): e2e: Write features/auth/login.md with 3 Given/When/Then scenarios plus its .impl.md and .discoveries.md companions, then run sync_status: it prints "No specs found in specs/", because a legacy spec counts for nothing until it is migrated, which is why Phase 1 has to find it itself; SKILL.md step 3a carries the recursive `features/` read "excluding `.impl.md` and `.discoveries.md`" and the "scenarios (Given/When/Then blocks)" extraction (Phase 1 is agent-run, so that instruction is the other checkable half) @e2e
- PROOF-11 (RULE-6): e2e: Create spec with unnumbered rules; verify sync_status warns about non-numbered rules @e2e
- PROOF-12 (RULE-6): e2e: Write specs/notify/notifications.md with `## What it does` and no `> Description:` line beside notifications_documented.md carrying `> Description: Sends email and SMS notifications to users.`, run sync_status and read the project dashboard payload: description is null for the first feature and exactly that sentence for the second; SKILL.md step 3b lists "Missing `> Description:` metadata" as a non-compliance criterion and Phase 3 step 3 orders "add missing `> Description:`" @e2e
- PROOF-13 (RULE-6): e2e: Write specs/search/search.md with RULE-1 to RULE-3 and no `## Proof` section beside specs/notify/notifications.md with 3 rules and 3 proofs, then run sync_status: search prints no planned-proof line and the placeholder directive `@pytest.mark.proof("search", "PROOF-N", "RULE-1")`, while notifications prints `planned PROOF-1: Create an order; verify confirmation email sent @integration`; SKILL.md step 3b lists "Missing `## Proof` section" as a non-compliance criterion @e2e
- PROOF-14 (RULE-7): e2e: Write the compliant specs/users/profile.md (Description, RULE-1 to RULE-3, PROOF-1 to PROOF-3), record its sha256 and mtime, then run sync_status: the file's sha256 and mtime are unchanged, its section reads "profile: 0/3 rules proved" and carries no WARNING line; SKILL.md step 3b says compliant specs "are left untouched" and are "not migration candidates" (the migration pass is agent prose with no script to drive) @e2e
- PROOF-15 (RULE-7): e2e: Run sync_status over one project holding the compliant specs/users/profile.md, the unnumbered specs/cart/cart.md and specs/legacy/legacy_thing.md with no `## Rules` section: cart is flagged "WARNING: 4 lines under ## Rules are not numbered.", legacy_thing "WARNING: No ## Rules section found.", and profile's own section carries no WARNING, so the only candidate list a tool can produce leaves the compliant spec out @e2e
- PROOF-16 (RULE-8): e2e: Write specs/notify/notifications.md carrying `> Scope: src/notify/email.py, src/notify/sms.py` and `> Stack: python/stdlib, twilio` but no Description, create src/notify/email.py and run sync_status: it directs "→ Run: purlin:test" and the dashboard payload reports stack "python/stdlib, twilio"; with the scope file absent the same spec directs "→ Run: purlin:build notifications", so both lines are load-bearing, and SKILL.md Phase 3 step 3 orders "existing metadata (`> Scope:`, `> Stack:`, `> Requires:`)" preserved @e2e
- PROOF-17 (RULE-5): e2e: With features/auth/login.md as the only spec, sync_status prints "No specs found in specs/"; write the same feature by hand to the migration destination specs/auth/login.md with RULE-1 to RULE-3 (migration is agent prose, so that file stands in for its output) and sync_status then reports "login: 0/3 rules proved", with the dashboard payload placing login in category "auth"; SKILL.md reads `features/<category>/<name>.md` and writes `specs/<category>/<name>.md` @e2e
- PROOF-18 (RULE-8): e2e: Migrate unnumbered spec; verify all original rule content preserved in numbered format with proofs @e2e
- PROOF-19 (RULE-10): e2e: Write the plain-description scenario spec, 4 rules generated from a quoted input that states every value, and run sync_status: the feature reads "0/4 rules proved" and its rule lines are RULE-1, RULE-2, RULE-3, RULE-4 in that order with no gap; the SKILL.md step 6 template numbers rules "- RULE-1:" then "- RULE-2:" (generation is agent prose, so the scenario file stands in for the generated spec) @e2e
- PROOF-20 (RULE-11): e2e: Verify every RULE-N has at least one PROOF referencing it @e2e
- PROOF-21 (RULE-12): e2e: Run sync_status over the plain-description scenario spec, whose quoted input states every value, beside the vague-input scenario spec: the plain feature holds no "(assumed" substring and its section carries no "(assumed) values" line, while the vague feature's section prints "⚠ 2 rules have (assumed) values — PM should confirm" @e2e
- PROOF-22 (RULE-13): e2e: Create PRD spec with 6 constraints; verify at least 5 RULE-N lines @e2e
- PROOF-23 (RULE-14): e2e: Verify PRD spec has Description, Scope, and Stack metadata @e2e
- PROOF-24 (RULE-15): e2e: Create project with overlapping anchor; verify Requires references it and sync_status shows required rules @e2e
- PROOF-25 (RULE-16): e2e: The vague-input scenario spec carries 2 rules tagged `(assumed — user said "<wording>")`, and sync_status prints "⚠ 2 rules have (assumed) values — PM should confirm" for it; with both tags rewritten as a bare "(assumed)" with no context, the same run prints no "(assumed) values" line, so only the context-carrying form is counted @e2e
- PROOF-26 (RULE-17): e2e: Run sync_status on vague-input spec; verify parses without errors with correct rule count @e2e
- PROOF-27 (RULE-18): e2e: Pair the scenario's quoted customer complaints with the generated spec and run sync_status: it reports 4 rules for the feature, the slowness complaint is answered by RULE-1 with a numeric latency bound ("500ms" in the search scenario, "2 seconds" in the dashboard scenario), and each remaining complaint maps to exactly one rule carrying its own literal ("fuzzy matching", "25 items per page"), so no complaint is left as prose @e2e
- PROOF-28 (RULE-19): e2e: Run sync_status over all four scenario specs: every planned-proof line it prints ends with @integration, @e2e, @manual or no tag at all, and the run emits no proof tag WARNING; insert "@e2e" before the trailing "@integration" on PROOF-1 of the plain scenario and re-run: it prints "WARNING: PROOF-1: a second tier tag @e2e precedes @integration"; SKILL.md step 7 routes a proof needing "a browser or full app stack" to `@e2e` and one that shells out to git or an external service to `@integration` @e2e
- PROOF-29 (RULE-20): e2e: Run sync_status on all four scenarios; verify UNTESTED status and correct rule counts @e2e
- PROOF-30 (RULE-21): e2e: Verify ## Rules and ## Proof sections exist in all four scenario specs @e2e
- PROOF-31 (RULE-22): e2e: Update (assumed) rule with explicit value; verify tag removed and RULE-N format valid @e2e
- PROOF-32 (RULE-23): Grep SKILL.md for "Inbound contracts", "Outbound contracts", "Transformation rules", "State transitions", "Access contracts" as subsections of step 4; verify all five exist and step is mandatory for ALL features
- PROOF-33 (RULE-23): e2e: Create a simulated component with API field consumption, filter/sort transformations, conditional gates by user segment, and missing-data fallbacks; verify the extraction identifies inbound fields, transformations, access gates, and failure modes @e2e
- PROOF-34 (RULE-24): Grep SKILL.md for "Draft and evaluate" AND "rebuild test" in Phase 3; verify the step applies rebuild, behavior, and overlap tests. Grep for "Verify contract coverage" in the rebuild-risk filter; verify it checks all five contract categories
- PROOF-35 (RULE-25): Grep SKILL.md for ".impl.md" AND "Active Deviations" AND "PM-ACCEPTED"; verify the skill reads deviations and converts PM-accepted deviations to rules reflecting actual behavior
- PROOF-36 (RULE-25): e2e: Create a features/ directory with a spec and .impl.md containing a PM-ACCEPTED deviation; verify the deviation's actual behavior becomes a RULE-N in the migrated spec @e2e
- PROOF-37 (RULE-26): Grep SKILL.md for ".discoveries.md" AND "Resolved bugs" AND "(deferred)"; verify resolved bugs become rules and open bugs become deferred rules
- PROOF-38 (RULE-26): e2e: Create features/ with .discoveries.md containing one RESOLVED bug and one OPEN bug; verify the resolved bug becomes a RULE-N and the open bug becomes a RULE-N with (deferred) tag @e2e
- PROOF-39 (RULE-27): Grep SKILL.md for "Visual-Reference" AND "Figma" in the .discoveries.md migration section; verify design references are preserved as metadata or manual proof references
- PROOF-40 (RULE-28): Grep spec_quality_guide.md for "Coverage dimensions"; verify section exists. Grep for "5–10 rules per feature"; verify the fixed target no longer exists
- PROOF-41 (RULE-29): Grep `skills/spec-from-code/SKILL.md` for the Phase 2 single-feature category check; verify it instructs merging single-feature categories into a related category or placing the spec at `specs/<name>.md` without a folder
- PROOF-42 (RULE-30): Grep `skills/spec-from-code/SKILL.md` step 7 for the inverse check: "observable flow", arrange → act → observe, and "must not name a source file or internal function"; verify the pointer to `spec_quality_guide.md` "E2E proof descriptions" is present
- PROOF-43 (RULE-31): Grep `skills/spec-from-code/SKILL.md` step 11 for the proof implementation-coupling check; verify it rejects proof descriptions naming source files or internal symbols as the asserted target
- PROOF-44 (RULE-32): Grep `skills/spec-from-code/SKILL.md` for the e2e-runner warning in BOTH the step 12 review block and the Phase 4 summary; verify both locations mention `@e2e` proofs with no e2e runner detected
- PROOF-45 (RULE-30): Grep `references/spec_quality_guide.md` for the "E2E proof descriptions" section; verify the canonical guidance the skill points to exists
