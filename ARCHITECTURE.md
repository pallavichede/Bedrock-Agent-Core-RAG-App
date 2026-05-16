# Bedrock Agent Core RAG Application - Architecture

## System Overview

This is an intelligent FAQ customer service agent powered by AWS Bedrock that combines retrieval-augmented generation (RAG), agentic reasoning, and persistent memory to provide context-aware customer support responses.

**Core Purpose**: Deliver accurate, contextual answers to customer queries by retrieving relevant FAQ information and using an LLM agent to reformulate and synthesize responses.

---

## Component Architecture

### 1. **Vector Store & Embeddings Layer**

```
┌─────────────────────────────────────┐
│   FAISS Vector Store                │
│   (Pre-built Index)                 │
│   "faiss_index/"                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Amazon Titan Embeddings v2         │
│  (amazon.titan-embed-text-v2:0)     │
│  eu-north-1                         │
└─────────────────────────────────────┘
```

**Responsibility**: Convert natural language queries and FAQ documents into dense vector embeddings for semantic similarity search.

- **Embeddings Model**: `amazon.titan-embed-text-v2:0`
- **Vector DB**: FAISS (local, pre-built index)
- **Region**: eu-north-1
- **Load Strategy**: Singleton at module initialization (prevents runtime rebuilds)

---

### 2. **Agent & Reasoning Layer**

```
┌──────────────────────────────────────────────┐
│         LangGraph ReAct Agent                │
│  (Reasoning + Acting loop)                  │
├──────────────────────────────────────────────┤
│ Model: ChatBedrock (Nova Lite v1)            │
│ Tools: [search_faq, search_detailed_faq,     │
│         reformulate_query]                   │
│ Checkpointer: AgentCoreMemorySaver           │
└──────────────────────────────────────────────┘
```

**Responsibility**: Orchestrate multi-turn reasoning, tool selection, and response generation.

- **Framework**: LangGraph (orchestration)
- **LLM**: `eu.amazon.nova-lite-v1:0` (fast, low-latency inference)
- **Pattern**: ReAct (Reasoning + Acting)
- **Checkpointing**: Persists agent state for recovery and replay

**System Prompt**:
```
You are a helpful FAQ assistant with access to a knowledge base.
Use search_faq first, then search_detailed_faq or reformulate_query if needed.
Always base your answer on retrieved information. If nothing is found, say so clearly.
```

---

### 3. **Tool Layer**

Three specialized tools enable the agent to retrieve and refine information:

#### **search_faq(query: str) → str**
- Default retrieval tool
- Returns top 3 most similar FAQ entries
- Fast, focused retrieval for straightforward queries
- Output: Concatenated FAQ entries with formatting

#### **search_detailed_faq(query: str, num_results: int = 5) → str**
- Extended retrieval for complex queries
- Returns configurable number of results (default 5)
- Allows agent to gather broader context when initial results are ambiguous

#### **reformulate_query(original_query: str, focus_aspect: str) → str**
- Semantic query refinement
- Converts vague queries into aspect-focused searches
- Enables multi-perspective information gathering
- Example: reformulating "payment issues" → "billing related to payment issues"

---

### 4. **Memory Management Layer**

```
┌────────────────────────────────────────────────┐
│      Memory Middleware (Custom)                │
├────────────────────────────────────────────────┤
│                                                │
│  Pre-Model Hook                Post-Model Hook│
│  ┌──────────────────┐      ┌──────────────┐  │
│  │ Save Human Msgs  │      │ Save AI Msgs │  │
│  │ Retrieve Memories│      │              │  │
│  └──────────────────┘      └──────────────┘  │
└────────────┬──────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────┐
│    AgentCoreMemoryStore                        │
│    (AWS Bedrock AgentCore backend)             │
│    memory_id: customerservice_agentmemory-*   │
└────────────────────────────────────────────────┘
```

**Responsibility**: Persist conversation history and enable long-term memory retrieval across sessions.

- **Storage Backend**: AWS Bedrock AgentCore Memory Service
- **Namespace**: `(actor_id, thread_id)` for per-user, per-conversation isolation
- **Lifecycle**:
  - **Pre-Model**: Retrieve relevant memories based on human message
  - **Post-Model**: Save AI response for future reference
- **Search Namespace**: `("preferences", actor_id)` for preference-based memory queries
- **Error Handling**: Graceful degradation (logs errors, continues execution)

