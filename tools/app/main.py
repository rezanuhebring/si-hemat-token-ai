import json
import logging
import re
import shutil
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

import docker
import requests
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field


APP_NAME = "OpenWebUI Tool Server"
APP_VERSION = "1.0.0"

TIKA_SERVER_URL = "http://tika:9998"
LITELLM_BASE_URL = "http://litellm:4000"
LITELLM_API_KEY = ""
OLLAMA_BASE_URL = "http://ollama:11434"
OPENWEBUI_BASE_URL = "http://open-webui:8080"
CHROMA_BASE_URL = "http://chromadb:8000"
KNOWLEDGE_ROOT = Path("/data/knowledge")
MEMORY_FILE_PATH = Path("/data/memory/memory.json")
SUMMARY_MODEL = "thinker-pro"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
COMPAT_PROXY_TIMEOUT_SECONDS = 600

import os

TIKA_SERVER_URL = os.getenv("TIKA_SERVER_URL", TIKA_SERVER_URL).rstrip("/")
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", LITELLM_BASE_URL).rstrip("/")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", LITELLM_API_KEY)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL).rstrip("/")
OPENWEBUI_BASE_URL = os.getenv("OPENWEBUI_BASE_URL", OPENWEBUI_BASE_URL).rstrip("/")
CHROMA_BASE_URL = os.getenv("CHROMA_BASE_URL", CHROMA_BASE_URL).rstrip("/")
KNOWLEDGE_ROOT = Path(os.getenv("KNOWLEDGE_ROOT", str(KNOWLEDGE_ROOT)))
MEMORY_FILE_PATH = Path(os.getenv("MEMORY_FILE_PATH", str(MEMORY_FILE_PATH)))
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", SUMMARY_MODEL)
RERANK_MODEL = os.getenv("RERANK_MODEL", RERANK_MODEL)
COMPAT_PROXY_TIMEOUT_SECONDS = int(os.getenv("COMPAT_PROXY_TIMEOUT_SECONDS", str(COMPAT_PROXY_TIMEOUT_SECONDS)))

DOCUMENTS_DIR = KNOWLEDGE_ROOT / "documents"
SUMMARIES_DIR = KNOWLEDGE_ROOT / "summaries"
METADATA_DIR = KNOWLEDGE_ROOT / "metadata"
INDEX_FILE = METADATA_DIR / "index.json"

SUPPORTED_TYPES = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".txt",
    ".html",
    ".htm",
    ".csv",
}

storage_lock = Lock()

app = FastAPI(title=APP_NAME, version=APP_VERSION)
logger = logging.getLogger("uvicorn.error")


def _litellm_headers_from_request(request: Request) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    incoming_auth = request.headers.get("authorization")
    if incoming_auth:
        headers["Authorization"] = incoming_auth
    elif LITELLM_API_KEY:
        headers["Authorization"] = f"Bearer {LITELLM_API_KEY}"
    return headers


def _extract_tool_call_from_content(content: str) -> dict[str, Any] | None:
    if not content:
        return None
    text = content.strip()
    if not text:
        return None

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict) and "name" in payload and "arguments" in payload:
        arguments = payload.get("arguments", {})
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=True)
        return {
            "id": f"call_{uuid.uuid4().hex}",
            "type": "function",
            "function": {
                "name": str(payload.get("name")),
                "arguments": arguments,
            },
        }

    if isinstance(payload, dict) and isinstance(payload.get("tool_calls"), list) and payload["tool_calls"]:
        first = payload["tool_calls"][0]
        if isinstance(first, dict) and first.get("function"):
            fn = first["function"]
            arguments = fn.get("arguments", "{}")
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=True)
            return {
                "id": first.get("id", f"call_{uuid.uuid4().hex}"),
                "type": "function",
                "function": {
                    "name": str(fn.get("name", "tool")),
                    "arguments": arguments,
                },
            }

    return None


def _sse_line(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=True)}\n\n"


