#!/usr/bin/env bash
# dev/setup_plugin_test_fixture.sh
#
# Creates a comprehensive test consumer project for plugin testing.
# The fixture covers all artifact types the scan engine parses:
#   - Feature specs (TODO, TESTING, COMPLETE) with prerequisites
#   - Companion files (acknowledged and unacknowledged deviations)
#   - Discovery sidecars (OPEN/RESOLVED bugs and discoveries)
#   - Invariant nodes (global and scoped)
#   - Anchor nodes (arch, design, policy)
#   - Delivery plan with multiple phases
#   - Test results and regression JSON
#   - Tombstoned features
#   - Config files (config.json, config.local.json)
#
# Usage:
#   ./dev/setup_plugin_test_fixture.sh [OUTPUT_DIR]
#
# Default output: /tmp/purlin-plugin-fixture
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
    cat <<'HELP'
Usage: setup_plugin_test_fixture.sh [OUTPUT_DIR]

Creates a comprehensive consumer project fixture for plugin testing.
The fixture includes all artifact types parsed by the scan engine.

Arguments:
  OUTPUT_DIR    Where to create the fixture (default: /tmp/purlin-plugin-fixture)

The fixture is a standalone git repo with 5 committed states, ready
for use in scan engine and plugin integration tests.
HELP
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${1:-/tmp/purlin-plugin-fixture}"

echo "=== Purlin Plugin Test Fixture Setup ==="
echo "Source: $PROJECT_ROOT"
echo "Output: $OUTPUT_DIR"
echo ""

# Clean previous
if [[ -d "$OUTPUT_DIR" ]]; then
    echo "Removing existing fixture..."
    rm -rf "$OUTPUT_DIR"
fi

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# =====================================================================
# Step 1: Initialize consumer project repo
# =====================================================================
echo "[1/5] Initializing consumer project repo and base structure..."

git init >/dev/null 2>&1
git config user.email "fixture@purlin.dev"
git config user.name "Purlin Fixture Engineer"

# Create directory structure
mkdir -p .purlin/runtime .purlin/cache
mkdir -p features/_tombstones features/_invariants
mkdir -p features/core features/ui features/foundation features/analytics
mkdir -p features/architecture features/design features/policy
mkdir -p tests/api_endpoints tests/search tests/data_model tests/billing tests/reporting
mkdir -p src/utils

# --- .purlin/config.json ---
cat > .purlin/config.json <<'CONFIG'
{
  "agents": {
    "purlin": {
      "model": "claude-sonnet-4-6",
      "effort": "high",
      "bypass_permissions": true,
      "find_work": false,
      "auto_start": false,
      "default_mode": null
    }
  },
  "acknowledged_warnings": []
}
CONFIG

# --- .purlin/config.local.json ---
cat > .purlin/config.local.json <<'CONFIG_LOCAL'
{
  "agents": {
    "purlin": {
      "model": "claude-opus-4-6[1m]",
      "effort": "high",
      "bypass_permissions": true,
      "find_work": false,
      "auto_start": false,
      "default_mode": null
    }
  },
  "acknowledged_warnings": ["claude-opus-4-6[1m]"]
}
CONFIG_LOCAL

# --- .purlin/delivery_plan.md ---
cat > .purlin/delivery_plan.md <<'PLAN'
# Delivery Plan: Consumer App

## Phase 1 — Foundation (COMPLETE)

- `features/foundation/data_model.md`

## Phase 2 — Core Features (IN_PROGRESS)

- `features/core/user_auth.md`
- `features/core/api_endpoints.md`
- `features/core/billing.md`

## Phase 3 — UI Layer (PENDING)

- `features/ui/dashboard.md`
- `features/core/search.md`
- `features/analytics/reporting.md`
- `features/core/notifications.md`
PLAN

# --- .purlin/PURLIN_OVERRIDES.md ---
cat > .purlin/PURLIN_OVERRIDES.md <<'OVERRIDES'
# Project Overrides

## General (all modes)

This is a consumer project using Purlin for spec-driven development.

## Engineer Mode

### Test Framework
Use pytest for unit tests.

## PM Mode

### Design System
Use Material Design components.

## QA Mode

No project-specific QA overrides.
OVERRIDES

# --- CLAUDE.md ---
cat > CLAUDE.md <<'CLAUDEMD'
# Consumer App

This project uses the Purlin plugin for spec-driven development.

