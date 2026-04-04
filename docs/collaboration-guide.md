# Collaboration

Two ways to collaborate with Purlin: **external anchors** (influence a project from outside it) and **branch handoff** (pass a project back and forth via git).

---

## External Anchors

An anchor with `> Source:` is an external reference — a contract defined outside the project that shapes how code is written inside it. This is how designers, API teams, security teams, and product managers influence a project without touching its code.

### How it works

1. Someone outside the project (a designer, an API team, a compliance officer) publishes a spec to a git repo or a Figma file.
2. A project member creates an anchor pointing to it:
   ```
   purlin:anchor create api_contract --source git@github.com:acme/api-spec.git
   ```
   Or for Figma:
   ```
   here's our design system: figma.com/design/abc123/Brand-System
   ```
3. The anchor's rules become part of the project's coverage. Engineers must write tests proving compliance.
4. When the external source updates, `purlin:anchor sync` pulls the changes. If local rules conflict, `purlin:drift` surfaces them as PM action items.

### Examples

**Design team publishes a Figma file.** A project member runs `purlin:anchor add-figma <url>`. The anchor gets one rule: "match the design." The builder reads Figma directly via MCP for full fidelity. The test captures a screenshot and compares. If the designer updates the Figma file, `purlin:anchor sync` detects the change and marks affected proofs as stale.

**API team publishes a contract.** A project member creates an anchor with `> Source:` pointing to the API spec repo. The anchor's rules define what the API must do. When the API team ships a breaking change, `purlin:anchor sync` pulls the new spec and `purlin:drift` flags affected features.

**Security team publishes policies.** A global anchor (`> Global: true`) with `> Source:` pointing to the security policy repo. Its rules auto-apply to every feature. Engineers must prove compliance without explicitly requiring the anchor.

**Product manager publishes a brief.** An anchor with `> Source:` pointing to a product brief in a git repo. The anchor's rules capture the testable requirements. The brief itself provides full context for the builder when implementing.

### The external reference is authoritative

You can add local rules to an externally-referenced anchor — but you can't change the external source by editing the anchor file. The `> Source:` and `> Pinned:` fields point to what the external team published. `purlin:anchor sync` updates from that source. If your local rules conflict with a source update, `purlin:drift` surfaces the conflict for the PM to resolve.

### CI staleness check

In CI, verify external references are current before deploying:

```bash
# Exit non-zero if any anchor is behind its external source
purlin:anchor sync --check-only
```

Or script it directly:

```bash
PINNED=$(grep '> Pinned:' specs/_anchors/api_contract.md | awk '{print $3}')
REMOTE=$(git ls-remote git@github.com:acme/api-spec.git HEAD | cut -f1)
if [ "$PINNED" != "$REMOTE" ]; then echo "Anchor stale"; exit 1; fi
```

---

## Branch Handoff

Pass a project back and forth between collaborators using git branches. Each person works in their own Claude Code session, pushes their changes, and the next person pulls.

### How it works

1. Person A works on the project, writes specs and code, pushes to a branch.
2. Person B pulls the branch, continues where A left off.
3. The specs, proof files, and receipts travel with the branch — the next person sees exactly what's proved and what isn't.

### Pre-push mode matters

The pre-push hook runs before every push. If it's set to **strict** mode, ALL features must be READY (every rule has a passing proof) before you can push. This blocks handoffs of work-in-progress.

**For branch collaboration, use warn mode:**

```json
// .purlin/config.json
{
  "pre_push": "warn"
}
```

In **warn** mode, the hook blocks only on FAILING proofs. Partial coverage (rules without tests yet) is allowed with a warning. This lets you push incomplete work for someone else to continue.

**Use strict mode for protected branches** (main, release) where everything should be verified before merging.

### What travels with the branch

| Artifact | Purpose |
|----------|---------|
| `specs/**/*.md` | The rules — what the code must do |
| `specs/**/*.proofs-*.json` | Test results — which rules are proved |
| `specs/**/*.receipt.json` | Verification receipts — certified completeness |
| `.purlin/config.json` | Team settings (test framework, pre-push mode) |

The next person runs `/purlin:status` to see the current state, `/purlin:drift` to see what changed, and picks up where you left off.

### Merge conflicts in proof files

Proof files (`.proofs-*.json`) are generated from test results, not hand-written. When merging:

1. Accept either version of the conflicting proof file (doesn't matter which).
2. Run `purlin:unit-test` to regenerate from the merged code.
3. Commit the regenerated file.

This works because proof files are feature-scoped — testing feature X only rewrites X's entries.
