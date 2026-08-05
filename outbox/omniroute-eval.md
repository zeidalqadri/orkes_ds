# OmniRoute Eval — diegosouzapw/OmniRoute

**Date**: 2026-08-04
**Verdict**: **HOLD**
**Evaluated by**: arbos (orkes_ds2)

---

## What It Is

OmniRoute is a MIT-licensed, self-hosted, OpenAI-compatible API gateway (Node.js/Next.js) that sits as a local proxy (`localhost:20128/v1`) and routes LLM requests to 290+ AI providers (90+ free tiers, 500+ models). Key features:

- 19 routing strategies (priority, cost-optimized, auto-fallback, weighted, round-robin…)
- 4-tier cascade: Subscription → API Key → Cheap → Free
- RTK + Caveman stacked compression (15–95% token savings, ~89% avg)
- Circuit breakers, key cooldown, model lockout (3-layer resilience)
- MCP/A2A, persistent memory, guardrails, evals
- Desktop app (Electron), PWA, Docker, npm
- ~1.53B documented free tokens/month across 43 provider pools
- OpenCode listed as compatible (npm plugin: `@omniroute/opencode-provider`)

## Drop-In Fit Assessment

### Current setup (post Flash migration, 2026-08-04)

| Component | Current |
|---|---|
| Default model | `deepseek/deepseek-v4-flash` |
| Model policy routes | `primary_execution: openrouter/owl-alpha`, `lightweight_routing: openrouter/owl-alpha` |
| API endpoint | `https://api.deepseek.com/v1` (direct, no proxy) |
| Config files | `~/.config/opencode/opencode.json`, `~/.config/opencode/model_policy.json`, `orkes_ds/.env` |
| Pricing | ~$0.028/$0.11 per M tokens (Flash) |

### What a swap would change

OmniRoute would be added as an OpenAI-compatible provider in `opencode.json`:

```diff
# opencode.json — add new provider block
+ "omniroute": {
+   "npm": "@ai-sdk/openai-compatible",
+   "name": "OmniRoute Gateway",
+   "options": {
+     "baseURL": "http://localhost:20128/v1",
+     "apiKey": "sk-any-value"
+   },
+   "models": {
+     "auto": { "name": "OmniRoute Auto" }
+   }
+ }
```

```diff
# model_policy.json — reroute primary execution
- "primary_execution": "openrouter/owl-alpha",
+ "primary_execution": "omniroute/auto",
```

```diff
# orkes_ds/.env — no change needed (OmniRoute manages its own keys)
```

Additionally:
- Install `@omniroute/opencode-provider` npm package, or run OmniRoute server separately via pm2
- OmniRoute manages API keys internally (AES-256-GCM encrypted in its own `.env`)
- DeepSeek API key would be registered inside OmniRoute, not in OpenCode's provider config

**Critical finding**: The OpenCode-specific integration path (`docs/integrations/opencode.md`) returns 404 from the repo — the page does not exist. The npm package `@omniroute/opencode-provider` exists but integration docs are missing. The generic OpenAI-compatible path (baseURL override) works for any OpenAI-compatible tool and is the tested path for OpenCode.

## Decision Benchmark

### Cost delta

| Scenario | Monthly cost (est.) |
|---|---|
| Current: V4 Flash, ~2M tokens/month (agent loop) | ~$0.28 input + output |
| With OmniRoute: free-tier providers (Mistral 1B, OpenCode Zen, Kilo, Gemini Flash) as primary, DeepSeek Flash as fallback | ~$0 (free tiers) to ~$0.28 (if all fallback) |

Annual savings: ~$3–$10. Not material.

### Redundancy gain

- **Does it fix a live problem?** No. The arbos pm2 loop has zero recorded provider outages. DeepSeek Flash has been reliable. OpenRouter owl-alpha has not been load-tested but is configured.
- **What it adds**: True multi-provider failover. If DeepSeek goes down, OmniRoute silently reroutes to Anthropic/Gemini/Mistral/Groq/etc.
- **Is this insurance worth it?** Marginal. The agent loop is a single low-throughput process. If the provider fails, the pm2 loop pauses — no revenue impact, no SLA, no production user-facing service goes down.

### Latency overhead

- Local proxy hop: <1ms (loopback interface)
- Routing strategy evaluation: 5-50ms (model catalog lookup + strategy scoring)
- Compression (RTK + Caveman): CPU-bound, 50-500ms depending on token count, but reduces network transfer time
- Net: negligible for a non-interactive loop. For the operator's interactive `claude` sessions, could add perceptible lag during compression.

### Blast radius

- **New failure surface**: OmniRoute server (Node.js process) is a single point of failure. If it crashes, ALL LLM calls fail — the pm2 loop halts.
- **Mitigation**: OmniRoute has its own circuit breakers and is self-hosted (you restart it). But it adds one more thing to monitor and manage.
- **Ops overhead**: Another pm2 service to maintain, another `~/.env` to secure, another npm package to keep updated (v3.8.50 as of now, 5,968 commits, rapid development velocity).
- **Security surface**: 290+ provider integrations, OAuth flows, session tokens, web cookie crawling for keyless providers. Massive attack surface for a tool that only needs to call ONE API. Most free-tier providers have ToS clauses prohibiting proxy/relay use (OmniRoute's own FREE_TIERS.md flags 15+ providers as "avoid" for this reason).

### Complexity assessment

OmniRoute is 5,968 commits, ~500 contributors, a full Next.js stack with dashboard, Electron app, MCP server, A2A protocol, memory system, guardrails, 12 compression engines. For a single `claude -p` loop that calls DeepSeek Flash ~100x/day, this is a nuclear flyswatter.

## Verdict: HOLD

OmniRoute is impressive OSS engineering solving a real problem (provider lock-in, rate-limit hell, surprise bills) for developers burning hundreds of dollars/month across multiple providers and coding tools. It is not the right tool for this setup.

**This setup needs**: One reliable coding model, one endpoint, lowest possible ops burden.
**OmniRoute provides**: 290 providers, multi-tier routing, compression, MCP, A2A, dashboard, desktop app.

The mismatch is architectural, not technical. OmniRoute is a complex adapter layer for a complex multi-provider world. The arbos loop lives in a simple single-provider world. Adding OmniRoute would increase ops burden, attack surface, and failure modes for a savings of ~$10/year.

### When to revisit

1. If DeepSeek Flash quality degrades below useful threshold for the agent loop
2. If costs exceed $50/month and free-tier aggregation becomes material
3. If the loop diversifies into task-specific model routing (heavy reasoning vs. fast triage vs. multimodal)
4. If OpenCode ships first-class OmniRoute integration (the `@omniroute/opencode-provider` plugin matures)

### Similar, lighter alternatives to monitor

- **LiteLLM** (Python, MIT) — lighter proxy, fewer providers, same OpenAI-compatible pattern. Better fit for Python-heavy stacks.
- **Single-provider direct**: Current setup. Zero ops overhead, zero failure surface. Stay here until a problem emerges.

---

## Config Correction: CONTEXT.md

CONTEXT.md still documents DeepSeek V4 Pro as current model. The operator confirmed ("No deepseek pro. All flash now") and `opencode.json` confirms `"model": "deepseek/deepseek-v4-flash"`. CONTEXT.md should be updated to reflect the Flash migration.

## Verification Defect Fix

See appended correction in `context/shared_learnings.md`.
