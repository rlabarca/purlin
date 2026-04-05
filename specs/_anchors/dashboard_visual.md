# Anchor: dashboard_visual

> Scope: scripts/report/purlin-report.html
> Type: design

## What it does

Defines the visual constants — colors, typography, status indicators, and spacing — for the Purlin dashboard. When required by other specs, it ensures the design system is enforced in one place.

## Rules

- RULE-1: Dark theme background is #0f172a, card background is #1e293b
- RULE-2: Light theme background is #f1f5f9, card background is #ffffff
- RULE-3: Status green is #22c55e, amber is #f59e0b, red is #ef4444, teal accent is #2dd4bf
- RULE-4: Font stack is -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif
- RULE-5: Monospace font stack is "SF Mono", "Fira Code", "Cascadia Code", "JetBrains Mono", Consolas, monospace
- RULE-6: VERIFIED status badge is solid green pill with white text
- RULE-7: PARTIAL status badge is amber outline pill (transparent background, amber border)
- RULE-8: FAIL status badge is solid red pill with white text
- RULE-9: UNTESTED status badge is gray pill with amber text; no-proofs badge (generic) is gray pill at reduced opacity
- RULE-10: Integrity color coding: green at 80%+, amber at 50-79%, red below 50%, gray when null
- RULE-11: All colors and visual constants are defined as CSS custom properties in :root or theme selectors, not hardcoded in component styles

## Proof

- PROOF-1 (RULE-1): Load dashboard in Playwright with dark theme; verify computed background-color of body is #0f172a and card element is #1e293b @e2e
- PROOF-2 (RULE-2): Load dashboard in Playwright with light theme; verify computed background-color of body is #f1f5f9 and card element is #ffffff @e2e
- PROOF-3 (RULE-3): Grep purlin-report.html CSS for --green: #22c55e, --amber: #f59e0b, --red: #ef4444, --teal: #2dd4bf; verify all present
- PROOF-4 (RULE-4): Grep purlin-report.html for the sans-serif font stack; verify it includes -apple-system and Roboto
- PROOF-5 (RULE-5): Grep purlin-report.html for the monospace font stack; verify it includes "SF Mono" and Consolas
- PROOF-6 (RULE-6): Load dashboard with a VERIFIED feature in Playwright; verify .sb-ready element has background-color matching --green and white text @e2e
- PROOF-7 (RULE-7): Load dashboard with a partial feature in Playwright; verify .sb-partial element has transparent background and amber border @e2e
- PROOF-8 (RULE-8): Load dashboard with a FAIL feature in Playwright; verify .sb-fail element has background-color matching --red @e2e
- PROOF-9 (RULE-9): Load dashboard with an UNTESTED feature in Playwright; verify .sb-untested element has gray background and amber text color; verify a separate no-proofs element (.sb-none) has reduced opacity @e2e
- PROOF-10 (RULE-10): Load dashboard with features at integrity 90%, 60%, and 30%; verify green, amber, and red color classes respectively @e2e
- PROOF-11 (RULE-11): Grep purlin-report.html for hardcoded hex colors outside of CSS custom property definitions; verify none exist in component style rules
