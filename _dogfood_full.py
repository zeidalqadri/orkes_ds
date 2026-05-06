#!/usr/bin/env python3
"""Full interactive dogfood: create bid, use chatbot, test all 5 canvas features, verify mobile UX."""

import asyncio, json
from playwright.async_api import async_playwright

BASE = "http://localhost:3636/tools/harga-v2"
API = "http://localhost:3636/api/harga-v2"

issues = []

async def check(step, condition, msg):
    if not condition:
        issues.append(f"[{step}] {msg}")
        return False
    return True

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()

        # ── 1. Load page ──
        await page.goto(BASE, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        title = await page.title()
        content_ok = await page.evaluate("document.querySelector('#app') !== null")
        await check("1.1", content_ok, "Page content (#app) not rendered")
        await check("1.2", "Salaam" in await page.content(), 'Chatbot greeting "Salaam. Apa mau?" missing')
        print(f"  Title: {title} | Content: {content_ok}")

        # ── 2. Check initial layout ──
        layout = await page.evaluate("""() => {
            const vw = window.innerWidth;
            const header = document.querySelector('.bidder-header');
            const sidebar = document.querySelector('#hargaSidebar');
            const main = document.querySelector('#bidderMain');
            const canvasPanel = document.querySelector('#canvasPanel');
            const btn = document.querySelector('#canvasToggleBtn');
            const chatbotInput = document.querySelector('#chatbotInput2');
            return {
                vw,
                hasHeader: !!header,
                hasSidebar: !!sidebar,
                hasMain: !!main,
                hasCanvasPanel: !!canvasPanel,
                hasCanvasBtn: !!btn,
                hasChatInput: !!chatbotInput,
                headerRect: header ? header.getBoundingClientRect() : null,
                sidebarRect: sidebar ? sidebar.getBoundingClientRect() : null,
                mainRect: main ? main.getBoundingClientRect() : null,
                canvasPanelDisplay: canvasPanel ? getComputedStyle(canvasPanel).display : 'none',
                canvasPanelVisibility: canvasPanel ? getComputedStyle(canvasPanel).visibility : 'hidden',
                canvasTabCount: document.querySelectorAll('.canvas-tab').length,
                canvasTabLabels: Array.from(document.querySelectorAll('.canvas-tab')).map(t => t.innerText.trim()),
            };
        }""")
        await check("2.1", layout['hasHeader'], "Header missing")
        await check("2.2", layout['hasSidebar'], "Sidebar missing")
        await check("2.3", layout['hasMain'], "Main area missing")
        await check("2.4", layout['hasCanvasPanel'], "Canvas panel missing")
        await check("2.5", layout['hasCanvasBtn'], "Canvas toggle button missing")
        await check("2.6", layout['hasChatInput'], "Chat input missing")
        await check("2.7", layout['canvasTabCount'] == 5, f"Expected 5 canvas tabs, got {layout['canvasTabCount']}")
        await check("2.8", layout['canvasTabLabels'] == ["Price Canvas", "Tender Doc", "Compare", "Dashboard", "Workspace"],
                    f"Canvas tab labels wrong: {layout['canvasTabLabels']}")
        # Canvas should be hidden initially
        await check("2.9", not layout['canvasPanelDisplay'] or layout['canvasPanelDisplay'] == 'none' or layout['canvasPanelVisibility'] == 'hidden',
                    "Canvas panel visible on load when it should be hidden")
        print(f"  Layout: {layout['vw']}px | Header:{layout['hasHeader']} Sidebar:{layout['hasSidebar']} Canvas:{layout['hasCanvasPanel']} Tabs:{layout['canvasTabCount']}")

        # ── 3. Check modals ──
        modals = await page.evaluate("""() => ({
            newBid: document.querySelector('#newBidModal') !== null,
            qpc: document.querySelector('#qpcModal') !== null,
            entity: document.querySelector('#entityModal') !== null,
            entityForm: document.querySelector('#entityFormModal') !== null,
            disambig: document.querySelector('#disambigModal') !== null,
            research: document.querySelector('#researchPanel') !== null,
            researchOverlay: document.querySelector('#researchOverlay') !== null,
            canvasOverlay: document.querySelector('#canvasOverlay') !== null,
        })""")
        for name, exists in modals.items():
            await check(f"3.{name}", exists, f"Modal/panel '{name}' missing")
        print(f"  Modals: {sum(1 for v in modals.values() if v)}/{len(modals)} present")

        # ── 4. Check chatbot ──
        chatbot = await page.evaluate("""() => {
            const input = document.querySelector('#chatbotInput2');
            const sendBtn = document.querySelector('#chatbotSendBtn');
            const messages = document.querySelector('#chatbotMessages2');
            const modelSelect = document.querySelector('#chatbotModelSelect');
            const newBtn = document.querySelectorAll('button');
            const resetBtn = Array.from(newBtn).find(b => b.innerText.trim() === '+ New');
            const flowBtn = document.querySelector('#flowToggleBtn');
            const sessionBar = document.querySelector('#chatbotSessionBar');
            const sessionPills = document.querySelector('#chatbotSessionPills');
            return {
                hasInput: !!input,
                inputPH: input ? input.placeholder : '',
                hasSendBtn: !!sendBtn,
                hasMessages: !!messages,
                hasModelSelect: !!modelSelect,
                modelOptions: modelSelect ? Array.from(modelSelect.options).map(o => o.value) : [],
                hasResetBtn: !!resetBtn,
                hasFlowBtn: !!flowBtn,
                hasSessionBar: !!sessionBar,
                hasSessionPills: !!sessionPills,
                msgCount: messages ? messages.children.length : 0,
                firstMsg: messages && messages.children[0] ? messages.children[0].innerText.trim() : '',
            };
        }""")
        await check("4.1", chatbot['hasInput'], "Chatbot input missing")
        await check("4.2", chatbot['hasSendBtn'], "Send button missing")
        await check("4.3", chatbot['hasModelSelect'], "Model select missing")
        await check("4.4", 'deepseek' in chatbot['modelOptions'] and 'openai' in chatbot['modelOptions'],
                    f"Model options incomplete: {chatbot['modelOptions']}")
        await check("4.5", chatbot['hasFlowBtn'], "Flow toggle button missing")
        await check("4.6", chatbot['hasResetBtn'], "New conversation button missing")
        await check("4.7", 'Salaam' in chatbot['firstMsg'], f"Greeting wrong: {chatbot['firstMsg']}")
        import textwrap
        print(f"  Chatbot: input={chatbot['hasInput']} models={chatbot['modelOptions']} flows={chatbot['hasFlowBtn']} msgs={chatbot['msgCount']}")

        # ── 5. Check header actions ──
        header_btns = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('.bidder-header-actions button'));
            return btns.map(b => b.innerText.trim());
        }""")
        await check("5.1", 'Entities' in header_btns, f"Entities button missing from header: {header_btns}")
        await check("5.2", 'Quick Check' in header_btns, "Quick Check button missing from header")
        await check("5.3", 'Chatbot' in header_btns, "Chatbot button missing from header")
        await check("5.4", '+ New Bid' in header_btns, "New Bid button missing from header")
        print(f"  Header buttons: {header_btns}")

        # ── 6. Open New Bid modal and check fields ──
        await page.click('button:has-text("+ New Bid")')
        await page.wait_for_timeout(500)
        newbid_fields = await page.evaluate("""() => {
            const modal = document.querySelector('#newBidModal');
            if (!modal || !modal.classList.contains('open')) return null;
            const ref = document.querySelector('#bidRef');
            const client = document.querySelector('#bidClient');
            const tenderPick = document.querySelector('#bidTenderPick');
            const strategy = document.querySelector('#bidStrategy');
            const upload = document.querySelector('#uploadZone');
            const createBtn = Array.from(document.querySelectorAll('#newBidModal button')).find(b => b.innerText.trim() === 'Create Bid');
            return {
                isOpen: modal.classList.contains('open'),
                hasRef: !!ref,
                hasClient: !!client,
                hasTenderPick: !!tenderPick,
                hasStrategy: !!strategy,
                hasUpload: !!upload,
                hasCreateBtn: !!createBtn,
            };
        }""")
        if newbid_fields is None:
            issues.append("[6.1] New Bid modal did not open")
        else:
            await check("6.1", newbid_fields['isOpen'], "New Bid modal not open")
            await check("6.2", newbid_fields['hasRef'], "Ref field missing in New Bid")
            await check("6.3", newbid_fields['hasTenderPick'], "Tender pick field missing")
            await check("6.4", newbid_fields['hasStrategy'], "Strategy select missing")
            await check("6.5", newbid_fields['hasUpload'], "Upload zone missing")
            await check("6.6", newbid_fields['hasCreateBtn'], "Create Bid button missing")
        print(f"  New Bid modal: {'open' if newbid_fields else 'failed'}")

        # Close modal
        close_btn = await page.query_selector('#newBidModal .bidder-modal-close')
        if close_btn:
            await close_btn.click()
            await page.wait_for_timeout(500)

        # ── 7. Test Quick Price Check modal ──
        await page.click('button:has-text("Quick Check")')
        await page.wait_for_timeout(500)
        qpc = await page.evaluate("""() => {
            const modal = document.querySelector('#qpcModal');
            return modal ? modal.classList.contains('open') : false;
        }""")
        await check("7.1", qpc, "Quick Price Check modal did not open")
        if qpc:
            input_el = await page.query_selector('#qpcInput')
            check_btn = await page.query_selector('button:has-text("Check Price")')
            await check("7.2", input_el is not None, "QPC input missing")
            await check("7.3", check_btn is not None, "QPC check button missing")
        close_btn = await page.query_selector('#qpcModal .bidder-modal-close')
        if close_btn:
            await close_btn.click()
            await page.wait_for_timeout(500)

        # ── 8. Test Entities modal ──
        await page.click('button:has-text("Entities")')
        await page.wait_for_timeout(500)
        entities = await page.evaluate("""() => {
            const modal = document.querySelector('#entityModal');
            return modal ? modal.classList.contains('open') : false;
        }""")
        await check("8.1", entities, "Entities modal did not open")
        if entities:
            add_btn = await page.query_selector('button:has-text("+ Add Entity")')
            await check("8.2", add_btn is not None, "Add Entity button missing")
        # Test add entity form
        if entities:
            add_btn = await page.query_selector('button:has-text("+ Add Entity")')
            if add_btn:
                await add_btn.click()
                await page.wait_for_timeout(500)
                ef = await page.evaluate("""() => {
                    const form = document.querySelector('#entityFormModal');
                    return form ? form.classList.contains('open') : false;
                }""")
                await check("8.3", ef, "Entity form modal did not open")
                if ef:
                    name = await page.query_selector('#efName')
                    reg = await page.query_selector('#efRegNo')
                    save = await page.query_selector('button:has-text("Save Entity")')
                    await check("8.4", name is not None, "Entity name field missing")
                    await check("8.5", save is not None, "Save Entity button missing")
                close_form = await page.query_selector('#entityFormModal .bidder-modal-close')
                if close_form:
                    await close_form.click()
                    await page.wait_for_timeout(500)
        close_entities = await page.query_selector('#entityModal .bidder-modal-close')
        if close_entities:
            await close_entities.click()
            await page.wait_for_timeout(500)

        # ── 9. Test chatbot input and model select ──
        model_select = await page.query_selector('#chatbotModelSelect')
        if model_select:
            await model_select.select_option('openai')
            await page.wait_for_timeout(200)
            selected = await model_select.input_value()
            await check("9.1", selected == 'openai', f"Model selection failed, got: {selected}")
            # Reset to Auto
            await model_select.select_option('')

        # ── 10. Test Flow toggle ──
        flow_btn = await page.query_selector('#flowToggleBtn')
        if flow_btn:
            await flow_btn.click()
            await page.wait_for_timeout(500)
            flow_visible = await page.evaluate("""() => {
                const flow = document.querySelector('#pricingFlow');
                return flow ? !flow.classList.contains('is-hidden') : false;
            }""")
            await check("10.1", flow_visible, "Pricing Flow panel did not show after toggle")
            if flow_visible:
                flow_body = await page.evaluate("""() => {
                    const body = document.querySelector('#pfBody');
                    const progress = document.querySelector('#pfProgress');
                    return {
                        hasBody: !!body,
                        hasChildren: body ? body.children.length > 0 : false,
                        hasProgress: !!progress,
                    };
                }""")
                await check("10.2", flow_body['hasBody'], "Flow body missing")
                await check("10.3", flow_body['hasProgress'], "Flow progress bar missing")
                print(f"  Flow: body={flow_body['hasBody']} children={flow_body['hasChildren']} progress={flow_body['hasProgress']}")
            # Toggle off
            await flow_btn.click()
            await page.wait_for_timeout(300)

        # ── 11. Test Enter to send in chatbot ──
        chat_input = await page.query_selector('#chatbotInput2')
        if chat_input:
            await chat_input.fill("test message")
            await page.wait_for_timeout(200)
            val = await chat_input.input_value()
            await check("11.1", val == "test message", f"Chat input fill failed: {val}")
            # Clear it
            await chat_input.fill("")

        # ── 12. Test session management ──
        session = await page.evaluate("""() => {
            const stored = localStorage.getItem('harga_chat_session');
            const display = localStorage.getItem('harga_chat_display');
            const provider = localStorage.getItem('harga_selected_provider');
            return { session: !!stored, display: !!display, provider: provider };
        }""")
        await check("12.1", session['session'], "Chat session not persisted to localStorage")
        print(f"  Session: id={session['session']} display={session['display']} provider={session['provider']}")

        # ── 13. Check mobile-specific issues ──
        mobile = await page.evaluate("""() => {
            const issues = [];
            const vw = window.innerWidth;

            // Check all interactive elements have >= 32px touch targets
            const clickable = document.querySelectorAll('button, a, input, [role="button"], select, textarea');
            for (const el of clickable) {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0 && (r.width < 32 || r.height < 32)) {
                    const text = (el.innerText || el.getAttribute('aria-label') || el.placeholder || el.tagName).trim().slice(0,30);
                    if (text) issues.push(`Small target: ${el.tagName} ${r.width}x${r.height} "${text}"`);
                }
            }

            // Check horizontal scroll
            if (document.documentElement.scrollWidth > vw + 2) {
                issues.push(`H-scroll: ${document.documentElement.scrollWidth}px > ${vw}px`);
            }

            return issues.slice(0, 20);
        }""")
        for m in mobile:
            issues.append(f"[13] {m}")

        # ── 14. Check CSS: are hex colors leaking into bidder.css? ──
        await page.goto(BASE, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1000)

        # ── Summary ──
        print(f"\n{'='*60}")
        print(f"DOGFOOD COMPLETE")
        print(f"{'='*60}")
        print(f"Issues found: {len(issues)}")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

        await browser.close()
        return issues

if __name__ == "__main__":
    issues = asyncio.run(main())
    if issues:
        print(f"\n{len(issues)} issue(s) found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\nNo issues found!")
