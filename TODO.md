# VOXAM - TODO List

## 🎯 Current Sprint Focus
**GraphRAG Implementation, UX/UI Improvements, Document Management**

---

## 🚀 High Priority

### 1. GraphRAG & Vector Search
**Files**: `python/ingestion_workflow.py`, `python/retrieval.py`, `python/setup_vector_index.py`

- [x] Run `setup_vector_index.py` to create Neo4j vector index (one-time)
- [ ] Test ingestion pipeline with sample PDF
- [ ] Verify embeddings are generated and stored
- [ ] Test vector search retrieval with sample queries
- [x] Integrate `retrieval.py` into chat agent
- [ ] Add table description generation in `extract_pdf()`

### 1.1 Agentic RAG Chat Agent (NEW)
**Files**: `python/agents/chat_agent.py`, `python/retrieval.py`

- [x] Query Rewriter Node (conditional, handles "tell me more about that")
- [x] Hybrid Search Retriever (Vector + Keyword + RRF fusion)
- [x] RRF score threshold filtering (min_score=0.018)
- [x] Return full `combined_context` instead of truncated text
- [ ] Replace MemorySaver with Redis checkpointer
- [ ] Test full pipeline end-to-end

#### Web Search Fallback (Human-in-the-Loop)
- [ ] Detect when retrieval returns empty/low-score results
- [ ] Return UI flag `needs_web_search: true` to frontend
- [ ] Display prompt: "I couldn't find this in your documents. Search the web?"
- [ ] Add `web_search_approved` state field for user consent
- [ ] Implement Tavily/Google web search tool
- [ ] Generate response with web context + disclaimer
- [ ] Track queries that trigger web search (analytics for "missing content")

---

### 2. Character & Persona System
**Files**: `python/agents/chat_agent.py`, `python/agents/exam_agent.py`

#### Chat Agent Character Prompting
- [ ] Design friendly, helpful tutor personality
- [ ] Add conversational warmth and encouragement
- [ ] Adaptive tone based on student performance
- [ ] Multi-persona support (strict teacher, casual tutor, etc.)

#### Exam Agent Character Prompting
- [ ] Professional but supportive tone
- [ ] Clear, concise question delivery
- [ ] Encouraging feedback in "learn" mode
- [ ] Neutral, objective tone in "exam" mode

---

### 3. Citation & Document Navigation
**Files**: `python/retrieval.py`, `nextjs/app/authenticated/chat/page.tsx`

#### Human-in-the-Loop Citation System
- [ ] Add citation metadata to chat responses
- [ ] Display clickable citation links in chat UI
- [ ] On citation click → open document viewer
- [ ] Highlight cited content block on specific page
- [ ] Show document title + page number in citation badge
- [ ] Side-by-side view: chat on left, document on right

#### UI Components Needed
- [ ] `<CitationBadge>` component (clickable pill with page number)
- [ ] `<DocumentViewer>` component (PDF.js integration)
- [ ] `<HighlightLayer>` for content highlighting
- [ ] Citation popover with preview text

**Note**: Schema already has `page_from`, `page_to`, `doc_id` in ContentBlock ✅

---

### 4. Document Management Simplification
**Files**: `nextjs/app/authenticated/documents/`, `python/api.py`

#### Remove Separate Document Page
- [ ] Delete `documents/page.tsx` (merge into chat)
- [ ] Remove document routes from navigation
- [ ] Update sidebar menu

#### Upload from Chat Interface
- [ ] Add upload button to chat page header
- [ ] Drag & drop zone in chat area
- [ ] Upload progress indicator
- [ ] Auto-start ingestion on upload
- [ ] Show ingestion status (extracting, generating questions, etc.)
- [ ] Success notification with document stats

#### FastAPI Document Endpoints
- [ ] `POST /api/upload-document` - Upload PDF, trigger ingestion
- [ ] `GET /api/documents?user_id=X` - List user's documents
- [ ] `GET /api/documents/:id` - Get document metadata
- [ ] `DELETE /api/documents/:id` - Delete document + cleanup Neo4j
- [ ] `GET /api/documents/:id/content` - Serve PDF for viewer

---

### 5. UI Overhaul - All Pages
**Files**: `nextjs/app/authenticated/*`

#### Global Changes
- [ ] Consistent color scheme across all pages
- [ ] Modern card-based layouts (like exam page)
- [ ] Responsive design for mobile/tablet
- [ ] Loading skeletons for better perceived performance
- [ ] Toast notifications for all actions
- [ ] Dark mode support

#### Chat Page Improvements
- [ ] Message bubbles with citations
- [ ] Document upload zone (drag & drop)
- [ ] Sidebar with document list
- [ ] Citation panel (shows all sources used)
- [ ] Clear chat button
- [ ] Export conversation as PDF/Markdown

#### Exam Page Improvements
- [ ] Add exam list/history in sidebar
- [ ] Quick start from previous exams
- [ ] Card grid layout for exams
- [ ] Filter/sort options (date, status, duration)

---

### 6. Page Structure Simplification
**Files**: `nextjs/app/authenticated/`

#### Consolidate to 2 Main Pages
**Page 1: Chat Interface** (`chat/page.tsx`):
- Left sidebar: Document list + upload
- Main area: Chat messages with citations
- Right sidebar (optional): Document viewer

**Page 2: Voice Exam Interface** (`exam-livekit/page.tsx`):
- Keep current beautiful design ✅
- Add exam list/history in sidebar
- Quick start from previous exams

#### Remove/Archive
- [ ] `documents/page.tsx` → merge into chat
- [ ] `exam/page.tsx` → keep only `exam-livekit/page.tsx`
- [ ] `examlist/page.tsx` → move to sidebar in exam page

---

## 🔐 Authentication & Security

