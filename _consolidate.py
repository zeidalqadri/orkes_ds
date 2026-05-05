#!/usr/bin/env python3
"""
SmartGEP Data Consolidation — all phases.

Phase 1: source_type cleanup (retag petronas-RFP -> smartgep)
Phase 2: silo consolidation (link pricesheet/BoQ data to DB tenders)
Phase 3: dedup (merge duplicate GEP-RFP references)
Phase 4: recalibrate (update CREMA queries, pricing engine, auto-detect logic)
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("consolidate")

DB_PATH = Path("/home/the_bomb/orkes/yellowpages/tenders/tenders.db")
YELLOWPAGES = Path("/home/the_bomb/orkes/yellowpages")
ORKES_DS = Path("/home/the_bomb/orkes_ds")


# ── Phase 1: source_type cleanup ─────────────────────────────────────

def phase1_source_type_cleanup(dry_run: bool = True) -> dict:
    """
    Retag petronas-tagged tenders with RFP/GEP-RFP refs -> "smartgep".
    """
    stats = {"retagged_to_smartgep": 0, "skipped": 0, "errors": 0}
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """SELECT id, reference, source_type, data FROM tenders
           WHERE source_type != 'smartgep'
           AND (reference LIKE 'RFP-%' OR reference LIKE 'GEP-RFP-%')
           ORDER BY reference"""
    ).fetchall()

    log.info("Phase 1: Found %d non-smartgep tenders with RFP/GEP-RFP refs", len(rows))
    updated_ids = []

    for r in rows:
        try:
            data = json.loads(r["data"])
        except (json.JSONDecodeError, TypeError) as e:
            log.warning("Corrupt data for %s: %s", r["id"], e)
            stats["errors"] += 1
            continue

        old_type = r["source_type"]
        data["source_type"] = "smartgep"
        meta = data.setdefault("metadata", {})
        meta["portal"] = "smartgep"
        if not meta.get("uploaded_by"):
            meta["uploaded_by"] = "SmartGEP"
        source_tags = meta.setdefault("source_tags", [])
        for tag in ("petronas", "smartgep"):
            if tag not in source_tags:
                source_tags.append(tag)
        meta["updated"] = datetime.now(timezone.utc).isoformat()

        if dry_run:
            log.info("[DRY-RUN] Would retag %s: %s -> smartgep (ref: %s, title: %s)",
                     r["id"], old_type, r["reference"], data.get("title", "?")[:50])
            stats["retagged_to_smartgep"] += 1
        else:
            conn.execute(
                "UPDATE tenders SET source_type=?, data=?, updated_at=? WHERE id=?",
                ("smartgep", json.dumps(data, ensure_ascii=False),
                 datetime.now(timezone.utc).isoformat(), r["id"])
            )
            log.info("Retagged %s: %s -> smartgep (ref: %s)", r["id"], old_type, r["reference"])
            stats["retagged_to_smartgep"] += 1
        updated_ids.append(r["id"])

    conn.commit()
    conn.close()
    stats["updated_ids"] = updated_ids
    log.info("Phase 1 complete: %d retagged, %d errors",
             stats["retagged_to_smartgep"], stats["errors"])
    return stats


# ── Phase 2: silo consolidation ──────────────────────────────────────

def phase2_silo_consolidation(dry_run: bool = True) -> dict:
    """
    Link pricesheet_extract data to DB tender records.
    """
    stats = {
        "pricesheet_tenders_linked": 0,
        "missing_rfps": [],
        "boq_files_empty": 0,
        "errors": 0,
    }

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Load pricesheet metadata
    event_map_path = ORKES_DS / "data" / "pricesheet_extract" / "event_id_map.json"
    event_map = {}
    if event_map_path.exists():
        with open(event_map_path) as f:
            event_map = json.load(f)

    log.info("Phase 2: event_id_map has %d RFPs", len(event_map))

    for rfp, info in event_map.items():
        num = rfp.replace("RFP-", "")
        row = conn.execute(
            "SELECT id, reference, source_type, data FROM tenders WHERE reference LIKE ?",
            (f"%{num}%",)
        ).fetchone()

        if row:
            try:
                tender_data = json.loads(row["data"])
            except (json.JSONDecodeError, TypeError):
                log.warning("Corrupt data for %s", row["id"])
                stats["errors"] += 1
                continue

            ps_meta = tender_data.setdefault("metadata", {}).setdefault("pricesheet", {})
            if not ps_meta:
                if not dry_run:
                    ps_meta["event_id"] = info.get("event_id", "")
                    ps_meta["doc_code"] = info.get("doc_code", "")
                    ps_meta["doc_url"] = info.get("doc_url", "")
                    ps_meta["source_file"] = "pricesheet_extract/parent_pricesheet.json"
                    tender_data["metadata"]["pricesheet"] = ps_meta
                    tender_data["metadata"]["updated"] = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        "UPDATE tenders SET data=?, updated_at=? WHERE id=?",
                        (json.dumps(tender_data, ensure_ascii=False),
                         datetime.now(timezone.utc).isoformat(), row["id"])
                    )
                    log.info("Linked pricesheet %s -> tender %s", rfp, row["id"])
                else:
                    log.info("[DRY-RUN] Would link pricesheet %s -> tender %s", rfp, row["id"])
                stats["pricesheet_tenders_linked"] += 1
            else:
                log.info("Pricesheet already linked for %s (%s)", row["id"], rfp)
        else:
            log.info("RFP %s not found in DB", rfp)
            stats["missing_rfps"].append(rfp)

    # Check BoQ files
    boq_dir = ORKES_DS / "data" / "boq_output"
    if boq_dir.exists():
        for f in sorted(boq_dir.iterdir()):
            if f.suffix == ".json":
                try:
                    with open(f) as fh:
                        boq = json.load(fh)
                    items = boq.get("items", [])
                    if len(items) == 0:
                        stats["boq_files_empty"] += 1
                        log.info("BoQ %s: 0 items", f.name)
                except Exception as e:
                    log.warning("BoQ %s: error %s", f.name, e)

    # Check re-extract summary
    re_summary = ORKES_DS / "data" / "boq_re_extract" / "re_extract_summary.json"
    if re_summary.exists():
        with open(re_summary) as f:
            summary = json.load(f)
        log.info("BoQ re-extract: %d total, %d successful, %d items",
                 summary.get("total", 0), summary.get("successful", 0),
                 summary.get("total_items", 0))

    conn.commit()
    conn.close()

    log.info("Phase 2 complete: %d pricesheet links, %d missing RFPs",
             stats["pricesheet_tenders_linked"], len(stats["missing_rfps"]))
    return stats


# ── Phase 3: dedup ───────────────────────────────────────────────────

def phase3_dedup_geprfp(dry_run: bool = True) -> dict:
    """
    Merge duplicate GEP-RFP reference entries.
    Keep the richer one, merge data from the thinner one, delete.
    """
    stats = {"pairs_found": 0, "merged": 0, "skipped": 0, "errors": 0}
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """SELECT reference, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
           FROM tenders WHERE reference LIKE 'GEP-RFP-%'
           GROUP BY reference HAVING cnt > 1
           ORDER BY reference"""
    ).fetchall()

    stats["pairs_found"] = len(rows)
    log.info("Phase 3: Found %d duplicate GEP-RFP refs", len(rows))

    for r in rows:
        ref = r["reference"]
        ids = r["ids"].split(",")

        tenders = {}
        for tid in ids:
            row = conn.execute(
                "SELECT id, data, source_type, document_count FROM tenders WHERE id=?",
                (tid,)
            ).fetchone()
            if row:
                try:
                    tenders[tid] = {
                        "data": json.loads(row["data"]),
                        "source_type": row["source_type"],
                        "document_count": row["document_count"],
                    }
                except (json.JSONDecodeError, TypeError):
                    stats["errors"] += 1

        if len(tenders) < 2:
            stats["skipped"] += 1
            continue

        def richness(t):
            d = t["data"]
            return (len(d.get("documents", [])) * 10 +
                    len(d.get("line_items", [])) * 5 +
                    len(d.get("requirements", {}).get("artifacts", [])) * 3 +
                    (2 if d.get("scope", {}).get("summary") else 0) +
                    (2 if d.get("evaluation", {}) else 0) +
                    (1 if d.get("issuer", {}).get("name") else 0) +
                    t["document_count"])

        sorted_ids = sorted(tenders.keys(), key=lambda tid: richness(tenders[tid]), reverse=True)
        keep_id = sorted_ids[0]
        merge_ids = sorted_ids[1:]

        log.info("Dedup %s: keep=%s (richness=%d)", ref, keep_id, richness(tenders[keep_id]))

        if dry_run:
            stats["skipped"] += len(merge_ids)
            continue

        primary = tenders[keep_id]["data"]
        for merge_id in merge_ids:
            mt = tenders[merge_id]["data"]
            changes = []

            # Merge aliases
            mref = mt.get("reference", "")
            if mref and mref != primary.get("reference", ""):
                aliases = primary.setdefault("metadata", {}).setdefault("aliases", [])
                if mref not in aliases:
                    aliases.append(mref)
                    changes.append(f"alias: {mref}")

            # Merge documents
            existing = {d.get("filename", "") for d in primary.get("documents", [])}
            new_docs = [d for d in mt.get("documents", []) if d.get("filename", "") not in existing]
            if new_docs:
                primary.setdefault("documents", []).extend(new_docs)
                changes.append(f"{len(new_docs)} docs")

            # Merge line_items, scope, issuer, evaluation
            if not primary.get("line_items") and mt.get("line_items"):
                primary["line_items"] = mt["line_items"]
                changes.append("line_items")
            if mt.get("scope", {}).get("summary") and not primary.get("scope", {}).get("summary"):
                primary.setdefault("scope", {})["summary"] = mt["scope"]["summary"]
                changes.append("scope")
            if mt.get("issuer", {}).get("name") and not primary.get("issuer", {}).get("name"):
                primary.setdefault("issuer", {})["name"] = mt["issuer"]["name"]
                changes.append("issuer")
            if mt.get("evaluation") and not primary.get("evaluation"):
                primary["evaluation"] = mt["evaluation"]
                changes.append("evaluation")

            # Source tags
            p_tags = primary.setdefault("metadata", {}).setdefault("source_tags", [])
            for tag in mt.get("metadata", {}).get("source_tags", []):
                if tag not in p_tags:
                    p_tags.append(tag)

            # Merge note
            note = f"Merged from {merge_id}: {', '.join(changes) if changes else 'no new data'}"
            primary.setdefault("metadata", {}).setdefault("notes", []).append(note)
            primary["metadata"]["updated"] = datetime.now(timezone.utc).isoformat()

            # Save primary and delete merge
            try:
                st = _build_search_text(primary)
                conn.execute(
                    """UPDATE tenders SET title=?, reference=?, status=?, issuer_name=?,
                       closing_date=?, updated_at=?, document_count=?, data=?, search_text=?
                       WHERE id=?""",
                    (primary.get("title", "Untitled"), primary.get("reference", ""),
                     primary.get("status", "draft"),
                     primary.get("issuer", {}).get("name", ""),
                     primary.get("dates", {}).get("closing"),
                     datetime.now(timezone.utc).isoformat(),
                     len(primary.get("documents", [])),
                     json.dumps(primary, ensure_ascii=False), st, keep_id)
                )
                conn.execute("DELETE FROM tenders WHERE id=?", (merge_id,))
                log.info("Merged %s -> %s: %s", merge_id, keep_id, ", ".join(changes) if changes else "no new data")
                stats["merged"] += 1
            except Exception as e:
                log.error("Failed to merge %s -> %s: %s", merge_id, keep_id, e)
                stats["errors"] += 1

    conn.commit()
    conn.close()
    log.info("Phase 3 complete: %d pairs, %d merged, %d errors",
             stats["pairs_found"], stats["merged"], stats["errors"])
    return stats


def _build_search_text(tender: dict) -> str:
    parts = [tender.get("title", ""), tender.get("reference", ""),
             tender.get("issuer", {}).get("name", "")]
    for li in tender.get("line_items", []):
        if isinstance(li, dict):
            parts.append(li.get("description", ""))
    return " ".join(filter(None, parts)).lower()


# ── Phase 4: recalibrate ─────────────────────────────────────────────

def phase4_recalibrate(dry_run: bool = True) -> dict:
    """
    Update source_type-dependent code paths.
    """
    stats = {"tender_db_updated": False, "pricing_engine_updated": False}

    # 1. Update tender_db.py save_tender auto-detection
    tdb = YELLOWPAGES / "tender_db.py"
    if tdb.exists():
        content = tdb.read_text()
        old = ('    _src = tender.get("source_type", "unknown")\n'
               '    _upl = meta.get("uploaded_by", "")\n'
               '    if ref and _src in ("unknown", "portal", ""):')
        new = ('    _src = tender.get("source_type", "unknown")\n'
               '    _upl = meta.get("uploaded_by", "")\n'
               '    # Also retag petronas -> smartgep for SmartGEP RFP refs\n'
               '    if ref and _src in ("unknown", "portal", "", "petronas"):')

        if old in content:
            if not dry_run:
                content = content.replace(old, new)
                tdb.write_text(content)
                log.info("Updated tender_db.py: added 'petronas' to auto-detect list")
            else:
                log.info("[DRY-RUN] Would update tender_db.py auto-detection")
            stats["tender_db_updated"] = True
        else:
            log.info("tender_db.py auto-detect already updated or pattern differs")
            stats["tender_db_updated"] = True

    # 2. Add 'smartgep' to pricing_engine_data.py TENDER_TYPE_NORMS
    ped = YELLOWPAGES / "pricing_engine_data.py"
    if ped.exists():
        content = ped.read_text()
        if "'smartgep'" in content or '"smartgep"' in content:
            log.info("pricing_engine_data.py already has 'smartgep' in TENDER_TYPE_NORMS")
            stats["pricing_engine_updated"] = True
        else:
            old = '''    "private": {
        "label": "Private Sector",'''
            new = '''    "smartgep": {
        "label": "SmartGEP (PETRONAS Procurement Portal)",
        "guidance": (
            "SmartGEP portal tender. Typically PETRONAS or PETRONAS-linked procurement. "
            "Price evaluation 30-50% weight. Technical/HSE scores critical. "
            "PETRONAS License status differentiator. "
            "Include mobilization, HSE, PETRONAS-specific insurance."
        ),
    },
    "private": {
        "label": "Private Sector",'''
            if old in content:
                if not dry_run:
                    content = content.replace(old, new)
                    ped.write_text(content)
                    log.info("Added 'smartgep' to TENDER_TYPE_NORMS")
                else:
                    log.info("[DRY-RUN] Would add 'smartgep' to TENDER_TYPE_NORMS")
                stats["pricing_engine_updated"] = True
            else:
                log.warning("Could not find insertion point in pricing_engine_data.py")

    return stats


# ── Verification ─────────────────────────────────────────────────────

def verify_state() -> dict:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    dist = {}
    rows = conn.execute("SELECT source_type, COUNT(*) as cnt FROM tenders GROUP BY source_type").fetchall()
    for r in rows:
        dist[r["source_type"]] = r["cnt"]

    remaining = conn.execute(
        "SELECT COUNT(*) FROM tenders WHERE source_type='petronas' AND (reference LIKE 'RFP-%' OR reference LIKE 'GEP-RFP-%')"
    ).fetchone()[0]

    dups = conn.execute(
        "SELECT COUNT(*) FROM (SELECT reference FROM tenders WHERE reference LIKE 'GEP-RFP-%' GROUP BY reference HAVING COUNT(*) > 1)"
    ).fetchone()[0]

    total = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
    conn.close()

    return {
        "total_tenders": total,
        "source_type_distribution": dist,
        "remaining_petronas_rfp": remaining,
        "remaining_duplicates": dups,
    }


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SmartGEP data consolidation")
    parser.add_argument("phase", choices=["phase1", "phase2", "phase3", "phase4", "verify", "all"])
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    dry_run = not args.apply

    phases = {
        "phase1": ("Source Type Cleanup", phase1_source_type_cleanup),
        "phase2": ("Silo Consolidation", phase2_silo_consolidation),
        "phase3": ("GEP-RFP Dedup", phase3_dedup_geprfp),
        "phase4": ("Recalibrate Code", phase4_recalibrate),
    }

    if args.phase == "all":
        for key, (name, func) in phases.items():
            print(f"\n=== {name} ===\n")
            result = func(dry_run=dry_run)
            print(json.dumps(result, indent=2))
    elif args.phase == "verify":
        pass
    else:
        name, func = phases[args.phase]
        print(f"\n=== {name} ===\n")
        result = func(dry_run=dry_run)
        print(json.dumps(result, indent=2))

    if args.phase in ("verify", "all"):
        print(f"\n=== Verification ===\n")
        state = verify_state()
        print(json.dumps(state, indent=2))