---

## Data Flow

### Request → Response Cycle

```
1. CLIENT REQUEST
   {
     "prompt": "How do I reset my password?",
     "actor_id": "user-123",
     "thread_id": "session-456"
   }
        │
        ▼
2. MEMORY RETRIEVAL (Pre-Model Hook)
   - Load user preferences
   - Search (preferences, actor_id) for relevant context
   - Inject memory into state
        │
        ▼
3. AGENT INVOCATION
   - Format state with [HumanMessage(prompt)]
   - LLM selects tool: search_faq()
   - Retrieve 3 FAQ entries from FAISS
        │
        ▼
4. AGENT REASONING
   - LLM evaluates retrieved info
   - If incomplete: trigger search_detailed_faq()
   - If ambiguous: trigger reformulate_query()
   - Generate synthesized response
        │
        ▼
5. MEMORY PERSISTENCE (Post-Model Hook)
   - Save AI response to memory store
   - Persist under (actor_id, thread_id) namespace
        │
        ▼
6. RESPONSE
   {
     "result": "To reset your password, navigate to Settings > Security > Change Password..."
   }
```

### Namespace Hierarchy

```
AgentCoreMemoryStore (memory_id)
├── (actor_id="user-123", thread_id="session-456")
│   ├── msg_uuid_1: {message: "How do I reset my password?"}
│   ├── msg_uuid_2: {message: "Password reset is available at..."}
│   └── msg_uuid_3: {message: "Can I reset via email?"}
│
├── (actor_id="user-123", thread_id="session-457")
│   └── [separate conversation history]
│
└── ("preferences", actor_id="user-123")
    ├── pref_uuid_1: {message: "User prefers email updates"}
    └── pref_uuid_2: {message: "Account type: Premium"}
```

---

## Technology Stack

| Layer | Technology | Version/Model | Purpose |
|-------|-----------|---------------|---------|
| **Vector Embeddings** | Amazon Titan | v2:0 | Semantic encoding of FAQ & queries |
| **Vector Store** | FAISS | Local | Fast similarity search at inference |
| **LLM** | Amazon Nova Lite | v1:0 | Fast, cost-effective reasoning |
| **Agent Framework** | LangGraph | Latest | Tool orchestration & state management |
| **Memory Backend** | Bedrock AgentCore | AWS | Persistent, scalable memory service |
| **Checkpointing** | AgentCoreMemorySaver | AWS | Snapshot conversation state |
| **Text Splitting** | LangChain RecursiveCharacterTextSplitter | - | Chunk FAQ documents |
| **Document Format** | LangChain Documents | - | Unified document representation |
| **Region** | AWS EU-North-1 | Ireland | Latency optimization for EU users |

---

## Key Design Patterns

### 1. **Retrieval-Augmented Generation (RAG)**
- External FAISS index provides factual grounding
- Prevents hallucination by anchoring responses in FAQ data
- Ensures consistency and traceability

### 2. **Agentic Loop (ReAct)**
```
Agent Loop:
  Thought → Action (select tool) → Observation (tool output)
    → Thought → Action → ... → Final Answer
```
Enables adaptive tool selection based on query complexity.

### 3. **Middleware Hooks**
- **Pre-Model**: Retrieve contextual memories before generation
- **Post-Model**: Persist new memories after generation
- Decouples memory logic from agent core

### 4. **Namespace Isolation**
- Per-user memory: `(actor_id, thread_id)`
- Per-user preferences: `("preferences", actor_id)`
- Prevents cross-user data leakage

### 5. **Singleton Pattern** (Embeddings & FAISS)
```python
# Module-level initialization (runs once)
embeddings = BedrockEmbeddings(...)
store = FAISS.load_local(...)

# Reused across all requests
```
Avoids expensive re-initialization on each request.

---

## Request Configuration

Each request passes configurable parameters:

```python
config = {
    "configurable": {
        "thread_id": thread_id,        # Conversation identifier
        "actor_id": actor_id,           # User identifier
    }
}
```

These enable:
- Multi-turn conversation tracking
- Per-user memory isolation
- Concurrent user handling
- Thread-safe execution

---

## Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| Memory save fails | Log error, continue (non-blocking) |
| Memory retrieval fails | Log error, continue without context |
| FAQ search returns empty | Return explicit "No relevant FAQ entries found" |
| LLM invocation fails | Propagate exception (blocking) |
| Missing prompt | Return "No prompt provided" |

