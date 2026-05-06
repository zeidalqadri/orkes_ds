#!/usr/bin/env python3
"""Click each canvas button and verify panel content on iPhone viewport."""

import asyncio, json
from playwright.async_api import async_playwright

BASE = "http://localhost:3636/tools/harga-v2"

async def click_and_report(page, label):
    """Click a button by text and return visible panel info."""
    btn = page.locator(f'button:has-text("{label}"):not(:has-text("×"))').first
    if not await btn.is_visible():
        return f"Button '{label}' not visible"
    await btn.click()
    await page.wait_for_timeout(1500)

    # Get panel content rendered after click
    info = await page.evaluate(f"""
() => {{
    const vh = window.innerHeight;
    const els = [];

    // Find all visible panels/sections
    document.querySelectorAll('[class*="panel"], [class*="canvas"], [class*="view"], [class*="container"], section, div').forEach(el => {{
        const r = el.getBoundingClientRect();
        if (r.width > 50 && r.height > 30 && r.top < vh && r.bottom > 0) {{
            const txt = (el.innerText || '').trim().slice(0,100);
            if (txt) {{
                els.push({{
                    cls: (el.className || '').slice(0,40),
                    rect: `${{Math.round(r.width)}}x${{Math.round(r.height)}}`,
                    text: txt
                }});
            }}
        }}
    }});

    return {{
        panels: els.slice(0,15),
        visibleButtons: Array.from(document.querySelectorAll('button')).filter(b => {{
            const r = b.getBoundingClientRect();
            return r.top < vh && r.bottom > 0 && r.width > 0;
        }}).map(b => (b.innerText || '').trim().slice(0,30)).filter(t => t)
    }};
}}
""")
    return info

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
        )
        page = await context.new_page()
        await page.goto(BASE, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        buttons = ["Price Canvas", "Tender Doc", "Compare", "Dashboard", "Workspace"]
        for btn in buttons:
            print(f"\n{'='*50}")
            print(f"CLICK: {btn}")
            print(f"{'='*50}")
            try:
                result = await click_and_report(page, btn)
                print(json.dumps(result, indent=2))
            except Exception as e:
                print(f"  ERROR: {e}")

        # Final state
        print(f"\n{'='*50}")
        print(f"FINAL STATE")
        print(f"{'='*50}")
        await page.wait_for_timeout(1000)
        final = await page.evaluate("""
() => {
    const vh = window.innerHeight;
    const visible = [];
    document.querySelectorAll('button').forEach(b => {
        const r = b.getBoundingClientRect();
        if (r.top < vh && r.bottom > 0 && r.width > 0) {
            visible.push((b.innerText || '').trim().slice(0,40));
        }
    });
    return visible;
}
""")
        print(f"Visible buttons: {final}")

        await browser.close()

asyncio.run(main())
