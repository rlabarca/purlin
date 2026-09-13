# Feature: purlin_teammate_definitions

> Scope: agents/purlin-auditor.md
> Stack: markdown (agent definitions)
> Description: Defines the independent auditor agent role used by the Purlin verify-audit loop. The definition lives in the plugin's `agents/` directory so it ships to consumer projects and resolves as a namespaced agent type (`purlin:purlin-auditor`). A definition under `.claude/agents/` would be project-local to this repository and unavailable to any project that installs Purlin as a plugin: which is why the former `purlin-builder` and `purlin-reviewer` definitions were retired rather than relocated: neither was ever invoked.

## Rules

- RULE-1: `agents/purlin-auditor.md` exists with YAML frontmatter containing `name: purlin-auditor` and `description` and **no** `model` field, and the body states that the auditor's independence is a fresh context rather than a different model. Pinning the auditor to a model is how a reader concludes the independence claim rests on cross-model disagreement; it rests on the auditor not having written the tests it grades. The host chooses the model for both shipped agents
- RULE-4: The agent definition is located in the plugin's `agents/` directory, not `.claude/agents/`, so it ships with the plugin. No `purlin-*.md` agent definitions remain under `.claude/agents/`
- RULE-5: The auditor definition does not instruct spawning any other agent to remediate findings: the audit is read-only, and remediation is routed to `purlin:build`
- RULE-6: The auditor definition states that the auditor writes its own assessments through `static_checks.py --write-cache`, never to `.purlin/cache/audit_cache.json` directly, and says why: the flag holds an exclusive lock around its read/merge/write cycle, which is what lets several auditors run at once, and it re-keys and stamps every entry. The definition and `skills/audit/SKILL.md` agree on this division; they previously contradicted each other, with the skill forbidding subagent writes and the definition requiring them, so one of the two was wrong on every run

## Proof

- PROOF-1 (RULE-1): Read `agents/purlin-auditor.md`; verify its YAML frontmatter contains `name: purlin-auditor` and a `description:` key and declares no `model:` key, and that the body carries a sentence saying independence is a fresh context and not a different model. Restoring `model: claude-sonnet-4-6` to the frontmatter fails the proof naming that key
- PROOF-4 (RULE-4): Glob `agents/purlin-*.md`; verify `agents/purlin-auditor.md` is found. Glob `.claude/agents/purlin-*.md`; verify zero matches
- PROOF-5 (RULE-5): Read `agents/purlin-auditor.md`; verify it contains none of the four literals a delegation would be written with, `purlin-builder`, `spawn` (case-insensitive), `Task(` and `subagent_type`, and that it does contain `purlin:build`, the route remediation takes instead
- PROOF-6 (RULE-6): Grep `agents/purlin-auditor.md` and verify it names `--write-cache`, forbids writing `.purlin/cache/audit_cache.json` directly, and gives the exclusive lock as the reason. Grep `skills/audit/SKILL.md` for the same division and verify it contains no sentence forbidding a subagent from writing the cache, and that it states the lead reads the cache back to verify the entries landed. Asserting on both files is the point: either file alone can be made to read correctly while the pair still disagrees
