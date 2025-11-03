# VOXAM - TODO List

## 🎯 Core Features Status

### ✅ Completed
- [x] Exam Agent with two modes (exam/learn)
- [x] QP Agent workflow (Neo4j → Redis)
- [x] WebRTC voice communication
- [x] Redis storage for QP and conversation state
- [x] Automatic cleanup on exam completion
- [x] Mode selection UI (frontend)

---

## 🚀 Priority Tasks

### 1. Create Exam Form Logic
**File**: `nextjs/app/authenticated/examlist/page.tsx`

- [ ] Connect form to `/create-qp` endpoint
- [ ] Handle "Now" vs "Later" scheduling properly
- [ ] Show loading state during QP generation
- [ ] Display success/error messages
- [ ] Redirect to exam page for "Now" exams
- [ ] Store scheduled exams in list view
- [ ] Add form validation (required fields, min/max values)

**Dependencies**: Backend `/create-qp` endpoint, Postgres schema

---

### 2. Postgres Integration with Prisma
**Files**: `nextjs/prisma/schema.prisma`, `nextjs/app/api/exams/route.ts`

#### Schema Design
```prisma
model ExamSession {
  id            Int       @id @default(autoincrement())
  userId        Int
  title         String
  qpId          String    @unique
  threadId      String    @unique
  mode          String    @default("exam") // "exam" | "learn"
  
  // Exam parameters
  duration      Int
  numQuestions  Int?
  questions     Json      // Store full questions array
  
  // Scheduling
  scheduling    String    // "now" | "later"
  scheduledFor  DateTime?
  
  // Status tracking
  status        String    @default("scheduled") // "scheduled" | "in_progress" | "completed"
  
  // Timestamps
  createdAt     DateTime  @default(now())
  startedAt     DateTime?
  completedAt   DateTime?
  
  // Relations
  user          User      @relation(fields: [userId], references: [id])
  
  @@index([userId])
  @@index([status])
  @@index([qpId])
}
```

