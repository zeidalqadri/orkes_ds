# DeepSeek V4 Pro Config

## Applied (2026-04-30 — operator requested Pro)

### Current model
All agent loop steps use `deepseek/deepseek-v4-pro` (full reasoning).

### Files configured
- `orkes_ds/.env` — `OPENCODE_MODEL=deepseek/deepseek-v4-pro`, `OPENCODE_SMALL_MODEL=deepseek/deepseek-v4-pro`
- `~/.config/opencode/opencode.json` — default `model` + `small_model` → pro
- `~/.config/opencode/model_policy.json` — `primary_execution` + `lightweight_routing` → pro
- `~/.opencode-bot/core/engine.py` — default fallback reads from env

### Pricing
| Model | Input/M | Output/M | Speed |
|-------|---------|----------|-------|
| V4 Pro | ~$0.40 | ~$1.60 | Full reasoning |
| V4 Flash | ~$0.028 | ~$0.11 | Fast, cheaper |

### Toggle back to Flash
1. Edit `orkes_ds/.env` → `OPENCODE_MODEL=deepseek/deepseek-v4-flash` (both vars)
2. Edit `~/.config/opencode/opencode.json` → set `"model"` to `"deepseek/deepseek-v4-flash"`
3. Edit `~/.config/opencode/model_policy.json` → set routes back to flash
4. `touch .restart`

### Deepfix command
Pinned to V4 Pro in opencode.json regardless of default.
