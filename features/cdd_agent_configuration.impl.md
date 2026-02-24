# Implementation Notes: CDD Agent Configuration

### Agent Row Grid Layout
Uses CSS Grid with a column header row and three agent data rows. The header row contains column label cells; narrow checkbox column headers use two-line text (via `<br>` or CSS line wrapping) to fit within their fixed widths. Suggested column definition: `grid-template-columns: 64px 140px 80px 60px` (agent-name | model | effort | YOLO). Hidden capability-gated controls use `visibility: hidden` (not `display: none`) to preserve column space and prevent layout shift. No inline label appears adjacent to checkboxes in the agent data rows.

### YOLO Checkbox Semantics
The YOLO checkbox has no inline label; it is identified solely by the column header. Its checked state maps directly to `bypass_permissions` in config.json. Checked = agent skips permission prompts (`bypass_permissions: true`). Unchecked = agent asks before using tools (`bypass_permissions: false`).

### Pending-Write Lock
Uses a `pendingWrites` Map (key: control identifier like `"builder.bypass_permissions"`, value: the user's pending DOM value). On user interaction, the event handler stores the value via `pendingWrites.set()`. In `diffUpdateAgentRows()`, controls present in the Map are skipped. When `POST /config/agents` resolves (success or error), the Map is cleared.

### Flicker-Free Refresh
On 5-second auto-refresh, `initAgentsSection()` compares incoming config JSON against the cached `agentsConfig` before deciding whether to re-render. If config is unchanged, rendering is skipped entirely. If changed, `diffUpdateAgentRows()` updates only the controls whose values differ.

### Badge Grouping
Both the server-side Python badge and client-side JS badge use the same algorithm: group model labels by count, sort by count descending then alphabetically, format as `"<count>x <label>"` segments joined by `" | "`.

### DOM Identifiers
All HTML IDs, CSS classes, JS variable names, and localStorage section-name entries for this section use the `agents` prefix (e.g., `agents-section`, `initAgentsSection()`, `agentsConfig`). If a prior implementation pass used `models`-prefixed identifiers, the Builder MUST rename them back. The `purlin-section-states` localStorage key itself is unchanged; only the section name entry within that object changes from `"models"` (if applicable) back to `"agents"`.

### Test Directory
The automated test suite lives at `tests/cdd_agent_configuration/`. If a prior implementation pass renamed this to `tests/cdd_model_configuration/`, rename it back. The `tests.json` file inside should be preserved.
