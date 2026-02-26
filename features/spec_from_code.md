# Feature: Spec From Code

> Label: "/pl-spec-from-code: Spec From Code"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/impl_notes_companion.md

[TODO]

## 1. Overview

When Purlin is installed into a project with an existing codebase, there is no systematic way to reverse-engineer the codebase into Purlin's feature spec system. The `/pl-spec-from-code` command automates this onboarding by scanning an existing codebase, categorizing what it finds, interacting with the user to validate the taxonomy, and generating properly-structured feature files (with draft Gherkin scenarios), anchor nodes, and companion files. The command is Architect-only and uses a 5-phase, context-managed approach with durable state artifacts for cross-session continuity.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the Architect role.
- Non-Architect agents MUST receive a redirect message: "This is an Architect command. Ask your Architect agent to run `/pl-spec-from-code`."

### 2.2 State Management and Cross-Session Resume

- The command MUST create a state file at `.purlin/cache/sfc_state.json` on initialization.
- The state file MUST track the current phase number, phase status (`in_progress` or `complete`), a start timestamp, and per-category completion progress during Phase 3.
- On invocation, the command MUST check for an existing state file and resume from the last incomplete phase if one is found.
- The user MUST NOT be re-asked questions whose answers are already preserved in the taxonomy or inventory files from prior phases.

### 2.3 Phase 0 -- Initialization

- The command MUST prompt the user (via `AskUserQuestion`) to specify which directories contain application source code.
- The prompt MUST offer common defaults (`src/`, `lib/`, `app/`) and common exclusions (`node_modules/`, `vendor/`, `.purlin/`, `tools/`, `dist/`, `build/`).
- The user's directory include/exclude choices MUST be saved to the state file and committed to git.

### 2.4 Phase 1 -- Codebase Survey

- The command MUST launch up to 3 Explore sub-agents in parallel, each assigned a distinct partition of work:
  - **Agent A (Structure):** Directory tree, entry points, file types, main/index files, route definitions, CLI entry points, config files.
  - **Agent B (Domain):** Key files, frameworks, domain concepts, tech stack (languages, frameworks, key deps from package manifests), domain terminology, module boundaries, public API surfaces.
  - **Agent C (Comments & Docs):** Code comments, docstrings, READMEs, significant comments (TODO, FIXME, HACK, architectural decision comments, module-level docstrings), existing documentation files.
- Sub-agent results MUST be synthesized into `.purlin/cache/sfc_inventory.md` containing: directory map with annotations, detected tech stack summary, preliminary feature candidates (module-level granularity), cross-cutting concerns detected, and a code comments index.
- The inventory file MUST be committed to git.

### 2.5 Phase 2 -- Taxonomy Review

- The command MUST read the inventory and propose a category taxonomy grouping feature candidates into logical categories.
- Each category MUST be presented with its name, feature count, and per-feature name + one-line description.
- The user MUST be asked (via `AskUserQuestion`, in batches of 2-3 categories) to validate each category: confirm the name, confirm feature membership, and identify missed features.
- The command MUST propose anchor nodes derived from detected cross-cutting concerns, classified by type (`arch_*`, `design_*`, `policy_*`).
- The user MUST be asked to validate the proposed anchor nodes.
- The validated taxonomy MUST be written to `.purlin/cache/sfc_taxonomy.md` containing: ordered anchor node list, ordered category list with features, and per-feature proposed file name, description, and anchor node references.
- The taxonomy file MUST be committed to git.

### 2.6 Phase 3 -- Feature Generation

