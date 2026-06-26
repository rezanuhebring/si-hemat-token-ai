# OpenWebUI Claude-like Assistant Platform

This workspace now deploys a production-ready assistant platform on Windows and Linux with:

- OpenWebUI
- LiteLLM proxy
- Ollama local models on Windows, or containerized Ollama on Linux
- Apache Tika for document extraction
- ChromaDB for vector storage
- Custom OpenWebUI tools API (FastAPI)
- Persistent knowledge and memory volumes

## What Was Implemented

### Phase 1: Document Processing

- Added Apache Tika service to `docker-compose.yml`.
- Configured OpenWebUI to use Tika with:
	- `CONTENT_EXTRACTION_ENGINE=tika`
	- `TIKA_SERVER_URL=http://tika:9998`
- Added `ingest_document()` equivalent endpoint as OpenAPI tool:
	- `POST /ingest_document`
	- Accepts file upload
	- Extracts text via Tika
	- Generates metadata + summary
	- Persists extracted content

Supported document types:

- PDF
- DOCX
- XLSX
- PPTX
- TXT
- HTML
- CSV

### Phase 2: Knowledge Management

Persistent structure (inside `openwebui-tools` container):

- `/data/knowledge/documents`
- `/data/knowledge/summaries`
- `/data/knowledge/metadata`

Implemented tools:

- `POST /save_knowledge`
- `POST /search_knowledge`
- `GET /list_knowledge`
- `POST /delete_knowledge`

### Phase 3: RAG Improvements

LiteLLM model aliases updated:

- Primary embedding alias: `embed-model -> ollama/mxbai-embed-large:latest`
- Fallback alias: `embed-model-fallback -> ollama/nomic-embed-text:latest`
- Router fallback mapping in `config.yaml`

OpenWebUI retrieval config:

- Hybrid retrieval enabled
- Reranking model set to `BAAI/bge-reranker-v2-m3`
- Top-K and reranking depth configured

### Phase 4: Infrastructure Tools

Structured JSON tool endpoints:

- `GET /system_health`
- `GET /gpu_status`
- `GET /docker_ps`
- `POST /docker_logs`
- `GET /ollama_models`
- `GET /ollama_running`
- `GET /litellm_health`
- `GET /openwebui_health`

### Phase 5: Document Extraction Agent

Tool endpoint:

- `POST /extract_information`

Returns structured JSON with:

- `document_type`
- `entities`
- `dates`
- `project_names`
- `contacts`
- `action_items`
- `risks`

### Phase 6: Memory Assistant

Persistent memory file:

- `/data/memory/memory.json`

Implemented tools:

- `POST /save_fact`
- `POST /get_fact`
- `POST /search_facts`

### Phase 7: Thinker-Pro Configuration

Created recommended system prompt file:

- `thinker-pro-system-prompt.md`

Includes:

- Deep reasoning policy
- Fact-checking policy
- Tool-first policy
- Citation requirement
- Anti-hallucination policy

### Phase 8: Docker Updates

`docker-compose.yml` now includes:

- Apache Tika
- ChromaDB
- OpenWebUI tools service
- Persistent volumes for knowledge, memory, and Chroma
- Health checks across services
- Service dependency ordering
- Host-override support for Ollama on Windows

## Repository Files

- `docker-compose.yml`
- `config.yaml`
- `.env.example`
- `tools/Dockerfile`
- `tools/requirements.txt`
- `tools/app/main.py`
- `openwebui-tools-config.json`
- `thinker-pro-system-prompt.md`

## Installation Instructions

1. Copy environment template:

```powershell
Copy-Item .env.example .env
```

2. Set secure values in `.env`:

- `LITELLM_MASTER_KEY`
- `LITELLM_SALT_KEY`
- `OPENWEBUI_LITELLM_KEY`
- `POSTGRES_PASSWORD`
- `WEBUI_SECRET_KEY`

3. Start stack:

Windows:

```powershell
.\scripts\deploy-stack.ps1
```

Linux:

```bash
./scripts/deploy-stack.sh
```

4. Pull required models:

Windows local Ollama:

```powershell
ollama pull qwen3.5:9b
ollama pull qwen2.5-coder:7b
ollama pull qwen3:14b
ollama pull llava
ollama pull mxbai-embed-large:latest
ollama pull nomic-embed-text:latest
ollama pull BAAI/bge-reranker-v2-m3
```

Linux container Ollama:

```powershell
docker compose --profile local-models exec ollama ollama pull qwen3.5:9b
docker compose --profile local-models exec ollama ollama pull qwen2.5-coder:7b
docker compose --profile local-models exec ollama ollama pull qwen3:14b
docker compose --profile local-models exec ollama ollama pull llava
docker compose --profile local-models exec ollama ollama pull mxbai-embed-large:latest
docker compose --profile local-models exec ollama ollama pull nomic-embed-text:latest
docker compose --profile local-models exec ollama ollama pull BAAI/bge-reranker-v2-m3
```

