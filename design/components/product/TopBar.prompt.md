Use `TopBar` at the top of any Purlin product view.

```jsx
<TopBar
  status="Data: 12h ago (pre-commit) — run purlin:status to refresh"
  meta={['Design: 12h ago', 'Integrity: 12h ago']}
  actions={<Button>Remote: 7 awaiting</Button>}
/>
```

The bar sits on `--canvas-deep`, one step darker than the page. The status dot is amber when data is stale, green when fresh.
