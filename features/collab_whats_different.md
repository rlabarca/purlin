# Feature: What's Different? (Collaboration Digest)

> Label: "CDD: What's Different?"
> Category: "CDD Dashboard"
> Prerequisite: features/cdd_remote_collab.md
> Prerequisite: features/design_visual_standards.md

[TODO]

## 1. Overview

When collaborators are out of sync with the remote collab branch (AHEAD, BEHIND, or DIVERGED), there is no human-readable way to understand what changed. The "What's Different?" feature compares local main vs the collab branch in both directions, uses an LLM agent to synthesize a plain-English summary, and makes it available from the CDD dashboard and via agent command. The summary orients a collaborator on what features changed, what specs shifted, whether feedback was addressed, and what needs testing.

---

## 2. Requirements

### 2.1 Output File and Lifecycle

- The generated digest is written to `features/digests/whats-different.md`.
- The `features/digests/` directory is gitignored (per-machine artifact, not committed).
- The file is overwritten on each generation. No versioned history is kept.
- If the file does not exist, no cached digest is available.

### 2.2 Trigger Points

The digest can be generated from three trigger points:

1. **CDD dashboard:** A "What's Different?" button in the active session panel (Section 2.3 of `cdd_remote_collab.md`) triggers fresh generation.
2. **Agent command:** `/pl-whats-different` is a standalone command usable by any role from the main checkout.
3. **Post-merge auto-generation:** After a successful merge in `/pl-collab-pull`, a new Step 7 auto-generates the digest.

### 2.3 Direction-Dependent Content Structure

The digest content varies by sync state:

- **AHEAD:** Only a "Your Local Changes" section (what local main has that collab does not).
- **BEHIND:** Only a "Collab Changes" section (what collab has that local main does not).
- **DIVERGED:** Both "Your Local Changes" and "Collab Changes" sections.
- **SAME:** A short "in sync" message. The dashboard button is hidden when sync state is SAME.

### 2.4 Content Sections (Per Direction)

Each direction (Your Local / Collab) is split into two halves: what changed in the specs vs what changed in the code. This mirrors the CDD philosophy that specs are the source of truth and code follows.

#### Spec Changes ("What Should Change")

- **Feature specs:** Added, modified, or deleted feature files, with plain-language descriptions of what the changes mean.
- **Anchor and policy nodes:** What changed and what it implies for product direction.
- **Visual specs:** What users will notice differently.
- **Discoveries:** New BUG, SPEC_DISPUTE, INTENT_DRIFT, or DISCOVERY entries and their status.
- **Status transitions:** Features that moved lifecycle state (TODO to TESTING, TESTING to COMPLETE, etc.).

#### Code Changes ("What Did Change")

- **Implementation files:** Source code, scripts, and tools (grouped by area, not individually listed unless the changeset is small).
- **Tests:** New or modified test files.
- **Companion files (`.impl.md`):** Implementation notes that were added or updated.

#### Purlin Changes (Framework and Process)

- A separate section for `.purlin/` directory changes (config, overrides, release config) AND Purlin submodule updates.
- Explains what the changes mean for agent behavior or workflow (e.g., "builder startup sequence was disabled", "new release step added", "Purlin submodule updated to v0.6 with new collaboration features").
- Not mixed with spec or code changes -- these are framework and process configuration shifts.

#### Sync Check (Per Direction, at Bottom)

- Flag any spec that changed without corresponding code changes (spec leads, code may lag).
- Flag any code area that changed without a corresponding spec change (code may have drifted).
- This is informational, not blocking -- orientation for the reader.

#### At a Glance (After Both Directions)

- Summary table: commits, spec changes, code changes per side.

### 2.5 Extraction Tool

- A Python extraction tool produces structured JSON from git range queries.
- Input: two commit ranges (local ahead range, remote ahead range), either or both of which may be empty.
- Output: structured JSON categorizing changed files into specs, code, tests, companion files, purlin config, and submodule changes.
- Feature file changes are further categorized: feature specs vs anchor nodes vs policy nodes.
- Status commits (matching `[Complete ...]` or `[TODO]` patterns in commit messages) are parsed into lifecycle transitions.

### 2.6 Agent-Powered Generation

