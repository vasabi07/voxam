# Voxam Pricing Analysis (Final - Dec 2025)

## Tech Stack

| Service | Provider | Rate |
| :--- | :--- | :--- |
| **STT** | Deepgram Flux | $0.0077/min |
| **TTS (Expressive)**| Cartesia Sonic | $38-$65/1M chars (~$0.04/min) |
| **TTS (Fast)** | Deepgram Aura 2 | $30/1M chars (~$0.03/min) |
| **TTS (Value)** | Google Neural2 | $16/1M chars (~$0.016/min) |
| **Voice LLM** | Groq (free tier) | $0 |
| **Ingestion** | Gemini 2.5 Flash-Lite | $0.10/1M input, $0.40/1M output |
| **Chat** | Gemini 2.5 Flash-Lite | $0.10/1M input, $0.40/1M output |
| **LiveKit** | Audio transport | $0.0005/min + $0.12/GB (50GB free) |

---

## Pricing Model: Prepaid Packs (Not Subscription)

- One-time payment via Razorpay/Stripe
- Minutes valid for X days
- Phone OTP verification required

---

## �🇳 India Plans

### Starter (₹299 / 90 min)

| Component | Usage | Calculation | Cost (₹) |
| :--- | :--- | :--- | :--- |
| STT (Deepgram Flux) | 90 min | 90 × $0.0077 | ₹59 |
| TTS (Gemini 2.5 Flash) | 45 min (50%) | 45 × $0.015 | ₹57 |
| LiveKit | 90 min | 90 × $0.0005 | ₹4 |
| Voice LLM (Groq) | ~100 turns | Free tier | ₹0 |
| Ingestion (50 pg) | ~25K tokens | Gemini Flash-Lite | ₹1 |
| Chat (unlimited) | ~500 queries | Gemini Flash-Lite | ₹2 |
| Razorpay (2%) | | 2% of ₹299 | ₹6 |
| **Total Cost** | | | **₹129** |
| **Revenue** | | | **₹299** |
| **Profit** | | | **₹170** |
| **Margin** | | | **57%** ✅ |

---

### Standard (₹599 / 250 min)

| Component | Usage | Cost (₹) |
| :--- | :--- | :--- |
| STT (Deepgram) | 250 min | ₹163 |
| TTS (Gemini) | 125 min | ₹159 |
| LiveKit | 250 min | ₹11 |
| Voice LLM | Free | ₹0 |
| Ingestion (200 pg) | | ₹4 |
| Chat | | ₹5 |
| Razorpay (2%) | | ₹12 |
| **Total Cost** | | **₹354** |
| **Revenue** | | **₹599** |
| **Profit** | | **₹245** |
| **Margin** | | **41%** ✅ |

---

### Achiever (₹1,099 / 450 min)

| Component | Usage | Cost (₹) |
| :--- | :--- | :--- |
| STT (Deepgram Aura) | 450 min | ₹294 |
| TTS (Deepgram Aura 2) | 225 min | ₹459 |
| LiveKit | 450 min | ₹19 |
| Voice LLM | Free | ₹0 |
| Ingestion/Chat | | ₹20 |
| Razorpay (2%) | | ₹22 |
| **Total Variable Cost** | | **₹814** |
| **Revenue** | | **₹1,099** |
| **Gross Profit** | | **₹285** |
| **Gross Margin** | | **26%** ⚠️ |

---

### Top-Up (₹199 / 60 min)

| Component | Usage | Cost (₹) |
| :--- | :--- | :--- |
| STT (Deepgram) | 60 min | ₹39 |
| TTS (Gemini) | 30 min | ₹38 |
| LiveKit | 60 min | ₹3 |
| Razorpay (2%) | | ₹4 |
| **Total Cost** | | **₹84** |
| **Revenue** | | **₹199** |
| **Profit** | | **₹115** |
| **Margin** | | **58%** ✅ |

---

## 🌍 Global Plans (US/EU/UK)

### Standard ($9.99 / 120 min)

