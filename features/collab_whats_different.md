# Feature: What's Different? (Collaboration Digest)

> Label: "CDD: What's Different?"
> Category: "CDD Dashboard"
> Prerequisite: features/cdd_branch_collab.md
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/cdd_modal_base.md
> Web Test: http://localhost:9086
> Web Start: /pl-cdd

[TODO]

## 1. Overview

When collaborators are out of sync with the remote collab branch (AHEAD, BEHIND, or DIVERGED), there is no human-readable way to understand what changed. The "What's Different?" feature compares the local collab branch vs the remote collab branch in both directions, uses an LLM agent to synthesize a plain-English summary, and makes it available from the CDD dashboard and via agent command. The summary orients a collaborator on what features changed, what specs shifted, whether feedback was addressed, and what needs testing.

---

## 2. Requirements

### 2.1 Output File and Lifecycle

- The generated digest is written to `features/digests/whats-different.md`.
- The `features/digests/` directory is gitignored (per-machine artifact, not committed).
- The file is overwritten on each generation. No versioned history is kept.
- If the file does not exist, no cached digest is available.

### 2.2 Trigger Points

The digest can be generated from two trigger points:

1. **CDD dashboard:** A "What's Different?" button in the active branch panel (Section 2.3 of `cdd_branch_collab.md`) triggers fresh generation.
2. **Post-merge auto-generation:** After a successful merge in `/pl-remote-pull`, a new Step 7 auto-generates the digest.

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
| `[BUG]` | Discovery sidecar files (`<name>.discoveries.md`) | Builder (default) or Architect (if `Action Required: Architect`) |
| `[INTENT_DRIFT]` | Discovery sidecar files (`<name>.discoveries.md`) | Architect |
| `[SPEC_DISPUTE]` | Discovery sidecar files (`<name>.discoveries.md`) | Architect |
| `[DISCOVERY]` (testing) | Discovery sidecar files (`<name>.discoveries.md`) | Architect |

**Purlin infrastructure file classification:**

Files installed by the Purlin framework into the consumer project root or `.claude/` directory -- but outside `.purlin/` and the submodule -- MUST be classified as `purlin_config` (not `code`). These files are framework infrastructure, not application code. The extraction tool MUST recognize the following patterns:

- **Bootstrap-installed launchers:** Root-level files matching `pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`.
- **Purlin command files:** Files under `.claude/commands/` with a `pl-` prefix (e.g., `.claude/commands/pl-status.md`). These are Purlin slash command definitions distributed by bootstrap.

All matched files are classified as `purlin_config`, which rolls up to the `[N Purlin]` tag in the dashboard. This ensures Purlin framework changes are reported in the "Purlin Changes" section, not mixed with application code in "Code Changes".

### 2.6 Agent-Powered Generation

- The dashboard invokes Claude CLI in non-interactive mode (`--print`) via a shell script.
- The shell script is the agent abstraction point -- swappable for other agents in the future.
- The extraction tool produces structured JSON; the agent (Claude) synthesizes it into plain English.
- The post-merge trigger in `/pl-remote-pull` Step 7 also runs the same script.

### 2.7 Dashboard UI: Button

- The "What's Different?" button is visible in the active branch panel when sync state is not SAME.
- The button is absent when there is no active branch.
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
- Close behavior: inherited from `cdd_modal_base.md` (X button, Escape key, click outside modal).
- Inherits shared modal infrastructure from `cdd_modal_base.md`: 70vw width, 80vh max-height, scrollable body, font size control, title sizing, theme integration.
- Modal body uses `.modal-body` markdown CSS for rendered content.

### 2.9 Dashboard UI: Change Tags Bar

Below the modal title and date, a row of highlighted tag boxes gives an instant visual summary of the change landscape before the user reads the full report. Tags use the existing `.st-*` badge styling and `--purlin-tag-fill`/`--purlin-tag-outline` tokens.

Tags appear only when their count is greater than 0. Each tag has a specific text color from the design token system:

