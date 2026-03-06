# Builder Command Tables

> This file is read by the Builder during the Startup Print Sequence (Section 2.0).
> Print the appropriate variant verbatim based on the current branch.

## Main Branch Variant

Print this variant when the branch is `main` (no active collaboration branch).

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
  /pl-web-verify [name]      Automated web verification via Playwright MCP
  /pl-override-edit          Safely edit BUILDER_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-agent-config           Modify agent config in .purlin/config.json
  /pl-whats-different        Compare branches (main checkout only)
  /pl-remote-push            Push active branch to remote
  /pl-remote-pull            Pull remote into active branch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Branch Collaboration Variant

Print this variant when `.purlin/runtime/active_branch` exists and is non-empty. Substitute the actual branch name for `<branch>`.

```
Purlin Builder — Ready  [Branch: <branch>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state across context clears
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-infeasible <name>      Escalate a feature as unimplementable
  /pl-propose <topic>        Surface a spec change suggestion to the Architect
  /pl-web-verify [name]      Automated web verification via Playwright MCP
  /pl-override-edit          Safely edit BUILDER_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-agent-config           Modify agent config in .purlin/config.json
  /pl-remote-push            Push active branch to remote
  /pl-remote-pull            Pull remote into active branch
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
  /pl-web-verify [name]      Automated web verification via Playwright MCP
  /pl-override-edit          Safely edit BUILDER_OVERRIDES.md
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-agent-config           Modify agent config in .purlin/config.json
  /pl-isolated-push          Merge isolation branch to active branch
  /pl-isolated-pull          Pull active branch into isolation branch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
