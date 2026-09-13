Use `Panel` for every boxed region: stat tiles, code wells, dashboard cards, deck call-outs.

```jsx
<Panel tone="veil"><SectionLabel>A coverage board</SectionLabel></Panel>
<Panel tone="sunken"><CodeBlock>$ purlin:verify</CodeBlock></Panel>
```

Never add a box-shadow. Never round past `--radius-sm`. A panel that needs emphasis switches to `tone="accent"` (copper rule), not to a heavier shadow.
