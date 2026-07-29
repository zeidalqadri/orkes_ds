# Harga CLI Development Guide

This guide explains how to develop, test, and release the harga-cli tool with the expert team.

## Project Structure

```
orkes_ds2/
├── CLAUDE.md                      # Architecture & verification checklist
├── PROMPT.md                      # Agent prompt (GOAL.md, STATE.md, INBOX.md driven)
├── DEVELOP.md                     # This file — development workflow
├── HARGA_CLI_README.md            # CLI spec & command reference
├── pyproject.toml                 # Package config, entry point, dependencies
├── tools/
│   └── harga_cli/
│       ├── __init__.py            # Version
│       ├── __main__.py            # Entry point & argument parsing
│       ├── db.py                  # Database connections & queries
│       ├── formatters.py          # JSON & text output formatting
│       ├── errors.py              # Custom exceptions
│       └── commands/
│           ├── __init__.py
│           ├── tenders.py         # 'harga-cli tenders' implementation
│           ├── bids.py            # 'harga-cli bids' implementation
│           └── entities.py        # 'harga-cli entities' implementation
├── tests/
│   ├── conftest.py                # Pytest fixtures (test DBs, sample data)
│   └── test_harga_cli_example.py  # Example test patterns (to implement)
├── data/
│   ├── harga_v8.db                # Bids, entities, audit log (must exist)
│   └── tenders.db                 # Tender feed (must exist)
└── context/
    ├── experts.json               # Expert definitions (cli-builder, etc.)
    ├── STATE.md                   # Agent loop state (phase, approach)
    ├── GOAL.md                    # Current objective
    └── INBOX.md                   # Operator notes (consumed each step)
```

## Setup

1. **Install package in development mode:**
   ```bash
   cd /home/the_bomb/orkes_ds2
   python -m pip install -e .
   ```

2. **Verify installation:**
   ```bash
   harga-cli --version  # Should show "harga-cli 0.1.0"
   harga-cli --help      # Should show all subcommands
   ```

3. **Ensure databases exist:**
   ```bash
   ls -la data/harga_v8.db data/tenders.db  # Both must exist
   ```

## Development Workflow

### Phase 1: Plan (Read-Only)

1. **Operator writes goal** to `context/GOAL.md`:
   ```
   Implement 'tenders' command: list, filter by entity, paginate with limit/offset
   ```

2. **Conductor reads goal** → breaks into tasks for builders:
   ```
   @cli-builder: Implement query_tenders() in db.py
   @cli-builder: Implement handle_tenders() in commands/tenders.py
   @cli-builder: Update __main__.py to call handle_tenders()
   @cli-tester: Write tests for tenders command
   @cli-reviewer: Audit code for SQL injection, performance
   @cli-deployer: Verify installation & entry point work
   ```

3. **Builders write approach** to `context/STATE.md`:
   ```
   phase: PLAN
   approach: |
     - Use sqlite3 with parameterized queries
     - Join tenders table with entities for filtering
     - Return list of dicts, not Row objects
   files:
     - MODIFY: tools/harga_cli/db.py (query_tenders)
     - MODIFY: tools/harga_cli/commands/tenders.py (handle_tenders)
     - MODIFY: tools/harga_cli/__main__.py (dispatch)
     - CREATE: tests/test_harga_cli_tenders.py
   verify:
     - python -m pytest tests/test_harga_cli_tenders.py -v
     - harga-cli tenders --help
   ```

### Phase 2: Act (Read-Write)

1. **Builders implement** the functions (remove NotImplementedError placeholders)
2. **Builders run tests** locally: `python -m pytest tests/ -v`
3. **Builders commit:** describe what was implemented and any learnings
4. **Testers write tests** and verify coverage (conftest.py provides fixtures)
5. **Reviewers audit** for security (SQL injection, input validation), performance
6. **Deployers verify** installation: `pip install -e .` and `harga-cli --help`

## Implementation Patterns

### Query Template

