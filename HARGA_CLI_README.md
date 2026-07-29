# Harga CLI

Command-line tool for Malaysian government procurement tender discovery and bid management.

## Architecture

```
tools/harga_cli/
├── __init__.py          # Package metadata
├── __main__.py          # Entry point, argument parsing
├── db.py                # Database connection & queries
├── commands/
│   ├── tenders.py       # Tender listing & filtering
│   ├── bids.py          # Bid management
│   └── entities.py      # Entity configuration
├── formatters.py        # JSON & text output formatting
└── errors.py            # Custom exceptions
```

## Command Structure

All commands follow this pattern:

```bash
harga-cli <command> [options]
```

### Tenders Command
```bash
harga-cli tenders --entity ePerolehan --status open --limit 10 --text
```
- `--entity`: Filter by procurement platform (ePerolehan, ForSAH, eTimad)
- `--status`: Filter by tender status (open, closed, awarded, etc)
- `--limit`: Max results (default: 50)
- `--offset`: Pagination offset (default: 0)
- `--text`: Human-readable output (default: JSON)

**Output (JSON)**:
```json
{
  "tenders": [
    {
      "id": "EPE-2026-00123",
      "title": "Office Supplies",
      "entity": "ePerolehan",
      "status": "open",
      "deadline": "2026-08-15T17:00:00Z",
      "amount": 50000
    }
  ],
  "total": 127,
  "limit": 10,
  "offset": 0
}
```

### Bids Command
```bash
harga-cli bids --entity BuzzBuzz --status active --text
```
- `--entity`: Filter by bidding entity (company name)
- `--status`: Filter by bid status (active, won, lost, overdue)
- `--limit`: Max results (default: 50)
- `--text`: Human-readable output

**Output (JSON)**:
```json
{
  "bids": [
    {
      "id": 42,
      "tender_id": "EPE-2026-00123",
      "entity_id": 3,
      "status": "active",
      "deadline": "2026-08-15T17:00:00Z",
      "amount": 48500,
      "created_at": "2026-07-28T10:30:00Z"
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

### Entities Command
```bash
harga-cli entities list
harga-cli entities config --entity-id 3 --notification-channel 123456
```
- `list`: Show all entities configured in the system
- `config`: Set notification channel (Telegram chat_id) for an entity

## Data Model

### harga_v8.db
- `bids` — Bid records with status, deadlines, amounts
- `entities` — Bidding entities (companies) with Telegram notification settings
- `audit_log` — All admin actions logged with timestamp

### tenders.db
- `tenders` — Tender records from ePerolehan, ForSAH, eTimad (deduplicated)

## Development

### Setup
```bash
cd /home/the_bomb/orkes_ds2
python -m pip install -e .
```

### Test
```bash
python -m pytest tests/test_harga_cli*.py -v
```

### Run
```bash
python -m tools.harga_cli tenders --help
harga-cli tenders --entity ePerolehan
```

## Implementation Checklist

- [ ] Database module (db.py) — connect, query templates, error handling
- [ ] Tenders command — query tenders.db, filter & paginate, format output
- [ ] Bids command — query harga_v8.db, show active/deadline status
- [ ] Entities command — list & configure notification channels
- [ ] Text formatter — human-readable table output (--text flag)
- [ ] Unit tests — each command tested against test DBs
- [ ] Integration tests — end-to-end CLI invocation
- [ ] pyproject.toml — entry point, dependencies, versioning
- [ ] Installation guide — pip/conda/manual setup

## Exit Codes

- `0` — Success
- `1` — Database error (DB locked, connection failed, query error)
- `2` — User error (invalid arguments, bad input format)

## Notes

- All commands are **idempotent** — safe to run multiple times
- Default output is **JSON** — machine-readable, stable schema
- Add `--text` flag for human-friendly output
- Queries use parameterized SQL to prevent injection
- Pagination: use `--limit` and `--offset` for large result sets
