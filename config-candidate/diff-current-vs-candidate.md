## Redacted Current-vs-Candidate Diff

### Current config (redacted — secrets omitted)
```json
{
  "agents": {
    "defaults": {
      "compaction": {
        "reserveTokensFloor": 50000
      },
      "model": {
        "fallbacks": [],
        "primary": "openrouter/z-ai/glm-5.3-flash"
      },
      "models": {
        "deepseek/deepseek-chat": {
          "alias": "DeepSeek"
        },
        "deepseek/deepseek-v4-flash": {
          "alias": "DeepSeek V4 Flash"
        },
        "deepseek/deepseek-v4-pro": {
          "alias": "DeepSeek V4 Pro"
        },
        "kimi/kimi-k3": {
          "alias": "Kimi K3"
        },
        "openrouter/deepseek/deepseek-chat": {
          "alias": "DeepSeek V3"
        },
        "openrouter/inclusionai/ling-3.0-flash": {
          "alias": "Ling 3.0 Flash"
        },
        "openrouter/nex-agi/nex-n2.5-pro:free": {
          "alias": "Nex Pro"
        },
        "openrouter/nvidia/nemotron-3.5-lightning:free": {
          "alias": "Lightning"
        },
        "openrouter/z-ai/glm-5.3-flash": {
          "alias": "GLM 5.3 Flash"
        }
      },
      "sandbox": {
        "sessionToolsVisibility": "all"
      },
      "subagents": {
        "delegationMode": "prefer",
        "maxChildrenPerAgent": 3,
        "maxConcurrent": 3,
        "maxSpawnDepth": 1
      },
      "timeoutSeconds": 900,
      "workspace": "/Users/habeebodubunmi/.openclaw/workspace"
    },
    "list": [
      {
        "agentDir": "/Users/habeebodubunmi/.openclaw/agents/shiftlyx/agent",
        "id": "shiftlyx",
        "memorySearch": {
          "enabled": true,
          "fallback": "none",
          "local": {
            "contextSize": 2048,
            "modelPath": "/Users/habeebodubunmi/.node-llama-cpp/models/hf_ggml-org_embeddinggemma-300m-qat-Q8_0.gguf"
          },
          "provider": "local",
          "sources": [
            "memory"
          ]
        },
        "model": {
          "fallbacks": [],
          "primary": "openrouter/z-ai/glm-5.3-flash"
        },
        "name": "shiftlyx",
        "skills": [
          "self-improving-agent"
        ],
        "workspace": "/Users/habeebodubunmi/.openclaw/workspace-shiftlyx"
      },
      {
        "default": true,
        "id": "tola",
        "memorySearch": {
          "enabled": true,
          "fallback": "none",
          "local": {
            "contextSize": 2048,
            "modelPath": "/Users/habeebodubunmi/.node-llama-cpp/models/hf_ggml-org_embeddinggemma-300m-qat-Q8_0.gguf"
          },
          "provider": "local",
          "sources": [
            "memory"
          ]
        },
        "model": {
          "fallbacks": [
            "openrouter/inclusionai/ling-3.0-flash"
          ],
          "primary": "openrouter/z-ai/glm-5.3-flash"
        },
        "name": "Tola",
        "skills": [
          "notion",
          "github",
          "supabase",
          "self-improving-agent"
        ],
        "subagents": {
          "allowAgents": [
            "rhythm",
            "growth",
            "scholar"
          ],
          "requireAgentId": true
        },
        "workspace": "/Users/habeebodubunmi/.openclaw/workspace"
      },
      {
        "agentDir": "/Users/habeebodubunmi/.openclaw/agents/rhythm/agent",
        "description": "Batch 10 live: shift & recovery planner. Planner, not project manager. Rhythm Blackboard tools + My Rhythm typed tools only. No Growth/IntenSIQ tools, no delegation.",
        "id": "rhythm",
        "memorySearch": {
          "enabled": true,
          "fallback": "none",
          "local": {
            "contextSize": 2048,
            "modelPath": "/Users/habeebodubunmi/.node-llama-cpp/models/hf_ggml-org_embeddinggemma-300m-qat-Q8_0.gguf"
          },
          "provider": "local",
          "sources": [
            "memory"
          ]
        },
        "model": {
          "fallbacks": [
            "openrouter/inclusionai/ling-3.0-flash"
          ],
          "primary": "openrouter/qwen/qwen3.8-27b:free"
        },
        "name": "Rhythm",
        "skills": [],
     
```

