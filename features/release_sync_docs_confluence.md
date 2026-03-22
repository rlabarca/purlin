# Feature: Sync Docs to Confluence

> Label: "Release Step: Sync Docs to Confluence"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md
> Prerequisite: features/release_refresh_docs.md

## 1. Overview

This feature defines the `sync_docs_to_confluence` local release step: a hybrid sync that publishes project documentation from `docs/` to Confluence as child pages under a designated parent page. Text and page operations use the Atlassian MCP server (which accepts markdown natively). Image uploads use a lightweight Python script (`dev/confluence_upload_images.py`) calling the Confluence REST API v1, since the MCP server has no attachment upload capability. The step includes first-time setup assistance for both the MCP server and API token credentials. Doc freshness is handled by the upstream `refresh_docs` step.

---

## 2. Requirements

### 2.1 Documentation Directory Convention

The `docs/` directory uses subdirectories that map to Confluence page groups:

```
docs/
├── guides/
│   ├── testing-workflow-guide.md
│   └── images/
│       └── (optional per-section images)
└── reference/
    ├── parallel-execution-guide.md
    └── images/
        └── (optional per-section images)
```

Subdirectory-to-Confluence mapping:

| Subdirectory | Confluence Section Title | Purpose |
|---|---|---|
| `guides/` | Guides | End-to-end process docs spanning multiple agents ("how to do X") |
| `reference/` | Technical Reference | Component/agent deep dives ("how X works") |

Each subdirectory becomes a section page (child of the parent page). Each markdown file becomes a child page under its section page.

### 2.2 Confluence Page Hierarchy

All pages are organized under a single parent page (ID: `4011458562`, space: `PRODENG`, site: `trustengine.atlassian.net`):

```
Purlin Documentation (parent page 4011458562)
├── Guides                             (section page, from subdirectory)
│   └── Testing Workflow Guide         (child page, from markdown file)
├── Technical Reference                (section page, from subdirectory)
│   └── Parallel Execution Guide       (child page, from markdown file)
└── [manually-managed content untouched]
```

Page titles are derived from filenames: hyphens to spaces, title-case. The step MUST NOT delete Confluence pages that have no local counterpart -- manually-managed content is preserved.

### 2.3 Image Upload Script

A Python script at `dev/confluence_upload_images.py` handles image attachment uploads via the Confluence REST API v1. This script lives in `dev/` (not `tools/`) because it is specific to the Purlin repository's release process and is not needed by consumer projects.

**Interface:**

```
python3 dev/confluence_upload_images.py --page-id <id> --files image1.png image2.png ...
```

**Behavior:**

1. Reads credentials from `.purlin/runtime/confluence/credentials.json`.
2. Scans each file argument and uploads to the target page via:
   ```
   POST /wiki/rest/api/content/{pageId}/child/attachment
   Headers: X-Atlassian-Token: no-check, Authorization: Basic base64(email:token)
   Body: multipart/form-data with file
   ```
3. Skips upload if an attachment with the same filename and file size already exists on the page.
4. Re-uploads if the file size differs (content changed).
5. Outputs a JSON mapping to stdout: `{ "local/path.png": "https://trustengine.atlassian.net/wiki/download/attachments/{pageId}/filename.png" }`.

**Dependencies:** `requests` library (with `urllib.request` as stdlib fallback if `requests` is unavailable).

### 2.4 Credential Storage Convention

API token credentials for image uploads are stored at `.purlin/runtime/confluence/credentials.json`:

```json
{
  "email": "user@example.com",
  "token": "<api-token>",
  "base_url": "https://trustengine.atlassian.net"
}
```

This path is gitignored via the existing `.purlin/runtime/` pattern. The step MUST NOT commit or log credential values.

### 2.5 First-Time Setup Flow

On first execution, the step detects missing prerequisites and guides the user through setup:

1. **Confluence MCP check:** Attempt to list Confluence spaces. If the MCP server is unavailable:
   - Check if `.mcp.json` in the project root already contains an `atlassian` entry.
   - If not configured, run `claude mcp add atlassian --transport http --scope project https://mcp.atlassian.com/v1/mcp` to configure it automatically (per `policy_release.md` Invariant 2.7).
   - Whether newly configured or already present in `.mcp.json`, the MCP is not loaded in the current session. Ask the user to type `/mcp` in Claude Code, select the `atlassian` MCP server from the list, and authenticate when prompted (OAuth 2.1 -- a browser window opens for authorization). HALT and wait for the user to confirm authentication is complete. No API token or credentials file is needed for MCP operations.
