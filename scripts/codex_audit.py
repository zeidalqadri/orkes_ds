#!/usr/bin/env python3
"""Codex — vision bridge for UI audit reports.

Translates a UI screenshot into structured XML audit report
via whichever vision-capable LLM backend is available.

Usage:
    python scripts/codex_audit.py --image <path> [--prompt <text>] [--output <path>]
    python scripts/codex_audit.py --check

Backends (checked in order):
    1. ANTHROPIC_API_KEY → Claude 3.5 Sonnet (vision)
    2. CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID → Llama 3.2 Vision / LLaVA
    3. OPENAI_API_KEY → GPT-4o / GPT-4V

Exit codes:
    0 — success (XML written)
    1 — no backend available (instructions printed)
    2 — image not found
    3 — API error
"""

import argparse
import base64
import json
import os
import sys
import xml.sax.saxutils as saxutils
from pathlib import Path

DEFAULT_PROMPT = (
    "You are a UI/UX expert analyzing a screenshot of a web/mobile game interface. "
    "Produce a structured UI audit report in XML format. "
    "Follow this exact schema:\n\n"
    "<ui_audit_report>\n"
    "  <subject>App/Game Name</subject>\n"
    "  <platform>Mobile Web (Safari) | Desktop Chrome | etc</platform>\n\n"
    "  <current_state_analysis label=\"The Shambles\">\n"
    "    <issues>\n"
    "      <redundancy>\n"
    "        <element>Duplicated element name</element>\n"
    "        <occurrence count=\"2\">Where it appears</occurrence>\n"
    "        <impact>What's wrong</impact>\n"
    "      </redundancy>\n"
    "      <visual_hierarchy_confusion>\n"
    "        <problem>Describe the confusion</problem>\n"
    "      </visual_hierarchy_confusion>\n"
    "      <styling>\n"
    "        <issue>Font/color/layout problem</issue>\n"
    "      </styling>\n"
    "    </issues>\n"
    "  </current_state_analysis>\n\n"
    "  <proposed_redesign label=\"How It Should Be\">\n"
    "    <layout_strategy>...</layout_strategy>\n"
    "    <component_specifications>...</component_specifications>\n"
    "  </proposed_redesign>\n\n"
    "  <ux_improvements>\n"
    "    <improvement><category>Clarity</category><description>...</description></improvement>\n"
    "    <improvement><category>Conversion</category><description>...</description></improvement>\n"
    "    <improvement><category>Aesthetics</category><description>...</description></improvement>\n"
    "  </ux_improvements>\n"
    "</ui_audit_report>"
)


UI_AUDIT_SYSTEM_PROMPT = (
    "You are Codex, a UI/UX audit specialist. Your output is always valid XML "
    "following the ui_audit_report schema. Analyze the screenshot for:\n"
    "1. Redundancy (duplicate elements, wasted space)\n"
    "2. Visual hierarchy confusion (conflicting focal points)\n"
    "3. Styling issues (inconsistent fonts, colors, button styles)\n"
    "4. Layout/alignment problems\n"
    "5. Missing or broken UI elements\n\n"
    "Propose a concrete redesign with specific layout strategy, "
    "component specifications, and prioritized UX improvements. "
    "Respond ONLY with the XML report — no preamble, no commentary."
)


def _b64_encode(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _fmt_xml(text: str) -> str:
    """Escape text for XML content."""
    return saxutils.escape(text)


def _check_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _check_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _check_mistral() -> bool:
    return bool(os.environ.get("MISTRAL_API_KEY", "").strip())


def _check_cloudflare() -> tuple[bool, str]:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not token or not account:
        return False, "missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID"
    return True, f"account={account}"


def check_backends() -> dict:
    return {
        "anthropic": _check_anthropic(),
        "openai": _check_openai(),
        "mistral": _check_mistral(),
        "cloudflare": _check_cloudflare()[0],
    }


# ── Mistral (Pixtral) vision ────────────────────────────────────────────


def _call_mistral(image_path: str, prompt: str) -> str:
    api_key = os.environ["MISTRAL_API_KEY"]
    image_data = _b64_encode(image_path)
    ext = Path(image_path).suffix.lstrip(".") or "jpeg"

    body = {
        "model": "pixtral-large-latest",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{ext};base64,{image_data}"
                        },
                    },
                ],
            }
        ],
    }

    resp = _http_post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        body=body,
    )
    return resp.get("choices", [{}])[0].get("message", {}).get("content", "")


