# Feature: PM First Session Guide

> Label: "Tool: PM First Session Guide"
> Category: "Install, Update & Scripts"
> Owner: PM
> Prerequisite: features/pm_agent_launcher.md

## 1. Overview

When the PM agent launches into an empty project (zero feature specs), it enters a guided first-session mode that walks the user through creating their first feature spec. The PM also checks Figma MCP availability on every startup and offers guided setup if the connection is missing. Together these ensure a non-technical user can go from an empty project to a complete first spec without external help.

---

## 2. Requirements

### 2.1 Empty Project Detection

- The PM startup protocol MUST detect `feature_summary.total == 0` in the startup briefing.
- When zero features are detected, the PM MUST enter guided onboarding mode instead of the standard command-table-and-work-plan flow.
- Guided mode MUST suppress the standard command table and Critic action items (these are overwhelming and empty for a new project).
- The PM MUST still load its full instruction set internally; the simplification is in presentation only.

### 2.2 Guided Onboarding Conversation

- The PM MUST greet the user and explain this is a new project.
- The PM MUST ask what the user is building. One sentence is sufficient; the PM probes for detail only if the answer is too vague to write a scenario.
- The PM MUST ask if the user has Figma designs and invite them to paste a URL.
- If the user provides a Figma URL and Figma MCP is available, the PM MUST call `get_design_context` and create a feature spec with a `## Visual Specification` section referencing the design.
- If the user has no Figma designs, the PM MUST create a text-based feature spec from the description.
- The PM MUST create at least one anchor node appropriate to the described project (e.g., `design_visual_standards.md` for UI-heavy apps, `arch_data_layer.md` for data-driven apps). The anchor node provides the structural foundation for future specs.
- All created files MUST follow the standard feature file template and pass the Critic's spec gate.

### 2.3 Next Steps Guidance

- After creating the first spec and anchor node, the PM MUST commit all created files.
- The PM MUST tell the user to run `./pl-run-builder.sh` in another terminal to start building from the spec.
- The PM MUST tell the user to run `./pl-cdd-start.sh` to see the status dashboard.
- The PM MUST explain (one sentence) what the Builder will do: "The Builder reads your spec and writes the code and tests to match it."

### 2.4 Figma MCP Health Check

- On every PM startup (not just empty projects), the PM MUST check whether the `get_design_context` tool is available.
- If Figma MCP is NOT available AND one of these is true: (a) the project has features with `## Visual Specification` sections, (b) the user mentions Figma or shares a Figma URL, then the PM MUST offer to guide through setup.
- The guided setup instructions MUST be: (1) type `/mcp` in this terminal, (2) select "figma" from the list, (3) complete the authentication in the browser window that opens, (4) come back to this terminal.
- If Figma MCP IS available, the health check MUST be silent (no output).
- The health check MUST NOT block startup. If the user declines setup, the PM continues without Figma.

### 2.5 Scope Boundaries

- Guided onboarding mode activates ONLY when `feature_summary.total == 0`. Once any feature exists, the PM follows its standard startup protocol.
- The Figma health check runs on every startup regardless of project state.
- The PM MUST NOT attempt to run the Builder or start the CDD dashboard itself. It advises the user on what command to run.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Empty project triggers guided mode

    Given the PM agent launches
    And the startup briefing shows feature_summary.total is 0
    Then the PM enters guided onboarding mode
    And the PM does not display the standard command table
    And the PM asks what the user is building

#### Scenario: Non-empty project skips guided mode

    Given the PM agent launches
    And the startup briefing shows feature_summary.total is greater than 0
    Then the PM follows the standard startup protocol
    And guided onboarding mode is not activated

#### Scenario: First spec created from text description

    Given the PM is in guided onboarding mode
    And the user describes their project
    And the user has no Figma designs
    When the PM processes the description
    Then at least one feature spec is created in features/
    And at least one anchor node is created in features/
    And all created files follow the feature file template
    And the PM commits the created files
    And the PM instructs the user to run ./pl-run-builder.sh

#### Scenario: First spec created from Figma design

    Given the PM is in guided onboarding mode
    And Figma MCP is available
    And the user provides a Figma design URL
    When the PM processes the design
    Then the PM calls get_design_context with the parsed fileKey and nodeId
    And a feature spec with a Visual Specification section is created
    And the visual spec references the Figma source
    And at least one anchor node is created

#### Scenario: Next steps include Builder and CDD

    Given the PM has completed the guided onboarding flow
    Then the PM output includes "./pl-run-builder.sh"
    And the PM output includes "./pl-cdd-start.sh"
    And the PM output includes a one-sentence explanation of what the Builder does

#### Scenario: Figma MCP missing when user shares URL

    Given the PM agent is running (any project state)
    And Figma MCP tools are not available
    And the user shares a Figma URL
    Then the PM offers to guide through Figma MCP setup
    And the guidance includes typing /mcp and selecting figma
    And the guidance includes completing browser authentication

#### Scenario: Figma MCP present is silent

    Given the PM agent launches
    And Figma MCP tools are available
    Then no Figma health check message is displayed

#### Scenario: Figma MCP missing without visual context is silent

    Given the PM agent launches
    And Figma MCP tools are not available
    And no features have Visual Specification sections
    And the user has not mentioned Figma
    Then no Figma health check message is displayed

### Manual Scenarios (Human Verification Required)

#### Scenario: End-to-end first session walkthrough

    Given a freshly initialized Purlin project with zero features
    And Figma MCP is configured and authenticated
    When the user runs ./pl-run-pm.sh
    Then the PM greets the user conversationally (no jargon, no command dump)
    And after the user describes their project and shares a Figma URL
    Then the PM creates a spec with visual specification
    And creates at least one anchor node
    And commits all files
    And clearly explains what to do next (Builder, dashboard)
    And the created spec passes the Critic spec gate when tools/cdd/status.sh runs

#### Scenario: First session without Figma

    Given a freshly initialized Purlin project with zero features
    And Figma MCP is NOT configured
    When the user runs ./pl-run-pm.sh
    Then the PM greets the user and asks what they are building
    And does NOT immediately push Figma setup (waits for the user to mention it)
    And creates a text-based feature spec from the user's description
    And the experience feels conversational, not procedural
