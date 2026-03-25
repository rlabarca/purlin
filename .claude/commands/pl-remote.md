**Purlin mode: shared**

Branch collaboration commands for multi-user workflows.

---

## Usage

```
/pl-remote push       — Push active branch to remote
/pl-remote pull       — Pull remote branch into current branch
/pl-remote add        — Configure a git remote for this project
```

## Subcommands

### push

Push the current branch to the configured remote. Safety checks:
- Verify remote exists
- Check for uncommitted changes (warn if dirty)
- Verify branch is not `main` (warn before pushing to main)
- `git push -u origin <branch>`

### pull

Pull the remote branch into the current local branch:
- `git fetch origin`
- `git merge origin/<branch> --no-edit`
- On conflict: present to user for resolution
- After merge, show what changed (categorized by file type)

### add

Configure a git remote:
- Prompt for remote URL
- `git remote add origin <url>` (or update if exists)
- Verify connection with `git ls-remote`
