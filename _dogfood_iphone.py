#!/usr/bin/env python3
"""Dogfood harga tool on iPhone 14 viewport using Playwright."""

import asyncio
import json
import sys
from playwright.async_api import async_playwright

BASE = "http://localhost:3636/tools/harga-v2"

async def report(step, status, detail, screenshot=None):
    entry = {"step": step, "status": status, "detail": detail}
    if screenshot:
        entry["screenshot"] = screenshot
    print(json.dumps(entry, indent=2))
    print("---")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()

        issues = []

        # ── 1. Load page ──
        print("=" * 60)
        print("STEP 1: Load harga tool on iPhone viewport")
        print("=" * 60)
        try:
            await page.goto(BASE, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            title = await page.title()
            vis = await page.evaluate("document.querySelector('#app, main, .container, body') !== null")
            await page.screenshot(path="/tmp/harga_01_load.png", full_page=True)
            await report("1. Load page", "PASS" if vis else "WARN",
                         f"Title: {title}, Content rendered: {vis}",
                         "/tmp/harga_01_load.png")

            # Check for horizontal overflow
            overflow = await page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if overflow:
                issues.append("Horizontal overflow detected on load")

            # Get viewport dimensions
            vp = await page.evaluate("({w: window.innerWidth, h: window.innerHeight})")
            print(f"  Viewport: {vp['w']}x{vp['h']}")
            if vp['w'] > 390:
                issues.append(f"Viewport wider than expected: {vp['w']}px")
        except Exception as e:
            await report("1. Load page", "FAIL", str(e))
            issues.append(f"Page load failed: {e}")

        # ── Check for price canvas / canvas panel ──
        print("\n" + "=" * 60)
        print("STEP 2: Price Canvas — toggle canvas panel, check layout")
        print("=" * 60)

        # Look for canvas toggle buttons or panels
        canvas_btns = await page.query_selector_all('button:has-text("Canvas"), button:has-text("canvas"), button:has-text("Price"), [class*="canvas"], [class*="panel"]')
        print(f"  Found {len(canvas_btns)} canvas-related elements")

        # Try clicking canvas toggle
        canvas_clicked = False
        for selector in ['button:has-text("Canvas")', 'button:has-text("Price")', 'button:has-text("Toggle")', '[class*="canvas-toggle"]', '[class*="panel-toggle"]']:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    canvas_clicked = True
                    print(f"  Clicked: {selector}")
                    break
            except:
                continue

        await page.screenshot(path="/tmp/harga_02_canvas.png", full_page=True)
        await report("2. Price Canvas", "PASS" if canvas_clicked else "INFO",
                     f"Canvas toggle found: {canvas_clicked}",
                     "/tmp/harga_02_canvas.png")

        # ── 3. Chatbot ──
        print("\n" + "=" * 60)
        print("STEP 3: Chatbot interaction")
        print("=" * 60)
        chatbot_found = False
        chat_input = await page.query_selector('input[type="text"], textarea, [contenteditable="true"], [class*="chat"] input, [class*="message"] input')
        if chat_input:
            chatbot_found = True
            print("  Chat input found, typing message...")
            await chat_input.fill("Hello from iPhone")
            await page.wait_for_timeout(500)
            # Try Enter to send
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(2000)
        else:
            print("  No chat input found via generic selectors")
            # Check for any chatbot-like elements
            chat_els = await page.query_selector_all('[class*="chat"], [class*="message"], [class*="bot"], [class*="Chat"]')
            print(f"  Chat-like elements found: {len(chat_els)}")

        await page.screenshot(path="/tmp/harga_03_chat.png", full_page=True)
        await report("3. Chatbot", "PASS" if chatbot_found else "INFO",
                     f"Chat input found: {chatbot_found}",
                     "/tmp/harga_03_chat.png")

        # ── 4. Tender Doc Viewer ──
        print("\n" + "=" * 60)
        print("STEP 4: Tender Doc Viewer")
        print("=" * 60)
        tender_found = False
        for selector in ['[class*="tender"]', '[class*="document"]', '[class*="Tender"]', '[class*="doc"]', 'a:has-text("Tender")', 'button:has-text("Tender")', 'button:has-text("Document")', 'button:has-text("Doc")']:
            try:
                el = await page.query_selector(selector)
                if el:
                    txt = await el.inner_text()
                    print(f"  Found: {selector} -> '{txt[:60]}'")
                    tender_found = True
                    try:
                        await el.click()
                        await page.wait_for_timeout(1500)
                    except:
                        pass
                    break
            except:
                continue

        # Try tabs for tender doc viewer
        if not tender_found:
            tabs = await page.query_selector_all('button[role="tab"], [class*="tab"], nav a')
            for t in tabs:
                txt = await t.inner_text()
                if any(k in txt.lower() for k in ["tender", "doc", "document", "viewer", "detail"]):
                    tender_found = True
                    print(f"  Tab found: {txt}")
                    try:
                        await t.click()
                        await page.wait_for_timeout(1500)
                    except:
                        pass
                    break

        await page.screenshot(path="/tmp/harga_04_tender.png", full_page=True)
        await report("4. Tender Doc Viewer", "PASS" if tender_found else "INFO",
                     f"Tender/doc elements found: {tender_found}",
                     "/tmp/harga_04_tender.png")

        # ── 5. Comparison View ──
        print("\n" + "=" * 60)
        print("STEP 5: Comparison View — side-by-side pricing")
        print("=" * 60)
        compare_found = False
        for selector in ['[class*="compar"]', '[class*="Compar"]', '[class*="side"]', 'button:has-text("Compar")', 'button:has-text("compar")']:
            try:
                el = await page.query_selector(selector)
                if el:
                    txt = await el.inner_text()
                    print(f"  Found: {selector} -> '{txt[:60]}'")
                    compare_found = True
                    try:
                        await el.click()
                        await page.wait_for_timeout(1500)
                    except:
                        pass
                    break
            except:
                continue

        await page.screenshot(path="/tmp/harga_05_compare.png", full_page=True)
        await report("5. Comparison View", "PASS" if compare_found else "INFO",
                     f"Comparison elements found: {compare_found}",
                     "/tmp/harga_05_compare.png")

        # ── 6. Result Dashboard ──
        print("\n" + "=" * 60)
        print("STEP 6: Result Dashboard — structured cards with badges")
        print("=" * 60)
        results_found = False
        for selector in ['[class*="result"]', '[class*="card"]', '[class*="badge"]', '[class*="Result"]', '[class*="dashboard"]']:
            try:
                els = await page.query_selector_all(selector)
                if els:
                    print(f"  Found {len(els)} elements matching '{selector}'")
                    results_found = True
                    if len(els) > 0:
                        txt = await els[0].inner_text()
                        print(f"  First element text: '{txt[:80]}'")
                    break
            except:
                continue

        await page.screenshot(path="/tmp/harga_06_results.png", full_page=True)
        await report("6. Result Dashboard", "PASS" if results_found else "INFO",
                     f"Result/card elements found: {results_found}",
                     "/tmp/harga_06_results.png")

        # ── 7. Workspace Canvas / drag-drop ──
        print("\n" + "=" * 60)
        print("STEP 7: Workspace Canvas — drag-drop items")
        print("=" * 60)
        workspace_found = False
        for selector in ['[class*="workspace"]', '[class*="Workspace"]', '[class*="drag"]', '[class*="item"]', '[class*="card"]', '[class*="category"]']:
            try:
                els = await page.query_selector_all(selector)
                if els:
                    print(f"  Found {len(els)} elements matching '{selector}'")
                    workspace_found = True
                    break
            except:
                continue

        # Check for drag-drop attributes
        draggable = await page.query_selector_all('[draggable="true"]')
        print(f"  Draggable elements: {len(draggable)}")

        await page.screenshot(path="/tmp/harga_07_workspace.png", full_page=True)
        await report("7. Workspace Canvas", "PASS" if workspace_found else "INFO",
                     f"Workspace elements: {workspace_found}, Draggable: {len(draggable)}",
                     "/tmp/harga_07_workspace.png")

        # ── Summary ──
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Issues found: {len(issues)}")
        for i in issues:
            print(f"  ! {i}")

        # Check mobile-specific issues
        mobile_issues = await page.evaluate("""
            () => {
                const issues = [];
                const body = document.body;
                if (!body) return issues;

                // Check for elements wider than viewport
                const all = document.querySelectorAll('*');
                const vw = window.innerWidth;
                for (const el of all) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > vw + 5 && rect.width < 10000) {
                        const tag = el.tagName.toLowerCase();
                        const id = el.id ? '#' + el.id : '';
                        const cls = el.className && typeof el.className === 'string' ? '.' + el.className.slice(0,20) : '';
                        const text = (el.innerText || '').trim().slice(0,30);
                        issues.push(`Overflow: <${tag}${id}${cls}> width=${Math.round(rect.width)}px > viewport ${vw}px "${text}"`);
                        if (issues.length >= 10) break;
                    }
                }

                // Check touch targets
                const small = [];
                const clickable = document.querySelectorAll('button, a, input, [role="button"], [onclick]');
                for (const el of clickable) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && (rect.width < 32 || rect.height < 32)) {
                        const text = (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0,30);
                        small.push(`Small target: <${el.tagName.toLowerCase()}> ${Math.round(rect.width)}x${Math.round(rect.height)} "${text}"`);
                        if (small.length >= 10) break;
                    }
                }

                return { overflow: issues, smallTargets: small };
            }
        """)

        print(f"\nMobile overflow issues: {len(mobile_issues.get('overflow', []))}")
        for o in mobile_issues['overflow'][:10]:
            print(f"  ! {o}")
            issues.append(o)

        print(f"\nSmall touch targets (<32px): {len(mobile_issues.get('smallTargets', []))}")
        for s in mobile_issues['smallTargets'][:10]:
            print(f"  ! {s}")
            issues.append(s)

        # Final screenshot
        await page.screenshot(path="/tmp/harga_99_final.png", full_page=True)

        print(f"\n{'='*60}")
        print(f"DOGFOOD COMPLETE — {len(issues)} issues found")
        print(f"{'='*60}")

        await browser.close()
        return issues

if __name__ == "__main__":
    issues = asyncio.run(main())
    if issues:
        print(f"\nFound {len(issues)} issue(s):")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\nNo issues found — clean dogfood!")
