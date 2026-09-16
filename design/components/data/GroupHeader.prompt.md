Use `GroupHeader` to band a run of spec rows by kind.

```jsx
<GroupHeader title="Skills" count={12} covered={158} total={158}
  summary={[{label:'9 signed'},{label:'3 passed',tone:'pass'}]} />
```

The summary dots are 7px circles, never icons. Title is bold and letter-spaced; the count beside it is muted and parenthesised.
