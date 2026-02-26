# Implementation Notes: Submodule Sync

*   **No External Dependencies:** Use only git and standard shell utilities. Do not require `jq`, `python`, or other tools.
*   **Diff Readability:** Consider using `--stat` for a summary view and `--no-color` for clean terminal output, followed by the full diff.
*   **Structural Change Detection:** A simple heuristic: grep the diff output for lines that modify markdown headers (`^## `, `^### `) in the `instructions/` directory and flag them as potential override impact points.
*   **pl-edit-base.md Exclusion (Section 2.6):** The command file sync loop silently skips `pl-edit-base.md` via a filename check before any processing. The file is not reported, not warned about, and not counted in the summary — treated as if the change doesn't exist.
*   **Spec-vs-implementation cross-validation (DISCOVERY resolved 2026-02-24):** Full audit confirmed all requirements (SHA handling, changelog display, command file sync, pl-edit-base exclusion, project root detection) match implementation. No discrepancies found, no spec changes required.
*   **[CLARIFICATION]** Remote tracking branch detection uses a three-step fallback: (1) if on a branch, use its configured upstream, (2) try `origin/main`, (3) try `origin/master`. If none found, print a warning and skip the update check. (Severity: INFO)
*   **[CLARIFICATION]** The `read` for the y/n prompt defaults to "n" on EOF (`read -r REPLY || REPLY="n"`), allowing the script to run non-interactively (piped input) without hanging. (Severity: INFO)
*   **[CLARIFICATION]** The fetch uses `--quiet` with stderr suppressed; on failure it warns and continues rather than aborting, since the fetch is best-effort (network may be unavailable). (Severity: INFO)
*   DISCOVERY — Script originally lacked auto-fetch; spec updated (2026-02-26) to require fetching from remote and prompting user before sync, making the script self-contained.
