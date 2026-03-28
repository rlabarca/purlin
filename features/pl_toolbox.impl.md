## Implementation Notes

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

**[IMPL]** Skill file (skills/toolbox/SKILL.md) defines all subcommands (list, run, create, edit, copy, delete, add, pull, push). Core Python infrastructure exists: scripts/toolbox/resolve.py (three-source resolution, fuzzy matching), scripts/toolbox/manage.py (CLI tool management). Unit tests in scripts/toolbox/test_toolbox.py.

**[IMPL]** All subcommand code paths now have backing implementations: `list` and `run` use resolve.py (agent calls resolve.py, formats output per skill file). `create`, `modify`, `delete` use manage.py with argparse CLI. `edit` and `copy` are agent-level JSON operations documented in skill file. `add`, `pull`, `push` use scripts/toolbox/community.py (17 tests). The skill file provides complete agent instructions for all subcommands, and the Python modules provide the data operations the agent invokes.
