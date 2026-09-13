Use `StatusPill` in spec tables and PR summaries wherever a rule's state is shown.

```jsx
<StatusPill status="passing" />
<StatusPill status="verified" />
<StatusPill status="failing" />
```

The distinction matters: `verified` is solid because a person signed it, everything else is outline because a machine computed it. Do not invent new statuses — the product recognises exactly seven.
