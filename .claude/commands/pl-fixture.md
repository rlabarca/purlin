**Purlin command: shared (all roles)**

---

The test fixture system provides deterministic, reproducible project state for automated
testing. Fixture states are immutable git tags in a dedicated bare repo. See
`features/test_fixture_repo.md` for the full specification.

## For Architects: Fixture-Aware Feature Design

### When to Use Fixtures

Use fixtures for scenarios needing:
- Specific git state (branch topologies, commit histories, ahead/behind counts)
- Specific config values or file system layouts
- Worktree configurations
- Specific database state
- Any precondition that is fragile to construct at test time or non-deterministic to reproduce

### When NOT to Use Fixtures

Do not use fixtures when the scenario's verification requires human judgment (visual
aesthetics, subjective UX quality), real hardware interaction, or real-time external service
state. A fixture adds infrastructure without adding testability in these cases. Keep those
scenarios manual (`@manual-interactive` / `@manual-visual`). Fixtures are for scenarios where
a machine can check the Given/When/Then chain end-to-end.

### How to Write Fixture Tag Sections

Add a `### 2.x Integration Test Fixture Tags` or `### 2.x Web Test Fixture Tags` heading
in the Requirements section. Include a table with Tag and State Description columns:

    | Tag | State Description |
    |-----|-------------------|
    | `main/feature_name/slug` | Description of the project state |

See `instructions/references/feature_format.md` "Fixture Tag Section Format" for the full
format reference.

### Slug Convention

Tag format: `<project-ref>/<feature-name>/<slug>`. Slugs are Architect-chosen, short
descriptive identifiers (2-4 words, kebab-case). They describe the fixture state, not the
scenario title. Examples: `ahead-3`, `empty-repo`, `expert-mode`.

### User Communication Mandate

When adding fixtures to a feature for the first time, explain to the user what they are and
why: "These scenarios need controlled project state. I am adding fixture tags -- immutable
snapshots that tests check out automatically. The Builder will create a setup script to
generate them."

## For Builders: Fixture Setup Workflow

### Fixture Detection (Pre-Flight)

Check whether the feature spec contains a fixture tag section (a heading matching
`### 2.x ... Fixture Tags`).

1. If yes: resolve the fixture repo via the three-tier lookup:
   - Per-feature `> Test Fixtures:` metadata
   - Project-level `fixture_repo_url` in `.purlin/config.json`
   - Convention path `.purlin/runtime/fixture-repo`
2. If no fixture repo exists at any tier: check for a setup script.
   - **Purlin framework repo:** `dev/setup_fixture_repo.sh`
   - **Consumer projects:** Check companion file (`features/<name>.impl.md`) or
     `BUILDER_OVERRIDES.md` for the setup script location.
   - Run the setup script if found. If not found, create one (see below).
3. Verify all declared fixture tags exist by running `fixture list` against the resolved repo.

### Creating a Setup Script

When no setup script exists:

1. Use `fixture init` to create the bare repo at the convention path.
2. For each declared tag: construct the required project state in a temp directory, then run
   `fixture add-tag <tag> --from-dir <tmpdir> --message "<state description>"`.
3. Save the script at the project-appropriate location:
   - **Purlin:** `dev/setup_fixture_repo.sh` (not distributed to consumers)
   - **Consumer:** Builder's choice, documented in companion file

### State Construction Guidance

Start with a minimal valid project structure (config files, basic features directory), then
layer the specific state the scenario requires. Each tag's temp directory should contain only
the files needed for that scenario's Given preconditions.

## For QA: Fixture Awareness

If the Critic report for a feature includes a `fixture_repo_unavailable` finding, inform the
user that the fixture infrastructure has not been created yet. Web-verify and automated test
results for fixture-backed scenarios will be INCONCLUSIVE until the Builder creates the
fixture repo. This is Builder-routable, not a QA failure -- do not record as a discovery.
