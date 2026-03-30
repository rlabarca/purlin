### [DISCOVERY] STALE: "Submit" button bg `--color-danger` (#c0392b) (Discovered: 2026-03-20)
- **Screen:** Feedback Modal
- **Checklist Item:** "Submit" button: bg `--color-danger` (`#c0392b`), border-radius 8px, height 40px, Inter Medium 14px (`--text-white`)
- **Figma Reference:** Figma node 7:81 in file TEZI0T6lObCJrC9mkmZT8v
- **Detail:** Figma design updated after spec extraction — spec value is outdated. Figma shows Submit button with `--color-neutral-800` (#1e1e1e); spec and app correctly use `--color-danger` (#c0392b, red). Figma needs to be updated to reflect the red Submit button requirement.
- **Action Required:** PM
- **Status:** SPEC_UPDATED
- **Resolution:** Figma updated to amber (#F59E0B) for Submit button fill. Spec updated (2026-03-24): Submit button bg is `--color-supplementary-amber` (#F59E0B); Cancel button border remains `--color-supplementary-purple-500` (#681f95). **Architect action required:** add `--color-supplementary-purple-500: #681f95` and `--color-supplementary-amber: #F59E0B` to `features/design_visual_standards.md`. **Builder action required:** update app CSS and button styles to use the new tokens.
