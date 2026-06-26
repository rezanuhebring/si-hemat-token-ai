# Thinker-Pro Recommended OpenWebUI Configuration

Use this configuration in OpenWebUI Model settings for `thinker-pro`.

## Model

- Display Name: thinker-pro
- Backend Model ID: thinker-pro
- Provider: OpenAI-compatible (LiteLLM)
- API Base URL: <http://openwebui-tools:9099/v1>

## System Prompt

Use the contents of `thinker-pro-system-prompt.md`.

## Capabilities

Enable these capabilities in OpenWebUI for this model profile:

- Knowledge Retrieval: enabled
- Tool Calling: enabled
- Citations: enabled
- Web Search: enabled (if your OpenWebUI web search provider is configured)
- Terminal Tool: enabled (if OpenWebUI terminal plugin is installed)
- Code Interpreter: enabled

## Retrieval Settings

- Embedding Engine: OpenAI-compatible
- Embedding Model: embed-model
- Hybrid Search: enabled
- Reranking: enabled
- Reranking Model: BAAI/bge-reranker-v2-m3
- Top K: 8
- Top K Reranker: 8

## Safety Settings

- Temperature: 0.2
- Max retries: 2
- Strict citation requirement: enabled
- Hallucination mitigation: instruct model to state uncertainty and request verification
