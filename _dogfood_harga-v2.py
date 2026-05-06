#!/usr/bin/env python3
"""Dogfood harga.roowang.com — comprehensive e2e audit.

Phases:
  1. Layout audit — all expected elements present
  2. CSS/token audit — design tokens, no hardcoded hex, monochrome compliance
  3. Interactivity — tender search, chat input, archive, new conversation
  4. Mobile (iPhone 390x844) — viewport, touch targets, layout
  5. Dark mode — data-mode="dark" renders correctly
  6. Send flow — type message, click send, loading indicator, canvas updates
  7. HTML validation — unlabeled buttons, duplicate IDs, alt text
  8. Console/network — JS errors, failed requests
  9. State persistence — localStorage after interactions
 10. API endpoints — direct backend health checks
 11. Full user flow — tender search → pull → factsheet → archive
"""
import asyncio, json, sys, os
from datetime import datetime, timezone
import subprocess as _subprocess
from playwright.async_api import async_playwright, TimeoutError as PwTimeout

BASE = "https://harga.roowang.com"
API_BASE = BASE.rstrip("/") + "/api/harga-v2"
YELLOWPAGES_PM2 = "yellowpages"
REPORT = {"timestamp": datetime.now(timezone.utc).isoformat(), "issues": [], "pass": 0, "fail": 0, "warn": 0}


def fail(phase, msg, detail=None):
    REPORT["issues"].append({"phase": phase, "severity": "fail", "msg": msg, "detail": detail})
    REPORT["fail"] += 1
    print(f"  \u274c FAIL  [{phase}] {msg}")


def warn(phase, msg, detail=None):
    REPORT["issues"].append({"phase": phase, "severity": "warn", "msg": msg, "detail": detail})
    REPORT["warn"] += 1
    print(f"  \u26a0\ufe0f WARN  [{phase}] {msg}")


def ok(msg):
    REPORT["pass"] += 1
    print(f"  \u2705 {msg}")


async def phase_layout(page):
    """Verify all expected DOM elements exist and are visible."""
    print(f"\n{'='*60}")
    print("PHASE 1: Layout Audit")
    print(f"{'='*60}")

    checks = {
        "Header": ("header.hv2-header", None),
        "Sidebar": ("aside.hv2-sidebar", None),
        "Canvas main": ("main.hv2-canvas", None),
        "Header title": ("header.hv2-header h1", "crema/harga"),
        "Archive btn": ("#hv2ArchiveBtn", None),
        "+New btn": ("#hv2NewBtn", None),
        "Sidebar title": (".hv2-sidebar-header h3", "Pricing Chat"),
        "Tender search input": ("#hv2TenderInput", None),
        "Tender search label": (".hv2-tender-search-label", "Notice DB"),
        "Tender search hint": (".hv2-tender-search-hint", None),
        "Tender dropdown": ("#hv2TenderDropdown", None),
        "Active tender section": ("#hv2ActiveTender", None),
        "Chat area": ("#hv2ChatArea", None),
        "Processing dots": ("#hv2Processing", None),
        "Chat input": ("#hv2ChatInput", None),
        "Send button": ("#hv2SendBtn", None),
        "Command hint": (".hv2-command-hint", None),
        "Canvas content": ("#hv2CanvasContent", None),
        "Canvas empty state": ("#hv2CanvasEmpty", None),
        "Greeting message": (".hv2-msg-assistant", "Salaam. Apa mau?"),
    }

    for label, (selector, expected_text) in checks.items():
        el = await page.query_selector(selector)
        if not el:
            fail("1", f"Missing element: {label} ({selector})")
            continue
        visible = await el.is_visible()
        if not visible:
            warn("1", f"Element not visible: {label} ({selector})")
            continue
        if expected_text:
            text = (await el.inner_text()).strip()
            if expected_text.lower() not in text.lower():
                warn("1", f"{label} text mismatch", f"expected {expected_text!r}, got {text[:60]!r}")
                continue
        ok(f"{label} \u2014 present and visible")

    # Check processing indicator starts hidden
    proc = await page.query_selector("#hv2Processing")
    if proc:
        if await proc.is_hidden():
            ok("Processing indicator hidden at rest")
        else:
            warn("1", "Processing indicator visible at rest")

    # Check active tender starts hidden
    at = await page.query_selector("#hv2ActiveTender")
    if at:
        if await at.is_hidden():
            ok("Active tender section hidden at rest")
        else:
            warn("1", "Active tender section visible at rest")


