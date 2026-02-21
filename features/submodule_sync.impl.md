# Implementation Notes: Submodule Sync

*   **No External Dependencies:** Use only git and standard shell utilities. Do not require `jq`, `python`, or other tools.
*   **Diff Readability:** Consider using `--stat` for a summary view and `--no-color` for clean terminal output, followed by the full diff.
*   **Structural Change Detection:** A simple heuristic: grep the diff output for lines that modify markdown headers (`^## `, `^### `) in the `instructions/` directory and flag them as potential override impact points.
