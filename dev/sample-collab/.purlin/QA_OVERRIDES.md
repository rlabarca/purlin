# QA Overrides: Sample Task Manager

> Project-specific rules for the QA role in this sample project.

## Verification Scope

All scenarios in this sample project are automated. There are no manual scenarios requiring human verification. QA verification consists of:

1. Confirming the Builder's automated tests pass (`tests/*/tests.json` with `status: "PASS"`).
2. Running `/pl-handoff-check` to confirm readiness to merge.

## Worktree Pre-Flight

Before starting QA verification, verify that `git log --oneline` shows the Builder's `[Ready for Verification]` commit for the feature you are verifying. If the commit is not visible, run `git merge main` to pull the merged implementation branch.
