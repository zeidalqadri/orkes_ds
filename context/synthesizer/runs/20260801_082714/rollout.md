W32 CONNECTIONS.md written. 5 insights, 13 action items.

The most actionable finding: **builder's learnings.md is still rotten (6th week)**, but the Telegram chat from Jul 28-Aug 1 contains ~15 concrete learnings that should re-seed it — Albert architecture, DeepSeek migration, webdav pipeline, memory leak diagnosis. The knowledge exists, it's just in the wrong place.

Second-most: **the /restart clean-exit bug** is a one-line fix (`sys.exit(1)` instead of `sys.exit(0)`) that affects 3+ agents. PM2 treats exit code 0 as intentional and won't autorestart.