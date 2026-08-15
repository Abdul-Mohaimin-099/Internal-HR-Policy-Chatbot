# Internal HR Policy Chatbot — End-to-End Workflow

This document explains how a request moves through the system today: ingestion,
chat (subagents + tools), and human-in-the-loop escalation.

---

## 1. Big picture

```mermaid
flowchart LR
  subgraph clients [Clients]
    Emp[Employee client]
    HR[HR tools / curl]
  end

  subgraph api [FastAPI /api/v1]
    Chat[POST /chat]
    Docs[Documents APIs]
    Esc[Escalations APIs]
    Conv[Conversations API]
  end

  subgraph graph [LangGraph policy_chat]
    Triage[triage]
    Answer[policy_answer subagent]
    Escalate[escalate subagent]
    Persist[persist]
  end

  subgraph data [Data plane]
    Gemini[Gemini]
    Qdrant[Qdrant]
    PG[(PostgreSQL)]
  end

  Emp --> Chat
  HR --> Esc
  HR --> Conv
  HR --> Docs
  Emp --> Conv

  Chat --> Triage
  Triage -->|safe| Answer
  Triage -->|sensitive| Escalate
  Answer --> Persist
  Escalate --> Persist

  Answer -->|rag_search| Qdrant
  Answer --> Gemini
  Triage --> Gemini
  Escalate -->|create_escalation_ticket| PG
  Persist --> PG
  Esc --> PG
  Conv --> PG
  Docs --> Qdrant
  Docs --> PG
```

**Design rules**

- Chat is one synchronous turn: `POST /chat` always returns a reply (grounded answer or safe refusal).
- Routing is **deterministic** (structured triage + graph edges), not a free-roaming supervisor.
- RAG and ticket creation are **tools** used by subagents.
- HR follow-up is **ticket-queue HITL** after the graph ends — not a LangGraph `interrupt`.

---

## 2. Document ingestion (before chat can cite policies)

Used by `POST /api/v1/documents/upload`, reindex, and `scripts/seed_policies.py`.

```mermaid
flowchart TD
  File[PDF / Markdown / text] --> Parse[Docling parse]
  Parse --> Chunk[RecursiveCharacterTextSplitter]
  Chunk --> Embed[gemini-embedding-2]
  Embed --> QdrantUpsert[Upsert vectors + citation payload to Qdrant]
  Chunk --> PGDocs[Postgres: policy_documents + document_chunks]
  QdrantUpsert --> Ready[Ready for rag_search]
  PGDocs --> Ready
```

Qdrant payload typically includes `text`, `document_id`, `filename`, `section`, `page_number`, `chunk_index` so answers can cite sources without a second lookup.

---

## 3. Chat turn — LangGraph topology

Entry: `POST /api/v1/chat` → compiles / invokes `policy_chat_graph` with `thread_id`.

```mermaid
flowchart TD
  START([START]) --> triage[triage_node]
  triage --> route{route_after_triage}

  route -->|"sensitivity != high AND needs_human = false"| policy[policy_answer_node]
  route -->|"sensitivity = high OR needs_human = true"| esc[escalate_node]

  policy --> persist[persist_node]
  esc --> persist
  persist --> END([END])
```

| Node | What happens |
|---|---|
| **triage** | Gemini structured output → `TriageResult` (category, sensitivity, `needs_human`, confidence) |
| **policy_answer** | Subagent (`create_agent`) must call **`rag_search`**, then draft a grounded reply |
| **escalate** | Subagent must call **`create_escalation_ticket`**, then return fixed safe refusal |
| **persist** | Write user + assistant messages + audit row to Postgres |

State fields returned to the API include: `reply`, `sources`, `escalated`, `escalation_id`, `triage`, `conversation_id`, `thread_id`.

The HTTP body exposes the answer in **two forms**:
- `text` / `reply` — simple string for UI display
- `json` — structured object with the same reply plus sources, triage, escalation flags, and ids

---

## 4. Safe path — RAG as a tool

When triage says the question is safe:

```mermaid
sequenceDiagram
  participant API as FastAPI
  participant G as LangGraph
  participant Agent as policy_answer subagent
  participant Tool as rag_search tool
  participant Emb as gemini-embedding-2
  participant Q as Qdrant
  participant LLM as Gemini response model
  participant DB as PostgreSQL

  API->>G: ainvoke(user_input, thread_id)
  G->>G: triage → policy_answer
  G->>Agent: run subagent
  Agent->>Tool: rag_search(query)
  Tool->>Emb: embed query
  Emb-->>Tool: vector
  Tool->>Q: query_points top-k + score threshold
  Q-->>Tool: chunks + payload
  Tool-->>Agent: JSON context / chunks / sources
  Agent->>LLM: answer only from tool context
  LLM-->>Agent: grounded reply
  Agent-->>G: reply + sources
  G->>DB: persist messages + audit respond
  G-->>API: ChatResponse escalated=false
```

**Fallback:** if the model skips `rag_search`, `policy_answer_node` invokes the tool directly so retrieval still happens.

---

## 5. Sensitive path — escalate then HR HITL

### 5.1 Inside the chat turn

```mermaid
sequenceDiagram
  participant Emp as Employee
  participant API as FastAPI
  participant G as LangGraph
  participant Agent as escalate subagent
  participant Tool as create_escalation_ticket
  participant DB as PostgreSQL

  Emp->>API: POST /chat sensitive question
  API->>G: ainvoke
  G->>G: triage → escalate
  G->>Agent: run subagent
  Agent->>Tool: create_escalation_ticket(...)
  Tool->>DB: insert escalations status=open
  Tool->>DB: audit escalate
  Tool-->>Agent: escalation_id, conversation_id
  Agent-->>G: fixed safe refusal text
  G->>DB: persist user + assistant messages + audit
  G-->>API: ChatResponse escalated=true
  API-->>Emp: safe refusal + escalation_id
```

