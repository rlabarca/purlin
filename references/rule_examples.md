# Rule Examples from Real Projects

Bad-to-good rule rewrites collected from actual spec reviews and audit findings. This file grows over time — when a bad rule is caught and rewritten, add the pair here.

For the judgment framework behind these examples, see [spec_quality_guide.md](spec_quality_guide.md) ("The rebuild test").

---

## tca-frontend: Single Product Presentation (2026-04)

UI component displaying loan product details with purchase/refi conditional rendering, data-driven sections, and graceful degradation.

### Data source rules (wrong-behavior tier)

```
Bad:  "Hero calls useProductQuery hook"
Good: "Hero displays product.address, product.loanAmount, and product.rate from GET /api/products/:id"
Why:  Hook name is implementation. Data fields are what an engineer needs to wire correctly.

Bad:  "Loan details uses product.fields array"
Good: "Loan details renders product.fields filtered by excluded=false, sorted by field.order"
Why:  Without filter/sort spec, a rebuild shows all fields in wrong order.

Bad:  "Chart data comes from Redux store"
Good: "Looking Ahead chart renders product.chartData; purchase-only — hidden for refinance loans"
Why:  Store name is implementation. The conditional gate and data field are behavioral.
```

### Conditional gate rules (wrong-behavior tier)

```
Bad:  "Component checks loanType === 'purchase'"
Good: "Purchase flow displays rate lock date and estimated closing costs; refinance flow displays current balance and payoff amount"
Why:  The conditional expression is implementation. What each segment sees is the behavior.

Bad:  "Uses feature flag to show chart"
Good: "Chart section renders only when product.chartData is present and loanType is purchase"
Why:  Feature flag mechanism is implementation. The visibility conditions are behavioral.
```

### Failure mode rules (broken-functionality tier)

```
Bad:  "Has error boundary around chart"
Good: "Missing chart data shows 'No data available' message instead of crashing"
Why:  Error boundary is a technique. The user-visible fallback is the behavior.

Bad:  "Each accordion is a separate component"
Good: "Accordion sections render independently — one section failing does not collapse others"
Why:  Component structure is implementation. Section independence is the behavior an engineer would miss.
```

### Implementation details — NOT rules

```
"Uses useMediaQuery hook with 768px breakpoint"     -- names the hook, not the behavior
"Hero background uses var(--surface-primary)"        -- names the token, not the behavior
"SVG elbow connector uses rx={h/2} path formula"     -- names the technique, not the behavior
"Info bar has margin-top: -66px"                     -- CSS pixel value, visual polish
"Stats grid uses CSS Grid with 3 columns"            -- names the layout technique
```

When responsive or theme code causes a **behavioral** problem, the problem is a rule — the technique is not:

```
"Stat cards remain usable (no overlap, no hidden content) on viewports below 768px"  -- rule (behavioral)
"Section colors follow the active theme"                                              -- rule (behavioral)
```

---

<!-- Add new project examples below. Format: ## project-name: Feature (YYYY-MM) -->
