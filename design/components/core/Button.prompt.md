Use `Button` for any control the user clicks. Purlin's product uses outline pills almost exclusively — solid is for the single primary action on a screen, ghost for tertiary/dismiss.

```jsx
<Button tone="accent">Remote: 7 awaiting</Button>
<Button variant="solid" tone="pass">Approve rule</Button>
<Button variant="ghost">Dismiss</Button>
```

Sentence case, never all-caps. Hover lifts the fill to a 6% tint of the hue; press darkens rather than scales.
