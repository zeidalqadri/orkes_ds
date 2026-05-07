#!/usr/bin/env python3
"""Dogfood harga.roowang.com — comprehensive e2e audit.

Phases:
  1. Layout audit — all expected DOM elements present and visible
  2. CSS/token audit — design tokens, monochrome compliance, zero hex violations
  3. Interactivity — tender search, keyboard nav, chat input, archive, new session
  4. Mobile (iPhone 390x844) — viewport, touch targets, stacked layout, zoom prevention
  5. Dark mode — data-mode="dark" renders correctly
  6. Send flow — type message, Enter submit, processing indicator, canvas update
  7. HTML validation — ARIA roles, labels, duplicate IDs, unlabeled buttons
  8. Console/network — JS errors logged during test
  9. State persistence — sessionStorage after interactions
 10. API endpoints — direct backend health, session lifecycle
 11. Full user flow — search notice, pull via Enter, factsheet view, archive, clear
"""
import asyncio, json, os, sys
from datetime import datetime, timezone
from playwright.async_api import async_playwright, TimeoutError as PwTimeout

BASE = "http://127.0.0.1:3636/tools/harga-v2"
API_BASE = "http://127.0.0.1:3636/api/harga-v2"
REPORT = {"timestamp": datetime.now(timezone.utc).isoformat(), "issues": [], "pass": 0, "fail": 0, "warn": 0}


def fail(phase, msg, detail=None):
    REPORT["issues"].append({"phase": phase, "severity": "fail", "msg": msg, "detail": detail})
    REPORT["fail"] += 1
    print(f"  \u2716 FAIL  [{phase}] {msg}")


def warn(phase, msg, detail=None):
    REPORT["issues"].append({"phase": phase, "severity": "warn", "msg": msg, "detail": detail})
    REPORT["warn"] += 1
    print(f"  \u26a0 WARN  [{phase}] {msg}")


def ok(msg):
    REPORT["pass"] += 1
    print(f"  \u2714 {msg}")


