# Implementation Notes: CDD QA Effort Display

### Rendering Location
The QA effort breakdown renders inline within each feature row on the CDD Dashboard, below the QA status column. It displays the effort classification computed by the Critic's `verification_effort` block in `tests/<feature>/critic.json`.

### Data Source
All effort data comes from the Critic's per-feature `critic.json` output. The dashboard reads this at page load and on each 5-second auto-refresh. No separate computation is needed in the frontend.