- The dashboard invokes Claude CLI in non-interactive mode (`--print`) via a shell script.
- The shell script is the agent abstraction point -- swappable for other agents in the future.
- The extraction tool produces structured JSON; the agent (Claude) synthesizes it into plain English.
- The agent command (`/pl-whats-different`) runs the same shell script inline.
- The post-merge trigger in `/pl-collab-pull` Step 7 also runs the same script.

### 2.7 Dashboard UI: Button

- The "What's Different?" button is visible in the active session panel when sync state is not SAME.
- The button is absent when there is no active session.
- When a cached digest exists, the button area shows "Last generated: `<timestamp>`" below the button.
- Button click sends a POST request to a generation endpoint, then opens a modal with "Generating..." state.

### 2.8 Dashboard UI: Modal

- The modal displays the rendered markdown digest.
- The generation date is displayed prominently at the top of the modal.
- Close behavior: X button, Escape key, or click outside the modal.
- Follows existing CDD modal patterns: 700px max-width, 80vh max-height, scrollable body.
- Modal body uses `.modal-body` markdown CSS for rendered content.

### 2.9 Dashboard UI: Change Tags Bar

Below the modal title and date, a row of highlighted tag boxes gives an instant visual summary of the change landscape before the user reads the full report. Tags use the existing `.st-*` badge styling and `--purlin-tag-fill`/`--purlin-tag-outline` tokens.

Tags appear only when their count is greater than 0. Each tag has a specific text color from the design token system:

| Tag | Token (text color) | Rationale |
|-----|-------------------|-----------|
| `[N Specs]` | `--purlin-accent` | Source of truth -- most important in CDD |
| `[N Anchor]` | `--purlin-status-warning` | Cascading impact -- anchor changes reset dependent features |
| `[N Visual]` | `--purlin-status-good` | User-facing -- visible product improvements |
| `[N Code]` | `--purlin-primary` | Core implementation -- neutral, expected work |
| `[N Tests]` | `--purlin-muted` | Supporting verification -- important but secondary |
| `[N Purlin]` | `--purlin-status-todo` | Framework/process shift -- affects agent behavior |
| `[N Discovery]` | `--purlin-status-error` | Problems found -- BUG/DISPUTE/DRIFT needs attention |

"Purlin" covers both `.purlin/` directory changes (config, overrides, release config) and Purlin submodule updates -- framework shifts that affect how agents behave, not what the product does.

When DIVERGED, tags aggregate both directions (total across local and collab). The full breakdown per direction is in the body.

**Tag styling:** Small rounded pill badges in a flex-wrap row. All tags use `--purlin-tag-fill` background and `--purlin-tag-outline` border (existing dashboard tag pattern). The text color varies per tag as shown above. Tag text is Inter 700 (Bold) 12px per the typography standard.

### 2.10 Dashboard UI: Section Header Colors

The three major content sections in the modal body use color-coded headers to match their domain:

- **Spec Changes** header: `--purlin-accent` (blue)
- **Code Changes** header: `--purlin-status-good` (green)
- **Purlin Changes** header: `--purlin-status-todo` (yellow)

This creates a visual map: scan the tags for "what changed," then jump to the matching colored section for details.

### 2.11 Post-Merge Integration (pl-collab-pull Step 7)

After a successful merge in `/pl-collab-pull` (BEHIND fast-forward or DIVERGED merge), a new Step 7 runs:

1. Execute the generation shell script to produce the digest.
2. Read and display the generated markdown inline in the agent output.
3. This step is informational -- it does not block or fail the pull.

### 2.12 Dashboard Endpoint

- `POST /whats-different/generate` triggers generation.
- Returns 400 when no active session exists.
- Returns 200 with the generated content on success.
- The endpoint invokes the generation shell script and returns the result.

### 2.13 Dashboard Button Visibility Rules

- Button is present in the HTML when: active session exists AND sync state is not SAME.
- Button is absent from the HTML when: no active session OR sync state is SAME.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Extraction Tool Produces Correct JSON for SAME State

    Given local main and origin/collab/session are at the same commit
    When the extraction tool runs with the session name
    Then the output JSON has empty arrays for both local_changes and collab_changes
    And the sync_state field is "SAME"

#### Scenario: Extraction Tool Produces Correct JSON for AHEAD State

    Given local main has 3 commits not in origin/collab/session
    And origin/collab/session has 0 commits not in local main
    When the extraction tool runs with the session name
    Then the output JSON has entries in local_changes
    And collab_changes is an empty array
    And the sync_state field is "AHEAD"

