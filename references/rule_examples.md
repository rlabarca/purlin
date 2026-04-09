# Rule Examples from Real Projects

Bad-to-good rule rewrites collected from actual spec reviews and audit findings. Organized by the five contract categories from the [spec quality guide](spec_quality_guide.md). This file grows over time — when a bad rule is caught and rewritten, add the pair here.

---

## Inbound Contracts

Rules about data entering the system — API responses, config, props, messages. The #1 rebuild risk: wrong field names mean wrong data on screen or in storage.

### tca-frontend: Mortgage Report Data (2026-04)

```
Bad:  "MortgageReport type defines the raw API response shape including AnalysisContact and report metadata"
Good: "API field user.LogoFileName maps to header logo (via formatImageUrl); user.FirstName + ' ' + user.LastName maps to contact display name"
Why:  The API uses lowercase 'contact' not 'AnalysisContact', 'user' not 'User'. Without exact field names, a rebuild wires to wrong fields.

Bad:  "Fetches report data from the API"
Good: "GET /EdgeMobileService/EdgeService.svc/json/GetAnalysisGuidDisplay with params {contactId, isFirstTime, position, isDetails, historyId, updateDate} returns full report directly"
Why:  Missing the service path prefix and query params means a rebuild can't even call the API correctly.

Bad:  "Hero calls useProductQuery hook"
Good: "Hero displays product.address, product.loanAmount, and product.rate from GET /api/products/:id"
Why:  Hook name is implementation. Data fields are what an engineer needs to wire correctly.
```

## Outbound Contracts

Rules about data leaving the system — analytics events, API calls out, database writes, log entries.

### tca-frontend: Analytics Integration (2026-04)

```
Bad:  "Sends analytics events on key interactions"
Good: "Fires Firebase event 'report_viewed' with params {reportId, reportType, contactId} when report page loads"
Why:  Without event name and param shape, analytics dashboards break on rebuild.

Bad:  "Tracks user behavior with TrustEngine"
Good: "TrustEngine pixel fires on page load, polling at 100ms intervals for max 50 attempts until container element exists"
Why:  Polling strategy and retry limits are behavioral — affects whether analytics actually fires.

Bad:  "Logs errors"
Good: "API fetch failures log {endpoint, statusCode, errorMessage} at warn level; do not surface to user"
Why:  Log shape matters for monitoring dashboards. 'Do not surface' is a UX constraint.
```

## Transformation Rules

Rules about logic that converts between inbound and outbound — field mappings, formulas, formatters.

### tca-frontend: Data Builders (2026-04)

```
Bad:  "Formats data for display"
Good: "formatImageUrl prepends CDN base URL to user.LogoFileName; returns empty string if null"
Why:  The null handling and URL construction are both behavioral — a rebuild without this shows broken images.

Bad:  "Builds mortgage data from API response"
Good: "Header logo comes from formatImageUrl(user.LogoFileName), not contact.CompanyLogo. Contact name from user.FirstName + user.LastName, not a single ContactName field."
Why:  Field source matters. The API has multiple name-like fields — picking the wrong one shows wrong data.

Bad:  "Loan details uses product.fields array"
Good: "Loan details renders product.fields filtered by excluded=false, sorted by field.order"
Why:  Without filter/sort spec, a rebuild shows all fields in wrong order.

Bad:  "Calculates monthly payment"
Good: "Monthly payment = principal * (rate/12) / (1 - (1 + rate/12)^-term); displayed as currency with 2 decimal places"
Why:  The formula is the behavior. Getting it wrong means wrong financial numbers shown to users.
```

## State Transitions

Rules about feature lifecycle — valid states, transitions, timeouts.

### tca-frontend: Recording Session (2026-04)

```
Bad:  "Has multiple recording states"
Good: "Recording lifecycle: idle → recording → paused → stopped. Cannot go from stopped back to recording without reinitializing."
Why:  Missing transitions mean a rebuild allows invalid state changes.

Bad:  "Polls for updates"
Good: "Analysis polling: starts on mount at 5s intervals, pauses when tab hidden, resumes on tab focus, stops on unmount or when analysis complete"
Why:  Tab visibility and cleanup behavior prevent resource leaks and stale data.
```

## Access Contracts

Rules about who can see or do what — permissions, flags, modes.

### tca-frontend: Report Access (2026-04)

```
Bad:  "Checks user permissions"
Good: "Password-gated reports show password form; authenticated reports show content directly. Password validated against GET /ValidatePassword endpoint."
Why:  The gate type (password vs auth) and validation endpoint are both behavioral.

Bad:  "Has loan officer mode"
Good: "Loan officer mode (activated by lo=true URL hash param OR lo cookie) shows editable benefit fields and save button; merges LO overrides with base report data"
Why:  Activation mechanism (hash + cookie) and data merging are both things a rebuild would get wrong.

Bad:  "Uses feature flags"
Good: "Feature flag 'ai_chat_enabled' controls AI chat widget visibility; evaluated at render time via Split SDK"
Why:  Flag name and evaluation timing matter — wrong flag name means wrong feature toggling.
```

## Implementation Details — NOT Rules

These describe *how* code works, not *what* it does. They fail the rebuild test — an engineer using a different technique would still produce correct behavior.

```
"Uses useMediaQuery hook with 768px breakpoint"     -- names the hook, not the behavior
"Hero background uses var(--surface-primary)"        -- names the token, not the behavior
"SVG elbow connector uses rx={h/2} path formula"     -- names the technique
"Info bar has margin-top: -66px"                     -- CSS pixel value, visual polish
"Stats grid uses CSS Grid with 3 columns"            -- names the layout technique
"Each accordion is a separate component"             -- component structure, not behavior
"Has error boundary around chart"                    -- error handling technique, not outcome
```

When implementation causes a **behavioral** problem, the problem is a rule — the technique is not:

```
"Stat cards remain usable (no overlap, no hidden content) on viewports below 768px"  -- rule (behavioral)
"Section colors follow the active theme"                                              -- rule (behavioral)
"Missing chart data shows 'No data available' message instead of crashing"            -- rule (behavioral)
```

---

<!-- Add new project examples below. Format: ## project-name: Feature (YYYY-MM) under the relevant contract category -->