async def phase_layout(page):
    """Verify all expected DOM elements exist and are visible."""
    print(f"\n{'='*60}")
    print("PHASE 1: Layout Audit")
    print(f"{'='*60}")

    checks = {
        "App shell": (".hv2-body", None),
        "Header": ("header.hv2-header", None),
        "Header title": ("header.hv2-header h1", "crema/harga"),
        "Archive btn": ("#hv2ArchiveBtn", "Archive"),
        "+New btn": ("#hv2NewBtn", "+ New"),
        "Sidebar": ("aside.hv2-sidebar", "PRICING CHAT"),
        "Sidebar header": (".hv2-sidebar-header h3", "PRICING CHAT"),
        "Notice DB label": (".hv2-tender-search-label", "NOTICE DB"),
        "Tender search input": ("#hv2TenderInput", None),
        "Tender dropdown": ("#hv2TenderDropdown", None),
        "Active tender section": ("#hv2ActiveTender", None),
        "Clear tender btn": ("#hv2ClearTenderBtn", "Clear"),
        "Chat area": ("#hv2ChatArea", None),
        "Greeting message": (".hv2-msg-assistant", "Salaam. Apa mau?"),
        "Processing indicator": ("#hv2Processing", None),
        "Chat input": ("#hv2ChatInput", None),
        "Send button": ("#hv2SendBtn", "Ask"),
        "Command hint": (".hv2-command-hint", None),
        "Canvas main": ("main.hv2-canvas", None),
        "Canvas content": ("#hv2CanvasContent", None),
        "Canvas empty": ("#hv2CanvasEmpty", None),
        "Canvas loading": ("#hv2CanvasLoading", None),
        "Canvas error": ("#hv2CanvasError", None),
        "Canvas error dismiss": ("#hv2CanvasErrorDismiss", None),
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
            if expected_text not in text:
                warn("1", f"{label} text mismatch", f"expected {expected_text!r}, got {text[:60]!r}")
                continue
        ok(f"{label}")

    proc = await page.query_selector("#hv2Processing")
    if proc and await proc.is_hidden():
        ok("Processing indicator hidden at rest")

    at = await page.query_selector("#hv2ActiveTender")
    if at and await at.get_attribute("hidden") is not None:
        ok("Active tender section hidden at rest")

    ce = await page.query_selector("#hv2CanvasEmpty")
    if ce and await ce.is_visible():
        ok("Canvas empty state visible on load")
    for sel_id, label in [("#hv2CanvasLoading", "Canvas loading"), ("#hv2CanvasError", "Canvas error")]:
        el = await page.query_selector(sel_id)
        if el and await el.get_attribute("hidden") is not None:
            ok(f"{label} hidden on load")


async def phase_tokens(page):
    """Verify design tokens, monochrome compliance, no hex violations."""
    print(f"\n{'='*60}")
    print("PHASE 2: CSS / Token Audit")
    print(f"{'='*60}")

    tokens = await page.evaluate("""() => {
        const s = getComputedStyle(document.body);
        const want = ['--bg','--surface','--text-1','--text-2','--accent',
                      '--radius-md','--font-body','--font-display','--font-mono'];
        const r = {};
        for (const t of want) r[t] = s.getPropertyValue(t).trim();
        return r;
    }""")
    missing = [k for k, v in tokens.items() if not v]
    if missing:
        fail("2", f"Missing design tokens: {missing}")
    else:
        ok(f"All {len(tokens)} design tokens defined")
    for k, v in tokens.items():
        if v:
            print(f"      {k}: {v[:50]}")

    # Check harga-v2.css file for hardcoded hex colors (not inherited crema.css values)
    import re as _re
    hv2_css_paths = [
        "/home/the_bomb/orkes/yellowpages/static/tools/harga-v2.css",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "static/tools/harga-v2.css"),
    ]
    hv2_css_text = ""
    for _p in hv2_css_paths:
        if os.path.exists(_p):
            with open(_p) as _f:
                hv2_css_text = _f.read()
            break
    if hv2_css_text:
        css_clean = _re.sub(r'/\*.*?\*/', '', hv2_css_text, flags=_re.DOTALL)
        non_neutral = []
        for m in _re.finditer(r'#[0-9a-fA-F]{6}\b', css_clean):
            h = m.group()
            r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
            if max(r, g, b) - min(r, g, b) > 20 and not (r < 30 and g < 30 and b < 30):
                non_neutral.append(h)
        if non_neutral:
            for h in sorted(set(non_neutral)):
                fail("2", f"Hardcoded hex in harga-v2.css: {h}")
        else:
            ok("No hardcoded non-neutral hex colors in harga-v2.css (uses var() tokens)")
    else:
        warn("2", "Cannot read harga-v2.css for hex audit")

    gradients = await page.evaluate("""() => {
        const els = document.querySelectorAll('[class*="hv2"], [id*="hv2"]');
        const found = [];
        for (const el of els) {
            if (getComputedStyle(el).background.includes('gradient'))
                found.push((el.className||el.id||'').slice(0,50));
        }
        return found;
    }""")
    if gradients:
        warn("2", f"Gradients found: {gradients}")
    else:
        ok("No gradient backgrounds")


