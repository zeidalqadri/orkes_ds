#!/usr/bin/env python3
"""
SmartGEP Data Consolidation + Housekeeping Script

Phases:
  1. source_type cleanup — retag SmartGEP entities from government/unknown/petronas → smartgep
  2. Silo consolidation — ingest pricesheet_extract data into DB linked to tender records
  3. Dedup — merge 10 duplicate GEP-RFP references (preserve richest data)
  4. Recalibrate — update all affected queries, views, and tests

Usage:
    python scripts/consolidate_smartgep.py          # dry run (safe)
    python scripts/consolidate_smartgep.py --run    # execute changes
    python scripts/consolidate_smartgep.py --undo   # restore from backup
"""

import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────
DB_PATH = Path("/home/the_bomb/orkes/yellowpages/tenders/tenders.db")
BACKUP_DIR = Path("/home/the_bomb/orkes_ds/data/db_backups")
PRICESHEET_DIR = Path("/home/the_bomb/orkes_ds/data/pricesheet_extract")
BOQ_OUTPUT_DIR = Path("/home/the_bomb/orkes_ds/data/boq_output")

SMARTGEP_ENTITIES = ("dyna-segmen", "consurv-technic", "dyna-om", "dyna-sche")

# Ensure backup dir
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, phase=""):
    tag = f"[Phase {phase}] " if phase else ""
    print(f"  {tag}{msg}")


def connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def backup_db():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"tenders_backup_{ts}.db"
    shutil.copy2(str(DB_PATH), str(backup_path))
    log(f"Backup saved to {backup_path}")
    return backup_path


def restore_db(backup_path):
    if not backup_path.exists():
        log(f"Backup not found: {backup_path}", "ERROR")
        return False
    shutil.copy2(str(backup_path), str(DB_PATH))
    log(f"Restored from {backup_path}")
    return True


def find_backup():
    backups = sorted(BACKUP_DIR.glob("tenders_backup_*.db"))
    if not backups:
        log("No backups found")
        return None
    return backups[-1]


# ─── Phase 1: source_type cleanup ────────────────────────────────────────────

def phase1_source_type_cleanup(dry_run=True):
    """Retag SmartGEP entity tenders to source_type='smartgep'."""
    conn = connect()
    c = conn.cursor()

    # 1a. Tenders with SmartGEP entities — regardless of current source_type
    placeholders = ",".join("?" * len(SMARTGEP_ENTITIES))
    c.execute(
        f"SELECT source_type, COUNT(*) FROM tenders "
        f"WHERE entity IN ({placeholders}) GROUP BY source_type",
        SMARTGEP_ENTITIES,
    )
    entity_counts = dict(c.fetchall())

    c.execute(
        f"SELECT COUNT(*) FROM tenders WHERE entity IN ({placeholders})",
        SMARTGEP_ENTITIES,
    )
    total_entity = c.fetchone()[0]

    log(f"Tenders with SmartGEP entities: {total_entity}", "1")
    for src, cnt in sorted(entity_counts.items()):
        log(f"  Currently tagged '{src}': {cnt}", "1")

    # 1b. GEP-RFP references without entity (orphaned SmartGEP)
    c.execute(
        "SELECT COUNT(*) FROM tenders WHERE entity='' AND reference LIKE 'GEP-RFP%'"
    )
    orphan_gep = c.fetchone()[0]
    log(f"GEP-RFP references without entity: {orphan_gep}", "1")

    # 1c. Probe unknown-source no-entity tenders
    c.execute(
        "SELECT id, reference, title FROM tenders WHERE entity='' AND source_type='unknown'"
    )
    unknowns = c.fetchall()
    log(f"Unknown-source tenders with no entity: {len(unknowns)}", "1")
    for u in unknowns:
        ref = u["reference"] or "(empty)"
        log(f"  {u['id']}: ref='{ref}' title='{u['title'][:60]}'", "1")

    # 1d. Show what will change
    c.execute(
        f"SELECT COUNT(*) FROM tenders "
        f"WHERE entity IN ({placeholders}) AND source_type != 'smartgep'",
        SMARTGEP_ENTITIES,
    )
    to_retag_entity = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM tenders WHERE entity='' AND reference LIKE 'GEP-RFP%' AND source_type != 'smartgep'"
    )
    to_retag_orphan = c.fetchone()[0]
    total_retag = to_retag_entity + to_retag_orphan

    log(f"Will retag: {total_retag} tenders ({to_retag_entity} from entities + {to_retag_orphan} orphans)", "1")

    if dry_run:
        log("DRY RUN — no changes made", "1")
        conn.close()
        return total_retag

    # Execute retag
    c.execute(
        f"UPDATE tenders SET source_type='smartgep', updated_at=? "
        f"WHERE entity IN ({placeholders}) AND source_type != 'smartgep'",
        (datetime.now(timezone.utc).isoformat(),) + SMARTGEP_ENTITIES,
    )
    retagged_entity = c.rowcount

    c.execute(
        "UPDATE tenders SET source_type='smartgep', updated_at=? "
        "WHERE entity='' AND reference LIKE 'GEP-RFP%' AND source_type != 'smartgep'",
        (datetime.now(timezone.utc).isoformat(),),
    )
    retagged_orphan = c.rowcount

    conn.commit()
    conn.close()
    log(f"Retagged: {retagged_entity} entity-based + {retagged_orphan} orphans = {retagged_entity + retagged_orphan} total", "1")
    return retagged_entity + retagged_orphan