**Philosophy**: Graceful degradation for memory operations, strict for core LLM logic.

---

## Scalability Considerations

### Horizontal Scaling
- **Stateless agent invocation**: Each request is independent
- **Shared memory backend**: AWS Bedrock AgentCore handles concurrent access
- **Shared embeddings model**: Bedrock endpoint auto-scales

### Vertical Scaling
- **FAISS index**: Loaded once in memory (~predictable size for FAQ scale)
- **Agent state**: Stored in memory only during invocation (garbage collected after)
- **Embeddings**: Called via API (no local GPU required)

### Bottlenecks
- **Cold start**: First FAISS load (mitigated by module-level init)
- **Embeddings API calls**: Rate limited by Bedrock quota
- **Memory searches**: Depend on Bedrock AgentCore latency (typically <100ms)

---

## Configuration Parameters

| Parameter | Source | Purpose |
|-----------|--------|---------|
| `region` | Config | AWS region for Bedrock models |
| `memory_id` | Config | AgentCore memory instance identifier |
| `model_id` | Config | Nova Lite v1:0 for LLM inference |
| `embeddings_model_id` | Config | Titan Embed v2 for vectorization |
| `faiss_index_path` | Filesystem | Pre-built vector index location |
| `actor_id` | Request payload | User identifier for memory isolation |
| `thread_id` | Request payload | Conversation identifier |
| `prompt` | Request payload | User query |

---

## Deployment Architecture

```
┌──────────────────────────────────────────────┐
│      AWS Bedrock AgentCore Service           │
│  (Manages agent orchestration & memory)      │
└──────────────────┬───────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
    ┌─────────┐ ┌──────────┐ ┌──────────┐
    │  Nova   │ │  Titan   │ │  Memory  │
    │  Lite   │ │  Embed   │ │  Store   │
    │  LLM    │ │ Embedder │ │          │
    └─────────┘ └──────────┘ └──────────┘
        ▲          ▲
        │          │
┌───────┴──────────┴───────────┐
│  Application Runtime         │
│ (Python / BedrockAgentCore)  │
│  - MemoryMiddleware          │
│  - Tool Definitions          │
│  - FAISS Index (cached)      │
└──────────────────────────────┘
```

---

## Security Considerations

1. **Memory Isolation**: Namespace-based separation prevents cross-user memory leakage
2. **API Keys**: Loaded via `.env` (not hardcoded)
3. **FAISS Index**: Loaded with `allow_dangerous_deserialization=True` (ensure index is trusted)
4. **Access Control**: Bedrock IAM policies control model/memory service access
5. **Input Validation**: Tool parameters are typed (Python type hints enforce schema)

---

## Future Enhancement Opportunities

1. **Semantic Caching**: Cache embedding results for frequently asked questions
2. **Feedback Loop**: Store user satisfaction ratings to improve FAQ relevance
3. **Multi-Language Support**: Extend Titan Embed for multilingual queries
4. **Conversation Summarization**: Periodically summarize long threads to manage memory growth
5. **Tool Confidence Scoring**: Track tool selection accuracy to optimize routing
6. **A/B Testing**: Compare Nova Lite vs Claude model performance
7. **Real-time FAQ Updates**: Implement vector index refresh pipeline
8. **User Preferences Learning**: Auto-detect user preferences from conversation patterns

---

## Monitoring & Observability

### Key Metrics
- **Tool Selection Distribution**: Which tools are agents choosing most?
- **FAQ Hit Rate**: % of queries finding relevant entries
- **Response Latency**: End-to-end invocation time
- **Memory Operations**: Success rate of save/retrieve operations
- **Error Rate**: Failed invocations by error type

### Logging Points
- Memory save/retrieval exceptions
- Retrieved memories (for context inspection)
- Tool selections by agent
- Final response content

---

## Deployment & Testing Commands

### Configuration Phase

**Command:**
```bash
agentcore configure -e ./customerservice_agent_memory.py
```

**Configuration Options Presented:**
- **Agent Name**: `customerservice_memoryagent`
- **Requirements File**: `pyproject.toml`
- **Deployment Type**: Direct Code Deploy (Python only, no Docker)
- **Python Runtime**: Python 3.13
- **Execution Role**: Auto-create
- **S3 Bucket**: Auto-create
- **Authorization**: IAM (default)
- **Memory**: Short-term + Long-term (30-day retention)

