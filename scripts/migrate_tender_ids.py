"""Migrate tender IDs from internal tdr-<hash> format to source-based IDs.

Rules:
  - government (ePE-QT): reference=QT<num>  →  ePE-QT-<num>
  - smartgep (GEP-RFP):  reference=GEP-RFP-<n>  →  as-is
                          reference=RFP-<n>      →  GEP-RFP-<n>
  - petronas:             reference=GEP-RFP-<n>  →  as-is
                          reference=RFP-<n>      →  GEP-RFP-<n>
                          reference=other        →  use reference (slugged)
  - unknown:              reference non-empty    →  use reference (slugged)
                          reference empty        →  keep existing tdr-<hash>

Duplicates get a -1, -2 suffix.
"""

import sqlite3, json, os, sys, re, shutil
from pathlib import Path
from collections import defaultdict

BACKUP = Path("/home/the_bomb/orkes_ds/data/db_backups/tenders_backup_20260504_201253.db")
TARGET = Path("/home/the_bomb/orkes/yellowpages/tenders/tenders.db")
MIGRATION_LOG = Path("/home/the_bomb/orkes_ds/data/db_backups/id_migration_log.txt")


def new_id_from_tender(row) -> str:
    """Compute the new source-based ID for a tender row."""
    tid, ref, stype, data_json = row["id"], row["reference"], row["source_type"], row["data"]

    # Empty reference → keep existing
    if not ref or ref.strip() == "":
        return tid

    ref = ref.strip()

    def make_valid(s: str) -> str:
        """Sanitize a string into a valid ID."""
        s = s.replace(" ", "-").replace("_", "-")
        s = re.sub(r"[^A-Za-z0-9\-]", "", s)
        return s

    # --- government: QT<num> → ePE-QT-<num> ---
    if stype == "government":
        # Remove leading zeros in the numeric part
        m = re.match(r"^(QT)(\d+)$", ref)
        if m:
            return f"ePE-QT-{m.group(2)}"
        return f"ePE-{make_valid(ref)}"

    # --- smartgep ---
    if stype == "smartgep":
        if ref.startswith("GEP-RFP-"):
            return ref
        if ref.startswith("RFP-"):
            return f"GEP-{ref}"
        return make_valid(ref)

    # --- petronas ---
    if stype == "petronas":
        if ref.startswith("GEP-RFP-"):
            return ref
        if ref.startswith("RFP-"):
            return f"GEP-{ref}"
        return make_valid(ref)

    # --- unknown ---
    if stype == "unknown":
        return make_valid(ref)

    return make_valid(ref)