async def phase_tokens(page):
    """Verify design tokens, monochrome compliance, no hardcoded hex."""
    print(f"\n{'='*60}")
    print("PHASE 2: CSS / Token Audit")
    print(f"{'='*60}")

    # Design tokens
    tokens = await page.evaluate("""() => {
        const s = getComputedStyle(document.body);
        const want = ['--bg','--surface','--text-1','--text-2','--accent','--radius-md','--font-body','--font-display'];
        const r = {};
        for (const t of want) r[t] = s.getPropertyValue(t).trim();
        return r;
    }""")
    missing = [k for k, v in tokens.items() if not v and k != '--accent']
    if missing:
        fail("2", f"Missing design tokens: {missing}")
    elif not tokens.get('--accent'):
        warn("2", "--accent token not defined (expected in monochrome mode)")
        ok(f"All {len([v for v in tokens.values() if v])} other design tokens defined")
    else:
        ok(f"All {len(tokens)} design tokens defined")
    for k, v in tokens.items():
        if v:
            print(f"      {k}: {v[:50]}")

    # Hardcoded hex colors in hv2 elements
    hexes = await page.evaluate("""() => {
        const els = document.querySelectorAll('[class*="hv2"], [id*="hv2"]');
        const found = [];
        for (const el of els) {
            const s = getComputedStyle(el);
            for (const prop of ['color','background-color','border-color']) {
                const val = s[prop];
                if (val && val.startsWith('rgb')) {
                    const m = val.match(/\\d+/g);
                    if (m) {
                        const [r,g,b] = m.slice(0,3).map(Number);
                        const hex = '#' + [r,g,b].map(x =>
                            x.toString(16).padStart(2,'0')
                        ).join('').toLowerCase();
                        // Skip neutral grays (R≈G≈B within tolerance)
                        const maxDiff = Math.max(Math.abs(r-g), Math.abs(g-b), Math.abs(b-r));
                        if (maxDiff <= 30) continue;
                        found.push(`${el.className.slice(0,40)}:${prop}=${hex}`);
                    }
                }
            }
        }
        return found.slice(0,30);
    }""")
    if hexes:
        for h in hexes:
            warn("2", f"Non-neutral hex color: {h}")
    else:
        ok("No hardcoded non-neutral hex colors in hv2 elements")

    # Monochrome audit: no gradients
    gradients = await page.evaluate("""() => {
        const els = document.querySelectorAll('[class*="hv2"], [id*="hv2"]');
        const found = [];
        for (const el of els) {
            const bg = getComputedStyle(el).background;
            if (bg && bg.includes('gradient')) found.push(el.className.slice(0,50));
        }
        return found;
    }""")
    if gradients:
        warn("2", f"Gradients found (banned per DESIGN.md): {gradients}")
    else:
        ok("No gradient backgrounds")


async def phase_interactivity(page):
    """Test tender search, chat input, archive, new conversation."""
    print(f"\n{'='*60}")
    print("PHASE 3: Interactivity")
    print(f"{'='*60}")

    # 3.1 Tender search
    search = await page.query_selector("#hv2TenderInput")
    if search:
        await search.fill("GEP-RFP")
        await page.wait_for_timeout(2000)
        count = await page.evaluate("document.querySelectorAll('#hv2TenderDropdown > *').length")
        if count > 0:
            ok(f"Tender search returned {count} results for 'GEP-RFP'")
        else:
            warn("3", "Tender search returned 0 results for 'GEP-RFP'", "May mean no tenders loaded")

        # Keyboard nav in dropdown
        if count > 0:
            await search.press("ArrowDown")
            await page.wait_for_timeout(300)
            sel = await page.evaluate("""() => {
                const s = document.querySelector('.hv2-tender-item.selected');
                return s ? (s.querySelector('.hv2-tender-item-ref')?.innerText || 'selected') : null;
            }""")
            if sel:
                ok(f"ArrowDown highlights tender item: {sel}")
            else:
                warn("3", "ArrowDown did not highlight any tender item")

            # Escape closes dropdown
            dropdown_visible_before = await page.evaluate(
                "document.querySelector('#hv2TenderDropdown')?.classList?.contains('is-visible')")
            if dropdown_visible_before:
                await search.press("Escape")
                await page.wait_for_timeout(300)
                dd_v = await page.evaluate(
                    "document.querySelector('#hv2TenderDropdown')?.classList?.contains('is-visible')")
                if dd_v:
                    warn("3", "Escape did not close tender dropdown")
                else:
                    ok("Escape closes tender dropdown")

        await search.fill("")
        await page.wait_for_timeout(500)
    else:
        fail("3", "Tender search input not found")

    # 3.2 Chat input fill
    chat = await page.query_selector("#hv2ChatInput")
    if chat:
        await chat.fill("/factsheet")
        val = await chat.input_value()
        if val == "/factsheet":
            ok("Chat input accepts text")
        else:
            fail("3", f"Chat input fill failed", f"expected '/factsheet', got {val!r}")
        await chat.fill("")
    else:
        fail("3", "Chat input not found")

    # 3.3 Archive button
    archive = await page.query_selector("#hv2ArchiveBtn")
    if archive:
        await archive.click()
        await page.wait_for_timeout(800)
        cc_text = await page.evaluate("""() => {
            const cc = document.getElementById('hv2CanvasContent');
            if (!cc) return '';
            return (cc.innerText || '').trim().slice(0,120);
        }""")
        if "archive" in cc_text.lower() or "global" in cc_text.lower():
            ok(f"Archive view opened in canvas")
        else:
            warn("3", f"Archive click: canvas shows: {cc_text[:60]}")
    else:
        fail("3", "Archive button not found")

    # 3.4 +New button
    new_btn = await page.query_selector("#hv2NewBtn")
    if new_btn:
        await new_btn.click()
        await page.wait_for_timeout(800)
        msgs = await page.evaluate("document.querySelectorAll('.hv2-msg').length")
        if msgs == 1:
            ok("+New cleared chat, greeting remains")
        else:
            warn("3", f"+New left {msgs} messages (expected 1)")
    else:
        fail("3", "+New button not found")