## Purlin Agent (Unified)

- **Engineer mode**: Code, tests, scripts, arch anchors, companions.
- **PM mode**: Feature specs, design/policy anchors.
- **QA mode**: Discovery sidecars, QA tags, regression JSON.

## Context Recovery

If context is cleared, run `purlin:resume` to restore session context.

## Project Overrides

See `.purlin/PURLIN_OVERRIDES.md` for project-specific rules.

## Commands

Run `purlin:help` for the full command reference.
CLAUDEMD

# --- .gitignore ---
cat > .gitignore <<'GITIGNORE'
.purlin/cache/
.purlin/runtime/
.purlin_session.lock
node_modules/
.DS_Store
GITIGNORE

# --- README.md ---
cat > README.md <<'README'
# Consumer App

A sample consumer application for testing the Purlin plugin.

## Getting Started

```bash
python3 src/app.py
```

## Structure

- `src/` — Application source code
- `features/` — Feature specifications
- `tests/` — Test results
README

# --- src/app.py ---
cat > src/app.py <<'APP'
"""Consumer App — main entry point."""

from utils.helpers import format_response, validate_input


def main():
    """Run the consumer application."""
    data = validate_input({"user": "test", "action": "login"})
    response = format_response(data)
    print(response)


if __name__ == "__main__":
    main()
APP

# --- src/utils/helpers.py ---
cat > src/utils/helpers.py <<'HELPERS'
"""Utility helpers for the consumer app."""


def format_response(data):
    """Format a response dict as a string."""
    return f"OK: {data}"


def validate_input(data):
    """Validate input data. Returns sanitized copy."""
    if not isinstance(data, dict):
        raise ValueError("Input must be a dict")
    return {k: str(v) for k, v in data.items()}
HELPERS

# Keep .purlin/runtime and .purlin/cache as empty dirs via .gitkeep
touch .purlin/runtime/.gitkeep
touch .purlin/cache/.gitkeep

# Commit 1: Initial project structure
git add -A >/dev/null 2>&1
git commit -m "feat: initial project structure" >/dev/null 2>&1

# =====================================================================
# Step 2: Add feature specifications
# =====================================================================
echo "[2/5] Creating feature specifications..."

# --- features/user_auth.md --- [TODO]
cat > features/core/user_auth.md <<'SPEC'
# Feature: User Authentication

> Label: "User Authentication"
> Category: "Core"

## Status

[TODO]

## 1. Overview

Handles user login, logout, and session management.

## 2. Requirements

### 2.1 Login

- Users can log in with email and password.
- Failed login attempts are rate-limited after 5 attempts.

### 2.2 Session Management

- Sessions expire after 24 hours of inactivity.
- Refresh tokens rotate on each use.

### 2.3 Logout

- Invalidates the current session token.
- Clears any stored refresh tokens.

## 3. Scenarios

### Unit Tests

#### Test: Login with valid credentials

    Given a registered user with email "test@example.com"
    When they submit valid credentials
    Then a session token is returned

#### Test: Login with invalid credentials

    Given an unregistered email "unknown@example.com"
    When they submit credentials
    Then a 401 error is returned

### QA Scenarios

#### Scenario: Rate limiting

    Given a user has failed login 5 times
    When they attempt login again within 15 minutes
    Then the attempt is blocked with a rate limit message
SPEC

# --- features/dashboard.md --- [TODO], Prereq: features/user_auth.md
cat > features/ui/dashboard.md <<'SPEC'
# Feature: Dashboard

> Label: "Dashboard"
> Category: "UI"
> Prerequisite: user_auth.md

## Status

[TODO]

## 1. Overview

Main dashboard view showing user metrics and recent activity.

## 2. Requirements

### 2.1 Layout

- Top navigation bar with user avatar and logout button.
- Left sidebar with navigation links.
- Main content area with metric cards.

### 2.2 Data Display

- Metric cards refresh every 30 seconds.
- Charts use the last 30 days of data by default.

## 3. Scenarios

### Unit Tests

#### Test: Dashboard loads metrics

    Given an authenticated user
    When they navigate to /dashboard
    Then metric cards display current data

### QA Scenarios

#### Scenario: Responsive layout

    Given a browser window at 768px width
    When the dashboard loads
    Then the sidebar collapses to a hamburger menu
SPEC

# --- features/notifications.md --- [TODO]
cat > features/core/notifications.md <<'SPEC'
# Feature: Notifications

