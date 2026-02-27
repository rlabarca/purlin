# Implementation Notes: What's Different? (Collaboration Digest)

**[DEVIATION] [ACKNOWLEDGED]** Summarize Impact button placement: Originally spec'd for the dashboard panel above the "What's Different?" button. Moved inside the modal per Human Executive direction. Spec updated (Sections 2.14.1, 2.14.2, 2.14.3, scenarios, visual spec) to match implementation. (Severity: HIGH)

**[CLARIFICATION]** Modal scroll structure: The impact section and digest body are wrapped in a single `.modal-body` scrollable container (`wd-modal-scroll`) to prevent overflow when the impact summary adds significant content. The impact section, generate button, and digest body are all children of this scroll container. (Severity: INFO)
