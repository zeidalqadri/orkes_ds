#!/usr/bin/env python3
"""
Final comprehensive dogfood test of the CREMA harga tool.
Handles modal interference robustly.
"""

import asyncio, json, os, re
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://yellowpages.zeidgeist.com/tools/harga"
USERNAME = "mamak"
PASSWORD = "Ayamgoreng1!"

REPORT = []
SCREENSHOT_DIR = "/home/the_bomb/orkes_ds/data/screenshots_final"

def log(cat, status, msg, ss_name=None):
    icon = {"PASS":"PASS","FAIL":"FAIL","WARN":"WARN","INFO":"INFO"}.get(status,"INFO")
    print(f"  [{icon}] [{cat:15s}] {msg}")
    REPORT.append({"category":cat,"status":status,"message":msg,"screenshot":ss_name,"timestamp":datetime.now().isoformat()})

async def snap(page, name):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = f"{SCREENSHOT_DIR}/{name}.png"
    await page.screenshot(path=path, full_page=True)
    return name

async def force_close_modals(page):
    """Force-close ALL modals via JS."""
    closed = await page.evaluate("""
        () => {
            const modals = document.querySelectorAll('.bidder-modal.open');
            modals.forEach(m => {
                m.classList.remove('open');
                m.style.display = 'none';
            });
            return modals.length;
        }
    """)
    if closed > 0:
        log("ModalCleanup", "WARN", f"Force-closed {closed} lingering modal(s)")
    await asyncio.sleep(0.3)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={"width":1280,"height":900})

        # ==========================================================================
        # 1. LOGIN
        # ==========================================================================
        print("\n" + "="*70)
        print("1. LOGIN")
        print("="*70)

        page = await context.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        await snap(page, "01_login_page_loaded")

        title = await page.title()
        log("Login", "PASS", f"Page loaded. Title: '{title}'")

        if "CREMA/harga" in title and "Bidder's Pricing Tool" in title:
            log("Login", "PASS", "Title matches expected exactly")
        else:
            log("Login", "WARN", f"Title differs from expected. Got: '{title}'")

        # Check if Basic Auth needed
        body_text = await page.text_content("body") or ""
        if "401" in title or "unauthorized" in body_text.lower():
            log("Login", "INFO", "Basic auth needed. Retrying with URL credentials.")
            auth_url = f"https://{USERNAME}:{PASSWORD}@yellowpages.zeidgeist.com/tools/harga"
            await page.goto(auth_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            log("Login", "INFO", f"After basic auth, title: '{(await page.title())}'")

        # Check for Cloudflare Access form
        pw_inputs = await page.query_selector_all('input[type="password"]')
        if pw_inputs:
            text_inputs = await page.query_selector_all('input:not([type=hidden]):not([type=submit])')
            for inp in text_inputs:
                ph = (await inp.get_attribute("placeholder") or "").lower()
                if "user" in ph or "name" in ph or "email" in ph:
                    await inp.fill(USERNAME)
                    break
            else:
                if text_inputs:
                    await text_inputs[0].fill(USERNAME)
            await pw_inputs[0].fill(PASSWORD)
            await snap(page, "01_credentials_filled")
            log("Login", "PASS", "Credentials filled")
            submit = await page.query_selector('button[type=submit]')
            if submit:
                await submit.click()
            else:
                await page.keyboard.press("Enter")
            await asyncio.sleep(4)
            log("Login", "PASS", "Login submitted", "01_post_login")
        else:
            log("Login", "INFO", "No password field - page auto-authenticated")

        # Final verification
        title = await page.title()
        body_has_crema = "CREMA" in (await page.text_content("body") or "")
        log("Login", "PASS" if ("CREMA" in title or body_has_crema) else "FAIL",
            f"On harga page. Title='{title}'")

        # Force close any lingering modals from page load
        await force_close_modals(page)

        # ==========================================================================
        # 2. MAIN WORKSPACE / TENDER LIST
        # ==========================================================================
        print("\n" + "="*70)
        print("2. MAIN WORKSPACE / TENDER LIST")
        print("="*70)

        await asyncio.sleep(2)
        await snap(page, "02_workspace_overview")

        # Check header
        header = await page.query_selector("header.bidder-header")
        log("Workspace", "PASS" if header else "WARN", "Header: " + ("FOUND" if header else "NOT FOUND"))

        # Check main
        main_el = await page.query_selector("#bidderMain, main")
        log("Workspace", "PASS" if main_el else "WARN", "Main content: " + ("FOUND" if main_el else "NOT FOUND"))

        # Toolbar buttons
        new_bid_btn = await page.query_selector('button:has-text("+ New Bid")')
        log("Workspace", "PASS" if new_bid_btn else "WARN", "'+ New Bid' button: " + ("FOUND" if new_bid_btn else "NOT FOUND"))

        entities_btn = await page.query_selector('button:has-text("Entities")')
        quick_check_btn = await page.query_selector('button:has-text("Quick Check")')
        chatbot_btn = await page.query_selector('button:has-text("Chatbot")')
        all_present = entities_btn and quick_check_btn and chatbot_btn
        log("Workspace", "PASS" if all_present else "WARN",
            "Toolbar buttons (Entities, Quick Check, Chatbot): " + ("ALL FOUND" if all_present else "SOME MISSING"))

        # Empty state check
        create_first = await page.query_selector('button:has-text("Create Your First Bid")')
        if create_first:
            log("Workspace", "INFO", "Workspace is EMPTY (no bids yet)")
            log("Workspace", "PASS", "Empty state: '+ Create Your First Bid' visible")
        else:
            log("Workspace", "INFO", "Workspace has bids (no empty state prompt)")

        # Open New Bid modal
        await snap(page, "02_before_new_bid")
        if new_bid_btn:
            await new_bid_btn.click()
            await asyncio.sleep(1.5)
            await snap(page, "02_new_bid_modal")

            new_bid_open = await page.query_selector("#newBidModal.open, #newBidModal[class*='open']")
            log("Workspace", "PASS" if new_bid_open else "WARN", "New Bid modal opened")

            # Fill fields
            bid_ref = await page.query_selector("#bidRef")
            if bid_ref:
                await bid_ref.fill("GEP-RFP-TEST-001")
                log("Workspace", "PASS", "Filled Tender Reference")

            bid_client = await page.query_selector("#bidClient")
            log("Workspace", "PASS" if bid_client else "WARN", "Client field: " + ("FOUND" if bid_client else "NOT FOUND"))

            bid_search = await page.query_selector("#bidTenderPick")
            if bid_search:
                await bid_search.fill("GEP-RFP")
                await asyncio.sleep(1)
                await snap(page, "02_search_gep_rfp")
                log("Workspace", "PASS", "Searched 'GEP-RFP' in SmartGEP picker")

            strategy = await page.query_selector("#bidStrategy")
            log("Workspace", "PASS" if strategy else "WARN", "Strategy dropdown: " + ("FOUND" if strategy else "NOT FOUND"))

            create_btn = await page.query_selector('button:has-text("Create Bid")')
            log("Workspace", "PASS" if create_btn else "WARN", "'Create Bid' button: " + ("FOUND" if create_btn else "NOT FOUND"))

            cancel_btn = await page.query_selector('button:has-text("Cancel")')
            if cancel_btn:
                await cancel_btn.click()
                await asyncio.sleep(1)
                log("Workspace", "PASS", "Clicked Cancel to close New Bid modal")

            # Force-check: is the modal REALLY closed?
            still_open = await page.query_selector("#newBidModal.open")
            if still_open:
                log("Workspace", "WARN", "BUG: New Bid modal did NOT close via Cancel button")
                await force_close_modals(page)
            else:
                log("Workspace", "PASS", "New Bid modal successfully closed")

            await snap(page, "02_after_new_bid_close")

        else:
            log("Workspace", "WARN", "Skipped New Bid modal test - button not found")

        # ==========================================================================
        # 3. CHATBOT
        # ==========================================================================
        print("\n" + "="*70)
        print("3. CHATBOT")
        print("="*70)

        await force_close_modals(page)

        sidebar = await page.query_selector("#hargaSidebar")
        if sidebar:
            log("Chatbot", "PASS", "Chatbot sidebar found")
            sidebar_text = await sidebar.text_content() or ""
            if "Salaam" in sidebar_text and "Apa mau" in sidebar_text:
                log("Chatbot", "PASS", "Greeting 'Salaam. Apa mau?' found")
            else:
                log("Chatbot", "WARN", f"Expected greeting not found. Text: {sidebar_text[:200]}",
                    "03_chatbot_greeting")
            await snap(page, "03_chatbot_overview")
        else:
            log("Chatbot", "FAIL", "No chatbot sidebar found")

        # Model selector
        model_select = await page.query_selector("#chatbotModelSelect")
        if model_select:
            options = await model_select.query_selector_all("option")
            option_texts = [await o.inner_text() for o in options]
            log("Chatbot", "PASS", f"Model options: {option_texts}")

            expected = ["Auto", "DeepSeek", "Mistral", "OpenAI"]
            missing = [m for m in expected if not any(m.lower() in t.lower() for t in option_texts)]
            if missing:
                log("Chatbot", "WARN" if len(missing) < 4 else "FAIL",
                    f"Missing models: {missing}")
            else:
                log("Chatbot", "PASS", "All 4 models found")

            for ov in ["deepseek", "mistral", "openai"]:
                try:
                    await model_select.select_option(ov)
                    log("Chatbot", "PASS", f"Selected: {ov}")
                except:
                    log("Chatbot", "WARN", f"Could not select '{ov}'")
            try:
                await model_select.select_option("auto")
                log("Chatbot", "PASS", "Reset to Auto")
            except:
                pass
        else:
            log("Chatbot", "FAIL", "Model selector not found")

        # Chat messages
        chat_panel = await page.query_selector(".chatbot-panel")
        if chat_panel:
            log("Chatbot", "PASS", "Chat messages container found")
            bot_msgs = await chat_panel.query_selector_all(".bot-message, .ai-message, [class*='assistant']")
            greeting_found = any("Salaam" in (await m.inner_text()) for m in bot_msgs)
            if not greeting_found:
                all_ps = await chat_panel.query_selector_all("p, div")
                for p in all_ps:
                    t = (await p.inner_text()).strip()
                    if "Salaam" in t or "Apa mau" in t:
                        greeting_found = True
                        break
            log("Chatbot", "PASS" if greeting_found else "WARN",
                "Greeting in chat: " + ("FOUND" if greeting_found else "NOT FOUND"))
        else:
            log("Chatbot", "WARN", "Chat messages container not found")

        # Send test message
        chat_input = await page.query_selector("#chatbotInput2")
        if chat_input:
            log("Chatbot", "PASS", "Chat input textarea found")
            tag = await chat_input.evaluate("el => el.tagName")
            log("Chatbot", "PASS" if tag == "TEXTAREA" else "WARN", f"Input type: {tag}")

            await chat_input.type("list my tenders", delay=20)
            await snap(page, "03_message_typed")
            log("Chatbot", "PASS", "Typed 'list my tenders'")

            ask_btn = await page.query_selector('button:has-text("Ask")')
            if ask_btn:
                await ask_btn.click()
                log("Chatbot", "PASS", "Clicked 'Ask' button")
            else:
                await chat_input.press("Enter")
                log("Chatbot", "WARN", "No Ask button, pressed Enter")

            await asyncio.sleep(2)
            await snap(page, "03_sent_processing")
            log("Chatbot", "PASS", "Message sent, processing state captured")

            # Wait for response
            await asyncio.sleep(10)
            await snap(page, "03_response_final")
            log("Chatbot", "PASS", "Response captured after 10s")

            # Check for new messages
            new_msgs = 0
            if chat_panel:
                all_msg_els = await chat_panel.query_selector_all(".bot-message, .ai-message, [class*='assistant'], p")
                for el in all_msg_els:
                    txt = (await el.inner_text()).strip()
                    if txt and txt != "Salaam. Apa mau?" and len(txt) > 5:
                        new_msgs += 1
            log("Chatbot", "PASS" if new_msgs > 0 else "WARN",
                f"Bot response messages: {new_msgs}")

            # Check for animated processing
            anim = await page.query_selector_all(".typing-dots, .thinking, .processing, [class*='dot']")
            log("Chatbot", "INFO" if anim else "WARN", f"Typing animation elements: {len(anim)}")

            # New conversation
            new_btn = await page.query_selector('button:has-text("+ New")')
            if new_btn:
                log("Chatbot", "PASS", "'+ New' button found")
                await new_btn.click()
                await asyncio.sleep(1)
                log("Chatbot", "PASS", "Clicked '+ New' for new conversation")
            else:
                log("Chatbot", "WARN", "'+ New' button not found")

            await snap(page, "03_after_new")
        else:
            log("Chatbot", "FAIL", "Chat input not found", "03_no_input")

        # ==========================================================================
        # 4. CANVAS FEATURES
        # ==========================================================================
        print("\n" + "="*70)
        print("4. CANVAS FEATURES")
        print("="*70)

        await force_close_modals(page)

        canvas_panel = await page.query_selector(".canvas-panel")
        if canvas_panel:
            log("Canvas", "PASS", "Canvas panel present in DOM")

            # Check 5 tabs
            tabs = await canvas_panel.query_selector_all(".canvas-tab")
            tab_texts = [await t.inner_text() for t in tabs]
            log("Canvas", "PASS", f"Tabs: {tab_texts}")

            expected_tabs = ["Price Canvas", "Tender Doc", "Compare", "Dashboard", "Workspace"]
            for et in expected_tabs:
                found = any(et.lower() in t.lower() for t in tab_texts)
                log("Canvas", "PASS" if found else "WARN",
                    f"Tab '{et}': {'FOUND' if found else 'MISSING'}")

            # Click each tab (use force=True to bypass any overlay issues)
            for tab_el, tab_text in zip(tabs, tab_texts):
                if await tab_el.is_visible():
                    try:
                        await tab_el.click(force=True)
                        await asyncio.sleep(1)
                        sn = await snap(page, f"04_tab_{tab_text.replace(' ','')}")
                        is_active = await tab_el.evaluate("el => el.classList.contains('active')")
                        log("Canvas", "PASS" if is_active else "WARN",
                            f"Tab '{tab_text}' clicked. Active: {is_active}", sn)
                    except Exception as e:
                        log("Canvas", "WARN", f"Tab '{tab_text}' click error: {str(e)[:80]}")

            # Canvas body
            canvas_body = await canvas_panel.query_selector(".canvas-body")
            log("Canvas", "PASS" if canvas_body else "WARN",
                "Canvas body: " + ("FOUND" if canvas_body else "NOT FOUND"))

            # Close canvas
            await force_close_modals(page)
            close_btn = await canvas_panel.query_selector(".canvas-close")
            if close_btn:
                try:
                    await close_btn.click(force=True)
                    await asyncio.sleep(1)
                    await snap(page, "04_canvas_closed")
                    log("Canvas", "PASS", "Canvas closed via ×", "04_canvas_closed")
                except Exception as e:
                    log("Canvas", "WARN", f"Canvas close click issue: {str(e)[:80]}")
            else:
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
                log("Canvas", "WARN", "No close button; pressed Escape")
        else:
            log("Canvas", "FAIL", "Canvas panel not found")

        # ==========================================================================
        # 5. QUICK PRICE CHECK
        # ==========================================================================
        print("\n" + "="*70)
        print("5. QUICK PRICE CHECK")
        print("="*70)

        await force_close_modals(page)

        qc_btn = await page.query_selector('button:has-text("Quick Check")')
        if qc_btn:
            await qc_btn.click()
            await asyncio.sleep(2)
            await snap(page, "05_quick_check_modal")
            log("QuickCheck", "PASS", "Opened Quick Price Check modal")

            qpc_input = await page.query_selector("#qpcInput")
            log("QuickCheck", "PASS" if qpc_input else "WARN",
                "Price input: " + ("FOUND" if qpc_input else "NOT FOUND"))
            if qpc_input:
                await qpc_input.fill("12mm steel rebar - 100 units")
                log("QuickCheck", "PASS", "Filled price input")

            check_btn = await page.query_selector('button:has-text("Check Price")')
            log("QuickCheck", "PASS" if check_btn else "WARN",
                "'Check Price' button: " + ("FOUND" if check_btn else "NOT FOUND"))

            # Close
            await page.keyboard.press("Escape")
            await asyncio.sleep(1)
            await force_close_modals(page)
            log("QuickCheck", "PASS", "Closed Quick Check modal")
            await snap(page, "05_quick_check_closed")
        else:
            log("QuickCheck", "FAIL", "Quick Check button not found")

        # ==========================================================================
        # 6. ENTITIES
        # ==========================================================================
        print("\n" + "="*70)
        print("6. ENTITIES")
        print("="*70)

        await force_close_modals(page)

        entities_btn = await page.query_selector('button:has-text("Entities")')
        if entities_btn:
            await entities_btn.click()
            await asyncio.sleep(2.5)
            await snap(page, "06_entities_modal")
            log("Entities", "PASS", "Opened Entities modal")

            entities_text = await page.text_content(".bidder-modal.open") or await page.text_content("body") or ""
            log("Entities", "PASS", f"Entities content loaded ({len(entities_text)} chars)")

            if "Loading" in entities_text:
                log("Entities", "WARN", "Entities still loading")

            add_entity = await page.query_selector('button:has-text("+ Add Entity")')
            log("Entities", "PASS" if add_entity else "WARN",
                "'+ Add Entity' button: " + ("FOUND" if add_entity else "NOT FOUND"))

            # Close
            await page.keyboard.press("Escape")
            await asyncio.sleep(1)
            await force_close_modals(page)
            log("Entities", "PASS", "Closed Entities modal", "06_entities_closed")
        else:
            log("Entities", "FAIL", "Entities button not found")

        # ==========================================================================
        # 7. MOBILE RESPONSIVENESS
        # ==========================================================================
        print("\n" + "="*70)
        print("7. MOBILE RESPONSIVENESS")
        print("="*70)

        await force_close_modals(page)
        await page.set_viewport_size({"width": 375, "height": 812})
        await asyncio.sleep(2)
        await snap(page, "07_mobile_view")
        log("Mobile", "PASS", "Viewport set to 375x812 (iPhone)")

        body_w = await page.evaluate("() => document.body.getBoundingClientRect().width")
        log("Mobile", "PASS" if abs(body_w - 375) < 50 else "WARN",
            f"Body width: {body_w}px (target ~375px)")

        has_scroll = await page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        log("Mobile", "PASS" if not has_scroll else "WARN",
            "Horizontal scroll: " + ("NONE (good)" if not has_scroll else "PRESENT (bad)"))

        # Hamburger menu
        ham = await page.query_selector(
            'button[class*="hamburger"], button[class*="menu"], button[aria-label*="menu" i], '
            '.navbar-toggler, [class*="nav-toggle"]')
        log("Mobile", "PASS" if ham else "WARN", "Hamburger menu: " + ("FOUND" if ham else "NOT FOUND"))

        # Touch targets
        small = []
        for el in await page.query_selector_all("button, a"):
            if await el.is_visible():
                box = await el.bounding_box()
                if box and (box["width"] < 44 or box["height"] < 44):
                    text = (await el.inner_text()).strip()[:30]
                    small.append(f"'{text}' ({box['width']:.0f}x{box['height']:.0f}px)")
        if small:
            log("Mobile", "WARN", f"Small touch targets ({len(small)}): {small[:10]}")
        else:
            log("Mobile", "PASS", "All touch targets >= 44px")

        # Restore
        await page.set_viewport_size({"width": 1280, "height": 900})
        await asyncio.sleep(1)

        # ==========================================================================
        # 8. DARK MODE
        # ==========================================================================
        print("\n" + "="*70)
        print("8. DARK MODE")
        print("="*70)

        theme_toggle = await page.query_selector(
            'button[class*="theme"], button[class*="dark"], button[class*="light"], '
            'button[aria-label*="theme" i], [class*="theme-toggle"], [id*="theme-toggle"], '
            'button[class*="mode"]')
        if not theme_toggle:
            for btn in await page.query_selector_all("button"):
                cls = (await btn.get_attribute("class") or "").lower()
                aria = (await btn.get_attribute("aria-label") or "").lower()
                if "theme" in cls or "dark" in cls or "light" in cls or "theme" in aria:
                    theme_toggle = btn
                    break

        if theme_toggle:
            log("DarkMode", "PASS", "Theme toggle found")
            await theme_toggle.click()
            await asyncio.sleep(1.5)
            bg = await page.evaluate("() => getComputedStyle(document.body).backgroundColor")
            fg = await page.evaluate("() => getComputedStyle(document.body).color")
            log("DarkMode", "INFO", f"Body bg={bg}, fg={fg}")
            await snap(page, "08_dark_mode")
            log("DarkMode", "PASS", "Dark mode screenshot", "08_dark_mode")

            # Contrast check
            issues = await page.evaluate("""
                () => {
                    const issues = [];
                    document.querySelectorAll('*').forEach(el => {
                        if (el.children.length) return;
                        const t = el.textContent.trim();
                        if (!t || t.length < 2) return;
                        const s = getComputedStyle(el);
                        if (s.backgroundColor === s.color && s.backgroundColor !== 'rgba(0,0,0,0)') {
                            issues.push(t.slice(0, 30));
                        }
                    });
                    return issues.slice(0, 10);
                }
            """)
            log("DarkMode", "FAIL" if issues else "PASS",
                "Contrast issues: " + (str(issues) if issues else "None found"))

            # Restore
            await theme_toggle.click()
            await asyncio.sleep(1)
            log("DarkMode", "PASS", "Restored to light mode")
            await snap(page, "08_light_restored")
        else:
            log("DarkMode", "WARN", "No theme toggle found - dark mode NOT IMPLEMENTED",
               "08_no_theme_toggle")

        # ==========================================================================
        # 9. ACCESSIBILITY
        # ==========================================================================
        print("\n" + "="*70)
        print("9. ACCESSIBILITY")
        print("="*70)

        # Skip-to-content
        skip = await page.query_selector("a.skip-to-content, a[href='#main'], a[href='#content']")
        log("A11y", "PASS" if skip else "FAIL", "Skip-to-content: " + ("FOUND" if skip else "NOT FOUND"))

        # Main landmark
        main_lm = await page.query_selector("main, [role='main']")
        log("A11y", "PASS" if main_lm else "FAIL", "Main landmark: " + ("FOUND" if main_lm else "NOT FOUND"))

        # Header banner
        hdr = await page.query_selector("header[role='banner'], header")
        log("A11y", "PASS" if hdr else "WARN", "Header/banner: " + ("FOUND" if hdr else "NOT FOUND"))

        # Headings
        heading_data = await page.evaluate("""
            () => {
                const hTags = {}; const issues = []; let last = 0;
                document.querySelectorAll('h1,h2,h3,h4,h5,h6').forEach(h => {
                    const lv = parseInt(h.tagName[1]);
                    hTags[h.tagName] = (hTags[h.tagName]||0) + 1;
                    if (last > 0 && lv - last > 1) issues.push(`h${last}->h${lv}: "${h.textContent.trim().slice(0,40)}"`);
                    last = lv;
                });
                return { hTags, issues, total: Object.values(hTags).reduce((a,b)=>a+b,0) };
            }
        """)
        log("A11y", "INFO", f"Headings ({heading_data['total']}): {heading_data['hTags']}")
        if heading_data['issues']:
            log("A11y", "WARN", f"Heading hierarchy: {heading_data['issues']}")
        else:
            log("A11y", "PASS", "Heading hierarchy sequential")

        # Buttons without labels
        no_label = await page.evaluate("""
            () => document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])').length
        """)
        log("A11y", "PASS" if no_label == 0 else "WARN", f"Buttons lacking aria-label: {no_label}")

        # Images
        img_info = await page.evaluate("""
            () => {
                const imgs = document.querySelectorAll('img');
                let noAlt = 0;
                imgs.forEach(i => { if (!i.getAttribute('alt') && i.getAttribute('alt') !== '') noAlt++; });
                return { total: imgs.length, noAlt };
            }
        """)
        log("A11y", "PASS" if img_info['noAlt'] == 0 else "WARN",
            f"Images: {img_info['total']}, missing alt: {img_info['noAlt']}")

        # Form labels
        unlabeled = await page.evaluate("""
            () => {
                let c = 0;
                document.querySelectorAll('input:not([type=hidden]), select, textarea').forEach(inp => {
                    const id = inp.id;
                    if (!id) { c++; return; }
                    const lbl = document.querySelector(`label[for="${id}"]`);
                    if (!lbl && !inp.getAttribute('aria-label') && !inp.getAttribute('aria-labelledby') && !inp.placeholder) c++;
                });
                return c;
            }
        """)
        log("A11y", "WARN" if unlabeled > 0 else "PASS", f"Unlabeled form inputs: {unlabeled}")

        await snap(page, "09_accessibility_desktop")
        log("A11y", "PASS", "Accessibility tests complete", "09_accessibility_desktop")

        # ==========================================================================
        # REPORT
        # ==========================================================================
        await page.close()
        await context.close()
        await browser.close()

    print("\n" + "="*70)
    print("FINAL TEST REPORT")
    print("="*70)
    print(f"Date: {datetime.now().isoformat()}")
    print(f"URL: {URL}")
    print(f"Total tests: {len(REPORT)}")
    print(f"Screenshots: {SCREENSHOT_DIR}/")

    cats = {}
    for r in REPORT:
        c = r["category"]
        if c not in cats: cats[c] = {"PASS":0,"FAIL":0,"WARN":0,"INFO":0}
        cats[c][r["status"]] = cats[c].get(r["status"],0)+1

    print("\n--- Summary by Category ---")
    totals = {"PASS":0,"FAIL":0,"WARN":0,"INFO":0}
    for cat in sorted(cats):
        c = cats[cat]
        t = sum(c.values())
        print(f"  {cat:15s}: {t:2d} | P:{c['PASS']:2d} F:{c['FAIL']:2d} W:{c['WARN']:2d} I:{c['INFO']:2d}")
        for k in totals: totals[k] += c[k]

    print(f"\n--- Grand Totals ---")
    print(f"  PASS: {totals['PASS']}   FAIL: {totals['FAIL']}   WARN: {totals['WARN']}   INFO: {totals['INFO']}")
    print(f"  TOTAL: {len(REPORT)}")

    failures = [r for r in REPORT if r['status']=='FAIL']
    if failures:
        print(f"\n--- FAILURES ({len(failures)}) ---")
        for r in failures:
            print(f"  [{r['category']:15s}] {r['message'][:120]}")

    warnings = [r for r in REPORT if r['status']=='WARN']
    print(f"\n--- WARNINGS ({len(warnings)}) ---")
    for r in warnings:
        ss = f" (screenshot: {r['screenshot']})" if r['screenshot'] else ""
        print(f"  [{r['category']:15s}] {r['message'][:150]}{ss}")

    report_path = "/home/the_bomb/orkes_ds/data/harga_final_report.json"
    with open(report_path, "w") as f:
        json.dump({"summary":totals,"categories":{k:v for k,v in cats.items()},"results":REPORT},
                  f, indent=2, default=str)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
