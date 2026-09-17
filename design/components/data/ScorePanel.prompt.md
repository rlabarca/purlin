Use `ScorePanel` for the two headline percentages — proof design and proof integrity. Only ever two of these on a screen; more and they stop reading as headlines.

```jsx
<ScorePanel value="92%" label="Proof design" detail="885 of 885 measured" tone="pass" />
<ScorePanel value="43%" label="Proof integrity" detail="884 of 1195 measured" tone="fail" />
```
