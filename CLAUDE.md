# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VOXAM is an AI-powered educational examination platform that enables students to upload study materials, automatically generate question papers, take interactive voice-based exams with AI proctoring, and receive instant AI-driven feedback.

## Architecture

### Monorepo Structure
```
voxam/
├── nextjs/          # Frontend - Next.js 15, React 19, TypeScript
├── python/          # Backend - FastAPI, LangGraph agents
└── supabase/        # Database migrations (Postgres via Supabase)
```

### Data Flow
1. **Document Ingestion**: Upload → R2 Storage → Celery task → OCR (Gemini/olmOCR) → Embeddings → Neo4j
2. **Question Paper Generation**: Query Neo4j → LLM ranking → Group by difficulty → Store in Postgres
3. **Exam Session**: Start → LiveKit room → LangGraph exam agent → Redis conversation cache → Correction
4. **Chat**: Query rewriting → Hybrid search (Neo4j) → RAG generation → LangGraph checkpointing (Redis)

### Key Services
- **Postgres (Supabase)**: Users, documents, exam sessions, subscriptions, correction reports
- **Neo4j**: Document content blocks with embeddings, generated questions (graph structure)
- **Redis**: LangGraph checkpointer, QP cache during exams, Celery task queue, progress tracking
- **LiveKit**: WebRTC voice/video for real-time exam sessions
- **R2 (Cloudflare)**: Document file storage

### Python Agents (`python/agents/`)
- `realtime.py` - LiveKit voice agent (Deepgram STT, Google/Deepgram TTS)
- `exam_agent.py` - LangGraph exam proctor (EXAM mode strict, LEARN mode interactive)
- `chat_agent.py` - Agentic RAG with query rewriting and hybrid search
- `correction_agent.py` - Post-exam evaluation and report generation

### Key Python Modules
- `api.py` - FastAPI main application with all endpoints
- `ingestion_workflow.py` - Document processing pipeline (OCR, embeddings, Neo4j persistence)
- `qp_agent.py` - Question paper generation workflow (LangGraph)
- `retrieval.py` - Hybrid search implementation (vector + keyword + RRF)
- `tasks/ingestion.py` - Celery background task for document processing

## Common Commands

### Frontend (Next.js)
```bash
cd nextjs
pnpm install          # Install dependencies
pnpm dev              # Start dev server (localhost:3000)
pnpm build            # Build for production (runs prisma generate first)
pnpm lint             # Run ESLint
```

### Backend (Python)
```bash
cd python
uv sync               # Install dependencies with uv
source .venv/bin/activate

# Run API server
uvicorn api:app --reload --port 8000

# Run Celery worker (for document ingestion)
celery -A celery_app worker --loglevel=info
```

### Database
```bash
cd nextjs
npx prisma generate   # Generate Prisma client
npx prisma db push    # Push schema to database
npx prisma studio     # Open Prisma Studio GUI
```

### Required Services
```bash
redis-server          # Redis for caching and Celery
# Neo4j - use AuraDB cloud or local instance
# LiveKit - use LiveKit Cloud or local: livekit-server --dev
```

## Environment Variables

### Python (`python/.env`)
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` - LiveKit credentials
- `DEEPGRAM_API_KEY` - Speech-to-text
- `GOOGLE_APPLICATION_CREDENTIALS` - Google Cloud TTS
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` - Graph database
- `REDIS_URI` - Redis connection
- `OPENAI_API_KEY` - Embeddings and LLM
- `DEEPINFRA_API_KEY` - Alternative LLM provider (Nemotron)
- `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` - Supabase access

### Next.js (`nextjs/.env.local`)
- `NEXT_PUBLIC_LIVEKIT_URL` - LiveKit WebSocket URL (client-side)
- `NEXT_PUBLIC_API_URL` - Python backend URL
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase client
- `DATABASE_URL` - Postgres connection for Prisma

## Key Patterns

### Authentication
- Better-Auth with Supabase JWT (ES256 algorithm)
- Token verification in `python/security.py` using JWKS
- Middleware in `api.py` protects `/copilotkit` endpoint

### LangGraph State Persistence
- Uses `AsyncRedisSaver` for conversation checkpointing
- Thread IDs follow pattern: `{user_id}:{doc_id}` for scoped retrieval

### Exam Modes
- `EXAM` - Strict proctoring, no hints, timed
- `LEARN` - Interactive, hints allowed, exploratory

### TTS Region Support
- `india` - Google Cloud TTS (Neural2 voices)
- `global` - Deepgram Aura (faster for international users)

## Prisma Schema Notes

Located at `nextjs/prisma/schema.prisma`. Key models:
- `User` - Includes subscription and usage limits inline (no separate tables)
- `Document` - Status: PENDING → PROCESSING → READY/FAILED
- `QuestionPaper` - Generated QP with `questions` JSON field
- `ExamSession` - Links user, document, QP; has `CorrectionReport`
