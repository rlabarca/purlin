# TOMBSTONE: release_system_docs

**Retired:** 2026-03-26
**Reason:** Replaced by the Agentic Toolbox system (features/toolbox_core.md, features/pl_toolbox.md).

## Retired Features

- release_refresh_docs.md
- release_sync_docs_confluence.md
- release_sync_docs_confluence.impl.md
- release_sync_docs_github_wiki.md
- release_record_version_notes.md
- release_record_version_notes.impl.md
- release_record_version_notes.discoveries.md

## Files to Delete

None. Documentation scripts have been preserved as toolbox tools.

## Dependencies to Check

- References to release doc refresh steps updated to toolbox action references
- Confluence and GitHub Wiki sync configurations updated to toolbox action format
- Version notes recording workflow updated to use toolbox execution

## Context

This group defined the documentation lifecycle steps within the release process: refreshing local documentation for staleness and cross-linking, syncing documentation to Confluence, syncing documentation to GitHub Wiki, and recording version notes. The `refresh_docs` step performed doc freshness review, automatic cross-linking, and index generation. The sync steps handled publishing to external platforms. The version notes step recorded release summaries. These capabilities have been preserved as reusable toolbox actions; only the release-system-specific feature specs are retired.