5. Verify services:

```powershell
docker compose ps
curl http://localhost:9099/healthz
curl http://localhost:4000/health/liveliness
```

The bootstrap scripts now handle the deployment split automatically:

- Windows checks Docker availability, installs Docker Desktop when possible, checks for a local Ollama service, and deploys the app without the Ollama container.
- Linux checks Docker availability, installs Docker Engine and the Compose plugin when possible, and deploys the full stack including the Ollama container.

## OpenWebUI Tool Integration

Use OpenWebUI Admin settings to add an OpenAPI tool server:

- Base URL: `http://openwebui-tools:9099`
- OpenAPI URL: `http://openwebui-tools:9099/openapi.json`
- Auth: none (internal Docker network)

Reference config file:

- `openwebui-tools-config.json`

## Cline Configuration

Use native Ollama for Cline in this workspace.

Recommended settings:

- Cline Provider: `Ollama`
- Model: `qwen3:14b`
- Model Context Window: `32768`
- Keep manual model selection enabled; do not route Cline through `jarvis`.

Operational note:

- OpenWebUI continues to use LiteLLM through the local stack.
- Cline should not use the OpenAI-compatible LiteLLM path in this repository for agentic tool workflows.
- The `openwebui-tools` proxy still exposes `/v1/models` and `/v1/chat/completions` for OpenWebUI-compatible integrations, but Cline is expected to use the native Ollama provider directly.

Why this split exists:

- `qwen3:14b` behaves correctly for Cline when used through the native Ollama provider.
- The `OpenAI-compatible -> LiteLLM -> Ollama` path proved unreliable for Cline's tool loop in this environment.

Windows local Ollama note:

- Ensure `.env` contains `OLLAMA_BASE_URL=http://host.docker.internal:11434` so LiteLLM in Docker can reach local Ollama.

After editing `config.yaml`, restart LiteLLM:

```powershell
docker compose restart litellm
```

## Migration Instructions

1. Stop previous stack:

```powershell
docker compose down
```

2. Back up existing OpenWebUI and LiteLLM data (optional, recommended):

```powershell
docker volume ls
```

3. Pull new images and rebuild tools service:

```powershell
docker compose --profile local-models pull
docker compose --profile local-models build --no-cache openwebui-tools
```

4. Start updated stack:

```powershell
docker compose --profile local-models up -d
```

5. Reconfigure OpenWebUI model/system prompt if needed:

- Set `thinker-pro` instructions using `thinker-pro-system-prompt.md` in model settings.

6. Optional knowledge migration:

- Existing OpenWebUI knowledge remains in `open-webui-data` volume.
- New custom tool knowledge persists in `knowledge-data` volume.

## Testing Procedures

### A. Infrastructure Health

```powershell
curl http://localhost:9099/system_health
curl http://localhost:9099/docker_ps
curl http://localhost:9099/litellm_health
curl http://localhost:9099/openwebui_health
```

Expected: JSON responses with `status` or `ok` fields and no fatal errors.

### B. Document Ingestion

```powershell
curl -X POST "http://localhost:9099/ingest_document" -F "file=@C:/path/to/sample.pdf"
```

Expected:

- `doc_id` returned
- Metadata and summary generated
- Files written under `/data/knowledge/*`

### C. Information Extraction

```powershell
curl -X POST "http://localhost:9099/extract_information" -F "file=@C:/path/to/sample.docx"
```

Expected: structured JSON including entities, dates, contacts, actions, and risks.

### D. Knowledge Operations

1. Save:

```powershell
curl -X POST "http://localhost:9099/save_knowledge" -H "Content-Type: application/json" -d "{\"title\":\"Runbook\",\"content\":\"Service restart procedure...\"}"
```

2. Search:

```powershell
curl -X POST "http://localhost:9099/search_knowledge" -H "Content-Type: application/json" -d "{\"query\":\"restart procedure\",\"top_k\":5}"
```

3. List:

```powershell
curl http://localhost:9099/list_knowledge
```

### E. Memory Operations

```powershell
curl -X POST "http://localhost:9099/save_fact" -H "Content-Type: application/json" -d "{\"key\":\"primary_cluster\",\"value\":\"prod-us-east-1\"}"
curl -X POST "http://localhost:9099/get_fact" -H "Content-Type: application/json" -d "{\"key\":\"primary_cluster\"}"
curl -X POST "http://localhost:9099/search_facts" -H "Content-Type: application/json" -d "{\"keyword\":\"cluster\"}"
```

## Operational Notes

- `openwebui-tools` mounts Docker socket read-only for diagnostic endpoints.
- Keep `openwebui-tools` bound to localhost (`127.0.0.1:9099`) on host.
- For production hardening, put tools service behind auth or restrict via Docker network policy.
- If Ollama is unavailable, embedding fallback and some tools may degrade gracefully.
