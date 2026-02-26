# Deprecation Plan: sync_upstream.sh → /pl-update-purlin

> **Status**: Deprecation Plan
> **Affects**: tools/sync_upstream.sh
> **Replaced By**: /pl-update-purlin agent skill (features/pl_update_purlin.md)
> **Timeline**: Gradual deprecation over 2 releases

---

## 1. Rationale

The script-based `tools/sync_upstream.sh` has fundamental limitations that cannot be addressed within a bash script:

1. **No Intelligence About User Customizations**
   - Cannot understand semantic differences between user overrides and upstream changes
   - Binary decision only: auto-copy or warn (no smart merging)

2. **Limited Scope**
   - Only tracks `.claude/commands/` and base `instructions/` + `tools/`
   - Does not track top-level scripts: `run_builder.sh`, `run_architect.sh`, etc.
   - Does not intelligently handle `.purlin/` folder customizations

3. **No Migration Guidance**
   - Cannot provide contextual migration plans for breaking changes
   - Cannot detect structural changes that affect overrides
   - Cannot suggest specific line-by-line updates

4. **Poor UX for Conflicts**
   - Warns about conflicts but provides no resolution assistance
   - User must manually diff and merge with no guidance

The `/pl-update-purlin` agent skill solves all these problems by using AI to:
- Analyze changes semantically
- Preserve user intent during merges
- Track all Purlin-sourced files (including top-level scripts)
- Generate migration plans with specific action items
- Offer interactive merge strategies

---

## 2. Deprecation Timeline

### Phase 1: Soft Deprecation (Current Release)
**Status**: PENDING IMPLEMENTATION

1. **Mark Script as Deprecated**
   - Add deprecation notice to `tools/sync_upstream.sh` header
   - Print deprecation warning when script runs
   - Direct users to `/pl-update-purlin`

2. **Documentation Updates**
   - Mark `features/submodule_sync.md` as DEPRECATED ✓
   - Add reference to `features/pl_update_purlin.md` ✓
   - Update README to recommend `/pl-update-purlin`

3. **Backward Compatibility**
   - Keep script functional
   - No breaking changes

**Script Modification Required**:
```bash
#!/bin/bash
# sync_upstream.sh — DEPRECATED: Use /pl-update-purlin instead
# This script will be removed in a future release.
# The new agent skill provides intelligent merging and migration guidance.

echo "⚠️  DEPRECATION WARNING"
echo ""
echo "This script is deprecated and will be removed in a future release."
echo "Please use the new intelligent agent skill instead:"
echo ""
echo "  /pl-update-purlin"
echo ""
echo "The agent skill provides:"
echo "  • Intelligent merge strategies for conflicts"
echo "  • Automatic tracking of top-level scripts"
echo "  • Migration plans for breaking changes"
echo "  • Preservation of .purlin/ customizations"
echo ""
read -p "Continue with legacy script? (y/N) " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Exiting. Please run: /pl-update-purlin"
    exit 0
fi
echo ""

# [rest of existing script...]
```

### Phase 2: Hard Deprecation (Next Release)
**Status**: NOT YET SCHEDULED

1. **Make Script Exit by Default**
   - Script prints deprecation message and exits
   - Add `--force-legacy` flag to override and run anyway
   - Update to critical priority warning

2. **Consumer Project Migration**
   - Identify any consumer projects still using `sync_upstream.sh`
   - Assist with migration to `/pl-update-purlin`
   - Document any edge cases

### Phase 3: Removal (Future Release)
**Status**: NOT YET SCHEDULED

1. **Remove Script**
   - Delete `tools/sync_upstream.sh`
   - Remove from all documentation
   - Archive spec file (keep for historical reference)

2. **Final Communication**
   - Announce removal in release notes
   - Confirm all consumer projects migrated

---

## 3. Migration Guide for Users

### For Purlin Core Developers
1. Implement `/pl-update-purlin` agent skill per `features/pl_update_purlin.md`
2. Test thoroughly against multiple consumer projects
3. Apply Phase 1 deprecation changes
4. Update all documentation

### For Consumer Project Users
**Old Workflow**:
```bash
cd <project_root>
tools/sync_upstream.sh
# Review warnings, manually merge conflicts
```

**New Workflow**:
```bash
# From Claude Code
/pl-update-purlin

# Review changes, choose merge strategies interactively
# Agent handles conflicts intelligently
```

**Benefits**:
- No manual conflict resolution
- Automatic tracking of all synced files
- Migration plans for breaking changes
- Dry-run mode to preview changes

---

## 4. Compatibility Notes

### What Stays the Same
- `.purlin/.upstream_sha` marker file (same format, same purpose)
- Git submodule structure
- Bootstrap process unchanged
- Project root detection logic

### What Changes
- Sync mechanism: bash script → agent skill
- Conflict resolution: manual → intelligent/interactive
- Scope: limited → comprehensive (includes top-level scripts)
- Output: text changelog → structured migration plans

### Breaking Changes
None. The agent skill is a superset of script functionality. All existing workflows continue to work (with deprecation warnings).

---

## 5. Rollback Plan

If critical issues are discovered with `/pl-update-purlin`:

1. **Immediate**: Remove deprecation warning from `sync_upstream.sh`
2. **Short-term**: Fix issues in agent skill
3. **Long-term**: Resume deprecation once stable

The script remains fully functional throughout deprecation phases to ensure zero downtime.

---

## 6. Implementation Checklist

### Phase 1 Tasks
- [ ] Implement `/pl-update-purlin` agent skill (create `.claude/commands/pl-update-purlin.md`)
- [ ] Add deprecation warning to `tools/sync_upstream.sh`
- [ ] Update README to recommend new skill
- [ ] Test agent skill against sample consumer projects
- [ ] Document migration guide for users

### Phase 2 Tasks (Future)
- [ ] Make script exit by default with `--force-legacy` override
- [ ] Identify and migrate any remaining consumer projects
- [ ] Update critical priority warning

### Phase 3 Tasks (Future)
- [ ] Remove `tools/sync_upstream.sh`
- [ ] Archive `features/submodule_sync.md`
- [ ] Announce removal in release notes

---

## 7. Success Metrics

Track success of migration:
1. **Adoption Rate**: % of sync operations using agent skill vs. script
2. **User Feedback**: Issues filed, user satisfaction
3. **Merge Conflict Resolution**: % of conflicts resolved without manual intervention
4. **Migration Plan Quality**: User reports of successful migrations

**Target for Phase 2**: >90% of sync operations using agent skill for 2 release cycles

---

## 8. Open Questions

1. **Should we provide a compatibility shim?**
   - E.g., `tools/sync_upstream.sh` could internally invoke `/pl-update-purlin`
   - Pro: Seamless migration for users who have automated workflows
   - Con: Delays true migration, complicates maintenance

2. **How to handle non-interactive environments?**
   - Agent skill requires Claude Code session
   - Script can run in CI/CD
   - Solution: Keep script for automated environments only?

3. **Version pinning strategy?**
   - Some users may want to stay on script-based sync
   - Should we support version pinning to delay migration?

---

## 9. Notes

- This deprecation is motivated by fundamental architectural limitations, not bugs
- The agent skill approach aligns with Purlin's philosophy: use AI where it adds value
- Gradual deprecation ensures no disruption to existing projects
