# Implementation Notes: What's Different? (Collaboration Digest)

**[DEVIATION]** Summarize Impact button placement: Spec Section 2.14.1 places the button in the dashboard panel above the "What's Different?" button. Implemented inside the modal instead, per Human Executive direction. The button appears in the modal body above the digest content — when no cached analysis exists it shows "Summarize Impact", when cached it shows the impact summary with a "Regenerate" button. The dashboard panel only has the "What's Different?" button. (Severity: HIGH)

**[CLARIFICATION]** Modal scroll structure: The impact section and digest body are wrapped in a single `.modal-body` scrollable container (`wd-modal-scroll`) to prevent overflow when the impact summary adds significant content. The impact section, generate button, and digest body are all children of this scroll container. (Severity: INFO)
