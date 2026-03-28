#!/bin/bash
# SessionStart hook — fires on clear and compact events.
# Injects a context reminder so the agent knows Purlin is active.

echo "IMPORTANT: Context was cleared. Purlin plugin is active. Run purlin:start to restore session context."
exit 0
