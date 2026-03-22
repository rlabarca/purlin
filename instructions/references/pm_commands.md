# PM Command Tables

> This file is read by the PM during the Startup Print Sequence (Section 7.0).
> Print the appropriate variant verbatim based on the current branch.

## Main Branch Variant

Print this variant when the branch is `main` (no active collaboration branch).

```
Purlin PM -- Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the PM agent -- it helps product managers and designers
shape feature specs and iterate on Figma designs. It doesn't
write code; specs are handed to the Architect for validation,
then to the Builder for implementation.

  Specification & Design
  ──────
  /pl-spec <topic>           Shape a feature spec (guided)
  /pl-anchor <topic>         Create or update a design/policy anchor
  /pl-design-ingest          Ingest Figma design into visual spec
  /pl-design-audit           Audit design-spec consistency

  Navigation
  ──────
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-status                 Check CDD status
  /pl-help                   Re-display this command list
  /pl-resume [save|role]     Save or restore session state
  /pl-override-edit          Edit PM_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Branch Collaboration Variant

Print this variant when `.purlin/runtime/active_branch` exists and is non-empty. Substitute the actual branch name for `<branch>`.

```
Purlin PM -- Ready  [Branch: <branch>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the PM agent -- it helps product managers and designers
shape feature specs and iterate on Figma designs. It doesn't
write code; specs are handed to the Architect for validation,
then to the Builder for implementation.

  Specification & Design
  ──────
  /pl-spec <topic>           Shape a feature spec (guided)
  /pl-anchor <topic>         Create or update a design/policy anchor
  /pl-design-ingest          Ingest Figma design into visual spec
  /pl-design-audit           Audit design-spec consistency

  Navigation
  ──────
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-status                 Check CDD status
  /pl-help                   Re-display this command list
  /pl-resume [save|role]     Save or restore session state
  /pl-override-edit          Edit PM_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
