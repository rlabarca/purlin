# Design: Purlin Visual Standards

> Label: "Design: Visual Standards"
> Category: "Common Design Standards"

## 1. Purpose
Defines the visual language for all Purlin-branded web tools (CDD Monitor, Software Map). This anchor node establishes color tokens, typography, theme switching behavior, and logo placement that all visual tool features MUST adhere to.

## 2. Invariants

### 2.1 Brand Identity
*   **Name:** Purlin
*   **Tagline:** Continuous Design-Driven Development Framework
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
| `--font-display` | `'Montserrat', sans-serif` | Titles, wordmarks |
| `--font-body` | `'Inter', sans-serif` | Headers, labels, body |

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
| `--font-display` | `'Montserrat', sans-serif` |
| `--font-body` | `'Inter', sans-serif` |

### 2.3 Typography

**Font Stacks & Custom Properties:**

| Token | Value | Usage |
|-------|-------|-------|
| `--font-display` | `'Montserrat', sans-serif` | Page titles, tool wordmarks |
| `--font-body` | `'Inter', sans-serif` | Section headers, UI labels, body text |
| (none) | `'Menlo', 'Monaco', 'Consolas', monospace` | Data tables, code blocks, feature file paths |

Both `--font-display` and `--font-body` MUST be defined in both theme blocks (`:root` and `[data-theme='light']`).

**CDN Loading:** Tools MUST load Montserrat (weights 200, 800, 900) and Inter (weights 400, 500, 700) via Google Fonts CDN `<link>` tags.

**Usage Patterns:**

| Element | Font | Weight | Size | Letter-Spacing | Transform |
|---------|------|--------|------|----------------|-----------|
| Tool wordmark / page title | Montserrat | 200 (ExtraLight) | 32-40px | `0.12em` (wide) | `uppercase` |
| Section headers | Inter | 700 (Bold) | 14px | `0.1em` (wide) | `uppercase` |
| Captions / sub-labels | Inter | 700 (Bold) | 10px | `0.1em` (wide) | `uppercase` |
| Body text | Inter | 400 (Regular) | 14px | normal | None |
| UI labels / metadata | Inter | 500 (Medium) | 12-14px | normal | None |
| Tag text | Inter | 700 (Bold) | 12px | normal | None |
| Monospace data | Menlo stack | 400 | 12px | normal | None |

The wide letter-spacing on uppercase elements is a defining characteristic of the Purlin visual language. Tool wordmarks and page titles MUST match the SVG logo treatment (`assets/purlin-logo.svg`): Montserrat ExtraLight 200, wide tracking `0.12em`, uppercase. The thin strokes with generous spacing create an architectural, blueprint-like feel.

### 2.4 Theme Switching
*   **Default:** Dark (Blueprint).
*   **Toggle:** Sun/moon icon in top-right of page header.
*   **Persistence:** `localStorage` key `purlin-theme`, value `light` or `dark`.
*   **Application:** `:root` defines dark theme defaults. `[data-theme='light']` on `<html>` overrides to light values.
*   **FOUC Prevention:** An early synchronous `<script>` in `<head>` reads localStorage and applies the `data-theme` attribute before first paint. This is critical for CDD's 5-second meta-refresh cycle.

### 2.5 Logo Placement
*   Top-left of every tool header, approximately 24px height, adjacent to tool title.
*   Logo uses CSS classes for theme-responsive fill colors.

### 2.6 Project Name Display
*   **Source (resolution order):**
    1.  The `project_name` key in `.agentic_devops/config.json` (preferred).
    2.  If the key is absent or empty, fall back to the **directory name** of the project root (i.e., the last path component, not the full path). For example, if the project root is `/home/user/my-app`, the displayed name is `my-app`.
*   **Position:** Displayed on a second line below the tool title in the page header left group, left-justified. The left edge of the project name text MUST align horizontally with the left edge of the "P" in the PURLIN title above it (i.e., the project name sits directly under the title text, not under the logo).
*   **Font:** `var(--font-body)` (Inter), weight 500 (Medium), same size as body text (14px). No text-transform.
*   **Color:** `var(--purlin-primary)` -- the same token used for the logo triangle main fill (`.logo-fill`). This ensures the project name color matches the logo and switches correctly between Blueprint (dark) and Architect (light) themes.

### 2.7 FORBIDDEN Patterns
*   Hardcoded hex colors in tool CSS (MUST use `var(--purlin-*)` custom properties).
*   Inline style color values that bypass the token system.

## 3. Implementation Notes
*   Consumer projects MAY override these standards in their own `design_*.md` anchor node.
*   The standalone logo SVG (`assets/purlin-logo.svg`) uses dark-theme hex defaults. When embedded inline in tool HTML, the SVG elements use CSS classes that respond to the `data-theme` attribute for theme-responsive colors.
*   The FOUC prevention script must be placed before any `<link>` stylesheet tags to ensure the correct theme is applied before CSS renders.
