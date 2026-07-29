# Developer Quickstart

Get harga-cli building in 5 minutes.

## Setup

### 1. Activate environment (one-time)

```bash
cd /home/the_bomb/orkes_ds2
source /home/the_bomb/orkes/.venv/bin/activate
```

### 2. Verify infrastructure

```bash
bash SETUP_VERIFY.sh
```

All ✓? You're ready to build.

---

## Development Workflow

### 1. Read the reference

```bash
cat context/HARGA_CLI_REFERENCE.md  # DB schemas, module APIs, CLI surface
```

Key facts:
- **Entry point**: `/home/the_bomb/orkes/harga/harga_cli.py` (single file, argparse)
- **Databases**: `/home/the_bomb/orkes/harga/data/` (harga_v8.db, price_memory.db, supplier_index.db)
- **Reusable modules**: `modules/bid_crud.py`, `orkes_pricing.price_memory`, `orkes_tender.tender_db`
- **Venv**: `/home/the_bomb/orkes/.venv/`

### 2. Understand the task

Read `context/GOAL.md` and `context/<your-handle>/GOAL.md` from conductor.

Example goal:
> Implement tenders subcommand: list, filter by entity, paginate with limit/offset

### 3. Implement

Use the patterns in `context/shared_learnings.md`:

**Query function** (in db.py or harga_cli.py):
```python
import sqlite3
from pathlib import Path

DB_PATH = "/home/the_bomb/orkes/harga/data/tenders.db"

def query_tenders(entity=None, status=None, limit=50, offset=0):
    """Query with optional filters, return (rows, total)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Named tuples
    try:
        cursor = conn.cursor()

        # Build parameterized query
        query = "SELECT * FROM tenders WHERE 1=1"
        params = []
        if entity:
            query += " AND entity = ?"
            params.append(entity)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]

        # Count total
        count_query = "SELECT COUNT(*) FROM tenders WHERE 1=1"
        count_params = []
        if entity:
            count_query += " AND entity = ?"
            count_params.append(entity)
        if status:
            count_query += " AND status = ?"
            count_params.append(status)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]

        return rows, total
    finally:
        conn.close()
```

**Output formatter** (JSON default, --text optional):
```python
import json

def format_tenders(rows, total, as_text=False):
    """Format rows as JSON or human-readable table."""
    if as_text:
        # Simple table: | id | title | entity | status |
        if not rows:
            return "No results."
        print("| ID | Title | Entity | Status |")
        print("|-------|-------|--------|--------|")
        for r in rows:
            print(f"| {r['id']} | {r['title'][:30]:<30} | {r['entity']:<8} | {r['status']:<8} |")
        return ""
    else:
        return json.dumps({"rows": rows, "total": total, "limit": len(rows), "offset": 0}, indent=2)
```

**Argument parsing** (in __main__.py):
```python
import argparse

parser = argparse.ArgumentParser(prog="harga-cli")
subparsers = parser.add_subparsers(dest="command")

# Tenders subcommand
tenders_parser = subparsers.add_parser("tenders", help="Tender operations")
tenders_parser.add_argument("--entity", help="Filter by entity slug")
tenders_parser.add_argument("--status", help="Filter by status")
tenders_parser.add_argument("--limit", type=int, default=50, help="Max results")
tenders_parser.add_argument("--offset", type=int, default=0, help="Pagination offset")
tenders_parser.add_argument("--text", action="store_true", help="Human-readable table")

args = parser.parse_args()
if args.command == "tenders":
    rows, total = query_tenders(args.entity, args.status, args.limit, args.offset)
    output = format_tenders(rows, total, args.text)
    print(output)
    sys.exit(0)
```

### 4. Test

**Unit test** (in tests/test_harga_cli.py using conftest.py fixtures):
```python
def test_query_tenders_all(sample_tenders):
    """Test query returns all results when no filters."""
    from tools.harga_cli import query_tenders

    rows, total = query_tenders()
    assert len(rows) == 3  # From fixture
    assert total == 3

def test_query_tenders_filter_by_entity(sample_tenders):
    """Test filtering by entity."""
    rows, total = query_tenders(entity="ePerolehan")
    assert all(r["entity"] == "ePerolehan" for r in rows)

def test_cli_tenders_help():
    """Test CLI help works."""
    result = subprocess.run(
        ["/home/the_bomb/orkes/.venv/bin/python", "-m", "tools.harga_cli", "tenders", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "entity" in result.stdout
```