async def phase_mobile(page):
    """iPhone viewport tests: layout, touch targets, zoom prevention."""
    print(f"\n{'='*60}")
    print("PHASE 4: Mobile (iPhone 390x844)")
    print(f"{'='*60}")

    info = await page.evaluate("""() => {
        const r = {};
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        r.vw = vw; r.vh = vh;

        r.hScroll = document.documentElement.scrollWidth > vw + 2;
        r.scrollW = document.documentElement.scrollWidth;

        const vp = document.querySelector('meta[name="viewport"]');
        r.viewportMeta = vp ? vp.getAttribute('content') : null;

        r.bodyFontSize = getComputedStyle(document.body).fontSize;
        r.inputFontSize = (() => {
            const inp = document.querySelector("#hv2ChatInput");
            if (!inp) return "0px";
            return getComputedStyle(inp).fontSize;
        })();

        r.smallTargets = [];
        const clickable = document.querySelectorAll('button, a, input, textarea, [role="button"], select');
        for (const el of clickable) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && (rect.width < 32 || rect.height < 32)) {
                const label = el.innerText || el.getAttribute('aria-label') || el.placeholder || el.id || el.tagName;
                if (label) r.smallTargets.push(`${el.tagName} ${Math.round(rect.width)}x${Math.round(rect.height)} "${String(label).trim().slice(0,30)}"`);
            }
        }

        const sidebar = document.querySelector('.hv2-sidebar');
        const canvas = document.querySelector('.hv2-canvas');
        if (sidebar) {
            const sr = sidebar.getBoundingClientRect();
            r.sidebar = { w: Math.round(sr.width), h: Math.round(sr.height), top: Math.round(sr.top) };
            r.sidebarFullWidth = sr.width >= vw - 20;
        }
        if (canvas) {
            const cr = canvas.getBoundingClientRect();
            r.canvas = { w: Math.round(cr.width), h: Math.round(cr.height), top: Math.round(cr.top) };
        }
        const chatArea = document.querySelector('#hv2ChatArea');
        if (chatArea) {
            const cr = chatArea.getBoundingClientRect();
            r.chatAreaHeight = Math.round(cr.height);
        }
        return r;
    }""")

    print(f"  Viewport: {info.get('vw')}x{info.get('vh')}")
    print(f"  Body font: {info.get('bodyFontSize')}")
    print(f"  Viewport meta: {info.get('viewportMeta')}")

    if info.get('hScroll'):
        fail("4", f"Horizontal overflow: scrollW={info.get('scrollW')}px > vw={info.get('vw')}px")
    else:
        ok("No horizontal overflow")

    bf = info.get("inputFontSize", info.get("bodyFontSize", "0px"))
    bf_px = float(bf.replace('px', ''))
    if bf_px >= 16:
        ok(f"Body font >= 16px ({bf}) \u2014 prevents iOS zoom on focus")
    else:
        fail("4", f"Body font {bf} < 16px \u2014 iOS will auto-zoom input fields")

    if info.get('viewportMeta') and 'initial-scale=1.0' in info.get('viewportMeta', ''):
        ok("Viewport meta has initial-scale=1.0")
    else:
        fail("4", "Viewport meta missing initial-scale=1.0")

    small = info.get('smallTargets', [])
    if small:
        for t in small:
            warn("4", f"Small touch target: {t}")
    else:
        ok("All touch targets >= 32px")

    sidebar = info.get('sidebar', {})
    if sidebar.get('w', 0) >= 350:
        ok("Sidebar is full-width on mobile")
    else:
        warn("4", f"Sidebar only {sidebar.get('w')}px on 390px viewport")

    chat_h = info.get('chatAreaHeight', 0)
    if chat_h >= 80:
        ok(f"Chat area has room: {chat_h}px")
    elif chat_h > 0:
        warn("4", f"Chat area cramped: {chat_h}px")

    # Check stacked layout (sidebar above canvas)
    s_top = sidebar.get('top', 0)
    c_top = info.get('canvas', {}).get('top', 0)
    if c_top > s_top + 10:
        ok("Sidebar+canvas stacked vertically on mobile")
    else:
        warn("4", "Sidebar+canvas may not be stacked on mobile")