#### Scenario: Extraction Tool Produces Correct JSON for BEHIND State

    Given origin/collab/session has 2 commits not in local main
    And local main has 0 commits not in origin/collab/session
    When the extraction tool runs with the session name
    Then the output JSON has entries in collab_changes
    And local_changes is an empty array
    And the sync_state field is "BEHIND"

#### Scenario: Extraction Tool Produces Correct JSON for DIVERGED State

    Given local main has 1 commit not in origin/collab/session
    And origin/collab/session has 2 commits not in local main
    When the extraction tool runs with the session name
    Then the output JSON has entries in both local_changes and collab_changes
    And the sync_state field is "DIVERGED"

#### Scenario: Feature File Changes Correctly Categorized

    Given a commit range that modifies features/login.md, features/arch_data_layer.md, and features/login.impl.md
    When the extraction tool categorizes the changed files
    Then features/login.md is categorized as a feature spec change
    And features/arch_data_layer.md is categorized as an anchor node change
    And features/login.impl.md is categorized as a companion file change

#### Scenario: Status Commits Parsed Into Lifecycle Transitions

    Given a commit with message "[Complete features/login.md] [Scope: full]"
    And a commit with message "spec(auth): add edge-case scenarios"
    When the extraction tool parses the commit messages
    Then a lifecycle transition is recorded for login.md from TESTING to COMPLETE
    And no lifecycle transition is recorded for the spec commit

#### Scenario: Dashboard Endpoint Returns 400 When No Active Session

    Given no file exists at .purlin/runtime/active_remote_session
    When a POST request is sent to /whats-different/generate
    Then the response status is 400
    And the response body contains an error message

#### Scenario: Dashboard Endpoint Returns 200 After Generation

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response body contains the generated markdown content
    And features/digests/whats-different.md exists on disk

#### Scenario: Dashboard HTML Includes Button When Sync State Is Not SAME

    Given an active session "v0.5-sprint" is set
    And the sync state is BEHIND
    When the dashboard HTML is generated
    Then the active session panel contains a "What's Different?" button

#### Scenario: Dashboard HTML Omits Button When Sync State Is SAME

    Given an active session "v0.5-sprint" is set
    And local main and origin/collab/v0.5-sprint are at the same commit
    When the dashboard HTML is generated
    Then the active session panel does not contain a "What's Different?" button

#### Scenario: Dashboard HTML Omits Button When No Active Session

    Given no active remote session exists
    When the dashboard HTML is generated
    Then no "What's Different?" button is present in the HTML

#### Scenario: Generated Markdown File Exists After Generation

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has commits not in local main
    When the generation script is executed
    Then features/digests/whats-different.md exists
    And the file contains a date header
    And the file contains a "Collab Changes" section

### Manual Scenarios (Human Verification Required)

#### Scenario: Modal Typography and Layout

    Given the CDD dashboard is open
    And an active session exists with BEHIND sync state
    When the User clicks the "What's Different?" button
    Then a modal appears with 700px max-width and scrollable body
    And the generation date is displayed prominently at the top
    And the modal body renders markdown with proper formatting

#### Scenario: Modal Close Behavior

    Given the What's Different modal is open
    When the User presses Escape
    Then the modal closes
    When the User clicks outside the modal
    Then the modal closes
    When the User clicks the X button
    Then the modal closes

#### Scenario: Change Tags Bar Displays Correct Colors

    Given the What's Different modal is open
    And the digest includes spec changes, code changes, and discoveries
    When the User views the tag bar below the title
    Then Specs tags use --purlin-accent text color
    And Code tags use --purlin-primary text color
    And Discovery tags use --purlin-status-error text color
    And all tags use --purlin-tag-fill background and --purlin-tag-outline border

#### Scenario: Section Header Colors Match Domain

    Given the What's Different modal is open with a DIVERGED digest
    When the User scrolls through the modal body
    Then the "Spec Changes" header uses --purlin-accent color
    And the "Code Changes" header uses --purlin-status-good color
    And the "Purlin Changes" header uses --purlin-status-todo color

