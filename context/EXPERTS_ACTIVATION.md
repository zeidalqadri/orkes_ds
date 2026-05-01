# Expert Fleet Activation

**Date:** 2026-04-28
**Status:** 17 experts inventoried in `context/experts.json`, all currently stopped. Fleet is local-only (bot.json `expert_sources: ["local"]`) — no Nirwana global experts loaded.

## Fleet Overview

| Priority | Expert | Capability | Skill File |
|----------|--------|------------|------------|
| P1 | builder | Dev/deploy/restart services | `~/.claude/skills/builder/SKILL.md` |
| P1 | enricher | Batch enrichment | `~/.claude/skills/enricher/SKILL.md` |
| P1 | debugger | Pipeline troubleshooting | `~/.claude/skills/debugger/SKILL.md` |
| P1 | harvester | SERP/linkedin crawl | `~/.claude/skills/harvester/SKILL.md` |
| P1 | verifier | LLM review/confidence upgrade | `~/.claude/skills/verifier/SKILL.md` |
| P2 | analyst | Data quality reports | `~/.claude/skills/analyst/SKILL.md` |
| P2 | deduplicator | Identity resolution | `~/.claude/skills/deduplicator/SKILL.md` |
| P2 | guardian | Backup/DB safety | `~/.claude/skills/guardian/SKILL.md` |
| P2 | ops | Infrastructure health | `~/.claude/skills/ops/SKILL.md` |
| P2 | reporter | Progress reports | `~/.claude/skills/reporter/SKILL.md` |
| P2 | scheduler | Pipeline orchestration | `~/.claude/skills/scheduler/SKILL.md` |
| P3 | architect | Code architecture analysis | `~/.claude/skills/architect/SKILL.md` |
| P3 | codex | Vision-based UI audit | `~/.claude/skills/codex/SKILL.md` |
| P3 | designer | Interface design | `~/.claude/skills/design-an-interface/SKILL.md` |
| P3 | qa | Bug filing | `~/.claude/skills/qa/SKILL.md` |
| P3 | tdd | Test-first development | `~/.claude/skills/tdd/SKILL.md` |
| P2 | elliot | Offensive security / pentesting / social engineering / SmartGEP scraper countermeasures | `~/.claude/skills/elliot/SKILL.md` |

## Activation Protocol

### Prerequisites
1. Expert skill SKILL.md exists with valid frontmatter
2. Expert registered in `context/experts.json`
3. Fleet status tracked in `context/.fleet_status.json`

### Activation Flow
1. Parent agent identifies sub-task suitable for expert delegation
2. Compress current context to < 2000 tokens
3. Load expert skill: `skill` tool with expert name
4. Spawn via `task` tool with `subagent_type: general`
5. Full handoff spec per Sub-Task Handoff protocol
6. Expert returns result; parent verifies and integrates

### Phase 2 Activation Plan (first 3 experts)
1. `builder` — first to activate (highest utility for dev workflow)
2. `enricher` — core business function
3. `debugger` — incident response

### Phase 3 Activation (next 5 experts)
4. `harvester` — data collection
5. `verifier` — quality control
6. `analyst` — insights
7. `scheduler` — orchestration
8. `ops` — monitoring

### Activation Monitoring
- Check `.fleet_status.json` for expert step counts
- Active expert = step_count > 0 in current session
- Failed activation = 3 consecutive failures → escalate to operator

### Status
All 17 experts at 0 steps. No activations occurred yet. P1 experts (builder, enricher, debugger, harvester, verifier) are the highest priority for first activation. Elliot (P2) is the newest addition — a world-class offensive security engineer for scraper countermeasures (SmartGEP Angular SPA bypass, BizNet SSO gates, anti-bot evasion), social engineering (alumni contact manipulation), and general pentesting/reverse engineering. Codex (P3) requires a vision-capable LLM backend to be configured (see `scripts/codex_audit.py --check`). The `dsdeepthink` and Nirwana orchestration fleet (conductor, reviewer, scout, etc.) are NOT loaded — this project uses local skill-based experts only.
