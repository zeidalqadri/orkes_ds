# Arbos State
Updated: 2026-08-05T11:14 UTC

## Status: IDLE — hargai.roowang dropped per operator

### Last Completed: Outstanding clearing (2026-08-05T18:48 MYT)
Operator: "Clear outstanding". Actioned everything not operator-gated:
- .old cleanup DONE: 7 dirs (7.0G) moved to /mnt/data/trash-20260805/ (google-cloud-sdk, EasyOCR, torch, puppeteer, android-sdk, crawl4ai, swift — live symlinks verified on /mnt/data/caches). Disk 84% -> 83% (158G free).
- pm2 save DONE (dump.pm2 18:47).
- snapd_27406.snap confirmed ABSENT (resolved).
- hargai.roowang.com DROPPED (operator 19:12: "Consider dropping hargai.roowang given coverage done earlier"): ingress removed from ~/.cloudflared/config.json (backup config.json.bak-hargai-drop-*), tunnel restarted + pm2 save, JSON validated. DNS never existed so nothing was live; harga.work/vX covers ex-SmartGEP, hargai.zeidgeist.com retained as the live mirror. Post-restart: harga.roowang.com /vX /v9, harga.work /vX = 200; hargai.zeidgeist.com = 302.
- CF token cleanup Phase 3: still operator-gated — rotate BOTH CF tokens (dashboard); then pm2 restart harga-work-tunnel + pm2 save. journald 1.4G (was 3.9G), vacuum needs sudo (operator: sudo journalctl --vacuum-size=200M).
- Loop idle, GOAL empty, sites healthy (harga.roowang.com /vX /v9, harga.work /vX, hargai.zeidgeist.com), sec stack online.

## Recent Telegram chat
[2026-08-05T11:18] user: Check
[2026-08-05T11:19] user: include harga.work/vX in the https list and recognise the difference to harga.roowang.com/vX
[2026-08-05T11:21] user: hargai.roowang and hargai.zeidgeist are mirrors to harga.work
[2026-08-05T14:12] user: action on the self improving shared leanings
[2026-08-05T17:19] user: check
[2026-08-05T18:41] user: Clear outstanding
[2026-08-05T19:12] user: Consider dropping hargai.roowang given coverage done earlier
