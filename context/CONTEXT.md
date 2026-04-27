# DeepSeek V4 Flash Config

## Applied Changes (2026-04-27)

### What changed
Agent backend switched from `deepseek/deepseek-v4-pro` (Pro) to `deepseek/deepseek-v4-flash` (Flash) for all agent loop steps.

### Files modified
- `orkes_ds/.env` — `OPENCODE_MODEL=deepseek/deepseek-v4-flash`
- `~/.config/opencode/opencode.json` — default model → flash, `deepfix` cmd pinned to pro
- `~/.config/opencode/model_policy.json` — `primary_execution` and `lightweight_routing` → flash
- `~/.opencode-bot/core/engine.py` — default constants → flash + cost updated

### Pricing comparison
| Model | Input/M | Output/M | Speed |
|-------|---------|----------|-------|
| V4 Pro | ~$0.40 | ~$1.60 | Full reasoning |
| V4 Flash | ~$0.028 | ~$0.11 | Fast, cheaper |

### Toggle back to V4 Pro
1. Edit `orkes_ds/.env` → set `OPENCODE_MODEL=deepseek/deepseek-v4-pro`
2. Edit `~/.config/opencode/opencode.json` → set `"model"` to `"deepseek/deepseek-v4-pro"`
3. `touch .restart`

### Deepfix command
The `deepfix` command (difficult implementation work) is pinned to V4 Pro in opencode.json.
Everything else runs on Flash by default.
