# Architect Command Tables

> This file is read by the Architect during the Startup Print Sequence (Section 5.0).
> Print the appropriate variant verbatim based on the current branch.

## Main Branch Variant

Print this variant when the branch is `main` (no active collaboration branch).

```
Purlin Architect — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state across context clears
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-spec <topic>           Add or refine a feature spec
  /pl-anchor <topic>         Create or update an anchor node
  /pl-tombstone <name>       Retire a feature (generates tombstone for Builder)
  /pl-design-ingest          Ingest a design artifact into a feature's visual spec
  /pl-design-audit           Audit design artifact integrity and staleness
  /pl-release-check          Execute the CDD release checklist step by step
  /pl-release-run            Run a single release step by name
  /pl-release-step           Create, modify, or delete a local release step
  /pl-override-edit          Safely edit an override file
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-spec-from-code         Reverse-engineer feature specs from existing code
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
Purlin Architect — Ready  [Branch: <branch>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state across context clears
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-spec <topic>           Add or refine a feature spec
  /pl-anchor <topic>         Create or update an anchor node
  /pl-tombstone <name>       Retire a feature (generates tombstone for Builder)
  /pl-design-ingest          Ingest a design artifact into a feature's visual spec
  /pl-design-audit           Audit design artifact integrity and staleness
  /pl-release-check          Execute the CDD release checklist step by step
  /pl-release-run            Run a single release step by name
  /pl-release-step           Create, modify, or delete a local release step
  /pl-override-edit          Safely edit an override file
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-spec-from-code         Reverse-engineer feature specs from existing code
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-agent-config           Modify agent config in .purlin/config.json
  /pl-remote-push            Push active branch to remote
  /pl-remote-pull            Pull remote into active branch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Isolated Session Variant

Print this variant when the branch starts with `isolated/`. Substitute the actual isolation name for `<name>`.

```
Purlin Architect — Ready  [Isolated: <name>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state across context clears
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-spec <topic>           Add or refine a feature spec
  /pl-anchor <topic>         Create or update an anchor node
  /pl-tombstone <name>       Retire a feature (generates tombstone for Builder)
  /pl-design-ingest          Ingest a design artifact into a feature's visual spec
  /pl-design-audit           Audit design artifact integrity and staleness
  /pl-release-check          Execute the CDD release checklist step by step
  /pl-release-run            Run a single release step by name
  /pl-release-step           Create, modify, or delete a local release step
  /pl-override-edit          Safely edit an override file
  /pl-override-conflicts     Check override for conflicts with base
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-spec-from-code         Reverse-engineer feature specs from existing code
  /pl-update-purlin          Intelligent submodule update with conflict resolution
  /pl-agent-config           Modify agent config in .purlin/config.json
  /pl-isolated-push          Merge isolation branch to active branch
  /pl-isolated-pull          Pull active branch into isolation branch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
