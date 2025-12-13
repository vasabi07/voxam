# Voxam Pricing Analysis

## Pricing Tiers

| Feature | 🌱 Starter (₹299) | ⭐ Pro (₹599) | 🚀 Unlimited (₹999) |
|---------|-------------------|---------------|---------------------|
| Voice Exam | 60 min | 150 min | **Unlimited** |
| Chat Queries | 200 | 500 | **Unlimited** |
| Document Pages | 50 pages | 150 pages | 300 pages |
| Correction Reports | 3 | 10 | **Unlimited** |
| Priority Support | ❌ | ❌ | ✅ |
| **Price (USD)** | ~$3.57 | ~$7.15 | ~$11.95 |

---

## Tier Cost Analysis

### 🌱 Starter Tier (₹299/month)

| Category | Usage | Cost |
|----------|-------|------|
| Voice Exam | 60 min | $0.54 |
| Chat | 200 queries | $0.02 |
| Ingestion | 50 pages (~17 chunks) | $0.05 |
| Correction | 3 reports | $0.02 |
| Infrastructure | @100 users | $0.37 |
| **Total Cost** | | **$1.00** |
| **Revenue** | | $3.57 |
| **Margin** | | **72%** ✅ |

---

### ⭐ Pro Tier (₹599/month) - RECOMMENDED

| Category | Usage | Cost |
|----------|-------|------|
| Voice Exam | 150 min | $1.35 |
| Chat | 500 queries | $0.05 |
| Ingestion | 150 pages (~50 chunks) | $0.16 |
| Correction | 10 reports | $0.05 |
| Infrastructure | @100 users | $0.37 |
| **Total Cost** | | **$1.98** |
| **Revenue** | | $7.15 |
| **Margin** | | **72%** ✅ |

#### Pro Tier - Detailed API Breakdown

| Service | Provider | Rate | Usage | Cost |
|---------|----------|------|-------|------|
| LiveKit | LiveKit | $0.0005/min × 2 | 300 min | $0.15 |
| STT | Deepgram Flux | $0.0077/min | 75 min | $0.58 |
| TTS | Google Neural2 | $16/1M chars | 37.5K chars | $0.60 |
| Voice LLM | Cerebras Llama 70B | $0.60/1M | 75 exchanges | $0.02 |
| Chat LLM | GPT-OSS 20B | $0.03/$0.14 | 500 queries | $0.04 |
| Question Gen | GPT-OSS 120B | $0.09/$0.45 | 50 chunks | $0.10 |
| Vision | GPT-4o-mini | $0.15/$0.60 | 20 images | $0.05 |
| Correction | GPT-OSS 120B | $0.09/$0.45 | 10 reports | $0.05 |
| Embeddings | OpenAI | $0.02/1M | - | $0.02 |

---

### 🚀 Unlimited Tier (₹999/month)

| Category | Est. Usage | Cost |
|----------|------------|------|
| Voice Exam | ~300 min | $2.70 |
| Chat | ~1000 queries | $0.10 |
| Ingestion | 300 pages (~100 chunks) | $0.32 |
| Correction | ~20 reports | $0.10 |
| Infrastructure | @100 users | $0.37 |
| **Total Cost** | | **$3.59** |
| **Revenue** | | $11.95 |
| **Margin** | | **70%** ✅ |

> ⚠️ Unlimited assumes average power user. Heavy users may reduce margin to 50-60%.

---

## Model Selection

| Use Case | Model | Provider |
|----------|-------|----------|
| Voice Exam | Llama 3.1 70B | Cerebras |
| Voice STT | Flux Nova-3 | Deepgram |
| Voice TTS | Neural2 | Google Cloud |
| Chat | GPT-OSS 20B | OpenAI |
| Question Gen | GPT-OSS 120B | OpenAI |
| Correction | GPT-OSS 120B | OpenAI |
| Vision | GPT-4o-mini | OpenAI |

---

## Infrastructure (Hetzner CCX23)

| Item | Cost/Month |
|------|------------|
| Server (4 vCPU, 16GB) | €24 (~$26) |
| Backups | €5 (~$5) |
| Load Balancer | €5 (~$5.50) |
| **Total** | **~$36.50** |

---

## Revenue Projections (Mixed Tiers)

Assuming: 40% Starter, 45% Pro, 15% Unlimited

| Users | Starter | Pro | Unlimited | Revenue | Cost | Profit |
|-------|---------|-----|-----------|---------|------|--------|
| 100 | 40 | 45 | 15 | $644 | $193 | **$451** |
| 500 | 200 | 225 | 75 | $3,220 | $965 | **$2,255** |
| 1000 | 400 | 450 | 150 | $6,440 | $1,930 | **$4,510** |

---

## Comparison: Before vs After

| Metric | Before (GPT-4.1) | After (Optimized) |
|--------|------------------|-------------------|
| Pro Tier Cost | ~$5.50 | $1.98 |
| Pro Tier Margin | ~23% | **72%** |
| Break-even | ~50 users | **10 users** |
