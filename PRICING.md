# Voxam Pricing Strategy

## Cost Analysis (Per Unit)

### PDF Ingestion Costs
| Component | Model | Cost |
|-----------|-------|------|
| Question Generation | GPT-4.1 | ~$0.0065/page |
| Image Captioning | GPT-4o-mini | ~$0.0007/page (avg) |
| Embeddings | text-embedding-3-small | ~$0.00003/page |
| **Total per page** | | **~$0.0072/page** |

**Alternative (86% cheaper):**
- DeepSeek-V3 via OpenRouter: ~$0.001/page

### Chat Costs (Per Query)
| Component | Model | Tokens | Cost |
|-----------|-------|--------|------|
| Input (6 msgs + RAG) | GPT-4.1-mini | ~4,250 | $0.0017 |
| Output | GPT-4.1-mini | ~800 | $0.00128 |
| **Total per query** | | | **~$0.003** |

### Voice Exam Costs (Per Minute)
| Component | Provider | Cost |
|-----------|----------|------|
| STT | Deepgram Nova-2 | $0.0043/min |
| TTS | Google Neural2 | ~$0.016/min (100 chars/sec) |
| **Total per minute** | | **~$0.0205/min** |

---

## Pricing Tiers

### 🇮🇳 India Pricing

#### Starter - ₹499/month
| Resource | Included | Our Cost | Margin |
|----------|----------|----------|--------|
| Voice Exam | 120 min | ₹205 | |
| PDF Pages | 150 pages | ₹90 | |
| Chat Queries | 500 | ₹125 | |
| **Total Cost** | | **₹420** | **16%** |

#### Pro - ₹1,499/month
| Resource | Included | Our Cost | Margin |
|----------|----------|----------|--------|
| Voice Exam | 400 min | ₹684 | |
| PDF Pages | 500 pages | ₹300 | |
| Chat Queries | 2,000 | ₹500 | |
| **Total Cost** | | **₹1,484** | **1%** |

*Note: Pro tier margin is thin - consider adjusting limits or using DeepSeek for ingestion*

#### Unlimited - ₹2,999/month
| Resource | Included |
|----------|----------|
| Voice Exam | 1,000 min |
| PDF Pages | 2,000 pages |
| Chat Queries | Unlimited |

---

### 🌍 International Pricing

#### Starter - $12/month
| Resource | Included | Our Cost | Margin |
|----------|----------|----------|--------|
| Voice Exam | 150 min | $3.08 | |
| PDF Pages | 300 pages | $2.16 | |
| Chat Queries | 1,000 | $3.00 | |
| **Total Cost** | | **$8.24** | **31%** |

#### Pro - $29/month
| Resource | Included | Our Cost | Margin |
|----------|----------|----------|--------|
| Voice Exam | 500 min | $10.25 | |
| PDF Pages | 1,000 pages | $7.20 | |
| Chat Queries | 5,000 | $15.00 | |
| **Total Cost** | | **$32.45** | **-12%** |

*Note: Pro tier needs adjustment - reduce chat queries to 3,000 or raise price to $35*

#### Enterprise - $99/month
| Resource | Included |
|----------|----------|
| Voice Exam | 2,000 min |
| PDF Pages | 5,000 pages |
| Chat Queries | Unlimited |
| Priority Support | ✅ |
| Custom Branding | ✅ |

---

## Top-Up Packs (High Margin)

### 🇮🇳 India Top-Ups
| Pack | Amount | Price | Our Cost | Margin |
|------|--------|-------|----------|--------|
| Voice Minutes | +60 min | ₹149 | ₹103 | **31%** |
| Chat Queries | +500 | ₹99 | ₹125 | **-26%** |
| PDF Pages | +100 | ₹79 | ₹60 | **24%** |

*Note: Chat top-up is below cost - increase to ₹149 or reduce to +300 queries*

### 🌍 International Top-Ups
| Pack | Amount | Price | Our Cost | Margin |
|------|--------|-------|----------|--------|
| Voice Minutes | +100 min | $4.99 | $2.05 | **59%** |
| Chat Queries | +1,000 | $4.99 | $3.00 | **40%** |
| PDF Pages | +200 | $2.99 | $1.44 | **52%** |

---

## Infrastructure Costs (Monthly Fixed)

| Service | Tier | Cost |
|---------|------|------|
| Neo4j Aura | Free → Pro | $0 → $65/mo |
| Redis Cloud | Free → Basic | $0 → $5/mo |
| Vercel | Hobby → Pro | $0 → $20/mo |
| Fly.io (FastAPI) | Free → $5 | $0 → $5/mo |
| Cloudflare R2 | Free tier | $0 (first 10GB) |
| LiveKit Cloud | Pay-as-you-go | ~$0.002/min |

**Estimated infrastructure at scale:** $100-200/month for 1,000 users

---

## Cost Optimization Strategies

### 1. Use DeepSeek for Ingestion (86% savings)
```
GPT-4.1: $0.0072/page → DeepSeek-V3: $0.001/page
```

### 2. Cache Frequent Queries
- Redis cache for repeated questions
- Estimated 30-40% hit rate = 30-40% chat cost reduction

### 3. Batch Embeddings
- Already batching in ingestion pipeline
- ~20% cheaper than individual calls

### 4. Tiered Model Selection
- Simple queries → GPT-4.1-mini
- Complex queries → GPT-4.1
- Use classifier to route (adds ~$0.0001/query)

---

## Break-Even Analysis

### India Market
| Tier | Price | Cost | Users for $1000 profit |
|------|-------|------|------------------------|
| Starter | ₹499 | ₹420 | 1,266 users |
| Pro | ₹1,499 | ₹1,484 | 66,667 users |

### International Market
| Tier | Price | Cost | Users for $1000 profit |
|------|-------|------|------------------------|
| Starter | $12 | $8.24 | 266 users |
| Pro | $29 | $32.45 | N/A (loss) |

**Recommendation:** Focus on Starter tier acquisition, upsell via top-ups

---

## Recommended Adjustments

1. **India Pro Tier:** Reduce chat to 1,500 queries OR use DeepSeek for ingestion
2. **International Pro:** Raise to $35 OR reduce chat to 3,000 queries
3. **Chat Top-Up (India):** Increase to ₹149 for +500 queries
4. **Add Annual Plans:** 20% discount = better retention + cash flow

---

## Competitive Positioning

| Feature | Voxam | Competitor A | Competitor B |
|---------|-------|--------------|--------------|
| Voice Exams | ✅ | ❌ | ❌ |
| AI Question Gen | ✅ | ✅ | ❌ |
| GraphRAG Chat | ✅ | ❌ | ✅ |
| Price (India) | ₹499 | ₹999 | ₹699 |

**Unique Value:** Voice-first exam experience with AI-generated questions from your own materials.

---

*Last Updated: November 28, 2025*