# ── Anthropic Claude vision ─────────────────────────────────────────────


def _call_anthropic(image_path: str, prompt: str) -> str:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    image_data = _b64_encode(image_path)
    ext = Path(image_path).suffix.lstrip(".") or "jpeg"
    media_type = f"image/{ext}"

    body = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                ],
            }
        ],
        "system": UI_AUDIT_SYSTEM_PROMPT,
    }

    resp = _http_post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        body=body,
    )
    data = resp
    content = data.get("content", [])
    texts = [b.get("text", "") for b in content if b.get("type") == "text"]
    return "\n".join(texts)


# ── OpenAI-compatible vision (GPT-4o / GPT-4V) ─────────────────────────


def _call_openai(image_path: str, prompt: str) -> str:
    api_key = os.environ["OPENAI_API_KEY"]
    image_data = _b64_encode(image_path)
    ext = Path(image_path).suffix.lstrip(".") or "jpeg"

    body = {
        "model": "gpt-4o",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{ext};base64,{image_data}"
                        },
                    },
                ],
            }
        ],
    }

    resp = _http_post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        body=body,
    )
    return resp.get("choices", [{}])[0].get("message", {}).get("content", "")


# ── Cloudflare Workers AI vision ────────────────────────────────────────


def _call_cloudflare(image_path: str, prompt: str) -> str:
    token = os.environ["CLOUDFLARE_API_TOKEN"]
    account = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    image_data = _b64_encode(image_path)

    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ],
        "max_tokens": 4096,
    }

    models = [
        "@cf/moonshotai/kimi-k2.5",
        "@cf/meta/llama-3.2-11b-vision-instruct",
        "@cf/llava-hf/llava-1.5-7b-hf",
    ]

    for model in models:
        url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
        try:
            resp = _http_post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "content-type": "application/json",
                },
                body=body,
            )
            if isinstance(resp, dict) and resp.get("success"):
                result = resp.get("result", {})
                if "choices" in result:
                    choices = result.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        content = msg.get("content") or msg.get("reasoning_content", "")
                        if content:
                            return content
                text = result.get("response", "")
                if text:
                    return text
                return json.dumps(result)
        except Exception:
            continue

    raise RuntimeError(
        "Cloudflare Workers AI vision unavailable. "
        "Ensure CLOUDFLARE_API_TOKEN has 'Workers AI' permission."
    )


# ── HTTP helper ─────────────────────────────────────────────────────────


def _http_post(url: str, headers: dict, body: dict, timeout: int = 120) -> dict:
    import urllib.error
    import urllib.request

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"HTTP {e.code} from {url}: {err_body}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}") from e


# ── Scrub XML from LLM response ─────────────────────────────────────────


def _extract_xml(text: str) -> str:
    """Extract <ui_audit_report>...</ui_audit_report> from LLM response."""
    start = text.find("<ui_audit_report>")
    end = text.find("</ui_audit_report>")
    if start >= 0 and end >= 0:
        return text[start: end + len("</ui_audit_report>")]
    return text


# ── Fallback / instructions ─────────────────────────────────────────────


def _build_config_help() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<codex_setup_required>
  <message>No vision-capable LLM backend is configured.</message>
  <backends>
    <backend name="Anthropic Claude">
      <env_var>ANTHROPIC_API_KEY</env_var>
      <model>claude-3-5-sonnet-20241022</model>
      <setup>Set ANTHROPIC_API_KEY in .env and restart</setup>
    </backend>
    <backend name="Cloudflare Workers AI">
      <env_var>CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID</env_var>
      <models>@cf/moonshotai/kimi-k2.5, @cf/meta/llama-3.2-11b-vision-instruct, @cf/llava-hf/llava-1.5-7b-hf</models>
      <setup>Ensure token has 'Workers AI' permission. Set CLOUDFLARE_ACCOUNT_ID in .env.</setup>
    </backend>
    <backend name="OpenAI GPT-4o">
      <env_var>OPENAI_API_KEY</env_var>
      <model>gpt-4o</model>
      <setup>Set OPENAI_API_KEY in .env and restart</setup>
    </backend>
  </backends>
  <check_command>python scripts/codex_audit.py --check</check_command>
