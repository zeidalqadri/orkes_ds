Let me verify the responsive CSS changes.The claimed fix was never applied. The CSS at lines 285-289 still has `display: none` on `.lyric-col.py` at ≤700px with no landscape override. Let me fix it and also clean up the stale state files.Good, the CSS is correct. Now clean up state files and verify the HTML is valid.The prior agent claimed to fix this but never actually wrote the changes. Fixed now at `caodong-site/index.html:282-299`:

| Viewport | Layout |
|----------|--------|
| Base (>900px) | 3 columns: cn \| py \| en |
| ≤700px portrait | 2 columns: cn \| py (en hidden) |
| ≤480px portrait | Stacked: cn above py |
| Landscape (any width) | 3 columns: cn \| py \| en |

GOAL.md cleared, STATE.md updated.