**Output**: Configuration file saved to `.bedrock_agentcore.yaml`

---

### Deployment Phase

**Primary Deployment Command (Cloud Mode - Recommended):**
```bash
agentcore launch
```

**Alternative Deployment Options:**
```bash
# Cloud deployment (same as launch)
agentcore deploy

# Local development mode
agentcore deploy --local
```

**Deployment Process Workflow:**
1. Create/reuse execution IAM role: `<EXECUTION_ROLE>`
2. Create deployment package (71.33 MB)
3. Reuse existing S3 bucket: `<S3_BUCKET_NAME>`
4. Upload deployment package to S3
5. Deploy to Bedrock AgentCore Runtime
6. Enable observability (CloudWatch + X-Ray)

**Deployment Outputs:**
- **Agent ARN**: `arn:aws:bedrock-agentcore:eu-north-1:<AWS_ACCOUNT_ID>:runtime/customerservice_memoryagent-<AGENT_SUFFIX>`
- **Session ID**: `<SESSION_ID>` (reset on each deployment)
- **CloudWatch Log Groups**:
  - `/aws/bedrock-agentcore/runtimes/customerservice_memoryagent-<AGENT_SUFFIX>-DEFAULT`

---

### Status & Monitoring Commands

**Check Agent Status:**
```bash
agentcore status
```

**View CloudWatch Logs (Real-time):**
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/customerservice_memoryagent-<AGENT_SUFFIX>-DEFAULT \
  --log-stream-name-prefix "<DATE>/[runtime-logs" \
  --follow
```

**View CloudWatch Logs (Last Hour):**
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/customerservice_memoryagent-<AGENT_SUFFIX>-DEFAULT \
  --log-stream-name-prefix "<DATE>/[runtime-logs" \
  --since 1h
```

**GenAI Observability Dashboard:**
```
https://console.aws.amazon.com/cloudwatch/home?region=eu-north-1#gen-ai-observability/agent-core
```

---

### Testing & Invocation Commands

**Basic Query Test:**
```bash
agentcore invoke '{"prompt": "Explain roaming activation."}'
```

**Response Format:**
```json
{
  "result": "<thinking>...</thinking>\n\nRoaming activation refers to the process of enabling your mobile device..."
}
```

**Memory Retrieval Test:**
```bash
agentcore invoke '{"prompt": "what did I ask earlier."}'
```

**Expected Behavior**: Agent references previous queries using retrieved memories.

**Custom User & Session Test:**
```bash
agentcore invoke '{
  "prompt": "Your question here",
  "actor_id": "user-123",
  "thread_id": "session-456"
}'
```

---

### Deployment Configuration Summary

| Component | Value |
|-----------|-------|
| **Agent Name** | `customerservice_memoryagent` |
| **Deployment Type** | Direct Code Deploy (python3.13) |
| **Region** | eu-north-1 |
| **Account** | `<AWS_ACCOUNT_ID>` |
| **Execution Role** | Auto-created |
| **S3 Bucket** | Auto-created |
| **Memory Service** | Bedrock AgentCore (30-day retention) |
| **Authorization** | IAM |
| **Network Mode** | Public |
| **Observability** | CloudWatch + X-Ray + GenAI Dashboard |

---

### Key Deployment Notes

1. **Direct Code Deploy**: No Docker required—Python code deployed directly to AWS Lambda runtime
2. **Cached Dependencies**: Dependencies are cached to speed up deployments (71.33 MB package size)
3. **Memory Integration**: Agent uses existing memory resource `<MEMORY_ID>`
4. **Observability**: Auto-enabled with CloudWatch Logs and X-Ray tracing
5. **Session Management**: New session ID generated per deployment; previous sessions remain accessible
6. **Cold Start**: First deployment may take several minutes; subsequent deployments use cached dependencies

---

## Summary

This architecture elegantly combines:
- **Retrieval** (FAISS + Embeddings) for grounded knowledge
- **Reasoning** (ReAct Agent) for adaptive problem-solving
- **Memory** (Bedrock AgentCore) for multi-turn context
- **Persistence** (Checkpointing) for resilience

The result is a scalable, fault-tolerant customer service agent that learns from interactions and delivers increasingly contextual responses over time.
