# Design: Purlin Visual Standards

> Label: "Design: Visual Standards"
> Category: "Common Design Standards"

## 1. Purpose
Defines the visual language for all Purlin-branded web tools (CDD Monitor, Software Map). This anchor node establishes color tokens, typography, theme switching behavior, and logo placement that all visual tool features MUST adhere to.

## 2. Invariants

### 2.1 Brand Identity
*   **Name:** Purlin
*   **Tagline:** Agentic Development Framework
*   **Logo:** `assets/purlin-logo.svg` -- standalone SVG with dark-theme defaults. When embedded inline in tools, uses CSS classes for theme-responsive fills.

### 2.2 Color Token System
All tool CSS MUST use `var(--purlin-*)` custom properties. Hardcoded hex colors are FORBIDDEN.

**Architect Theme (Light):**

| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-bg` | `#F5F6F0` | Page background |
| `--purlin-surface` | `#FFFFFF` | Card/panel backgrounds |
| `--purlin-primary` | `#0C2637` | Headings, primary text |
| `--purlin-accent` | `#0284C7` | Links, focus rings |
| `--purlin-muted` | `#64748B` | Secondary text |
| `--purlin-border` | `#E2E8F0` | Borders, separators |
| `--purlin-status-good` | `#059669` | DONE/CLEAN |
| `--purlin-status-todo` | `#D97706` | TODO/WIP |
| `--purlin-status-warning` | `#EA580C` | Warning states |
| `--purlin-status-error` | `#DC2626` | FAIL/INFEASIBLE |
| `--purlin-tag-fill` | `#F1F5F9` | Tag backgrounds |
| `--purlin-tag-outline` | `#CBD5E1` | Tag borders |

**Blueprint Theme (Dark -- Default):**

| Token | Value |
|-------|-------|
| `--purlin-bg` | `#0B131A` |
| `--purlin-surface` | `#162531` |
| `--purlin-primary` | `#E2E8F0` |
| `--purlin-accent` | `#38BDF8` |
| `--purlin-muted` | `#94A3B8` |
| `--purlin-border` | `#1E293B` |
| `--purlin-status-good` | `#34D399` |
| `--purlin-status-todo` | `#FCD34D` |
| `--purlin-status-warning` | `#FB923C` |
| `--purlin-status-error` | `#F87171` |
| `--purlin-tag-fill` | `#1E293B` |
| `--purlin-tag-outline` | `#334155` |

### 2.3 Typography
*   **Display:** `'Montserrat', sans-serif` -- headings, titles. Loaded via Google Fonts CDN. Weights: 700, 900.
*   **Body:** `'Inter', sans-serif` -- UI labels, text. Loaded via Google Fonts CDN. Weights: 400, 500.
*   **Code:** `'Menlo', 'Monaco', 'Consolas', monospace` -- data tables, code blocks, feature file paths.
*   Tools MUST load Montserrat (weight 700, 900) and Inter (weight 400, 500) via CDN `<link>` tags.

### 2.4 Theme Switching
*   **Default:** Dark (Blueprint).
*   **Toggle:** Sun/moon icon in top-right of page header.
*   **Persistence:** `localStorage` key `purlin-theme`, value `light` or `dark`.
*   **Application:** `:root` defines dark theme defaults. `[data-theme='light']` on `<html>` overrides to light values.
*   **FOUC Prevention:** An early synchronous `<script>` in `<head>` reads localStorage and applies the `data-theme` attribute before first paint. This is critical for CDD's 5-second meta-refresh cycle.

### 2.5 Logo Placement
*   Top-left of every tool header, approximately 24px height, adjacent to tool title.
*   Logo uses CSS classes for theme-responsive fill colors.

### 2.6 FORBIDDEN Patterns
*   Hardcoded hex colors in tool CSS (MUST use `var(--purlin-*)` custom properties).
*   Inline style color values that bypass the token system.

## 3. Implementation Notes
*   Consumer projects MAY override these standards in their own `design_*.md` anchor node.
*   The standalone logo SVG (`assets/purlin-logo.svg`) uses dark-theme hex defaults. When embedded inline in tool HTML, the SVG elements use CSS classes that respond to the `data-theme` attribute for theme-responsive colors.
*   The FOUC prevention script must be placed before any `<link>` stylesheet tags to ensure the correct theme is applied before CSS renders.