### Candidate config (redacted — secrets as placeholders)
```json
{
  "agents": {
    "defaults": {
      "sandbox": {
        "sessionToolsVisibility": "own"
      },
      "subagents": {
        "maxChildrenPerAgent": 3,
        "maxConcurrent": 3,
        "maxSpawnDepth": 1
      },
      "timeoutSeconds": 900
    },
    "list": [
      {
        "_agent": "tola",
        "description": "Chief of Staff \u2014 coordinator, git ops, approval gates. Only general delegator in V1.",
        "id": "tola",
        "model": {
          "primary": "openrouter/z-ai/glm-5.3-flash"
        },
        "name": "Tola",
        "session": {
          "visibility": "all"
        },
        "skills": {
          "allow": [
            "notion",
            "github",
            "supabase",
            "self-improving-agent"
          ]
        },
        "subagents": {
          "allowAgents": [
            "rhythm",
            "growth",
            "scholar"
          ],
          "maxChildrenPerAgent": 3,
          "maxConcurrent": 3,
          "maxSpawnDepth": 1,
          "requireAgentId": true
        },
        "tools": {
          "allow": [
            "listProjects",
            "getProject",
            "listGoals",
            "getGoal",
            "createTask",
            "listTasks",
            "getTask",
            "assignTask",
            "updateTaskStatus",
            "recordDecision",
            "recordEvent",
            "requestApproval",
            "getApproval",
            "getTaskRun",
            "webSearch"
          ]
        },
        "workspace": "/Users/habeebodubunmi/.openclaw/workspace"
      },
      {
        "_agent": "rhythm",
        "description": "Shift & recovery planner. Planner only, no project management. Rhythm Blackboard + My Rhythm typed tools only.",
        "id": "rhythm",
        "model": {
          "fallbacks": [
            "openrouter/inclusionai/ling-3.0-flash"
          ],
          "primary": "openrouter/qwen/qwen3.8-27b:free"
        },
        "name": "Rhythm",
        "session": {
          "visibility": "own"
        },
        "skills": {
          "allow": [
            "rhythm"
          ]
        },
        "subagents": {
          "maxChildrenPerAgent": 3,
          "maxConcurrent": 3,
          "maxSpawnDepth": 1
        },
        "tools": {
          "allow": [
            "listProjects",
            "getProject",
            "listGoals",
            "getGoal",
            "createTask",
            "listTasks",
            "getTask",
            "assignTask",
            "updateTaskStatus",
            "recordDecision",
            "recordEvent",
            "requestApproval",
            "getApproval",
            "getTaskRun"
          ]
        },
        "workspace": "/Users/habeebodubunmi/.openclaw/workspace-rhythm"
      },
      {
        "_agent": "growth",
        "description": "Growth & product-intelligence specialist. Read-only Metricool; no write tools.",
        "id": "growth",
        "model": {
          "fallbacks": [
            "openrouter/inclusionai/ling-3.0-flash",
            "openrouter/nvidia/nemotron-3.5-lightning:free"
          ],
          "primary": "openrouter/qwen/qwen3.8-27b:free"
        },
        "name": "Growth",
        "session": {
          "visibility": "own"
        },
        "skills": {
          "allow": [
            "product-intelligence",
            "marketing-psychology"
          ]
        },
        "subagents": {
          "maxChildrenPerAgent": 3,
          "maxConcurrent": 3,
          "maxSpawnDepth": 1
        },
        "tools": {
          "allow": [
            "listProjects",
            "getProject",
            "listGoals",
            "getGoal",
            "createTask",
            "listTasks",
            "getTask",
            "assignTask",
            "updateTaskStatus",
            "recordDecision",
            "recordEvent",
            "requestApproval",
            "getApproval",
            "getTaskRun"
          ]
        },
        "workspace": "/Users/habe
```

### Key Changes
1. **session.visibility**: `all` -> `own` (per-agent session isolation)
2. **agents.defaults.sandbox.sessionToolsVisibility**: `all` -> `own`
3. **agents.defaults.subagents**: added maxSpawnDepth=1, maxChildrenPerAgent=3, maxConcurrent=3
4. **Per-agent tool allowlists**: each specialist gets only Blackboard tools + webSearch (Tola only); no generic exec/SQL
5. **Per-agent skill allowlists**: restricted to agent-specific skills
6. **Per-agent session.visibility**: `own` for rhythm/growth/scholar; `all` for tola only
7. **workshop.autonomousMode**: `propose` (new key)
8. **workshop.approvalPolicy**: `pending` (new key)
9. **bindings**: preserved exactly from current (Telegram/Discord channels, guilds, peer IDs)
10. **channels.telegram/discord**: secret values replaced with ${secrets.*} placeholders
11. **plugins.entries.openclaw-tools**: added with SecretRef placeholders for supabaseUrl/supabaseKey
12. **agents.defaults.session.visibility**: `all` -> `own`