# ─── Phase 2: Silo consolidation ─────────────────────────────────────────────

def phase2_silo_consolidation(dry_run=True):
    """Ingest pricesheet_extract data into DB linked to tender records."""
    conn = connect()
    c = conn.cursor()

    # 2a. Load pricesheet event_id_map
    event_map = {}
    event_map_path = PRICESHEET_DIR / "event_id_map.json"
    if event_map_path.exists():
        event_map = json.loads(event_map_path.read_text())

    # Load parent pricesheet data
    parent_data = {}
    parent_path = PRICESHEET_DIR / "parent_pricesheet.json"
    if parent_path.exists():
        parent_data = json.loads(parent_path.read_text())

    # Load material specs
    specs_data = {}
    specs_path = PRICESHEET_DIR / "extracted_material_specs.json"
    if specs_path.exists():
        specs_data = json.loads(specs_path.read_text())

    log(f"Pricesheet events in map: {len(event_map)}", "2")
    log(f"Parent pricesheet keys: {len(parent_data)}", "2")
    log(f"Material specs entries: {len(specs_data.get('col_schema', {}))}", "2")

    # 2b. Check which events exist in tenders DB
    matched = 0
    unmatched = []
    for ref in event_map:
        c.execute("SELECT COUNT(*) FROM tenders WHERE reference=?", (ref,))
        cnt = c.fetchone()[0]
        if cnt > 0:
            matched += 1
        else:
            unmatched.append(ref)

    log(f"Events with matching tender records: {matched}", "2")
    if unmatched:
        log(f"Events without tender records: {len(unmatched)}", "2")
        for ref in unmatched:
            log(f"  No tender record for {ref}", "2")

    # 2c. Link pricesheet data into tenders' data JSON (artifacts section)
    updates = 0
    for ref, ev_info in event_map.items():
        c.execute("SELECT id, data FROM tenders WHERE reference=?", (ref,))
        row = c.fetchone()
        if not row:
            continue

        tender_id = row["id"]
        data = json.loads(row["data"])

        # Attach pricesheet metadata
        data.setdefault("pricesheet", {})
        data["pricesheet"].update({
            "event_id": ev_info.get("event_id"),
            "doc_code": ev_info.get("doc_code"),
            "doc_url": ev_info.get("doc_url"),
            "status_code": ev_info.get("status"),
        })

        # Attach column schema if available
        if specs_data and "col_schema" in specs_data:
            data["pricesheet"]["columns"] = specs_data["col_schema"]
            data["pricesheet"]["supplier_count"] = specs_data.get("total_supplier", 0)
            data["pricesheet"]["buyer_count"] = specs_data.get("total_buyer", 0)

        # Attach parent pricesheet summary
        if isinstance(parent_data, dict) and ref in parent_data:
            parent_sheet = parent_data[ref]
            if isinstance(parent_sheet, dict):
                data["pricesheet"]["parent_data"] = parent_sheet

        # Update document_count if pricesheet has docs
        doc_keys = [k for k in data.get("pricesheet", {}).keys() if k not in ("columns", "parent_data")]
        if doc_keys:
            existing_docs = data.get("documents", [])
            data["document_count"] = max(data.get("document_count", 0), len(existing_docs))

        if dry_run:
            continue

        c.execute(
            "UPDATE tenders SET data=?, updated_at=? WHERE id=?",
            (json.dumps(data), datetime.now(timezone.utc).isoformat(), tender_id),
        )
        updates += 1

    # 2d. Check BoQ output tenders
    boq_files = list(BOQ_OUTPUT_DIR.glob("*.json"))
    boq_refs = set()
    for bf in boq_files:
        # Extract RFP reference from filename
        ref = bf.stem  # e.g., RFP-000000178387
        boq_refs.add(ref)

    log(f"BoQ output files: {len(boq_files)} referencing {len(boq_refs)} tenders", "2")

    for ref in sorted(boq_refs):
        c.execute("SELECT COUNT(*) FROM tenders WHERE reference=?", (ref,))
        cnt = c.fetchone()[0]
        if cnt == 0:
            log(f"  BoQ for {ref} — NOT in DB", "2")

    # 2e. Flag unprocessed raw notices (gmv2_docs.json)
    gmv2_path = PRICESHEET_DIR / "gmv2_docs.json"
    if gmv2_path.exists():
        gmv2 = json.loads(gmv2_path.read_text())
        if isinstance(gmv2, list):
            log(f"GMv2 raw documents: {len(gmv2)} entries", "2")
            # Count how many are already in DB
            in_db = 0
            not_in_db = 0
            for doc in gmv2:
                ref = doc.get("eventNumber") or doc.get("reference") or ""
                if ref:
                    c.execute("SELECT COUNT(*) FROM tenders WHERE reference=?", (ref,))
                    if c.fetchone()[0] > 0:
                        in_db += 1
                    else:
                        not_in_db += 1
            log(f"  GMv2 docs in DB: {in_db}, not in DB: {not_in_db}", "2")

    conn.commit()
    conn.close()
    log(f"Linked pricesheet data to {updates} tenders", "2")
    return updates


