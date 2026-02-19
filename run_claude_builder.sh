#!/bin/bash
claude --print-system-prompt-file ".agentic_devops/BUILDER_INSTRUCTIONS.md" --dangerously-skip-permissions "$@"