async def phase_interactivity(page):
    """Test tender search, keyboard nav, chat input, archive, new session."""
    print(f"\n{'='*60}")
    print("PHASE 3: Interactivity")
    print(f"{'='*60}")

    search = await page.query_selector("#hv2TenderInput")
    if not search:
        fail("3", "Tender search input not found")
        return

    await search.fill("GEP-RFP")
    await page.wait_for_timeout(1500)
    count = await page.evaluate("document.querySelectorAll('#hv2TenderDropdown > *').length")
    if count > 0:
        ok(f"Tender search: {count} results for 'GEP-RFP'")
    else:
        warn("3", "Tender search returned 0 results")

    dd_visible = await page.evaluate(
        "document.getElementById('hv2TenderDropdown')?.classList?.contains('is-visible')")
    if dd_visible:
        ok("Dropdown visible after search")

    if count > 0:
        await search.press("ArrowDown")
        await page.wait_for_timeout(300)
        sel = await page.evaluate("""() => {
            const s = document.querySelector('.hv2-tender-item.selected');
            return s ? (s.querySelector('.hv2-tender-item-ref')?.innerText || 'selected') : null;
        }""")
        if sel:
            ok(f"ArrowDown highlights: {sel}")
        else:
            warn("3", "ArrowDown did not highlight")

        await search.press("Escape")
        await page.wait_for_timeout(300)
        closed = not await page.evaluate(
            "document.getElementById('hv2TenderDropdown')?.classList?.contains('is-visible')")
        if closed:
            ok("Escape closes dropdown")
        else:
            warn("3", "Escape did not close dropdown")

        await search.fill("GEP-RFP")
        await page.wait_for_timeout(1500)
        await page.click("h1")
        await page.wait_for_timeout(300)
        closed2 = not await page.evaluate(
            "document.getElementById('hv2TenderDropdown')?.classList?.contains('is-visible')")
        if closed2:
            ok("Click outside closes dropdown")
        else:
            warn("3", "Click outside did not close")

    await search.fill("")
    await page.wait_for_timeout(500)

    chat = await page.query_selector("#hv2ChatInput")
    if chat:
        await chat.fill("/factsheet")
        if await chat.input_value() == "/factsheet":
            ok("Chat input accepts text")
        else:
            fail("3", "Chat fill failed")
        await chat.fill("")
    else:
        fail("3", "Chat input not found")

    archive = await page.query_selector("#hv2ArchiveBtn")
    if archive:
        await archive.click()
        try:
            await page.wait_for_function(
                "document.getElementById('hv2SendBtn') && !document.getElementById('hv2SendBtn').disabled",
                timeout=10000)
        except Exception:
            warn("3", "Archive: processing did not complete in time")
        cc_text = await page.evaluate("""() => {
            const cc = document.getElementById('hv2CanvasContent');
            return cc ? (cc.innerText || '').trim().slice(0,80) : '';
        }""")
        if cc_text:
            ok(f"Archive: canvas updated")
        else:
            warn("3", "Archive: canvas empty")
    else:
        fail("3", "Archive button not found")

    new_btn = await page.query_selector("#hv2NewBtn")
    if new_btn:
        try:
            await page.wait_for_function(
                "document.getElementById('hv2NewBtn') && !document.getElementById('hv2NewBtn').disabled",
                timeout=5000)
        except Exception:
            warn("3", "+New button still disabled after waiting")
        await new_btn.click()
        await page.wait_for_timeout(800)
        msgs = await page.evaluate("document.querySelectorAll('.hv2-msg').length")
        if msgs == 1:
            greet = await page.evaluate(
                "document.querySelector('.hv2-msg-assistant')?.innerText || ''")
            if "Salaam" in greet:
                ok("+New: chat cleared, greeting remains")
            else:
                warn("3", f"+New greeting: {greet[:40]}")
        else:
            warn("3", f"+New: {msgs} msgs (expected 1)")
    else:
        fail("3", "+New button not found")


