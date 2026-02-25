# Implementation Notes: Submodule Sync

*   **No External Dependencies:** Use only git and standard shell utilities. Do not require `jq`, `python`, or other tools.
*   **Diff Readability:** Consider using `--stat` for a summary view and `--no-color` for clean terminal output, followed by the full diff.
*   **Structural Change Detection:** A simple heuristic: grep the diff output for lines that modify markdown headers (`^## `, `^### `) in the `instructions/` directory and flag them as potential override impact points.
*   **pl-edit-base.md Exclusion (Section 2.6):** The command file sync loop silently skips `pl-edit-base.md` via a filename check before any processing. The file is not reported, not warned about, and not counted in the summary — treated as if the change doesn't exist.
*   **Spec-vs-implementation cross-validation (DISCOVERY resolved 2026-02-24):** Full audit confirmed all requirements (SHA handling, changelog display, command file sync, pl-edit-base exclusion, project root detection) match implementation. No discrepancies found, no spec changes required.
