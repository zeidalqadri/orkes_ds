"""Validate STATE.md, GOAL.md, INBOX.md are well-formed."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "context"

FILES = {
    "STATE.md": [
        ("# Arbos State", "# header"),
        ("Updated:", "timestamp field"),
        ("## Status:", "status field"),
        ("## Last Completed:", "completed field"),
    ],
    "GOAL.md": [],
    "INBOX.md": [],
}

errors = []

for fname, checks in FILES.items():
    fpath = CONTEXT / fname
    if not fpath.exists():
        errors.append(f"MISSING: {fname}")
        continue
    text = fpath.read_text()
    if fname == "INBOX.md" and text.strip():
        errors.append(f"NON-EMPTY: {fname} should be cleared after processing")
    for marker, desc in checks:
        if marker not in text:
            errors.append(f"STATE.md missing {desc} ('{marker}')")

text = (CONTEXT / "STATE.md").read_text()
lines = text.splitlines()
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if not stripped:
        continue
    if stripped.startswith(("#", "-", "|", "*", ">", "`")):
        continue
    if ":" in stripped or "✓" in stripped or "—" in stripped:
        continue
    if stripped.startswith(("Updated", "##", "---", "```", "Phase", "**", "(", "Scorecard", "Module", "|", "Total")):
        continue
    import re
    if re.match(r"^\d+[\s\.\)]", stripped):
        continue
    if len(stripped) < 20 and not any(c.isalpha() for c in stripped):
        continue
    errors.append(f"STATE.md:{i}: possible garbled content: {stripped[:80]}")

if errors:
    for e in errors:
        print(f"FAIL: {e}", file=sys.stderr)
    sys.exit(1)

print("All state files valid.")
