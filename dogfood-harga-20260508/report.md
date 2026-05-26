# Dogfood Report: Harga v5 (Flask Pricing Tool)

| Field | Value |
|-------|-------|
| **Date** | 2026-05-08 |
| **App URL** | http://0.0.0.0:3637 |
| **Session** | harga-20260508 |
| **Scope** | Full app: all pages, features, text input alignment, design spec compliance |

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| **Total** | **0 (2 fixed)** |

## Issues

### ISSUE-001: ~~JS Syntax Error — Unescaped apostrophe breaks all frontend interactions~~ **FIXED**

| Field | Value |
|-------|-------|
| **Severity** | high |
| **Category** | functional / console |
| **Status** | **FIXED** |

Root cause: unescaped apostrophe in `what's` inside a single-quoted string on the `out_of_domain` error case. Escaped to `what\'s`. JS syntax verified clean. All buttons working after fix.

---

### ISSUE-002: ~~All core buttons non-functional~~ **FIXED** (resolved by ISSUE-001 fix)

| Field | Value |
|-------|-------|
| **Severity** | high |
| **Category** | functional |
| **Status** | **FIXED** |

**Verification after fix:**
- **"chats" button** — Shows sessions overlay with chat history ✓
- **"import" button** — Shows CREMA import sheet with 265 tenders ✓
- **"harga" button** — Submits "harga besi 12mm", transitions to chat, returns RM35.00 pricing data ✓
- **Dynamic buttons** — "Add to bid" and "View sources" render after API response ✓
- **Keyboard shortcuts** — Ctrl+K/Ctrl+I/Ctrl+Shift+C all functional ✓

---

### ISSUE-003: Light theme instead of dark theme (design spec violation)

| Field | Value |
|-------|-------|
| **Severity** | medium |
| **Category** | visual |
| **URL** | http://0.0.0.0:3637/ |
| **Repro Video** | N/A |

**Description**

The DESIGN.md ("Harga — Commerce Chat Design Document" section "Visual Identity") specifies:

> **Dark theme** — `#000` background, `#fff` text, single accent (`#0a84ff` blue)

The actual implementation uses a light theme:

```css
body { background: #fff; color: #1a1a1a; /* ... */ }
```

This is the inverse of the spec. The `#000` color is only used on the "harga" button (`btn-harga { background: #000 }`), not for the page background. While the user said not to fret about component arrangement, a complete theme inversion is a meaningful deviation from the design spec.

---

### ISSUE-004: Missing welcome screen components (design spec violation)

| Field | Value |
|-------|-------|
| **Severity** | medium |
| **Category** | ux |
| **URL** | http://0.0.0.0:3637/ |
| **Repro Video** | N/A |

**Description**

The DESIGN.md "User Journey" and "Component Inventory" specify a welcome/landing screen with:

- A centered greeting message
- A 2x2 category grid (quick-category tiles)
- 3 example query chips

The actual landing page (id="landingWrap") contains only:
- A single textarea with placeholder "Ask anything…"
- Two buttons: "harga" and "import"

No greeting, no category tiles, no example chips. The landing is functional but minimal — missing the onboarding context that would help new users understand what to ask.

---

### ISSUE-005: Missing workflow progress indicator (design spec deviation)

| Field | Value |
|-------|-------|
| **Severity** | low |
| **Category** | ux |
| **URL** | http://0.0.0.0:3637/ |
| **Repro Video** | N/A |

**Description**

The DESIGN.md "Component Inventory" lists a "Workflow progress" component:

> 5-dot commerce stage indicator, 6px dots, blue = active, dim = future

This component is not present in the HTML. The five-stage FSM (discovery → pricing → priced → ready_for_review → approved) is tracked server-side in the session but has no frontend visual indicator. The user has no visibility into which commerce stage they are in during a chat session.

---

## Placeholder Alignment Assessment

The text inputs use `text-align: left` (default for textarea) with `padding: 20px 24px` (landing) / `padding: 18px 20px` (chat). The line-height and padding values center the single-line placeholder text vertically within the input box. The left padding provides proper left alignment. **The dim text "Ask anything…" is correctly aligned left-center.**

However, there is no custom `::placeholder` CSS pseudo-element styling — it uses the browser default gray color rather than a styled dim appearance.
