Use `ScorePanel` for a headline percentage, such as the project's test strength against the
minimum its gate asks for. Only ever two of these on a screen; more and they stop reading as
headlines.

```jsx
<ScorePanel value="86%" label="Test strength" detail="minimum 80%" tone="pass" />
<ScorePanel value="64%" label="Test strength" detail="minimum 80%" tone="fail" />
```