| Tag | Token (text color) | Section |
|-----|-------------------|---------|
| `[N Specs]` | `--purlin-accent` | Spec Changes |
| `[N Anchor]` | `--purlin-accent` | Spec Changes |
| `[N Visual]` | `--purlin-accent` | Spec Changes |
| `[N Code]` | `--purlin-status-good` | Code Changes |
| `[N Tests]` | `--purlin-status-good` | Code Changes |
| `[N Purlin]` | `--purlin-status-todo` | Purlin Changes |
| `[N Discovery]` | `--purlin-accent` | Spec Changes |

"Purlin" covers both `.purlin/` directory changes (config, overrides, release config) and Purlin submodule updates -- framework shifts that affect how agents behave, not what the product does.

When DIVERGED, tags aggregate both directions (total across local and collab). The full breakdown per direction is in the body.

**Tag styling:** Small rounded pill badges in a flex-wrap row. All tags use `--purlin-tag-fill` background and `--purlin-tag-outline` border (existing dashboard tag pattern). The text color varies per tag as shown above. Tag text is Inter 700 (Bold) 12px per the typography standard.

### 2.10 Dashboard UI: Section Header Colors

The three major content sections in the modal body use color-coded headers to match their domain:

- **Spec Changes** header: `--purlin-accent` (blue)
- **Code Changes** header: `--purlin-status-good` (green)
- **Purlin Changes** header: `--purlin-status-todo` (yellow)

This creates a visual map: scan the tags for "what changed," then jump to the matching colored section for details.

### 2.11 Post-Merge Integration (pl-remote-pull Step 7)

After a successful merge in `/pl-remote-pull` (BEHIND fast-forward or DIVERGED merge), a new Step 7 runs:

1. Execute the generation shell script to produce the digest.
2. Read and display the generated markdown inline in the agent output.
3. This step is informational -- it does not block or fail the pull.

### 2.12 Dashboard Endpoints

**`GET /whats-different/read`:**

- Returns the cached digest if `features/digests/whats-different.md` exists: `{ "status": "ok", "digest": "<content>", "generated_at": "<ISO 8601 timestamp>", "tags": { ... } }`.
- Returns 404 if no cached file exists.
- Returns 400 if no active branch exists.

**`POST /whats-different/generate`:**

- Triggers generation via the generation shell script.
- Returns 400 when no active branch exists.
- Returns 200 with the generated content on success: `{ "status": "ok", "digest": "<content>", "generated_at": "<ISO 8601 timestamp>", "tags": { ... } }`.
- The `generated_at` field uses ISO 8601 UTC format (e.g., `2026-02-26T20:45:00Z`).

### 2.13 Dashboard Button Visibility Rules

- Button is present in the HTML when: active branch exists AND sync state is not SAME.
- Button is absent from the HTML when: no active branch OR sync state is SAME.

### 2.14 Deep Semantic Analysis ("Summarize Impact")

#### 2.14.1 Modal UI: "Summarize Impact" Button

- The "Summarize Impact" button appears inside the What's Different? modal, above the digest content.
- The button is visible whenever the modal is open and no cached analysis exists (when a cached analysis exists, the impact summary section replaces the button).
- Same `btn-critic` styling as other dashboard action buttons.
- When a cached analysis exists, the impact summary section (Section 2.14.3) is shown instead of the button. The impact summary section includes its own "Regenerate" button to refresh the analysis.

#### 2.14.2 Button Click Behavior

- Clicking the "Summarize Impact" button (inside the modal) triggers `POST /whats-different/deep-analysis/generate`.
- The button text changes to "Summarizing" with animated ellipsis (same `.` / `..` / `...` animation at ~500ms from Section 2.8).
- The button is disabled during generation to prevent duplicate requests.
- When generation completes: the button is replaced by the impact summary section (Section 2.14.3) with the generated content, its own "Generated:" timestamp, and a "Regenerate" button.

#### 2.14.3 Modal Integration

- When a cached deep analysis exists, it appears in the modal ABOVE the file-level digest content.
- "Impact Summary" header in `var(--purlin-accent)` (bold).
- A horizontal rule separates the impact summary from the file-level content below.
- The impact summary section has its own "Generated:" timestamp (bold label, local timezone AM/PM format per Section 2.8) and its own "Regenerate" button (same styling as the digest Regenerate button).
- **Role-specific section header colors:**
  - **Architect Actions** header: `var(--purlin-status-warning)` (amber — attention required)
  - **Builder Actions** header: `var(--purlin-status-good)` (green — implementation work)

