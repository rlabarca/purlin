# Discovery Sidecar: release_step_management

## M52: manage_step.py has zero unit tests

- **Status:** RESOLVED
- **Action Required:** Engineer
- **Severity:** HIGH
- **Description:** manage_step.py CLI tool had no unit tests covering internal helper functions, CLI argument parsing, or edge cases beyond the 11 spec scenarios.
- **Resolution:** Added comprehensive unit test file at `tests/release_step_management/test_manage_step_unit.py` with 59 assertions across 31 test functions covering: internal helpers (`_load_json_safe`, `_load_steps`, `_find_step_index`), CLI argument parsing (no subcommand, missing required args, invalid subcommand), and edge cases (create with all optional fields, preserving existing steps, modify multiple fields, modify each field individually, clear agent-instructions, mutual exclusion of agent-instructions flags, delete preserving other steps, dry-run for all subcommands, empty field validation, output message format, step order preservation, parent directory creation).
