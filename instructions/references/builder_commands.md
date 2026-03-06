# Builder Command Tables

> This file is read by the Builder during the Startup Print Sequence (Section 2.0).
> Print the appropriate variant verbatim based on the current branch.

## Main Branch Variant

Print this variant when the branch is `main` (no active collaboration branch).

```
Purlin Builder — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the Builder — it turns feature specs into working code,
writes tests, and documents what it learned along the way.
Tell it what to build or let it pick up the next item.

  Global
  ──────
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state
  /pl-help                   Re-display this command list
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-agent-config           Modify agent config
  /pl-context-guard          View or modify context guard settings
  /pl-override-edit          Edit & validate BUILDER_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

  Implementation
  ──────
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-web-verify [name]      Verify web-testable features via Playwright
  /pl-spec-code-audit        Full spec-code audit (plan mode)

  Cross-Agent Communication
  ──────
  /pl-propose <topic>        Suggest a spec change to the Architect
  /pl-infeasible <name>      Escalate a feature as unimplementable

  Collaboration & Git
  ──────
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

This is the Builder — it turns feature specs into working code,
writes tests, and documents what it learned along the way.
Tell it what to build or let it pick up the next item.

  Global
  ──────
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state
  /pl-help                   Re-display this command list
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-agent-config           Modify agent config
  /pl-context-guard          View or modify context guard settings
  /pl-override-edit          Edit & validate BUILDER_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

  Implementation
  ──────
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-web-verify [name]      Verify web-testable features via Playwright
  /pl-spec-code-audit        Full spec-code audit (plan mode)

  Cross-Agent Communication
  ──────
  /pl-propose <topic>        Suggest a spec change to the Architect
  /pl-infeasible <name>      Escalate a feature as unimplementable

  Collaboration & Git
  ──────
  /pl-remote-push            Push active branch to remote
  /pl-remote-pull            Pull remote into active branch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Isolated Session Variant

Print this variant when the branch starts with `isolated/`. Substitute the actual isolation name for `<name>`.

```
Purlin Builder — Ready  [Isolated: <name>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the Builder — it turns feature specs into working code,
writes tests, and documents what it learned along the way.
Tell it what to build or let it pick up the next item.

  Global
  ──────
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state
  /pl-help                   Re-display this command list
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-agent-config           Modify agent config
  /pl-context-guard          View or modify context guard settings
  /pl-override-edit          Edit & validate BUILDER_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

  Implementation
  ──────
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-web-verify [name]      Verify web-testable features via Playwright
  /pl-spec-code-audit        Full spec-code audit (plan mode)

  Cross-Agent Communication
  ──────
  /pl-propose <topic>        Suggest a spec change to the Architect
  /pl-infeasible <name>      Escalate a feature as unimplementable

  Collaboration & Git
  ──────
  /pl-isolated-push          Merge isolation branch to active branch
  /pl-isolated-pull          Pull active branch into isolation branch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
