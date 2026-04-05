# Feature: purlin_version

> Scope: VERSION, templates/config.json, scripts/mcp/purlin_server.py
> Description: Ensures the Purlin version string is defined in exactly one place (the VERSION file) and all references to it read from that file or match its value. Prevents version drift when releasing new versions.

## Rules

- RULE-1: A VERSION file exists at the project root containing a single semver string
- RULE-2: purlin_server.py reads the version from the VERSION file via _read_version(), not a hardcoded string
- RULE-3: templates/config.json version field matches the VERSION file
- RULE-4: No hardcoded version strings in purlin_server.py (no literal "0.9.0" or similar version patterns)

## Proof

- PROOF-1 (RULE-1): Read VERSION file; verify it exists and contains a valid semver string (X.Y.Z)
- PROOF-2 (RULE-2): Grep purlin_server.py for _read_version; verify it's called to set PURLIN_VERSION; verify SERVER_INFO uses PURLIN_VERSION
- PROOF-3 (RULE-3): Read VERSION file and templates/config.json; verify the version field in the template matches the VERSION file content
- PROOF-4 (RULE-4): Grep purlin_server.py for hardcoded version patterns like "0.9.0" or "0.10.0"; verify zero matches outside of comments
