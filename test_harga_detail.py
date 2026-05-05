#!/usr/bin/env python3
"""Second pass: detailed exploration of the harga tool's UI structure."""

import asyncio
import json
import os
from datetime import datetime

from playwright.async_api import async_playwright

URL = "https://yellowpages.zeidgeist.com/tools/harga"
USERNAME = "mamak"
PASSWORD = "Ayamgoreng1!"
REPORT = []

def log(cat, status, msg, ss=None):
    icon = {"PASS":"PASS","FAIL":"FAIL","WARN":"WARN","INFO":"INFO"}.get(status,"INFO")
    print(f"  [{icon}] [{cat:15s}] {msg}" + (f" ss={ss}" if ss else ""))
    REPORT.append({"category":cat,"status":status,"message":msg,"screenshot":ss,"timestamp":datetime.now().isoformat()})

async def ss(page, name):
    path = f"/home/the_bomb/orkes_ds/data/screenshots_v2/{name}.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    await page.screenshot(path=path, full_page=True)
    return path

async def dump_page_structure(page):
    """Dump the full accessibility/ARIA tree + key HTML elements."""
    return await page.evaluate("""
        () => {
            const info = {
                title: document.title,
                url: location.href,
                bodyClasses: document.body.className,
                meta: { viewport: document.querySelector('meta[name=viewport]')?.content },
                landmarks: [],
                interactive: [],
                tables: [],
                forms: [],
                panels: [],
            };
            // Landmarks
            document.querySelectorAll('main, nav, aside, header, footer, [role=main], [role=navigation], [role=complementary], [role=banner], [role=contentinfo]').forEach(el => {
                info.landmarks.push({
                    tag: el.tagName,
                    role: el.getAttribute('role'),
                    id: el.id,
                    class: el.className.slice(0, 80),
                    visible: el.offsetParent !== null,
                    rect: el.getBoundingClientRect(),
                    text: el.textContent.trim().slice(0, 80),
                });
            });
            // Interactive buttons
            document.querySelectorAll('button, a[href], [role=button], [role=tab], [role=link]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    info.interactive.push({
                        tag: el.tagName,
                        text: el.textContent.trim().slice(0, 60),
                        id: el.id,
                        class: el.className.slice(0, 60),
                        rect: {x: rect.x|0, y: rect.y|0, w: rect.width|0, h: rect.height|0},
                        visible: el.offsetParent !== null,
                        ariaLabel: el.getAttribute('aria-label') || '',
                    });
                }
            });
            // Tables / grids
            document.querySelectorAll('table, [role=grid], [role=table], [role=treegrid]').forEach(el => {
                const rows = el.querySelectorAll('tr, [role=row]');
                const headers = el.querySelectorAll('th, [role=columnheader]');
                info.tables.push({
                    tag: el.tagName,
                    id: el.id,
                    class: el.className.slice(0, 60),
                    rows: rows.length,
                    cols: headers.length,
                    headerTexts: [...headers].map(h => h.textContent.trim()).slice(0, 10),
                    visible: el.offsetParent !== null,
                    rect: el.getBoundingClientRect(),
                });
            });
            // Forms / inputs
            document.querySelectorAll('form, input, textarea, select').forEach(el => {
                if (el.tagName === 'FORM') {
                    info.forms.push({id: el.id, action: el.action, inputs: el.querySelectorAll('input,textarea,select').length});
                } else if (['INPUT','TEXTAREA','SELECT'].includes(el.tagName)) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        const lbl = document.querySelector(`label[for="${el.id}"]`);
                        info.forms.push({
                            tag: el.tagName,
                            type: el.type || '',
                            placeholder: el.placeholder || '',
                            id: el.id,
                            name: el.name,
                            class: el.className.slice(0, 60),
                            ariaLabel: el.getAttribute('aria-label') || '',
                            label: lbl ? lbl.textContent.trim() : '',
                            rect: {x: rect.x|0, y: rect.y|0, w: rect.width|0, h: rect.height|0},
                        });
                    }
                }
            });
            // Panels / drawers / sidebars
            document.querySelectorAll('[class*=panel], [class*=drawer], [class*=sidebar], [class*=canvas], [role=dialog], [role=complementary], aside').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0) {
                    info.panels.push({
                        tag: el.tagName,
                        id: el.id,
                        class: el.className.slice(0, 80),
                        role: el.getAttribute('role'),
                        rect: {x: rect.x|0, y: rect.y|0, w: rect.width|0, h: rect.height|0},
                        visible: el.offsetParent !== null,
                        children: el.children.length,
                        text: el.textContent.trim().slice(0, 100),
                    });
                }
            });
            return info;
        }
    """)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={"width":1280,"height":900})
        page = await context.new_page()

        # PHASE 1: Initial load
        print("\n=== PHASE 1: Page Load & Auth ===")
        await page.goto(URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)

        # Check if we see a login form or auth wall
        html = await page.content()
        pw_inputs = await page.query_selector_all('input[type="password"]')
        text_inputs = await page.query_selector_all('input:not([type=hidden]):not([type=submit])')

        log("Auth", "INFO", f"Password inputs: {len(pw_inputs)}, Text inputs: {len(text_inputs)}")
        log("Auth", "INFO", f"Page title: {await page.title()}")

        if pw_inputs and len(text_inputs) >= 1:
            log("Auth", "PASS", "Login form detected (password input + text input found)")
            # Fill credentials
            for inp in text_inputs:
                typ = await inp.get_attribute("type")
                ph = (await inp.get_attribute("placeholder") or "").lower()
                if ph and ("user" in ph or "name" in ph or "email" in ph):
                    await inp.fill(USERNAME)
                    log("Auth", "PASS", "Filled username field")
                    break
            if len(text_inputs) == 1:
                await text_inputs[0].fill(USERNAME)
            await pw_inputs[0].fill(PASSWORD)
            await ss(page, "01_credentials_filled")
            log("Auth", "PASS", "Credentials filled", "01_credentials_filled")

            # Find submit
            submit = await page.query_selector('button[type=submit], input[type=submit]')
            if submit:
                await submit.click()
                await asyncio.sleep(3)
                await ss(page, "02_after_login")
                log("Auth", "PASS", "Login submitted", "02_after_login")
            else:
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                await ss(page, "02_after_login_enter")
                log("Auth", "WARN", "No submit btn; pressed Enter", "02_after_login_enter")
        else:
            log("Auth", "INFO", "No standard login form. Page may use HTTP Basic Auth or already be authenticated.")

            # Check if Basic Auth is needed
            if "401" in await page.title() or "unauthorized" in (await page.text_content("body") or "").lower():
                log("Auth", "INFO", "Basic auth challenge detected. Retrying with credentials in URL.")
                auth_url = f"https://{USERNAME}:{PASSWORD}@yellowpages.zeidgeist.com/tools/harga"
                await page.goto(auth_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(3)
                await ss(page, "02_basic_auth")
                log("Auth", "INFO", "Retried with Basic Auth in URL", "02_basic_auth")

        await ss(page, "03_page_state")
        log("Auth", "INFO", "Full page screenshot taken", "03_page_state")

        # Dump page structure
        structure = await dump_page_structure(page)
        log("Structure", "INFO", f"Landmarks: {len(structure['landmarks'])}; Interactive: {len(structure['interactive'])}; Tables: {len(structure['tables'])}; Forms: {len(structure['forms'])}; Panels: {len(structure['panels'])}")

        # Print key structure info
        for k, v in structure.items():
            if isinstance(v, list):
                for i, item in enumerate(v[:5]):
                    log("Structure", "INFO", f"{k}[{i}]: {json.dumps(item, default=str)[:200]}")
            else:
                log("Structure", "INFO", f"{k}: {v}")

        # PHASE 2: Try to login if Cloudflare Access
        print("\n=== PHASE 2: Auth Interactive ===")
        # Check for any login-related content
        body = await page.text_content("body") or ""
        if "log in" in body.lower() or "sign in" in body.lower() or "masuk" in body.lower():
            login_els = await page.query_selector_all('a:has-text("Log"), a:has-text("Sign"), button:has-text("Log"), button:has-text("Sign"), a:has-text("Masuk"), button:has-text("Masuk")')
            for el in login_els:
                if await el.is_visible():
                    txt = await el.inner_text()
                    log("Auth", "PASS", f"Found login element: {txt}")
                    await el.click()
                    await asyncio.sleep(3)
                    await ss(page, "04_after_click_login")
                    log("Auth", "PASS", "Clicked login link", "04_after_click_login")

                    # Now look for username/password
                    pw = await page.query_selector('input[type="password"]')
                    txt2 = await page.query_selector('input[type="text"], input[name="username"]')
                    if pw and txt2:
                        await txt2.fill(USERNAME)
                        await pw.fill(PASSWORD)
                        submit2 = await page.query_selector('button[type=submit]')
                        if submit2:
                            await submit2.click()
                            await asyncio.sleep(3)
                            await ss(page, "05_post_login")
                            log("Auth", "PASS", "Login via Cloudflare Access form", "05_post_login")
                    break

        # Get final page state
        await asyncio.sleep(2)
        final_structure = await dump_page_structure(page)
        log("Final", "INFO", f"After auth: Landmarks={len(final_structure['landmarks'])}; Interactive={len(final_structure['interactive'])}; Tables={len(final_structure['tables'])}; Panels={len(final_structure['panels'])}")

        # Print ALL interactive elements
        print("\n--- INTERACTIVE ELEMENTS ---")
        for el in final_structure['interactive']:
            if el['visible']:
                print(f"  {el['tag']:6s} | '{el['text']:40s}' | ({el['rect']['x']:4d},{el['rect']['y']:4d}) {el['rect']['w']:4d}x{el['rect']['h']:4d} | cls={el['class'][:50]}")

        print("\n--- PANELS ---")
        for p in final_structure['panels']:
            print(f"  {p['tag']:6s} | '{p['text'][:60]:60s}' | ({p['rect']['x']:4d},{p['rect']['y']:4d}) {p['rect']['w']:4d}x{p['rect']['h']:4d} | cls={p['class'][:50]}")

        print("\n--- ALL FORM INPUTS ---")
        for f in final_structure['forms']:
            if isinstance(f, dict) and 'tag' in f:
                print(f"  {f['tag']:8s} | type={f.get('type',''):12s} | placeholder='{f.get('placeholder',''):20s}' | id='{f.get('id',''):20s}' | label='{f.get('label',''):20s}' | aria='{f.get('ariaLabel',''):20s}' | rect=({f['rect']['x']:4d},{f['rect']['y']:4d}) {f['rect']['w']:4d}x{f['rect']['h']:4d}")
            elif isinstance(f, dict) and 'inputs' in f:
                print(f"  FORM: id='{f.get('id','')}' inputs={f.get('inputs','')}")

        await browser.close()

    # Print report
    print(f"\n=== REPORT ({len(REPORT)} entries) ===")
    for r in REPORT:
        icon = {"PASS":"PASS","FAIL":"FAIL","WARN":"WARN","INFO":"INFO"}.get(r["status"]," ?? ")
        print(f"  [{icon}] [{r['category']:15s}] {r['message'][:120]}")

    report_path = "/home/the_bomb/orkes_ds/data/harga_detail_report.json"
    with open(report_path, "w") as f:
        json.dump(REPORT, f, indent=2, default=str)
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
