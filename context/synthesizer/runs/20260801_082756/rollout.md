CONNECTIONS.md updated for W32. Here's what changed from the previous version:

**New recurring failures:**
- **Pattern E**: 429/provider cascade — when one provider rate-limits, agents cascade without backoff or circuit breaker. No graceful degradation exists.
- **Pattern D** (institutional knowledge loss) escalated to HIGH — builder still logging empty "Build X" entries across multiple months with zero improvement.

**New knowledge gaps:**
- **Gap 5**: Crawler/scout regex extraction patterns (58% hit rate) not reaching sec-webdav-intel, which classifies 86% of files as "other" using a filename-only heuristic.
- **Gap 6**: Albert's L0→L3 evolution framework (Watchman→Medic→Helpdesk) is a reusable maturity model for all monitoring agents but hasn't been captured.

**New bottlenecks:**
- **Bottleneck 5**: Single-provider LLM dependency with no circuit breaker — 429 from one provider halts all agents.
- **Bottleneck 6**: Memory pressure creates cascading failures — sec-webdav-intel leak (77→3902MB) pushed swap to 99%, degrading all services. No aggregate monitoring exists.

**New successful patterns:**
- **Pattern 7**: Bot maturity model L0→L3 — standardize across jaga, devops, guardian, Albert.
- **Pattern 8**: Reinforced "direct action after 2+ blocked steps" rule.

**3 new action items** and risk flags updated to HIGH for 429 cascade and memory monitoring gaps.