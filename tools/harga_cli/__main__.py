#!/usr/bin/env python3
"""Harga CLI — Malaysian government procurement tender discovery and bid management.

Usage:
    python -m tools.harga_cli t           # list tenders
    python -m tools.harga_cli b -s active # active bids
    python -m tools.harga_cli e ls        # list entities
    python -m tools.harga_cli s           # pipeline dashboard
"""

import argparse
import json
import sys
import time

from . import __version__
from .theme import console
from .panels import header_bar
from .tables import render_tenders, render_bids, render_entities, render_status_dashboard


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-j", "--json", action="store_true", help="JSON output")
    common.add_argument("-q", "--quiet", action="store_true", help="suppress header")

    p = argparse.ArgumentParser(
        prog="harga",
        description="Malaysian government procurement CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Sources: ePerolehan, ForSAH, eTimad",
        parents=[common],
    )
    p.add_argument("-V", "--version", action="version", version=f"harga {__version__}")

    sub = p.add_subparsers(dest="cmd")

    # tenders
    t = sub.add_parser("t", aliases=["tenders"], help="list tenders", parents=[common])
    t.add_argument("-p", "--portal", help="ePerolehan|ForSAH|eTimad")
    t.add_argument("-s", "--status", help="open|closed")
    t.add_argument("-b", "--buyer", help="buyer slug (petronas, shell, etc.)")
    t.add_argument("-n", "--limit", type=int, default=50)
    t.add_argument("-o", "--offset", type=int, default=0)

    # bids
    b = sub.add_parser("b", aliases=["bids"], help="list bids", parents=[common])
    b.add_argument("-e", "--entity", help="entity slug (consurv-technic, dyna-om, etc.)")
    b.add_argument("-s", "--status", help="active|overdue|won|lost|draft|submitted|priced|in_progress")
    b.add_argument("-w", "--phase", help="pricing|approval|packaging|submitted|post_submit")
    b.add_argument("-n", "--limit", type=int, default=50)
    b.add_argument("-o", "--offset", type=int, default=0)

    # entities
    e = sub.add_parser("e", aliases=["entities"], help="manage entities", parents=[common])
    esub = e.add_subparsers(dest="ecmd")
    esub.add_parser("ls", aliases=["list"], help="list entities")
    cfg = esub.add_parser("cfg", aliases=["config"], help="set notification")
    cfg.add_argument("entity_slug", help="entity slug (e.g. consurv-technic)")
    cfg.add_argument("channel", help="notification channel (e.g. tg:198234)")

    # status dashboard
    sub.add_parser("s", aliases=["status"], help="pipeline dashboard", parents=[common])

    return p


def main(query_fn=None, argv=None):
    """Main entry point.

    query_fn: callable(cmd, **kwargs) -> dict
        Data layer callback. Returns dicts matching shapes in tables.py.
        If None, uses built-in sample data (demo mode).
    """
    p = build_parser()
    args = p.parse_args(argv)

    if not args.cmd:
        p.print_help()
        return

    if not args.quiet:
        console.print(header_bar("HARGA", __version__))

    fetch = query_fn or _demo_query
    t0 = time.monotonic()

    if args.cmd in ("t", "tenders"):
        data = fetch("tenders", portal=args.portal, status=args.status,
                      buyer=getattr(args, "buyer", None),
                      limit=args.limit, offset=args.offset)
        elapsed = (time.monotonic() - t0) * 1000
        if args.json:
            console.print_json(json.dumps(data))
        else:
            data["_query_ms"] = elapsed
            render_tenders(data)

    elif args.cmd in ("b", "bids"):
        data = fetch("bids", entity=args.entity, status=args.status,
                      phase=getattr(args, "phase", None),
                      limit=args.limit, offset=args.offset)
        elapsed = (time.monotonic() - t0) * 1000
        if args.json:
            console.print_json(json.dumps(data))
        else:
            data["_query_ms"] = elapsed
            render_bids(data)

    elif args.cmd in ("e", "entities"):
        if args.ecmd in ("ls", "list", None):
            data = fetch("entities")
            if args.json:
                console.print_json(json.dumps(data))
            else:
                render_entities(data)
        elif args.ecmd in ("cfg", "config"):
            data = fetch("entity_config", entity_slug=args.entity_slug, channel=args.channel)
            console.print(f"[green]Updated {args.entity_slug} \u2192 {args.channel}[/green]")

    elif args.cmd in ("s", "status"):
        data = fetch("status")
        if args.json:
            console.print_json(json.dumps(data))
        else:
            render_status_dashboard(data)


def _demo_query(cmd, **kwargs):
    from .sample_data import SAMPLE_DATA
    return SAMPLE_DATA.get(cmd, {})


if __name__ == "__main__":
    main()
