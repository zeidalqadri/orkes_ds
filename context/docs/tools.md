# Tool Taxonomy

All tools available to the agent, with descriptions and usage rules.

## Read Tools

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `Read` | Read file/directory contents by absolute path | Any time you need file contents | Use offset/limit for large files. Returns max 2000 lines. |
| `Glob` | Find files by glob pattern (e.g. `**/*.py`) | Need to locate files by name pattern | Returns paths sorted by modification time. |
| `Grep` | Search file contents by regex | Need to find specific code or text | Use `include` to filter by file type. |

## Write/Edit Tools

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `edit` | Replace exact text in a file | Precise surgical edits, renames | MUST read file first. Fails if old_string not found. 3 edits max per file per message. |
| `write` | Write/overwrite entire file | New files, complete rewrites | MUST read first if file exists. |
| `replaceAll` (edit param) | Replace all occurrences of a string | Bulk rename across file | Set `replaceAll: true` on edit. |

## Search/Discovery Tools

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `Grep` | Regex content search | Find specific code patterns |
| `Glob` | File pattern matching | Find files by name/extension |
| `Task` (explore) | Launch sub-agent for deep codebase exploration | Need comprehensive search across multiple naming conventions | Use `subagent_type: explore` with desired thoroughness. |

## Execution Tools

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `Bash` | Run shell commands with timeout | Git, npm, docker, python, pm2 | Use `workdir` instead of `cd`. 120s default timeout. |
| `WebFetch` | Fetch URL content | Need web content | HTTP→HTTPS auto. Returns markdown. |

## Agent Communication

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `Task` (general) | Launch sub-agent for multi-step work | Parallel work, delegated sub-tasks | Compress context to <2000 tokens before handoff. |
| `Task` (review) | Read-only code review | Verify implementation quality | Does NOT edit files. |
| `Task` (writer) | One-shot code generation | Producing standalone artifacts | No planning required. |
| `Skill` | Load specialized skill instructions | When task matches a skill description | Skills at ~/.claude/skills/<name>/SKILL.md |

## Context Management

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `compress` | Summarize and compact conversation | After goals, before handoffs, when context > 80% | Must be exhaustive. Preserve user intent. Never mid-task unless blocked. |
| `compress` with blocks | Selective range compression | Closed sections, dead ends | Cannot overlap ranges. Use boundary IDs. |

## EnvSitter Tools

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `envsitter_keys` | List .env key names (no values) | Audit what env vars exist | Never returns values. |
| `envsitter_match` | Check if value matches criteria | Verify env config without exposing values | Supports exists/empty/equal/prefix/suffix/regex. |
| `envsitter_scan` | Detect value shapes (jwt/url/base64) | Security audit of secrets | Never reveals values. |
| `envsitter_set` | Set a key value in .env | Configure env vars safely | Dry-run by default; use `write: true` to persist. |
| `envsitter_format` | Reorder/format .env file | Clean up messy .env files | Dry-run by default. |
| `envsitter_copy` | Copy keys between .env files | Propagate config across projects | Dry-run by default. |

## Meta Tools

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `todowrite` | Create/manage task list | Complex tasks with 3+ steps | One `in_progress` at a time. |
| `todoread` | Read current task list | Check progress mid-task |

## Compression Tools

| Tool | What It Does | When To Use | Rules |
|------|-------------|-------------|-------|
| `compress` | Summarize and compact conversation history | After goals, before expert handoffs, when context > 80% | Must be exhaustive. Preserve user intent. Never mid-task unless blocked. |
| `compress` (range) | Selective compression of closed sections | Dead ends, completed exploration, research phases | Boundaries must not overlap. Use injected boundary IDs. |

## Behavioral Rules (All Tools)

1. **Read before edit**: Must read a file before editing it.
2. **Verify after edit**: Read file after edit to confirm change applied.
3. **No secrets in output**: Never output .env contents, tokens, or keys.
4. **Tool result truncation**: Results >50K chars are truncated. Re-run with narrower scope if results seem short.
5. **Edit integrity**: Edit tool fails silently on stale context. Always re-read before retry.
