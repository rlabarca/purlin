# The Features Folder

How feature files are organized in a Purlin project.

---

## Structure

Feature files live in category subfolders under `features/`. Each subfolder groups related features by their `> Category:` metadata.

```
features/
  skills_common/         Agent Skills: Common
  skills_engineer/       Agent Skills: Engineer
  skills_pm/             Agent Skills: PM
  skills_qa/             Agent Skills: QA
  design_standards/      Common Design Standards
  framework_core/        Framework Core
  infrastructure/        Infrastructure
  install_update/        Install, Update & Scripts
  policy/                Policy
  shared_definitions/    Shared Agent Definitions
  test_infrastructure/   Test Infrastructure
  _design/               Design artifacts (images, PDFs, brief.json)
  _digests/              Generated branch comparison digests
  _invariants/           Externally-sourced invariant files (i_*.md)
  _tombstones/           Features queued for deletion
```

Consumer projects use their own categories (e.g., `core/`, `ui/`, `analytics/`). The canonical mapping from category string to folder slug is defined in `references/feature_format.md`.

## File Types

Each category folder contains up to three file types per feature:

| Pattern | Owner | Purpose |
|---------|-------|---------|
| `<name>.md` | PM | Feature specification |
| `<name>.impl.md` | Engineer | Implementation companion (deviations, notes) |
| `<name>.discoveries.md` | QA | Discovery sidecar (bugs, intent drift) |

Companion and discovery files always live alongside their parent spec in the same category folder.

## System Folders

Folders prefixed with `_` are system folders, not feature categories:

- **`_invariants/`** -- Externally-sourced constraint documents (`i_*.md`). No mode can edit these directly; changes come via `purlin:invariant sync`.
- **`_tombstones/`** -- Features queued for retirement. Engineer processes these before regular work.
- **`_digests/`** -- Machine-generated branch comparison summaries. Gitignored.
- **`_design/`** -- Design artifacts organized per-feature: `_design/<feature_stem>/brief.json`, screenshots, PDFs.

## Finding Features

Never construct a flat path like `features/<name>.md`. Feature files are resolved by searching recursively:

```
features/**/<name>.md
```

The scan engine, graph engine, and all skills use this resolution pattern. The agent definition (Section 2.2.1) mandates glob-first resolution.

## Prerequisites

Prerequisites use bare filenames without paths:

```markdown
> Prerequisite: purlin_mode_system.md
```

The scanner resolves the filename across all category subfolders automatically.

## Category Rules

- One category per feature. The folder is the category.
- `> Category:` metadata in the file must match the containing folder.
- New categories require adding a slug to the mapping table in `references/feature_format.md`.
- `purlin:update` automatically organizes misplaced files into their correct category folder.

## Anchor Nodes

Anchor nodes (`arch_*`, `design_*`, `policy_*`) live in whatever category folder matches their `> Category:` metadata, just like regular features. They are distinguished by filename prefix, not by folder.

## Adding a New Feature

1. Choose the appropriate category from the mapping table.
2. Create the file in the matching subfolder: `features/<slug>/<name>.md`.
3. Set `> Category:` metadata to match the folder.
4. Use `> Prerequisite: <name>.md` (bare filename) for dependencies.
