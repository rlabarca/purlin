# QA Command Tables

> This file is read by the QA Agent during the Startup Print Sequence (Section 3.0).
> Print the appropriate variant verbatim based on the current branch.

**CRITICAL:** Printing the command table means outputting the pre-formatted text block below **verbatim**. Do NOT invoke the `/pl-status` skill, do NOT call `tools/cdd/status.sh`, and do NOT use any tool during this step. Any tool or skill invocation before Section 3.0.1 is complete is a protocol violation.

## Main Branch Variant

Print this variant when the branch is `main` (no active collaboration branch).

```
Purlin QA — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the QA Agent — it runs through test scenarios, flags
anything that looks off, and confirms the code matches the spec.
Point it at a feature or let it find what's ready to verify.
Spotted a bug? Use /pl-discovery anytime to log it.

  Global
  ──────
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state
  /pl-help                   Re-display this command list
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-agent-config           Modify agent config
  /pl-cdd                    Start, stop, or check CDD Dashboard
  /pl-override-edit          Edit & validate QA_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

  Verification
  ──────
  /pl-verify <name>          Run interactive verification for a feature
  /pl-web-test [name]     Run web test verification via Playwright
  /pl-complete <name>        Mark a verified feature as complete
  /pl-qa-report              Summary of open discoveries and features
  /pl-fixture                Test fixture convention reference

  Cross-Agent Communication
  ──────
  /pl-discovery <name>       Record a structured discovery

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
Purlin QA — Ready  [Branch: <branch>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the QA Agent — it runs through test scenarios, flags
anything that looks off, and confirms the code matches the spec.
Point it at a feature or let it find what's ready to verify.
Spotted a bug? Use /pl-discovery anytime to log it.

  Global
  ──────
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state
  /pl-help                   Re-display this command list
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-agent-config           Modify agent config
  /pl-cdd                    Start, stop, or check CDD Dashboard
  /pl-override-edit          Edit & validate QA_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

  Verification
  ──────
  /pl-verify <name>          Run interactive verification for a feature
  /pl-web-test [name]     Run web test verification via Playwright
  /pl-complete <name>        Mark a verified feature as complete
  /pl-qa-report              Summary of open discoveries and features
  /pl-fixture                Test fixture convention reference

  Cross-Agent Communication
  ──────
  /pl-discovery <name>       Record a structured discovery

  Collaboration & Git
  ──────
  /pl-remote-push            Push active branch to remote
  /pl-remote-pull            Pull remote into active branch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

