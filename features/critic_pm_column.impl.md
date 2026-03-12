# Implementation Notes: Critic PM Column

## Owner Tag Parsing
The `extract_owner()` function scans the blockquote metadata at the top of feature files for `> Owner: PM` or `> Owner: Architect`. It stops scanning at the first non-blockquote, non-heading line to avoid false matches in body text. Anchor nodes (`arch_*`, `design_*`, `policy_*`) always return 'Architect' via the existing `is_policy_file()` check.

## SPEC_DISPUTE Visual Detection
Visual SPEC_DISPUTEs are detected by checking the dispute title for: `Visual:` prefix, `visual specification` substring (case-insensitive), or exact screen name matches from the feature's parsed `visual_spec.screen_names`. This heuristic covers the standard naming conventions without requiring structured metadata in discovery entries.

## PM Role Status Logic
PM status uses the same pattern as other roles but with simpler states (DONE/TODO/N/A). Relevance is determined by: feature is PM-owned, has a Visual Specification section, or has Figma references. This keeps PM N/A for the majority of features that have no design component.
