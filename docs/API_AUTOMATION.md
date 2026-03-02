# Unmanic API Automation Guide

Unmanic exposes a REST API (v2) for programmatic control of workers and library settings.
This guide covers the endpoints most useful for automation scripts — pausing workers
during disk-intensive operations, toggling library scanners, and combining both into
end-to-end recipes.

## Overview

| Detail | Value |
|--------|-------|
| Base URL | `http://<host>:8888/unmanic/api/v2` |
| Content-Type | `application/json` |
| Authentication | None (local network assumed) |
| Swagger UI | `http://<host>:8888/unmanic/swagger` |

All endpoints return JSON. Success responses use HTTP 200; errors use standard codes
(400 for bad input, 500 for internal failures) with an `error` string and optional
`messages` object.

> **Tip:**  The Swagger UI is the fastest way to explore all available endpoints
> interactively. Open it in your browser at `/unmanic/swagger`.

## Worker Control

Workers process queued tasks. Each worker belongs to a **worker group** with a
randomly-generated name (e.g., "Altoa", "Zuljah"). Worker IDs follow the format
`{group_name}-{index}` — for example, `Altoa-0` is the first worker in the "Altoa"
group.

> **Important:**  Worker IDs are dynamic. Always discover them at runtime via the
> status endpoint rather than hardcoding values.

### Get Workers Status

Returns the status of all active workers, including their IDs, pause state, and
current task info.

```bash
curl -s http://localhost:8888/unmanic/api/v2/workers/status | jq
```

**Response** (abbreviated):

```json
{
  "success": true,
  "workers_status": [
    {
      "id": "Altoa-0",
      "name": "Altoa-Worker-1",
      "idle": true,
      "paused": false,
      "start_time": null,
      "current_task": null,
      "current_file": "",
      "current_command": null,
      "worker_log_tail": [],
      "runners_info": {},
      "subprocess": null
    }
  ]
}
```

### Pause a Single Worker

```bash
curl -s -X POST http://localhost:8888/unmanic/api/v2/workers/worker/pause \
  -H 'Content-Type: application/json' \
  -d '{"worker_id": "Altoa-0"}'
```

### Pause All Workers

```bash
curl -s -X POST http://localhost:8888/unmanic/api/v2/workers/worker/pause/all
```

### Resume a Single Worker

```bash
curl -s -X POST http://localhost:8888/unmanic/api/v2/workers/worker/resume \
  -H 'Content-Type: application/json' \
  -d '{"worker_id": "Altoa-0"}'
```

### Resume All Workers

```bash
curl -s -X POST http://localhost:8888/unmanic/api/v2/workers/worker/resume/all
```

## Library Scanner Control

Each library has independent scanner and inotify (file-watch) settings. To
enable or disable scanning, you read the current library config, modify it,
and write it back.

### List All Libraries

```bash
curl -s http://localhost:8888/unmanic/api/v2/settings/libraries | jq
```

**Response** (abbreviated):

```json
{
  "success": true,
  "libraries": [
    {
      "id": 1,
      "name": "Movies",
      "path": "/library/movies",
      "locked": false,
      "enable_remote_only": false,
      "enable_scanner": true,
      "enable_inotify": true,
      "tags": []
    }
  ]
}
```

### Read Library Configuration

```bash
curl -s -X POST http://localhost:8888/unmanic/api/v2/settings/library/read \
  -H 'Content-Type: application/json' \
  -d '{"id": 1}'
```

**Response** (abbreviated):

```json
{
  "success": true,
  "library_config": {
    "id": 1,
    "name": "Movies",
    "path": "/library/movies",
    "locked": false,
    "enable_remote_only": false,
    "enable_scanner": true,
    "enable_inotify": true,
    "priority_score": 100,
    "tags": []
  },
  "plugins": {
    "enabled_plugins": []
  }
}
```

### Write Library Configuration

