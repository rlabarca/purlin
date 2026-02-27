# QA Command Tables

> This file is read by the QA Agent during the Startup Print Sequence (Section 3.0).
> Print the appropriate variant verbatim based on the current branch.

**CRITICAL:** Printing the command table means outputting the pre-formatted text block below **verbatim**. Do NOT invoke the `/pl-status` skill, do NOT call `tools/cdd/status.sh`, and do NOT use any tool during this step. Any tool or skill invocation before Section 3.0.1 is complete is a protocol violation.

## Main Branch Variant

```
Purlin QA — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-verify <name>          Run interactive verification for a feature
  /pl-discovery <name>       Record a structured discovery
  /pl-complete <name>        Mark a verified feature as complete
  /pl-qa-report              Summary of open discoveries and TESTING features
  /pl-override-edit          Safely edit QA_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-collab-push            Push local main to remote collab branch (main only)
  /pl-collab-pull            Pull remote collab branch into local main (main only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Isolated Session Variant

Print this variant when the branch starts with `isolated/`. Substitute the actual isolation name for `<name>`.

```
Purlin QA — Ready  [Isolated: <name>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-verify <name>          Run interactive verification for a feature
  /pl-discovery <name>       Record a structured discovery
  /pl-complete <name>        Mark a verified feature as complete
  /pl-qa-report              Summary of open discoveries and TESTING features
  /pl-override-edit          Safely edit QA_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-local-push             Merge isolation branch to main
  /pl-local-pull             Pull main into isolation branch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
