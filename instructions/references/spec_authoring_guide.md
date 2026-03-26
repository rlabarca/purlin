# Spec Authoring Guide

> Shared reference for PM and Architect agents. Loaded by `/pl-spec` and `/pl-anchor`.

## 1. Shared Principles

Both PM and Architect write feature specs and must produce artifacts that are:

- **Behavioral, not implementational.** Describe what the system does, not how code is structured. The Builder decides the "how."
- **Unambiguous.** Every scenario has one correct interpretation. If two reasonable people could disagree on the expected behavior, the spec is incomplete.
- **Testable.** Every requirement must be verifiable — either through an automated scenario, a manual scenario, or a visual checklist item.
- **Anchored.** Every feature declares `> Prerequisite:` links to the anchor nodes whose constraints it must satisfy. Missing anchors mean missing constraints.
- **Minimal.** Include only what the Builder and QA need. Don't over-specify implementation details, don't pad with aspirational requirements, don't add scenarios for impossible states.
- **Untagged scenarios.** QA Scenarios are written without `@auto` or `@manual` suffix tags. These tags are QA-owned classification outputs added during verification. The Architect and PM write the scenario; QA decides how to test it.

## 2. Role Focus

| Concern | PM | Architect |
|---|---|---|
| **Intent & UX** | Primary — translates user intent into behavioral requirements | Reviews for completeness |
| **Visual Specification** | Authors Token Maps and visual checklists | Validates structure, defers design decisions to PM |
| **Structural Integrity** | Follows format rules | Enforces format rules, validates prerequisite graph |
| **Anchor Nodes** | May propose new anchors via specs | Creates and maintains anchor nodes |
| **Gap Analysis** | Probes for missing edge cases (Probing Questions) | Validates spec gate compliance, scenario coverage |
| **Figma Artifacts** | Reads/writes Figma, manages design pipeline | References for context, does not write to Figma |

When both roles are active: PM drafts, Architect validates. When only Architect is active: Architect does both.

### Anchor Node Authorship

| Prefix | PM | Architect |
|---|---|---|
| `design_*` | **Can create and modify** -- PM owns the design language | Can create and modify |
| `policy_*` | **Can create and modify** -- PM may define governance rules | Can create and modify |
| `arch_*` | **Cannot touch** -- technical architecture is Architect-only | Can create and modify |

The PM runs `/pl-anchor` for `design_*` and `policy_*` nodes. The command enforces the `arch_*` restriction.

## 3. Anchor Node Classification Guide

Anchor nodes define **shared constraints** that multiple features must obey. The prefix determines the domain. Use this guide to classify where a constraint belongs.

### 3.1 `arch_*` — Technical Architecture

**Question:** "How must the system be built?"

These define the technologies, code patterns, and structural conventions that the Builder follows when writing code. They are the technical contract.

| Domain | What Goes Here | Examples |
|---|---|---|
| **Languages & Runtimes** | Required versions, compiler flags, strict mode | "TypeScript strict mode", "Python 3.11+ with type hints" |
| **Frameworks & Libraries** | Approved frameworks, version constraints, banned alternatives | "React 18+ functional components only", "SQLAlchemy for all DB access" |
| **Code Organization** | Module boundaries, file naming, import rules | "Feature-sliced directory structure", "No circular imports between packages" |
| **API Contracts** | Wire format, versioning scheme, error response shape | "REST with JSON:API envelope", "GraphQL schema-first development" |
| **Data Patterns** | Storage conventions, serialization rules, migration discipline | "All timestamps UTC ISO 8601", "Migrations are forward-only, no rollbacks" |
| **State Management** | Client state libraries, caching strategy, persistence rules | "Zustand for client state", "React Query for server cache" |
| **Error Handling** | Error taxonomy, propagation patterns, recovery contracts | "All errors extend AppError", "Use Result types, not thrown exceptions" |
| **Logging & Observability** | Log format, levels, correlation, metrics | "Structured JSON logs", "Correlation ID on every request" |
| **Performance Budgets** | Hard limits the Builder must meet | "Bundle < 200KB gzipped", "API P95 < 200ms" |
| **Infrastructure** | Container base images, deployment shape, environment contracts | "Alpine-based Docker images", "12-factor app configuration" |
| **Testing Patterns** | Test tooling, assertion styles, fixture conventions | See `arch_testing.md` for the canonical example |
| **Dependency Rules** | What may depend on what, forbidden couplings | "UI layer must not import from data layer directly" |

**FORBIDDEN patterns** in `arch_*` are typically grepable code patterns: banned imports, prohibited function calls, disallowed file patterns.

**Key signal:** If the constraint tells the Builder *which tool to pick* or *how to structure code*, it belongs in `arch_*`.

### 3.2 `design_*` — Design Language

**Question:** "How must the system look and feel?"

These define the visual and interaction conventions that shape user experience. Both PM and Builder read these — PM to author Visual Specifications, Builder to implement them.

