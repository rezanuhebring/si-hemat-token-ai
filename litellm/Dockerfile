FROM python:3.11-slim

# System deps: gcc + libpq-dev are needed by some litellm[proxy] transitive deps.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Pillow is required by LiteLLM's Ollama image conversion path.
# prisma is the database client used by the LiteLLM proxy.
RUN pip install --no-cache-dir 'litellm[proxy]' Pillow prisma

# Generate the Prisma client from LiteLLM's bundled schema.
RUN prisma generate --schema /usr/local/lib/python3.11/site-packages/litellm/proxy/schema.prisma

WORKDIR /app

ENTRYPOINT ["litellm"]
