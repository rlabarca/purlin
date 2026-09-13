# Legacy `features/` Migration

How `purlin:spec-from-code` reads a pre-Purlin `features/` directory and turns it into compliant
3-section specs. `skills/spec-from-code/SKILL.md` branches here rather than carrying a second copy
of the procedure.

Phase 1 step 3 of the skill looks for migration candidates in **two locations**: a legacy
`features/` directory at the project root, and non-compliant specs already under `specs/`, reached
by globbing `specs/**/*.md`. This file owns the first. The second stays in the skill, because its
non-compliance criteria are the compliance criteria the rest of the skill enforces.

## Phase 1: detection

If `features/` exists at the project root:

- Read all `.md` files recursively (excluding `.impl.md` and `.discoveries.md` companion files
  from the main spec list)
- For each spec, extract: feature name, category (subdirectory), description, scenarios
  (Given/When/Then blocks), and any behavioral constraints
- For each spec, check for companion files:
  - **`.impl.md`**: deviations table, architecture details, test quality audit data
  - **`.discoveries.md`**: bug entries (resolved and open), user testing observations, Figma and
    design references
- Note all companion files found: they are critical migration inputs in Phase 3

Candidates go into `.purlin/cache/sfc_existing.md` alongside the non-compliant `specs/` ones, and
are counted in the skill's summary line as the `X from features/` half.

## Phase 3: migrating one feature

**From `features/` (legacy format):**

- Read the original `features/<category>/<name>.md` file in full
- Extract scenarios (Given/When/Then), descriptions, and behavioral constraints
- Old scenarios become RULE-N candidates; old descriptions inform the `> Description:` metadata

**Read ALL companion files:**

- **`.impl.md` companion**: read in full. Extract:
  - **Active Deviations table**: each deviation where the spec says X but the implementation does
    Y becomes a rule reflecting the *actual* behavior. If the deviation was PM-ACCEPTED, use the
    implementation's behavior as the rule. If PENDING or REJECTED, flag it for the user in the
    review step as a discrepancy.
  - **Architecture details**: design patterns, caching strategies, concurrency models, data flow,
    and tradeoffs go into `## Implementation Notes`
  - **Test Quality Audit data**: note the last audit date and score in Implementation Notes for
    context
- **`.discoveries.md` companion**: read in full. Extract:
  - **Resolved bugs** (`[BUG]` entries with status RESOLVED): each becomes a RULE-N protecting
    against regression. For example `[BUG] M12: info bar overlaps disclaimer on mobile` becomes
    `RULE-N: Info bar does not overlap disclaimer on viewports below 768px`
  - **Open bugs**: each becomes a RULE-N tagged `(deferred)`. The bug description becomes the
    rule, and the observed-versus-expected detail goes into a comment or Implementation Notes.
  - **Figma and design references**: any URLs or references to visual designs become
    `> Visual-Reference:` metadata or `@manual` proof references
  - **User testing observations**: behavioral observations that are not bugs but document expected
    behavior become rule candidates

**Companion files are migration inputs, not rule factories.** Extract *behavioral* deviations and
bug regressions as rules. Architecture decisions go to `## Implementation Notes`. Stale bugs and
resolved cosmetic issues are not rules: they belong in git history.

The fidelity contract in Phase 3 step 3 of the skill applies to a legacy spec exactly as it does
to a non-compliant one: the old spec is the primary input, divergence from the current code is
flagged for the user, and the result is marked `<!-- Migrated by purlin:spec-from-code. Review and
refine. -->`.

## Phase 4: cleanup

If `features/` was detected and specs were migrated from it:

- Ask the user via `AskUserQuestion`: `Migration complete. Remove old features/ directory? The old
  specs have been migrated to specs/. [y/n]`
- If approved: delete `features/` and any companion files. Also delete old artifacts if present:
  `pl-*` symlinks, `*.sh` scripts at root.
- If declined: leave `features/` in place. Print: `Keeping features/: you can remove it manually
  when ready: rm -rf features/`
