# Anchor: Task Data Schema

> Label: "Anchor: Task Data Schema"
> Category: "Architecture"

## 1. Overview

This anchor node defines the canonical Task data model for the sample task manager application. All features that read or write Task data MUST declare a prerequisite link to this file.

## 2. Task Model

A Task has the following fields:

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | string | UUID v4, system-generated, immutable |
| `title` | string | 1–200 characters, required |
| `status` | enum | `"open"` or `"done"`, default `"open"` |
| `tags` | string[] | 0–10 tags; each tag 1–50 chars; no duplicates |
| `created_at` | ISO 8601 string | system-generated, immutable |
| `updated_at` | ISO 8601 string | system-updated on any field change |

## 3. Invariants

- `id` and `created_at` are set on creation and never modified.
- `updated_at` reflects the timestamp of the most recent mutation.
- `tags` is an array; duplicates are rejected at the API level.
- `status` transitions: `open → done` and `done → open` are both allowed (tasks can be reopened).

## 4. Storage

For the sample application, tasks are stored in memory (no persistence). A module-level list in the backend serves as the data store. This is intentional — the sample demonstrates the Purlin workflow, not production persistence.

## Implementation Notes

This anchor node defines the data contract. No code implements the anchor itself — it constrains consumer features. Any feature that reads or writes Task data must reflect this schema exactly.