| Domain | What Goes Here | Examples |
|---|---|---|
| **Color System** | Token definitions, theme palettes, contrast rules | "All colors via `var(--app-*)` tokens", "Dark theme is default" |
| **Typography** | Font stacks, size scale, weight usage, letter spacing | "Inter for body, Montserrat for display", "Base size 14px" |
| **Spacing & Layout** | Grid system, spacing scale, responsive breakpoints | "8px base grid", "Mobile-first breakpoints at 640/768/1024" |
| **Component Styling** | Border radii, shadows, elevation, dividers | "4px border radius on cards", "3-level elevation system" |
| **Animation & Motion** | Transition durations, easing curves, reduced-motion | "150ms ease-out for micro-interactions", "Respect prefers-reduced-motion" |
| **Iconography** | Icon library, sizing, stroke weight | "Lucide icons, 20px default, 1.5px stroke" |
| **Interaction Patterns** | Modal behavior, toast placement, drag conventions | "Modals center-screen with backdrop blur", "Toasts stack bottom-right" |
| **Accessibility (Visual)** | Focus indicators, contrast ratios, target sizes | "2px solid accent focus ring", "4.5:1 contrast minimum" |
| **Platform Conventions** | OS-specific design rules | "Follow iOS HIG for native, Material 3 for Android" |
| **Design-to-Code Pipeline** | How Figma artifacts map to code tokens | "Figma variables map 1:1 to CSS custom properties" |

**FORBIDDEN patterns** in `design_*` are typically hardcoded visual values: hex colors outside token definitions, inline styles bypassing the token system, magic-number spacing.

**Key signal:** If the constraint governs *what the user sees or how they interact*, it belongs in `design_*`.

### 3.3 `policy_*` — Governance & Process

**Question:** "What rules must the system obey?"

These define organizational, legal, regulatory, and process requirements. They exist because of external authorities (law, compliance, security team, business rules) rather than technical preference.

| Domain | What Goes Here | Examples |
|---|---|---|
| **Security Baselines** | OWASP mitigations, auth requirements, input validation | "CSP headers on all responses", "No `eval()` or `innerHTML`" |
| **Compliance** | Regulatory mandates with legal force | "GDPR right-to-erasure within 30 days", "HIPAA encryption at rest" |
| **Accessibility (Regulatory)** | WCAG level commitment, audit requirements | "WCAG 2.1 AA compliance", "Annual third-party audit" |
| **Data Governance** | PII handling, retention, encryption, anonymization | "PII encrypted at rest", "No PII in log output", "90-day retention" |
| **Licensing** | Dependency license constraints | "No GPL in commercial builds", "Apache-2.0 compatible only" |
| **Versioning & Compatibility** | SemVer commitments, deprecation windows | "Public API backward-compatible for 2 major versions" |
| **Release Process** | Quality gates, sign-off requirements, deploy rules | "Zero open BUGs before release", "Staging deploy precedes prod" |
| **Coordination Rules** | Agent handoff protocols, status tracking | Agent role boundaries, handoff checklists |
| **Documentation** | Required docs, changelog discipline | "All public APIs documented", "Changelog entry per PR" |
| **Incident Response** | Escalation paths, SLA commitments | "P1 acknowledged within 15 minutes", "Post-mortem within 48 hours" |

**FORBIDDEN patterns** in `policy_*` are often security-sensitive: `eval()`, unparameterized SQL, secrets in source, disabled security headers.

**Key signal:** If the constraint exists because of an *external authority* (legal, security, compliance, business rule, process agreement) rather than a technical preference, it belongs in `policy_*`.

### 3.4 Boundary Cases

Some concerns span multiple anchor types. Split them by the nature of the constraint:

| Concern | `arch_*` aspect | `design_*` aspect | `policy_*` aspect |
|---|---|---|---|
| **Accessibility** | Semantic HTML patterns, ARIA attribute conventions | Focus indicator styling, contrast ratios, target sizes | WCAG level commitment, audit schedule |
| **Performance** | Caching strategy, lazy-loading patterns, code splitting | Animation frame budget (60fps), transition limits | Response time SLAs, uptime commitments |
| **Error Handling** | Error class hierarchy, Result types, retry logic | Error message presentation, toast styling, empty states | Error logging requirements, PII redaction in errors |
| **i18n** | String extraction tooling, RTL layout support, locale detection | Locale-specific typography, date format display | Legally required supported languages |
| **Authentication** | Auth library choice, token storage pattern, session management | Login form design, password strength indicator | Session timeout policy, MFA requirements, audit trail |

**Heuristic:** When unsure, ask: "Who would object if this constraint were violated?"
- A developer reviewing code quality → `arch_*`
- A designer reviewing the UI → `design_*`
- A compliance officer, security auditor, or manager reviewing process → `policy_*`

### 3.5 One Anchor, One Domain

Each anchor node covers **one coherent domain** — not one per concern. Prefer fewer, broader anchors over many narrow ones.

Good: `arch_data_layer.md` (covers ORM choice, migration rules, query patterns, caching)
Bad: `arch_orm.md`, `arch_migrations.md`, `arch_queries.md`, `arch_cache.md`

Good: `design_visual_standards.md` (covers colors, typography, spacing, themes)
Bad: `design_colors.md`, `design_fonts.md`, `design_spacing.md`

Split an anchor only when it grows beyond ~150 lines or when two genuinely independent domains are forced together (e.g., "API contracts" and "logging conventions" serve different audiences and change for different reasons).
