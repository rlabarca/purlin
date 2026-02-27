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
2. **Agent command:** `/pl-whats-different` -- see `features/pl_whats_different.md`.
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
- The extraction tool MUST extract **structured decision entries** from changed feature files and companion files, returning an array of objects alongside the existing `discovery_count` (kept for backward compatibility with the standard digest tags). Each entry includes:
  - `category`: tag name (e.g., `[INFEASIBLE]`, `[BUG]`, `[DEVIATION]`)
  - `feature`: feature file name the entry belongs to
  - `summary`: one-line description from the entry text
  - `role`: routed recipient (`architect` or `builder`)
- The extraction JSON output gains a new `decisions` array per direction.

**Decision categories and routing:**

| Category | Source | Routed To |
|---|---|---|
| `[INFEASIBLE]` | Companion files (`## Implementation Notes`) | Architect |
| `[DEVIATION]` | Companion files (`## Implementation Notes`) | Architect |
| `[DISCOVERY]` (impl) | Companion files (`## Implementation Notes`) | Architect |
| `[BUG]` | Feature files (`## User Testing Discoveries`) | Builder (default) or Architect (if `Action Required: Architect`) |
| `[INTENT_DRIFT]` | Feature files (`## User Testing Discoveries`) | Architect |
| `[SPEC_DISPUTE]` | Feature files (`## User Testing Discoveries`) | Architect |
| `[DISCOVERY]` (testing) | Feature files (`## User Testing Discoveries`) | Architect |

### 2.6 Agent-Powered Generation

- The dashboard invokes Claude CLI in non-interactive mode (`--print`) via a shell script.
- The shell script is the agent abstraction point -- swappable for other agents in the future.
- The extraction tool produces structured JSON; the agent (Claude) synthesizes it into plain English.
- The agent command (`/pl-whats-different`) runs the same shell script inline (see `features/pl_whats_different.md`).
- The post-merge trigger in `/pl-collab-pull` Step 7 also runs the same script.

### 2.7 Dashboard UI: Button

- The "What's Different?" button is visible in the active session panel when sync state is not SAME.
- The button is absent when there is no active session.
- When a cached digest exists, the button area shows "Last generated: `<timestamp>`" below the button.
- **Cached read:** When `features/digests/whats-different.md` exists, clicking the button opens the modal with cached content via `GET /whats-different/read`. No regeneration occurs.
- **No cache:** When no cached file exists, clicking sends `POST /whats-different/generate` and shows the "Generating" state with animated ellipsis (Section 2.8).
- A "Regenerate" button is displayed inside the modal on the same line as the "Generated:" timestamp, right-aligned. It uses the `btn-critic` class with `font-size: 10px; padding: 2px 8px`. Clicking it triggers `POST /whats-different/generate` and refreshes the modal content.

### 2.8 Dashboard UI: Modal

- The modal displays the rendered markdown digest.
- The generation date is displayed prominently at the top of the modal.
- **Timestamp formatting:**
  - The "Generated:" label is **bold** (font-weight 700).
  - The server returns an ISO 8601 UTC timestamp (e.g., `2026-02-26T20:45:00Z`).
  - The client converts using `Intl.DateTimeFormat` to the user's local timezone with AM/PM format: `MMM DD, YYYY h:mm AM/PM TZ` (e.g., "Feb 26, 2026 3:45 PM EST").
