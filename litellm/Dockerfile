FROM docker.litellm.ai/berriai/litellm-database:main-stable

# Pillow is required by LiteLLM's Ollama image conversion path.
RUN apk add --no-cache py3-pip \
	&& pip install --no-cache-dir --target /app/.venv/lib/python3.13/site-packages Pillow
