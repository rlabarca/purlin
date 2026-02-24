# Implementation Notes: Verify Dependency Integrity

This step is a structural read-only check. The Architect does not modify feature files as part of this step. Regenerating the dependency cache via `tools/cdd/status.sh --graph` is permissible and does not count as a spec modification.

The dependency graph is computed and cached by `tools/cdd/status.sh --graph`. Manual graph file edits are not supported; the cache is always regenerated from source feature files.