> Label: "Notifications"
> Category: "Core"

## Status

[TODO]

## 1. Overview

Real-time notification system for user events.

## 2. Requirements

### 2.1 Delivery Channels

- In-app notification bell with unread count.
- Email notifications for critical events.
- Push notifications for mobile (optional).

### 2.2 Preferences

- Users can mute specific notification categories.
- Digest mode batches notifications hourly.

## 3. Scenarios

### Unit Tests

#### Test: Notification creation

    Given a triggering event occurs
    When the notification service processes the event
    Then a notification record is created with correct type

### QA Scenarios

#### Scenario: Unread count badge

    Given the user has 3 unread notifications
    When they view the notification bell
    Then the badge shows "3"
SPEC

# --- features/api_endpoints.md --- [TESTING]
cat > features/core/api_endpoints.md <<'SPEC'
# Feature: API Endpoints

> Label: "REST API"
> Category: "Core"

## Status

[TESTING]

## 1. Overview

RESTful API for CRUD operations on user data and resources.

## 2. Requirements

### 2.1 Endpoints

- GET /api/users — list users with pagination
- POST /api/users — create a new user
- GET /api/users/:id — get user by ID
- PUT /api/users/:id — update user
- DELETE /api/users/:id — soft-delete user

### 2.2 Validation

- All request bodies validated with JSON Schema.
- Invalid requests return 422 with error details.

### 2.3 Authentication

- All endpoints require Bearer token authentication.
- Rate limiting: 100 requests per minute per user.

## 3. Scenarios

### Unit Tests

#### Test: List users returns paginated results

    Given 50 users exist in the database
    When GET /api/users?page=1&limit=10 is called
    Then 10 users are returned with pagination metadata

#### Test: Create user with valid data

    Given valid user data in the request body
    When POST /api/users is called
    Then a 201 response is returned with the new user

### QA Scenarios

#### Scenario: Rate limiting enforcement

    Given a user has made 100 requests in the last minute
    When they make another request
    Then a 429 Too Many Requests response is returned
SPEC

# --- features/search.md --- [TESTING]
cat > features/core/search.md <<'SPEC'
# Feature: Search

> Label: "Search"
> Category: "Core"

## Status

[TESTING]

## 1. Overview

Full-text search across application entities.

## 2. Requirements

### 2.1 Search Index

- Index updates within 5 seconds of data changes.
- Supports fuzzy matching with configurable threshold.

### 2.2 Query API

- GET /api/search?q=term&type=users
- Supports filtering by entity type.
- Results ranked by relevance score.

### 2.3 Performance

- Search queries complete in under 200ms for datasets up to 1M records.

## 3. Scenarios

### Unit Tests

#### Test: Basic search returns results

    Given indexed data with 100 user records
    When GET /api/search?q=john is called
    Then matching users are returned sorted by relevance

### QA Scenarios

#### Scenario: Fuzzy matching

    Given a user named "Jonathan"
    When searching for "Jonathn" (typo)
    Then "Jonathan" appears in results with fuzzy match indicator
SPEC

# --- features/data_model.md --- [COMPLETE]
cat > features/foundation/data_model.md <<'SPEC'
# Feature: Data Model

> Label: "Data Model"
> Category: "Foundation"

## Status

[COMPLETE]

## 1. Overview

Core database schema and data access layer.

## 2. Requirements

### 2.1 Schema

- Users table with id, email, name, created_at, updated_at.
- Sessions table with id, user_id, token, expires_at.
- Audit log table with id, user_id, action, timestamp.

### 2.2 Migrations

- All schema changes managed through versioned migrations.
- Rollback support for all migrations.

### 2.3 Access Layer

- Repository pattern for data access.
- Connection pooling with configurable pool size.

## 3. Scenarios

### Unit Tests

#### Test: User creation persists correctly

    Given valid user data
    When the user repository creates a new record
    Then the record is retrievable by ID with all fields intact

### QA Scenarios

#### Scenario: Migration rollback

    Given a migration has been applied
    When a rollback is executed
    Then the schema returns to the previous state
SPEC

# --- features/billing.md --- [COMPLETE], Prereq: features/data_model.md
cat > features/core/billing.md <<'SPEC'
# Feature: Billing

> Label: "Billing"
> Category: "Core"
> Prerequisite: data_model.md

## Status

