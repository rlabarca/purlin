Use `CodeBlock` for anything the machine printed: command transcripts, record JSON, spec fragments, mutation diffs. It is the single most common element in the deck after body text.

```jsx
<CodeBlock lines={[
  'break 7 of 41   src/auth.py:71',
  '-   if token.issued_at < now - TTL:',
  '+   if token.issued_at > now - TTL:',
  {text:'    noticed', kind:'muted'},
]} />
```

Never syntax-highlight beyond the four line kinds. Deck usage sets `size="var(--type-body-sm)"`; product usage drops to `var(--ui-sm)`.