</codex_setup_required>"""


def _build_fallback_report(image_path: str, prompt: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ui_audit_report>
  <subject>UI Screenshot (unprocessed — no vision backend)</subject>
  <platform>Unknown</platform>
  <image_path>{_fmt_xml(image_path)}</image_path>
  <status>No vision-capable LLM configured. Run `python scripts/codex_audit.py --check` for setup instructions.</status>
  <prompt_sent>{_fmt_xml(prompt[:500])}</prompt_sent>
</ui_audit_report>"""


# ── Main ────────────────────────────────────────────────────────────────


def run_audit(image_path: str, prompt: str = "") -> str:
    path = Path(image_path)
    if not path.exists():
        print(f"ERROR: image not found: {image_path}", file=sys.stderr)
        sys.exit(2)

    if not prompt:
        prompt = DEFAULT_PROMPT

    backends = check_backends()

    if backends.get("anthropic"):
        print("  backend: Anthropic Claude 3.5 Sonnet (vision)", file=sys.stderr)
        raw = _call_anthropic(image_path, prompt)
        return _extract_xml(raw)

    if backends.get("openai"):
        print("  backend: OpenAI GPT-4o (vision)", file=sys.stderr)
        raw = _call_openai(image_path, prompt)
        return _extract_xml(raw)

    if backends.get("mistral"):
        print("  backend: Mistral Pixtral Large (vision)", file=sys.stderr)
        raw = _call_mistral(image_path, prompt)
        return _extract_xml(raw)

    cf_ok, cf_info = _check_cloudflare()
    if cf_ok:
        print(f"  backend: Cloudflare Workers AI ({cf_info})", file=sys.stderr)
        try:
            raw = _call_cloudflare(image_path, prompt)
            return _extract_xml(raw)
        except RuntimeError as e:
            print(f"  Cloudflare AI error: {e}", file=sys.stderr)
            print("  Falling back to setup instructions.", file=sys.stderr)

    return _build_fallback_report(image_path, prompt)


def cmd_check():
    backends = check_backends()
    print("Codex Backend Check")
    print("=" * 40)
    for name, ok in sorted(backends.items()):
        status = "READY" if ok else "NOT CONFIGURED"
        print(f"  {name:20s} {status}")

    cf_ok, cf_info = _check_cloudflare()
    if cf_ok:
        print(f"  cloudflare-token: PRESENT ({cf_info})")
        print("  cloudflare-perm:  UNVERIFIED (test with --image to check)")

    print()
    if not any(backends.values()):
        print(_build_config_help())
        print()
        print("No backends ready. Configure one of the above and try again.")
    else:
        print("At least one backend is ready. Use --image <path> to run an audit.")


def cmd_audit(args):
    print("Codex UI Audit", file=sys.stderr)
    print(f"  image: {args.image}", file=sys.stderr)
    print(f"  prompt: {len(args.prompt or DEFAULT_PROMPT)} chars", file=sys.stderr)
    xml = run_audit(args.image, args.prompt or DEFAULT_PROMPT)
    if args.output:
        Path(args.output).write_text(xml)
        print(f"  output: {args.output}", file=sys.stderr)
    else:
        print(xml)


def main():
    parser = argparse.ArgumentParser(
        description="Codex — vision bridge for UI audit reports"
    )
    parser.add_argument("--image", help="Path to screenshot image")
    parser.add_argument("--prompt", help="Custom analysis prompt (optional)")
    parser.add_argument("--output", help="Write XML to file instead of stdout")
    parser.add_argument(
        "--check", action="store_true", help="Check available backends and exit"
    )
    args = parser.parse_args()

    if args.check:
        cmd_check()
        return

    if not args.image:
        parser.print_help()
        print("\nERROR: --image is required (or use --check to verify backends)")
        sys.exit(1)

    cmd_audit(args)


if __name__ == "__main__":
    main()
