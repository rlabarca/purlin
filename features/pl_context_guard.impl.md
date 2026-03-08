# Implementation Notes: Skill -- Context Guard

**[DECISION]** Simplified from threshold-setting skill (status/set/on/off with 5-200 range validation) to toggle-only skill (status/on/off). The `set <threshold>` subcommand and all threshold validation logic are removed. The context guard is now binary (on/off) with no configurable threshold -- auto-compaction interception replaces turn counting. The `context_guard_threshold` config key is no longer read or written by this skill.