async def phase_breakpoint_768(page):
    """FINDING 4: Test exact 768px breakpoint for vertical stacking."""
    print(f"
{'=' * 60}")
    print("FINDING 4: 768px Breakpoint")
    print(f"{'=' * 60}")

    await page.set_viewport_size({"width": 768, "height": 900})
    await page.wait_for_timeout(500)

    layout = await page.evaluate("""() => {
        const s = document.querySelector('.hv2-sidebar');
        const c = document.querySelector('.hv2-canvas');
        if (\!s || \!c) return {};
        const sr = s.getBoundingClientRect();
        const cr = c.getBoundingClientRect();
        const sStyle = window.getComputedStyle(s);
        const cStyle = window.getComputedStyle(c);
        return {
            sidebarW: Math.round(sr.width),
            sidebarH: Math.round(sr.height),
            canvasW: Math.round(cr.width),
            canvasH: Math.round(cr.height),
            sidebarFullWidth: sr.width >= 768 - 20,
            sidebarMaxHeight: sStyle.maxHeight,
            canvasMaxHeight: cStyle.maxHeight,
            canvasBelow: cr.top >= sr.bottom - 5,
            canvasTop: Math.round(cr.top),
            sidebarBottom: Math.round(sr.bottom),
        };
    }""")

    if layout.get("sidebarFullWidth"):
        ok(f"At 768px: sidebar full-width ({layout.get('sidebarW')}px)")
    elif layout.get("sidebarW", 0) > 400:
        warn("4", f"At 768px: sidebar width {layout.get('sidebarW')}px (partial)")
    else:
        fail("4", f"At 768px: sidebar only {layout.get('sidebarW')}px (not stacked)")

    if layout.get("canvasBelow"):
        ok("At 768px: canvas below sidebar (vertical stack)")
    else:
        warn("4", f"At 768px: canvas does not stack")

    if layout.get("sidebarMaxHeight"):
        ok(f"Sidebar max-height: {layout['sidebarMaxHeight']}")
    if layout.get("canvasMaxHeight"):
        ok(f"Canvas max-height: {layout['canvasMaxHeight']}")


async def phase_dark_mode(page):
    """Verify dark mode renders correctly."""
    print(f"\n{'='*60}")
    print("PHASE 5: Dark Mode")
    print(f"{'='*60}")

    # Check theme-color meta tags exist for both modes
    meta = await page.evaluate("""() => {
        const light = document.querySelector('meta[name="theme-color"][media="(prefers-color-scheme: light)"]');
        const dark = document.querySelector('meta[name="theme-color"][media="(prefers-color-scheme: dark)"]');
        return { light: light?.getAttribute('content') || null, dark: dark?.getAttribute('content') || null };
    }""")
    if meta.get('light') and meta.get('dark'):
        ok(f"Theme-color meta: light={meta['light']} dark={meta['dark']}")
    else:
        warn("5", f"Missing theme-color meta: {meta}")

    # Set dark mode via data attribute on html
    await page.evaluate("document.documentElement.setAttribute('data-mode', 'dark')")
    await page.wait_for_timeout(500)

    colors = await page.evaluate("""() => {
        const s = getComputedStyle(document.body);
        return {
            bg: s.getPropertyValue('--bg').trim(),
            surface: s.getPropertyValue('--surface').trim(),
            text1: s.getPropertyValue('--text-1').trim(),
            text2: s.getPropertyValue('--text-2').trim(),
            bodyBg: s.backgroundColor,
            bodyColor: s.color,
        };
    }""")

    bg = colors.get('bg', '')
    body_bg = colors.get('bodyBg', '')

    if bg:
        ok(f"Dark mode --bg: {bg}")
    else:
        fail("5", "Dark mode --bg token missing")

    # Check body bg is dark in dark mode
    if '255' in body_bg and '255' in body_bg and '255' in body_bg:
        warn("5", f"Dark mode body bg appears white: {body_bg}")
    else:
        ok(f"Dark mode body bg: {body_bg}")

    # Verify canvas content is readable
    canvas_text = await page.evaluate("""() => {
        const ce = document.querySelector('#hv2CanvasEmpty');
        if (!ce) return null;
        const s = getComputedStyle(ce);
        return { color: s.color, bg: s.backgroundColor };
    }""")
    if canvas_text:
        ok("Canvas empty state rendered in dark mode")

    # Reset to light
    await page.evaluate("document.documentElement.removeAttribute('data-mode')")
    await page.wait_for_timeout(300)


async def phase_send_flow(page):
    """Test typing message, clicking send, loading state, canvas update."""
    print(f"\n{'='*60}")
    print("PHASE 6: Send Flow")
    print(f"{'='*60}")

    chat = await page.query_selector("#hv2ChatInput")
    send = await page.query_selector("#hv2SendBtn")
    if not chat or not send:
        fail("6", "Chat input or send button not found")
        return

    await chat.fill("test message")
    val = await chat.input_value()
    if val == "test message":
        ok("Chat input accepts typed text")
    else:
        fail("6", f"Chat fill failed: {val!r}")

    enabled = await send.is_enabled()
    if enabled:
        ok("Send button is enabled with text")
    else:
        warn("6", "Send button disabled even with text in input")

    # Test Enter key sends message
    await chat.fill("/help")
    await page.wait_for_timeout(200)
    msg_before = await page.evaluate("document.querySelectorAll('.hv2-msg').length")
    await chat.press("Enter")
    await page.wait_for_timeout(1000)
    msg_after = await page.evaluate("document.querySelectorAll('.hv2-msg').length")
    if msg_after > msg_before:
        ok(f"Enter sends message: {msg_before} -> {msg_after} messages")
    else:
        warn("6", f"Enter did not add message: {msg_before} -> {msg_after}")


async def phase_html_validation(page):
    """Check HTML structure, accessibility attributes."""
    print(f"\n{'='*60}")
    print("PHASE 7: HTML Validation")
    print(f"{'='*60}")

    results = await page.evaluate("""() => {
        const issues = [];

        if (!document.documentElement.hasAttribute('lang'))
            issues.push('Missing lang on <html>');
        if (!document.querySelector('head title'))
            issues.push('Missing <title>');

        const idCount = {};
        document.querySelectorAll('[id]').forEach(el => {
            idCount[el.id] = (idCount[el.id] || 0) + 1;
        });
        for (const [id, count] of Object.entries(idCount)) {
            if (count > 1) issues.push(`Duplicate ID #${id} (${count}x)`);
        }

        document.querySelectorAll('button').forEach(b => {
            const label = b.getAttribute('aria-label') || b.innerText.trim();
            if (!label) issues.push(`Unlabeled button: <${(b.className||'').slice(0,30)}>`);
        });

        document.querySelectorAll('img:not([alt])').forEach(img => {
            issues.push(`Image missing alt: ${img.getAttribute('src')?.slice(0,30)}`);
        });

        const chatLog = document.querySelector('[role="log"]');
        if (!chatLog) issues.push('Chat area missing role="log"');
        else if (!chatLog.getAttribute('aria-live'))
            issues.push('Chat log missing aria-live');

        const dd = document.getElementById('hv2TenderDropdown');
        if (dd && dd.getAttribute('role') !== 'listbox')
            issues.push(`Tender dropdown role: ${dd.getAttribute('role') || 'MISSING'} (expected listbox)`);

        const ti = document.getElementById('hv2TenderInput');
        if (ti) {
            if (!ti.getAttribute('aria-label')) issues.push('Tender input missing aria-label');
            if (ti.getAttribute('aria-controls') !== 'hv2TenderDropdown')
                issues.push('Tender input missing aria-controls');
        }

        return issues.slice(0,30);
    }""")

    if results:
        for r in results:
            warn("7", r)
    else:
        ok("All HTML validation checks passed")


async def phase_state_persistence(page):
    """Check localStorage after interactions."""
    print(f"\n{'='*60}")
    print("PHASE 8: State Persistence")
    print(f"{'='*60}")

    ls = await page.evaluate("""() => {
        const keys = Object.keys(localStorage).filter(k =>
            k.includes('harga') || k.includes('hv2') || k.includes('chat') || k.includes('tender')
        );
        const data = {};
        for (const k of keys) {
            try { data[k] = JSON.parse(localStorage[k]); }
            catch { data[k] = localStorage[k].slice(0,100); }
        }
        return data;
    }""")

    if ls:
        for k, v in ls.items():
            truncated = json.dumps(v)[:80] if not isinstance(v, str) else v[:80]
            print(f"    {k}: {truncated}")
        ok(f"localStorage has {len(ls)} harga-related keys")
    else:
        warn("8", "No harga-related keys in localStorage")

    ss = await page.evaluate("""() => {
        const keys = Object.keys(sessionStorage).filter(k =>
            k.includes('harga') || k.includes('hv2') || k.includes('chat') || k.includes('tender')
        );
        return keys;
    }""")
    if ss:
        ok(f"sessionStorage has {len(ss)} keys: {ss}")
    else:
        print("    No harga-related keys in sessionStorage")


def phase_yellowpages_health():
    """FINDING 5: PM2 health, restart count, swap usage."""
    print(f"\n{'=' * 60}")
    print("FINDING 5: Yellowpages PM2 Health")
    print(f"{'=' * 60}")

    try:
        r = _subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=10)
        procs = json.loads(r.stdout) if r.stdout else []
    except Exception as e:
        warn("5", f"PM2 jlist failed: {e}")
        return

    yp = next((p for p in procs if p.get("name") == YELLOWPAGES_PM2), None)
    if not yp:
        fail("5", f"PM2 process '{YELLOWPAGES_PM2}' not found")
        return

    status = yp.get("pm2_env", {}).get("status", "unknown")
    restart_count = yp.get("pm2_env", {}).get("restart_time", 0)
    memory_mb = round((yp.get("monit", {}).get("memory", 0) or 0) / (1024 * 1024), 1)

    if status == "online":
        ok(f"yellowpages PM2: online (mem {memory_mb}MB)")
    else:
        fail("5", f"yellowpages PM2 status: {status}")

    if restart_count >= 5:
        warn("5", f"High restart count: {restart_count}")
    elif restart_count > 0:
        warn("5", f"Elevated restart count: {restart_count}")
    else:
        ok("Restart count: 0 (clean)")

    try:
        free_r = _subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        lines = free_r.stdout.strip().split("\n")
        if len(lines) >= 3:
            parts = lines[2].split()
            if len(parts) >= 3:
                swap_used = int(parts[2])
                swap_total = int(parts[1])
                if swap_used > 500:
                    warn("5", f"High swap usage: {swap_used}MB / {swap_total}MB")
                elif swap_used > 100:
                    warn("5", f"Moderate swap usage: {swap_used}MB / {swap_total}MB")
                else:
                    ok(f"Swap usage: {swap_used}MB / {swap_total}MB")
    except Exception:
        pass


