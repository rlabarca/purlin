# Discovery Sidecar: PM Agent Launcher

## [BUG] M51: PM non-bypass allowedTools missing Write and Edit
- **Status:** RESOLVED
- **Action Required:** Engineer
- **Description:** PM agent's non-bypass allowedTools list did not include Write and Edit tools. The spec (Section 2.1) includes Write and Edit in the PM non-bypass allowedTools list.
- **Resolution:** Added Write and Edit to the allowedTools in pl-run-pm.sh and updated tools/init.sh to include PM in the branch that generates allowedTools with Write and Edit. Added test coverage for PM non-bypass allowedTools.