[COMPLETE]

## 1. Overview

Subscription billing and payment processing.

## 2. Requirements

### 2.1 Plans

- Free tier with limited API calls (1000/month).
- Pro tier with unlimited API calls.
- Enterprise tier with SLA and priority support.

### 2.2 Payment Processing

- Stripe integration for credit card payments.
- Invoice generation for enterprise customers.

### 2.3 Usage Tracking

- Track API calls per user per billing period.
- Overage notifications at 80% and 100% of limits.

## 3. Scenarios

### Unit Tests

#### Test: Usage counter increments

    Given a user on the free tier
    When they make an API call
    Then their usage counter increments by one

### QA Scenarios

#### Scenario: Plan upgrade

    Given a user on the free tier
    When they upgrade to Pro
    Then their usage limits update immediately
SPEC

# --- features/reporting.md --- [COMPLETE], Prereq: features/billing.md
cat > features/analytics/reporting.md <<'SPEC'
# Feature: Reporting

> Label: "Reporting"
> Category: "Analytics"
> Prerequisite: billing.md

## Status

[COMPLETE]

## 1. Overview

Analytics and reporting dashboard for usage and billing data.

## 2. Requirements

### 2.1 Reports

- Daily usage summary with charts.
- Monthly billing report with line items.
- Export to CSV and PDF.

### 2.2 Scheduling

- Automated weekly email reports.
- Custom report scheduling by admin users.

## 3. Scenarios

### Unit Tests

#### Test: Daily summary generation

    Given usage data for the current day
    When the daily summary job runs
    Then a summary record is created with correct totals

### QA Scenarios

#### Scenario: CSV export

    Given a monthly billing report
    When the user clicks export CSV
    Then a valid CSV file downloads with correct data
SPEC

# Commit 2: Add feature specifications
git add -A >/dev/null 2>&1
git commit -m "feat: add feature specifications" >/dev/null 2>&1

# =====================================================================
# Step 3: Add companion files and discoveries
# =====================================================================
echo "[3/5] Creating companion files and discovery sidecars..."

# --- features/api_endpoints.impl.md --- (unacknowledged deviation)
cat > features/core/api_endpoints.impl.md <<'IMPL'
# Companion: API Endpoints

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| Offset-based pagination | Cursor-based pagination | DEVIATION | PM status: PENDING |

## Implementation Log

- [IMPL] Created Express router with all 5 CRUD endpoints.
- [IMPL] Added JSON Schema validation for request bodies.
- [IMPL] Integrated Bearer token authentication middleware.
- [DEVIATION] Used cursor-based pagination instead of offset-based. Reason: better performance with large datasets.
- [IMPL] Added rate limiting middleware at 100 req/min.
IMPL

# --- features/search.impl.md --- (acknowledged deviation)
cat > features/core/search.impl.md <<'IMPL'
# Companion: Search

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| PostgreSQL FTS | Elasticsearch | DEVIATION | PM status: ACCEPTED |

## Implementation Log

- [IMPL] Set up Elasticsearch index with custom analyzers.
- [DEVIATION] Used Elasticsearch instead of PostgreSQL full-text search. Reason: better fuzzy matching and relevance scoring. ACKNOWLEDGED
- [IMPL] Added search query API endpoint with type filtering.
- [IMPL] Implemented index update hooks with 5-second propagation.
IMPL

# --- features/api_endpoints.discoveries.md --- (OPEN BUG + OPEN DISCOVERY)
cat > features/core/api_endpoints.discoveries.md <<'DISC'
# Discoveries: API Endpoints

### [BUG] Pagination cursor breaks on special characters

- **Status:** OPEN
- **Action Required:** Engineer
- **Description:** When user names contain unicode characters, the cursor encoding fails silently and returns duplicate results on the next page.
- **Severity:** High
- **Found by:** QA automated test suite

### [DISCOVERY] Rate limiter does not reset on plan upgrade

- **Status:** OPEN
- **Action Required:** Engineer
- **Description:** When a user upgrades from free to pro tier, their rate limit counter does not reset. They remain throttled until the next billing period window.
DISC

# --- features/data_model.discoveries.md --- (RESOLVED BUG)
cat > features/foundation/data_model.discoveries.md <<'DISC'
# Discoveries: Data Model

### [BUG] Migration rollback fails on foreign key constraints

