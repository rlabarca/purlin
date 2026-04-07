# Feature: figma_web

> Description: End-to-end workflow proof that the exact 5-message sequence from
>   docs/examples/figma-web-app.md produces a working web UI with high visual
>   fidelity to the Figma design. Uses the modal-test Figma file as the design
>   reference. Each step is a real `claude -p` invocation — nothing is faked.
> Scope: docs/examples/figma-web-app.md, skills/anchor/SKILL.md, skills/build/SKILL.md
> Stack: python/pytest, playwright, shell/bash
> Requires: skill_anchor

## What it does

Proves that running the exact 5-message workflow documented in
docs/examples/figma-web-app.md against the modal-test Figma design
(https://www.figma.com/design/TEZI0T6lObCJrC9mkmZT8v/modal-test?node-id=7-81)
produces a working, visually faithful web UI. The test uses `claude -p` with
`--resume` for session continuity — each message is sent exactly as documented.
Prerequisites (purlin:init) are run before the 5-message sequence.

The 5 documented messages (adapted for the modal-test design):
1. "here's our design: https://www.figma.com/design/TEZI0T6lObCJrC9mkmZT8v/modal-test?node-id=7-81"
2. "I need a feature for the feedback modal from this design"
3. "build it"
4. "run the tests"
5. "verify and ship"

## Rules

- RULE-1: Prerequisites — purlin:init creates a valid Purlin project before the workflow starts
- RULE-2: Message 1 — sharing the Figma URL creates a design anchor in specs/_anchors/ with Source, Visual-Reference, Pinned, and Type: design metadata
- RULE-3: The anchor contains at least one visual-match rule with an @e2e proof
- RULE-4: Message 2 — describing the feature creates a spec with > Requires: referencing the anchor
- RULE-5: The anchor contains the real Figma file key, proving Figma MCP was used
- RULE-6: Message 3 — "build it" produces a functioning HTML file that renders in a browser
- RULE-7: The build writes tests with proof markers referencing the feature and anchor
- RULE-8: A Playwright screenshot of the built UI can be captured and compared against a reference
- RULE-9: The built UI visually matches the Figma design within the fidelity threshold
- RULE-10: All 5 documented steps produce their expected artifacts — no extra commands needed
- RULE-11: FORBIDDEN — Modifying existing framework docs, proof files, skill definitions, or source code to make the workflow succeed
- RULE-12: FORBIDDEN — Claude silently fixing errors; on failure it must report the issue
- RULE-13: The audit static_checks pipeline returns a classification for anchor proofs
- RULE-14: Each test run saves screenshot(s) to dev/figma_web_result.png showing the built UI
- RULE-15: Message 4+5 — "run the tests" and "verify and ship" result in passing tests (pytest exit 0)

## Proof

- PROOF-1 (RULE-1): Run purlin:init via claude -p in a temp dir; verify .purlin/config.json exists with required fields @e2e
- PROOF-2 (RULE-2): Send message 1 (Figma URL) via claude -p --resume; verify anchor .md in specs/_anchors/ has > Source:, > Visual-Reference: figma://, > Pinned:, > Type: design @e2e
- PROOF-3 (RULE-3): Read the anchor; verify it has a visual-match rule and an @e2e proof @e2e
- PROOF-4 (RULE-4): Send message 2 via claude -p --resume; verify a feature spec exists with > Requires: referencing the anchor @e2e
- PROOF-5 (RULE-5): Verify the anchor text contains the Figma file key TEZI0T6lObCJrC9mkmZT8v @e2e
- PROOF-6 (RULE-6): Send message 3 via claude -p --resume; open the built HTML in Playwright; verify page renders visible content @e2e
- PROOF-7 (RULE-7): Read test files; verify proof markers reference both feature and anchor names @e2e
- PROOF-8 (RULE-8): Capture Playwright screenshot of built UI; verify it is a valid PNG alongside the MCP fixture reference @e2e
- PROOF-9 (RULE-9): Compute pixel diff between built UI screenshot and MCP fixture reference; verify diff is within threshold @e2e
- PROOF-10 (RULE-10): Verify all 5 steps produced artifacts: config, anchor, spec, HTML, tests @e2e
- PROOF-11 (RULE-11): Check git diff of framework repo; verify no new changes to docs/, skills/, scripts/, references/ @e2e
- PROOF-12 (RULE-12): Send a broken Figma URL via claude -p; verify Claude reports an error rather than silently succeeding @e2e
- PROOF-13 (RULE-13): Run static_checks.py on the anchor test file; verify it returns proof classifications @e2e
- PROOF-14 (RULE-14): Capture Playwright screenshot to dev/figma_web_result.png; verify valid PNG @e2e
- PROOF-15 (RULE-15): Send messages 4+5 via claude -p --resume; run pytest in the built project; verify exit code 0 @e2e