#### 2.14.4 Generation Pipeline

- A new script `tools/collab/generate_whats_different_deep.sh <branch>` drives generation.
- Uses the same extraction tool JSON as the standard digest, but with a different LLM prompt emphasizing:
  - What functionality changed and why it matters.
  - Which workflows or user experiences are affected.
  - What specification shifts mean for the product direction.
  - What the collaborator should pay attention to.
- Output: `features/digests/whats-different-analysis.md` (gitignored).
- The file is overwritten on each generation.

**Sync state directional glossary (MUST be included in the LLM prompt):**

The LLM prompt MUST prepend a directional glossary before the JSON data so the model has correct context before interpreting the extraction output:

- **AHEAD** — Your local collab branch has commits the remote collab branch does not. Action: **push** to share your work.
- **BEHIND** — The remote collab branch has commits your local collab branch does not. Action: **pull** to receive their work.
- **DIVERGED** — Both sides have unique commits. Action: **pull first** (merge remote into local collab branch), then **push**.
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
- Returns 400 if no active branch exists.

**`POST /whats-different/deep-analysis/generate`:**

- Triggers generation via `tools/collab/generate_whats_different_deep.sh <branch>`.
- Returns 200 with the generated analysis on success: `{ "status": "ok", "analysis": "<content>", "generated_at": "<ISO 8601 timestamp>" }`.
- Returns 400 if no active branch exists.

### 2.16 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/collab_whats_different/divergent-branches` | Main and collab branches with different file changes for testing diff extraction |

---

## 3. Scenarios

### Unit Tests
#### Scenario: Extraction Tool Produces Correct JSON for SAME State

    Given local the collaboration branch (from .purlin/runtime/active_branch) and origin/the collaboration branch (from .purlin/runtime/active_branch) are at the same commit
    When the extraction tool runs with the branch name
    Then the output JSON has empty arrays for both local_changes and collab_changes
    And the sync_state field is "SAME"

#### Scenario: Extraction Tool Produces Correct JSON for AHEAD State

    Given local the collaboration branch (from .purlin/runtime/active_branch) has 3 commits not in origin/the collaboration branch (from .purlin/runtime/active_branch)
    And origin/the collaboration branch (from .purlin/runtime/active_branch) has 0 commits not in local the collaboration branch (from .purlin/runtime/active_branch)
    When the extraction tool runs with the branch name
    Then the output JSON has entries in local_changes
    And collab_changes is an empty array
    And the sync_state field is "AHEAD"

#### Scenario: Extraction Tool Produces Correct JSON for BEHIND State

    Given origin/the collaboration branch (from .purlin/runtime/active_branch) has 2 commits not in local the collaboration branch (from .purlin/runtime/active_branch)
    And local the collaboration branch (from .purlin/runtime/active_branch) has 0 commits not in origin/the collaboration branch (from .purlin/runtime/active_branch)
    When the extraction tool runs with the branch name
    Then the output JSON has entries in collab_changes
    And local_changes is an empty array
    And the sync_state field is "BEHIND"

#### Scenario: Extraction Tool Produces Correct JSON for DIVERGED State

    Given local the collaboration branch (from .purlin/runtime/active_branch) has 1 commit not in origin/the collaboration branch (from .purlin/runtime/active_branch)
    And origin/the collaboration branch (from .purlin/runtime/active_branch) has 2 commits not in local the collaboration branch (from .purlin/runtime/active_branch)
    When the extraction tool runs with the branch name
    Then the output JSON has entries in both local_changes and collab_changes
    And the sync_state field is "DIVERGED"

#### Scenario: Feature File Changes Correctly Categorized

    Given a commit range that modifies features/login.md, features/arch_data_layer.md, and features/login.impl.md
    When the extraction tool categorizes the changed files
    Then features/login.md is categorized as a feature spec change
    And features/arch_data_layer.md is categorized as an anchor node change
    And features/login.impl.md is categorized as a companion file change

