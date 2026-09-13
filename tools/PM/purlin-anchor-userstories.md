---
name: purlin-anchor-userstories
description: >
  Create, edit, and maintain Purlin anchor specs: structured user-story specifications
  used to drive AI-assisted software development with the Purlin plugin.
  Use this skill whenever the user wants to: write or update user stories for a software
  project, create or edit a Purlin anchor spec, manage spec files in a git repo, define
  testable workflows or acceptance criteria for a product, or any time the user mentions
  "anchor spec", "Purlin", "user stories for a spec", or "spec-driven development".
  This skill runs in Claude Code mode and requires git access.
---

# Purlin Anchor Skill

This skill helps users create and maintain **Purlin anchor specs**: Markdown specification
files that capture testable user workflows (rules plus proofs) used to drive AI-assisted
software development. An anchor spec lives in the project's own git repo and is read by
the Purlin plugin.

---

## Two Repos: Always Keep These Separate

This skill always works with **two distinct git repositories** that serve completely
different purposes. Never confuse them or use the wrong URL for the wrong purpose:

| | Repo | Purpose | Cloned to |
|---|---|---|---|
| 1 | **Purlin plugin repo** | Holds the Purlin plugin and its reference docs (`anchor_format.md`, `spec_quality_guide.md`, `audit_criteria.md`). Fetched for reading, and not locally editable by this skill. | `/tmp/purlin-refs` |
| 2 | **Project repo** | The user's project repo, where the anchor spec lives under `specs/_anchors/` and is committed. This is what gets pushed. | A working directory chosen at runtime |

The Purlin plugin repo URL is a **tool or environment setting**: it changes rarely and can be
saved to an env var. The project repo URL is **project-specific**, so the user provides it
per session.

---

## Step 0: Locate the Purlin Plugin Repo and Fetch Reference Docs

**Do this every time the skill is invoked.**

### 0a. Determine the Purlin plugin repo URL

Check whether a `PURLIN_REPO` environment variable is set:

```bash
echo $PURLIN_REPO
```

If it is set and non-empty, use that value as the Purlin plugin repo URL.

If it is **not** set, ask the user:
> "What is the URL of your Purlin plugin repository? (This is the repo containing the Purlin
> plugin and its reference docs, not the project repo your anchor spec lives in.)"

Once you have the URL, offer to save it for future sessions:
> "Would you like me to set `PURLIN_REPO` in your shell profile so you don't need to
> provide this again?"

If yes:
```bash
echo 'export PURLIN_REPO="<URL>"' >> ~/.bashrc   # or ~/.zshrc if zsh
source ~/.bashrc
```

### 0b. Fetch the reference docs

Always fetch the latest versions via git before doing any work. Do not rely on cached
or memorized versions: these docs are version-tracked and may change.

```bash
# Sparse-clone only the references/ folder from the Purlin plugin repo
git clone \
  --depth 1 \
  --filter=blob:none \
  --sparse \
  <PURLIN_REPO_URL> \
  /tmp/purlin-refs

cd /tmp/purlin-refs
git sparse-checkout set references
```

Then read all three files:

```bash
cat references/formats/anchor_format.md
cat references/spec_quality_guide.md
cat references/audit_criteria.md
```

Note the **version number** at the top of `anchor_format.md`. All work in this session
must conform to that version.

> **Scope constraint**: The Purlin reference docs describe multiple anchor types.
> This skill is **exclusively** for **user story anchor specs**: testable workflows that
> represent what a real user must be able to do for the software to be considered
> successful. Do not suggest, create, or reference any other anchor type, even if the
> reference docs describe them. If the user asks about other anchor types, acknowledge
> they exist but redirect: "This skill focuses on user story anchor specs. For other anchor
> types, consult the Purlin docs directly."

If the clone fails due to authentication (same diagnosis flow as Step 2), ask the user
for credentials and apply the same credential-store resolution before retrying.
If the Purlin plugin repo is temporarily unavailable, ask the user to paste the reference docs
directly into the conversation as a fallback, but always prefer the git-fetched version.

---

## Step 1: Determine Mode

Ask the user what they want to do:

1. **Create**: a new anchor spec in a project repo
2. **Edit**: an existing anchor spec in a project repo

Then collect the **project repo URL**. This is the user's project repo, not the
Purlin plugin repo. Clone it to a local working directory if not already present.