#### Tasks
- [ ] Add `ExamSession` model to Prisma schema
- [ ] Run `prisma migrate dev` to create tables
- [ ] Create API route: `POST /api/exams` (save exam metadata)
- [ ] Create API route: `GET /api/exams?user_id=X` (list user's exams)
- [ ] Create API route: `PATCH /api/exams/:id` (update status)
- [ ] Update `/create-qp` to return questions to frontend
- [ ] Frontend saves questions to Postgres via API
- [ ] Add error handling for database failures

**Files to create**:
- `nextjs/app/api/exams/route.ts`
- `nextjs/app/api/exams/[id]/route.ts`

---

### 3. Payment System Integration
**Files**: `nextjs/app/api/stripe/`, `nextjs/components/pricing.tsx`

#### Features Needed
- [ ] Stripe integration setup
- [ ] Pricing tiers:
  - Free: 5 exams/month
  - Pro: Unlimited exams, advanced features
  - Enterprise: Team accounts, analytics
- [ ] Checkout flow
- [ ] Webhook for payment confirmation
- [ ] Update user subscription status in database
- [ ] Enforce exam limits based on subscription
- [ ] Usage tracking (exams created/completed)
- [ ] Billing dashboard

**Schema Addition**:
```prisma
model Subscription {
  id            Int       @id @default(autoincrement())
  userId        Int       @unique
  tier          String    @default("free") // "free" | "pro" | "enterprise"
  stripeCustomerId String?
  stripeSubscriptionId String?
  examsUsed     Int       @default(0)
  examsLimit    Int       @default(5)
  periodStart   DateTime
  periodEnd     DateTime
  status        String    @default("active")
  
  user          User      @relation(fields: [userId], references: [id])
}
```

**Dependencies**: Stripe account, API keys

---

### 4. Time Management & Exam Duration
**Files**: `python/exam_agent.py`, `nextjs/app/authenticated/exam/page.tsx`

#### Backend (Python)
- [ ] Add timer state to LangGraph `State` class
- [ ] Create `check_time_remaining` tool
- [ ] Add time warnings at 50%, 75%, 90% completion
- [ ] Auto-submit exam when time expires
- [ ] Send time updates via data channel

#### Frontend (Next.js)
- [ ] Display countdown timer in UI
- [ ] Show time warnings (color changes, alerts)
- [ ] Disable exam controls when time expires
- [ ] Auto-submit on timeout
- [ ] Store duration in exam metadata

**New State Fields**:
```python
class State(MessagesState):
    thread_id: str
    qp_id: str
    current_index: int = 0
    mode: Literal["exam", "learn"] = "exam"
    duration_minutes: int = 60  # NEW
    start_time: Optional[float] = None  # NEW (Unix timestamp)
```

---

### 5. Data Channel for Question Display
**Files**: `python/api.py`, `nextjs/app/authenticated/exam/page.tsx`

#### Current Issue
- Questions/options only transmitted via voice
- Need visual display for better UX

#### Implementation
- [ ] Set up WebRTC data channel in Python backend
- [ ] Set up data channel listener in Next.js frontend
- [ ] Send structured question data:
  ```json
  {
    "type": "question",
    "index": 0,
    "text": "What is photosynthesis?",
    "context": "...",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "question_type": "multiple_choice"
  }
  ```
- [ ] Display question text in UI
- [ ] Show options for multiple choice questions
- [ ] Highlight current question
- [ ] Show answer progress (X/Y questions answered)

**Files to modify**:
- `python/api.py` (add data channel setup)
- `nextjs/app/authenticated/exam/page.tsx` (add data channel handler)

---

### 6. Question Format Verification
**Files**: `python/qp_agent.py`, Neo4j database

#### Verify Current Storage
- [ ] Check if `store_redis` node stores options
- [ ] Verify Neo4j question schema includes options
- [ ] Test multiple_choice question format

#### Expected Format
```json
{
  "question_id": "q1",
  "text": "What is photosynthesis?",
  "context": "Plants convert light energy...",
  "question_type": "multiple_choice",
  "options": [
    "A) Respiration process",
    "B) Light to chemical energy conversion",
    "C) Water absorption",
    "D) Root growth"
  ],
  "correct_answer": "B",
  "difficulty": "intermediate",
  "bloom_level": "understand"
}
```

#### Tasks
- [ ] Inspect `qp_agent.py` `fetch_content` node
- [ ] Verify Neo4j query includes options
- [ ] Update `group_questions` if needed
- [ ] Test QP generation with multiple choice questions
- [ ] Update exam agent tools to handle options
- [ ] Add option display logic in frontend

---

### 7. Voice UI Components (ElevenLabs) ✅
**Files**: `nextjs/components/ui/`, `nextjs/app/authenticated/exam/page.tsx`

#### Integration
- [x] Install ElevenLabs UI package: `npx shadcn@latest add https://ui.elevenlabs.io/r/all.json`
- [x] Replace basic voice controls with ElevenLabs components
- [x] Add Orb visualization (animated sphere that reacts to voice)
- [x] Add voice activity indicator (talking/listening states)
- [x] Add mute/unmute button
- [x] Remove debug logs from UI (console only now)
- [x] Add connection status badge
- [x] Beautiful gradient UI with cards
- [x] **Intelligent turn-taking** with LLM-based completion detection

**Components Added**:
- `components/ui/orb.tsx` - 3D animated voice visualizer
- `components/ui/bar-visualizer.tsx` - Audio waveform
- `components/ui/live-waveform.tsx` - Real-time audio visualization
- `components/ui/conversation.tsx` - Chat-style conversation display
- `components/ui/voice-button.tsx` - Voice control buttons
- Plus 9 more ElevenLabs components

**UI Features**:
- ✅ Animated Orb changes color based on mode (blue=exam, green=learn)
- ✅ Shows agent state: Agent Speaking → Your Turn → You're Speaking
- ✅ Clean modern interface with shadcn/ui cards
- ✅ Responsive grid layout (2 columns on desktop)
- ✅ Connection status badges
- ✅ Progress tracking UI
- ✅ Instructions panel with mode-specific tips
- ✅ **Automatic turn-taking** (no manual submit button)
- ✅ **GPT-4o-mini checks answer completion** (intelligent, not time-based)

---

## 🔧 Optimization Tasks

### 8. Agent Performance
**File**: `python/exam_agent.py`

- [ ] Add caching for frequently accessed questions
- [ ] Optimize Redis JSON queries (use JSONPath)
- [ ] Add connection pooling for Redis
- [ ] Monitor LLM token usage
- [ ] Add retry logic for failed tool calls
- [ ] Implement rate limiting
- [ ] Add telemetry/logging with timestamps

---

### 9. Error Handling
**Files**: Multiple

- [ ] Handle Redis connection failures
- [ ] Handle QP not found in Redis (load from Postgres)
- [ ] Handle WebRTC connection drops
- [ ] Handle audio device errors
- [ ] Add user-friendly error messages
- [ ] Implement automatic retry mechanisms
- [ ] Log errors to monitoring service

---

## 📊 Future Enhancements

### 10. Analytics & Reporting
- [ ] Track exam completion rates
- [ ] Track average scores
- [ ] Track time spent per question
- [ ] Generate performance reports
- [ ] Export exam results as PDF
- [ ] Show historical trends

### 11. Multi-User Support
- [ ] Authentication with Better Auth
- [ ] User roles (student, teacher, admin)
- [ ] Exam sharing between users
- [ ] Class/group management
- [ ] Teacher dashboard

### 12. Advanced Features
- [ ] Voice cloning for personalized tutors
- [ ] Multi-language support
- [ ] Offline mode
- [ ] Mobile app (React Native)
- [ ] Proctoring features (optional)
- [ ] Adaptive difficulty (change based on performance)

---

## 🐛 Known Issues

- [x] ~~Submit Answer button not working~~ - **FIXED**: Replaced with automatic turn-taking
- [x] ~~Agent interrupting user during speech~~ - **FIXED**: Auto-submit after 3s silence
- [x] ~~Audio getting cut off~~ - **FIXED**: Proper audio state management
- [ ] Redis cleanup might fail if connection drops mid-exam
- [ ] WebRTC connection unstable on poor networks
- [ ] No validation for QP generation parameters
- [ ] No rate limiting on API endpoints
- [ ] Mode field not persisted in database yet

---

## 📝 Documentation Needed

- [ ] API documentation (endpoints, payloads)
- [ ] Database schema documentation
- [ ] Deployment guide
- [ ] Environment variables guide
- [ ] Testing guide
- [ ] User manual

---

## 🔒 Security Tasks

- [ ] Add authentication to all API routes
- [ ] Validate user owns exam before starting
- [ ] Sanitize user inputs
- [ ] Add CORS configuration
- [ ] Secure WebSocket connections (wss://)
- [ ] Add rate limiting
- [ ] Encrypt sensitive data in database

---

## 🧪 Testing

- [ ] Unit tests for QP Agent
- [ ] Unit tests for Exam Agent
- [ ] Integration tests for WebRTC flow
- [ ] E2E tests for exam creation → completion
- [ ] Load testing for concurrent exams
- [ ] Test Redis failure scenarios
- [ ] Test payment flow

---

## Next Immediate Steps (This Week)

1. **Verify Question Format** - Check if options are stored in Neo4j/Redis
2. **Create Exam Form Logic** - Connect frontend to backend
3. **Postgres Schema** - Add ExamSession model and migrate
4. **Data Channel** - Set up question display in UI
5. **Time Management** - Add countdown timer

---

**Last Updated**: December 17, 2024
**Current Sprint**: Core Features & Postgres Integration
