# Implementation Notes: CDD Modal Base

Modal body base font size was originally 13px but `design_modal_standards.md` specifies 14px (inherited from `design_visual_standards.md` Section 2.3, Inter 14px). Title was 21px fixed but spec says 4pts above body = 18px. Corrected to: body 14px, title calc(18px + adjust), headings h1=17px/h2=15px/h3=13px/code=12px. All non-body elements (title, metadata, tabs) now scale with the --modal-font-adjust slider. Step Detail inline-styled content updated to use calc() for scaling.

### Audit Finding -- 2026-03-19

[DISCOVERY] Font size slider uses integer step instead of sub-integer step — Acknowledged

**Source:** /pl-spec-code-audit --deep (item #16)
**Severity:** MEDIUM
**Details:** The spec (`design_modal_standards.md` Section 2.4) states the slider step should be <=0.5 for fine-grained control. The current implementation uses an integer step (1). This means users cannot select intermediate font sizes (e.g., 14.5px), reducing the granularity of the adjustment.
**Suggested fix:** Change the slider `step` attribute from `1` to `0.5` (or finer). Ensure the display label and calc() expressions handle decimal values correctly.

---

[DISCOVERY] Overlay click-to-close behavior untested — Acknowledged

**Source:** /pl-spec-code-audit --deep (item #17)
**Severity:** MEDIUM
**Details:** The spec defines three close methods: X button, Escape key, and clicking the overlay (outside the modal). Automated tests verify X button and Escape key but not overlay click. The overlay click behavior is implemented but has no test coverage.
**Suggested fix:** Add an automated scenario that verifies clicking the overlay backdrop closes the modal. This should test that: (a) clicking the overlay closes the modal, (b) clicking inside the modal content area does NOT close it (event propagation guard).