- **Status:** RESOLVED
- **Action Required:** None
- **Description:** Rolling back the sessions table migration failed because the foreign key to users was not dropped first. Fixed by adding CASCADE to the rollback.
- **Resolution:** Added explicit foreign key drop in rollback step. Verified in migration test suite.
DISC

# Commit 3: Add companion files and discoveries
git add -A >/dev/null 2>&1
git commit -m "feat: add companion files and discoveries" >/dev/null 2>&1

# =====================================================================
# Step 4: Add test results
# =====================================================================
echo "[4/5] Creating test results..."

# --- tests/api_endpoints/tests.json --- PASS 8/8
cat > tests/api_endpoints/tests.json <<'JSON'
{
  "feature": "api_endpoints",
  "status": "PASS",
  "passed": 8,
  "failed": 0,
  "total": 8,
  "timestamp": "2026-03-25T10:00:00Z",
  "results": [
    {"name": "List users returns paginated results", "status": "PASS"},
    {"name": "Create user with valid data", "status": "PASS"},
    {"name": "Get user by ID", "status": "PASS"},
    {"name": "Update user fields", "status": "PASS"},
    {"name": "Soft-delete user", "status": "PASS"},
    {"name": "Invalid request returns 422", "status": "PASS"},
    {"name": "Unauthenticated request returns 401", "status": "PASS"},
    {"name": "Rate limit returns 429", "status": "PASS"}
  ]
}
JSON

# --- tests/api_endpoints/regression.json --- PASS 5/5
cat > tests/api_endpoints/regression.json <<'JSON'
{
  "feature": "api_endpoints",
  "status": "PASS",
  "passed": 5,
  "failed": 0,
  "total": 5,
  "timestamp": "2026-03-25T10:05:00Z",
  "results": [
    {"name": "Pagination returns correct page size", "status": "PASS"},
    {"name": "User creation idempotency key works", "status": "PASS"},
    {"name": "Soft-delete hides user from list", "status": "PASS"},
    {"name": "Rate limit resets after window", "status": "PASS"},
    {"name": "CORS headers present on all responses", "status": "PASS"}
  ]
}
JSON

# --- tests/search/tests.json --- FAIL 3/5
cat > tests/search/tests.json <<'JSON'
{
  "feature": "search",
  "status": "FAIL",
  "passed": 3,
  "failed": 2,
  "total": 5,
  "timestamp": "2026-03-26T14:00:00Z",
  "results": [
    {"name": "Basic search returns results", "status": "PASS"},
    {"name": "Search with type filter", "status": "PASS"},
    {"name": "Relevance scoring order", "status": "PASS"},
    {"name": "Fuzzy matching threshold", "status": "FAIL", "error": "Fuzzy results not returned for edit distance 2"},
    {"name": "Index update latency under 5 seconds", "status": "FAIL", "error": "Average latency 8.2 seconds"}
  ]
}
JSON

# --- tests/data_model/tests.json --- PASS 12/12
cat > tests/data_model/tests.json <<'JSON'
{
  "feature": "data_model",
  "status": "PASS",
  "passed": 12,
  "failed": 0,
  "total": 12,
  "timestamp": "2026-03-20T09:00:00Z",
  "results": [
    {"name": "User creation persists correctly", "status": "PASS"},
    {"name": "User update modifies updated_at", "status": "PASS"},
    {"name": "Session creation with valid user", "status": "PASS"},
    {"name": "Session expiry check", "status": "PASS"},
    {"name": "Audit log records user actions", "status": "PASS"},
    {"name": "Migration forward applies cleanly", "status": "PASS"},
    {"name": "Migration rollback restores state", "status": "PASS"},
    {"name": "Connection pool handles concurrent access", "status": "PASS"},
    {"name": "Repository findById returns null for missing", "status": "PASS"},
    {"name": "Repository findAll with pagination", "status": "PASS"},
    {"name": "Foreign key constraints enforced", "status": "PASS"},
    {"name": "Index on email column improves lookup", "status": "PASS"}
  ]
}
JSON

# --- tests/billing/tests.json --- PASS 7/7
cat > tests/billing/tests.json <<'JSON'
{
  "feature": "billing",
  "status": "PASS",
  "passed": 7,
  "failed": 0,
  "total": 7,
  "timestamp": "2026-03-22T11:00:00Z",
  "results": [
    {"name": "Usage counter increments", "status": "PASS"},
    {"name": "Free tier limit enforcement", "status": "PASS"},
    {"name": "Pro tier unlimited access", "status": "PASS"},
    {"name": "Stripe webhook processes payment", "status": "PASS"},
    {"name": "Invoice generation for enterprise", "status": "PASS"},
    {"name": "Overage notification at 80 percent", "status": "PASS"},
    {"name": "Overage notification at 100 percent", "status": "PASS"}
  ]
}
JSON