def _build_stream_chunks(upstream_payload: dict[str, Any], upstream_json: dict[str, Any]) -> Iterator[str]:
    choice = ((upstream_json.get("choices") or [{}])[0])
    message = choice.get("message") or {}
    model_name = upstream_json.get("model", upstream_payload.get("model", "unknown"))
    stream_id = upstream_json.get("id", f"chatcmpl_{uuid.uuid4().hex}")
    created = int(datetime.now(UTC).timestamp())

    tool_calls = message.get("tool_calls")
    if not tool_calls and isinstance(message.get("content"), str):
        parsed = _extract_tool_call_from_content(message.get("content", ""))
        if parsed:
            tool_calls = [parsed]

    # Emit minimal OpenAI-style SSE chunks that clients can execute as tools.
    yield _sse_line(
        {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model_name,
            "choices": [{"index": 0, "delta": {"role": "assistant"}}],
        }
    )

    if tool_calls:
        name_calls = []
        arg_calls = []
        for idx, call in enumerate(tool_calls):
            fn = call.get("function", {}) if isinstance(call, dict) else {}
            arguments = fn.get("arguments", "{}")
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=True)
            tool_call_id = call.get("id", f"call_{uuid.uuid4().hex}")
            name_calls.append(
                {
                    "index": idx,
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": str(fn.get("name", "tool")),
                        "arguments": "",
                    },
                }
            )
            arg_calls.append(
                {
                    "index": idx,
                    "function": {
                        "arguments": arguments,
                    },
                }
            )

        yield _sse_line(
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {"tool_calls": name_calls}}],
            }
        )
        yield _sse_line(
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {"tool_calls": arg_calls}}],
            }
        )
        yield _sse_line(
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
            }
        )
    else:
        content = message.get("content")
        if isinstance(content, str) and content:
            yield _sse_line(
                {
                    "id": stream_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model_name,
                    "choices": [{"index": 0, "delta": {"content": content}}],
                }
            )
        yield _sse_line(
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
        )

    yield "data: [DONE]\n\n"


