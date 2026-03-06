# Implementation Notes: /pl-isolated-pull

**[AUTONOMOUS]** PROJECT_ROOT resolution updated to use negative-match heuristic: "the entry whose `branch` field does NOT start with `refs/heads/isolated/`" instead of looking specifically for `refs/heads/main`. This handles the case where the main checkout is on a collaboration branch during active branch collaboration. The spec does not detail PROJECT_ROOT resolution, so this decision fills the gap. (Severity: WARN)
