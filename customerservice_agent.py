import csv
import boto3
from typing import List
from typing_extensions import TypedDict

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain_aws import ChatBedrock
from langchain_community.vectorstores import FAISS
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from bedrock_agentcore.runtime import BedrockAgentCoreApp

_ = load_dotenv()

app = BedrockAgentCoreApp()

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

def get_groq_api_key():
    client = boto3.client("secretsmanager", region_name="eu-north-1")
    response = client.get_secret_value(SecretId="groq-api-key")
    return response["SecretString"]

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
    prompt=system_prompt
)


@app.entrypoint
def agent_invocation(payload, context):
    query = payload.get("prompt", "No prompt found in input")
    result = agent.invoke({"messages": [("human", query)]})
    return {"result": result['messages'][-1].content}


if __name__ == "__main__":
    app.run()