Updates a library's settings. The request body **must** wrap the config inside a
`library_config` key — see [Common Pitfalls](#the-library_config-nesting-requirement).

```bash
curl -s -X POST http://localhost:8888/unmanic/api/v2/settings/library/write \
  -H 'Content-Type: application/json' \
  -d '{
    "library_config": {
      "id": 1,
      "name": "Movies",
      "path": "/library/movies",
      "enable_scanner": false,
      "enable_inotify": false,
      "priority_score": 100,
      "tags": []
    }
  }'
```

### Trigger Library Rescan

Queues a full library scan regardless of scheduler state.

```bash
curl -s -X POST http://localhost:8888/unmanic/api/v2/pending/rescan
```

## Common Pitfalls

### The `library_config` Nesting Requirement

When writing library settings, the config **must** be nested under a `library_config`
key. Sending fields at the top level returns a 400 with "Unknown field" errors.

```bash
# WRONG — fields at top level, returns 400
curl -X POST .../settings/library/write \
  -H 'Content-Type: application/json' \
  -d '{"id": 1, "enable_scanner": false}'

# CORRECT — nested under library_config
curl -X POST .../settings/library/write \
  -H 'Content-Type: application/json' \
  -d '{"library_config": {"id": 1, "enable_scanner": false}}'
```

### Dynamic Worker IDs

Worker IDs are not sequential integers. They combine the worker group name with a
zero-based index (e.g., `Altoa-0`, `Zuljah-1`). Group names are randomly assigned
when a worker group is created.

Always query `/api/v2/workers/status` first to discover current worker IDs:

```bash
# Extract just the worker IDs
curl -s http://localhost:8888/unmanic/api/v2/workers/status \
  | jq -r '.workers_status[].id'
```

### Error Response Format

Failed requests return a JSON body with an `error` string. For validation failures
(HTTP 400), the `messages` object contains per-field errors:

```json
{
  "error": "400: Failed request schema validation",
  "messages": {
    "worker_id": ["Missing data for required field."]
  }
}
```

## Recipes

### Pause Workers During Disk-Intensive Operations

A common use case: pause all Unmanic processing during a parity check, backup, or
disk scrub, then restore the original state afterward.

```bash
#!/usr/bin/env bash
# unmanic-maintenance-mode.sh
# Pauses all workers and disables library scanners before a maintenance
# operation, then restores everything when done.
#
# Usage:
#   unmanic-maintenance-mode.sh <start|stop> [unmanic_url]
#
# Examples:
#   unmanic-maintenance-mode.sh start
#   unmanic-maintenance-mode.sh stop http://10.0.0.5:8888

set -euo pipefail

ACTION="${1:?Usage: $0 <start|stop> [unmanic_url]}"
BASE_URL="${2:-http://localhost:8888}"
API="${BASE_URL}/unmanic/api/v2"
STATE_FILE="/tmp/unmanic-maintenance-state.json"

pause_all_workers() {
  echo "Pausing all workers..."
  curl -sf -X POST "${API}/workers/worker/pause/all" > /dev/null
  echo "All workers paused."
}

resume_all_workers() {
  echo "Resuming all workers..."
  curl -sf -X POST "${API}/workers/worker/resume/all" > /dev/null
  echo "All workers resumed."
}

save_scanner_state() {
  echo "Saving current library scanner state..."
  local libraries
  libraries=$(curl -sf "${API}/settings/libraries")

  # Save each library's scanner and inotify state
  echo "$libraries" | jq '[.libraries[] | {id, enable_scanner, enable_inotify}]' \
    > "$STATE_FILE"

  echo "State saved to ${STATE_FILE}"
}

disable_all_scanners() {
  echo "Disabling all library scanners..."
  local libraries
  libraries=$(curl -sf "${API}/settings/libraries")

  echo "$libraries" | jq -c '.libraries[]' | while read -r lib; do
    local lib_id
    lib_id=$(echo "$lib" | jq '.id')

    # Read full config for this library
    local config
    config=$(curl -sf -X POST "${API}/settings/library/read" \
      -H 'Content-Type: application/json' \
      -d "{\"id\": ${lib_id}}")

    # Disable scanner and inotify, write back
    local updated
    updated=$(echo "$config" | jq '.library_config.enable_scanner = false | .library_config.enable_inotify = false')

    curl -sf -X POST "${API}/settings/library/write" \
      -H 'Content-Type: application/json' \
      -d "$updated" > /dev/null

    local name
    name=$(echo "$lib" | jq -r '.name')
    echo "  Disabled scanner for library: ${name}"
  done
}

restore_scanners() {
  if [ ! -f "$STATE_FILE" ]; then
    echo "No saved state found at ${STATE_FILE}. Skipping scanner restore."
    return
  fi

  echo "Restoring library scanner state..."
  jq -c '.[]' "$STATE_FILE" | while read -r saved; do
    local lib_id enable_scanner enable_inotify
    lib_id=$(echo "$saved" | jq '.id')
    enable_scanner=$(echo "$saved" | jq '.enable_scanner')
    enable_inotify=$(echo "$saved" | jq '.enable_inotify')

    # Read current config
    local config
    config=$(curl -sf -X POST "${API}/settings/library/read" \
      -H 'Content-Type: application/json' \
      -d "{\"id\": ${lib_id}}")

    # Restore original scanner settings
    local updated
    updated=$(echo "$config" | jq \
      --argjson scanner "$enable_scanner" \
      --argjson inotify "$enable_inotify" \
      '.library_config.enable_scanner = $scanner | .library_config.enable_inotify = $inotify')

    curl -sf -X POST "${API}/settings/library/write" \
      -H 'Content-Type: application/json' \
      -d "$updated" > /dev/null
  done

  rm -f "$STATE_FILE"
  echo "Scanner state restored and state file cleaned up."
}

case "$ACTION" in
  start)
    save_scanner_state
    pause_all_workers
    disable_all_scanners
    echo ""
    echo "Maintenance mode ACTIVE. Unmanic is paused."
    echo "Run '$0 stop' when done."
    ;;
  stop)
    resume_all_workers
    restore_scanners
    echo ""
    echo "Maintenance mode ENDED. Unmanic is running normally."
    ;;
  *)
    echo "Unknown action: ${ACTION}" >&2
    echo "Usage: $0 <start|stop> [unmanic_url]" >&2
    exit 1
    ;;
esac
```

### Quick One-Liners

```bash
# Check if any workers are currently processing
curl -s http://localhost:8888/unmanic/api/v2/workers/status \
  | jq '[.workers_status[] | select(.idle == false)] | length'

# Get names of files currently being processed
curl -s http://localhost:8888/unmanic/api/v2/workers/status \
  | jq -r '.workers_status[] | select(.current_file != "") | .current_file'

# List libraries with scanning enabled
curl -s http://localhost:8888/unmanic/api/v2/settings/libraries \
  | jq -r '.libraries[] | select(.enable_scanner == true) | "\(.id): \(.name)"'
```

## API Quick Reference

### Worker Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/workers/status` | Get all workers' status |
| POST | `/api/v2/workers/worker/pause` | Pause a worker (requires `worker_id`) |
| POST | `/api/v2/workers/worker/pause/all` | Pause all workers |
| POST | `/api/v2/workers/worker/resume` | Resume a worker (requires `worker_id`) |
| POST | `/api/v2/workers/worker/resume/all` | Resume all workers |

### Library / Scanner Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/settings/libraries` | List all libraries |
| POST | `/api/v2/settings/library/read` | Read library config (requires `id`) |
| POST | `/api/v2/settings/library/write` | Write library config (requires `library_config` wrapper) |
| POST | `/api/v2/pending/rescan` | Trigger a full library rescan |