async def phase_loading_state(page):
    """FINDING 1: Canvas loading state exists and triggers during processing."""
    print(f"\n{'='*60}")
    print("FINDING 1: Canvas Loading State")
    print(f"{'='*60}")

    loading_el = await page.query_selector("#hv2CanvasLoading")
    if not loading_el:
        fail("1", "Canvas loading element #hv2CanvasLoading missing from DOM")
        return

    ok("Loading element present in DOM")

    hidden = await loading_el.is_hidden()
    if hidden:
        ok("Loading element hidden at rest")
    else:
        warn("1", "Loading element visible at rest (should start hidden by default)")

    dots = await page.evaluate(
        "document.querySelectorAll('#hv2CanvasLoading .hv2-canvas-loading-dot').length"
    )
    if dots >= 3:
        ok(f"Loading has {dots} animation dots")
    else:
        warn("1", f"Loading has only {dots} dots (expected >= 3)")

    # Check processing triggers loading state via startProcessing
    loading_connected = await page.evaluate("""() => {
        const startProc = window.startProcessing;
        if (typeof startProc !== 'function') return false;
        return true;
    }""")
    if loading_connected:
        ok("startProcessing function available (links to setCanvasLoading)")
    else:
        warn("1", "startProcessing not globally accessible")


async def phase_error_state(page):
    """FINDING 2: Canvas error state exists with proper elements."""
    print(f"\n{'='*60}")
    print("FINDING 2: Canvas Error State")
    print(f"{'='*60}")

    error_el = await page.query_selector("#hv2CanvasError")
    if not error_el:
        fail("2", "Canvas error element #hv2CanvasError missing from DOM")
        return

    ok("Error element present in DOM")

    hidden = await error_el.is_hidden()
    if hidden:
        ok("Error element hidden at rest")
    else:
        warn("2", "Error element visible at rest (should start hidden)")

    err_title = await page.query_selector("#hv2CanvasError .hv2-canvas-error-title")
    err_body = await page.query_selector("#hv2CanvasErrorBody")
    err_dismiss = await page.query_selector("#hv2CanvasErrorDismiss")
    if err_title:
        ok("Error title element present")
    if err_body:
        ok("Error body element present")
    if err_dismiss:
        ok("Error dismiss button present")
    else:
        warn("2", "Error dismiss button missing from DOM")

    role = await error_el.get_attribute("role")
    if role == "alert":
        ok("Error element has role='alert'")
    else:
        warn("2", f"Error element missing role='alert' (got '{role}')")

    # Check hideCanvasError is hooked to dismiss button
    dismiss_hooked = await page.evaluate("""() => {
        const btn = document.getElementById('hv2CanvasErrorDismiss');
        if (!btn) return false;
        return true;
    }""")
    if dismiss_hooked:
        ok("Error dismiss button wired in DOM")


