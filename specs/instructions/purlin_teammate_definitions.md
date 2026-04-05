# Feature: purlin_teammate_definitions

> Scope: .claude/agents/purlin-auditor.md, .claude/agents/purlin-builder.md, .claude/agents/purlin-reviewer.md
> Stack: markdown (agent definitions)
> Description: Defines three Claude Code agent roles for the Purlin verify-audit-build loop: an auditor that evaluates proof quality, a builder that fixes code/tests based on audit feedback, and a reviewer that validates specs and detects spec drift. These definitions live in `.claude/agents/` where Claude Code discovers them as available agent roles.

## Rules

- RULE-1: purlin-auditor.md exists with YAML frontmatter containing `name: purlin-auditor`, `description`, and `model` fields
- RULE-2: purlin-builder.md exists with YAML frontmatter containing `name: purlin-builder`, `description`, and `model` fields
- RULE-3: purlin-reviewer.md exists with YAML frontmatter containing `name: purlin-reviewer`, `description`, and `model` fields
- RULE-4: All three agent definitions are located in the `.claude/agents/` directory

## Proof

- PROOF-1 (RULE-1): Read `.claude/agents/purlin-auditor.md`; verify YAML frontmatter contains `name: purlin-auditor`, a `description:` field, and a `model:` field
- PROOF-2 (RULE-2): Read `.claude/agents/purlin-builder.md`; verify YAML frontmatter contains `name: purlin-builder`, a `description:` field, and a `model:` field
- PROOF-3 (RULE-3): Read `.claude/agents/purlin-reviewer.md`; verify YAML frontmatter contains `name: purlin-reviewer`, a `description:` field, and a `model:` field
- PROOF-4 (RULE-4): Glob `.claude/agents/purlin-*.md`; verify exactly 3 files are found and all are in `.claude/agents/`