```python
def query_tenders(
    entity: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query with optional filters, return list of dicts."""
    conn = get_tenders_db()
    try:
        cursor = conn.cursor()

        # Build parameterized query
        query = "SELECT id, title, entity, status, deadline, amount FROM tenders WHERE 1=1"
        params = []

        if entity:
            query += " AND entity = ?"
            params.append(entity)

        if status:
            query += " AND status = ?"
            params.append(status)

        # Pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        tenders = [dict(row) for row in cursor.fetchall()]

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

        return tenders, total

    except sqlite3.Error as e:
        raise DatabaseError(f"Query failed: {e}") from e
    finally:
        conn.close()
```

### Handler Template

```python
def handle_tenders(
    entity: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    as_text: bool = False,
) -> str:
    """Query tenders, format, and return as string."""
    try:
        tenders, total = query_tenders(entity, status, limit, offset)
        data = {
            "tenders": tenders,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
        return format_tenders(data, as_text)
    except DatabaseError as e:
        return json.dumps({"error": str(e)})
```

### Test Template

```python
def test_query_tenders_filter_by_entity(self, sample_tenders):
    """Test filtering by entity returns only matching records."""
    from tools.harga_cli.db import query_tenders

    tenders, total = query_tenders(entity="ePerolehan")

    # Verify results
    assert total > 0, "Should find tenders for ePerolehan"
    assert all(t["entity"] == "ePerolehan" for t in tenders), "All results match filter"
```

## Verification Checklist

Each deliverable must pass these checks:

| Task | Verify | Command |
|------|--------|---------|
| **db.py** | Syntax check | `python -c "import py_compile; py_compile.compile('tools/harga_cli/db.py', doraise=True)"` |
| **commands/** | Syntax check | `python -c "from tools.harga_cli.commands import *; print('OK')"` |
| **formatters.py** | Syntax check | `python -c "from tools.harga_cli.formatters import *; print('OK')"` |
| **__main__.py** | Help works | `python -m tools.harga_cli --help` |
| **All commands** | Argument parsing | `harga-cli tenders --help` and `harga-cli bids --help` |
| **Tests** | All pass | `python -m pytest tests/ -v --tb=short` |
| **Installation** | Entry point | `harga-cli --version` (after `pip install -e .`) |

## Code Standards

- **SQL**: Always parameterized (use `?` placeholders, never f-strings)
- **Errors**: Raise custom exceptions from `errors.py`, include context
- **Output**: Default JSON, use `--text` flag for human-readable tables
- **Exit codes**: 0=success, 1=database error, 2=user argument error
- **Typing**: Use type hints for all function signatures
- **Docstrings**: Include Args, Returns, Raises sections

## Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test
```bash
python -m pytest tests/test_harga_cli_tenders.py::TestTendersCommand::test_query_tenders_all -v
```

### Check Coverage
```bash
python -m pytest tests/ --cov=tools/harga_cli --cov-report=term-missing
```

### Debug a Test
```bash
python -m pytest tests/test_harga_cli_tenders.py::TestTendersCommand::test_query_tenders_all -vv -s
```

## Release

When ready to release a new version:

1. **Update version** in `tools/harga_cli/__init__.py`:
   ```python
   __version__ = "0.2.0"  # Semantic versioning
   ```

2. **Update pyproject.toml**:
   ```toml
   version = "0.2.0"
   ```

3. **Tag in git**:
   ```bash
   git tag v0.2.0
   git push --tags
   ```

4. **Build distribution** (deployer task):
   ```bash
   python -m pip install build
   python -m build
   # Creates dist/harga-cli-0.2.0.tar.gz and dist/harga-cli-0.2.0-py3-none-any.whl
   ```

## Escalation

If stuck, write diagnostics to `context/STATE.md`:

```
## Blocker

**Issue**: query_tenders() fails with "table does not exist"

**Root Cause**: tenders.db schema doesn't match expected columns

**Tried**:
1. Checked data/tenders.db exists ✓
2. Ran sqlite3 ".schema" — columns are id, name, NOT title
3. Updated query to use 'name' instead of 'title'

**Solution**: Update HARGA_CLI_README.md to match actual schema
```

Then escalate to operator via: `python arbos.py send "blocker: schema mismatch"`

## References

- **CLAUDE.md**: Architecture, experts, verification tables
- **PROMPT.md**: Agent loop constraints, expert activation
- **HARGA_CLI_README.md**: Command spec, data model, examples
- **pyproject.toml**: Dependencies, entry point, coverage config
