# Feature: Task Filtering

> Label: "Feature: Task Filtering"
> Category: "Core Features"
> Prerequisite: features/arch_data_schema.md
> Prerequisite: features/task_crud.md

[TODO]

## 1. Overview

Filter and search operations on the Task list. Extends the `GET /tasks` endpoint with optional query parameters for filtering by status and tags.

## 2. Requirements

### 2.1 Status Filter

- `GET /tasks?status=open` — returns only tasks with `status: "open"`
- `GET /tasks?status=done` — returns only tasks with `status: "done"`
- Invalid `status` values return 400 Bad Request
- Omitting the `status` parameter returns all tasks (existing behavior)

### 2.2 Tag Filter

- `GET /tasks?tag=<value>` — returns tasks that include the given tag
- Multiple tag parameters: `GET /tasks?tag=work&tag=urgent` — returns tasks that have ALL specified tags (AND semantics)
- Tag matching is case-insensitive
- An unrecognized tag (no tasks have it) returns an empty array, not a 404

### 2.3 Combined Filters

- Status and tag filters MAY be combined: `GET /tasks?status=open&tag=work`
- Returns tasks matching ALL specified criteria

### 2.4 Result Ordering

- Filtered results maintain the same ordering as the unfiltered list (newest first by `created_at`)

## 3. Scenarios

### Automated Scenarios

#### Scenario: Filter by Status Open

    Given tasks exist with status "open" and "done"
    When a GET /tasks?status=open request is sent
    Then only tasks with status "open" are returned
    And tasks with status "done" are absent

#### Scenario: Filter by Status Done

    Given tasks exist with status "open" and "done"
    When a GET /tasks?status=done request is sent
    Then only tasks with status "done" are returned

#### Scenario: Invalid Status Returns 400

    Given the API server is running
    When a GET /tasks?status=invalid request is sent
    Then the response status is 400

#### Scenario: Filter by Single Tag

    Given tasks exist: task A with tags ["work"], task B with tags ["personal"]
    When a GET /tasks?tag=work request is sent
    Then only task A is returned

#### Scenario: Filter by Multiple Tags Uses AND Semantics

    Given tasks exist: task A with tags ["work", "urgent"], task B with tags ["work"]
    When a GET /tasks?tag=work&tag=urgent request is sent
    Then only task A is returned (task A has both tags; task B has only one)

#### Scenario: Combined Status and Tag Filter

    Given tasks exist: task A (status=open, tags=["work"]), task B (status=done, tags=["work"])
    When a GET /tasks?status=open&tag=work request is sent
    Then only task A is returned

### Manual Scenarios

None.

## Implementation Notes

Tag matching is case-insensitive. AND semantics for multiple tag filters is intentional — OR semantics would return too many results for the typical use case. Filtering is implemented in the same handler as `GET /tasks` via query parameter parsing. No new endpoint is needed.
