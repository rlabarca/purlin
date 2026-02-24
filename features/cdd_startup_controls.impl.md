# Implementation Notes: CDD Startup Controls

### BUG Resolution: startup_sequence Flag Ignored (2026-02-22)
Initial implementation ran full orientation despite `startup_sequence: false`. Fixed by Architect adding explicit flag-gating sections (5.0.1/2.0.1/3.0.1) to all three BASE instruction files. Re-verified PASS 2026-02-22.

### Ownership Boundary
The Builder implements: config schema updates (both `config.json` and `purlin-config-sample/config.json`), launcher validation logic, dashboard checkbox controls, and API validation. The Architect separately updates instruction files (`instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, `instructions/QA_BASE.md`) to add the startup print sequence and conditional startup behavior. Instruction files are not Builder-owned.

### Config Reading Pattern for New Fields
Launchers read the new flags with the same Python one-liner pattern used for existing agent fields:
```sh
eval "$(python3 -c "
import json, sys
try:
    cfg = json.load(open('.purlin/config.json'))
    a = cfg.get('agents', {}).get('ROLE', {})
    print('AGENT_STARTUP=' + ('true' if a.get('startup_sequence', True) else 'false'))
    print('AGENT_RECOMMEND=' + ('true' if a.get('recommend_next_actions', True) else 'false'))
except Exception:
    print('AGENT_STARTUP=true')
    print('AGENT_RECOMMEND=true')
")"
```
The `ROLE` placeholder is substituted per-launcher (`architect`, `builder`, `qa`).

### Suggest-Next Disable Logic
The "Startup Sequence" checkbox `onchange` handler: when unchecked, sets `checkbox_suggest_next.disabled = true` and `checkbox_suggest_next.checked = false`, then marks both controls as pending. When re-checked, restores `checkbox_suggest_next.disabled = false` and restores the checkbox to its pre-disable state (cached locally before the disable action).

### Dashboard Grid Extension
The base agent row grid from `cdd_agent_configuration.md` uses `grid-template-columns: 64px 140px 80px 60px` (agent-name | model | effort | YOLO). Extend with two fixed-width columns: `grid-template-columns: 64px 140px 80px 60px 60px 60px` (agent-name | model | effort | YOLO | Startup/Sequence | Suggest/Next). The column header row gains two new cells with two-line text ("Startup" / "Sequence" and "Suggest" / "Next") using `<br>` or CSS wrapping; no inline labels appear in the agent data rows.

### QA Verification (2026-02-22)
All 6 manual scenarios PASS. Expert Mode BUG (QA invokes /pl-status before reading startup flags) re-verified PASS after Architect added CRITICAL prohibition to QA_BASE.md Section 3.0.

### **[CLARIFICATION]** BUG Ownership: /pl-status Invocation Before Flag Read (Severity: INFO)
The BUG "QA agent invokes /pl-status before reading startup flags" was in Architect scope, not Builder scope. All Builder-owned code (launchers, API validation, dashboard checkboxes, config schema) was implemented and passing 19/19 tests. The bug was an LLM agent behavior issue: the QA agent did not follow the instruction ordering in `QA_BASE.md` Section 3.0.1. Fixed 2026-02-22 by adding a CRITICAL prohibition to `QA_BASE.md` Section 3.0: the print-table step must output the pre-formatted text verbatim with no tool or skill invocations. The Builder has no mechanism to enforce instruction-level behavior from launchers (per Section 2.3: "No behavioral injection"). This case also drove a SOP update — see `HOW_WE_WORK_BASE.md` Section 7.5 and `policy_critic.md` Section 2.4 for the new `Action Required: Architect` override mechanism for instruction-level BUGs.