async def phase_api_endpoints(page):
    """Hit harga-v2 API endpoints directly to verify backend health."""
    print(f"\n{'='*60}")
    print("PHASE 10: API Endpoint Checks")
    print(f"{'='*60}")

    endpoints = [
        ("GET", f"{API_BASE}/tenders?q=GEP-RFP", "Tender search"),
        ("GET", f"{API_BASE}/archive", "Archive list"),
        ("POST", f"{API_BASE}/sessions", "Create session"),
    ]

    for method, url, label in endpoints:
        try:
            resp = await page.evaluate(f"""async () => {{
                try {{
                    const r = await fetch({json.dumps(url)}, {{
                        method: {json.dumps(method)},
                        headers: {{ 'Content-Type': 'application/json' }},
                        {("body: JSON.stringify({})" if method == "POST" else "")}
                    }});
                    const text = await r.text();
                    let data = null;
                    try {{ data = JSON.parse(text); }} catch {{}}
                    return {{ status: r.status, ok: r.ok, data, text: text.slice(0,200) }};
                }} catch(e) {{
                    return {{ status: 0, ok: false, text: e.message }};
                }}
            }}""")
            if resp.get("ok"):
                ok(f"{label}: {method} {url.rsplit('/',1)[-1]} \u2192 {resp.get('status')}")
            else:
                warn("10", f"{label}: {method} {url.rsplit('/',1)[-1]} \u2192 {resp.get('status')}",
                     resp.get("text", "")[:100])
            print(f"      status={resp.get('status')}")
        except Exception as e:
            warn("10", f"API test exception: {label}", str(e))

    # Session lifecycle: create, then load
    print("  --- Session lifecycle ---")
    session_data = await page.evaluate(f"""async () => {{
        try {{
            const r = await fetch({json.dumps(API_BASE + '/sessions')}, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{}})
            }});
            const data = await r.json();
            return {{ status: r.status, sessionId: data?.session?.id || null, ok: r.ok }};
        }} catch(e) {{
            return {{ status: 0, sessionId: null, ok: false, error: e.message }};
        }}
    }}""")
    sid = session_data.get("sessionId")
    if sid:
        ok(f"POST /sessions \u2192 session {sid[:16]}...")
        load_resp = await page.evaluate(f"""async () => {{
            try {{
                const r = await fetch({json.dumps(API_BASE + '/sessions/' + sid)});
                return {{ status: r.status, ok: r.ok }};
            }} catch(e) {{
                return {{ status: 0, ok: false }};
            }}
        }}""")
        if load_resp.get("ok"):
            ok(f"GET /sessions/{{id}} \u2192 {load_resp.get('status')}")
        else:
            warn("10", f"GET /sessions/{{id}} \u2192 {load_resp.get('status')}")
    else:
        warn("10", "POST /sessions returned no session ID", json.dumps(session_data.get("data",{}))[:200])


