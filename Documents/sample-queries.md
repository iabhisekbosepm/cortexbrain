# CortexBrain API — Sample Queries

Base URL: `http://localhost:8000/api/v1`
Auth: Bearer token (any non-empty string accepted in dev mode)

---

## 1. Health Check

```bash
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

---

## 2. Ingest a Document (Synchronous)

Upload a markdown file:

```bash
curl -s -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer dev-test-key" \
  -F "files=@prd-mfca-compliance-brain-mvp.md" \
  -F "dataset_name=compliance" \
  -F "source_type=document" \
  | python3 -m json.tool
```

Upload multiple files:

```bash
curl -s -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer dev-test-key" \
  -F "files=@docs/architecture.md" \
  -F "files=@docs/runbook.md" \
  -F "dataset_name=internal-docs" \
  | python3 -m json.tool
```

---

## 3. Batch Ingestion (Async via Celery)

Submit files for background processing:

```bash
curl -s -X POST http://localhost:8000/api/v1/ingest/batch \
  -H "Authorization: Bearer dev-test-key" \
  -F "files=@README.md" \
  -F "files=@CLAUDE.md" \
  -F "dataset_name=project-docs" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "status": "queued",
    "task_id": "abc123-...",
    "files": ["README.md", "CLAUDE.md"],
    "dataset": "project-docs"
}
```

Poll for status:

```bash
curl -s http://localhost:8000/api/v1/ingest/batch/{task_id} \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response (when complete):
```json
{
    "task_id": "abc123-...",
    "status": "SUCCESS",
    "result": {
        "status": "ingested",
        "dataset": "project-docs",
        "nodes_initialized": 15
    }
}
```

---

## 4. Query the Knowledge Base

Queries now use the full hybrid pipeline: Cognee search -> spreading activation -> M_meta enrichment -> confidence gating -> LLM generation.

### Basic query

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-test-key" \
  -d '{
    "query": "What is the activation engine and how does it work?",
    "user_id": "test-user"
  }' | python3 -m json.tool
```

Expected response (note activation-based sources and real confidence):
```json
{
    "answer": "The activation engine uses weighted BFS...",
    "confidence": "high",
    "confidence_score": 0.82,
    "sources": [
        {
            "node_id": "...",
            "source_name": "Activation Engine",
            "confidence": 0.85
        },
        {
            "node_id": "...",
            "source_name": "Spreading Activation",
            "confidence": 0.78
        }
    ],
    "tokens_used": {"input": 320, "output": 85},
    "session_id": "...",
    "fallback": false
}
```

### Architecture questions

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-test-key" \
  -d '{
    "query": "What are the main components of CortexBrain?",
    "user_id": "test-user"
  }' | python3 -m json.tool
```

### Session continuity (pass session_id to maintain activation context)

```bash
# First query seeds activation
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-test-key" \
  -d '{
    "query": "What is the metacognition layer?",
    "user_id": "test-user",
    "session_id": "my-session-001"
  }' | python3 -m json.tool

# Follow-up query benefits from existing activation scores
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-test-key" \
  -d '{
    "query": "How does confidence gating work?",
    "user_id": "test-user",
    "session_id": "my-session-001"
  }' | python3 -m json.tool
```

---

## 5. Submit a Correction

```bash
curl -s -X POST http://localhost:8000/api/v1/correct \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-test-key" \
  -d '{
    "node_id": "00000000-0000-0000-0000-000000000001",
    "corrected_value": "The activation engine uses weighted BFS with dampening factor 0.5",
    "user_id": "test-user",
    "reason": "Added specific dampening factor from implementation"
  }' | python3 -m json.tool
```

---

## 6. Get Node Version History