- **Animated ellipsis during generation:**
  - The "Generating" text displays dots cycling through `.` / `..` / `...` at approximately 500ms intervals.
  - Implementation may be CSS-only or minimal JS (builder's choice).
  - Text color: `var(--purlin-muted)`.
  - The same animated ellipsis pattern is reused for the "Summarize Impact" button (Section 2.14).
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

### 2.12 Dashboard Endpoints

**`GET /whats-different/read`:**

- Returns the cached digest if `features/digests/whats-different.md` exists: `{ "status": "ok", "digest": "<content>", "generated_at": "<ISO 8601 timestamp>", "tags": { ... } }`.
- Returns 404 if no cached file exists.
- Returns 400 if no active session exists.

**`POST /whats-different/generate`:**

- Triggers generation via the generation shell script.
- Returns 400 when no active session exists.
- Returns 200 with the generated content on success: `{ "status": "ok", "digest": "<content>", "generated_at": "<ISO 8601 timestamp>", "tags": { ... } }`.
- The `generated_at` field uses ISO 8601 UTC format (e.g., `2026-02-26T20:45:00Z`).

### 2.13 Dashboard Button Visibility Rules

- Button is present in the HTML when: active session exists AND sync state is not SAME.
- Button is absent from the HTML when: no active session OR sync state is SAME.

### 2.14 Deep Semantic Analysis ("Summarize Impact")

#### 2.14.1 Dashboard UI: "Summarize Impact" Button

- The "Summarize Impact" button appears on its own row, ABOVE the "What's Different?" button.
- Same visibility rules: active session exists AND sync state is not SAME.
- Same `btn-critic` styling as other dashboard action buttons.
- When a cached analysis exists, "Last generated: `<relative time>`" is displayed below the button in `var(--purlin-muted)` 12px.

#### 2.14.2 Button Click Behavior

- Clicking triggers `POST /whats-different/deep-analysis/generate`.
- The button text changes to "Summarizing" with animated ellipsis (same `.` / `..` / `...` animation at ~500ms from Section 2.8).
- The button is disabled during generation to prevent duplicate requests.
- When generation completes: button reverts to "Summarize Impact", "Last generated: just now" appears below.

#### 2.14.3 Modal Integration

- When a cached deep analysis exists, it appears in the modal ABOVE the file-level digest content.
- "Impact Summary" header in `var(--purlin-accent)` (bold).
- A horizontal rule separates the impact summary from the file-level content below.
- The impact summary section has its own "Generated:" timestamp (bold label, local timezone AM/PM format per Section 2.8) and its own "Regenerate" button (same styling as the digest Regenerate button).
- **Role-specific section header colors:**
  - **Architect Actions** header: `var(--purlin-status-warning)` (amber — attention required)
  - **Builder Actions** header: `var(--purlin-status-good)` (green — implementation work)

#### 2.14.4 Generation Pipeline

- A new script `tools/collab/generate_whats_different_deep.sh <session>` drives generation.
- Uses the same extraction tool JSON as the standard digest, but with a different LLM prompt emphasizing:
  - What functionality changed and why it matters.
  - Which workflows or user experiences are affected.
  - What specification shifts mean for the product direction.
  - What the collaborator should pay attention to.
- Output: `features/digests/whats-different-analysis.md` (gitignored).
- The file is overwritten on each generation.

**Sync state directional glossary (MUST be included in the LLM prompt):**

The LLM prompt MUST prepend a directional glossary before the JSON data so the model has correct context before interpreting the extraction output:

- **AHEAD** — Your local main has commits the collab branch does not. Action: **push** to share your work.
- **BEHIND** — The collab branch has commits your local main does not. Action: **pull** to receive their work.
- **DIVERGED** — Both sides have unique commits. Action: **pull first** (merge collab into local), then **push**.
- **SAME** — No action needed (deep analysis is not generated for SAME).

**Output format:**

The deep analysis output uses role-routed action sections instead of a flat "Action Items" list:

- **Key Changes** (unchanged)
- **Workflow Impact** (unchanged)
- **Architecture Notes** (optional, unchanged)
- **Architect Actions** — role-specific items tagged with decision categories, one line each
- **Builder Actions** — role-specific items tagged with decision categories, one line each

Each action line follows the format: `[CATEGORY] feature_name — one-line description`

When no actions exist for a role, the section header is still present with "No action items." below it.

**LLM prompt requirements:**
1. Include the sync state directional glossary above before the JSON data.
2. Read the `decisions` array from the extraction JSON.
3. Route each entry to the correct role section (Architect Actions or Builder Actions).
4. Use the exact `[CATEGORY]` tag syntax so the frontend can apply color styling.
5. Keep descriptions to one line (no multi-line explanations).
6. Never suggest "pull" when the state is AHEAD, or "push" when the state is BEHIND.

#### 2.14.5 No Agent Command

- Deep analysis is dashboard-only. In agent context, users ask conversationally.

#### 2.14.6 Decision Category Rendering

The dashboard post-processes rendered markdown in the deep analysis modal body to detect `[CATEGORY]` tags and wrap them in `<span>` elements with the corresponding color token. Tags are rendered as inline styled text (bold, colored) preceding the one-line description. Format per line: `[CATEGORY] feature_name — one-line description`

**Color mapping (using existing design tokens):**

| Category | Severity | Token (text color) | Rationale |
|---|---|---|---|
| `[INFEASIBLE]` | CRITICAL | `--purlin-status-error` | Release-blocking, requires spec revision |
| `[BUG]` | HIGH | `--purlin-status-error` | Behavior contradicts spec |
| `[SPEC_DISPUTE]` | HIGH | `--purlin-status-warning` | Spec itself questioned |
| `[INTENT_DRIFT]` | MEDIUM | `--purlin-status-warning` | Literal match, intent missed |
| `[DEVIATION]` | MEDIUM | `--purlin-accent` | Alternate path, needs acknowledgment |
| `[DISCOVERY]` | LOW | `--purlin-muted` | New finding, informational |
| `[AUTONOMOUS]` | LOW | `--purlin-muted` | Builder judgment call, FYI |

#### 2.14.7 Staleness Invalidation

The deep analysis is derived from the same extraction data as the standard digest. If the standard digest is regenerated (new extraction), any previously cached deep analysis is stale and must not be displayed.

- When `POST /whats-different/generate` succeeds (new standard digest written), the server MUST delete `features/digests/whats-different-analysis.md` if it exists. The analysis was generated from a prior extraction state and is now invalid.
- The generation shell script (`generate_whats_different.sh`) MUST delete the analysis file after writing a new digest, so both CLI and dashboard trigger paths enforce the same invariant.
- The `GET /whats-different/deep-analysis/read` endpoint already returns 404 when the file doesn't exist -- no additional endpoint changes needed.
- The modal already checks for the analysis file's existence before rendering the "Impact Summary" section -- no additional frontend changes needed.
- The "Summarize Impact" button's "Last generated" timestamp disappears when the cached file is absent (existing behavior).

**Net effect:** After regenerating the standard digest, the user must explicitly click "Summarize Impact" again to get a fresh analysis. This prevents stale analysis from appearing above a fresh digest.

### 2.15 Deep Analysis Endpoints

**`GET /whats-different/deep-analysis/read`:**

- Returns the cached analysis if `features/digests/whats-different-analysis.md` exists: `{ "status": "ok", "analysis": "<content>", "generated_at": "<ISO 8601 timestamp>" }`.
- Returns 404 if no cached file exists.
- Returns 400 if no active session exists.

**`POST /whats-different/deep-analysis/generate`:**

- Triggers generation via `tools/collab/generate_whats_different_deep.sh <session>`.
- Returns 200 with the generated analysis on success: `{ "status": "ok", "analysis": "<content>", "generated_at": "<ISO 8601 timestamp>" }`.
- Returns 400 if no active session exists.

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

#### Scenario: GET Read Endpoint Returns Cached Digest

    Given an active session "v0.5-sprint" is set
    And features/digests/whats-different.md exists on disk
    When a GET request is sent to /whats-different/read
    Then the response status is 200
    And the response body contains a "digest" field with the cached content
    And the response body contains a "generated_at" field in ISO 8601 format

#### Scenario: GET Read Endpoint Returns 404 When No Cache

    Given an active session "v0.5-sprint" is set
    And features/digests/whats-different.md does not exist
    When a GET request is sent to /whats-different/read
    Then the response status is 404

#### Scenario: GET Read Endpoint Returns 400 When No Session

    Given no file exists at .purlin/runtime/active_remote_session
    When a GET request is sent to /whats-different/read
    Then the response status is 400
    And the response body contains an error message

#### Scenario: POST Generate Endpoint Returns ISO 8601 Timestamp

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response body "generated_at" field matches ISO 8601 format

#### Scenario: POST Deep Analysis Generate Endpoint Returns Analysis

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When a POST request is sent to /whats-different/deep-analysis/generate
    Then the response status is 200
    And the response body contains an "analysis" field with the generated content
    And the response body contains a "generated_at" field in ISO 8601 format

#### Scenario: GET Deep Analysis Read Endpoint Returns Cached Analysis

    Given an active session "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response status is 200
    And the response body contains an "analysis" field with the cached content

#### Scenario: GET Deep Analysis Read Endpoint Returns 404 When No Cache

    Given an active session "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md does not exist
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response status is 404

#### Scenario: Extraction Tool Returns Structured Decisions Array

    Given a commit range that modifies features/login.impl.md containing an [INFEASIBLE] entry
    And a commit range that modifies features/auth.impl.md containing a [DEVIATION] entry
    When the extraction tool runs with the session name
    Then the output JSON contains a decisions array
    And each decision entry has category, feature, summary, and role fields
    And the [INFEASIBLE] entry has role "architect"
    And the [DEVIATION] entry has role "architect"

#### Scenario: Extraction Tool Routes BUG Entries to Builder by Default

    Given a commit range that modifies features/login.md containing a [BUG] entry in User Testing Discoveries
    And the entry does not contain "Action Required: Architect"
    When the extraction tool runs with the session name
    Then the decisions array contains the [BUG] entry with role "builder"

#### Scenario: Extraction Tool Routes INFEASIBLE Entries to Architect

    Given a commit range that modifies features/login.impl.md containing an [INFEASIBLE] entry
    When the extraction tool runs with the session name
    Then the decisions array contains the [INFEASIBLE] entry with role "architect"

#### Scenario: Standard Digest Generation Deletes Stale Deep Analysis

    Given an active session "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And features/digests/whats-different-analysis.md does not exist on disk

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

#### Scenario: Button Opens Cached Content Without Regeneration

    Given the CDD dashboard is open
    And an active session exists with BEHIND sync state
    And features/digests/whats-different.md exists on disk
    When the User clicks the "What's Different?" button
    Then the modal opens immediately with the cached digest content
    And no POST request is sent to /whats-different/generate

#### Scenario: Regenerate Button Inside Modal Triggers Fresh Generation

    Given the What's Different modal is open with cached content
    When the User clicks the "Regenerate" button
    Then a POST request is sent to /whats-different/generate
    And the modal shows the animated "Generating" ellipsis state
    And after generation completes the modal displays the fresh content

#### Scenario: Animated Ellipsis During Generation

    Given the CDD dashboard is open
    And an active session exists with BEHIND sync state
    And no cached digest exists
    When the User clicks the "What's Different?" button
    Then the modal shows "Generating" text with dots cycling through . / .. / ... at ~500ms intervals
    And the text color is var(--purlin-muted)

#### Scenario: Timestamp Shows Local Time With AM/PM and Timezone

    Given the What's Different modal is open with generated content
    When the User views the generation timestamp
    Then the "Generated:" label is bold (font-weight 700)
    And the timestamp is displayed in local timezone with AM/PM format (e.g., "Feb 26, 2026 3:45 PM EST")

#### Scenario: Summarize Impact Button Placement Above What's Different

    Given the CDD dashboard is open
    And an active session exists with BEHIND sync state
    When the User views the active session panel
    Then a "Summarize Impact" button is visible above the "What's Different?" button
    And the button follows the same visibility rules as "What's Different?"

#### Scenario: Impact Summary Content Appears Above File-Level Digest in Modal

    Given the What's Different modal is open
    And a cached deep analysis exists at features/digests/whats-different-analysis.md
    When the User views the modal content
    Then the "Impact Summary" section appears above the file-level digest
    And the "Impact Summary" header is in var(--purlin-accent), bold
    And a horizontal rule separates the impact summary from the file-level content
    And the impact summary has its own "Generated:" timestamp and "Regenerate" button

#### Scenario: End-to-End Deep Analysis Generation via Dashboard

    Given the CDD dashboard is open
    And an active session exists in BEHIND state
    When the User clicks the "Summarize Impact" button
    Then the button text changes to "Summarizing" with animated ellipsis
    And the button is disabled during generation
    And after generation completes the button reverts to "Summarize Impact"
    And "Last generated: just now" appears below the button

#### Scenario: Auto-Generation After pl-collab-pull Merge

    Given the agent is on the main branch
    And an active session exists in BEHIND state
    When the agent runs /pl-collab-pull and the merge succeeds
    Then the digest is auto-generated as Step 7
    And the digest content is displayed inline after the merge summary

#### Scenario: Deep Analysis Architect Actions Display Category Tags With Correct Colors

    Given the What's Different modal is open
    And a cached deep analysis exists with Architect Actions containing [INFEASIBLE] and [INTENT_DRIFT] entries
    When the User views the impact summary section
    Then the "Architect Actions" header is in var(--purlin-status-warning)
    And the [INFEASIBLE] tag is rendered in var(--purlin-status-error)
    And the [INTENT_DRIFT] tag is rendered in var(--purlin-status-warning)

#### Scenario: Deep Analysis Builder Actions Display Category Tags With Correct Colors

    Given the What's Different modal is open
    And a cached deep analysis exists with Builder Actions containing [BUG] entries
    When the User views the impact summary section
    Then the "Builder Actions" header is in var(--purlin-status-good)
    And the [BUG] tag is rendered in var(--purlin-status-error)

#### Scenario: Stale Impact Summary Absent After Digest Regeneration

    Given the What's Different modal is open with both a cached digest and a cached deep analysis
    When the User clicks "Regenerate" on the standard digest
    And the digest regeneration completes
    Then the impact summary section is absent from the modal
    And the "Summarize Impact" button no longer shows a "Last generated" timestamp

---

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: CDD Dashboard -- What's Different? Button

- **Reference:** N/A
- **Processed:** N/A
- **Description:** The "What's Different?" button is rendered within the active session panel of the REMOTE COLLABORATION section, below the sync state row. The button uses standard dashboard button styling with `var(--font-body)` Inter 500 14px text. When a cached digest exists, a "Last generated: `<timestamp>`" line appears below the button in `var(--purlin-muted)` Inter 400 12px. The button is hidden when sync state is SAME or when no active session exists.
- [ ] "Summarize Impact" button visible above "What's Different?" button (same visibility rules)
- [ ] "Last generated" timestamp below "Summarize Impact" when cached analysis exists
- [ ] "Summarize Impact" button text changes to animated "Summarizing." / "Summarizing.." / "Summarizing..." during generation
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
- [ ] "Generated:" label bold (font-weight 700)
- [ ] Timestamp in local timezone with AM/PM (e.g., "Feb 26, 2026 3:45 PM EST")
- [ ] "Generating" shows animated cycling ellipsis (`.` / `..` / `...`) at ~500ms
- [ ] "Regenerate" button on same line as timestamp, right-aligned
- [ ] Clicking button with cached digest opens modal immediately (no regeneration)
- [ ] Impact summary section above file-level content when present
- [ ] "Impact Summary" header in `var(--purlin-accent)`, bold
- [ ] Horizontal rule between impact summary and file-level content
- [ ] Impact summary has own "Generated:" timestamp and "Regenerate" button
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
- [ ] "Architect Actions" section header color: `var(--purlin-status-warning)`
- [ ] "Builder Actions" section header color: `var(--purlin-status-good)`
- [ ] Decision category tags `[INFEASIBLE]` and `[BUG]` rendered in `var(--purlin-status-error)`
- [ ] Decision category tags `[SPEC_DISPUTE]` and `[INTENT_DRIFT]` rendered in `var(--purlin-status-warning)`
- [ ] Decision category tag `[DEVIATION]` rendered in `var(--purlin-accent)`
- [ ] Decision category tags `[DISCOVERY]` and `[AUTONOMOUS]` rendered in `var(--purlin-muted)`
- [ ] Each action item is a single line: `[CATEGORY] feature — description`
- [ ] Modal body markdown rendered with proper formatting (lists, headers, code blocks)
- [ ] Close via X button, Escape, or click outside modal