**Run tests**:
```bash
cd /home/the_bomb/orkes/harga
/home/the_bomb/orkes/.venv/bin/python -m pytest tests/test_harga_cli.py -v
```

### 5. Verify

**Syntax check**:
```bash
python -c "import py_compile; py_compile.compile('/home/the_bomb/orkes/harga/harga_cli.py', doraise=True)"
```

**Smoke test**:
```bash
/home/the_bomb/orkes/.venv/bin/python /home/the_bomb/orkes/harga/harga_cli.py --help
/home/the_bomb/orkes/.venv/bin/python /home/the_bomb/orkes/harga/harga_cli.py tenders --help
```

### 6. Commit + report

```bash
cd /home/the_bomb/orkes/harga
git add harga_cli.py tests/
git commit -m "feat: implement tenders subcommand (list, filter by entity/status, paginate)"
```

Write learnings to `context/builder/learnings.md`:
```markdown
## Tenders Subcommand Implementation

**Pattern**: Parameterized queries + separate count query for pagination

**Gotcha**: SQLite Row factory requires `conn.row_factory = sqlite3.Row` to get dict-like access

**Why**: `cursor.fetchall()` returns Row objects by default; converting to dict with `dict(row)` makes JSON serialization trivial

**Next**: Apply same pattern for bids subcommand (same DB, different table)
```

---

## Common Commands

```bash
# Navigate to project
cd /home/the_bomb/orkes_ds2

# Activate venv
source /home/the_bomb/orkes/.venv/bin/activate

# Read reference
cat context/HARGA_CLI_REFERENCE.md

# Read shared learnings
cat context/shared_learnings.md

# Check databases
sqlite3 /home/the_bomb/orkes/harga/data/harga_v8.db ".tables"
sqlite3 /home/the_bomb/orkes/harga/data/harga_v8.db ".schema v8_bids" | head -20

# Run tests
cd /home/the_bomb/orkes/harga && python -m pytest tests/test_harga_cli.py -v

# Verify syntax
python -c "import py_compile; py_compile.compile('/home/the_bomb/orkes/harga/harga_cli.py', doraise=True)"

# Try the CLI
/home/the_bomb/orkes/.venv/bin/python /home/the_bomb/orkes/harga/harga_cli.py --help
```

---

## Troubleshooting

### Import errors: ModuleNotFoundError

**Problem**: Can't import orkes_core, orkes_pricing, orkes_tender

**Solution**: They're pip-installed from `/home/the_bomb/orkes/packages/`. Verify:
```bash
pip list | grep orkes
# Should show:
#   orkes-core     0.2.0 /home/the_bomb/orkes/packages/orkes_core
#   orkes-pricing  0.2.0 /home/the_bomb/orkes/packages/orkes_pricing
#   orkes-tender   0.2.0 /home/the_bomb/orkes/packages/orkes_tender
```

### Database locked: sqlite3.OperationalError: database is locked

**Problem**: Another process has the DB open

**Solution**: Usually transient. Try again in 1-2 seconds. If persistent, find the process:
```bash
lsof /home/the_bomb/orkes/harga/data/harga_v8.db
```

### Absolute path errors

**Problem**: Test fails with "no such file or directory"

**Solution**: Always use absolute paths in code. Never use relative paths or `~` expansions.

```python
# ❌ Wrong
DB_PATH = "data/harga_v8.db"
DB_PATH = "~/orkes/harga/data/harga_v8.db"

# ✅ Right
DB_PATH = "/home/the_bomb/orkes/harga/data/harga_v8.db"
```

---

## Resources

- **Architecture**: `CLAUDE.md`
- **Reference**: `context/HARGA_CLI_REFERENCE.md`
- **Patterns**: `context/shared_learnings.md`
- **Expert Guide**: `EXPERT_ACTIVATION.md`
- **Setup Check**: `bash SETUP_VERIFY.sh`
- **Entry point**: `/home/the_bomb/orkes/harga/harga_cli.py`

---

## Next

1. Read `context/GOAL.md`
2. Run `bash SETUP_VERIFY.sh` to confirm setup
3. Read `context/HARGA_CLI_REFERENCE.md` to understand DB & modules
4. Implement your task
5. Write tests
6. Verify + commit
7. Update `context/shared_learnings.md` with new patterns