# ─── Phase 3: Dedup ──────────────────────────────────────────────────────────

def phase3_dedup(dry_run=True):
    """Merge 10 duplicate GEP-RFP references."""
    conn = connect()
    c = conn.cursor()

    # Find duplicates
    c.execute(
        "SELECT reference, COUNT(*) as cnt, "
        "GROUP_CONCAT(id) as ids, GROUP_CONCAT(entity) as entities "
        "FROM tenders WHERE reference LIKE 'GEP-RFP%' "
        "GROUP BY reference HAVING cnt > 1"
    )
    dupes = c.fetchall()

    log(f"Duplicate GEP-RFP references: {len(dupes)}", "3")

    merged_count = 0
    deleted_count = 0

    for dupe in dupes:
        ref = dupe["reference"]
        ids = dupe["ids"].split(",")
        entities = dupe["entities"].split(",")

        log(f"  {ref}: ids={ids} entities={entities}", "3")

        # Fetch data for each duplicate
        records = []
        for tid in ids:
            c.execute("SELECT * FROM tenders WHERE id=?", (tid,))
            records.append(dict(c.fetchone()))

        if len(records) < 2:
            continue

        # Decide which record to keep (prefer the one with more data)
        records.sort(key=lambda r: _record_richness(r), reverse=True)
        primary = records[0]
        secondaries = records[1:]

        log(f"    Primary: {primary['id']} (entity={primary['entity']}, richness={_record_richness(primary)})", "3")

        # Merge data from secondaries into primary
        primary_data = json.loads(primary["data"])

        for sec in secondaries:
            sec_data = json.loads(sec["data"])

            # Merge documents (dedup by filename)
            existing_filenames = {d.get("filename") for d in primary_data.get("documents", [])}
            for doc in sec_data.get("documents", []):
                if doc.get("filename") not in existing_filenames:
                    primary_data.setdefault("documents", []).append(doc)
                    existing_filenames.add(doc.get("filename"))

            # Merge portal_accounts
            primary_accounts = set(primary_data.get("metadata", {}).get("portal_accounts", []))
            sec_accounts = set(sec_data.get("metadata", {}).get("portal_accounts", []))
            merged_accounts = primary_accounts | sec_accounts
            if merged_accounts:
                primary_data.setdefault("metadata", {})
                primary_data["metadata"]["portal_accounts"] = list(merged_accounts)

            # Merge notes
            primary_notes = primary_data.get("metadata", {}).get("notes", [])
            sec_notes = sec_data.get("metadata", {}).get("notes", [])
            merged_notes = list(dict.fromkeys(primary_notes + sec_notes))  # dedup, preserve order
            if merged_notes:
                primary_data.setdefault("metadata", {})
                primary_data["metadata"]["notes"] = merged_notes

            # Keep earliest created, latest updated
            pri_meta = primary_data.get("metadata", {})
            sec_meta = sec_data.get("metadata", {})
            if sec_meta.get("created", "") < pri_meta.get("created", ""):
                pri_meta["created"] = sec_meta["created"]

            # Merge activity
            primary_activity = primary_data.get("activity", [])
            sec_activity = sec_data.get("activity", [])
            merged_activity = primary_activity + [
                a for a in sec_activity
                if a not in primary_activity
            ]
            if merged_activity:
                primary_data["activity"] = merged_activity

            # Merge scope
            pri_scope = primary_data.get("scope", {})
            sec_scope = sec_data.get("scope", {})
            for key in ("summary", "full_text", "industries"):
                if not pri_scope.get(key) and sec_scope.get(key):
                    pri_scope[key] = sec_scope[key]

        # Update document_count
        primary_data["document_count"] = len(primary_data.get("documents", []))

        # Update search_text
        search_parts = [primary.get("title", ""), ref, primary.get("issuer_name", "")]
        if primary_data.get("scope", {}).get("summary"):
            search_parts.append(primary_data["scope"]["summary"])
        primary["search_text"] = " ".join(search_parts)[:1000]

        if dry_run:
            continue

        # Update primary record
        c.execute(
            "UPDATE tenders SET data=?, search_text=?, document_count=?, updated_at=? WHERE id=?",
            (json.dumps(primary_data), primary["search_text"],
             primary_data["document_count"],
             datetime.now(timezone.utc).isoformat(), primary["id"]),
        )

        # Delete secondary records
        for sec in secondaries:
            c.execute("DELETE FROM tenders WHERE id=?", (sec["id"],))
            deleted_count += 1

        merged_count += 1

    conn.commit()
    conn.close()
    log(f"Merged: {merged_count} groups, deleted: {deleted_count} duplicates", "3")
    return merged_count, deleted_count