Also collect:
- **Anchor name**: a snake_case token such as `playlist_app`, which becomes the file
  `specs/_anchors/playlist_app.md`. Ask if creating; list the existing
  `specs/_anchors/*.md` files if editing
- For **Create only**: the spec **description** (what software or product this spec is for)
  and any other metadata the format requires that cannot be auto-generated

---

## Step 2: Set Up the Project Repo

This step operates on the **project repo**, not the Purlin plugin repo.

### 2a. Ensure git is installed

```bash
git --version 2>/dev/null || (apt-get install -y git && echo "Git installed.")
```

### 2b. Configure git identity (required for commits)

```bash
git config --global user.email 2>/dev/null || git config --global user.email "purlin-anchor@local"
git config --global user.name  2>/dev/null || git config --global user.name  "Purlin Anchor Skill"
```

If the user has a preferred git identity, ask and set it.

### 2c. Clone or update the repo

```bash
git clone <REPO_URL> <local-dir> 2>&1
```

**If clone fails**, do not give up. Work through auth:

#### Diagnosing auth failures

Run `git clone <URL>` and capture stderr. Common failure patterns:

| Error message | Likely cause |
|---|---|
| `Authentication failed` / `could not read Username` | HTTPS with no credentials stored |
| `Permission denied (publickey)` | SSH key not set up |
| `Repository not found` | Wrong URL, or no read access |

#### Auth option A: HTTPS with a Personal Access Token (PAT)

Best for GitHub, Bitbucket, GitLab over HTTPS.

1. Ask the user to generate a PAT:
   - **GitHub**: Settings → Developer settings → Personal access tokens → Fine-grained or Classic → `repo` scope
   - **Bitbucket**: Personal settings → App passwords → `Repositories: Read & Write`
   - **GitLab**: User settings → Access Tokens → `read_repository` plus `write_repository`
2. Hand the token to a credential store, never to the URL. A URL carrying a username and a
   secret before the `@` is written into shell history, into the clone's own config file,
   and into the process table where any other account on the machine can read it:
   ```bash
   gh auth login                                      # GitHub: stores it in the gh keyring
   git config --global credential.helper osxkeychain  # any host, macOS
   # git config --global credential.helper libsecret  # any host, Linux
   ```
3. Retry the clone unchanged. On GitHub, `gh repo clone <org>/<repo> <local-dir>` takes the
   credential from the `gh` keyring. On any other host the first clone prompts once for the
   username and the PAT, and the helper remembers both.

#### Auth option B: SSH key

Best if the user prefers SSH or already has keys.

```bash
# Check for existing keys
ls ~/.ssh/id_*.pub 2>/dev/null || echo "No SSH keys found."

# Generate a new key if needed
ssh-keygen -t ed25519 -C "purlin-anchor" -f ~/.ssh/id_ed25519 -N ""

# Print the public key for the user to add to their git host
cat ~/.ssh/id_ed25519.pub
```

Tell the user to add the printed public key to their git host:
- **GitHub**: Settings → SSH and GPG keys → New SSH key
- **Bitbucket**: Personal settings → SSH keys → Add key
- **GitLab**: User settings → SSH Keys → Add new key

Then re-test with:
```bash
ssh -T git@github.com   # or git@bitbucket.org / git@gitlab.com
```

Confirm success before proceeding.

#### After successful auth

```bash
cd <local-dir>
git pull  # Always pull latest before editing
```

---

## Step 3: Writing and Editing User Stories

### Determine approach

Ask the user:
> "Do you want me to help you brainstorm and write the user stories interactively, or
> do you have stories ready that you'd like me to format and refine?"

#### A) Interview Mode (brainstorm together)

Guide the user with questions like:
- "What is the core job this software does for its user?"
- "What are the 3 to 5 most critical actions a user must be able to take for this to be
  considered successful?"
- "What would a developer need to prove, via a real test, that each of those actions
  works end to end?"

For each workflow uncovered, draft a **rule** and one or more **proofs** per the
`anchor_format.md` spec. Show drafts to the user and iterate.

#### B) Format and Validate Mode (user provides content)

Accept the user's raw stories or bullet points. Then:
1. Map each one to the anchor format (rules plus proofs)
2. Check each proof against `audit_criteria.md`. Is it testable? Is it specific enough
   to give a developer full confidence if it passes?
3. Flag any that are vague, untestable, or missing a clear assertion, and suggest
   improvements