```bash
curl -s http://localhost:8000/api/v1/nodes/00000000-0000-0000-0000-000000000001/history \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

---

## 7. Node Detail (Graph + Metadata Combined)

Fetch a node's full detail — Neo4j properties, M_meta confidence/salience/access_count, and edge count:

```bash
curl -s http://localhost:8000/api/v1/nodes/{node_id} \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "node_id": "...",
    "name": "Activation Engine",
    "description": "Performs spreading activation over the knowledge graph",
    "confidence": 0.7,
    "salience": 0.45,
    "conflicted": false,
    "volatile": false,
    "access_count": 3,
    "correction_count": 0,
    "last_accessed": "2026-02-10T15:30:00+00:00",
    "edge_count": 5,
    "properties": {"version": 1}
}
```

---

## 8. Debug Endpoints (Inspect Internal State)

### View session activation scores (Redis)

After running a query with `session_id`, inspect what's in Redis:

```bash
# Run a query first with a known session_id
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-test-key" \
  -d '{
    "query": "What is the activation engine?",
    "user_id": "test-user",
    "session_id": "debug-session-001"
  }' | python3 -m json.tool

# Then inspect the activation scores
curl -s http://localhost:8000/api/v1/sessions/debug-session-001/activations \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "session_id": "debug-session-001",
    "active_node_count": 4,
    "activations": [
        {"node_id": "...", "score": 100.0},
        {"node_id": "...", "score": 50.0},
        {"node_id": "...", "score": 50.0},
        {"node_id": "...", "score": 25.0}
    ]
}
```

### Trigger salience recompute (on-demand)

Same logic as the hourly Celery beat task, but triggered manually:

```bash
curl -s -X POST http://localhost:8000/api/v1/debug/salience-recompute \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "status": "completed",
    "nodes_updated": 42
}
```

### System-wide debug stats

See entity count, active sessions, and top nodes across all subsystems:

```bash
curl -s http://localhost:8000/api/v1/debug/stats \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "total_entities": 42,
    "active_sessions": 2,
    "total_metadata_rows": 42,
    "top_accessed_nodes": [
        {"node_id": "...", "access_count": 15, "confidence": 0.85, "salience": 0.72}
    ],
    "top_salient_nodes": [
        {"node_id": "...", "salience": 0.91, "access_count": 10, "confidence": 0.9}
    ]
}
```

---

## 9. Full End-to-End Test Flow

Test all subsystems in sequence:

```bash
# Step 1: Health check
curl -s localhost:8000/api/v1/health | python3 -m json.tool

# Step 2: Ingest a document
curl -s -X POST localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer dev" \
  -F "files=@prd-mfca-compliance-brain-mvp.md" \
  -F "dataset_name=test" | python3 -m json.tool

# Step 3: Check debug stats (should show entities now)
curl -s localhost:8000/api/v1/debug/stats \
  -H "Authorization: Bearer dev" | python3 -m json.tool

# Step 4: Query with a session_id
curl -s -X POST localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev" \
  -d '{"query":"What is CortexBrain?","user_id":"me","session_id":"e2e-test"}' \
  | python3 -m json.tool

# Step 5: Verify activation scores in Redis
curl -s localhost:8000/api/v1/sessions/e2e-test/activations \
  -H "Authorization: Bearer dev" | python3 -m json.tool

# Step 6: Pick a node_id from the sources and inspect it
curl -s localhost:8000/api/v1/nodes/{node_id} \
  -H "Authorization: Bearer dev" | python3 -m json.tool

# Step 7: Query again — access_count should increment
curl -s -X POST localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev" \
  -d '{"query":"What is CortexBrain?","user_id":"me","session_id":"e2e-test"}' \
  | python3 -m json.tool

# Step 8: Check node again — access_count should be higher
curl -s localhost:8000/api/v1/nodes/{node_id} \
  -H "Authorization: Bearer dev" | python3 -m json.tool

# Step 9: Trigger salience recompute
curl -s -X POST localhost:8000/api/v1/debug/salience-recompute \
  -H "Authorization: Bearer dev" | python3 -m json.tool
```

---

## 10. Agentic Query (SSE Streaming)

The agent endpoint uses Server-Sent Events — the LLM autonomously decides which tools to call, and each step streams in real-time.

### Basic agentic query

```bash
curl -N -X POST http://localhost:8000/api/v1/query/agent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-test-key" \
  -d '{
    "query": "What is spreading activation and how does it work?",
    "user_id": "test-user"
  }'