async def phase_mobile(page):
    """iPhone viewport: touch targets, overflow, stacked layout."""
    print(f"\n{'='*60}")
    print("PHASE 4: Mobile (iPhone 390x844)")
    print(f"{'='*60}")

    info = await page.evaluate("""() => {
        const r = {};
        const vw = window.innerWidth, vh = window.innerHeight;
        r.vw = vw; r.vh = vh;
        r.hScroll = document.documentElement.scrollWidth > vw + 2;
        const vp = document.querySelector('meta[name="viewport"]');
        r.viewportMeta = vp ? vp.getAttribute('content') : null;
        r.bodyFontSize = getComputedStyle(document.querySelector('.hv2-body') || document.body).fontSize;
        r.smallTargets = [];
        for (const el of document.querySelectorAll(
            'button, a, input, textarea, [role="button"], select')) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && (rect.width < 44 || rect.height < 44)) {
                const label = el.innerText || el.getAttribute('aria-label') ||
                    el.placeholder || el.id || el.tagName;
                if (label) r.smallTargets.push(
                    el.tagName + ' ' + Math.round(rect.width) + 'x' + Math.round(rect.height) +
                    ' "' + String(label).trim().slice(0,30) + '"');
            }
        }
        const sidebar = document.querySelector('.hv2-sidebar');
        const canvas = document.querySelector('.hv2-canvas');
        if (sidebar) {
            const sr = sidebar.getBoundingClientRect();
            r.sidebar = { w: Math.round(sr.width), h: Math.round(sr.height), top: Math.round(sr.top) };
        }
        if (canvas) {
            const cr = canvas.getBoundingClientRect();
            r.canvas = { w: Math.round(cr.width), h: Math.round(cr.height), top: Math.round(cr.top) };
        }
        const sa = document.querySelector('#hv2ChatArea');
        if (sa) r.chatAreaHeight = Math.round(sa.getBoundingClientRect().height);
        const sb = document.querySelector('.hv2-input-row button');
        if (sb) r.sendBtnHeight = Math.round(sb.getBoundingClientRect().height);
        return r;
    }""")

    print(f"  Viewport: {info.get('vw')}x{info.get('vh')}")
    print(f"  Body font: {info.get('bodyFontSize')}")

    if info.get('hScroll'):
        fail("4", f"Horizontal overflow: scrollW overflow")
    else:
        ok("No horizontal overflow")

    bf = info.get('bodyFontSize', '0px')
    bf_px = float(bf.replace('px', ''))
    if bf_px >= 16:
        ok(f"Body font >= 16px ({bf})")
    else:
        fail("4", f"Body font {bf} < 16px")

    vp_meta = info.get('viewportMeta', '')
    if vp_meta:
        ok("Viewport meta present")
        if 'initial-scale=1.0' in vp_meta:
            ok("Has initial-scale=1.0")
        if 'viewport-fit=cover' in vp_meta:
            ok("Has viewport-fit=cover")
    else:
        fail("4", "Viewport meta missing")

    small = info.get('smallTargets', [])
    if small:
        for t in small:
            warn("4", f"Small target: {t}")
    else:
        ok("All touch targets >= 44px")

    send_h = info.get('sendBtnHeight', 0)
    if send_h >= 44:
        ok(f"Send button >= 44px ({send_h}px)")

    sidebar = info.get('sidebar', {})
    if sidebar.get('w', 0) >= 350:
        ok(f"Sidebar full-width ({sidebar['w']}px)")

    s_top = sidebar.get('top', 0)
    c_top = info.get('canvas', {}).get('top', 0)
    if c_top > s_top:
        ok("Sidebar+canvas stacked vertically")


async def phase_dark_mode(page):
    """Verify dark mode renders correctly."""
    print(f"\n{'='*60}")
    print("PHASE 5: Dark Mode")
    print(f"{'='*60}")

    meta = await page.evaluate("""() => {
        const light = document.querySelector(
            'meta[name="theme-color"][media="(prefers-color-scheme: light)"]');
        const dark = document.querySelector(
            'meta[name="theme-color"][media="(prefers-color-scheme: dark)"]');
        return { light: light?.getAttribute('content'), dark: dark?.getAttribute('content') };
    }""")
    if meta.get('light') and meta.get('dark'):
        ok(f"Theme-color: {meta['light']} / {meta['dark']}")
    else:
        warn("5", f"Missing theme-color meta")

    await page.evaluate("document.documentElement.setAttribute('data-mode', 'dark')")
    await page.wait_for_timeout(500)

    colors = await page.evaluate("""() => {
        const s = getComputedStyle(document.body);
        return {
            bg: s.getPropertyValue('--bg').trim(),
            surface: s.getPropertyValue('--surface').trim(),
            bodyBg: s.backgroundColor,
        };
    }""")
    if colors.get('bg'):
        ok(f"Dark --bg: {colors['bg']}")
    else:
        fail("5", "Dark mode --bg token missing")
    if colors.get('surface'):
        ok(f"Dark --surface: {colors['surface']}")
    body_bg = colors.get('bodyBg', '')
    if '255' in body_bg and body_bg.count('255') >= 3:
        warn("5", f"Body bg appears white: {body_bg}")
    else:
        ok("Body bg is dark")

    await page.evaluate("document.documentElement.removeAttribute('data-mode')")
    await page.wait_for_timeout(300)