def main():
    if not BACKUP.exists():
        print(f"ERROR: backup not found at {BACKUP}")
        sys.exit(1)

    # Work on a copy
    work_path = BACKUP.parent / "tenders_working_migrate.db"
    shutil.copy2(BACKUP, work_path)
    print(f"Working copy: {work_path}")

    conn = sqlite3.connect(work_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Load all tenders and compute new IDs
    cur.execute("SELECT id, reference, source_type, data FROM tenders ORDER BY rowid")
    rows = cur.fetchall()

    mapping = {}  # old_id → new_id
    seen = defaultdict(int)  # new_id → count

    log_lines = []
    for r in rows:
        row_dict = dict(r)
        new_id = new_id_from_tender(row_dict)

        # Handle duplicates
        if new_id != row_dict["id"]:
            seen[new_id] += 1
            if seen[new_id] > 1:
                new_id = f"{new_id}-{seen[new_id]}"

        mapping[row_dict["id"]] = new_id

        old_id = row_dict["id"]
        if old_id != new_id:
            log_lines.append(f"{old_id}  →  {new_id}  ({row_dict['source_type']}: {row_dict['reference']})")

    changed = sum(1 for k, v in mapping.items() if k != v)
    kept = sum(1 for k, v in mapping.items() if k == v)
    print(f"\nMapping: {changed} changed, {kept} kept unchanged, {len(mapping)} total")

    # Write migration log
    with open(MIGRATION_LOG, "w") as f:
        f.write(f"ID Migration Log\n")
        f.write(f"Source: {BACKUP.name}\n")
        f.write(f"Total: {len(mapping)}, Changed: {changed}, Kept: {kept}\n\n")
        f.write("\n".join(log_lines))
    print(f"Log written to {MIGRATION_LOG}")

    # 2. Update tenders table
    print("\nUpdating tenders table...")
    cur.execute("BEGIN TRANSACTION")
    for old_id, new_id in mapping.items():
        if old_id == new_id:
            continue
        # Update id column
        cur.execute("UPDATE tenders SET id = ? WHERE id = ?", (new_id, old_id))
        # Update data JSON
        cur.execute("SELECT data FROM tenders WHERE id = ?", (new_id,))
        row = cur.fetchone()
        if row:
            d = json.loads(row["data"])
            if d.get("id") == old_id:
                d["id"] = new_id
            cur.execute("UPDATE tenders SET data = ? WHERE id = ?", (json.dumps(d), new_id))

    # 3. Update wizard_sessions
    print("Updating wizard_sessions...")
    cur.execute("SELECT id, tender_id FROM wizard_sessions")
    for r in cur.fetchall():
        old_tid = r["tender_id"]
        if old_tid in mapping and mapping[old_tid] != old_tid:
            cur.execute("UPDATE wizard_sessions SET tender_id = ? WHERE id = ?",
                        (mapping[old_tid], r["id"]))

    # 4. Update pricing_versions
    print("Updating pricing_versions...")
    cur.execute("SELECT id, tender_id FROM pricing_versions")
    for r in cur.fetchall():
        old_tid = r["tender_id"]
        if old_tid in mapping and mapping[old_tid] != old_tid:
            cur.execute("UPDATE pricing_versions SET tender_id = ? WHERE id = ?",
                        (mapping[old_tid], r["id"]))

    # 5. Update audit_log (resource_type='tender')
    print("Updating audit_log...")
    cur.execute("SELECT id, resource_type, resource_id FROM audit_log")
    for r in cur.fetchall():
        if r["resource_type"] == "tender":
            old_rid = r["resource_id"]
            if old_rid in mapping and mapping[old_rid] != old_rid:
                cur.execute("UPDATE audit_log SET resource_id = ? WHERE id = ?",
                            (mapping[old_rid], r["id"]))

    conn.commit()

    # 6. Verify
    print("\n=== Verification ===")
    cur.execute("SELECT COUNT(*) FROM tenders")
    print(f"Tenders: {cur.fetchone()[0]}")

    cur.execute("SELECT source_type, COUNT(*) FROM tenders GROUP BY source_type")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")

    # Sample new IDs
    cur.execute("SELECT id, source_type, reference FROM tenders ORDER BY RANDOM() LIMIT 15")
    print("\nSample new IDs:")
    for r in cur.fetchall():
        print(f"  {r['source_type']:15s} {r['id']:40s} (ref: {r['reference']})")

    # Check for any remaining tdr- IDs
    cur.execute("SELECT COUNT(*) FROM tenders WHERE id LIKE 'tdr-%'")
    remaining = cur.fetchone()[0]
    print(f"\nRemaining tdr-* IDs: {remaining}")

    # Check for duplicates in new IDs
    cur.execute("SELECT id, COUNT(*) FROM tenders GROUP BY id HAVING COUNT(*) > 1")
    dupes = cur.fetchall()
    if dupes:
        print(f"WARNING: {len(dupes)} duplicate IDs after migration:")
        for d in dupes:
            print(f"  {d['id']} ({d[1]}x)")
    else:
        print("No duplicate IDs — clean!")

    # Verify related tables still reference valid tender IDs
    for tbl, col in [("wizard_sessions", "tender_id"), ("pricing_versions", "tender_id")]:
        cur.execute(f"SELECT DISTINCT {col} FROM {tbl}")
        refs = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT id FROM tenders")
        valid = {r[0] for r in cur.fetchall()}
        orphaned = refs - valid
        if orphaned:
            print(f"WARNING: {tbl} has {len(orphaned)} orphaned references: {orphaned}")
        else:
            print(f"{tbl}: all references valid ({len(refs)} refs)")

    conn.close()

    # 7. All good? Replace target
    print(f"\n--- Restore ---")
    target_bak = TARGET.parent / "tenders.db.pre_migrate_bak"
    if TARGET.exists():
        shutil.copy2(TARGET, target_bak)
        print(f"Backed up current target → {target_bak}")
    shutil.copy2(work_path, TARGET)
    print(f"Restored migrated DB → {TARGET} ({TARGET.stat().st_size} bytes)")

    # Cleanup working copy
    os.unlink(work_path)
    print(f"Cleaned up working copy")

    print("\nDone. Tender IDs migrated in backup and restored.")


if __name__ == "__main__":
    main()
