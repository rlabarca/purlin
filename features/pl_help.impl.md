# Implementation Notes: Skill -- /pl-help

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (see prose) | [ACKNOWLEDGED]** Skill contradicts spec on --help execution | DISCOVERY | PENDING |

### Command Table Source
The skill reads the role-appropriate command table from `instructions/references/{role}_commands.md` and prints the correct variant based on the current branch (main, collaboration, or isolated). This is the same logic used by the Startup Print Sequence and `/pl-resume`.

### Role Detection
Uses the same 3-tier fallback as `/pl-resume`: explicit argument, system prompt inference, then user prompt.

### Audit Finding -- 2026-03-23

**[DISCOVERY] [ACKNOWLEDGED]** Skill contradicts spec on --help execution
**Source:** /pl-spec-code-audit --deep (H14)
**Severity:** HIGH
**Details:** Spec §2.5 requires the skill to run each discovered `pl-*.sh` script with `--help` (stderr suppressed, 3-second timeout) and display the output. The skill file Step 4.4 explicitly says "Do NOT attempt to run the scripts or fetch `--help` output." This is a direct contradiction. Users asking "how do I run X" get filenames only, not usage flags like `--continuous` or `-p <port>`.
**Suggested fix:** Update skill file to execute each script with `--help` per spec §2.5. Add fallback text `(no help -- run pl-init.sh to refresh)` for scripts that produce no output or exit non-zero.
