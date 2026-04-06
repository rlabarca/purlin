# Feature: figma_web

> Description: End-to-end workflow proof that a web UI can be built from a Figma design
>   using only Purlin's documented skills, achieving ≥95% visual fidelity. Uses the
>   modal-test Figma design as the reference and a local anchor as the build instruction.
> Scope: docs/examples/figma-web-app.md, skills/anchor/SKILL.md, skills/build/SKILL.md
> Stack: python/pytest, playwright, shell/bash
> Requires: skill_anchor

## What it does

Proves that the complete Figma-to-web workflow documented in docs/examples/figma-web-app.md
works end-to-end with high fidelity. Uses the modal-test Figma design
(https://www.figma.com/design/TEZI0T6lObCJrC9mkmZT8v/modal-test?node-id=7-81) as the
visual reference. Each step — from project initialization through verification — is
exercised in a sample project using only the documented Purlin skills. No modifications to
existing framework code, docs, or proofs are permitted. If the workflow cannot complete
as documented, the test fails and reports what needs to change.

## Rules

- RULE-1: purlin:init on a new empty directory creates a valid Purlin config file
- RULE-2: Natural language input with the Figma URL creates a design anchor in specs/_anchors/ via purlin:anchor, with correct > Source:, > Visual-Reference:, > Pinned:, and > Type: design metadata
- RULE-3: The created design anchor contains exactly one visual-match rule with an @e2e screenshot comparison proof description
- RULE-4: purlin:spec creates a feature spec with > Requires: referencing the created figma design anchor
- RULE-5: purlin:build reads the Figma design via real Figma MCP calls (get_design_context or get_screenshot) — not from cached or hardcoded data
- RULE-6: Build produces a functioning web UI that renders the modal-test design and can be opened in a browser
- RULE-7: Build writes tests with proof markers for both the feature spec rules and the design anchor visual-match rule
- RULE-8: At least one proof captures a real browser screenshot of the implemented UI and compares it against a Figma MCP-sourced screenshot of the original design
- RULE-9: The implemented UI achieves ≥95% visual fidelity match to the Figma design at the same viewport dimensions
- RULE-10: The entire workflow completes using only the documented skill commands (purlin:init, purlin:anchor, purlin:spec, purlin:build, purlin:unit-test, purlin:verify) — no extra commands, manual fixes, or workarounds
- RULE-11: FORBIDDEN — Modifying existing framework docs, proof files, skill definitions, or source code to make the workflow succeed
- RULE-12: FORBIDDEN — Auto-fixing workflow failures; on any failure the LLM must stop execution and present suggested changes for the user to approve before continuing
- RULE-13: purlin:audit on the figma design anchor reports an assessment classification (STRONG, WEAK, or HOLLOW) for the visual-match proof, and this classification is captured in the test output
- RULE-14: Each test run saves screenshot image(s) to dev/figma_web_result*.png showing the final implemented UI, overwriting previous screenshots from prior runs
- RULE-15: purlin:verify succeeds with all rules proved across both the feature spec and the design anchor

## Proof

- PROOF-1 (RULE-1): Create a temp directory, run purlin:init, verify purlin.json exists with required fields (version, specs directory) @e2e
- PROOF-2 (RULE-2): In the initialized sample project, provide "here's our design: https://www.figma.com/design/TEZI0T6lObCJrC9mkmZT8v/modal-test?node-id=7-81" as natural language input; verify a .md file is created in specs/_anchors/ containing > Source: with the Figma URL, > Visual-Reference: with figma://, > Pinned: with an ISO 8601 timestamp, and > Type: design @e2e
- PROOF-3 (RULE-3): Read the created anchor .md file; verify ## Rules contains exactly one RULE-1 with "visually match" text and ## Proof contains exactly one PROOF-1 with @e2e tag and "screenshot" in the description @e2e
- PROOF-4 (RULE-4): Run purlin:spec to create a feature spec for the modal UI; verify the output .md file contains > Requires: with the anchor name from PROOF-2 @e2e
- PROOF-5 (RULE-5): During purlin:build, capture MCP tool call logs; verify at least one call to get_design_context or get_screenshot with file key TEZI0T6lObCJrC9mkmZT8v @e2e
- PROOF-6 (RULE-6): After build completes, start a local dev server, navigate Playwright browser to the built page; verify the page loads (HTTP 200) and renders visible content (page is not blank) @e2e
- PROOF-7 (RULE-7): After build completes, read the generated test files; verify proof markers exist referencing both the feature spec name and the anchor spec name @e2e
- PROOF-8 (RULE-8): Run the visual comparison test; verify it fetches a screenshot from Figma MCP (get_screenshot call with the modal-test file key) AND captures a Playwright screenshot of the local implementation, then performs pixel comparison between the two @e2e
- PROOF-9 (RULE-9): Capture Playwright screenshot of implementation at Figma frame viewport dimensions, fetch Figma reference screenshot at same dimensions, compute pixel diff percentage; verify diff is ≤5% @e2e
- PROOF-10 (RULE-10): Record all skill invocations during the workflow; verify the only commands used are purlin:init, purlin:anchor (or natural language anchor creation), purlin:spec, purlin:build, purlin:unit-test, and purlin:verify — no other purlin: commands or manual shell commands were needed @e2e
- PROOF-11 (RULE-11): Compute git status of the Purlin framework repo after the sample project workflow completes; verify zero new or modified files in docs/, skills/, scripts/, references/ @e2e
- PROOF-12 (RULE-12): Introduce a deliberate failure condition (e.g., unreachable Figma URL); verify the LLM output contains a request for user approval (phrases like "approve", "confirm", or "would you like") rather than silently modifying files @e2e
- PROOF-13 (RULE-13): Run purlin:audit targeting the created figma design anchor; verify output contains an assessment line with STRONG, WEAK, or HOLLOW for the RULE-1 visual-match proof; capture the classification text in the test output @e2e
- PROOF-14 (RULE-14): After the full workflow completes, verify dev/figma_web_result.png exists, is a valid PNG (starts with PNG magic bytes), and has non-zero width and height @e2e
- PROOF-15 (RULE-15): Run purlin:verify on the sample project; verify exit code 0 and output contains success indicator for both the feature spec and the design anchor showing all rules proved @e2e
