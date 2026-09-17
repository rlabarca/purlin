Use `StatusPill` in spec tables and PR summaries wherever a rule's cell is shown.

```jsx
<StatusPill status="passed" />
<StatusPill status="signed" />
<StatusPill status="failed" />
```

The distinction matters: `signed` is solid because a person signed it, everything else is outline because a machine computed it. Do not invent new words — use the cell word the rule's level already gives you.
