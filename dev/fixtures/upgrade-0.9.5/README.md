# Upgrade fixture: the v0.9.5 layout

A project as Purlin v0.9.5 left it (tag `v0.9.5`): `.purlin/` with that release's config keys,
a committed cache directory, the plugin copies and a committed dashboard data file (a stub
here); the v0.9.5 Windows workflow under `.github/workflows/`; and a representative `specs/`
subset with the committed verification and proof JSON files beside each spec, including the
`proofs-windows` tier file and a spec carrying a `figma://` source.

`_gitignore` is the project's `.gitignore`; a test copies the fixture to a temporary directory
and renames it, so the fixture's own ignore rules never apply to this repository.

Frozen: `scripts/init/update.py` and `dev/test_init_update.py` read it and never change it.