```

The `-N` flag disables buffering so you see SSE events as they arrive:
```
event: step
data: {"type":"tool_call","name":"search_knowledge","content":"Searching knowledge base for \"spreading activation\""}

event: step
data: {"type":"tool_result","name":"search_knowledge","content":"Found 5 nodes: Spreading Activation, ..."}

event: step
data: {"type":"tool_call","name":"activate_and_gather","content":"Running spreading activation for 3 entities"}

event: step
data: {"type":"tool_result","name":"activate_and_gather","content":"Activated 12 nodes, max score 100.0"}

event: answer
data: {"answer":"Spreading activation is...","confidence":"high","confidence_score":0.87,"sources":[...],"session_id":"...","fallback":false}

event: done
data: {}
```

### Multi-turn conversation

Pass `conversation_history` to enable follow-up questions:

```bash
curl -N -X POST http://localhost:8000/api/v1/query/agent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-test-key" \
  -d '{
    "query": "Tell me more about the dampening factor",
    "user_id": "test-user",
    "session_id": "my-session-001",
    "conversation_history": [
      {"role": "user", "content": "What is spreading activation?"},
      {"role": "assistant", "content": "Spreading activation is a graph traversal algorithm..."}
    ]
  }'
```

---

## 11. Meta Memory Timeline

View audit log events (corrections, ingestions, decay cycles, consolidations) as a timeline.

### Get all events (default: latest 50)

```bash
curl -s http://localhost:8000/api/v1/timeline \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "summary": {
        "total": 127,
        "corrections": 8,
        "ingestions": 45,
        "decays": 60,
        "consolidations": 2,
        "other": 12
    },
    "events": [
        {
            "id": 1,
            "node_id": "...",
            "action": "correct",
            "changed_by": "test-user",
            "previous_value": "old description...",
            "new_value": "corrected description...",
            "reason": "Fixed inaccuracy",
            "version": 2,
            "timestamp": "2026-02-14T10:30:00+00:00"
        }
    ],
    "total": 127,
    "limit": 50,
    "offset": 0
}
```

### Filter by action type

```bash
curl -s "http://localhost:8000/api/v1/timeline?action=correct" \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

### Filter by date range

```bash
curl -s "http://localhost:8000/api/v1/timeline?start=2026-02-13T00:00:00&end=2026-02-14T23:59:59" \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

### Pagination

```bash
curl -s "http://localhost:8000/api/v1/timeline?limit=10&offset=20" \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

---

## 12. Knowledge Graph Visualization

### Get graph overview (top 200 salient nodes + edges)

```bash
curl -s http://localhost:8000/api/v1/graph/overview?limit=200 \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "nodes": [
        {
            "id": "...",
            "name": "Activation Engine",
            "description": "Performs spreading activation...",
            "confidence": 0.85,
            "salience": 0.72,
            "edge_count": 8,
            "access_count": 12
        }
    ],
    "edges": [
        {
            "source": "...",
            "target": "...",
            "rel_type": "RELATES_TO",
            "weight": 1.0
        }
    ]
}
```

### Get subgraph around a specific node

BFS expansion from a center node (depth 1 or 2):

```bash
curl -s "http://localhost:8000/api/v1/graph/subgraph?center={node_id}&depth=2" \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "center": "...",
    "depth": 2,
    "nodes": [...],
    "edges": [...]
}
```

---

## 13. Confidence Dashboard

### Get dashboard statistics

Returns total nodes, average confidence, confidence distribution buckets, and low-confidence nodes:

```bash
curl -s http://localhost:8000/api/v1/dashboard/stats \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "total_nodes": 142,
    "avg_confidence": 0.68,
    "distribution": [
        {"range": "0.0-0.3", "count": 12},
        {"range": "0.3-0.5", "count": 25},
        {"range": "0.5-0.8", "count": 65},
        {"range": "0.8-1.0", "count": 40}
    ],
    "low_confidence_nodes": [
        {
            "node_id": "...",
            "name": "Some Entity",
            "confidence": 0.35,
            "salience": 0.22,
            "access_count": 1,
            "last_accessed": "2026-02-14T10:00:00+00:00"
        }
    ]
}
```

