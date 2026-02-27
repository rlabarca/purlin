# Feature File Format Reference

> This file is loaded on-demand by `/pl-spec` and `/pl-anchor` commands.
> It contains heading format rules and Critic parser requirements.

The Critic's parser enforces specific Markdown heading formats. Wrong heading levels or
section names cause Spec Gate failures that are not obvious from the error message.

## Template Files

**MANDATE:** When creating a new feature file or anchor node, you MUST copy from the template as the starting point. Do NOT create feature files from memory or scratch. When updating an existing feature file, consult the template to verify section structure is correct. The template is the authoritative reference for required sections, heading formats, and section order.

Copy from `{tools_root}/feature_templates/`:
- `_feature.md` -- regular feature file
- `_anchor.md` -- anchor node (arch_*, design_*, policy_*)

**No Implementation Notes section:** Feature files do NOT contain an `## Implementation Notes` section. All implementation knowledge belongs in companion files (`features/<name>.impl.md`). See HOW_WE_WORK_BASE Section 4.3 and BUILDER_BASE Section 5.2 for the companion file convention.

## Regular Feature Files

**Required section headings** (Critic checks for these words, case-insensitive, substring match):
- A heading containing `overview`
- A heading containing `requirements`
- A heading containing `scenarios`

**Scenario heading format -- MUST use four-hash `####`:**

    #### Scenario: Title of the scenario

        Given <precondition>
        When <action>
        Then <expected outcome>

NOT valid: `**Scenario: Title**`, `### Scenario: Title`, `- Scenario: Title`

**Manual scenario block:**

    ### Manual Scenarios (Human Verification Required)

    #### Scenario: Title

        Given ...

    (Use "None." if no manual scenarios.)

## Anchor Nodes (arch_*, design_*, policy_*)

**Required section headings** (Critic checks for these words, case-insensitive, substring match):
- A heading containing `purpose`
- A heading containing `invariants`

Note: `## 1. Overview` does NOT satisfy the `purpose` check. The heading text must contain
the word "purpose" -- e.g., `## Purpose`, `## 1. Purpose`.

Scenario classification and gherkin quality checks are automatically skipped for anchor nodes.