- Anchor nodes MUST be generated before features (dependency graph roots first).
- Each anchor node MUST be created from the canonical `_anchor.md` template (`tools/feature_templates/_anchor.md`).
- Each anchor node MUST include a proper heading (`# Architecture:`, `# Policy:`, or `# Design:` matching its prefix type), Label and Category metadata, Purpose section, and Invariants section.
- Each anchor node MUST be committed individually.
- Features MUST be generated one category at a time, ordered by dependency (categories with fewer anchor node dependencies first).
- For categories spanning more than 5 source files, the command MUST use an Explore sub-agent to read the relevant source; otherwise it MAY read directly.
- Each feature file MUST be created from the canonical `_feature.md` template (`tools/feature_templates/_feature.md`).
- Each feature file MUST include: `> Label:`, `> Category:`, and `> Prerequisite:` metadata linking to relevant anchor nodes; an Overview paragraph; Requirements organized into numbered subsections; and Gherkin scenarios describing current code behavior.
- The Scenarios section of every generated feature MUST include the note: `> **[Draft]** These scenarios were auto-generated from existing code by /pl-spec-from-code. Review and refine before marking as final.`
- All generated features MUST have status marker `[TODO]`.
- Companion files (`features/<name>.impl.md`) MUST be created for features where significant code comments were found (TODOs, architectural decisions, known issues). Each companion file MUST include a `### Source Mapping` section listing which source files implement the feature.
- After generating each category, the user MUST be asked (via `AskUserQuestion`) to confirm the generated features look correct before proceeding to the next category.
- Each category batch (all features + companion files for that category) MUST be committed together in a single commit.
- The state file MUST be updated with the completed category name after each category commit.

### 2.7 Phase 4 -- Finalization

- The command MUST run `tools/cdd/status.sh` to generate the initial Critic report and dependency graph for the newly created features.
- The command MUST summarize the results: total features created, total anchor nodes created, total companion files created, and any immediate Critic findings.
- The command MUST delete the temporary state and cache files (`.purlin/cache/sfc_state.json`, `.purlin/cache/sfc_inventory.md`, `.purlin/cache/sfc_taxonomy.md`) and commit the cleanup.
- The command MUST print recommended next steps to the user:
  - "Run `/pl-spec-code-audit` to validate the generated specs against the actual code and identify any gaps the import missed."
  - "Review generated features in dependency order (anchor nodes first) and refine the draft scenarios."
  - "Once specs are refined, have the Builder run `/pl-build` to begin implementation verification."

### 2.8 Context Management

- Heavy file reading in Phase 1 MUST be delegated to Explore sub-agents so the main agent sees summaries only.
- Phase 3 feature generation MUST be batched per category with commits between batches, providing natural save points if context fills up.
- All phases MUST produce durable artifacts committed to git so the agent can be relaunched between phases without losing progress.

### 2.9 Template Compliance

- All generated feature files MUST pass the Critic's Spec Gate (required sections: overview, requirements, scenarios; scenario headings at `####` level).
- All generated anchor nodes MUST pass the Critic's Spec Gate (required sections: purpose, invariants).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Role gate rejects non-Architect invocation

    Given a Builder agent session
    When the agent invokes /pl-spec-from-code
    Then the command responds with "This is an Architect command. Ask your Architect agent to run /pl-spec-from-code."
    And no state file is created

#### Scenario: Phase 0 creates state file and prompts for directories

    Given an Architect agent session with no existing sfc_state.json
    When the agent invokes /pl-spec-from-code
    Then the command creates .purlin/cache/sfc_state.json with phase 0 and status in_progress
    And the command prompts the user to specify source directories and exclusions
    And the user's choices are saved to the state file
    And the state file is committed to git

#### Scenario: Phase 1 launches parallel sub-agents for codebase survey

    Given Phase 0 is complete with directory choices saved
    When Phase 1 begins
    Then up to 3 Explore sub-agents are launched in parallel
    And Agent A scans directory structure, entry points, and file types
    And Agent B identifies tech stack, domain concepts, and module boundaries
    And Agent C extracts significant code comments and documentation
    And results are synthesized into .purlin/cache/sfc_inventory.md
    And the inventory file is committed to git

#### Scenario: Phase 2 presents taxonomy for interactive review

    Given the inventory file exists at .purlin/cache/sfc_inventory.md
    When Phase 2 begins
    Then the command proposes categories with feature candidates grouped by module
    And the user is prompted in batches of 2-3 categories to validate names and membership
    And the command proposes anchor nodes from detected cross-cutting concerns
    And the user is prompted to validate the anchor node proposals
    And the validated taxonomy is written to .purlin/cache/sfc_taxonomy.md
    And the taxonomy file is committed to git

#### Scenario: Phase 3 generates anchor nodes before features

    Given the taxonomy file exists with approved anchor nodes and categories
    When Phase 3 begins
    Then all anchor nodes are created first using the _anchor.md template
    And each anchor node is committed individually
    And features are generated after all anchor nodes exist

