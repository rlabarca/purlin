## Implementation Notes

### Companion File Resolution
The Critic resolves companion files by stripping the `.md` extension from the feature filename and appending `.impl.md`. For example, `features/critic_tool.md` resolves to `features/critic_tool.impl.md`.

### API Endpoint
The `/impl-notes` endpoint reads companion files from disk on each request (no caching). The response is raw markdown suitable for rendering in the CDD Dashboard's modal overlay.

### Orphan Detection
The Critic scans all `features/*.impl.md` files during each pass. For each, it checks whether a corresponding `features/<name>.md` exists. Orphaned companions are flagged as MEDIUM-priority Architect action items with the recommendation to either create the parent feature or delete the orphan.

### Re-Verification (2026-03-24)

**[CLARIFICATION]** Sections 2.2-2.10 were re-verified against the existing implementation. All requirements are satisfied by existing code. No code changes were needed. (Severity: INFO)

Verified sections:
- **2.2 Companion File Resolution**: `resolve_impl_notes()` in critic.py resolves by naming convention without feature file references.
- **2.3 Companion File Structure**: Companion files have no metadata headers; begin with heading and content directly.
- **2.4 Exclusion Rules**: graph.py, serve.py, cleanup_orphaned_features.py, and critic.py all exclude `.impl.md` and `.discoveries.md` from feature scanning.
- **2.5 Status Reset Exemption**: CDD status generation excludes `.impl.md` from feature file scanning, so companion edits do not trigger lifecycle resets.
- **2.6 Companion File Resolution in Critic**: `resolve_impl_notes()` reads companions by convention; `check_section_completeness()` checks for companion on disk when inline notes are empty.
- **2.7 Orphan Detection**: `audit_orphan_companions()` in critic.py and `get_referenced_features()` in cleanup_orphaned_features.py both detect orphaned companions.
- **2.8 CDD Dashboard Feature Modal**: Modal tabs (Specification / Implementation Notes) with lazy-loading and caching implemented in serve.py HTML/JS.
- **2.9 Integration Test Fixture Tags**: Fixture tag `companion-with-decisions` defined in spec and referenced in `dev/setup_fixture_repo.sh`.
- **2.10 Companion File API Endpoint**: `_serve_impl_notes()` in serve.py implements `GET /impl-notes?file=<path>` with 200/404 responses.
