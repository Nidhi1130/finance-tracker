# UI Context

> Note: the source spec does not define a visual design. The tokens below
> are a **proposed default** for a clean, trustworthy finance dashboard.
> Adjust freely — but once changed, keep this file the single source of
> truth. This is logged as an open question in `progress-tracker.md`.

## Theme

Light, calm, and data-first — a clean finance dashboard where numbers and
charts are the focus. Neutral surfaces, restrained accent color, and clear
semantic colors for money direction (income vs. expense). No dark mode for
v1.

## Colors

Defined as CSS custom properties in a global stylesheet (e.g.
`app/globals.css`). All components use these tokens — no hardcoded hex
values in `*.module.css` files.

| Role            | CSS Variable       | Value     |
| --------------- | ------------------ | --------- |
| Page background | `--bg-base`        | `#f7f8fa` |
| Surface         | `--bg-surface`     | `#ffffff` |
| Primary text    | `--text-primary`   | `#111827` |
| Muted text      | `--text-muted`     | `#6b7280` |
| Primary accent  | `--accent-primary` | `#2563eb` |
| Border          | `--border-default` | `#e5e7eb` |
| Error / expense | `--state-error`    | `#dc2626` |
| Success/ income | `--state-success`  | `#16a34a` |

Semantic money colors: use `--state-success` for income and
`--state-error` for expense consistently across the transaction list, the
summary cards, and the charts.

## Typography

| Role      | Font                                    | Variable      |
| --------- | --------------------------------------- | ------------- |
| UI text   | Inter (or system UI stack)              | `--font-sans` |
| Code/mono | ui-monospace / system mono              | `--font-mono` |

Load `--font-sans` via `next/font` for performance. Numbers/amounts should
use tabular figures so columns align.

## Border Radius

| Context           | Token / Class     |
| ----------------- | ----------------- |
| Inline / small UI | `--radius-sm` (6px)  |
| Cards / panels    | `--radius-md` (10px) |
| Modals / overlays | `--radius-lg` (14px) |

## Component Library

No component library — components are hand-written with **CSS Modules**.
Each component owns a scoped `ComponentName.module.css` imported as
`styles` and applied via `className={styles.myClass}`. Charts use
**Recharts**. Keep shared primitives (Button, Input, Card, Modal) in
`components/` and reuse them rather than restyling per page.

## Layout Patterns

- App shell: top navbar with a bottom border, main content area below.
- Dashboard: responsive grid of summary cards on top, charts below (donut
  for category breakdown, line/bar for over-time).
- Transaction list: table/list with inline filter controls (date range,
  type, category, account) above it.
- Forms (create/edit transaction): centered card or a modal overlay with a
  backdrop.
- Sidebars (if used): fixed width with a border separator.

## Icons

Lucide React — stroke-based icons only. Sizes: `h-4 w-4` equivalent for
inline (16px), `h-5 w-5` equivalent for buttons (20px). Define sizes via
tokens/classes rather than inline magic numbers where practical.
