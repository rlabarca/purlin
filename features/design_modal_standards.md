# Design: CDD Text Modal Standards

> Label: "Design: Text Modal Standards"
> Category: "Common Design Standards"

## Purpose

Defines the visual and behavioral constraints for all text-based (content-reading) modals in the CDD Dashboard. These modals share a common width, font size control, title sizing, close behavior, scrollable body, and theme integration. The Branch Collaboration Operation Modal is an operational modal and is excluded from these standards.

## Design Invariants

### Width

- All text-based modals MUST occupy 70% of the viewport width.
- On viewports narrower than 500px, modals MUST fall back to 90% of viewport width.

### Title

- Modal titles MUST render 4 points larger than the modal's default body font size.
- The default body font size is inherited from the project's design anchor (for Purlin: `design_visual_standards.md` Section 2.3, Inter 14px). With a 14px base, titles render at 18px.

### Font Size Control

- All text-based modals MUST include a font size adjustment control in the header area: a decrease button (minus sign), horizontal slider, and increase button (plus sign).
- Range: 4 points below the default body font size to 30 points above the default body font size.

### Font Control Position Stability

- The font size control widget (buttons and slider) MUST occupy a fixed position in the modal header that does NOT shift horizontally or vertically when the font size adjustment value changes.
- The modal title MUST be constrained (e.g., truncated with ellipsis, or given a fixed flex allocation) so that title size changes do not displace the font controls or close button.

### Smooth Scaling

- Dragging the slider MUST produce visually smooth, continuous transitions. Individual step increments MUST NOT be perceptible as discrete jumps during a continuous drag operation.
- The slider MUST use sub-integer step granularity (step <= 0.5) so that the number of discrete positions across the slider's physical width is sufficient for smooth visual feedback.
- Button clicks MUST produce visually distinct, sequential increments. Rapid clicking MUST NOT cause batched or skipped visual updates -- each click MUST result in one visible increment before the next click takes effect.

### Relative Scaling Invariant

- All text within the modal (title, metadata rows, tabs, headings, paragraphs, lists, code blocks, tags, and inline-styled content in consumer modals) MUST scale together when the font size control is adjusted, preserving relative size differences between text elements.

### Text Wrapping

- Text MUST wrap correctly at all slider positions without horizontal overflow or clipping.

### Session Persistence

- The selected font size MUST persist for the browser session across modal open/close cycles. Reopening any text-based modal retains the last setting.

### Close Behavior

- All text-based modals MUST support three close methods: X button, Escape key, click outside the modal overlay.

### Scrollable Body

- Modal body MUST scroll vertically when content exceeds the available height.

### Theme Integration

- All modal elements MUST respect the active theme (Blueprint/Architect) using CSS custom properties from `design_visual_standards.md`.

### Excluded Modals

- The Branch Collaboration Operation Modal (`#bc-op-modal-overlay`) is an operational modal and is NOT governed by these standards.

## Scenarios

No automated or manual scenarios. This is a design anchor node -- its constraints are
enforced by the foundation feature (`cdd_modal_base.md`) and validated through consumer
feature scenarios.
