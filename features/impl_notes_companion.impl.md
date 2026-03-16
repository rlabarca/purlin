## Implementation Notes

### Companion File Resolution
The Critic resolves companion files by stripping the `.md` extension from the feature filename and appending `.impl.md`. For example, `features/critic_tool.md` resolves to `features/critic_tool.impl.md`.

### API Endpoint
The `/impl-notes` endpoint reads companion files from disk on each request (no caching). The response is raw markdown suitable for rendering in the CDD Dashboard's modal overlay.

### Orphan Detection
The Critic scans all `features/*.impl.md` files during each pass. For each, it checks whether a corresponding `features/<name>.md` exists. Orphaned companions are flagged as MEDIUM-priority Architect action items with the recommendation to either create the parent feature or delete the orphan.
