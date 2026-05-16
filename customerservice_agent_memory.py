import csv
import uuid
import boto3
from typing import List
from langgraph_checkpoint_aws import AgentCoreMemorySaver, AgentCoreMemoryStore
from typing_extensions import TypedDict

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings,ChatBedrock
from langchain_aws import ChatBedrock
from langchain_community.vectorstores import FAISS
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from bedrock_agentcore.runtime import BedrockAgentCoreApp

_ = load_dotenv()

app = BedrockAgentCoreApp()

region = "eu-north-1"
memory_id = "customerservice_agentmemory-YuP9XI5Y5m"

checkpointer = AgentCoreMemorySaver(memory_id=memory_id)
memory_store = AgentCoreMemoryStore(memory_id=memory_id)

# ✅ Load embeddings once at module level
embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v2:0",
    region_name="eu-north-1"
)

# ✅ Load pre-built FAISS index — never rebuild at runtime
store = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)


@tool
def search_faq(query: str) -> str:
    """Search the FAQ knowledge base for relevant information."""
    results = store.similarity_search(query, k=3)
    if not results:
        return "No relevant FAQ entries found."
    return "\n\n---\n\n".join([f"FAQ Entry {i+1}:\n{doc.page_content}" for i, doc in enumerate(results)])


@tool
def search_detailed_faq(query: str, num_results: int = 5) -> str:
    """Search the FAQ knowledge base with more results for complex queries."""
    results = store.similarity_search(query, k=num_results)
    if not results:
        return "No relevant FAQ entries found."
    return "\n\n---\n\n".join([f"FAQ Entry {i+1}:\n{doc.page_content}" for i, doc in enumerate(results)])


@tool
def reformulate_query(original_query: str, focus_aspect: str) -> str:
    """Reformulate the query to focus on a specific aspect."""
    results = store.similarity_search(f"{focus_aspect} related to {original_query}", k=3)
    if not results:
        return f"No results found for aspect: {focus_aspect}"
    return "\n\n---\n\n".join([f"Entry {i+1}:\n{doc.page_content}" for i, doc in enumerate(results)])


tools = [search_faq, search_detailed_faq, reformulate_query]


# ── Memory Middleware ─────────────────────────────────────────────────────────

class MemoryMiddleware:
    """Persists conversation turns and retrieves long-term memories."""

    def pre_model_hook(self, state: dict, config: RunnableConfig) -> dict:
        actor_id = config["configurable"].get("actor_id", "default")
        thread_id = config["configurable"].get("thread_id", "default")
        namespace = (actor_id, thread_id)
        messages = state.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                try:
                    memory_store.put(namespace, str(uuid.uuid4()), {"message": msg.content})
                except Exception as e:
                    print(f"Memory save error: {e}")
                try:
                    memories = memory_store.search(
                        ("preferences", actor_id),
                        query=msg.content,
                        limit=5,
                    )
                    if memories:
                        memory_context = "\n".join(
                            f"Memory: {item.value.get('message', '')}"
                            for item in memories
                        )
                        print(f"Retrieved memories:\n{memory_context}")
                except Exception as e:
                    print(f"Memory retrieval error: {e}")
                break

        return {"messages": messages}

    def post_model_hook(self, state: dict, config: RunnableConfig) -> dict:
        actor_id = config["configurable"].get("actor_id", "default")
        thread_id = config["configurable"].get("thread_id", "default")
        namespace = (actor_id, thread_id)
        messages = state.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                try:
                    memory_store.put(namespace, str(uuid.uuid4()), {"message": msg.content})
                except Exception as e:
                    print(f"Memory save error: {e}")
                break

        return state



# ✅ Valid BedRock model
model = ChatBedrock(
    model_id="eu.amazon.nova-lite-v1:0",  # or "anthropic.claude-3-5-haiku-20241022-v1:0"
    region_name="eu-north-1",
)

system_prompt = """You are a helpful FAQ assistant with access to a knowledge base.
Use search_faq first, then search_detailed_faq or reformulate_query if needed.
Always base your answer on retrieved information. If nothing is found, say so clearly."""

# ✅ Correct agent creation
agent = create_react_agent(
    model=model,
    tools=tools,
    prompt=system_prompt, 
    checkpointer=checkpointer,
    store=memory_store,
)

middleware = MemoryMiddleware()

@app.entrypoint
def agent_invocation(payload, context):
    query = payload.get("prompt", "No prompt provided")
    # Extract or generate actor_id and thread_id
    actor_id = payload.get("actor_id", "default-user")
    thread_id = payload.get("thread_id", payload.get("session_id", "default-session"))
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "actor_id": actor_id,
        }
    }

    state = middleware.pre_model_hook({"messages": [("human", query)]}, config)
    result = agent.invoke(state, config=config)
    middleware.post_model_hook(result, config)

    messages = result.get("messages", [])
    answer = messages[-1].content if messages else "No response generated"

    return {"result": answer}


if __name__ == "__main__":
    app.run()