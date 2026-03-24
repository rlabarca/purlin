# Implementation Notes: /pl-remote-push

## Test Updates (2026-03-22)

### Removed
- **"pl-remote-push Offers gh Repo Create When gh CLI Available"** -- Removed per spec update. The old gh-specific scenario was replaced by the more general hosting hints approach.

### Added
- **"pl-remote-push Shows Hosting Hints When Available"** (2 assertions) -- Creates a mock `~/.ssh/config` in a temp directory with Host entries for `github.com` and `gitlab.example.com`. Verifies the SSH config parsing logic detects known git hosts (github.com) while excluding non-standard hosts (gitlab.example.com). Confirms the hint message format matches "Detected: github.com (SSH key)".
- **"pl-remote-push Verifies Remote Connectivity"** (2 assertions) -- Creates a local bare remote and verifies `git ls-remote` succeeds (exit 0). Also tests with an invalid remote path (`/nonexistent/path/to/repo.git`) and verifies `git ls-remote` fails (exit 128), confirming the connectivity verification logic.

**[CLARIFICATION]** The hosting hints test uses a mock SSH config file in the sandbox temp directory rather than the real `~/.ssh/config` to keep tests self-contained and avoid side effects. The parsing logic uses the same regex pattern that would be used in the command's Step 2 Remote Guard. (Severity: INFO)

**[CLARIFICATION]** Total test assertion count changed from 16 to 19: removed 1 assertion (gh CLI test), added 4 assertions (2 for hosting hints, 2 for connectivity). (Severity: INFO)
**[DISCOVERY] [ACKNOWLEDGED]** Skill file missing FORBIDDEN enforcement reflection
**Source:** /pl-spec-code-audit --deep (M23)
**Severity:** MEDIUM
**Details:** Spec §2.8 defines FORBIDDEN Pattern Enforcement (no force push, no push to wrong branch). The skill file (`.claude/commands/pl-remote-push.md`) contains no explicit prohibition or validation notes. An agent following the skill alone would have no inline constraint against force-push.
**Suggested fix:** Add a FORBIDDEN enforcement section to the skill file listing the prohibitions from spec §2.8 and `policy_branch_collab.md` Section 4.
