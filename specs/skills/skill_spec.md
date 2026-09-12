# Feature: skill_spec

> Scope: skills/spec/SKILL.md
> Stack: markdown (skill definition)
> Description: The `purlin:spec` skill scaffolds or edits feature specs in 3-section format. It accepts any input — plain English, PRDs, customer feedback, code files, images — and extracts structured rules.

## Rules

- RULE-1: Skill file has YAML frontmatter with `name` and `description` fields
- RULE-2: Skill file contains a `## Usage` section documenting command syntax
- RULE-3: The `name` field in frontmatter is `spec`, matching the directory name
- RULE-4: Skill includes commit instructions or git operations for file modifications
- RULE-5: Update workflow (Step 7) presents a delta report showing KEEPING/ADDING/UPDATING/REMOVING before applying changes
- RULE-6: Skill includes mandatory tier tag review for proof descriptions
- RULE-7: Spec skill has exit criteria requiring the spec file is committed and no uncommitted spec files remain before the skill can complete
- RULE-8: Validate-Before-Commit includes an e2e proof-description check: `@e2e` proofs must describe an observable flow and must not name source files or internal functions, per `references/spec_quality_guide.md` ("E2E proof descriptions")
- RULE-9: The skill points at the Proof Design criteria (`references/audit_criteria.md` § Pass D) and states that editing spec prose moves the Design gauge only — HOLLOW and EXCLUDED are decided by test code
- RULE-10: Exit criteria require reporting the Proof Design score for the descriptions just written, via `--check-proof-design` (which needs no test code), as advisory output that never blocks the commit; and require printing the next-step directive for the state the spec is now in — fix UNPROVABLE descriptions, `purlin:build` when the `> Scope:` files do not exist, or `purlin:test` when code exists without proofs
- RULE-11: `skills/spec/SKILL.md` Step 5 makes assumption tagging mandatory: after extracting rules the agent reviews each one, and any rule carrying a specific number, threshold, algorithm or constraint the user did not explicitly state is tagged `(assumed — user said "<wording>")` quoting the user's own words, while a rule whose value the user did state carries no tag
- RULE-12: `skills/spec/SKILL.md` Step 1 accepts customer feedback or a feature request as input without asking which format it is, and Step 5's rule-extraction table translates each complaint into a testable `RULE-N` constraint carrying a specific threshold or behaviour: a speed complaint becomes a boundary condition with a numeric bound, a prohibition becomes a FORBIDDEN pattern, so no complaint is left as prose

## Proof

- PROOF-1 (RULE-1): Grep `skills/spec/SKILL.md` for YAML frontmatter delimiters (`---`); verify `name:` and `description:` fields exist
- PROOF-2 (RULE-2): Grep `skills/spec/SKILL.md` for `## Usage`; verify the section exists
- PROOF-3 (RULE-3): Extract `name:` from frontmatter; verify it equals `spec`
- PROOF-4 (RULE-4): Grep `skills/spec/SKILL.md` for commit instructions (`git commit`, `commit the`, `create.*commit`); verify present
- PROOF-5 (RULE-5): Grep `skills/spec/SKILL.md` for `KEEPING`, `ADDING`, `UPDATING`, and `REMOVING`; verify the delta report structure is present
- PROOF-6 (RULE-6): Grep `skills/spec/SKILL.md` for tier review instructions and tier tag references (`@integration`/`@e2e`/unit tier); verify present
- PROOF-7 (RULE-7): Grep `skills/spec/SKILL.md` for "Exit Criteria" section; verify it requires spec committed and no uncommitted spec files
- PROOF-8 (RULE-7): Run `claude -p` with `purlin:spec auth_login` in two temp git projects. Accepted leg: `git ls-files --error-unmatch specs/auth_login.md` exits 0, `git status --porcelain specs/` prints exactly the empty string, and the subject read by `git log -1 --format=%s -- specs/auth_login.md` starts with `spec(auth_login):`. Rejection leg: in a project whose `.git/hooks/pre-commit` rejects every staged path under `specs/` and whose prompt forbids bypassing it, the session must name the blocked commit (one of `pre-commit`, `hook`, `blocked`, `could not commit`, `commit failed`, `not committed`) and must not claim all four exit criteria were met, while `git cat-file -e HEAD:specs/auth_login.md` exits non-zero (the spec never reaches HEAD, though the blocked commit leaves it staged) and `git status --porcelain specs/` still lists `specs/auth_login.md` @e2e @on(claude-cli)
- PROOF-9 (RULE-8): Grep `skills/spec/SKILL.md` Validate-Before-Commit for the `@e2e` observable-flow check and its pointer to `spec_quality_guide.md` "E2E proof descriptions"; verify present
- PROOF-10 (RULE-9): Grep `skills/spec/SKILL.md` for the pointer to `audit_criteria.md`; verify it names the Design levels or Pass D and states that spec edits do not move HOLLOW or EXCLUDED
- PROOF-11 (RULE-10): Grep `skills/spec/SKILL.md` Exit Criteria; verify they invoke `--check-proof-design`, state the report is advisory, and enumerate the three next-step directives including `purlin:build` and `purlin:test`
- PROOF-12 (RULE-11): Grep `skills/spec/SKILL.md` Step 5 and assert the paragraph headed `**Assumption tagging (mandatory):**` orders every extracted rule reviewed, and that its three worked examples spell the tag with its context in full as `(assumed — user said "fast")`, `(assumed — user said "secure")` and `(assumed — user said "handles errors")`, while the two explicit-value counterexamples read `RULE-3: Under 200ms` and `RULE-4: argon2 hashing` with no `(assumed` anywhere on those lines, so only an inferred value draws the tag
- PROOF-13 (RULE-12): Grep `skills/spec/SKILL.md` and assert Step 1's input list carries the line `- Customer feedback or feature request` under `Accept ANY of these input types`, and that Step 5's extraction table maps the signal row `"fast", "under N seconds", "real-time"` to the rule type `Boundary condition` with the example rule `RULE: API response time under 200ms at p95`, and the signal row `"never", "don't", "cannot", "forbidden"` to the rule type `FORBIDDEN pattern`, so a complaint is translated into a rule carrying a number or a named prohibition
