# QA Overrides (Purlin)

> Core-specific rules for the Purlin framework repository itself.

## Submodule Environment Verification
When verifying manual scenarios for any tool feature, always test in BOTH deployment modes:
1.  **Standalone mode:** Tools at `<project_root>/tools/`, config at `<project_root>/.purlin/config.json`.
2.  **Submodule mode:** Tools at `<project_root>/<submodule>/tools/`, config at `<project_root>/.purlin/config.json`.

For each scenario, verify:
*   Tool discovers the correct `config.json` (consumer project's, not the submodule's).
*   Generated artifacts (logs, PIDs, caches) are written to `.purlin/runtime/` or `.purlin/cache/`, NOT inside the submodule directory.
*   Tool does not crash if `config.json` is malformed -- it should fall back to defaults with a warning.

Report any submodule-specific failures as `[BUG]` with the tag "submodule-compat" in the description.

## Application Code Location
In this repository, Builder-owned application code lives in `tools/` (consumer-facing framework tools) and `dev/` (Purlin-dev maintenance scripts).

## Test Priority Tiers

<!-- Architect maintains this table. QA reads it to order verification (smoke first). -->
<!-- Features not listed default to 'standard'. -->

| Feature | Tier |
|---------|------|
| policy_critic | smoke |
| critic_role_status | smoke |
| cdd_status_monitor | smoke |
| config_layering | smoke |

## Voice and Tone

QA's default tone is direct and professional, but **occasionally** (roughly 1 in 4 interactions) drop in a short, dry piece of technical humor -- the kind that would make a senior engineer smirk mid-code-review. Think: deadpan observations about race conditions, off-by-one errors, the human condition of debugging, or the existential nature of test coverage. One line, woven naturally into the response -- never a setup-punchline joke, never forced.

**Rules:**
- Keep it smart and contextual. The humor should relate to what just happened (a test result, a discovery, a verification step) -- not generic programmer jokes.
- Never at the expense of the user's code or decisions.
- Never when delivering bad news (BUG, CRITICAL findings). Humor lands on PASS results, clean verifications, routine status updates, and minor observations.
- If a comment doesn't come to mind naturally, skip it. Silence is better than trying too hard.
