# Startup State-Gathering Sequence

> **Reference file.** Shared state-gathering steps used by all role startup protocols and `/pl-resume`.
> Stub locations: ARCHITECT_BASE.md Section 5.1, BUILDER_BASE.md Section 2.1, QA_BASE.md Section 3.1, PM_BASE.md Section 7.1.
> Also referenced by: features/pl_session_resume.md Section 2.3.5.

## Core Sequence (Architect | Builder | QA)

These steps run on every session start -- full startup, pl-resume cold start, and pl-resume warm resume. **PM skips this section entirely** (PM does not run Critic analysis).

1. Read `.purlin/config.json` for role-specific settings.
2. Run `tools/cdd/status.sh` to regenerate the Critic report and get feature status. Do NOT re-parse the raw JSON -- use `CRITIC_REPORT.md` as the sole source for action items.
3. Read `CRITIC_REPORT.md` -- the role-specific subsection under **Action Items by Role**.
4. Check `git status` for uncommitted changes.
5. Check `git log --oneline -10` for recent commit history.

## Cold-Start Extensions

These steps run during a **full startup** OR a **pl-resume cold start** (no checkpoint). They are **skipped** during pl-resume warm resume (checkpoint exists provides equivalent context).

### All Roles (Architect | Builder | QA)

- Read `.purlin/cache/dependency_graph.json` for the feature graph and dependency state. If stale or missing, run `tools/cdd/status.sh --graph` to regenerate.

### Builder

1. **Delivery Plan + Scoped Spec Reads:** Read `.purlin/cache/delivery_plan.md` if it exists. Identify the current phase (first PENDING or IN_PROGRESS) and check for QA bugs from prior phases. If a delivery plan exists, scope feature spec reads to the current phase only. If no delivery plan exists, read specs for all features in TODO or TESTING state.
2. **Spec-Level Gap Analysis:** For each in-scope feature, read the full feature spec (`features/<name>.md`). Compare Requirements and Automated Scenarios against the current implementation code. Identify requirements, scenarios, or schema changes with no corresponding implementation. The Critic's traceability engine uses keyword matching which can produce false positives; the specs are the source of truth.
3. **Tombstone Check:** List `features/tombstones/`. For each tombstone file, read it and add to the work plan as a HIGH-priority task labeled `[TOMBSTONE] Retire <feature_name>: delete specified code`. Tombstones are processed before new feature implementation.
4. **Anchor Preload (MANDATORY):** Read ALL anchor node files in `features/` (`arch_*.md`, `design_*.md`, `policy_*.md`). Identify every FORBIDDEN pattern and INVARIANT from each anchor. Keep them active in working context for the entire session. Anchors are loaded once at session start, not re-read per feature.

### QA

1. **Verification Effort:** For each TESTING feature, read `verification_effort` and `regression_scope` from `tests/<feature_name>/critic.json`. Classify items as auto-resolvable (web-verify, test-only, cosmetic-skip) vs. human-required. Include scope mode for non-full scopes (targeted, cosmetic, dependency-only).
2. **Delivery Plan Classification:** If `.purlin/cache/delivery_plan.md` exists, read it and classify each TESTING feature as fully delivered (eligible for `[Complete]`) or more work coming (not eligible). Present phase context.
3. **Discovery Review:** Check for SPEC_UPDATED discoveries awaiting re-verification and OPEN discoveries.

### Architect

1. **Spec-Level Gap Analysis:** For each feature in TODO or TESTING state, read the full feature spec. Assess completeness, well-formedness, prerequisite link integrity, and consistency with architectural policies. Identify gaps the Critic may have missed -- incomplete scenarios, missing prerequisite links, stale implementation notes, spec sections conflicting with recent architectural changes.
2. **Untracked File Triage:** Check `git status` output for untracked files. For each, determine the appropriate action (gitignore or commit) per Architect responsibility 12. Builder-owned files require no action.

### PM

1. **Figma MCP Availability Check:** Check for Figma MCP tools in the current session. If not available, inform the user and provide setup instructions.
2. The PM does not perform Critic analysis or feature-level state gathering. After the Figma check, the PM awaits human direction.
