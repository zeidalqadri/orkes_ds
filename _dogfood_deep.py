#!/usr/bin/env python3
"""Deep-dive dogfood: extract HTML structure, mobile layout, and interactive elements."""

import asyncio, json
from playwright.async_api import async_playwright

BASE = "http://localhost:3636/tools/harga-v2"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()

        await page.goto(BASE, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Get full layout breakdown
        info = await page.evaluate("""
() => {
  const r = {};
  const vw = window.innerWidth, vh = window.innerHeight;
  r.viewport = `${vw}x${vh}`;
  r.scrollW = document.documentElement.scrollWidth;
  r.scrollH = document.documentElement.scrollHeight;
  r.hasHOverflow = r.scrollW > vw + 2;

  // Top-level layout sections
  const sections = [];
  document.querySelectorAll('body > *, #app > *, main > *, [class*="layout"] > *, section, [role="main"], [role="region"]').forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      sections.push({
        tag: el.tagName,
        id: el.id || '',
        cls: (typeof el.className === 'string' ? el.className : '').slice(0,60),
        rect: `${Math.round(rect.x)},${Math.round(rect.y)} ${Math.round(rect.width)}x${Math.round(rect.height)}`,
        visible: rect.top < vh && rect.bottom > 0
      });
    }
  });
  r.sections = sections;

  // All buttons and links with positions
  const interactives = [];
  document.querySelectorAll('button, a, input, textarea, [role="button"], [tabindex]:not([tabindex="-1"])').forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      interactives.push({
        tag: el.tagName,
        type: el.getAttribute('type') || '',
        text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0,50),
        rect: `${Math.round(rect.width)}x${Math.round(rect.height)}`,
        visible: rect.top < vh && rect.bottom > 0
      });
    }
  });
  r.interactives = interactives;

  // Check for specific features
  r.features = {
    chatInput: !!document.querySelector('input[type="text"], textarea, [contenteditable="true"]'),
    draggable: document.querySelectorAll('[draggable="true"]').length,
    tabs: document.querySelectorAll('[role="tab"]').length,
    canvasPanel: document.querySelectorAll('[class*="canvas" i]').length,
    sidebar: document.querySelectorAll('[class*="sidebar" i], [class*="side" i], aside').length,
    table: document.querySelectorAll('table, [class*="table" i], [class*="grid" i]').length,
    card: document.querySelectorAll('[class*="card" i]').length,
    badge: document.querySelectorAll('[class*="badge" i]').length,
    modal: document.querySelectorAll('[class*="modal" i], [class*="dialog" i]').length,
  };

  // Text of first few visible elements for content understanding
  const visibleTexts = [];
  document.querySelectorAll('h1, h2, h3, h4, p, label, th, td, [class*="title"], [class*="heading"]').forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.top < vh && rect.bottom > 0) {
      const t = (el.innerText || '').trim().slice(0,80);
      if (t) visibleTexts.push({tag: el.tagName, text: t, cls: (el.className || '').slice(0,30)});
    }
  });
  r.visibleTexts = visibleTexts;

  // Check for mobile-specific issues
  r.mobileIssues = [];

  // Check sticky/fixed elements that could overlap
  const fixed = document.querySelectorAll('[style*="fixed"], [style*="sticky"], .fixed, .sticky');
  r.fixedElements = fixed.length;

  // Check font sizes on body text
  const bodyStyle = window.getComputedStyle(document.body);
  r.bodyFontSize = bodyStyle.fontSize;

  // Check meta viewport tag
  const vpMeta = document.querySelector('meta[name="viewport"]');
  r.viewportMeta = vpMeta ? vpMeta.getAttribute('content') : 'MISSING';
  if (!vpMeta) r.mobileIssues.push('Missing viewport meta tag');

  return r;
}
""")

        print(json.dumps(info, indent=2))

        # Summary
        print(f"\n{'='*60}")
        print(f"MOBILE DOGFOOD SUMMARY")
        print(f"{'='*60}")
        print(f"Viewport: {info['viewport']} | Scroll: {info['scrollW']}x{info['scrollH']}")
        print(f"Horizontal overflow: {'YES ⚠️' if info['hasHOverflow'] else 'None ✅'}")
        print(f"Viewport meta: {info['viewportMeta']}")
        print(f"Body font size: {info['bodyFontSize']}")
        print(f"Fixed/sticky elements: {info['fixedElements']}")
        print(f"\nFeatures detected:")
        for k, v in info['features'].items():
            print(f"  {k}: {v}")
        print(f"\nInteractive elements visible on screen:")
        for el in info['interactives']:
            if el['visible'] and el['text']:
                print(f"  <{el['tag']}> {el['text'][:50]} [{el['rect']}]")
        print(f"\nVisible headings/text:")
        for t in info['visibleTexts'][:20]:
            print(f"  {t['tag']}: {t['text']}")

        await browser.close()

asyncio.run(main())