### Quality bar (from spec_quality_guide.md plus audit_criteria.md)

Every rule and proof must be:
- **Testable**: a developer could write an automated test that definitively passes or fails
- **Workflow-level**: covers a real end-to-end user action, not an implementation detail
- **Specific**: names the exact UI action, data state, or observable outcome
- **Free of implementation assumptions**: no mention of a specific tech stack unless
  the spec intentionally requires it

### Proof level requirements

These rules override anything in the reference docs about proof levels:

| Level | Rule |
|---|---|
| **Level 3** | **Required default.** Full end-to-end proofs. Generic enough that a developer and their AI assistant can find a way to automate the test, but specific enough that if automation isn't possible, a manual tester has a clear, unambiguous script to follow. Always aim here first. |
| **Level 2** | **Allowed with warning.** Before including any level 2 proof, output a visible warning in the chat: `Proof "[name]" is level 2. Consider whether this can be elevated to a level 3 end-to-end proof.` Ask the user to confirm they accept level 2 before including it. |
| **Level 1** | **Not allowed.** Do not write, suggest, or accept level 1 proofs under any circumstances. If a story can only be proven at level 1, flag it to the user and work together to either reframe the story at a higher level or remove it. |

When writing level 3 proofs, follow this pattern:
- Describe the **starting state** (what is true before the test)
- Describe the **user action or actions** in plain language
- Describe the **observable outcome** that must be true for the test to pass
- Keep it technology-agnostic: no mention of Selenium, Cypress, Jest, and the like, unless
  the user explicitly requires it

Before writing to disk, audit every proof's level against these rules. Self-correct
any level 1 proofs and flag any level 2 proofs to the user before showing final output.

---

## Step 4: User Review

Present the full proposed anchor spec content in the conversation for the user to read.

Say something like:
> "Here's the full anchor spec. Review it and let me know if anything needs changing.
> Once you approve, I'll write it to disk and push to git."

Iterate as many times as needed until the user says it's ready.

---

## Step 5: Write the Anchor Spec and Push to Git

An anchor spec is written to `specs/_anchors/<name>.md` inside the project repo, and
nowhere else. That directory is the only place the Purlin plugin reads anchors from, so a
file placed anywhere else is invisible to every Purlin command the project runs. `<name>`
is the snake_case token collected in Step 1, and it is both the file name and the name on
the `# Anchor:` line.

Once the user approves:

```bash
# Write the anchor spec
mkdir -p specs/_anchors
cat > specs/_anchors/<name>.md << 'EOF'
<anchor spec content here>
EOF

# Stage, commit, push
git add specs/_anchors/<name>.md
git commit -m "anchor(<name>): create"
git push
```

The commit prefix is `anchor(<name>): create`, the form `commit_conventions.md` defines for
creating an anchor spec. Use `anchor(<name>): <what changed>` when editing an existing one.
Never commit an anchor spec under a `chore:` prefix: the prefix is what tells a reader, and
the project's own tooling, that a spec moved.

Confirm success by showing the commit hash and a brief summary of what was pushed.

---

## Anchor Spec Template

A new anchor spec is written in the 2-section format `anchor_format.md` defines: a title
line, the metadata fields, `## Rules`, and `## Proof`. Fill it in like this:

```markdown
# Anchor: <name>

> Description: <what this product brief covers, in one plain sentence>
> Scope: <file patterns this anchor governs>
> Type: prodbrief

## Rules

- RULE-1: <a workflow a real user must be able to complete>
- RULE-2: <another workflow>

## Proof

- PROOF-1 (RULE-1): <starting state, user action, observable outcome>
- PROOF-2 (RULE-2): <starting state, user action, observable outcome>
```

`> Type: prodbrief` marks the spec as a product brief, which is what a user-story anchor is.
Do not invent fields that `anchor_format.md` does not list, and do not omit the title line,
`## Rules` or `## Proof`: the Purlin plugin parses all three.

---

## Notes

- **Multiple anchor specs per repo** are fully supported. Each is an independent file under
  `specs/_anchors/`. When editing, list the available anchor specs and let the user pick.
- **Never push without user approval** of the full spec content.
- **Always pull before editing** to avoid overwriting changes made by others.
- If the Purlin format spec version has changed since the last edit of a spec, flag this to
  the user and offer to migrate the spec to the new version before proceeding.
