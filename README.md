# 🤖 Amazon Bedrock AgentCore Crash Course

This crash course is a hands-on introduction to **Amazon Bedrock AgentCore**, a fully managed service for building and deploying intelligent agents. This repository contains progressive examples demonstrating how to build AI agents that leverage language models, RAG (Retrieval-Augmented Generation), and memory management.

## 📚 Course Structure

This course includes three example implementations of increasing complexity:

1. **`00_langgraph_agent.py`** - Basic LangGraph agent with FAQ search capabilities using LangChain
2. **`01_agentcore_runtime.py`** - AgentCore runtime integration with tool-based FAQ search and query reformulation
3. **`02_agentcore_memory.py`** - Advanced agent with memory management for maintaining conversation history and user preferences

Each example uses the **Lauki Q&A dataset** (`lauki_qna.csv`) as a knowledge base for the agent to search and provide answers to user questions.

## 🛠️ **Set-up & Pre-requisites**

### System Requirements

- **Python**: 3.13 or newer (see [python.org/downloads](https://www.python.org/downloads/) to install)
- **Operating System**: Windows, macOS, or Linux
- **uv**: Ultra-fast Python package installer and resolver

Check your Python version:
```bash
python --version
```

Install uv:
```bash
pip install uv
```
Or follow the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)

### AWS Account & Credentials

- An **AWS account** with access to Amazon Bedrock
- **AWS credentials** configured (see [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html))
- Region set to a supported AgentCore region (e.g., `ap-southeast-2`, `us-east-1`)

### API Keys

- **GROQ API Key**: Required for accessing the Groq LLM service
  - Sign up at [console.groq.com](https://console.groq.com)
  - Create an API key in your account settings

## 📦 Installation

### Step 1: Clone or Download the Repository

```bash
cd agentcore-crash-course
```

### Step 2: Install Dependencies

#### Option A: Using uv with pyproject.toml (Recommended)

```bash
uv sync
```

This installs all dependencies specified in `pyproject.toml`.

### Step 3: Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
touch .env
```

Add your API keys:

```env
GROQ_API_KEY=your_groq_api_key_here
HF_API_KEY=your_huggingface_api_key_here
```

## ▶️ Running the Agents

### Example 1: Basic LangGraph Agent

A simple agent implementation using LangGraph with FAQ search capabilities:

```bash
python 00_langgraph_agent.py
```

This will run an agent that answers the question "Explain roaming activation" using semantic search over the FAQ knowledge base.

### Example 2: AgentCore Runtime Agent

An agent deployed in the AgentCore runtime with tool-based search and query reformulation:

```bash
agentcore configure -e 01_agentcore_runtime.py
```

This generates `bedrock_agentcore.yaml` with tool definitions and agent configuration.

Deploy the agent:

```bash
agentcore launch --env GROQ_API_KEY=your_groq_api_key_here
```

Test the deployed agent:

```bash
agentcore invoke '{"prompt": "Explain roaming activation"}'
```

This example demonstrates:

- Tool definitions for FAQ search
- Query reformulation for complex questions
- AgentCore entrypoint for production deployment

### Example 3: AgentCore with Memory

An advanced agent with conversation memory and user preferences:

```bash
agentcore configure -e 02_agentcore_memory.py
```

This generates the agent configuration with memory management settings.

Deploy the agent:

```bash
agentcore launch --env GROQ_API_KEY=your_groq_api_key_here
```

Test the deployed agent:

```bash
agentcore invoke '{"prompt": "Remember my preference and answer my question"}'
```

This example demonstrates:

- Persistent memory using AgentCore Memory
- Pre and post-model hooks for memory management
- Session-based conversation tracking
- User preference retrieval

## ⚙️ Troubleshooting

### Issue: Python version error
**Solution**: Ensure you have Python 3.13 or newer installed:
```bash
python --version
```

### Issue: Missing `GROQ_API_KEY`
**Solution**: Verify your `.env` file contains the key and is in the project root:
```bash
cat .env
```

### Issue: FAISS installation fails
**Solution**: Install the CPU version explicitly:
```bash
uv pip install --upgrade faiss-cpu
```

### Issue: AWS credentials not found
**Solution**: Configure AWS credentials using AWS CLI:
```bash
aws configure
```

## 📚 Additional Resources

- [Amazon bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/?trk=33dad69a-efe5-4eb8-b3eb-bfdc0cf9a3c0&sc_channel=el)
- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-toolkit.html/?trk=33dad69a-efe5-4eb8-b3eb-bfdc0cf9a3c0&sc_channel=el)
- [Amazon Bedrock Agentcore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)

---
Copyright©️ Codebasics Inc. All rights reserved.
