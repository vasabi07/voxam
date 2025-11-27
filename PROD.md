# Voxam Production Setup Guide

## System Dependencies

These must be installed on the production server (not handled by pip/poetry):

### PDF Processing (Required for Unstructured)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr libmagic1

# macOS
brew install poppler tesseract libmagic

# Alpine (Docker)
apk add --no-cache poppler-utils tesseract-ocr libmagic
```

| Package | Purpose | Required For |
|---------|---------|--------------|
| `poppler-utils` | PDF → image conversion | `partition_pdf()` with images |
| `tesseract-ocr` | OCR (extract text from images) | `hi_res` strategy |
| `libmagic` | File type detection | Auto-detecting file types |

---

## Docker Setup (Recommended for Prod)

### Dockerfile Example

```dockerfile
FROM python:3.12-slim

# Install system dependencies for Unstructured
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
RUN pip install .

COPY . .
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Infrastructure Services

### Neo4j Aura (Graph Database)
- **Purpose**: Store document chunks, embeddings, questions
- **Setup**: https://console.neo4j.io
- **Required Indexes**:
  ```cypher
  -- Vector index for semantic search
  CREATE VECTOR INDEX contentBlockEmbeddingIdx IF NOT EXISTS
  FOR (cb:ContentBlock) ON (cb.embedding)
  OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }}
  
  -- Fulltext index for keyword search
  CREATE FULLTEXT INDEX contentBlockFulltextIdx IF NOT EXISTS
  FOR (cb:ContentBlock) ON EACH [cb.text_content, cb.combined_context]
  ```

### Redis Stack (Checkpointing & Caching)
- **Purpose**: LangGraph memory checkpointing, session state
- **Docker**:
  ```bash
  docker run -d --name redis-stack \
    -p 6379:6379 \
    -p 8001:8001 \
    -v redis-data:/data \
    redis/redis-stack:latest
  ```
- **Managed Options**: Redis Cloud, AWS ElastiCache, Upstash

### R2/S3 (File Storage)
- **Purpose**: Store uploaded PDFs, audio recordings
- **Provider**: Cloudflare R2 (S3-compatible)

---

## Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Neo4j Aura
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# Redis
REDIS_URL=redis://localhost:6379

# R2/S3 Storage
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
R2_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com

# LiveKit (Voice)
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

---

## Health Checks

```bash
# Check tesseract
tesseract --version

# Check poppler
pdftoppm -v

# Check Neo4j connection
python -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('$NEO4J_URI', auth=('neo4j', '$NEO4J_PASSWORD')); d.verify_connectivity(); print('✅ Neo4j OK')"

# Check Redis
redis-cli ping
```

---

## Scaling Considerations

- [ ] Neo4j Aura tier sizing (based on document count)
- [ ] Redis memory limits
- [ ] API rate limits (OpenAI embeddings)
- [ ] Concurrent ingestion workers
- [ ] CDN for static assets (Next.js)

---

## TODO

- [ ] Add Kubernetes manifests
- [ ] Add docker-compose.yml for local dev
- [ ] Add CI/CD pipeline config
- [ ] Add monitoring (Prometheus/Grafana)
- [ ] Add backup strategy for Neo4j