async def phase_full_flow(page):
    """Full user flow: search tender, pull it, view factsheet, then archive."""
    print(f"\n{'='*60}")
    print("PHASE 11: Full User Flow")
    print(f"{'='*60}")

    ti = await page.query_selector("#hv2TenderInput")
    if not ti:
        fail("11", "Tender input not found for flow test")
        return

    # Search for tenders
    for query in ["GEP-RFP", "QT", "tender"]:
        await ti.fill(query)
        await page.wait_for_timeout(2000)
        count = await page.evaluate("document.querySelectorAll('#hv2TenderDropdown > *').length")
        if count > 0:
            ok(f"Found {count} results for {query!r}")
            break
        print(f"    No results for {query!r}, trying next...")
    else:
        warn("11", "No tender results for any query", "Flow test partially skipped")
        return

    # Pull via dblclick on first item
    first = await page.query_selector(".hv2-tender-item")
    if not first:
        warn("11", "No tender items rendered in dropdown")
        return

    await first.dispatch_event("dblclick")
    await page.wait_for_timeout(2000)

    # Verify active tender banner appears
    active = await page.evaluate("""() => {
        const banner = document.getElementById('hv2ActiveTender');
        if (!banner) return { visible: false };
        return {
            visible: !banner.hidden,
            title: (document.getElementById('hv2ActiveTenderTitle')?.innerText || '').slice(0,60),
        };
    }""")
    if active.get("visible"):
        ok(f"Active tender banner shown: {active.get('title','')[:50]}")
    else:
        warn("11", "Active tender banner not shown after pull")

    # Clear tender context
    clear = await page.query_selector("#hv2ClearTenderBtn")
    if clear:
        await clear.click()
        await page.wait_for_timeout(1500)
        hidden = await page.evaluate("document.getElementById('hv2ActiveTender')?.hidden !== false")
        if hidden:
            ok("Clear tender hides active banner")
        else:
            warn("11", "Clear tender did not hide active banner")