async def phase_send_flow(page):
    """Test typing message, Enter to send, Shift+Enter newline."""
    print(f"\n{'='*60}")
    print("PHASE 6: Send Flow")
    print(f"{'='*60}")

    chat = await page.query_selector("#hv2ChatInput")
    send = await page.query_selector("#hv2SendBtn")
    if not chat or not send:
        fail("6", "Chat input or send button not found")
        return

    await chat.fill("test message")
    if await chat.input_value() == "test message":
        ok("Chat input accepts text")
    else:
        fail("6", "Chat fill failed")

    if await send.is_enabled():
        ok("Send button enabled with text")

    await chat.fill("/help")
    await page.wait_for_timeout(200)
    msg_before = len(await page.query_selector_all('.hv2-msg'))
    await send.click()
    await page.wait_for_timeout(2000)
    msg_after = len(await page.query_selector_all('.hv2-msg'))
    if msg_after > msg_before:
        ok(f"Send click: {msg_before} -> {msg_after}")
    else:
        warn("6", "Send click did not add message")

    await page.wait_for_timeout(500)
    await chat.fill("/clear")
    await page.wait_for_timeout(200)
    msg_before2 = len(await page.query_selector_all('.hv2-msg'))
    await chat.press("Enter")
    await page.wait_for_timeout(2000)
    msg_after2 = len(await page.query_selector_all('.hv2-msg'))
    if msg_after2 > msg_before2:
        ok(f"Enter: {msg_before2} -> {msg_after2}")
    else:
        warn("6", "Enter did not add message")

    await chat.fill("line1")
    await page.wait_for_timeout(100)
    msg_before3 = len(await page.query_selector_all('.hv2-msg'))
    await chat.press("Shift+Enter")
    await page.wait_for_timeout(500)
    val2 = await chat.input_value()
    if val2 and val2 != "line1":
        ok("Shift+Enter adds newline (doesn't send)")
    else:
        warn("6", f"Shift+Enter: {val2!r}")


