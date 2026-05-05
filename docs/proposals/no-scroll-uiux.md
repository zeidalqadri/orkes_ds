# Proposal: No-Scroll UI/UX Refactor for CountBot

**Date:** 2026-04-28
**Status:** Draft

## Problem

The current CountBot UI allows page-level scrolling, which fragments the user's view and breaks the command-center feel of an LLM chat interface. Key navigation elements (sidebar, session list, settings) scroll out of view, forcing the user to scroll back and forth between context and input.

## Goal

Zero page-level scrolling. Everything fits in the viewport. All content areas scroll internally (overflow containers) while the outer frame stays fixed.

## Current Layout (ChatWindow)

```
┌──────────┬──────────────────────────────────────┐
│ Sidebar  │  Session List  │  Chat / Settings    │
│ (120px)  │  (variable w)  │  (fills remaining)  │
│          │                │  ┌──────────────┐   │
│ sessions │                │  │ Chat Header   │   │
│ skills   │                │  ├──────────────┤   │
│ cron     │                │  │ Messages      │   │
│ timeline │                │  │ (scrollable)  │   │
│ settings │                │  │               │   │
│          │                │  ├──────────────┤   │
│          │                │  │ Input Area    │   │
│          │                │  └──────────────┘   │
└──────────┴──────────────────────────────────────┘
```

Settings panels use a `grid-template-columns` layout within the same content area, replacing the chat view. The settings panel body scrolls internally but the page itself can also scroll if content overflows.

### Issues
- **Page scrolls** — browser address bar/compositing layer shifts, breaking immersion
- **Settings panel header scrolls away** — user loses context of which settings section they're in
- **Sidebar collapses/null** — nav items disappear on scroll-down
- **Session list grows unbounded** — pushes chat content or requires manual scroll
- **Inconsistent scroll containers** — some overflow is handled, some leaks to page level

## Proposed Architecture

### 1. Root Layout Lock

```css
html, body, #app {
  height: 100vh;
  overflow: hidden;
}
```

The `#app` div becomes the root flex container:

```css
#app {
  display: flex;
  flex-direction: column;
}
```

### 2. App Shell (No-Scroll Frame)

```
┌──────────────────────────────────────────────┐
│  Top Bar (optional) — 0-40px                 │  fixed
├──────────────────────────────────────────────┤
│  Main Content Area (flex-grow: 1)            │  fills
│  ┌────────┬──────────────────────────────┐   │
│  │ Nav    │ Content Panel                │   │  all
│  │ Sidebar│ (overflow-y: auto)            │   │
│  │ (56-   │                              │   │  internal
│  │ 120px) │                              │   │
│  │        │                              │   │  scroll
│  │        │                              │   │
│  └────────┴──────────────────────────────┘   │
├──────────────────────────────────────────────┤
│  Status Bar / Connection Indicator (optional) │  fixed
└──────────────────────────────────────────────┘
```

- **Nav Sidebar** (left, 56-120px, collapsible): `display: flex; flex-direction: column; height: 100%`. Always visible. Items vertically distributed with space for settings at bottom.
- **Content Panel** (right): `overflow-y: auto; height: 100%`. Handles all scrolling.

### 3. Chat View (within Content Panel)

```
┌──────────────────────────────────┐
│  Chat Header (48-56px)           │  fixed height
│  - session name, actions         │
├──────────────────────────────────┤
│  Messages (flex-grow: 1)         │  overflow-y: auto
│  - auto-scroll to bottom         │  fills remaining
│  - "scroll to bottom" FAB        │  space
│  when scrolled up                │
├──────────────────────────────────┤
│  Input Area (pinned bottom)      │  fixed height
│  - textarea, send, attachments   │
│  - team picker overlay           │
└──────────────────────────────────┘
```

All three zones are within a `display: flex; flex-direction: column` container that is `height: 100%` and `overflow: hidden`. Only the messages area scrolls.

### 4. Settings as Overlay Panel (Not Route Change)

Settings currently replace the chat content entirely (same route, different view). This causes a jarring context switch.

**Proposed:** Settings open as a **slide-in overlay panel** from the right, overlaying the chat content. This keeps chat state visible underneath.

