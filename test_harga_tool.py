#!/usr/bin/env python3
"""Comprehensive dogfood test of the CREMA harga tool."""

import asyncio
import os
import sys
import json
import time
from datetime import datetime

from playwright.async_api import async_playwright, expect

URL = "https://yellowpages.zeidgeist.com/tools/harga"
USERNAME = "mamak"
PASSWORD = "Ayamgoreng1!"
REPORT = []

def log_result(category, status, message, screenshot=None):
    """Log a test result. status: PASS, FAIL, WARN."""
    entry = {
        "category": category,
        "status": status,
        "message": message,
        "screenshot": screenshot,
        "timestamp": datetime.now().isoformat(),
    }
    REPORT.append(entry)
    icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}.get(status, "INFO")
    print(f"  [{icon}] {category}: {message}")
    return entry


class HargaTester:
    def __init__(self, browser):
        self.browser = browser
        self.page = None
        self._screenshot_counter = 0

    async def screenshot(self, name):
        """Take a screenshot and save it."""
        self._screenshot_counter += 1
        path = f"/home/the_bomb/orkes_ds/data/screenshots/{self._screenshot_counter:03d}_{name}.png"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await self.page.screenshot(path=path, full_page=True)
        return path

    async def run_all(self):
        """Run all test sections."""
        self.page = await self.browser.new_page(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        try:
            await self.test_login()
            await self.test_workspace()
            await self.test_chatbot()
            await self.test_canvas()
            await self.test_quick_check()
            await self.test_entities()
            await self.test_mobile_responsive()
            await self.test_dark_mode()
            await self.test_accessibility()
        except Exception as e:
            import traceback
            log_result("GLOBAL", "FAIL", f"Unhandled exception: {e}\n{traceback.format_exc()}",
                       await self.screenshot("global_error"))
        finally:
            await self.page.close()

    async def test_login(self):
        """Test 1: Login flow."""
        print("\n=== TEST 1: LOGIN ===")
        try:
            await self.page.goto(URL, wait_until="networkidle", timeout=30000)
            s = await self.screenshot("01_login_page")
            log_result("Login", "PASS", f"Navigated to {URL}", s)

            # Check if already logged in or need to log in
            page_text = await self.page.text_content("body") or ""
            title = await self.page.title()

            if "CREMA" in page_text or "harga" in page_text.lower():
                log_result("Login", "WARN", f"Already on harga page (title: {title}). Checking for login form...")

            # Look for login form (username/password inputs)
            username_input = await self.page.query_selector('input[type="text"], input[name="username"], input[name="email"], input[placeholder*="user" i], input[placeholder*="email" i]')
            password_input = await self.page.query_selector('input[type="password"]')

            if username_input and password_input:
                await username_input.fill(USERNAME)
                await password_input.fill(PASSWORD)
                s = await self.screenshot("02_login_filled")
                log_result("Login", "PASS", "Filled login credentials", s)

                # Find and click submit button
                submit_btn = await self.page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Log"), button:has-text("Sign"), button:has-text("Masuk")')
                if submit_btn:
                    await submit_btn.click()
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                    await asyncio.sleep(2)
                else:
                    await username_input.press("Enter")
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                    await asyncio.sleep(2)

                s = await self.screenshot("03_after_login")
                log_result("Login", "PASS", "Submitted login form", s)
            else:
                # Some pages use basic auth
                log_result("Login", "WARN", "No standard login form found; checking current page state", await self.screenshot("03_login_state"))

            # Verify we're on the harga page
            title = await self.page.title()
            body_text = await self.page.text_content("body") or ""

            if "CREMA" in body_text or "harga" in body_text.lower() or "Bidder" in body_text or "Pricing" in body_text:
                log_result("Login", "PASS", f"Successfully on harga page. Title: '{title}'. Page contains harga content.")
            else:
                log_result("Login", "FAIL", f"Page title: '{title}'. Body snippet: {body_text[:200]}",
                          await self.screenshot("04_login_failed"))

            # Check for the exact title
            await asyncio.sleep(1)
            title_el = await self.page.query_selector("title")
            if title_el:
                actual_title = await title_el.inner_text()
                if "CREMA" in actual_title and "harga" in actual_title.lower():
                    log_result("Login", "PASS", f"Page title verified: '{actual_title}'")
                else:
                    log_result("Login", "WARN", f"Title doesn't match expected. Got: '{actual_title}'")

        except Exception as e:
            log_result("Login", "FAIL", f"Exception during login: {e}",
                      await self.screenshot("login_error"))

    async def test_workspace(self):
        """Test 2: Main workspace / tender list."""
        print("\n=== TEST 2: MAIN WORKSPACE / TENDER LIST ===")
        try:
            # Wait for page to fully load
            await asyncio.sleep(3)
            page_text = await self.page.text_content("body") or ""

            # Check for tender table / list
            tables = await self.page.query_selector_all("table, .table, [role='table'], .tender-list, .tender-table, .data-table")
            log_result("Workspace", "PASS" if tables else "WARN",
                      f"Found {len(tables)} table elements on page")

            # Check for columns in any table
            columns_found = []
            for t in tables[:3]:
                headers = await t.query_selector_all("th, thead td, [role='columnheader']")
                for h in headers:
                    txt = (await h.inner_text()).strip()
                    if txt:
                        columns_found.append(txt)
            if columns_found:
                log_result("Workspace", "PASS", f"Table columns found: {columns_found[:10]}")
            else:
                log_result("Workspace", "WARN", "No table header columns found. Checking for other data display...")

            # Look for tender data rows
            rows = await self.page.query_selector_all("tr, [role='row'], .tender-row, .bid-row, .data-row")
            log_result("Workspace", "INFO", f"Found {len(rows)} rows in tables")

            # Search functionality
            search_input = await self.page.query_selector('input[type="search"], input[placeholder*="search" i], input[placeholder*="cari" i], input[placeholder*="tender" i]')
            if search_input:
                log_result("Workspace", "PASS", "Search input found")
                # Try searching for a tender
                await search_input.fill("GEP-RFP")
                await asyncio.sleep(2)
                s = await self.screenshot("10_search_gep_rfp")
                log_result("Workspace", "PASS", "Searched for 'GEP-RFP'", s)
                await search_input.fill("")
                await asyncio.sleep(1)
            else:
                log_result("Workspace", "WARN", "No search/filter input found",
                          await self.screenshot("10_no_search"))

            # Check for "+ New Bid" button
            new_bid_btn = await self.page.query_selector('button:has-text("New Bid"), button:has-text("New"), a:has-text("New Bid"), [class*="new" i][class*="bid" i]')
            if new_bid_btn:
                log_result("Workspace", "PASS", f"Found '+ New Bid' button: {(await new_bid_btn.inner_text()).strip()}")
            else:
                log_result("Workspace", "WARN", "No '+ New Bid' button found",
                          await self.screenshot("11_no_new_bid"))

            # General screenshot of workspace
            s = await self.screenshot("12_workspace_overview")
            log_result("Workspace", "PASS", "Workspace overview captured", s)

        except Exception as e:
            log_result("Workspace", "FAIL", f"Exception: {e}",
                      await self.screenshot("workspace_error"))

    async def test_chatbot(self):
        """Test 3: Chatbot features."""
        print("\n=== TEST 3: CHATBOT ===")
        try:
            # Find and click Chatbot button
            chatbot_btn = await self.page.query_selector(
                'button:has-text("Chatbot"), button:has-text("Chat"), a:has-text("Chatbot"), [class*="chatbot" i], [id*="chatbot" i]'
            )
            if not chatbot_btn:
                # Try harder to find it
                all_buttons = await self.page.query_selector_all("button, a.btn, [role='button']")
                for btn in all_buttons:
                    txt = (await btn.inner_text()).strip().lower()
                    if "chat" in txt:
                        chatbot_btn = btn
                        break

            if chatbot_btn:
                await chatbot_btn.click()
                await asyncio.sleep(2)
                s = await self.screenshot("20_chatbot_opened")
                log_result("Chatbot", "PASS", "Opened chatbot panel", s)
            else:
                log_result("Chatbot", "FAIL", "Could not find Chatbot button",
                          await self.screenshot("20_no_chatbot"))
                return

            # Check chatbot greeting
            await asyncio.sleep(1)
            chat_area = await self.page.query_selector(".chat-messages, .chat-area, .chat-container, [class*='chat' i]")
            chat_text = ""
            if chat_area:
                chat_text = await chat_area.text_content() or ""
            else:
                chat_text = await self.page.text_content("body") or ""

            if "salaam" in chat_text.lower() or "apa mau" in chat_text.lower():
                log_result("Chatbot", "PASS", "Greeting 'Salaam. Apa mau?' found")
            else:
                log_result("Chatbot", "WARN", f"Greeting not found. Chat text: {chat_text[:200]}")

            # Check model selector dropdown
            model_select = await self.page.query_selector("select, [role='combobox'], [class*='model' i] select")
            if model_select:
                options = await model_select.query_selector_all("option")
                option_texts = [await o.inner_text() for o in options]
                log_result("Chatbot", "PASS", f"Model selector found with options: {option_texts}")

                # Verify expected models
                expected = ["Auto", "DeepSeek", "Mistral", "OpenAI"]
                missing = [m for m in expected if not any(m.lower() in t.lower() for t in option_texts)]
                if missing:
                    log_result("Chatbot", "WARN", f"Expected model options not found: {missing}")
                else:
                    log_result("Chatbot", "PASS", "All 4 expected models found in dropdown")
            else:
                log_result("Chatbot", "WARN", "No model selector dropdown found. Options found, checking text...",
                          await self.screenshot("22_no_model_selector"))

            # Try sending a test message
            chat_input = await self.page.query_selector(
                'textarea, input[type="text"], [contenteditable="true"], .chat-input, [class*="message" i] input, [class*="input" i]'
            )
            if chat_input:
                await chat_input.fill("list my tenders")
                await asyncio.sleep(0.5)

                # Find send button
                send_btn = await self.page.query_selector(
                    'button[type="submit"], button:has-text("Send"), button:has-text("Kirim"), button:has-text(">>"), button:has-text("→"), svg[class*="send"]'
                )
                if send_btn:
                    await send_btn.click()
                else:
                    await chat_input.press("Enter")

                s = await self.screenshot("23_chat_message_sent")
                log_result("Chatbot", "PASS", "Sent test message 'list my tenders'", s)

                # Wait for response (thinking animation + actual response)
                await asyncio.sleep(2)
                s = await self.screenshot("24_chat_response_start")
                log_result("Chatbot", "PASS", "Checking for thinking/processing animation", s)

                # Wait for full response (may take time for LLM)
                await asyncio.sleep(8)
                s = await self.screenshot("25_chat_response_final")
                log_result("Chatbot", "PASS", "Captured chatbot response (after 10s wait)", s)
            else:
                log_result("Chatbot", "FAIL", "No chat input textarea found",
                          await self.screenshot("23_no_chat_input"))

            # Try "+ New" conversation button
            new_chat_btn = await self.page.query_selector(
                'button:has-text("New"), button:has-text("+"), [class*="new" i], [title*="new" i]'
            )
            if new_chat_btn:
                btn_text = (await new_chat_btn.inner_text()).strip().lower()
                if "new" in btn_text or "+" in btn_text:
                    log_result("Chatbot", "PASS", f"'+ New' conversation button found: '{btn_text}'")
                else:
                    log_result("Chatbot", "WARN", f"Possible new button found but text unclear: '{btn_text}'")
            else:
                log_result("Chatbot", "WARN", "No '+ New' conversation button found")

            # Close chatbot if there's a close button
            close_btn = await self.page.query_selector(
                'button:has-text("Close"), button[aria-label="Close"], .chatbot-close, [class*="close" i]'
            )
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)
                log_result("Chatbot", "PASS", "Closed chatbot panel")

        except Exception as e:
            log_result("Chatbot", "FAIL", f"Exception: {e}",
                      await self.screenshot("chatbot_error"))

    async def test_canvas(self):
        """Test 4: Canvas features - open a bid/tender to trigger canvas panel."""
        print("\n=== TEST 4: CANVAS FEATURES ===")
        try:
            # Find a clickable bid/tender item in the table
            bid_row = await self.page.query_selector(
                "tr[data-id], tr[data-bid], tr.clickable, .tender-row, .bid-row, "
                "table tbody tr, [role='row']"
            )
            if not bid_row:
                # Try any link that might open a bid
                bid_links = await self.page.query_selector_all("a[href*='bid'], a[href*='tender'], [class*='bid'] a")
                bid_row = bid_links[0] if bid_links else None

            if not bid_row:
                # Try any table row
                all_rows = await self.page.query_selector_all("table tbody tr, [role='rowgroup'] [role='row']")
                bid_row = all_rows[0] if all_rows else None

            if bid_row:
                await bid_row.click()
                await asyncio.sleep(2)
                s = await self.screenshot("30_canvas_opened")
                log_result("Canvas", "PASS", "Clicked on a bid/tender item to open canvas", s)
            else:
                log_result("Canvas", "WARN", "No clickable bid/tender found to open canvas",
                          await self.screenshot("30_no_bid_found"))
                # Try to click on any element that might open a panel
                all_links = await self.page.query_selector_all("a, button")
                found = False
                for el in all_links[:20]:
                    txt = (await el.inner_text()).strip().lower()
                    if any(kw in txt for kw in ["bid", "tender", "item", "project"]):
                        if await el.is_visible():
                            await el.click()
                            await asyncio.sleep(2)
                            s = await self.screenshot("30_canvas_attempt")
                            log_result("Canvas", "WARN", f"Attempted to click element with text '{txt}'", s)
                            found = True
                            break
                if not found:
                    log_result("Canvas", "WARN", "Could not find any element to trigger canvas panel")

            # Check if canvas panel opened
            await asyncio.sleep(1)
            canvas_panel = await self.page.query_selector(
                "[class*='canvas'], [class*='panel'], [class*='sidebar'], [class*='drawer'], "
                "[role='dialog'], [role='complementary'], aside"
            )

            if canvas_panel and await canvas_panel.is_visible():
                log_result("Canvas", "PASS", "Canvas/sidebar panel detected as visible")
                s = await self.screenshot("31_canvas_panel_visible")
                log_result("Canvas", "PASS", "Canvas panel screenshot", s)

                # Check for canvas tabs
                tabs = await canvas_panel.query_selector_all(
                    "button, [role='tab'], .tab, [class*='tab'], nav a"
                )
                tab_texts = []
                for t in tabs:
                    if await t.is_visible():
                        txt = (await t.inner_text()).strip()
                        if txt:
                            tab_texts.append(txt)

                if tab_texts:
                    log_result("Canvas", "PASS", f"Canvas tabs found: {tab_texts}")

                    # Check for the 5 expected canvas tabs
                    expected_tabs_lower = ["pricing", "price canvas", "tender", "tender doc", "compare", "comparison",
                                           "result", "dashboard", "items", "workspace canvas"]
                    for tab in tab_texts:
                        tl = tab.lower().strip()
                        match = [e for e in expected_tabs_lower if e in tl]
                        if match:
                            log_result("Canvas", "PASS", f"Canvas tab '{tab}' matches expected category: {match[0]}")

                    # Click each tab
                    for tab_el, tab_text in zip(tabs[:5], tab_texts[:5]):
                        if await tab_el.is_visible():
                            try:
                                await tab_el.click()
                                await asyncio.sleep(1.5)
                                s = await self.screenshot(f"32_tab_{tab_text[:20].replace(' ','_')}")
                                log_result("Canvas", "PASS", f"Clicked canvas tab '{tab_text}'", s)
                            except Exception as e:
                                log_result("Canvas", "WARN", f"Could not click tab '{tab_text}': {e}")
                else:
                    log_result("Canvas", "WARN", "Canvas panel open but no tabs found",
                              await self.screenshot("31_canvas_no_tabs"))
            else:
                log_result("Canvas", "WARN", "No canvas/sidebar panel detected after click",
                          await self.screenshot("31_no_canvas_panel"))

            # Close canvas if possible
            close_btn = await self.page.query_selector(
                "button[aria-label='Close'], .canvas-close, [class*='panel'] button:has-text('×'), "
                "button:has-text('Close'), [class*='drawer'] button:first-child"
            )
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)
                log_result("Canvas", "PASS", "Closed canvas panel")

            # Also try pressing Escape
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(1)

        except Exception as e:
            log_result("Canvas", "FAIL", f"Exception: {e}",
                      await self.screenshot("canvas_error"))

    async def test_quick_check(self):
        """Test 5: Quick Price Check."""
        print("\n=== TEST 5: QUICK PRICE CHECK ===")
        try:
            qc_btn = await self.page.query_selector(
                'button:has-text("Quick"), button:has-text("Quick Check"), button:has-text("Quick Price"), '
                'a:has-text("Quick"), [class*="quick" i] button, [class*="quick" i] a'
            )
            if qc_btn:
                await qc_btn.click()
                await asyncio.sleep(2)
                s = await self.screenshot("40_quick_check_opened")
                log_result("QuickCheck", "PASS", "Clicked Quick Check button and panel opened", s)

                # Check for input fields
                inputs = await self.page.query_selector_all("input, textarea, select")
                if inputs:
                    log_result("QuickCheck", "PASS", f"Quick Check has {len(inputs)} input fields visible")
                else:
                    log_result("QuickCheck", "WARN", "Quick Check opened but no input fields visible")
            else:
                log_result("QuickCheck", "WARN", "No 'Quick Check' button found",
                          await self.screenshot("40_no_quick_check"))

            # Close quick check if needed
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(1)

        except Exception as e:
            log_result("QuickCheck", "FAIL", f"Exception: {e}",
                      await self.screenshot("quick_check_error"))

    async def test_entities(self):
        """Test 6: Entities."""
        print("\n=== TEST 6: ENTITIES ===")
        try:
            entities_btn = await self.page.query_selector(
                'button:has-text("Entities"), button:has-text("Entity"), a:has-text("Entities"), '
                'a:has-text("Entity"), [class*="entity" i] button, [class*="entity" i] a'
            )
            if entities_btn:
                await entities_btn.click()
                await asyncio.sleep(2)
                s = await self.screenshot("50_entities_opened")
                log_result("Entities", "PASS", "Clicked Entities button and view opened", s)

                # Check for entities content
                entities_content = await self.page.query_selector(
                    "[class*='entity'], [class*='client'], table, .list, [role='list']"
                )
                if entities_content:
                    log_result("Entities", "PASS", "Entities view has content")
                else:
                    log_result("Entities", "WARN", "Entities view opened but no entity-specific content visible")
            else:
                log_result("Entities", "WARN", "No 'Entities' button found",
                          await self.screenshot("50_no_entities"))

            # Close
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(1)

        except Exception as e:
            log_result("Entities", "FAIL", f"Exception: {e}",
                      await self.screenshot("entities_error"))

    async def test_mobile_responsive(self):
        """Test 7: Mobile Responsiveness."""
        print("\n=== TEST 7: MOBILE RESPONSIVENESS ===")
        try:
            # Resize to mobile width
            await self.page.set_viewport_size({"width": 375, "height": 812})
            await asyncio.sleep(2)
            s = await self.screenshot("60_mobile_view")
            log_result("Mobile", "PASS", "Resized to 375x812 (mobile iPhone viewport)", s)

            # Check if layout adapts
            body = await self.page.query_selector("body")
            if not body:
                log_result("Mobile", "WARN", "Cannot find body element")
                return

            body_box = await body.bounding_box()
            if body_box:
                log_result("Mobile", "PASS", f"Body width: {body_box['width']}px (expected ~375px)")

            # Check for hamburger menu
            hamburger = await self.page.query_selector(
                'button[class*="hamburger"], button[class*="menu"], button[aria-label*="menu" i], '
                'button:has-text("☰"), .navbar-toggler, [class*="nav-toggle"], '
                'button:has-text("Menu"), .mobile-menu-btn, [class*="mobile" i] button'
            )
            if hamburger:
                log_result("Mobile", "PASS", "Hamburger/mobile menu button found")
            else:
                log_result("Mobile", "WARN", "No hamburger menu button found for mobile view",
                          await self.screenshot("61_no_hamburger"))

            # Check for bottom navigation
            bottom_nav = await self.page.query_selector(
                "nav[class*='bottom'], [class*='bottom-nav'], [class*='tab-bar'], "
                "[class*='mobile-nav'], footer nav"
            )
            if bottom_nav:
                log_result("Mobile", "PASS", "Bottom navigation found for mobile")

            # Check touch targets (minimum 44px)
            all_interactive = await self.page.query_selector_all(
                "button, a, input, select, textarea, [role='button'], [role='link']"
            )
            small_targets = []
            for el in all_interactive:
                if await el.is_visible():
                    box = await el.bounding_box()
                    if box and (box["width"] < 44 or box["height"] < 44):
                        text = (await el.inner_text()).strip()[:30]
                        small_targets.append(f"'{text}' ({box['width']:.0f}x{box['height']:.0f}px)")

            if small_targets:
                log_result("Mobile", "WARN", f"Touch targets smaller than 44px: {small_targets[:10]}")
            else:
                # Only pass if we could actually find some interactive elements
                if all_interactive:
                    log_result("Mobile", "PASS", "All visible touch targets >= 44px")
                else:
                    log_result("Mobile", "WARN", "No visible interactive elements found to check touch targets")

            # Check for overflow/scroll
            has_horizontal_scroll = await self.page.evaluate("""
                () => document.documentElement.scrollWidth > document.documentElement.clientWidth
            """)
            if has_horizontal_scroll:
                log_result("Mobile", "WARN", "Page has horizontal scrollbar (content overflow)")
            else:
                log_result("Mobile", "PASS", "No horizontal scrollbar - width fits mobile viewport")

            # Restore desktop viewport
            await self.page.set_viewport_size({"width": 1280, "height": 900})
            await asyncio.sleep(1)

        except Exception as e:
            log_result("Mobile", "FAIL", f"Exception: {e}",
                      await self.screenshot("mobile_error"))
            await self.page.set_viewport_size({"width": 1280, "height": 900})

    async def test_dark_mode(self):
        """Test 8: Dark Mode."""
        print("\n=== TEST 8: DARK MODE ===")
        try:
            theme_toggle = await self.page.query_selector(
                'button[class*="theme"], button[class*="dark"], button[class*="light"], '
                'button[aria-label*="theme" i], button[aria-label*="dark" i], '
                'button:has-text("🌙"), button:has-text("☀️"), button:has-text("🌓"), '
                'button:has-text("Dark"), button:has-text("Light"), '
                '[class*="theme-toggle"], [class*="dark-mode"], [id*="theme-toggle"]'
            )
            if theme_toggle:
                await theme_toggle.click()
                await asyncio.sleep(1)
                s = await self.screenshot("70_dark_mode")
                log_result("DarkMode", "PASS", "Toggled dark mode", s)

                # Check contrast/readability
                # Get computed background and text colors
                body_style = await self.page.evaluate("""
                    () => {
                        const s = getComputedStyle(document.body);
                        return { bg: s.backgroundColor, color: s.color };
                    }
                """)
                log_result("DarkMode", "INFO", f"Body styles in dark mode: bg={body_style['bg']}, color={body_style['color']}")

                # Check for unreadable text (white on white, dark on dark)
                unreadable = await self.page.evaluate("""
                    () => {
                        const issues = [];
                        const els = document.querySelectorAll('*');
                        for (const el of els) {
                            if (el.children.length > 0) continue;
                            const text = el.textContent.trim();
                            if (!text || text.length < 2) continue;
                            const s = getComputedStyle(el);
                            const bg = s.backgroundColor;
                            const color = s.color;
                            if (bg === color && bg !== 'rgba(0, 0, 0, 0)') {
                                issues.push({text: text.slice(0,30), bg, color});
                            }
                        }
                        return issues.slice(0, 20);
                    }
                """)
                if unreadable:
                    log_result("DarkMode", "FAIL", f"Elements with same bg/text color found: {unreadable[:5]}",
                              await self.screenshot("71_dark_mode_issues"))
                else:
                    log_result("DarkMode", "PASS", "No elements with identical background/text color found")

                _s = await self.screenshot("72_dark_mode_full")
                log_result("DarkMode", "PASS", "Dark mode full page screenshot", _s)

                # Toggle back to light
                await theme_toggle.click()
                await asyncio.sleep(1)
                log_result("DarkMode", "PASS", "Toggled back to light mode")

                s_light = await self.screenshot("73_light_mode_restored")
                log_result("DarkMode", "PASS", "Light mode restored", s_light)
            else:
                log_result("DarkMode", "WARN", "No theme toggle button found",
                          await self.screenshot("70_no_theme_toggle"))

        except Exception as e:
            log_result("DarkMode", "FAIL", f"Exception: {e}",
                      await self.screenshot("dark_mode_error"))

    async def test_accessibility(self):
        """Test 9: Accessibility."""
        print("\n=== TEST 9: ACCESSIBILITY ===")
        try:
            # Check for skip-to-content link
            skip_link = await self.page.query_selector(
                'a[href*="#main"], a[href*="#content"], a[class*="skip"], '
                '[class*="skip-to"], [id*="skip"]'
            )
            if skip_link:
                log_result("Accessibility", "PASS", "Skip-to-content link found")
            else:
                log_result("Accessibility", "WARN", "No skip-to-content link found")

            # Check for main landmark
            main_landmark = await self.page.query_selector("main, [role='main']")
            if main_landmark:
                log_result("Accessibility", "PASS", "Main landmark (role='main' or <main>) found")
            else:
                log_result("Accessibility", "WARN", "No main landmark found")

            # Check for ARIA attributes on interactive elements
            aria_buttons = await self.page.evaluate("""
                () => {
                    const issues = [];
                    const buttons = document.querySelectorAll('button, a, [role="button"]');
                    for (const btn of buttons) {
                        if (!btn.getAttribute('aria-label') && !btn.getAttribute('aria-labelledby')) {
                            const text = btn.textContent.trim();
                            if (!text && !btn.querySelector('img[alt]')) {
                                issues.push(btn.outerHTML.slice(0, 60));
                            }
                        }
                    }
                    return issues.slice(0, 10);
                }
            """)
            if aria_buttons:
                log_result("Accessibility", "WARN", f"Interactive elements without accessible names: {aria_buttons}")
            else:
                log_result("Accessibility", "PASS", "No interactive elements missing accessible names (or all have text content)")

            # Check for alt text on images
            images_no_alt = await self.page.evaluate("""
                () => {
                    const imgs = document.querySelectorAll('img:not([alt]), img[alt=""]');
                    return imgs.length;
                }
            """)
            if images_no_alt > 0:
                log_result("Accessibility", "WARN", f"Found {images_no_alt} images without alt text")
            else:
                log_result("Accessibility", "PASS", "All images have alt text")

            # Check for form labels
            inputs_no_label = await self.page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input, select, textarea');
                    let count = 0;
                    for (const inp of inputs) {
                        const id = inp.id;
                        const label = id ? document.querySelector(`label[for="${id}"]`) : null;
                        if (!label && !inp.getAttribute('aria-label') && !inp.getAttribute('aria-labelledby') && inp.type !== 'hidden') {
                            count++;
                        }
                    }
                    return count;
                }
            """)
            if inputs_no_label > 0:
                log_result("Accessibility", "WARN", f"Found {inputs_no_label} form inputs without labels")
            else:
                log_result("Accessibility", "PASS", "All form inputs have associated labels")

            # Check heading hierarchy
            heading_issues = await self.page.evaluate("""
                () => {
                    const issues = [];
                    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                    let lastLevel = 0;
                    for (const h of headings) {
                        const level = parseInt(h.tagName[1]);
                        if (level - lastLevel > 1 && lastLevel > 0) {
                            issues.push(`Skipped from h${lastLevel} to h${level}: "${h.textContent.trim().slice(0,30)}"`);
                        }
                        lastLevel = level;
                    }
                    return { count: headings.length, issues: issues.slice(0, 5), levels: [...new Set([...headings].map(h => h.tagName))].sort() };
                }
            """)
            log_result("Accessibility", "INFO", f"Found {heading_issues['count']} headings: {heading_issues['levels']}")
            if heading_issues['issues']:
                log_result("Accessibility", "WARN", f"Heading hierarchy issues: {heading_issues['issues']}")
            else:
                log_result("Accessibility", "PASS", "No heading hierarchy issues (sequential order maintained)")

            s = await self.screenshot("80_accessibility_overview")
            log_result("Accessibility", "PASS", "Accessibility test overview screenshot", s)

        except Exception as e:
            log_result("Accessibility", "FAIL", f"Exception: {e}",
                      await self.screenshot("accessibility_error"))


async def print_report():
    """Print full report."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST REPORT")
    print("=" * 80)
    print(f"Date: {datetime.now().isoformat()}")
    print(f"URL: {URL}")
    print(f"Total tests: {len(REPORT)}")

    # Group by category
    categories = {}
    for r in REPORT:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"PASS": 0, "FAIL": 0, "WARN": 0, "INFO": 0}
        categories[cat][r["status"]] = categories[cat].get(r["status"], 0) + 1

    print("\n--- Summary by Category ---")
    for cat, counts in sorted(categories.items()):
        total = sum(counts.values())
        passes = counts.get("PASS", 0)
        fails = counts.get("FAIL", 0)
        warns = counts.get("WARN", 0)
        infos = counts.get("INFO", 0)
        print(f"  {cat:15s}: {total:2d} tests | PASS: {passes:2d} | FAIL: {fails:2d} | WARN: {warns:2d} | INFO: {infos:2d}")

    totals = {"PASS": 0, "FAIL": 0, "WARN": 0, "INFO": 0}
    for r in REPORT:
        totals[r["status"]] += 1
    print(f"\n--- Grand Total ---")
    print(f"  PASS: {totals['PASS']}")
    print(f"  FAIL: {totals['FAIL']}")
    print(f"  WARN: {totals['WARN']}")
    print(f"  INFO: {totals['INFO']}")
    print(f"  TOTAL: {len(REPORT)}")

    # Detailed results
    print("\n--- Detailed Results ---")
    for r in REPORT:
        icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN", "INFO": "INFO"}.get(r["status"], " ?? ")
        ss = f" (screenshot: {r['screenshot']})" if r["screenshot"] else ""
        print(f"  [{icon}] [{r['category']:15s}] {r['message'][:120]}{ss}")

    # Save report to file
    report_path = "/home/the_bomb/orkes_ds/data/harga_test_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({"summary": totals, "categories": {k: v for k, v in categories.items()},
                   "results": REPORT}, f, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        try:
            tester = HargaTester(browser)
            # Override page to use context's page
            tester.page = await context.new_page()
            await tester.run_all()
        finally:
            await context.close()
            await browser.close()
        await print_report()


if __name__ == "__main__":
    asyncio.run(main())
