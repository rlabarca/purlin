Use `NoticeBar` for repo-state warnings that sit between the summary tiles and the spec list.

```jsx
<NoticeBar count={1}>uncommitted file</NoticeBar>
```

Counts are coloured, the noun is not. Keep the text lowercase and singular/plural correct — the product never says "1 file(s)".
