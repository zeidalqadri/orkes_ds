W23b synthesis complete.

**Report**: `context/synthesizer/CONNECTIONS.md` — 5 insights, 10 action items, 6 risks.

Key findings:
1. **Builder learnings corrupted** — 18 duplicate retros, 0 real knowledge. Retro system has a dedup bug writing identical entries 3x per timestamp
2. **Crawler/Scout duplication** — 5 of 6 learnings are verbatim copies (no shared knowledge layer)
3. **1/11 experts records mistakes** — analyst is the only one. Reviewer, conductor, architect all had real failures with empty mistake files
4. **2-step bypass rule** — architect's independently-discovered pattern solves the fleet's dominant failure mode (passive waiting). Guardian waits 810m without escalating
5. **"Verify against actual code"** — independently rediscovered by 3 experts. Stale worktrees bit both reviewer and conductor

Goal cleared. Bot idle.