### 7. Authentication Setup
**Files**: `nextjs/lib/auth.ts`, FastAPI middleware

- [ ] Check if Better Auth is already configured
- [ ] Verify JWT token generation
- [ ] Add authentication to all FastAPI routes
- [ ] Implement session management
- [ ] Protected route middleware (Next.js)
- [ ] Alternative: SQLAlchemy + JWT if needed

---

## 🔧 Backend Infrastructure

### 8. Postgres Schema for Exams
**Files**: `nextjs/prisma/schema.prisma`

- [ ] Add `ExamSession` model to Prisma schema
- [ ] Add `Document` model (title, user_id, neo4j_doc_id, status)
- [ ] Run `prisma migrate dev` to create tables
- [ ] Create API routes for exam CRUD operations

---

## 📊 Future Enhancements

### 9. Payment System (Later)
- [ ] Stripe integration setup
- [ ] Pricing tiers (Free, Pro, Enterprise)
- [ ] Checkout flow
- [ ] Usage tracking
- [ ] Subscription management
- [ ] Billing dashboard

### 10. Analytics & Reporting (Later)
- [ ] Track exam completion rates
- [ ] Performance reports
- [ ] Export results as PDF

### 11. Advanced Features (Later)
- [ ] Voice cloning for personalized tutors
- [ ] Multi-language support
- [ ] Adaptive difficulty
- [ ] Mobile app (React Native)

### 12. DSpy Integration (v2)
- [ ] Integrate DSpy for prompt optimization and evaluation
- [ ] Use DSpy to evaluate user exam responses
- [ ] Leverage user's long-term memory for personalized feedback
- [ ] Generate custom prompts per user for adaptive agent behavior
- [ ] Experiment with DSpy's evaluation and tuning workflows

### 13. Exam Correction Agent (Deep Report)
**Files**: `python/agents/correction_agent.py` (new), Postgres schema

A post-exam "Deep Research Agent" that generates detailed correction reports:

#### Core Features
- [ ] **Gap Analysis**: Compare user's spoken answer vs expected answer
- [ ] **What You Got Right**: Highlight correct points in green
- [ ] **What Was Missing**: List missing key concepts
- [ ] **Why It Matters**: Explain why the missed points are important for exams
- [ ] **Resource Links**: Link to specific pages/figures/tables from the source PDF
- [ ] **Practice Questions**: Suggest related questions for reinforcement

#### Data Storage (Postgres)
- [ ] Store exam attempts: `user_id`, `question_id`, `transcript`, `score`, `timestamp`
- [ ] Store correction reports as JSON blob or structured data

#### Historical Analysis (Phase 2)
- [ ] Track performance trends per topic/question over time
- [ ] Show improvement graphs ("Attempt 1: 4/10 → Attempt 3: 8/10")
- [ ] Identify recurring weaknesses across multiple exams
- [ ] Spaced repetition suggestions ("You haven't practiced this in 14 days")

#### UI Components
- [ ] `<CorrectionReport>` component - Detailed feedback view
- [ ] `<PerformanceChart>` - Historical trend visualization
- [ ] `<ResourceCard>` - Clickable links to PDF pages/figures

**Note**: This is a premium feature that justifies subscription pricing. Can run as async background job (30-60s is acceptable for deep analysis).

### 14. Adaptive Exam Agent (Smart Question Selection)
**Files**: `python/agents/exam_agent.py`

Real-time adaptive testing that adjusts difficulty and question type based on student performance:

#### Core Features
- [ ] **Performance Tracking**: Track score per question during exam
- [ ] **Difficulty Adaptation**: If student struggles (avg score < 5), switch to easier questions
- [ ] **Bloom's Taxonomy Scaffolding**: Drop from "analyze" → "understand" → "remember" when struggling
- [ ] **User Voice Commands**: Handle "ask me easier questions" / "I'm ready for harder ones"
- [ ] **Smart Question Pool**: Filter remaining questions by `difficulty` and `bloom_level` fields

#### Adaptation Logic
- [ ] Calculate rolling average of last 3 question scores
- [ ] If avg >= 8: Challenge with harder questions (advanced, analyze/evaluate)
- [ ] If avg >= 5: Maintain current difficulty
- [ ] If avg < 5: Simplify (basic difficulty, remember/understand bloom levels)

#### Voice Command Handling
- [ ] Detect user requests: "easier", "simpler", "too hard", "challenge me"
- [ ] Confirm adaptation: "Sure, let me ask something more manageable..."
- [ ] Gradual return: After 2 correct easier answers, nudge back up

#### Data Needed (Already Available in Redis)
- `difficulty`: basic, intermediate, advanced
- `bloom_level`: remember, understand, apply, analyze, evaluate
- `question_type`: multiple_choice, long_answer
- `expected_time`: For pacing hints

**Note**: This makes voice exams significantly more intelligent than competitors who ask fixed questions in order.

---

## 🐛 Known Issues

- [ ] Redis cleanup might fail if connection drops mid-exam
- [ ] WebRTC connection unstable on poor networks
- [ ] No validation for QP generation parameters
- [ ] No rate limiting on API endpoints

---

## Next Immediate Steps (This Week)

1. **GraphRAG Setup** - Run vector index setup, test ingestion + retrieval
2. **Character Prompting** - Design chat/exam agent personalities
3. **Citation System** - Verify page metadata in Neo4j, plan UI components
4. **UI Consolidation** - Merge documents page into chat interface
5. **Document Upload** - FastAPI endpoints for upload + ingestion
6. **Authentication** - Verify Better Auth or implement JWT
7. **Payment System** - Stripe integration, pricing tiers, subscription management

---

**Last Updated**: November 27, 2025
**Current Sprint**: GraphRAG, Agentic RAG Chat Agent, UX/UI Improvements, Document Management
