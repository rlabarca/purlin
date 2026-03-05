# Builder Command Tables

> This file is read by the Builder during the Startup Print Sequence (Section 2.0).
> Print the appropriate variant verbatim based on the current branch.

## Main Branch Variant

Print this variant when the branch is `main` (no active collab session).

```
Purlin Builder — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state across context clears
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-infeasible <name>      Escalate a feature as unimplementable
  /pl-propose <topic>        Surface a spec change suggestion to the Architect
  /pl-override-edit          Safely edit BUILDER_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-agent-config           Modify agent config in .purlin/config.json
  /pl-whats-different        Compare branches (main checkout only)
  /pl-collab-push            Push local collab branch to remote (collab session only)
  /pl-collab-pull            Pull remote collab branch into local (collab session only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Collab Session Variant

Print this variant when the branch starts with `collab/`. Substitute the actual session name for `<session>`.

```
Purlin Builder — Ready  [Collab: <session>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state across context clears
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-infeasible <name>      Escalate a feature as unimplementable
  /pl-propose <topic>        Surface a spec change suggestion to the Architect
  /pl-override-edit          Safely edit BUILDER_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-agent-config           Modify agent config in .purlin/config.json
  /pl-collab-push            Push local collab branch to remote (collab session only)
  /pl-collab-pull            Pull remote collab branch into local (collab session only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Isolated Session Variant

Print this variant when the branch starts with `isolated/`. Substitute the actual isolation name for `<name>`.

```
Purlin Builder — Ready  [Isolated: <name>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state across context clears
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-infeasible <name>      Escalate a feature as unimplementable
  /pl-propose <topic>        Surface a spec change suggestion to the Architect
  /pl-override-edit          Safely edit BUILDER_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-agent-config           Modify agent config in .purlin/config.json
  /pl-local-push             Merge isolation branch to collaboration branch
  /pl-local-pull             Pull collaboration branch into isolation branch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
