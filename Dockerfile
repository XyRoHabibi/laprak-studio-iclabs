# Laprak Studio dalam Docker: Python + LibreOffice (sampul docx ke PDF) + g++ (screenshot output) + font.
# Folder proyek di-mount ke /app lewat docker-compose.yml, jadi hasil laprak tersimpan di komputer kamu.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui \
        g++ \
        fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea fonts-dejavu-core fonts-cascadia-code \
    && rm -rf /var/lib/apt/lists/*

# Opsional: pasang CLI agent di dalam container, mis.
#   docker compose build --build-arg AGENT_NPM=@anthropic-ai/claude-code
#   docker compose build --build-arg AGENT_NPM=@openai/codex
#   docker compose build --build-arg AGENT_NPM=@google/gemini-cli
ARG AGENT_NPM=""
RUN if [ -n "$AGENT_NPM" ]; then \
        apt-get update && apt-get install -y --no-install-recommends nodejs npm git ca-certificates \
        && npm install -g "$AGENT_NPM" && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LAPRAK_HOST=0.0.0.0 \
    LAPRAK_NO_BROWSER=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "studio/server.py"]
