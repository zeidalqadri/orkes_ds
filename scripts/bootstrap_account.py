#!/usr/bin/env python3
"""One-shot Playwright login to bootstrap cookie file for any SmartGEP account.

Usage:
    python scripts/bootstrap_account.py dyna-segmen
    python scripts/bootstrap_account.py --all   # bootstrap all enabled accounts
"""
import asyncio
import json
import sys
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path

ACCOUNTS_PATH = Path("/home/the_bomb/orkes/yellowpages/scrapers/smartgep_accounts.json")
COOKIES_DIR = Path("/home/the_bomb/orkes/yellowpages/scrapers/data")


async def bootstrap(account_id: str) -> bool:
    """Login to SmartGEP for account_id and save cookies."""
    data = json.loads(ACCOUNTS_PATH.read_text())
    acct = None
    for a in data["accounts"]:
        if a["id"] == account_id:
            acct = a
            break
    if not acct:
        print(f"[bootstrap] Account '{account_id}' not found")
        return False
    if not acct.get("enabled", True):
        print(f"[bootstrap] Account '{account_id}' is disabled — skipping")
        return False

    print(f"[bootstrap] Logging in as {account_id} ({acct['username'][:5]}***)")
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        )
        page = await ctx.new_page()

        print("[bootstrap] Navigating to idplogin...")
        await page.goto("https://idplogin.gep.com", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        username_input = page.locator('input[id="userId"]').first
        if await username_input.is_visible(timeout=5000):
            await username_input.fill(acct["username"])
            print("[bootstrap] Username entered")
        else:
            print("[bootstrap] Username field not found")
            await browser.close()
            return False

        pw_btn = page.locator('button:has-text("Login with Password")').first
        if await pw_btn.is_visible(timeout=3000):
            await pw_btn.click()
            await page.wait_for_timeout(3000)
            print("[bootstrap] Login with Password clicked")

        pw_input = page.locator('input[type="password"]').first
        if await pw_input.is_visible(timeout=5000):
            await pw_input.fill(acct["password"])
            print("[bootstrap] Password entered")
        else:
            print("[bootstrap] Password field not found")
            await browser.close()
            return False

        login_btn = page.locator('button[type="submit"]').first
        if await login_btn.is_visible(timeout=3000):
            await login_btn.click()
        else:
            await pw_input.press("Enter")
        print("[bootstrap] Login submitted, waiting for SSO redirect...")

        for i in range(30):
            await page.wait_for_timeout(2000)
            url = page.url.lower()
            if "businessnetwork.gep.com" in url and "login" not in url:
                print(f"[bootstrap] Authenticated to BizNet after {(i+1)*2}s")
                break
        else:
            print("[bootstrap] SSO redirect timeout — check credentials")
            await browser.close()
            return False

        cookies = await ctx.cookies()
        cookie_list = []
        for c in cookies:
            cookie_list.append({
                "name": c["name"], "value": c["value"],
                "domain": c["domain"].lstrip("."),
                "path": c.get("path", "/"),
                "secure": c.get("secure", True),
                "httpOnly": c.get("httpOnly", False),
            })

        cookie_path = COOKIES_DIR / f"smartgep_cookies_{account_id}.json"
        COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        cookie_path.write_text(json.dumps({
            "cookies": cookie_list,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))
        cookie_path.chmod(0o600)
        print(f"[bootstrap] Saved {len(cookie_list)} cookies to {cookie_path}")

        await browser.close()
        return True


def main():
    parser = ArgumentParser(description="Bootstrap SmartGEP account cookie files")
    parser.add_argument("account", nargs="?", help="Account ID (e.g., dyna-segmen)")
    parser.add_argument("--all", action="store_true", help="Bootstrap all enabled accounts")
    args = parser.parse_args()

    if args.all:
        data = json.loads(ACCOUNTS_PATH.read_text())
        for acct in data["accounts"]:
            if acct.get("enabled", True):
                cookie_path = COOKIES_DIR / f"smartgep_cookies_{acct['id']}.json"
                if cookie_path.exists():
                    print(f"[skip] {acct['id']}: cookie file exists")
                    continue
                asyncio.run(bootstrap(acct["id"]))
    elif args.account:
        asyncio.run(bootstrap(args.account))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
