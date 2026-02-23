# Feature: Task CRUD

> Label: "Feature: Task CRUD"
> Category: "Core Features"
> Prerequisite: features/arch_data_schema.md

[TODO]

## 1. Overview

Create, read, update, and delete operations for Task objects. Exposed as a REST API with JSON request/response bodies.

## 2. Requirements

### 2.1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tasks` | Create a new task |
| `GET` | `/tasks` | List all tasks |
| `GET` | `/tasks/:id` | Get a single task |
| `PATCH` | `/tasks/:id` | Update task fields |
| `DELETE` | `/tasks/:id` | Delete a task |

### 2.2 Create Task (POST /tasks)

- Request body: `{ "title": "...", "tags": [...] }` (status defaults to `"open"`)
- Response: 201 Created with the full task object
- Validation: title is required; title length 1–200 chars; tags array optional (defaults to `[]`)
- Returns 400 Bad Request when validation fails

### 2.3 List Tasks (GET /tasks)

- Returns all tasks as a JSON array
- Sorted by `created_at` descending (newest first)
- Returns 200 OK with `[]` when no tasks exist

### 2.4 Get Task (GET /tasks/:id)

- Returns the task with the given id
- Returns 404 Not Found when id does not exist

### 2.5 Update Task (PATCH /tasks/:id)

- Request body: any subset of `{ "title": "...", "status": "...", "tags": [...] }`
- Only provided fields are updated; omitted fields are unchanged
- Updates `updated_at` on any successful change
- Returns 200 OK with the updated task object
- Returns 400 when validation fails; 404 when id not found

### 2.6 Delete Task (DELETE /tasks/:id)

- Removes the task from the store
- Returns 204 No Content on success
- Returns 404 when id not found

## 3. Scenarios

### Automated Scenarios

#### Scenario: Create Task Returns 201 with Task Object

    Given the API server is running
    When a POST /tasks request is sent with body { "title": "Buy groceries" }
    Then the response status is 201
    And the response body contains id, title "Buy groceries", status "open", tags [], created_at, updated_at

#### Scenario: Create Task Validates Title Required

    Given the API server is running
    When a POST /tasks request is sent with body {}
    Then the response status is 400

#### Scenario: List Tasks Returns Newest First

    Given two tasks exist, task A created before task B
    When a GET /tasks request is sent
    Then the response contains both tasks
    And task B appears before task A in the array

#### Scenario: Get Task Returns 404 for Unknown ID

    Given the API server is running
    When a GET /tasks/nonexistent-id request is sent
    Then the response status is 404

#### Scenario: Update Task Status

    Given a task exists with id "abc" and status "open"
    When a PATCH /tasks/abc request is sent with body { "status": "done" }
    Then the response status is 200
    And the task status is "done"
    And updated_at is later than the original updated_at

#### Scenario: Delete Task Returns 204

    Given a task exists with id "abc"
    When a DELETE /tasks/abc request is sent
    Then the response status is 204
    And a subsequent GET /tasks/abc returns 404

### Manual Scenarios

None. All scenarios for this feature are fully automated.

## Implementation Notes

This is a sample project for demonstrating Purlin's multi-role collaboration workflow. The backend implementation should be minimal — use the simplest possible stack (e.g., Python Flask or Node.js Express) to expose the endpoints. In-memory storage is intentional (see `arch_data_schema.md` Section 4).