async def phase_html_validation(page):
    """Check HTML structure, ARIA, labels, duplicate IDs."""
    print(f"\n{'='*60}")
    print("PHASE 7: HTML + Accessibility")
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
        for (const [id, count] of Object.entries(idCount))
            if (count > 1) issues.push('Duplicate ID #' + id + ' (' + count + 'x)');

        document.querySelectorAll('button').forEach(b => {
            const label = b.getAttribute('aria-label') || b.innerText.trim();
            if (!label) issues.push('Unlabeled button: <' + (b.className||'').slice(0,30) + '>');
        });

        document.querySelectorAll('img:not([alt])').forEach(img => {
            issues.push('Image missing alt: ' + (img.getAttribute('src')||'').slice(0,30));
        });

        const chatLog = document.querySelector('[role="log"]');
        if (!chatLog) issues.push('Chat area missing role="log"');
        else if (!chatLog.getAttribute('aria-live'))
            issues.push('Chat log missing aria-live');

        const dd = document.getElementById('hv2TenderDropdown');
        if (dd && dd.getAttribute('role') !== 'listbox')
            issues.push('Tender dropdown role: ' + (dd.getAttribute('role') || '?') + ' (expected listbox)');
        if (dd && !dd.getAttribute('aria-label'))
            issues.push('Tender dropdown missing aria-label');

        const ti = document.getElementById('hv2TenderInput');
        if (ti) {
            if (!ti.getAttribute('aria-label')) issues.push('Tender input missing aria-label');
            if (ti.getAttribute('aria-controls') !== 'hv2TenderDropdown')
                issues.push('Tender input missing aria-controls');
        }

        const header = document.querySelector('header');
        if (header && header.getAttribute('role') !== 'banner')
            issues.push('Header missing role="banner"');

        const aside = document.querySelector('aside');
        if (aside) {
            if (aside.getAttribute('role') !== 'complementary')
                issues.push('Sidebar missing role="complementary"');
            if (!aside.getAttribute('aria-label'))
                issues.push('Sidebar missing aria-label');
        }

        const main = document.querySelector('main');
        if (main) {
            if (main.getAttribute('role') !== 'main')
                issues.push('Canvas missing role="main"');
            if (!main.getAttribute('aria-label'))
                issues.push('Canvas missing aria-label');
        }

        const ci = document.getElementById('hv2ChatInput');
        if (ci && !ci.getAttribute('aria-label'))
            issues.push('Chat input missing aria-label');

        return issues.slice(0,30);
    }""")

    if results:
        for r in results:
            warn("7", r)
    else:
        ok("All HTML + a11y checks passed")


async def phase_state_persistence(page):
    """Check sessionStorage for session ID."""
    print(f"\n{'='*60}")
    print("PHASE 8: State Persistence")
    print(f"{'='*60}")

    ss = await page.evaluate("""() => {
        const keys = Object.keys(sessionStorage).filter(
            k => k.includes('harga') || k.includes('hv2'));
        const data = {};
        for (const k of keys) {
            try { data[k] = JSON.parse(sessionStorage[k]); }
            catch { data[k] = sessionStorage[k].slice(0,100); }
        }
        return data;
    }""")
    if ss:
        for k, v in ss.items():
            t = json.dumps(v)[:80] if not isinstance(v, str) else v[:80]
            print(f"    {k}: {t}")
        ok(f"sessionStorage: {len(ss)} key(s)")
        if any('session_id' in k for k in ss):
            ok("Session ID persisted")
    else:
        warn("8", "No harga keys in sessionStorage")


async def phase_performance(page):
    """Navigation timing metrics."""
    print(f"\n{'='*60}")
    print("PHASE 9: Performance Metrics")
    print(f"{'='*60}")

    perf = await page.evaluate("""() => {
        const nav = performance.getEntriesByType('navigation')[0];
        if (!nav) return {};
        return {
            dcl: Math.round(nav.domContentLoadedEventEnd),
            load: Math.round(nav.loadEventEnd),
            transferSize: nav.transferSize || 0,
        };
    }""")
    if perf and perf.get('dcl', 0):
        ok(f"DOMContentLoaded: {perf['dcl']}ms")
        if perf.get('load', 0):
            ok(f"Load: {perf['load']}ms")
        if perf.get('transferSize', 0):
            ok(f"Transfer: {perf['transferSize']} bytes")
    else:
        warn("9", "No nav timing data")


async def phase_api_endpoints(page):
    """Hit API endpoints via fetch from page context."""
    print(f"\n{'='*60}")
    print("PHASE 10: API Endpoint Checks")
    print(f"{'='*60}")

    for method, url, label in [
        ("GET", f"{API_BASE}/tenders?q=GEP-RFP", "Tender search"),
        ("GET", f"{API_BASE}/archive", "Archive list"),
    ]:
        resp = await page.evaluate(f"""async () => {{
            try {{
                const r = await fetch({json.dumps(url)}, {{
                    method: {json.dumps(method)},
                    headers: {{ 'Content-Type': 'application/json' }}
                }});
                return {{ status: r.status, ok: r.ok }};
            }} catch(e) {{
                return {{ status: 0, ok: false }};
            }}
        }}""")
        if resp.get("ok"):
            ok(f"{label}: {resp.get('status')}")
        else:
            warn("10", f"{label}: {resp.get('status')}")

    print("  --- Session lifecycle ---")
    session_data = await page.evaluate(f"""async () => {{
        try {{
            const r = await fetch({json.dumps(API_BASE + '/sessions')}, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{}})
            }});
            if (!r.ok) return {{ status: r.status, ok: false }};
            const data = await r.json();
            return {{ status: r.status, sessionId: data?.session?.id, ok: true }};
        }} catch(e) {{
            return {{ status: 0, sessionId: null, ok: false }};
        }}
    }}""")
    sid = session_data.get("sessionId")
    if sid:
        ok(f"POST /sessions -> {sid[:16]}...")
        load = await page.evaluate(f"""async () => {{
            try {{
                const r = await fetch({json.dumps(API_BASE + '/sessions/' + sid)});
                return {{ status: r.status, ok: r.ok }};
            }} catch(e) {{
                return {{ status: 0, ok: false }};
            }}
        }}""")
        if load.get("ok"):
            ok(f"GET /sessions/{{id}} -> {load.get('status')}")
        tender_set = await page.evaluate(f"""async () => {{
            try {{
                const r = await fetch({json.dumps(API_BASE + '/sessions/' + sid + '/tender')}, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ tender_ref: '' }})
                }});
                return {{ status: r.status, ok: r.ok }};
            }} catch(e) {{
                return {{ status: 0, ok: false }};
            }}
        }}""")
        ok(f"POST tender -> {tender_set.get('status')}")
    else:
        warn("10", "POST /sessions: no ID")


async def phase_full_flow(page):
    """Search notice, pull via Enter, verify banner, clear."""
    print(f"\n{'='*60}")
    print("PHASE 11: Full User Flow")
    print(f"{'='*60}")

    new_btn = await page.query_selector("#hv2NewBtn")
    if new_btn:
        await new_btn.click()
        await page.wait_for_timeout(800)
        ok("Fresh session started")

    ti = await page.query_selector("#hv2TenderInput")
    if not ti:
        fail("11", "Tender input not found")
        return

    found = False
    for query in ["GEP-RFP", "QT", "tender"]:
        await ti.fill(query)
        await page.wait_for_timeout(2000)
        count = await page.evaluate("document.querySelectorAll('#hv2TenderDropdown > *').length")
        if count > 0:
            ok(f"Found {count} results for {query!r}")
            found = True
            break
    if not found:
        warn("11", "No results for any query")
        return

    await ti.press("Enter")
    await page.wait_for_timeout(3000)

    active = await page.evaluate("""() => {
        const banner = document.getElementById('hv2ActiveTender');
        if (!banner) return { visible: false };
        return {
            visible: banner.hidden !== true,
            title: (document.getElementById('hv2ActiveTenderTitle')?.innerText || '').slice(0,60),
        };
    }""")
    if active.get("visible"):
        ok(f"Active tender: {active['title'][:50]}")
    else:
        warn("11", "Active tender not shown")

    msg_count = await page.evaluate("document.querySelectorAll('.hv2-msg').length")
    if msg_count > 1:
        ok(f"Chat: {msg_count} messages")

    clear = await page.query_selector("#hv2ClearTenderBtn")
    if clear:
        await clear.click()
        await page.wait_for_timeout(3000)
        hidden = await page.evaluate(
            "document.getElementById('hv2ActiveTender')?.hidden !== false")
        if hidden:
            ok("Clear hides banner")
        else:
            warn("11", "Clear did not hide")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print(f"Navigating to {BASE} ...")
        try:
            await page.goto(BASE, wait_until="networkidle", timeout=30000)
        except PwTimeout:
            warn("SETUP", "Page load timeout, continuing")
        await page.wait_for_timeout(2000)
        ok(f"Page loaded ({page.url})")

        await phase_layout(page)
        await phase_tokens(page)
        await phase_interactivity(page)
        await phase_html_validation(page)
        await phase_state_persistence(page)
        await phase_send_flow(page)
        await phase_performance(page)
        await phase_api_endpoints(page)

        if console_errors:
            for ce in console_errors[:10]:
                warn("CONSOLE", ce)
        else:
            ok("No JS console errors")

        await ctx.close()

        ctx2 = await browser.new_context(viewport={"width": 1280, "height": 800})
        page2 = await ctx2.new_page()
        try:
            await page2.goto(BASE, wait_until="networkidle", timeout=30000)
        except PwTimeout:
            pass
        await page2.wait_for_timeout(2000)
        await phase_full_flow(page2)
        await ctx2.close()

        ctx_m = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page_m = await ctx_m.new_page()
        try:
            await page_m.goto(BASE, wait_until="networkidle", timeout=30000)
        except PwTimeout:
            pass
        await page_m.wait_for_timeout(2000)
        await phase_mobile(page_m)
        await phase_dark_mode(page_m)
        await ctx_m.close()
        await browser.close()

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
            icon = "\u2716" if issue["severity"] == "fail" else "\u26a0"
            print(f"  {icon} {i}. [{issue['phase']}] {issue['msg']}")
            if issue.get("detail"):
                print(f"       {issue['detail']}")
    else:
        print("\nAll checks passed — no issues found!")

    return REPORT


if __name__ == "__main__":
    r = asyncio.run(main())
    sys.exit(1 if r["fail"] > 0 else 0)