| Component | Usage | Cost ($) |
| :--- | :--- | :--- |
| STT (Deepgram) | 120 min | $0.92 |
| TTS (Gemini) | 60 min | $0.90 |
| LiveKit | 120 min | $0.06 |
| Voice LLM | Free | $0 |
| Ingestion | Unlimited avg 100pg | $0.02 |
| Chat | Unlimited | $0.02 |
| Stripe (3%) | | $0.30 |
| **Total Cost** | | **$2.22** |
| **Revenue** | | **$9.99** |
| **Profit** | | **$7.77** |
| **Margin** | | **78%** ✅ |

---

### Pro Scholar ($19.99 / 300 min)

| Component | Usage | Cost ($) |
| :--- | :--- | :--- |
| STT (Deepgram) | 300 min | $2.31 |
| TTS (Gemini) | 150 min | $2.25 |
| LiveKit | 300 min | $0.15 |
| Voice LLM | Free | $0 |
| Ingestion | Unlimited | $0.05 |
| Chat | Unlimited | $0.05 |
| Stripe (3%) | | $0.60 |
| **Total Cost** | | **$5.41** |
| **Revenue** | | **$19.99** |
| **Profit** | | **$14.58** |
| **Margin** | | **73%** ✅ |

---

### Top-Up ($5.99 / 60 min)

| Component | Usage | Cost ($) |
| :--- | :--- | :--- |
| STT (Deepgram) | 60 min | $0.46 |
| TTS (Gemini) | 30 min | $0.45 |
| LiveKit | 60 min | $0.03 |
| Stripe (3%) | | $0.18 |
| **Total Cost** | | **$1.12** |
| **Revenue** | | **$5.99** |
| **Profit** | | **$4.87** |
| **Margin** | | **81%** ✅ |

---

## Free Tier (One-Time Trial)

| Feature | Limit |
| :--- | :--- |
| Voice Exam | 10 min (once) |
| Documents | 1 PDF (20pg) |
| Chat | 10 messages |
| Report | Summary only (blurred) |
| Validity | 7 days |
| **Cost per user** | ~₹17 ($0.20) |

---

## Summary

| Plan | Price | Minutes | Cost | Margin |
| :--- | :--- | :--- | :--- | :--- |
| 🇮🇳 **Starter** | ₹299 | 90 | ₹129 | **57%** ✅ |
| 🇮🇳 **Standard** | ₹599 | 250 | ₹354 | **41%** ✅ |
| 🇮🇳 **Achiever** | ₹1,099 | 500 | ₹707 | **36%** ✅ |
| 🇮🇳 **Top-Up** | ₹199 | 60 | ₹84 | **58%** ✅ |
| 🌍 **Standard** | $9.99 | 120 | $2.22 | **78%** ✅ |
| 🌍 **Pro** | $19.99 | 300 | $5.41 | **73%** ✅ |
| 🌍 **Top-Up** | $5.99 | 60 | $1.12 | **81%** ✅ |

---

## TTS Provider Comparison

| Provider | Model | Latency (TTFB) | Quality | Cost (per 1M chars) |
| :--- | :--- | :--- | :--- | :--- |
| **Cartesia** | Sonic | **~100ms** | Ultra-Expressive | **$38-$65** |
| **Deepgram** | Aura 2 | ~250ms | Clear, fast | $30 |
| **Google** | Neural2 | ~600ms | Standard | $16 |
| **OpenAI** | tts-1 | ~800ms | Natural | $15 |
| **Gemini** | 2.5 Flash | ~4s ❌ | High | $10 (audio tokens) |

> 💡 **Recommendation:** For V1 Launch, **Deepgram Aura 2** is the best balance of price ($30) and latency (~250ms). If we want "Wow" factor and have budget, **Cartesia** is the gold standard for sub-100ms lifelike voice.

---

## Key Assumptions

