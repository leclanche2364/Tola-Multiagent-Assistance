# Blackboard wiring — all four agents

Every agent writes to the shared Supabase Blackboard through
`packages/blackboard_client/client.py`. Supabase is the source of
truth; each agent keeps a local SQLite outbox only as backup.

Rules (standing, 2026-09-29):

- The client NEVER reads env files. The caller loads credentials and
  passes `base_url` + `api_key` in.
- One outbox file per agent. Never share outbox paths.
- Every row carries a deterministic `idempotency_key` (uuid5 of a
  stable namespace + natural key) so flush replays are safe.
- Read from the shared board, never from another agent's local files.
- Raw Postgres DB passwords are never used; REST key or linked CLI only.

## Integration snippets

All snippets assume:

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "packages"))
from blackboard_client import BlackboardClient
```

### Tola (portfolio / coordinator)

```python
client = BlackboardClient(base_url, api_key, outbox_path="~/.openclaw/workspace/four-agent-repo/data/tola_outbox.sqlite3")
client.write("decisions", {"idempotency_key": key, "agent_id": "tola", ...})
```

### Growth (product intelligence)

Growth keeps its existing local product-intelligence SQLite writer
(`~/.openclaw/workspace-growth/product-intelligence/data/blackboard.sqlite3`)
untouched. Publishing to the shared board is additive:

```python
client = BlackboardClient(base_url, api_key, outbox_path="~/.openclaw/workspace-growth/product-intelligence/data/growth_outbox.sqlite3")
client.write("metrics", {"idempotency_key": key, "source": "growth", ...})
```

### Rhythm (capacity & schedule)

```python
client = BlackboardClient(base_url, api_key, outbox_path="~/.openclaw/workspace-rhythm/rhythm/blackboard_outbox.sqlite3")
client.write("schedule_constraints", {"idempotency_key": key, "agent_id": "rhythm", ...})
```

### Scholar (learning intelligence)

```python
client = BlackboardClient(base_url, api_key, outbox_path="~/.openclaw/workspace/four-agent-repo/data/scholar_outbox.sqlite3")
client.write("skill_registry", {"idempotency_key": key, "agent_id": "scholar", ...})
```

## Credentials loading (caller side, per agent)

Each agent reads only its own env file (no bundling) and passes the
values in. Example:

```python
def load_env(path):
    env = {}
    for line in open(path):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env("<agent-own-env-file>")
client = BlackboardClient(env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"], outbox_path=...)
```

## Test command

```
cd ~/.openclaw/workspace/four-agent-repo
python3 -m unittest discover -s packages/blackboard_client/tests -v
```