2. **API token check (image uploads only):** The image upload script (`dev/confluence_upload_images.py`) requires REST API credentials stored at `.purlin/runtime/confluence/credentials.json`. This check is deferred to Phase 1 and only applies when images are found. If the credentials file is missing when needed, create the directory (`mkdir -p .purlin/runtime/confluence/`), ask the user for their Atlassian email and API token (direct them to `https://id.atlassian.com/manage-profile/security/api-tokens` to create one with label "purlin-docs-sync"), write the credentials file automatically, and verify with a test API call. Halt until working.

### 2.6 Image Upload Flow

1. Scan all markdown files for `![alt](path)` image references.
2. Resolve paths relative to the markdown file's directory.
3. Determine the target Confluence page ID for each image (the child page it belongs to).
4. Run: `python3 dev/confluence_upload_images.py --page-id <id> --files <paths>`.
5. Collect the URL mapping from script output.
6. Replace local image paths in markdown content with Confluence attachment URLs before syncing via MCP.

If no images are found, skip directly to page sync.

### 2.7 Confluence Page Sync

1. Search for existing child pages under parent page `4011458562`.
2. For each subdirectory in `docs/`: find or create a section page as a child of the parent page (directory name to title-case, with `reference` mapping to "Technical Reference").
3. For each `*.md` file: derive page title from filename, read content, apply image URL replacements if any, and create or update the child page under its section page via MCP.
4. NEVER delete pages that have no local counterpart.

### 2.8 Scope Constraint

This step syncs whatever docs exist in `docs/` at execution time. It NEVER creates new documentation files. It MAY recommend new docs the user should consider writing, presented in the completion report's Recommendations section.

### 2.9 Completion Report

After sync, print a change-focused summary:

```
-- Confluence Docs Sync ------------------------------------

Images:
  UPLOADED  guides/images/agent-sequence.png (12 KB)
  SKIPPED   reference/images/merge-protocol.png (unchanged)

Confluence sync:
  UPDATED  Guides / Testing Workflow Guide
  CREATED  Technical Reference / Parallel Execution Guide

2 pages synced -> trustengine.atlassian.net/wiki/spaces/PRODENG/pages/4011458562
-----------------------------------------------------------
```

Status tags: `UPLOADED`/`SKIPPED` for image attachments, `CREATED`/`UPDATED` for Confluence pages.

### 2.10 Step Metadata

| Field | Value |
|-------|-------|
| ID | `sync_docs_to_confluence` |
| Friendly Name | `Sync Docs to Confluence` |
| Code | `null` (interactive step requiring MCP and user interaction) |
| Agent Instructions | See Section 2.11 |

### 2.11 Agent Instructions (Release Step Content)

**Phase 0: Prerequisites and First-Time Setup**

1. Check Confluence MCP availability: search for Atlassian MCP tools in the current session.
   - If available: proceed to step 2.
   - If unavailable: check `.mcp.json` for existing `atlassian` entry. If not configured, run `claude mcp add atlassian --transport http --scope project https://mcp.atlassian.com/v1/mcp` automatically. Whether newly configured or already present, ask the user to type `/mcp` in Claude Code, select the `atlassian` MCP server, and authenticate (OAuth 2.1). HALT until the user confirms authentication is complete.
2. Verify Confluence access: use the Atlassian MCP to list accessible Atlassian resources and confirm the `PRODENG` space is reachable. No API token or credentials file is needed for MCP operations. Halt if not accessible.
3. If all prerequisites pass: proceed.

**Phase 1: Image Upload**

1. Scan all markdown files for `![alt](path)` image references.
2. If images found:
   a. Check credentials for the REST API image uploader: read `.purlin/runtime/confluence/credentials.json`.
      - If present with 'email', 'token', and 'base_url' keys: proceed.
      - If missing: run `mkdir -p .purlin/runtime/confluence/`, then ask the user for their Atlassian email and API token (direct to `https://id.atlassian.com/manage-profile/security/api-tokens`, label: "purlin-docs-sync"). Write the credentials file with keys `email`, `token`, and `base_url` (e.g., `https://trustengine.atlassian.net`). Verify with a test API call. Halt until working.
   b. Determine target page ID for each image (the child page it belongs to), run `python3 dev/confluence_upload_images.py --page-id <id> --files <paths>`, collect URL mapping.
3. If no images: skip to Phase 2.

**Phase 2: Confluence Page Sync**

