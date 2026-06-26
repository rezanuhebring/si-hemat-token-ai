# Jarvis Auto Routing (OpenWebUI + LiteLLM)

This guide creates a single model label, `Jarvis`, with conservative routing:

- Default for all requests -> `thinker-pro`
- If an image is attached and the prompt asks for image-to-text output -> `Vision`

## 1) LiteLLM Model Alias

`config.yaml` now includes a `jarvis` alias.

Use `jarvis` as the default backend model in OpenWebUI when your Pipe does not override to a specific specialist.

## 2) OpenWebUI Pipe (Single Entry Model)

Use the ready-to-paste script in:

- `scripts/openwebui_jarvis_pipe.py`

In OpenWebUI Admin -> Functions, create a Pipe function and paste the full contents of that file.

## 3) OpenWebUI Model Setup

In OpenWebUI Models:

- Add/select the Pipe model `Jarvis` as your default chat model.
- Keep specialist models available:
  - `Vision`
  - `thinker-pro`
  - `coder-fast`
  - `coder-pro`

## 4) Recommended Behavior Tuning

Tune these values in the Pipe:

- Extend `_image_needs_text_output()` keywords for your preferred image-intent detection.
- Keep `DEFAULT_MODEL` as `thinker-pro` for stable behavior.
- Keep `THINKER_MIN_MAX_TOKENS` around `800` for qwen3-based thinker-pro, otherwise short requests can return empty content.
- For CRM expansion prompts, keep `THINKER_CRM_MIN_MAX_TOKENS` high (default `2400`) to avoid hidden-thinking cutoffs.
- CRM expansion prompts now use a strict concise template (8 sections, 3-6 bullets each) to reduce UI-side apparent truncation.

## 5) Notes

- Intent routing is heuristic; keep manual model override enabled in UI.
- Deterministic image routing is reliable because request body contains image parts.
- If Pipe is unavailable, `jarvis` still routes via LiteLLM complexity router.
- For Cline tool workflows, prefer `coder-fast` or `coder-pro` directly instead of `jarvis`.

## 6) Vision Fallback

LiteLLM now includes:

- `Vision -> vision-fallback`
- `vision-fallback` model alias uses `ollama/llava`

If `llava` is not present locally, pull it:

```powershell
docker compose --profile local-models exec ollama ollama pull llava
```

## 7) Smoke Test

Run the routing smoke test script:

```powershell
.\scripts\test-jarvis-routing.ps1
```

This validates:

- `jarvis` simple prompt
- `jarvis` code prompt
- `jarvis` reasoning prompt
- `Vision` image prompt
- `vision-fallback` direct prompt
