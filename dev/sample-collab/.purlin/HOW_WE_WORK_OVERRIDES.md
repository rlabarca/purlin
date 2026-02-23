# How We Work: Sample Task Manager Overrides

> This file contains workflow additions specific to the sample-collab project.
> It is the override layer loaded after the Purlin base HOW_WE_WORK instructions.

## Purpose

This sample project demonstrates Purlin's multi-role collaboration workflow using git worktrees. Three agents (Architect, Builder, QA) work concurrently on the same feature set.

## Sample Project Conventions

### Minimal Footprint

This is a demonstration project. Implementations should use the simplest possible stack. Over-engineering is undesirable.

### In-Memory Storage

The backend uses in-memory storage intentionally. Do not add database persistence — it is out of scope for the demonstration.

### Worktree Workflow

Sessions are run from `.worktrees/<role>-session/` directories. Each session has its own `PURLIN_PROJECT_ROOT` pointing to the worktree directory.