#### Scenario: Phase 3 generates features per category with template compliance

    Given anchor nodes are created and committed
    When a category batch is generated
    Then each feature file uses the _feature.md template
    And each feature file includes Label, Category, and Prerequisite metadata
    And each feature file includes an Overview, Requirements, and Scenarios section
    And the Scenarios section includes the Draft auto-generation notice
    And all features have status marker TODO
    And the category batch is committed as a single commit

#### Scenario: Phase 3 creates companion files for features with rich comments

    Given Agent C found significant code comments for a feature's source files
    When the feature is generated in Phase 3
    Then a companion file is created at features/<name>.impl.md
    And the companion file contains extracted comments with source file references
    And the companion file includes a Source Mapping section listing implementation files

#### Scenario: Phase 3 asks user to confirm each category before continuing

    Given a category batch has been generated and committed
    When the category is complete
    Then the user is prompted via AskUserQuestion to confirm the generated features
    And the state file is updated with the completed category name
    And the next category does not begin until the user responds

#### Scenario: Phase 4 runs CDD status and summarizes results

    Given all categories are generated and committed
    When Phase 4 begins
    Then tools/cdd/status.sh is executed
    And the command prints total features created, anchor nodes created, and companion files created
    And the command prints any immediate Critic findings

#### Scenario: Phase 4 cleans up temporary files

    Given the CDD status has been generated in Phase 4
    When finalization cleanup runs
    Then .purlin/cache/sfc_state.json is deleted
    And .purlin/cache/sfc_inventory.md is deleted
    And .purlin/cache/sfc_taxonomy.md is deleted
    And the cleanup is committed to git

#### Scenario: Phase 4 prints recommended next steps

    Given cleanup is committed
    When finalization completes
    Then the command prints three recommended next steps
    And the first recommendation mentions /pl-spec-code-audit
    And the second recommendation mentions reviewing features in dependency order
    And the third recommendation mentions having the Builder run /pl-build

#### Scenario: Cross-session resume from interrupted Phase 3

    Given Phase 2 is complete and Phase 3 was interrupted after completing 2 of 5 categories
    And .purlin/cache/sfc_state.json records phase 3 with 2 completed categories
    When the agent invokes /pl-spec-from-code
    Then the command reads the state file and resumes Phase 3
    And the command skips the 2 already-completed categories
    And the command continues with category 3
    And the user is not re-asked Phase 0 or Phase 2 questions

#### Scenario: Resume from completed Phase 1

    Given Phase 1 is complete and the inventory file exists
    And the state file records phase 1 status complete
    When the agent invokes /pl-spec-from-code
    Then the command skips Phase 0 and Phase 1
    And the command begins Phase 2 using the existing inventory

#### Scenario: Generated features appear in CDD dashboard as TODO

    Given Phase 4 has completed successfully
    When tools/cdd/status.sh is run
    Then all generated features appear in the CDD dashboard with TODO status
    And all generated anchor nodes appear in the CDD dashboard

### Manual Scenarios (Human Verification Required)

#### Scenario: End-to-end onboarding of a non-trivial codebase

    Given a consumer project with 10+ source files across multiple directories
    And Purlin is freshly installed (features/ directory is empty or contains only framework features)
    When the Architect runs /pl-spec-from-code
    Then Phase 0 prompts for directory selection and the state file is created
    And Phase 1 produces an inventory with directory map, tech stack, and feature candidates
    And Phase 2 presents categories interactively and allows renaming and reorganization
    And Phase 3 generates feature files matching the _feature.md template structure
    And Phase 3 generates anchor nodes matching the _anchor.md template structure
    And Phase 3 companion files contain extracted comments with source references
    And Phase 3 commits happen per-category
    And Phase 4 produces a Critic report and cleanup commit
    And all generated features appear as TODO in CDD status

#### Scenario: Mid-Phase-3 session restart and resume

    Given the Architect is partway through Phase 3 (some categories complete, some not)
    When the agent session ends and a new session starts
    And the Architect runs /pl-spec-from-code
    Then the command detects the existing state file
    And the command resumes from the first incomplete category
    And previously generated features are not regenerated
    And the user is not re-asked earlier phase questions
