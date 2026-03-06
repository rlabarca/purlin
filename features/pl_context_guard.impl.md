# Implementation Notes: Skill -- Context Guard

### Config Target
The `/pl-context-guard` skill reads and writes `context_guard` and `context_guard_threshold` fields in `.purlin/config.local.json` (the gitignored local config). It uses the same config resolver as the CDD Dashboard API.

### Validation
Threshold values must be integers in the range 5-200, matching the `POST /config/agents` validation in `cdd_agent_configuration.md`.