No RAG advice is generated on this path.

### 5.2 After the ticket — human-in-the-loop

HR acts **after** the graph has already finished:

```mermaid
flowchart TD
  Open[Ticket status=open] --> List[GET /api/v1/escalations]
  List --> Detail[GET /api/v1/escalations/id]
  Detail --> Review[HR reviews messages + reason + category]
  Review --> Respond[POST .../respond]
  Respond --> Msg[Write messages role=hr]
  Msg --> StillOpen[Ticket still open]
  StillOpen --> More{More follow-up?}
  More -->|yes| Respond
  More -->|no| Resolve[POST .../resolve]
  Resolve --> OptionalMsg[Optional hr_message → role=hr]
  OptionalMsg --> Closed[status=resolved]
  Closed --> EmpSees[Employee sees HR text via GET /conversations/user_id]
```

| HR action | Endpoint | Effect |
|---|---|---|
| Queue | `GET /escalations?status=open` | List open tickets |
| Review | `GET /escalations/{id}` | Ticket + conversation messages + `thread_id` / `employee_id` |
| Reply | `POST /escalations/{id}/respond` | Append `role=hr` message; keep `open` |
| Close | `POST /escalations/{id}/resolve` | Mark `resolved`; optional final `hr_message` |

Audit events: `hr_respond`, `hr_resolve`.

---

## 6. Full lifecycle (employee + HR)

```mermaid
sequenceDiagram
  participant Emp as Employee
  participant API as FastAPI
  participant Graph as LangGraph
  participant Q as Qdrant
  participant DB as PostgreSQL
  participant HR as HR staff

  Note over Emp,HR: A — Routine policy question
  Emp->>API: POST /chat safe question
  API->>Graph: triage → policy_answer
  Graph->>Q: rag_search
  Q-->>Graph: policy chunks
  Graph->>DB: persist answer + sources
  API-->>Emp: grounded reply

  Note over Emp,HR: B — Sensitive question
  Emp->>API: POST /chat sensitive question
  API->>Graph: triage → escalate
  Graph->>DB: open escalation ticket
  Graph->>DB: persist safe refusal
  API-->>Emp: escalated=true + safe refusal

  Note over Emp,HR: C — Human in the loop
  HR->>API: GET /escalations/{id}
  API->>DB: load ticket + messages
  API-->>HR: context for review
  HR->>API: POST /escalations/{id}/respond
  API->>DB: insert role=hr message
  HR->>API: POST /escalations/{id}/resolve
  API->>DB: status=resolved + optional hr_message
  Emp->>API: GET /conversations/{user_id}
  API-->>Emp: history including HR replies
```

---

## 7. Memory and persistence

```mermaid
flowchart LR
  subgraph shortTerm [Short-term memory]
    CP[LangGraph checkpointer keyed by thread_id]
  end

  subgraph longTerm [Long-term / audit]
    Msg[Postgres messages]
    Esc[Postgres escalations]
    Aud[Postgres audit_logs]
  end

  ChatTurn[Each POST /chat] --> CP
  ChatTurn --> Msg
  ChatTurn --> Aud
  EscalatePath[Escalate path] --> Esc
  HRAction[HR respond / resolve] --> Msg
  HRAction --> Esc
  HRAction --> Aud
```

- Reuse the same `thread_id` for multi-turn chatbot memory.
- Clean Human / AI / HR text lives in `messages` (independent of checkpoint blobs — ADR-001).

---

## 8. Auth and surfaces

| Surface | Auth | Purpose |
|---|---|---|
| `POST /api/v1/chat` | `x-api-key` | Employee question |
| `GET/POST /api/v1/documents/*` | `x-api-key` | Policy ingest / list / reindex |
| `GET /api/v1/conversations/{user_id}` | `x-api-key` | History (includes `role=hr`) |
| `GET/POST /api/v1/escalations/*` | `x-api-key` | HR queue + HITL actions |
| `GET /health` | public | Liveness (alias of `/live`) |
| `GET /live` | public | Liveness — process up |
| `GET /ready` | public | Readiness — Postgres + Qdrant + LLM config |

There is no separate HR UI in-repo; HR tools call the escalations API (or curl).

---

## 9. Code map (where to look)

| Area | Path |
|---|---|
| Chat endpoint | `src/hr_chatbot/api/v1/endpoints/policy_chat.py` |
| Graph wiring | `src/hr_chatbot/llm/workflows/policy_chat/graph.py` |
| Nodes | `src/hr_chatbot/llm/workflows/policy_chat/nodes.py` |
| Subagents | `src/hr_chatbot/llm/workflows/policy_chat/agents.py` |
| Tools (`rag_search`, ticket) | `src/hr_chatbot/llm/workflows/policy_chat/tools.py` |
| Escalation HITL service | `src/hr_chatbot/services/escalation_service.py` |
| Escalation APIs | `src/hr_chatbot/api/v1/endpoints/escalations.py` |
| Retriever | `src/hr_chatbot/rag/retriever.py` |
| Ingestion | `src/hr_chatbot/rag/ingestion.py` |

---

## 10. One-line summary

**Ingest policies → chat triages → safe questions use `rag_search` for grounded answers → sensitive questions open a ticket and refuse automation → HR reviews/replies/resolves via escalations APIs → employees see HR messages in conversation history.**
