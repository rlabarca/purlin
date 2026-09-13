Use `StatTile` for the row of counts across the top of a dashboard: specs, verified, passing, incomplete, failing.

```jsx
<StatTile value={37} label="Verified" tone="pass" note="39 on host, 0 on claude-cli" />
<StatTile value={0} label="Incomplete" tone="warn" />
```

Tone carries the meaning: green for good, amber for pending, red for failing, cream for a plain count. A zero stays amber if the metric is "incomplete" — the hue describes the metric, not the value.