# --- tests/reporting/tests.json --- FAIL 4/5
cat > tests/reporting/tests.json <<'JSON'
{
  "feature": "reporting",
  "status": "FAIL",
  "passed": 4,
  "failed": 1,
  "total": 5,
  "timestamp": "2026-03-24T16:00:00Z",
  "results": [
    {"name": "Daily summary generation", "status": "PASS"},
    {"name": "Monthly billing report totals", "status": "PASS"},
    {"name": "CSV export format", "status": "PASS"},
    {"name": "PDF export format", "status": "PASS"},
    {"name": "Weekly email scheduling", "status": "FAIL", "error": "Cron job fires at wrong timezone offset"}
  ]
}
JSON

# --- tests/reporting/regression.json --- FAIL 4/5
cat > tests/reporting/regression.json <<'JSON'
{
  "feature": "reporting",
  "status": "FAIL",
  "passed": 4,
  "failed": 1,
  "total": 5,
  "timestamp": "2026-03-24T16:10:00Z",
  "results": [
    {"name": "Report date ranges are inclusive", "status": "PASS"},
    {"name": "Empty report shows placeholder", "status": "PASS"},
    {"name": "Large dataset export completes", "status": "PASS"},
    {"name": "Report currency formatting", "status": "PASS"},
    {"name": "Scheduled report email delivery", "status": "FAIL", "error": "Email not sent due to timezone cron bug"}
  ]
}
JSON

# Commit 4: Add test results
git add -A >/dev/null 2>&1
git commit -m "test: add test results" >/dev/null 2>&1

# =====================================================================
# Step 5: Add anchors, invariants, and tombstone
# =====================================================================
echo "[5/5] Creating anchors, invariants, and tombstone..."

# --- features/i_arch_security.md --- (invariant, global scope)
cat > features/_invariants/i_arch_security.md <<'INVARIANT'
> Format-Version: 1.0
> Invariant: true
> Version: 1.0.0
> Source: manual
> Scope: global

# Invariant: Security Standards

## Purpose

Defines the non-negotiable security requirements that apply to all features
and all development phases. These invariants cannot be overridden by
individual feature specs or delivery plan decisions.

## Invariants

1. All API endpoints MUST require authentication unless explicitly marked as public.
2. Passwords MUST be hashed with bcrypt (cost factor >= 12).
3. Session tokens MUST be cryptographically random (256-bit minimum).
4. All database queries MUST use parameterized statements (no string concatenation).
5. PII fields MUST be encrypted at rest.
6. Audit logs MUST be append-only and tamper-evident.
INVARIANT

# --- features/i_policy_data_retention.md --- (invariant, scoped)
cat > features/_invariants/i_policy_data_retention.md <<'INVARIANT'
> Format-Version: 1.0
> Invariant: true
> Version: 1.0.0
> Source: manual
> Scope: data_model.md, billing.md

# Invariant: Data Retention Policy

## Purpose

Defines data retention rules that apply to the data model and billing features.
Scoped to specific features rather than global.

## Invariants

1. User data MUST be retained for 90 days after account deletion.
2. Billing records MUST be retained for 7 years for compliance.
3. Session data MUST be purged within 24 hours of expiry.
4. Audit logs MUST be retained for 1 year minimum.
INVARIANT

# --- features/arch_testing.md --- (technical anchor)
cat > features/architecture/arch_testing.md <<'ANCHOR'
# Anchor: Testing Architecture

> Label: "Testing Architecture"
> Category: "Architecture"

## Purpose

Establishes the testing strategy and infrastructure for the project.
All features must conform to these testing patterns.

## Domain Invariants

1. Every feature MUST have unit tests covering all requirements.
2. Integration tests MUST use isolated database transactions.
3. Test data MUST be generated via factories, not hard-coded fixtures.
4. All tests MUST be deterministic (no random seeds without pinning).
5. CI pipeline MUST run the full test suite on every pull request.
ANCHOR