#### Scenario: Button Placement in Active Session Panel

    Given the CDD dashboard is open
    And an active session exists with AHEAD sync state
    When the User views the active session panel
    Then a "What's Different?" button is visible
    And "Last generated: <timestamp>" is shown below the button when a cached digest exists

#### Scenario: End-to-End DIVERGED Generation via Dashboard

    Given the CDD dashboard is open
    And an active session exists in DIVERGED state
    When the User clicks the "What's Different?" button
    Then the modal shows "Generating..." state
    And after generation completes the modal displays both "Your Local Changes" and "Collab Changes" sections
    And change tags appear in the tag bar
    And a sync check section appears at the bottom of each direction

#### Scenario: End-to-End Generation via Agent Command

    Given the agent is on the main branch
    And an active session exists in BEHIND state
    When the agent runs /pl-whats-different
    Then the generated digest is displayed inline
    And features/digests/whats-different.md is written to disk

#### Scenario: Auto-Generation After pl-collab-pull Merge

    Given the agent is on the main branch
    And an active session exists in BEHIND state
    When the agent runs /pl-collab-pull and the merge succeeds
    Then the digest is auto-generated as Step 7
    And the digest content is displayed inline after the merge summary

---

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: CDD Dashboard -- What's Different? Button

- **Reference:** N/A
- **Processed:** N/A
- **Description:** The "What's Different?" button is rendered within the active session panel of the REMOTE COLLABORATION section, below the sync state row. The button uses standard dashboard button styling with `var(--font-body)` Inter 500 14px text. When a cached digest exists, a "Last generated: `<timestamp>`" line appears below the button in `var(--purlin-muted)` Inter 400 12px. The button is hidden when sync state is SAME or when no active session exists.
- [ ] Button visible in active session panel when sync state is AHEAD, BEHIND, or DIVERGED
- [ ] Button hidden when sync state is SAME
- [ ] Button absent when no active session
- [ ] "Last generated" timestamp shown below button when cached digest exists, in `var(--purlin-muted)` 12px
- [ ] Button styling consistent with other dashboard action buttons

### Screen: CDD Dashboard -- What's Different? Modal

- **Reference:** N/A
- **Processed:** N/A
- **Description:** The modal follows the existing CDD modal pattern (Feature Detail Modal, Kill modal, Delete Confirmation Modal). Max-width 700px, max-height 80vh, scrollable body. The modal header contains the title "What's Different?" and the generation date in `var(--purlin-muted)`. Below the title and date, a change tags bar displays pill-shaped tag badges in a flex-wrap row. Each tag uses `var(--purlin-tag-fill)` background and `var(--purlin-tag-outline)` border with domain-specific text colors. The modal body renders the markdown digest with `.modal-body` CSS. Section headers for Spec Changes, Code Changes, and Purlin Changes use domain-specific colors.
- [ ] Modal max-width 700px, max-height 80vh, scrollable body
- [ ] Modal overlay and container match existing CDD modal pattern
- [ ] Title "What's Different?" in modal header
- [ ] Generation date displayed prominently below title in `var(--purlin-muted)`
- [ ] "Generating..." state shown while generation is in progress
- [ ] Change tags bar: flex-wrap row of pill badges below title and date
- [ ] Tags use `var(--purlin-tag-fill)` background and `var(--purlin-tag-outline)` border
- [ ] `[N Specs]` tag text color: `var(--purlin-accent)`
- [ ] `[N Anchor]` tag text color: `var(--purlin-status-warning)`
- [ ] `[N Visual]` tag text color: `var(--purlin-status-good)`
- [ ] `[N Code]` tag text color: `var(--purlin-primary)`
- [ ] `[N Tests]` tag text color: `var(--purlin-muted)`
- [ ] `[N Purlin]` tag text color: `var(--purlin-status-todo)`
- [ ] `[N Discovery]` tag text color: `var(--purlin-status-error)`
- [ ] Tag text: Inter 700 (Bold) 12px
- [ ] Tags only appear when count > 0
- [ ] DIVERGED state: tags aggregate both directions
- [ ] Spec Changes section header color: `var(--purlin-accent)`
- [ ] Code Changes section header color: `var(--purlin-status-good)`
- [ ] Purlin Changes section header color: `var(--purlin-status-todo)`
- [ ] Modal body markdown rendered with proper formatting (lists, headers, code blocks)
- [ ] Close via X button, Escape, or click outside modal