---

## 14. Auto-Learning Validation Queue

### Get nodes pending review

Returns auto-learned nodes with confidence 0.5–0.7:

```bash
curl -s http://localhost:8000/api/v1/review/queue \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "total": 8,
    "nodes": [
        {
            "node_id": "...",
            "name": "Auto-learned Entity",
            "description": "Knowledge extracted from LLM fallback...",
            "confidence": 0.6,
            "salience": 0.45,
            "access_count": 2,
            "created_at": "2026-02-14T12:00:00+00:00",
            "last_accessed": "2026-02-14T15:30:00+00:00"
        }
    ]
}
```

### Approve a node (promote to validated)

Sets confidence to 0.8 and records audit log:

```bash
curl -s -X POST http://localhost:8000/api/v1/review/approve/{node_id} \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "status": "approved",
    "node_id": "...",
    "new_confidence": 0.8
}
```

### Reject a node (archive)

Sets confidence to 0.0, marks volatile, archives in Neo4j:

```bash
curl -s -X POST http://localhost:8000/api/v1/review/reject/{node_id} \
  -H "Authorization: Bearer dev-test-key" \
  | python3 -m json.tool
```

Expected response:
```json
{
    "status": "rejected",
    "node_id": "...",
    "new_confidence": 0.0
}
```

---

## Quick One-Liners

```bash
# Health check
curl -s localhost:8000/api/v1/health | python3 -m json.tool

# Quick query
curl -s -X POST localhost:8000/api/v1/query -H "Content-Type: application/json" -H "Authorization: Bearer dev" -d '{"query":"What is CortexBrain?","user_id":"me"}' | python3 -m json.tool

# Sync ingest
curl -s -X POST localhost:8000/api/v1/ingest -H "Authorization: Bearer dev" -F "files=@README.md" | python3 -m json.tool

# Batch ingest
curl -s -X POST localhost:8000/api/v1/ingest/batch -H "Authorization: Bearer dev" -F "files=@README.md" | python3 -m json.tool

# Session activations
curl -s localhost:8000/api/v1/sessions/my-session/activations -H "Authorization: Bearer dev" | python3 -m json.tool

# Debug stats
curl -s localhost:8000/api/v1/debug/stats -H "Authorization: Bearer dev" | python3 -m json.tool

# Salience recompute
curl -s -X POST localhost:8000/api/v1/debug/salience-recompute -H "Authorization: Bearer dev" | python3 -m json.tool

# Agentic query (SSE streaming)
curl -N -X POST localhost:8000/api/v1/query/agent -H "Content-Type: application/json" -H "Authorization: Bearer dev" -d '{"query":"What is CortexBrain?","user_id":"me"}'

# Timeline (all events)
curl -s localhost:8000/api/v1/timeline -H "Authorization: Bearer dev" | python3 -m json.tool

# Timeline (corrections only)
curl -s "localhost:8000/api/v1/timeline?action=correct" -H "Authorization: Bearer dev" | python3 -m json.tool

# Graph overview (top 200 nodes)
curl -s localhost:8000/api/v1/graph/overview?limit=200 -H "Authorization: Bearer dev" | python3 -m json.tool

# Graph subgraph (BFS from node)
curl -s "localhost:8000/api/v1/graph/subgraph?center={node_id}&depth=2" -H "Authorization: Bearer dev" | python3 -m json.tool

# Dashboard stats
curl -s localhost:8000/api/v1/dashboard/stats -H "Authorization: Bearer dev" | python3 -m json.tool

# Review queue (auto-learned nodes)
curl -s localhost:8000/api/v1/review/queue -H "Authorization: Bearer dev" | python3 -m json.tool

# Approve a node
curl -s -X POST localhost:8000/api/v1/review/approve/{node_id} -H "Authorization: Bearer dev" | python3 -m json.tool

# Reject a node
curl -s -X POST localhost:8000/api/v1/review/reject/{node_id} -H "Authorization: Bearer dev" | python3 -m json.tool
```
