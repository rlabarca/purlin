# Implementation Notes: Push to Remote Repository

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|


This global release step has `code: null` (interactive). It cannot be automated as a one-liner because it requires remote/branch discovery and user confirmation before pushing. PM mode executes the agent instructions interactively during the release process.

In Purlin's own `.purlin/release/config.json`, this step is `enabled: true`. A companion local step `publish_to_github` handles pushing to the public GitHub remote as a separate deliberate action.
