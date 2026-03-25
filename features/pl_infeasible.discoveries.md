# User Testing Discoveries: PL Infeasible

### [BUG] Skill missing CRITICAL priority designation (Discovered: 2026-03-23)
- **Observed Behavior:** Skill only says "surface in the Critic report" without mentioning CRITICAL priority.
- **Expected Behavior:** Spec says INFEASIBLE generates a CRITICAL-priority PM action item. Skill should mention CRITICAL.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See pl_infeasible.impl.md for context.
