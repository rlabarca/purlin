Use `CoverageBar` in every spec row and group header where proofs-covered is shown.

```jsx
<CoverageBar covered={19} total={19} />
<CoverageBar covered={7} total={9} />
```

The bar is 5px, fully rounded, and never labelled with a percentage — the ratio to its left is the label.