# --- features/design_visual_system.md --- (design anchor)
cat > features/design/design_visual_system.md <<'ANCHOR'
# Anchor: Visual System

> Label: "Visual System"
> Category: "Design"

## Purpose

Defines the visual design system and component library standards
for all user-facing features.

## Domain Invariants

1. All UI components MUST use the shared color palette (no hard-coded colors).
2. Typography MUST follow the type scale (h1-h6, body, caption).
3. Spacing MUST use the 4px grid system.
4. Interactive elements MUST have visible focus indicators for accessibility.
5. All icons MUST come from the approved icon set.
ANCHOR

# --- features/policy_code_review.md --- (policy anchor)
cat > features/policy/policy_code_review.md <<'ANCHOR'
# Anchor: Code Review Policy

> Label: "Code Review Policy"
> Category: "Policy"

## Purpose

Establishes code review requirements and approval workflows
for all code changes in the project.

## Domain Invariants

1. All code changes MUST be reviewed by at least one team member.
2. Security-sensitive changes MUST have two reviewers.
3. Breaking API changes MUST include a migration guide.
4. Review comments MUST be resolved before merge.
5. Auto-generated code MUST still go through review.
ANCHOR

# --- features/_tombstones/legacy_auth.md --- (retired feature)
cat > features/_tombstones/legacy_auth.md <<'TOMBSTONE'
# Feature: Legacy Authentication (RETIRED)

> Label: "Legacy Auth"
> Category: "Core"

## Retirement Notice

This feature was retired on 2026-02-15. Authentication has been
replaced by the new User Authentication feature (features/user_auth.md).

## Reason for Retirement

- The legacy auth system used MD5 password hashing (insecure).
- Session management was cookie-based without CSRF protection.
- No support for multi-factor authentication.

## Migration Path

All users were migrated to the new auth system via the data migration
in features/data_model.md. Legacy session tokens were invalidated.
TOMBSTONE

# Commit 5: Add anchors, invariants, and tombstone
git add -A >/dev/null 2>&1
git commit -m "feat: add anchors, invariants, and tombstone" >/dev/null 2>&1

# =====================================================================
# Summary
# =====================================================================

echo ""
echo "=== Fixture Ready ==="
echo "Location: $OUTPUT_DIR"
echo ""
echo "Git history (5 commits):"
git log --oneline --reverse
echo ""
echo "Contents:"
echo "  .purlin/           — config.json, config.local.json, delivery_plan.md, PURLIN_OVERRIDES.md"
echo "  features/          — 10 specs: 3 TODO, 2 TESTING, 3 COMPLETE, 2 invariants"
echo "    companions       — 2 impl.md (1 unacknowledged deviation, 1 acknowledged)"
echo "    discoveries      — 2 discoveries.md (2 OPEN + 1 RESOLVED)"
echo "    anchors          — 3 (arch, design, policy)"
echo "    tombstones/      — 1 retired feature"
echo "  tests/             — 5 feature dirs with tests.json + 2 regression.json"
echo "  src/               — app.py, utils/helpers.py"
echo "  CLAUDE.md          — plugin-model references"
echo "  .gitignore         — standard purlin ignores"
echo "  README.md          — project readme"
echo ""

# Count files
FILE_COUNT=$(find "$OUTPUT_DIR" -type f -not -path '*/.git/*' | wc -l | tr -d ' ')
echo "Total files: $FILE_COUNT"
echo ""

echo "Feature breakdown:"
echo "  TODO:      user_auth, dashboard, notifications"
echo "  TESTING:   api_endpoints (unacked deviation, OPEN BUG + OPEN DISCOVERY)"
echo "             search (acked deviation, FAIL 3/5)"
echo "  COMPLETE:  data_model (PASS 12/12, RESOLVED BUG)"
echo "             billing (PASS 7/7, prereq: data_model)"
echo "             reporting (FAIL 4/5, prereq: billing)"
echo ""

echo "Delivery plan phases:"
echo "  Phase 1 — Foundation (COMPLETE):     data_model"
echo "  Phase 2 — Core Features (IN_PROGRESS): user_auth, api_endpoints, billing"
echo "  Phase 3 — UI Layer (PENDING):        dashboard, search, reporting, notifications"
echo ""

echo "To use this fixture:"
echo "  cd $OUTPUT_DIR"
echo "  claude --plugin-dir $PROJECT_ROOT"
echo "  # then run: purlin:resume"
