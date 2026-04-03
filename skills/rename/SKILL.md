---
name: rename
description: Rename a feature across specs, proofs, markers, and references
---

Rename a feature across all Purlin artifacts in one atomic operation.

## Usage

```
purlin:rename <old-name> <new-name>    Rename a feature
```

---

## What It Renames

1. **Spec file**: `specs/**/<old-name>.md` → `specs/**/<new-name>.md`
2. **Proof files**: `<old-name>.proofs-*.json` → `<new-name>.proofs-*.json` (same directory)
3. **Receipt files**: `<old-name>.receipt.json` → `<new-name>.receipt.json` (if exists)
4. **Proof markers in test code**: grep all test files for proof markers referencing the old name and replace:
   - Python: `@pytest.mark.proof("old-name",` → `@pytest.mark.proof("new-name",`
   - Jest: `[proof:old-name:` → `[proof:new-name:`
   - Shell: `purlin_proof "old-name"` → `purlin_proof "new-name"`
5. **Feature name inside spec file**: `# Feature: old_name` → `# Feature: new_name`
6. **`> Requires:` references in other specs**: grep all `specs/**/*.md` for `> Requires:` lines containing the old name, replace with new name
7. **Proof file entries**: inside the renamed proof JSON, update the `"feature"` field in each entry from old name to new name

---

## Steps

### Step 1 — Find the Spec

Search `specs/**/<old-name>.md`.

- **Not found:** Stop with: `No spec found for '<old-name>'. Check the name with purlin:find.`
- **Invariant (`i_*`):** Stop with: `Cannot rename invariant '<old-name>'. Invariants are read-only and synced from an external source. Rename at the source and run purlin:invariant sync.`
- **Multiple matches:** List them and use `AskUserQuestion` to ask the user which one.
- **Found:** Continue.

### Step 2 — Show What Will Change

Scan for all artifacts that reference the old name and present a summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ RENAME: <old-name> → <new-name>

Files to rename:
  specs/auth/login.md → specs/auth/authentication.md
  specs/auth/login.proofs-default.json → specs/auth/authentication.proofs-default.json

Proof markers to update:
  tests/test_login.py: 5 markers
  tests/test_auth_integration.py: 2 markers

Specs referencing this feature (> Requires:):
  specs/auth/session.md
  specs/auth/password_reset.md

[y] Proceed  [n] Cancel

Waiting for your response...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 3 — Wait for Approval

Use `AskUserQuestion` to pause and wait. Do NOT auto-proceed.

### Step 4 — Execute Rename (if approved)

Perform all changes in this order:

**a. Rename files** — use `git mv` for spec, proof, and receipt files:
```bash
git mv specs/auth/login.md specs/auth/authentication.md
git mv specs/auth/login.proofs-default.json specs/auth/authentication.proofs-default.json
git mv specs/auth/login.receipt.json specs/auth/authentication.receipt.json  # if exists
```

**b. Update proof markers in test files** — search and replace marker strings only:
- Python: `@pytest.mark.proof("old-name",` → `@pytest.mark.proof("new-name",`
- Jest: `[proof:old-name:` → `[proof:new-name:`
- Shell: `purlin_proof "old-name"` → `purlin_proof "new-name"`

**c. Update feature name inside the spec file:**
- `# Feature: old_name` → `# Feature: new_name`

**d. Update `> Requires:` in other specs:**
- Replace the old name with the new name in `> Requires:` lines across all `specs/**/*.md`
- Use word-boundary matching to avoid partial replacements (e.g., renaming `login` must not corrupt `login_oauth` → `newname_oauth`). Match on the exact comma-separated entry.

**e. Rename screenshot files** (if the spec has `> Visual-Reference:`):
- Rename `specs/<category>/screenshots/<old-name>.png` → `specs/<category>/screenshots/<new-name>.png` (using `git mv`)
- Update the `> Visual-Reference:` path inside the spec file

**f. Update `"feature"` field in proof JSON entries:**
- Inside each renamed proof file, replace `"feature": "old-name"` with `"feature": "new-name"`

**g. Run `sync_status`** to verify everything still resolves.

**h. Commit:**
```
git commit -m "rename(<old-name>): rename to <new-name>"
```

### Step 5 — Verify

If `sync_status` shows issues after rename, warn the user and show the directives. Do not silently ignore resolution failures.

---

## Edge Cases

- **Old name has underscores, new name has hyphens (or vice versa)**: handle both. The rename is exact string replacement — no normalization.
- **Old name appears in test function names**: do NOT rename test functions — only rename proof marker strings. `test_login_valid()` stays as-is; only `proof("login",` changes.
- **Old name appears in code comments or docs**: do NOT rename. Only rename in Purlin artifacts (specs, proofs, markers, `> Requires:`).
- **Multiple specs match**: if `specs/**/login.md` matches multiple files, list them and ask the user which one.
- **Invariant specs (`i_*`)**: refuse to rename — invariants are read-only and managed by `purlin:invariant sync`. The rename must happen at the external source.
- **`> Requires:` partial matches**: use word-boundary matching when replacing in `> Requires:` lines. The old name must match as a complete comma-separated entry, not as a substring of another name.