#### Scenario: Purlin Infrastructure Files Classified as purlin_config

    Given a commit range that modifies pl-run-builder.sh, pl-run-feat1-architect.sh, and .claude/commands/pl-status.md
    When the extraction tool categorizes the changed files
    Then pl-run-builder.sh is categorized as purlin_config
    And pl-run-feat1-architect.sh is categorized as purlin_config
    And .claude/commands/pl-status.md is categorized as purlin_config
    And none of these files appear in the code category

#### Scenario: Status Commits Parsed Into Lifecycle Transitions

    Given a commit with message "[Complete features/login.md] [Scope: full]"
    And a commit with message "spec(auth): add edge-case scenarios"
    When the extraction tool parses the commit messages
    Then a lifecycle transition is recorded for login.md from TESTING to COMPLETE
    And no lifecycle transition is recorded for the spec commit

#### Scenario: Dashboard Endpoint Returns 400 When No Active Session

    Given no file exists at .purlin/runtime/active_branch
    When a POST request is sent to /whats-different/generate
    Then the response status is 400
    And the response body contains an error message

#### Scenario: Dashboard Endpoint Returns 200 After Generation

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response body contains the generated markdown content
    And features/digests/whats-different.md exists on disk

#### Scenario: Dashboard HTML Includes Button When Sync State Is Not SAME

    Given an active branch "v0.5-sprint" is set
    And the sync state is BEHIND
    When the dashboard HTML is generated
    Then the active branch panel contains a "What's Different?" button

#### Scenario: Dashboard HTML Omits Button When Sync State Is SAME

    Given an active branch "v0.5-sprint" is set
    And local collab/v0.5-sprint and origin/collab/v0.5-sprint are at the same commit
    When the dashboard HTML is generated
    Then the active branch panel does not contain a "What's Different?" button

#### Scenario: Dashboard HTML Omits Button When No Active Session

    Given no active branch exists
    When the dashboard HTML is generated
    Then no "What's Different?" button is present in the HTML

#### Scenario: Generated Markdown File Exists After Generation

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has commits not in local collab/v0.5-sprint
    When the generation script is executed
    Then features/digests/whats-different.md exists
    And the file contains a date header
    And the file contains a "Collab Changes" section

#### Scenario: GET Read Endpoint Returns Cached Digest

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different.md exists on disk
    When a GET request is sent to /whats-different/read
    Then the response status is 200
    And the response body contains a "digest" field with the cached content
    And the response body contains a "generated_at" field in ISO 8601 format

#### Scenario: GET Read Endpoint Returns 404 When No Cache

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different.md does not exist
    When a GET request is sent to /whats-different/read
    Then the response status is 404

#### Scenario: GET Read Endpoint Returns 400 When No Session

    Given no file exists at .purlin/runtime/active_branch
    When a GET request is sent to /whats-different/read
    Then the response status is 400
    And the response body contains an error message

#### Scenario: POST Generate Endpoint Returns ISO 8601 Timestamp

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response body "generated_at" field matches ISO 8601 format

#### Scenario: POST Deep Analysis Generate Endpoint Returns Analysis

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When a POST request is sent to /whats-different/deep-analysis/generate
    Then the response status is 200
    And the response body contains an "analysis" field with the generated content
    And the response body contains a "generated_at" field in ISO 8601 format

#### Scenario: GET Deep Analysis Read Endpoint Returns Cached Analysis

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response status is 200
    And the response body contains an "analysis" field with the cached content

#### Scenario: GET Deep Analysis Read Endpoint Returns 404 When No Cache

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md does not exist
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response status is 404

#### Scenario: Extraction Tool Returns Structured Decisions Array

    Given a commit range that modifies features/login.impl.md containing an [INFEASIBLE] entry
    And a commit range that modifies features/auth.impl.md containing a [DEVIATION] entry
    When the extraction tool runs with the branch name
    Then the output JSON contains a decisions array
    And each decision entry has category, feature, summary, and role fields
    And the [INFEASIBLE] entry has role "architect"
    And the [DEVIATION] entry has role "architect"

#### Scenario: Extraction Tool Routes BUG Entries to Builder by Default

    Given a commit range that modifies features/login.discoveries.md containing a [BUG] entry
    And the entry does not contain "Action Required: Architect"
    When the extraction tool runs with the branch name
    Then the decisions array contains the [BUG] entry with role "builder"