1. **TTS usage = 50%** of session time (AI speaks half, student speaks half)
2. **Gemini 2.5 Flash TTS**: 25 audio tokens/second → 1M tokens = 667 minutes
1.  **TTS usage = 50%** of session time (AI speaks half, student speaks half)
2.  **Gemini 2.5 Flash TTS**: 25 audio tokens/second → 1M tokens = 667 minutes
3.  **Groq free tier** for voice LLM (Llama 3.1 70B)
4.  **LiveKit**: 50GB free bandwidth covers ~100K+ sessions
5.  **₹85 = $1 USD** conversion rate

---

## Infrastructure Costs (Fixed Monthly)

| Component | Monthly Cost |
| :--- | :--- |
| EzerHost SM 200 VPS (Delhi NCR) | ₹1,769 |
| Neo4j Aura (Free tier) | ₹0 |
| R2 Storage (Free tier) | ₹0 |
| **Total Fixed** | **₹1,769/mo** |

**Break-even:** ~10 India Starter users OR ~2 Global users

---

## Operating Costs (The "Hidden" Stack)

As we scale, these fixed costs apply regardless of how many minutes are used.

| Service | Tier | Monthly Cost | Notes |
| :--- | :--- | :--- | :--- |
| Service | Tier | Monthly Cost | Notes |
| :--- | :--- | :--- | :--- |
| **Hetzner CCX23** | 4 vCPU / 16GB | ₹2,200 | API, Redis, Neo4j, Workers |
| **Vercel** | **Free** | ₹0 | Supports V1 traffic (Hobby tier) |
| **Supabase** | **Free** | ₹0 | Up to 50K users (Free tier) |
| **Neo4j DB** | Self-Hosted | ₹0 | Included in CCX23 cost |
| **Total Fixed Costs**| | **~₹2,200/mo** | |

### Break-even Analysis (Net Profit)
To cover the **₹2,200** monthly overhead + variable costs:

*   **India Only:** Need **~16 Starter users/mo**.
*   **Global Only:** Need **~2 Pro Scholar users/mo**.

> [!IMPORTANT]
> **Conclusion:** The India plans (especially 450m Achiever) are "User Acquisition" tools. The **Global plans** are where the real cash to pay for Vercel/Supabase comes from. **V1 Strategy:** Use Deepgram credits to offset variable costs, and prioritize Global SEO to balance the ₹7,100/mo overhead.

---

## True Value: Groq Free Tier Savings

### LLM Cost If Paid (Groq Llama 3.1 70B)

| Rate | Value |
| :--- | :--- |
| Input tokens | $0.59/1M tokens |
| Output tokens | $0.79/1M tokens |

### Per 90-min Session (Starter Plan)

| Component | Tokens | Cost |
| :--- | :--- | :--- |
| Input (~100 turns × 500 tokens) | 50K tokens | $0.03 |
| Output (~100 turns × 200 tokens) | 20K tokens | $0.02 |
| **Total LLM Cost** | | **$0.05 (₹4)** |

### If Using Paid LLM (Without Free Tier)

| Plan | Current Cost | +LLM Cost | New Total | New Margin |
| :--- | :--- | :--- | :--- | :--- |
| 🇮🇳 Starter (90 min) | ₹129 | +₹4 | ₹133 | **55%** |
| 🇮🇳 Standard (250 min) | ₹354 | +₹11 | ₹365 | **39%** |
| 🇮🇳 Achiever (500 min) | ₹707 | +₹22 | ₹729 | **34%** |
| 🌍 Standard (120 min) | $2.22 | +$0.07 | $2.29 | **77%** |
| 🌍 Pro (300 min) | $5.41 | +$0.17 | $5.58 | **72%** |

### Free Tier Savings Summary

| Users | Sessions/mo | Groq Savings |
| :--- | :--- | :--- |
| 100 | ~500 | **$25/mo** (₹2,125) |
| 500 | ~2,500 | **$125/mo** (₹10,625) |
| 1,000 | ~5,000 | **$250/mo** (₹21,250) |

> 💡 **Insight:** Groq's free tier is extremely generous. Even at paid rates, LLM cost is only ~3% of total cost. The real expense is STT (40%) + TTS (45%).
