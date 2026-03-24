# User Testing Discoveries: PL Session Resume

### [BUG] Checkpoint format missing spec fields (Discovered: 2026-03-23)
- **Observed Behavior:** Regression Authoring + Last Authored Feature (QA) were in the skill but not the spec. Builder Delivery Plan field was missing "features completed this phase" sub-field.
- **Expected Behavior:** QA checkpoint template should only contain fields from spec Section 2.2.3. Builder Delivery Plan field should include completed features per spec Section 2.2.2.
- **Resolution:** Removed QA extra fields (Regression Authoring, Last Authored Feature) from skill file. Expanded Builder Delivery Plan template to include completed features sub-field. Fixed two tests broken by submodule_command_path_resolution path changes.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See pl_session_resume.impl.md for context.