#### Scenario: Extraction Tool Routes INFEASIBLE Entries to Architect

    Given a commit range that modifies features/login.impl.md containing an [INFEASIBLE] entry
    When the extraction tool runs with the branch name
    Then the decisions array contains the [INFEASIBLE] entry with role "architect"

#### Scenario: Standard Digest Generation Deletes Stale Deep Analysis

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And features/digests/whats-different-analysis.md does not exist on disk

#### Scenario: Impact Summary Content Appears Above File-Level Digest in HTML

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    And features/digests/whats-different.md exists on disk
    When a GET request is sent to /whats-different/read
    Then the response contains the digest content
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response contains the analysis content
    And the modal renders the impact summary section above the file-level digest

#### Scenario: Auto-Generation After pl-remote-pull Merge

    Given the agent is on the collaboration branch
    And an active branch exists in BEHIND state
    When the agent runs /pl-remote-pull and the merge succeeds
    Then the generation script is executed as Step 7
    And features/digests/whats-different.md is written to disk
    And the digest content is displayed inline after the merge summary

#### Scenario: Stale Impact Summary Absent After Digest Regeneration

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And features/digests/whats-different-analysis.md does not exist on disk
    And subsequent GET /whats-different/deep-analysis/read returns 404

#### Scenario: Button Opens Cached Content Without Regeneration

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different.md exists on disk
    When a GET request is sent to /whats-different/read
    Then the response status is 200
    And the response contains the cached digest content
    And no POST request is sent to /whats-different/generate

#### Scenario: DIVERGED Generation Returns Both Directions via Endpoint

    Given an active branch "v0.5-sprint" is set
    And the branch is in DIVERGED state
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response digest contains both "Your Local Changes" and "Collab Changes" sections
    And the response contains a tags object with change counts

#### Scenario: Regenerate Triggers Fresh Generation via Endpoint

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different.md exists on disk
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response contains freshly generated digest content
    And features/digests/whats-different.md is overwritten with new content

#### Scenario: Deep Analysis Generation Returns Analysis via Endpoint

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When a POST request is sent to /whats-different/deep-analysis/generate
    Then the response status is 200
    And the response contains an analysis field with generated content
    And features/digests/whats-different-analysis.md exists on disk

#### Scenario: Modal Close Button Present in HTML

    Given an active branch "v0.5-sprint" is set
    When the dashboard HTML is generated
    Then the What's Different modal template contains an X close button element
    And the modal container has the standard CDD modal overlay pattern

#### Scenario: What's Different Modal Width (auto-web)
    Given an active branch is set with sync state not SAME
    And a cached digest exists
    When the User clicks the "What's Different?" button
    Then the modal width is 70% of the viewport width

#### Scenario: What's Different Modal Font Slider (auto-web)
    Given the What's Different modal is open
    When the User adjusts the font size slider
    Then all digest text (headings, paragraphs, code, tags, impact summary) scales together
    And text wraps correctly without horizontal overflow

#### Scenario: What's Different Modal Font Persists (auto-web)
    Given the User has adjusted the font size slider in the What's Different modal
    When the User closes the modal
    And the User reopens the What's Different modal
    Then the font size slider position is retained at the previously set value

### QA Scenarios
None

---

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: CDD Dashboard -- What's Different? Button

- **Reference:** N/A
- **Processed:** N/A
- **Description:** The "What's Different?" button is rendered within the active branch panel of the REMOTE COLLABORATION section, below the sync state row. The button uses standard dashboard button styling with `var(--font-body)` Inter 500 14px text. When a cached digest exists, a "Last generated: `<timestamp>`" line appears below the button in `var(--purlin-muted)` Inter 400 12px. The button is hidden when sync state is SAME or when no active branch exists.
- [ ] Button visible in active branch panel when sync state is AHEAD, BEHIND, or DIVERGED
- [ ] Button hidden when sync state is SAME
- [ ] Button absent when no active branch
- [ ] "Last generated" timestamp shown below button when cached digest exists, in `var(--purlin-muted)` 12px
- [ ] Button styling consistent with other dashboard action buttons

### Screen: CDD Dashboard -- What's Different? Modal

