# Implementation Notes: CDD Agent Configuration

### Agent Row Grid Layout
Uses CSS Grid with a column header row and three agent data rows. The header row contains column label cells; narrow checkbox column headers use two-line text (via `<br>` or CSS line wrapping) to fit within their fixed widths. Suggested column definition: `grid-template-columns: 64px 140px 80px 60px` (agent-name | model | effort | YOLO). Hidden capability-gated controls use `visibility: hidden` (not `display: none`) to preserve column space and prevent layout shift. No inline label appears adjacent to checkboxes in the agent data rows.

### YOLO Checkbox Semantics
The YOLO checkbox has no inline label; it is identified solely by the column header. Its checked state maps directly to `bypass_permissions` in config.json. Checked = agent skips permission prompts (`bypass_permissions: true`). Unchecked = agent asks before using tools (`bypass_permissions: false`).

### Pending-Write Lock
Uses a `pendingWrites` Map (key: control identifier like `"builder.bypass_permissions"`, value: the user's pending DOM value). On user interaction, the event handler stores the value via `pendingWrites.set()`. In `diffUpdateAgentRows()`, controls present in the Map are skipped.

**Per-request lock association (spec update 2026-03-06):** The pending-write lock change is cross-cutting -- it affects ALL controls, not just context guard. When implementing, each pending lock must be associated with the specific POST request that carries its change. Only locks included in that POST are cleared on response; locks added after the POST was sent remain pending. This prevents rapid sequential edits from being reverted by stale responses. The previous approach of clearing all pending locks on any POST response is insufficient. **Full scope re-implementation is warranted** for this change.

### Flicker-Free Refresh
On 5-second auto-refresh, `initAgentsSection()` compares incoming config JSON against the cached `agentsConfig` before deciding whether to re-render. If config is unchanged, rendering is skipped entirely. If changed, `diffUpdateAgentRows()` updates only the controls whose values differ.

### Badge Grouping
Both the server-side Python badge and client-side JS badge use the same algorithm: group model labels by count, sort by count descending then alphabetically, format as `"<count>x <label>"` segments joined by `" | "`.

### DOM Identifiers
All HTML IDs, CSS classes, JS variable names, and localStorage section-name entries for this section use the `agents` prefix (e.g., `agents-section`, `initAgentsSection()`, `agentsConfig`). If a prior implementation pass used `models`-prefixed identifiers, the Builder MUST rename them back. The `purlin-section-states` localStorage key itself is unchanged; only the section name entry within that object changes from `"models"` (if applicable) back to `"agents"`.

### Test Directory
The automated test suite lives at `tests/cdd_agent_configuration/`. If a prior implementation pass renamed this to `tests/cdd_model_configuration/`, rename it back. The `tests.json` file inside should be preserved.

BUG — Live agent turn counters not shown in Dashboard agent config rows; fixed by implementing GET /context-guard/counters endpoint and rendering span UI with 5-second auto-refresh.
DISCOVERY — Concurrent threshold changes caused value revert due to pending-write lock gap; lock extended to block any response (not just auto-refresh) from overwriting controls with pending edits.

### Audit Finding -- 2026-03-16

[DISCOVERY] Visual separator between Workspace and Agents sections needs CSS margin verification — **ACKNOWLEDGED**

**Source:** /pl-spec-code-audit --deep
**Severity:** MEDIUM
**Details:** The visual spec requires a visible vertical gap between sections. Verify that CSS margin between the Workspace container bottom and the Agents section heading matches the gap between Active/Complete sections and Workspace sections.
**Suggested fix:** Add or verify `margin-top` on the Agents section container matching existing section gaps.

### Audit Finding -- 2026-03-16

[DISCOVERY] Per-request pending-write lock isolation has no test coverage — **ACKNOWLEDGED**

**Source:** /pl-spec-code-audit --deep
**Severity:** MEDIUM
**Details:** Implementation notes describe per-request lock association as warranted, but no test covers concurrent rapid edits being isolated from stale responses.
**Suggested fix:** Add test `test_pending_lock_per_request_isolation()` or escalate as infeasible if concurrency testing is impractical in the current test harness.

**[DISCOVERY] [ACKNOWLEDGED]** Pending write concurrent isolation untested
**Source:** /pl-spec-code-audit --deep (M40)
**Severity:** MEDIUM
**Details:** The per-request pending-write lock (preventing stale POST responses from overwriting newer edits) has no runtime concurrency test. Only structural presence of JS patterns is tested. The impl note already acknowledges this.
**Suggested fix:** Add a test that simulates concurrent requests: fire two POSTs with overlapping timing, verify the second write's pending state is not clobbered by the first response.
