Use `StatTile` for the row of counts across the top of a dashboard: specs, signed, passed, untested, failing.

```jsx
<StatTile value={37} label="Signed" tone="pass" note="39 on host, 0 on claude-cli" />
<StatTile value={0} label="Stale" tone="warn" />
```

Tone carries the meaning: green for good, amber for pending, red for failing, cream for a plain count. A zero stays amber if the metric is "stale" — the hue describes the metric, not the value.
