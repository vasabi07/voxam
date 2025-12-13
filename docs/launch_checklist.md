# Voxam Christmas Launch Checklist

**Target:** December 25, 2025  
**Today:** December 12, 2025  
**Time Left:** 13 days

---

## Week 1 (Dec 12-18): Core Features

### Day 1-2: Database & Credit System
- [ ] Add Prisma schema (SubscriptionPlan, Subscription, UserCredits, Transaction)
- [ ] Run migrations
- [ ] Create credit check middleware
- [ ] Add usage tracking hooks (voice minutes, chat messages, pages)
- [ ] Free tier limits: 30 min voice, 50 chat, 10 pages

### Day 3-4: Razorpay Integration
- [ ] Create Razorpay account, get API keys
- [ ] Create Plans in Razorpay Dashboard (Starter, Pro, Unlimited)
- [ ] Build subscription API endpoints
- [ ] Implement webhook handler with signature verification
- [ ] Build Pricing Page UI
- [ ] Test full subscription flow

### Day 5-6: Correction Agent
- [ ] Design correction report schema (Pydantic model)
- [ ] Build correction agent with GPT-OSS 120B
- [ ] Generate detailed exam analysis (strengths, weaknesses, score)
- [ ] Store reports in database
- [ ] Create report viewing UI
- [ ] Add to Celery queue for background processing

### Day 7: Voice Exam Battle Testing
- [ ] Test rapid interruptions
- [ ] Test long silences (timeout handling)
- [ ] Test network disconnection/reconnection
- [ ] Test multiple sessions simultaneously
- [ ] Test mode switching (exam ↔ learn)
- [ ] Fix any edge case bugs found

---

## Week 2 (Dec 19-25): Polish & Deploy

### Day 8-9: Celery Workers
- [ ] Set up Celery with Redis broker
- [ ] Move ingestion pipeline to Celery task
- [ ] Move correction agent to Celery task
- [ ] Add progress tracking / status updates
- [ ] Test concurrent ingestion jobs

### Day 10-11: Deployment
- [ ] Set up Hetzner CCX23
- [ ] Configure Docker containers (FastAPI, Redis, Neo4j)
- [ ] Deploy Next.js to Vercel
- [ ] Set up domain + SSL
- [ ] Configure environment variables
- [ ] Set up Uvicorn with 2 workers
- [ ] Test production deployment

### Day 12: Monitoring & Final Testing
- [ ] Add basic logging (errors, usage)
- [ ] Set up health check endpoint
- [ ] Full end-to-end testing on production
- [ ] Load test (10 concurrent users)
- [ ] Fix any production issues

### Day 13: Launch Prep
- [ ] Final pricing/copy review
- [ ] Landing page ready
- [ ] Social media posts prepared
- [ ] Email/WhatsApp to beta users
- [ ] Launch! 🚀

---

## Additional Items (if time permits)

### Nice to Have
- [ ] Update LLMs to GPT-OSS models (cost optimization)
- [ ] Fix CopilotKit rewritten query flash
- [ ] Handwritten notes support (vision fallback)
- [ ] Email notifications (welcome, subscription renewal)
- [ ] Terms of Service / Privacy Policy page
- [ ] Analytics (basic usage dashboard)

### Deferred to v2
- [ ] MCQ mode with data channels
- [ ] Proctoring feature
- [ ] Institution/B2B features
- [ ] Mobile app

---

## Daily Progress Tracker

| Date | Focus | Status |
|------|-------|--------|
| Dec 12 | Credit system schema | |
| Dec 13 | Credit middleware + tracking | |
| Dec 14 | Razorpay setup + Plans | |
| Dec 15 | Razorpay webhooks + API | |
| Dec 16 | Correction agent | |
| Dec 17 | Correction UI + Celery | |
| Dec 18 | Voice exam edge cases | |
| Dec 19 | Celery ingestion | |
| Dec 20 | Celery correction | |
| Dec 21 | Hetzner + Docker setup | |
| Dec 22 | Vercel + domain | |
| Dec 23 | Monitoring + testing | |
| Dec 24 | Final fixes | |
| Dec 25 | 🎄 LAUNCH | |

---

## Blockers / Risks

| Risk | Mitigation |
|------|------------|
| Razorpay account approval delay | Apply TODAY |
| Voice edge cases take longer | Has buffer on Day 7 |
| Deployment issues | Day 12 buffer for fixes |
| Neo4j cloud vs self-hosted | Stick with self-hosted for now |