```
┌──────────┬────────────────────────────────────────┐
│ Sidebar  │ Chat View (dimmed)    ┌──────────────┐ │
│          │                       │ Settings      │ │
│          │ [messages]            │ Overlay       │ │
│          │                       │ (overflow-y)  │ │
│          │ [input]               │ Sections:     │ │
│          │                       │ General       │ │
│          │                       │ Providers     │ │
│          │                       │ Memory        │ │
│          │                       │ Skills        │ │
│          │                       │ ...           │ │
│          │                       └──────────────┘ │
└──────────┴────────────────────────────────────────┘
```

- Settings overlay: `position: fixed; right: 0; top: 0; height: 100vh; width: min(640px, 90vw)`
- Backdrop: `position: fixed; inset: 0; background: rgba(0,0,0,0.4)`
- Internal scroll: `.settings-body { overflow-y: auto; flex: 1 }`

### 5. Session List as Slide-Out Drawer

The left session list (between nav sidebar and chat) currently takes variable width and can push chat content.

**Proposed:** Make it a **slide-out drawer** triggered by the Sessions nav icon, or a **resizable split panel** with `max-height: 100%` and internal scroll.

```
┌──────────┬──────────────┬─────────────────────────┐
│ Nav      │ Session      │ Chat                     │
│ Sidebar  │ Drawer       │                          │
│          │ (300-400px,  │                          │
│          │ overflow-y)  │                          │
└──────────┴──────────────┴─────────────────────────┘
```

### 6. Login Page

Login already uses `min-height: 100vh` with a centered card. Minor change: add `overflow: hidden` to prevent any edge-case scroll.

### 7. Responsive / Mobile Behavior

On narrow viewports (<768px):
- Nav sidebar collapses to a bottom tab bar (like mobile apps)
- Session drawer opens as full-width overlay
- Settings overlay opens as full-width
- Chat remains the primary view

### 8. Scroll Position Preservation

When toggling between chat sessions, preserve scroll position using `scrollTop` caching. When returning from settings overlay, restore the exact scroll position of the message list.

## Implementation Phases

### Phase 1: Lock the Root
1. Add `html, body, #app { height: 100vh; overflow: hidden }` to global CSS
2. Set `#app` to `display: flex; flex-direction: column`
3. Audit all components for viewport-height assumptions

### Phase 2: Chat View Fix
1. Make ChatWindow root `display: flex; flex-direction: column; height: 100%`
2. Fix message list to `overflow-y: auto; flex: 1; min-height: 0`
3. Fix input area to fixed bottom (no scroll with messages)
4. Add "scroll to bottom" FAB
5. Add scroll position caching per session

### Phase 3: Settings Overlay
1. Refactor settings from inline content replacement to `position: fixed` overlay
2. Add slide-in animation (translateX)
3. Add backdrop with click-to-close
4. Ensure each settings section scrolls independently

### Phase 4: Session Drawer
1. Refactor session list to slide-out drawer
2. Add animation (translateX)
3. Add resizable width (current drag handle)

### Phase 5: Polish & Edge Cases
1. Mobile responsive — bottom tab bar for nav
2. Keyboard shortcuts for all panel toggles
3. Focus trap in overlays
4. Screen reader support for dynamic panels
5. Performance audit — avoid layout thrashing

## Technical Notes

- **Frontend source:** Currently only `dist/` is in this repo. Source must be built externally or a `src/` directory established. This proposal assumes source access is available.
- **CSS custom properties:** Already present. No new design tokens needed — just layout rules.
- **Vue transitions:** Use `<Transition>` component for slide-in/out animations.
- **No new dependencies:** All achievable with CSS + Vue built-in features.

## Open Questions

1. Should the session list drawer be always-present (resizable) or toggle-only (slide from left)?
2. Should settings overlay have a tabbed sub-navigation (left sidebar inside overlay)?
3. Should the timeline view also be an overlay, or does it need full content panel?
4. What about the security warning banner — where does it live in the locked layout?

## Appendix: No-Scroll Reference Patterns

- **Discord:** Fixed sidebar, channel list, message area scrolls internally
- **Slack:** Same pattern — fixed left rails, internal scroll in content
- **Linear:** Fixed sidebar, scrollable issue list, overlay for detail view
- **Terminal UIs:** Never scroll — content wraps or paginates