1. Search for existing child pages under parent page `4011458562`.
2. For each subdirectory in `docs/`: derive section page title (directory name to title-case; `reference` maps to "Technical Reference"), find or create section page as child of parent.
3. For each `*.md` file: derive page title from filename (hyphens to spaces, title-case), read markdown content, replace local image paths with Confluence URLs if applicable, create or update child page under section page via MCP.
4. NEVER delete pages without a local counterpart.

**Phase 2.5: Parent Page from Index**

After all child pages are synced, update the parent page (ID: 4011458562, "Purlin Agentic Development") using the content from `docs/index.md` (generated by the upstream `refresh_docs` step). Convert the relative markdown links in `index.md` to absolute Confluence page URLs based on the child page IDs resolved during Phase 2. Use markdown content format when updating the parent page via MCP.

**Phase 3: Completion Report**

Print the change-focused summary per Section 2.9.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Subdirectory maps to Confluence section page

    Given the docs/ directory contains a subdirectory "guides" with one markdown file
    When the step processes the directory structure
    Then it derives the section page title "Guides" from the subdirectory name
    And it creates or finds a section page titled "Guides" as a child of the parent page

#### Scenario: Reference subdirectory maps to "Technical Reference"

    Given the docs/ directory contains a subdirectory "reference"
    When the step processes the directory structure
    Then it derives the section page title "Technical Reference" (not "Reference")

#### Scenario: Filename derives correct page title

    Given a markdown file named "testing-workflow-guide.md" in docs/guides/
    When the step derives the page title
    Then the title is "Testing Workflow Guide"

#### Scenario: Image upload produces URL mapping

    Given a markdown file contains "![diagram](images/flow.png)"
    And images/flow.png exists relative to the markdown file
    When the image upload script runs with --page-id and --files arguments
    Then the script outputs a JSON mapping from the local path to a Confluence attachment URL
    And the local image reference in markdown is replaced with the Confluence URL before sync

#### Scenario: Image upload skips unchanged attachment

    Given images/flow.png was previously uploaded to the target Confluence page
    And the local file size matches the existing attachment size
    When the image upload script runs
    Then the script skips the upload for that file
    And the output mapping still contains the existing Confluence URL

#### Scenario: Missing MCP server auto-configured

    Given the Atlassian MCP server is not configured in Claude Code
    When the step executes Phase 0
    Then the step runs "claude mcp add atlassian --transport http --scope project https://mcp.atlassian.com/v1/mcp" automatically
    And asks the user to type /mcp in Claude Code, select the atlassian MCP server, and authenticate
    And the step halts until the user confirms authentication is complete

#### Scenario: MCP configured but not loaded triggers authentication prompt

    Given the Atlassian MCP server is configured in .mcp.json
    But the MCP tools are not available in the current session
    When the step executes Phase 0
    Then the step asks the user to type /mcp in Claude Code, select the atlassian MCP server, and authenticate
    And the step halts until the user confirms authentication is complete

#### Scenario: Missing credentials file triggers token setup during image upload

    Given .purlin/runtime/confluence/credentials.json does not exist
    And markdown files contain image references
    When the step executes Phase 1 image upload
    Then the step guides the user to create an API token
    And collects the user's email and token
    And writes the credentials file to .purlin/runtime/confluence/credentials.json
    And verifies the credentials with a test API call

#### Scenario: Step never deletes Confluence pages

    Given the parent page has a manually-created child page "Release Notes" with no local counterpart
    When the step syncs docs/ to Confluence
    Then the "Release Notes" page is not deleted or modified

#### Scenario: Credentials are never committed or logged

    Given .purlin/runtime/confluence/credentials.json contains valid credentials
    When the step executes any phase
    Then the credentials file path is covered by .gitignore via .purlin/runtime/
    And no credential values appear in commit messages or step output

### QA Scenarios

#### @manual Scenario: End-to-end sync creates correct Confluence hierarchy

    Given the MCP server and API token are configured
    And docs/ contains guides/testing-workflow-guide.md and reference/parallel-execution-guide.md
    When the full release step executes
    Then Confluence parent page 4011458562 has child section pages "Guides" and "Technical Reference"
    And "Guides" has child page "Testing Workflow Guide" with content matching the markdown
    And "Technical Reference" has child page "Parallel Execution Guide" with content matching the markdown

#### @manual Scenario: Image renders correctly in Confluence

    Given a markdown file references a local image that was uploaded as an attachment
    When the page is viewed in Confluence
    Then the image renders inline at the expected location
