# Implementation Notes: Agent Config Skill

*   **Target File:** The skill writes to `.purlin/config.local.json` (gitignored), not `config.json` (committed). This follows the config layering convention -- local overrides are never committed.
*   **Key Validation:** The skill validates key names against the known schema before writing. Supported keys per role: `model`, `effort`, `bypass_permissions`, `find_work`, `auto_start`. The `qa_mode` key is Builder-only (`agents.builder.qa_mode`).
*   **No Commit Step:** Unlike earlier versions that targeted `config.json`, the skill does not run `git commit` after writing. The local config file is gitignored by design.
