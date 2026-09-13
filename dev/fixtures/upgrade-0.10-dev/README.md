# Upgrade fixture: the 0.10 development layout

A project as the unreleased 0.10 development branch left it (commit 539b9145): `.purlin/` with
the config keys of that branch, the two hook shims, the plugin copies and a committed dashboard
data file (a stub here); `.github/workflows/` with the two workflows of that branch; and a
representative `specs/` subset with the committed verification and proof JSON files beside each
spec, including one spec carrying a `figma://` source and one carrying OS-scoped proof files.

`_gitignore` is the project's `.gitignore`; a test copies the fixture to a temporary directory
and renames it, so the fixture's own ignore rules never apply to this repository.

Frozen: `scripts/init/update.py` and `dev/test_init_update.py` read it and never change it.
