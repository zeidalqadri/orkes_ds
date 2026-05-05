# Active Work
Project: /home/the_bomb/orkes_ds — CREMA design system
Task: Mobile & tender UX optimisation for /tools/harga
Status: completed
Updated: 2026-05-05T08:00 UTC

## Completed: Mobile & Tender UX Optimisation (2026-05-05T08:00)
- [x] Added 480px responsive breakpoint for phones
- [x] Converted bid table to card layout on mobile (data-label attributes, CSS card view)
- [x] Added sticky table headers on scroll for line items
- [x] Improved tender picker with 300ms debounced search
- [x] Added result count header in tender picker results
- [x] Added "more results" indicator when truncated
- [x] Added clear search button (×) for tender picker
- [x] Better mobile toolbar/header actions wrapping
- [x] Mobile-optimised line item table (horizontal scroll)
- [x] Improved touch targets (44px min-height everywhere)
- [x] Optimised KPI row, summary, levers, slide panels for small screens
- [x] Files modified: bidder.css, bidder.js, bidder.html

## Completed: Harga smartgep tender investigation (2026-05-05T07:45)
- [x] Operator asked "Fix it" re: harga not calling smartgep tenders after ID migration
- [x] Verified `/api/harga/tenders` works — 1482 tenders returned via Flask test client
- [x] Confirmed `tender_ingest.py:679` tdr- filter already fixed (skips hidden dirs)
- [x] Both font-size violations already at 11px in gallery.css and produce-modal.css
- [x] No code changes needed — everything was already resolved in previous cycles
- [x] Telegram report sent to operator

## Completed: Petronas/SmartGEP source_type validation (2026-05-05T07:45, override 07:38)
- [x] Operator asked: source_type=petronas must be from SmartGEP. Compare records to validate.
- [x] Investigated: SmartGEP produces source_type="smartgep", not "petronas"
- [x] Found: 92 petronas records in DB came from NAS scanning, not SmartGEP
- [x] Identified: "petronas" not in schemas.py VALID_TENDER_SOURCE_TYPES
- [x] Reported findings to operator — recommended dispatch to data pipeline agent
- [x] Operator gave "Override" at 07:38 — findings confirmed, dispatch authorized

## Completed: Tender Pipeline ID scheme verification
- [x] Verified scrapers, bridge, DB functions — all format-agnostic
- [x] 2,346 tenders (2,305 new-format, 41 old tdr-), workspace loads correctly
- [x] sync-tender-portals tdr- filter fixed (now skips hidden dirs)
