# Arbos State
Updated: 2026-05-02T06:58 UTC

## Status: COMPLETED — Campaign guardrails deployed

## Last Completed
Diagnosed 2 failed campaigns (patent_publication, convocation_ocr) and deployed guardrails.

### Root Cause
Both scripts didn't accept `--max` argument → orchestrator's `--max=N` caused argparse exit code 2.

### Fixes Applied
1. **harvest_patents.py** — added `--max`, `--check`, `--campaign` args. `--max` actually limits inventors.
2. **ocr_convocation.py** — added `--max`, `--check`, `--status` args. Made `--pdf/--edition/--year` conditional (not required for `--check/--status`). Disabled auto-run (requires manual parameters).
3. **campaign_orchestrator.py** — added pre-flight script validation, arg compatibility check, exit code diagnosis, stderr capture in state, actionable Telegram messages.
4. **campaign_config.json** — added `supports_max`, `notes` fields. convocation_ocr disabled.
5. **16 new tests** — arg support detection, script validation, exit code diagnosis.
6. **campaign_state.json** — reset to `never_run` for both failed, with `last_error` explaining the fix.

### Guardrail Layers
- Layer 1: Pre-flight `validate_all_scripts()` checks script existence at startup
- Layer 2: `_check_arg_support()` detects which args each script accepts via `--help`
- Layer 3: `validate_run()` verifies arg compatibility before execution
- Layer 4: Exit code 2 auto-diagnosis with actionable Telegram message
- Layer 5: `supports_max` flag in config for scripts that can't accept `--max`