class SaveKnowledgeInput(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    category: str = Field(default="general")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchKnowledgeInput(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    category: str | None = None
    metadata_filters: dict[str, str] = Field(default_factory=dict)
    rerank: bool = True


class DeleteKnowledgeInput(BaseModel):
    doc_id: str = Field(min_length=1)


class DockerLogsInput(BaseModel):
    container: str = Field(min_length=1)
    tail: int = Field(default=200, ge=1, le=2000)


class SaveFactInput(BaseModel):
    key: str = Field(min_length=1)
    value: Any


class GetFactInput(BaseModel):
    key: str = Field(min_length=1)


class SearchFactsInput(BaseModel):
    keyword: str = Field(min_length=1)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_paths() -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("[]", encoding="utf-8")

    if not MEMORY_FILE_PATH.exists():
        MEMORY_FILE_PATH.write_text(json.dumps({"facts": {}}, ensure_ascii=True), encoding="utf-8")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_\-]{3,}", text.lower()))


def detect_doc_type(filename: str, content_type: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext:
        return ext.lstrip(".")
    if content_type:
        return content_type
    return "unknown"


def service_ok(url: str, timeout: float = 4.0) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=timeout)
        return {"ok": response.status_code < 400, "status_code": response.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def extract_text_with_tika(file_bytes: bytes, filename: str, content_type: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": content_type or "application/octet-stream",
        "Content-Disposition": f'attachment; filename="{filename}"',
    }

    response = requests.put(
        f"{TIKA_SERVER_URL}/rmeta/text",
        data=file_bytes,
        headers=headers,
        timeout=120,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Tika extraction failed with status {response.status_code}")

    payload = response.json()
    if not isinstance(payload, list) or not payload:
        raise HTTPException(status_code=502, detail="Unexpected Tika response")

    first = payload[0]
    text = first.get("X-TIKA:content", "").strip()
    metadata = {k: v for k, v in first.items() if k != "X-TIKA:content"}
    return {"text": text, "metadata": metadata}


def summarize_text(text: str, title: str) -> str:
    trimmed = "\n".join(line.strip() for line in text.splitlines() if line.strip())[:12000]
    if not trimmed:
        return "No extractable text content found."

    prompt = (
        "Summarize the document in concise bullets. "
        "Include key facts, dates, project context, action items, and risks when present."
    )

    payload = {
        "model": SUMMARY_MODEL,
        "messages": [
            {"role": "system", "content": "You summarize documents accurately and conservatively."},
            {"role": "user", "content": f"Title: {title}\n\n{prompt}\n\nDocument:\n{trimmed}"},
        ],
        "temperature": 0.1,
    }

    headers = {"Content-Type": "application/json"}
    if LITELLM_API_KEY:
        headers["Authorization"] = f"Bearer {LITELLM_API_KEY}"

    try:
        response = requests.post(
            f"{LITELLM_BASE_URL}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        lines = [line for line in trimmed.splitlines() if line]
        return "\n".join(f"- {line[:180]}" for line in lines[:10])


def classify_category(filename: str, text: str) -> str:
    ext = Path(filename).suffix.lower()
    lower = text.lower()

    if ext in {".py", ".js", ".ts", ".go", ".java"}:
        return "code"
    if "invoice" in lower or "payment" in lower:
        return "finance"
    if "incident" in lower or "outage" in lower or "cluster" in lower:
        return "infrastructure"
    if "requirement" in lower or "specification" in lower:
        return "requirements"
    return "general"


def build_record(
    doc_id: str,
    filename: str,
    category: str,
    text: str,
    summary: str,
    tika_metadata: dict[str, Any],
    custom_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": doc_id,
        "filename": filename,
        "doc_type": detect_doc_type(filename, ""),
        "category": category,
        "summary": summary,
        "metadata": {
            "created_at": now_iso(),
            "text_length": len(text),
            "tika": tika_metadata,
            "custom": custom_metadata,
        },
        "paths": {
            "document": str((DOCUMENTS_DIR / f"{doc_id}.txt").as_posix()),
            "summary": str((SUMMARIES_DIR / f"{doc_id}.md").as_posix()),
            "metadata": str((METADATA_DIR / f"{doc_id}.json").as_posix()),
        },
    }


def persist_record(record: dict[str, Any], text: str, summary: str) -> None:
    with storage_lock:
        ensure_paths()

        (DOCUMENTS_DIR / f"{record['id']}.txt").write_text(text, encoding="utf-8")
        (SUMMARIES_DIR / f"{record['id']}.md").write_text(summary, encoding="utf-8")
        save_json(METADATA_DIR / f"{record['id']}.json", record)

        index = load_json(INDEX_FILE, [])
        index = [item for item in index if item.get("id") != record["id"]]
        index.append(record)
        save_json(INDEX_FILE, index)


def read_doc_text(doc_id: str) -> str:
    path = DOCUMENTS_DIR / f"{doc_id}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def metadata_matches(entry: dict[str, Any], metadata_filters: dict[str, str]) -> bool:
    if not metadata_filters:
        return True

    blob = json.dumps(entry.get("metadata", {}), ensure_ascii=True).lower()
    for key, value in metadata_filters.items():
        key_value = f"{key}:{value}".lower()
        if key_value not in blob and str(value).lower() not in blob:
            return False
    return True


def score_entry(query: str, entry: dict[str, Any], text: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0

    text_tokens = tokenize(text)
    summary_tokens = tokenize(entry.get("summary", ""))

    overlap_text = len(query_tokens.intersection(text_tokens)) / max(1, len(query_tokens))
    overlap_summary = len(query_tokens.intersection(summary_tokens)) / max(1, len(query_tokens))
    filename_hit = 0.15 if query.lower() in entry.get("filename", "").lower() else 0.0

    return round((overlap_text * 0.7) + (overlap_summary * 0.3) + filename_hit, 4)


def rerank(query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_tokens = tokenize(query)
    for candidate in candidates:
        excerpt = (candidate.get("excerpt") or "").lower()
        sentence_scores = []
        for sentence in re.split(r"(?<=[.!?])\s+", excerpt)[:20]:
            s_tokens = tokenize(sentence)
            sentence_scores.append(len(query_tokens.intersection(s_tokens)) / max(1, len(query_tokens)))
        candidate["rerank_score"] = round(max(sentence_scores) if sentence_scores else 0.0, 4)
        candidate["rerank_model"] = RERANK_MODEL
    return sorted(candidates, key=lambda x: (x.get("rerank_score", 0.0), x.get("score", 0.0)), reverse=True)


def extract_entities(text: str) -> list[str]:
    entities = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,3})\b", text)
    deduped = []
    seen = set()
    for item in entities:
        val = item.strip()
        if len(val) < 3:
            continue
        key = val.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(val)
    return deduped[:50]


def extract_dates(text: str) -> list[str]:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b",
    ]
    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    unique = []
    seen = set()
    for item in found:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:30]


def extract_project_names(text: str) -> list[str]:
    projects = []
    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        if re.search(r"\b(project|initiative|program)\b", line, flags=re.IGNORECASE):
            projects.append(line[:180])
    return projects[:20]


def extract_contacts(text: str) -> dict[str, list[str]]:
    emails = sorted(set(re.findall(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", text)))
    phones = sorted(set(re.findall(r"\+?\d[\d\s().-]{7,}\d", text)))
    names = extract_entities(text)
    return {"emails": emails[:20], "phones": phones[:20], "names": names[:30]}


def extract_action_items(text: str) -> list[str]:
    pattern = re.compile(r"^(todo|action|next step|owner|must|should|need to|follow up)[:\-\s]", re.IGNORECASE)
    hits = []
    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        if pattern.search(line):
            hits.append(line[:220])
    return hits[:40]


def extract_risks(text: str) -> list[str]:
    hits = []
    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        if re.search(r"\b(risk|issue|blocker|impact|failure|degraded|vulnerability)\b", line, flags=re.IGNORECASE):
            hits.append(line[:220])
    return hits[:40]


@app.on_event("startup")
def startup() -> None:
    ensure_paths()


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "service": APP_NAME, "version": APP_VERSION, "time": now_iso()}


@app.get("/v1/models")
def compat_models(request: Request) -> JSONResponse:
    headers = _litellm_headers_from_request(request)
    try:
        response = requests.get(
            f"{LITELLM_BASE_URL}/v1/models",
            headers=headers,
            timeout=COMPAT_PROXY_TIMEOUT_SECONDS,
        )
        return JSONResponse(status_code=response.status_code, content=response.json())
    except requests.exceptions.RequestException as exc:
        return JSONResponse(status_code=504, content={"error": {"message": str(exc), "type": "upstream_timeout"}})


def _passthrough_get(request: Request, path: str) -> JSONResponse:
    headers = _litellm_headers_from_request(request)
    try:
        response = requests.get(
            f"{LITELLM_BASE_URL}{path}",
            headers=headers,
            params=request.query_params,
            timeout=COMPAT_PROXY_TIMEOUT_SECONDS,
        )
        return JSONResponse(status_code=response.status_code, content=response.json())
    except requests.exceptions.RequestException as exc:
        return JSONResponse(status_code=504, content={"error": {"message": str(exc), "type": "upstream_timeout"}})


def _normalize_model_info_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, list):
        return payload

    for entry in data:
        if not isinstance(entry, dict):
            continue

        litellm_params = entry.get("litellm_params")
        model_info = entry.get("model_info")
        if not isinstance(litellm_params, dict) or not isinstance(model_info, dict):
            continue

        allowed = litellm_params.get("allowed_openai_params")
        if not isinstance(allowed, list):
            allowed = []

        supports_fc = bool(model_info.get("supports_function_calling")) or ("tools" in allowed)
        if not supports_fc:
            continue

        supported = model_info.get("supported_openai_params")
        if not isinstance(supported, list):
            supported = []

        for param in ("tools", "tool_choice", "parallel_tool_calls"):
            if param not in supported:
                supported.append(param)

        model_info["supported_openai_params"] = supported
        model_info["supports_function_calling"] = True
        model_info["supports_tool_choice"] = True

    return payload


@app.get("/model/info")
def compat_model_info(request: Request) -> JSONResponse:
    response = _passthrough_get(request, "/model/info")
    if response.status_code < 400 and isinstance(response.body, (bytes, bytearray)):
        try:
            payload = json.loads(response.body)
            payload = _normalize_model_info_payload(payload)
            return JSONResponse(status_code=response.status_code, content=payload)
        except Exception:
            return response
    return response


@app.get("/v1/model/info")
def compat_model_info_v1(request: Request) -> JSONResponse:
    response = _passthrough_get(request, "/v1/model/info")
    if response.status_code < 400 and isinstance(response.body, (bytes, bytearray)):
        try:
            payload = json.loads(response.body)
            payload = _normalize_model_info_payload(payload)
            return JSONResponse(status_code=response.status_code, content=payload)
        except Exception:
            return response
    return response


@app.get("/models/info")
def compat_models_info(request: Request) -> JSONResponse:
    # Some clients probe /models/info instead of /model/info.
    response = _passthrough_get(request, "/model/info")
    if response.status_code < 400 and isinstance(response.body, (bytes, bytearray)):
        try:
            payload = json.loads(response.body)
            payload = _normalize_model_info_payload(payload)
            return JSONResponse(status_code=response.status_code, content=payload)
        except Exception:
            return response
    return response


@app.get("/v1/models/info")
def compat_models_info_v1(request: Request) -> JSONResponse:
    # LiteLLM serves this as /v1/model/info.
    response = _passthrough_get(request, "/v1/model/info")
    if response.status_code < 400 and isinstance(response.body, (bytes, bytearray)):
        try:
            payload = json.loads(response.body)
            payload = _normalize_model_info_payload(payload)
            return JSONResponse(status_code=response.status_code, content=payload)
        except Exception:
            return response
    return response


@app.get("/model_group/info")
def compat_model_group_info(request: Request) -> JSONResponse:
    return _passthrough_get(request, "/model_group/info")


@app.get("/v1/model_group/info")
def compat_model_group_info_v1(request: Request) -> JSONResponse:
    # LiteLLM exposes model_group info on /model_group/info.
    return _passthrough_get(request, "/model_group/info")


@app.post("/v1/chat/completions", response_model=None)
async def compat_chat_completions(request: Request):
    payload = await request.json()
    logger.warning(
        "chat_completions model=%s stream=%s tools=%s tool_choice=%s ua=%s",
        payload.get("model"),
        bool(payload.get("stream")),
        len(payload.get("tools", [])) if isinstance(payload.get("tools"), list) else 0,
        payload.get("tool_choice"),
        request.headers.get("user-agent", ""),
    )
    headers = _litellm_headers_from_request(request)
    is_stream = bool(payload.get("stream"))

    if not is_stream:
        try:
            response = requests.post(
                f"{LITELLM_BASE_URL}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=COMPAT_PROXY_TIMEOUT_SECONDS,
            )
            return JSONResponse(status_code=response.status_code, content=response.json())
        except requests.exceptions.RequestException as exc:
            return JSONResponse(status_code=504, content={"error": {"message": str(exc), "type": "upstream_timeout"}})

    non_stream_payload = dict(payload)
    non_stream_payload["stream"] = False
    try:
        upstream = requests.post(
            f"{LITELLM_BASE_URL}/v1/chat/completions",
            json=non_stream_payload,
            headers=headers,
            timeout=COMPAT_PROXY_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        return JSONResponse(status_code=504, content={"error": {"message": str(exc), "type": "upstream_timeout"}})
    upstream_json = upstream.json()
    if upstream.status_code >= 400:
        return JSONResponse(status_code=upstream.status_code, content=upstream_json)

    return StreamingResponse(_build_stream_chunks(non_stream_payload, upstream_json), media_type="text/event-stream")


@app.post("/ingest_document")
async def ingest_document(file: UploadFile = File(...), category: str | None = Query(default=None)) -> dict[str, Any]:
    filename = sanitize_filename(file.filename or f"uploaded-{uuid.uuid4().hex}")
    extension = Path(filename).suffix.lower()

    if extension and extension not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    extracted = extract_text_with_tika(file_bytes, filename, file.content_type or "application/octet-stream")
    text = extracted["text"]
    if not text:
        raise HTTPException(status_code=422, detail="No text could be extracted from this document")

    final_category = category or classify_category(filename, text)
    summary = summarize_text(text, filename)

    doc_id = uuid.uuid4().hex
    record = build_record(
        doc_id=doc_id,
        filename=filename,
        category=final_category,
        text=text,
        summary=summary,
        tika_metadata=extracted["metadata"],
        custom_metadata={},
    )
    persist_record(record, text, summary)

    return {
        "ok": True,
        "tool": "ingest_document",
        "doc_id": doc_id,
        "category": final_category,
        "summary": summary,
        "metadata": record["metadata"],
        "paths": record["paths"],
    }


@app.post("/save_knowledge")
def save_knowledge(payload: SaveKnowledgeInput) -> dict[str, Any]:
    doc_id = uuid.uuid4().hex
    summary = summarize_text(payload.content, payload.title)
    record = build_record(
        doc_id=doc_id,
        filename=sanitize_filename(f"{payload.title}.txt"),
        category=payload.category,
        text=payload.content,
        summary=summary,
        tika_metadata={"source": "manual"},
        custom_metadata=payload.metadata,
    )
    persist_record(record, payload.content, summary)

    return {"ok": True, "tool": "save_knowledge", "doc_id": doc_id, "record": record}


@app.post("/search_knowledge")
def search_knowledge(payload: SearchKnowledgeInput) -> dict[str, Any]:
    ensure_paths()
    index = load_json(INDEX_FILE, [])

    candidates = []
    for entry in index:
        if payload.category and entry.get("category") != payload.category:
            continue
        if not metadata_matches(entry, payload.metadata_filters):
            continue

        text = read_doc_text(entry.get("id", ""))
        score = score_entry(payload.query, entry, text)
        if score <= 0:
            continue

        candidates.append(
            {
                "id": entry.get("id"),
                "filename": entry.get("filename"),
                "category": entry.get("category"),
                "score": score,
                "excerpt": text[:600],
                "summary": entry.get("summary"),
                "metadata": entry.get("metadata"),
            }
        )

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    if payload.rerank:
        candidates = rerank(payload.query, candidates)

    return {
        "ok": True,
        "tool": "search_knowledge",
        "query": payload.query,
        "hybrid_search": True,
        "similarity_search": True,
        "metadata_filtering": bool(payload.metadata_filters),
        "reranking": payload.rerank,
        "rerank_model": RERANK_MODEL,
        "count": min(payload.top_k, len(candidates)),
        "results": candidates[: payload.top_k],
    }


@app.get("/list_knowledge")
def list_knowledge() -> dict[str, Any]:
    ensure_paths()
    index = load_json(INDEX_FILE, [])
    return {"ok": True, "tool": "list_knowledge", "count": len(index), "items": index}


@app.post("/delete_knowledge")
def delete_knowledge(payload: DeleteKnowledgeInput) -> dict[str, Any]:
    ensure_paths()
    with storage_lock:
        index = load_json(INDEX_FILE, [])
        kept = [item for item in index if item.get("id") != payload.doc_id]
        removed = len(index) != len(kept)
        save_json(INDEX_FILE, kept)

        for folder, ext in ((DOCUMENTS_DIR, ".txt"), (SUMMARIES_DIR, ".md"), (METADATA_DIR, ".json")):
            path = folder / f"{payload.doc_id}{ext}"
            if path.exists():
                path.unlink()

    return {"ok": True, "tool": "delete_knowledge", "doc_id": payload.doc_id, "deleted": removed}


@app.get("/system_health")
def system_health() -> dict[str, Any]:
    disk = shutil.disk_usage(str(KNOWLEDGE_ROOT.parent if KNOWLEDGE_ROOT.parent.exists() else Path("/")))
    return {
        "ok": True,
        "tool": "system_health",
        "time": now_iso(),
        "services": {
            "tika": service_ok(f"{TIKA_SERVER_URL}/tika"),
            "litellm": service_ok(f"{LITELLM_BASE_URL}/health/liveliness"),
            "ollama": service_ok(f"{OLLAMA_BASE_URL}/api/tags"),
            "openwebui": service_ok(f"{OPENWEBUI_BASE_URL}/health"),
            "chromadb": service_ok(f"{CHROMA_BASE_URL}/api/v1/heartbeat"),
        },
        "storage": {"total_bytes": disk.total, "used_bytes": disk.used, "free_bytes": disk.free},
    }


@app.get("/gpu_status")
def gpu_status() -> dict[str, Any]:
    try:
        client = docker.from_env()
        info = client.info()
        runtimes = info.get("Runtimes", {})
        return {
            "ok": True,
            "tool": "gpu_status",
            "nvidia_runtime_available": "nvidia" in runtimes or "nvidia-container-runtime" in runtimes,
            "runtimes": list(runtimes.keys()),
            "driver": info.get("Driver"),
            "server_version": info.get("ServerVersion"),
        }
    except Exception as exc:
        return {"ok": False, "tool": "gpu_status", "error": str(exc)}


@app.get("/docker_ps")
def docker_ps() -> dict[str, Any]:
    try:
        client = docker.from_env()
        items = []
        for container in client.containers.list(all=True):
            items.append(
                {
                    "name": container.name,
                    "id": container.short_id,
                    "status": container.status,
                    "image": container.image.tags,
                }
            )
        return {"ok": True, "tool": "docker_ps", "count": len(items), "containers": items}
    except Exception as exc:
        return {"ok": False, "tool": "docker_ps", "error": str(exc), "containers": []}


@app.post("/docker_logs")
def docker_logs(payload: DockerLogsInput) -> dict[str, Any]:
    try:
        client = docker.from_env()
        container = client.containers.get(payload.container)
        logs = container.logs(tail=payload.tail, stdout=True, stderr=True).decode("utf-8", errors="ignore")
        return {
            "ok": True,
            "tool": "docker_logs",
            "container": payload.container,
            "tail": payload.tail,
            "logs": logs,
        }
    except Exception as exc:
        return {"ok": False, "tool": "docker_logs", "container": payload.container, "error": str(exc)}


@app.get("/ollama_models")
def ollama_models() -> dict[str, Any]:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=20)
        response.raise_for_status()
        return {"ok": True, "tool": "ollama_models", "models": response.json().get("models", [])}
    except Exception as exc:
        return {"ok": False, "tool": "ollama_models", "error": str(exc), "models": []}


@app.get("/ollama_running")
def ollama_running() -> dict[str, Any]:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/ps", timeout=20)
        if response.status_code == 404:
            return {
                "ok": True,
                "tool": "ollama_running",
                "running": [],
                "note": "Ollama API /api/ps not available on this version",
            }
        response.raise_for_status()
        return {"ok": True, "tool": "ollama_running", "running": response.json().get("models", [])}
    except Exception as exc:
        return {"ok": False, "tool": "ollama_running", "error": str(exc), "running": []}


@app.get("/litellm_health")
def litellm_health() -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {LITELLM_API_KEY}"} if LITELLM_API_KEY else {}
    try:
        response = requests.get(f"{LITELLM_BASE_URL}/v1/models", headers=headers, timeout=10)
        model_count = len(response.json().get("data", [])) if response.status_code < 400 else 0
        return {
            "ok": response.status_code < 400,
            "tool": "litellm_health",
            "status_code": response.status_code,
            "models_count": model_count,
        }
    except Exception as exc:
        return {"ok": False, "tool": "litellm_health", "error": str(exc)}


@app.get("/openwebui_health")
def openwebui_health() -> dict[str, Any]:
    return {"ok": True, "tool": "openwebui_health", "health": service_ok(f"{OPENWEBUI_BASE_URL}/health")}


@app.post("/extract_information")
async def extract_information(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = sanitize_filename(file.filename or f"uploaded-{uuid.uuid4().hex}")
    extension = Path(filename).suffix.lower()

    if extension and extension not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    extracted = extract_text_with_tika(file_bytes, filename, file.content_type or "application/octet-stream")
    text = extracted.get("text", "")
    if not text:
        raise HTTPException(status_code=422, detail="No text extracted for entity analysis")

    return {
        "ok": True,
        "tool": "extract_information",
        "document": {
            "filename": filename,
            "document_type": detect_doc_type(filename, file.content_type or ""),
            "size_bytes": len(file_bytes),
        },
        "entities": extract_entities(text),
        "dates": extract_dates(text),
        "project_names": extract_project_names(text),
        "contacts": extract_contacts(text),
        "action_items": extract_action_items(text),
        "risks": extract_risks(text),
        "metadata": extracted.get("metadata", {}),
    }


@app.post("/save_fact")
def save_fact(payload: SaveFactInput) -> dict[str, Any]:
    with storage_lock:
        ensure_paths()
        memory = load_json(MEMORY_FILE_PATH, {"facts": {}})
        facts = memory.setdefault("facts", {})
        facts[payload.key] = {"value": payload.value, "updated_at": now_iso()}
        save_json(MEMORY_FILE_PATH, memory)

    return {"ok": True, "tool": "save_fact", "key": payload.key, "value": payload.value}


@app.post("/get_fact")
def get_fact(payload: GetFactInput) -> dict[str, Any]:
    memory = load_json(MEMORY_FILE_PATH, {"facts": {}})
    facts = memory.get("facts", {})
    return {"ok": payload.key in facts, "tool": "get_fact", "key": payload.key, "fact": facts.get(payload.key)}


@app.post("/search_facts")
def search_facts(payload: SearchFactsInput) -> dict[str, Any]:
    memory = load_json(MEMORY_FILE_PATH, {"facts": {}})
    keyword = payload.keyword.lower()

    matches = []
    for key, value in memory.get("facts", {}).items():
        row = f"{key} {json.dumps(value, ensure_ascii=True)}".lower()
        if keyword in row:
            matches.append({"key": key, "value": value})

    return {
        "ok": True,
        "tool": "search_facts",
        "keyword": payload.keyword,
        "count": len(matches),
        "matches": matches,
    }


@app.get("/openapi_tool_manifest")
def openapi_tool_manifest() -> dict[str, Any]:
    return {
        "name": "openwebui-tools",
        "openapi_url": "/openapi.json",
        "base_url": "http://openwebui-tools:9099",
        "recommended_tools": [
            "ingest_document",
            "extract_information",
            "save_knowledge",
            "search_knowledge",
            "list_knowledge",
            "delete_knowledge",
            "system_health",
            "gpu_status",
            "docker_ps",
            "docker_logs",
            "ollama_models",
            "ollama_running",
            "litellm_health",
            "openwebui_health",
            "save_fact",
            "get_fact",
            "search_facts",
        ],
    }