def _record_richness(r):
    """Score a tender record by data richness."""
    score = 0
    data = r.get("data", "{}")
    try:
        d = json.loads(data) if isinstance(data, str) else data
    except (json.JSONDecodeError, TypeError):
        d = {}

    # Documents have the most weight
    score += len(d.get("documents", [])) * 10
    # Scope text
    scope = d.get("scope", {})
    if scope.get("summary"):
        score += 5
    if scope.get("full_text"):
        score += 10
    # Line items
    score += len(d.get("line_items", [])) * 5
    # Activity
    score += len(d.get("activity", [])) * 2
    # Requirements
    reqs = d.get("requirements", {})
    if reqs.get("technical", {}).get("checklist"):
        score += 3
    if reqs.get("eligibility"):
        score += 2
    # Notes
    notes = d.get("metadata", {}).get("notes", [])
    score += len(notes)
    # Issuer with name
    issuer = d.get("issuer", {})
    if issuer.get("name"):
        score += 2

    return score


# ─── Phase 4: Verify & report ────────────────────────────────────────────────

def phase4_verify():
    """Verify all changes and report current state."""
    conn = connect()
    c = conn.cursor()

    log("=== Verification Report ===", "4")

    # 4a. source_type distribution
    c.execute("SELECT source_type, COUNT(*) as cnt FROM tenders GROUP BY source_type ORDER BY cnt DESC")
    log("Source type distribution:", "4")
    for row in c.fetchall():
        log(f"  {row['source_type']}: {row['cnt']}", "4")

    # 4b. SmartGEP entity distribution
    c.execute(
        "SELECT source_type, entity, COUNT(*) FROM tenders "
        f"WHERE entity IN ({','.join('?' * len(SMARTGEP_ENTITIES))}) "
        "GROUP BY source_type, entity ORDER BY source_type, entity",
        SMARTGEP_ENTITIES,
    )
    log("SmartGEP entity cross-tab:", "4")
    for row in c.fetchall():
        log(f"  {row[0]}: {row[1]} = {row[2]}", "4")

    # 4c. Dedup check
    c.execute(
        "SELECT reference, COUNT(*) as cnt FROM tenders "
        "WHERE reference LIKE 'GEP-RFP%' GROUP BY reference HAVING cnt > 1"
    )
    remaining_dupes = c.fetchall()
    if remaining_dupes:
        log(f"Remaining duplicates: {len(remaining_dupes)}", "4")
        for d in remaining_dupes:
            log(f"  {d['reference']} (x{d['cnt']})", "4")
    else:
        log("No remaining duplicates ✓", "4")

    # 4d. Pricesheet links
    event_map_path = PRICESHEET_DIR / "event_id_map.json"
    if event_map_path.exists():
        event_map = json.loads(event_map_path.read_text())
        linked = 0
        for ref in event_map:
            c.execute("SELECT COUNT(*) FROM tenders WHERE reference=?", (ref,))
            if c.fetchone()[0] > 0:
                linked += 1
        log(f"Pricesheet events linked to tender records: {linked}/{len(event_map)}", "4")

    # 4e. Total counts
    c.execute("SELECT COUNT(*) FROM tenders")
    total = c.fetchone()[0]
    log(f"Total tender records: {total}", "4")

    conn.close()
    return total


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--run" not in sys.argv
    undo = "--undo" in sys.argv

    if undo:
        backup = find_backup()
        if backup:
            restore_db(backup)
            print(f"  Undo complete. Restored from {backup}")
        else:
            print("  No backup found to restore from.")
        return

    mode = "DRY RUN (no changes)" if dry_run else "LIVE"
    print(f"\n{'='*60}")
    print(f"  SmartGEP Data Consolidation — {mode}")
    print(f"{'='*60}\n")

    # Backup before live run
    if not dry_run:
        backup_db()

    # Phase 1
    print(f"\n{'─'*40}")
    print("  Phase 1: source_type cleanup")
    print(f"{'─'*40}")
    p1_result = phase1_source_type_cleanup(dry_run=dry_run)
    print(f"  Phase 1 result: {p1_result} tenders affected")

    # Phase 2
    print(f"\n{'─'*40}")
    print("  Phase 2: Silo consolidation (pricesheet data)")
    print(f"{'─'*40}")
    # Require non-dry-run and have pricesheet dir
    p2_dry = dry_run
    if not os.path.exists(str(PRICESHEET_DIR / "event_id_map.json")):
        print("  Pricesheet data dir not found, skipping phase 2")
        p2_result = 0
    else:
        p2_result = phase2_silo_consolidation(dry_run=p2_dry)
    print(f"  Phase 2 result: {p2_result} tenders updated with pricesheet data")

    # Phase 3
    print(f"\n{'─'*40}")
    print("  Phase 3: Dedup GEP-RFP references")
    print(f"{'─'*40}")
    groups, deleted = phase3_dedup(dry_run=dry_run)
    print(f"  Phase 3 result: {groups} groups merged, {deleted} duplicates deleted")

    # Phase 4
    print(f"\n{'─'*40}")
    print("  Phase 4: Verification")
    print(f"{'─'*40}")
    phase4_verify()

    print(f"\n{'='*60}")
    if dry_run:
        print("  DRY RUN complete. Run with --run to execute.")
    else:
        print("  Consolidation complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
