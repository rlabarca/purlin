# Builder Command Tables

> This file is read by the Builder during the Startup Print Sequence (Section 2.0).
> Print the appropriate variant verbatim based on the current branch.

## Main Branch Variant

```
Purlin Builder — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-infeasible <name>      Escalate a feature as unimplementable
  /pl-propose <topic>        Surface a spec change suggestion to the Architect
  /pl-override-edit          Safely edit BUILDER_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-collab-push            Push local main to remote collab branch (main only)
  /pl-collab-pull            Pull remote collab branch into local main (main only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Isolated Session Variant

Print this variant when the branch starts with `isolated/`. Substitute the actual isolation name for `<name>`.

```
Purlin Builder — Ready  [Isolated: <name>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-infeasible <name>      Escalate a feature as unimplementable
  /pl-propose <topic>        Surface a spec change suggestion to the Architect
  /pl-override-edit          Safely edit BUILDER_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-local-push             Merge isolation branch to main
  /pl-local-pull             Pull main into isolation branch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
