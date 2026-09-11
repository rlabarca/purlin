# Feature: skill_test

> Scope: skills/test/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:test` skill runs tests (unit tier unless `--all`), emits proof files via write-scoped overwrite, and reports coverage per feature. It is the single owner of test execution: `purlin:build` and `purlin:verify` delegate to it rather than invoking runners themselves. That ownership is also why remote execution of runner-gated tiers lives here: pushing a branch and pulling a runner's proof commits is writing, and `purlin:verify` is a read-only gate.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `test`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: Skill requires calling `sync_status` after tests and states it is not optional
- RULE-6: The freshness check distinguishes "no tests were collected" from "the proof plugin failed to emit". Zero collected tests reports that the plugin is fine and routes to `purlin:build`; only a run that executed tests without refreshing proof files reports a plugin problem and suggests `purlin:init --force`
- RULE-7: Step 1.5 classifies the tiers in scope as locally-runnable or runner-gated and reports the split **before the first test runs**, naming what cannot execute on this host. It forbids substituting a local approximation for a runner-gated proof, and states that an absent runner warns rather than blocks. Reporting the gap up front is the point: a run that silently skipped a platform and then reported PASSING is the defect this step exists to prevent
- RULE-8: Remote execution of runner-gated tiers is documented as a step of this skill and nowhere else, as four ordered operations: push the current branch, dispatch the workflow for that tier, await the run, and pull the proof commits it pushed back. The reason it lives here rather than in `purlin:verify` is stated, not implied: those operations write, and verify's contract forbids writing
- RULE-9: Step 3 reports a remotely-proved tier distinctly from a locally-proved one, and sources the runner identity and time from the proof commit's `Purlin-Runner:` trailer rather than from the proof entry, because the entry records that a test passed and only the commit records where. The freshness check is confined to locally-runnable tiers, since a pulled proof file's mtime says when it was fetched
- RULE-10: The remote loop is bounded at 3 rounds, matching `skills/audit/SKILL.md` and `skills/verify/SKILL.md`, and the bound is stated as a number rather than as "a few". A fourth round spends another CI run on a failure that is not converging
- RULE-11: Remote setup is offered on discovery and never at init: when runner-gated proofs exist and no workflow proves that tier, the skill offers to scaffold one from `references/remote_verification.md` and writes nothing without consent. `purlin:init` is not the place, because a project with no runner-gated proofs has no runner to configure

## Proof

- PROOF-1 (RULE-1): Grep `skills/test/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/test/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `test`
- PROOF-4 (RULE-4): Grep `skills/test/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/test/SKILL.md` for `sync_status` and `not optional`; verify both present
- PROOF-6 (RULE-6): Grep `skills/test/SKILL.md` for the freshness check; verify the zero-tests branch states the plugin is fine and routes to `purlin:build`, and that the `purlin:init --force` suggestion appears only in the branch where tests actually ran
- PROOF-7 (RULE-7): Grep `skills/test/SKILL.md` for the tier-classification step; verify it appears before the step that runs tests, that it names both `locally-runnable` and `runner-gated`, that it names `windows` as the runner-gated tier and cites the closed tier set that defines it, that it forbids substituting a local approximation, and that it says an absent runner does not block
- PROOF-8 (RULE-8): Grep `skills/test/SKILL.md` for the remote path; verify all four operations appear in order (push the branch, dispatch the workflow, await the run, pull the returned proof commits), and that the section states why the path lives in this skill rather than in `purlin:verify`, naming verify's read-only contract. Grep `skills/verify/SKILL.md` and confirm it gains no push, dispatch or pull instruction of its own
- PROOF-9 (RULE-9): Grep `skills/test/SKILL.md` Step 3 for the reporting distinction; verify the sample output marks a remotely-proved tier separately from a locally-proved one, that the runner identity is sourced from the `Purlin-Runner:` commit trailer and explicitly not from the proof entry, and that the freshness check states it does not apply to a pulled runner-gated proof file
- PROOF-10 (RULE-10): Grep `skills/test/SKILL.md` for the remote loop bound; verify the literal round count is 3 and that it matches the count in `skills/audit/SKILL.md` and `skills/verify/SKILL.md`, so the three skills cannot drift to different bounds
- PROOF-11 (RULE-11): Grep `skills/test/SKILL.md` for the setup offer; verify it is conditioned on discovering runner-gated proofs with no workflow, that it points at `references/remote_verification.md` for the template, that it requires consent before writing a workflow file, and that it states init is not where this happens. Grep `skills/init/SKILL.md` and confirm it contains no remote-verification setup step