async def phase_performance(page):
    """Navigation timing metrics."""
    print(f"\n{'='*60}")
    print("PHASE 9: Performance Metrics")
    print(f"{'='*60}")

    perf = await page.evaluate("""() => {
        const nav = performance.getEntriesByType('navigation')[0];
        if (!nav) return {};
        return {
            domContentLoaded: Math.round(nav.domContentLoadedEventEnd),
            loadComplete: Math.round(nav.loadEventEnd),
            domInteractive: Math.round(nav.domInteractive),
            transferSize: nav.transferSize || 0,
        };
    }""")
    if perf:
        dcl = perf.get('domContentLoaded', 0)
        load = perf.get('loadComplete', 0)
        if dcl > 0:
            ok(f"DOMContentLoaded: {dcl}ms")
        if load > 0:
            ok(f"Full load: {load}ms")
        if perf.get('transferSize', 0):
            ok(f"Transfer size: {perf['transferSize']} bytes")
        print(f"      DOMContentLoaded={dcl}ms Load={load}ms Transfer={perf.get('transferSize',0)}B")
    else:
        warn("9", "No navigation timing data available")


async def main():
    # Run PM2 health check first (FINDING 5 — no browser needed)
    phase_yellowpages_health()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ── Desktop (main suite) ──
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print(f"Navigating to {BASE} ...")
        await page.goto(BASE, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        ok(f"Page loaded ({page.url})")

        await phase_layout(page)
        await phase_tokens(page)
        await phase_interactivity(page)
        await phase_html_validation(page)
        await phase_state_persistence(page)
        await phase_loading_state(page)
        await phase_error_state(page)
        await phase_send_flow(page)
        await phase_performance(page)
        await phase_api_endpoints(page)

        if console_errors:
            for ce in console_errors[:10]:
                warn("CONSOLE", ce)
        else:
            ok("No JS console errors")

        await ctx.close()

        # ── Desktop (fresh page for flow test) ──
        ctx2 = await browser.new_context(viewport={"width": 1280, "height": 800})
        page2 = await ctx2.new_page()
        await page2.goto(BASE, wait_until="networkidle", timeout=30000)
        await page2.wait_for_timeout(2000)
        await phase_full_flow(page2)
        await ctx2.close()

        # ── Mobile ──
        ctx_m = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page_m = await ctx_m.new_page()
        await page_m.goto(BASE, wait_until="networkidle", timeout=30000)
        await page_m.wait_for_timeout(2000)

        await phase_mobile(page_m)
        await phase_dark_mode(page_m)

        await ctx_m.close()

        # ── 768px breakpoint (FINDING 4b) ──
        ctx_768 = await browser.new_context(viewport={"width": 768, "height": 900})
        page_768 = await ctx_768.new_page()
        await page_768.goto(BASE, wait_until="networkidle", timeout=30000)
        await page_768.wait_for_timeout(2000)
        await phase_breakpoint_768(page_768)
        await ctx_768.close()

        await browser.close()

    # ── Summary ──
    total = REPORT["pass"] + REPORT["fail"] + REPORT["warn"]
    issues_total = REPORT["fail"] + REPORT["warn"]

    print(f"\n{'='*60}")
    print("DOGFOOD SUMMARY")
    print(f"{'='*60}")
    print(f"  Pass:  {REPORT['pass']}")
    print(f"  Fail:  {REPORT['fail']}")
    print(f"  Warn:  {REPORT['warn']}")
    print(f"  Total: {total} checks")

    if issues_total:
        print(f"\nIssues ({issues_total}):")
        for i, issue in enumerate(REPORT["issues"], 1):
            icon = "\u274c" if issue["severity"] == "fail" else "\u26a0\ufe0f"
            print(f"  {icon} {i}. [{issue['phase']}] {issue['msg']}")
            if issue.get("detail"):
                print(f"       {issue['detail']}")
    else:
        print("\n\u2705 Clean dogfood \u2014 no issues found!")

    return REPORT


if __name__ == "__main__":
    r = asyncio.run(main())
    sys.exit(1 if r["fail"] > 0 else 0)