- **Reference:** N/A
- **Processed:** N/A
- **Description:** The modal follows the existing CDD modal pattern (Feature Detail Modal, Kill modal, Delete Confirmation Modal). Max-width 700px, max-height 80vh, scrollable body. The modal header contains the title "What's Different?" and the generation date in `var(--purlin-muted)`. Below the title and date, a change tags bar displays pill-shaped tag badges in a flex-wrap row. Each tag uses `var(--purlin-tag-fill)` background and `var(--purlin-tag-outline)` border with domain-specific text colors. The modal body renders the markdown digest with `.modal-body` CSS. Section headers for Spec Changes, Code Changes, and Purlin Changes use domain-specific colors.
- [ ] Modal width 70vw (inherited from cdd_modal_base.md), max-height 80vh, scrollable body
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
- [ ] "Summarize Impact" button visible inside modal above digest content when no cached analysis exists
- [ ] "Summarize Impact" button text changes to animated "Summarizing." / "Summarizing.." / "Summarizing..." during generation
- [ ] After generation completes, impact summary section replaces the "Summarize Impact" button
- [ ] Change tags bar: flex-wrap row of pill badges below title and date
- [ ] Tags use `var(--purlin-tag-fill)` background and `var(--purlin-tag-outline)` border
- [ ] `[N Specs]` tag text color: `var(--purlin-accent)` (Spec Changes)
- [ ] `[N Anchor]` tag text color: `var(--purlin-accent)` (Spec Changes)
- [ ] `[N Visual]` tag text color: `var(--purlin-accent)` (Spec Changes)
- [ ] `[N Code]` tag text color: `var(--purlin-status-good)` (Code Changes)
- [ ] `[N Tests]` tag text color: `var(--purlin-status-good)` (Code Changes)
- [ ] `[N Purlin]` tag text color: `var(--purlin-status-todo)` (Purlin Changes)
- [ ] `[N Discovery]` tag text color: `var(--purlin-accent)` (Spec Changes)
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
- [ ] Modal typography: 70vw width (inherited from cdd_modal_base.md), 80vh max-height, scrollable body, generation date prominently at top
- [ ] "Generating" animated ellipsis (`.` / `..` / `...` cycling at ~500ms) in `var(--purlin-muted)` during generation
- [ ] "Summarizing" animated ellipsis (same pattern) during deep analysis generation
- [ ] Regenerate click triggers animated "Generating" ellipsis state, then displays fresh content
- [ ] Timestamp: "Generated:" label bold (font-weight 700), local timezone AM/PM format (e.g., "Feb 26, 2026 3:45 PM EST")
- [ ] Change tags bar: `[N Specs]` in `var(--purlin-accent)`, `[N Code]` in `var(--purlin-status-good)`, `[N Discovery]` in `var(--purlin-accent)`, all on `var(--purlin-tag-fill)` background with `var(--purlin-tag-outline)` border
- [ ] Section header colors: "Spec Changes" in `var(--purlin-accent)`, "Code Changes" in `var(--purlin-status-good)`, "Purlin Changes" in `var(--purlin-status-todo)`
- [ ] "What's Different?" button visible in active branch panel when sync state is not SAME; "Last generated: `<timestamp>`" shown below when cached
- [ ] "Summarize Impact" button visible inside modal above digest content when no cached analysis exists; uses `btn-critic` styling
- [ ] Deep Analysis: "Architect Actions" header in `var(--purlin-status-warning)`, `[INFEASIBLE]` in `var(--purlin-status-error)`, `[INTENT_DRIFT]` in `var(--purlin-status-warning)`
- [ ] Deep Analysis: "Builder Actions" header in `var(--purlin-status-good)`, `[BUG]` in `var(--purlin-status-error)`
- [ ] Modal close via Escape key and clicking outside modal (JS behavior)
- [ ] Font size control (minus, slider, plus) visible in modal header (inherited from cdd_modal_base.md)
- [ ] Font size slider scales all digest text together (headings, paragraphs, code, tags, impact summary)
- [ ] Font size persists when closing and reopening the What's Different modal

## Regression Guidance
- Direction-dependent content: AHEAD shows only local changes, BEHIND shows only collab changes, DIVERGED shows both
- Digest file overwrites on each generation (no stale content accumulation)
- Dashboard button hidden when sync state is SAME
- Post-merge auto-generation triggers after successful /pl-remote-pull
