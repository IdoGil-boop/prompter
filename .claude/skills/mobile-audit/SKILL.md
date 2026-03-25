<!-- managed by claude-code-starter -->
---
name: mobile-audit
description: Run a comprehensive mobile compatibility audit on all frontend pages and components. Spawns the mobile-auditor agent to check touch targets, responsive layout, form usability, typography, navigation, and data table display. Produces a structured report at docs/qa/MOBILE_AUDIT.md.
user_invocable: true
---

# Mobile Compatibility Audit

Run a full mobile compatibility audit of the frontend.

## What It Does

Spawns the `mobile-auditor` agent (defined in `.claude/agents/mobile-auditor.md`) which:

1. Reads every page in the frontend pages directory
2. Reads every shared component
3. Greps for known anti-patterns (undersized touch targets, missing input types, physical direction classes)
4. Checks 10 categories: touch targets, responsive layout, typography, forms, navigation, RTL, data tables, performance, empty states, modals
5. Writes a structured audit report to `docs/qa/MOBILE_AUDIT.md`

## How to Run

Launch the mobile-auditor agent with this prompt:

```
Run a complete mobile compatibility audit of the frontend.
Follow the audit procedure in your instructions:
1. Glob all page files and component files
2. Read each file and check against all 10 checklist categories
3. Grep for cross-cutting anti-patterns
4. Write the full audit report to docs/qa/MOBILE_AUDIT.md

Be thorough — check every page and every shared component.
```

## When to Use

- Before a release to verify mobile readiness
- After adding new pages or components
- After UI redesign work
- When QA reports mobile-specific bugs

## Audit Categories

| # | Category | Key Checks |
|---|----------|------------|
| 1 | Touch Targets | min 44x44px, 8px spacing between targets |
| 2 | Responsive Layout | No horizontal overflow, stack on mobile |
| 3 | Typography | min 14px body, 16px inputs (prevent iOS zoom) |
| 4 | Forms | Visible labels, correct inputMode/type, full-width buttons |
| 5 | Navigation | Safe area insets, bottom padding, sticky headers |
| 6 | RTL | Logical properties only (if applicable) |
| 7 | Data Tables | overflow-x-auto, card alternative, column priority |
| 8 | Performance | Pagination, lazy loading, code splitting |
| 9 | Empty/Error States | Centered, sized for mobile, full-width CTAs |
| 10 | Modals | Near full-screen on mobile, scrollable, dismissible |

## Output

Structured report at `docs/qa/MOBILE_AUDIT.md` with:
- Summary table (CRITICAL / HIGH / MEDIUM / LOW counts)
- Findings per page and per component with line numbers
- Cross-cutting grep results
- Prioritized fix recommendations
