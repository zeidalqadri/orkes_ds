# DeepSeek V4 Flash Config

## Applied (2026-08-04 — operator requested Flash)

### Current model
All agent loop steps use `deepseek/deepseek-v4-flash` (fast).

### Files configured
- `~/.config/opencode/opencode.json` — `"model": "deepseek/deepseek-v4-flash"`, `"small_model": "deepseek/deepseek-v4-flash"`
- `~/.config/opencode/model_policy.json` — `primary_execution: "openrouter/owl-alpha"`, `lightweight_routing: "openrouter/owl-alpha"`. V4 Pro reserved for `deepfix` only.
- `orkes_ds/.env` — OPENCODE_MODEL vars (model routing key)

### Pricing
| Model | Input/M | Output/M | Speed |
|-------|---------|----------|-------|
| V4 Flash | ~$0.028 | ~$0.11 | Fast |
| V4 Pro | ~$0.40 | ~$1.60 | Full reasoning |

### Toggle to Pro
1. Edit `~/.config/opencode/opencode.json` → set `"model"` to `"deepseek/deepseek-v4-pro"`
2. Edit `~/.config/opencode/model_policy.json` → set routes to pro
3. Edit `orkes_ds/.env` → `OPENCODE_MODEL=deepseek/deepseek-v4-pro`
4. `touch .restart`

### Deepfix command
Pinned to V4 Pro in opencode.json regardless of default.
