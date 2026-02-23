# Builder Overrides: Sample Task Manager

> Project-specific rules for the Builder role in this sample project.

## Tech Stack

Implement the API using the simplest available stack in the project's language. Python + Flask or Node.js + Express are preferred. Use in-memory storage (module-level list). No database setup is required.

## Test Framework

Use pytest (Python) or Jest (Node). Keep tests minimal — one test file per feature is sufficient.

## Worktree Pre-Flight

Before starting implementation, verify that `git log --oneline` shows the Architect's spec commit for the feature you are implementing. If the spec commit is not visible, run `git merge main` to pull the merged spec branch.
