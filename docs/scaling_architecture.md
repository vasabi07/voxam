# Voxam Scaling Architecture

## Current Connection Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PER VOICE EXAM SESSION                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Student Browser                     Your Server (FastAPI/Uvicorn)      │
│   ┌───────────────┐                   ┌──────────────────────────────┐  │
│   │               │──WebRTC──────────▶│  LiveKit SDK (rtc.Room)      │  │
│   │   LiveKit     │                   │  ┌────────────────────────┐  │  │
│   │   Client      │                   │  │ WebSocket to LiveKit   │──┼──┼─▶ LiveKit Cloud
│   │               │                   │  │ Cloud (audio relay)    │  │  │
│   └───────────────┘                   │  └────────────────────────┘  │  │
│                                       │                              │  │
│                                       │  ┌────────────────────────┐  │  │
│                                       │  │ WebSocket to Deepgram  │──┼──┼─▶ Deepgram API
│                                       │  │ (STT streaming)        │  │  │
│                                       │  └────────────────────────┘  │  │
│                                       │                              │  │
│                                       │  ┌────────────────────────┐  │  │
│                                       │  │ HTTP to Google TTS     │──┼──┼─▶ Google Cloud
│                                       │  │ (sync per sentence)    │  │  │
│                                       │  └────────────────────────┘  │  │
│                                       │                              │  │
│                                       │  ┌────────────────────────┐  │  │
│                                       │  │ Redis connection       │──┼──┼─▶ Redis
│                                       │  │ (checkpointing)        │  │  │
│                                       │  └────────────────────────┘  │  │
│                                       └──────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Connections Per Session

| Connection Type | Protocol | Duration | Count per Session |
|-----------------|----------|----------|-------------------|
| LiveKit (agent) | WebSocket | Full session | 1 |
| Deepgram STT | WebSocket | Full session | 1 |
| Google TTS | HTTP | Per sentence | ~50-100 requests |
| Redis | TCP | Persistent | Shared pool |
| Neo4j | TCP | On-demand | Query-time only |

**Per concurrent session: 2 persistent WebSockets + HTTP bursts**

---

## Server Resource Consumption

### Per Voice Session

| Resource | Usage | Notes |
|----------|-------|-------|
| Memory | ~50-100 MB | Audio buffers + LLM context |
| File Descriptors | 4-6 | WebSockets + connections |
| CPU | 5-10% (burst) | TTS processing, audio encoding |
| Bandwidth | ~100 kbps | Bidirectional audio |

### Hetzner CCX23 Limits (4 vCPU, 16GB RAM)

| Resource | Limit | Sessions Supported |
|----------|-------|-------------------|
| RAM | 16 GB | ~100-150 concurrent |
| File Descriptors | 65,536 (default) | ~10,000+ sessions |
| CPU | 4 cores | ~40-60 concurrent |
| Network | 1 Gbps | ~1000+ audio streams |

**Bottleneck: CPU** (TTS generation is CPU-intensive)

---

## Concurrent User Estimates

| Scale | Concurrent Sessions | Peak Load Assumption | CCX23 Status |
|-------|---------------------|---------------------|--------------|
| 50 users | 5-10 | 10-20% concurrent | ✅ Easy |
| 100 users | 10-20 | 10-20% concurrent | ✅ Fine |
| 500 users | 50-100 | 10-20% concurrent | ⚠️ Near limit |
| 1000 users | 100-200 | 10-20% concurrent | ❌ Need upgrade |

> Assumption: Not all users use voice exam simultaneously. Peak = 10-20% of active users.

---

## Scaling Strategy by Stage

### Stage 1: 0-100 Users (Current)

```
┌─────────────────────────────────────┐
│         Single CCX23 Server         │
│    FastAPI + Uvicorn (4 workers)    │
│         ~20 concurrent OK           │
└─────────────────────────────────────┘
```

**No changes needed.**

---

### Stage 2: 100-500 Users

```
┌─────────────────────────────────────┐
│         Upgrade to CCX33            │
│      (8 vCPU, 32GB RAM)             │
│        ~50-80 concurrent            │
└─────────────────────────────────────┘
└─────────────────────────────────────┘
          Cost: ~₹2,200/mo (€24.49)
```

**Changes:**
- Upgrade Hetzner server
- Increase Uvicorn workers to 8

---

### Stage 3: 500-2000 Users

```
┌──────────────────────────────────────────────────────────┐
│                    Load Balancer                          │
│                    (Hetzner LB)                           │
└────────────────┬─────────────────┬───────────────────────┘
                 │                 │
    ┌────────────▼─────┐  ┌────────▼────────┐
    │   API Server 1   │  │   API Server 2   │
    │   (CCX23)        │  │   Voice Sessions │
    └──────────────────┘  └──────────────────┘
                 │                 │
                 └────────┬────────┘
                          │
              ┌───────────▼───────────┐
              │    Managed Redis      │
              │    (shared state)     │
              └───────────────────────┘
                          │
              ┌───────────▼───────────┐
              │    Self-Hosted Neo4j  │
              │    (In-VPS / Docker)  │
              └───────────────────────┘
```

**Changes:**
- Add load balancer (€5/month)
- Run 2+ API servers
- Use managed Redis (or self-hosted with persistence)
- Sticky sessions for voice (room-based routing)

---

### Stage 4: 2000+ Users

```
┌──────────────────────────────────────────────────────────────┐
│                      Load Balancer                            │
└────────┬─────────────┬─────────────┬─────────────┬───────────┘
         │             │             │             │
   ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
   │  API 1    │ │  API 2    │ │  API 3    │ │  API 4    │
   └───────────┘ └───────────┘ └───────────┘ └───────────┘
         │             │             │             │
         └─────────────┴─────────────┴─────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
       ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
       │   Redis     │ │   Neo4j     │ │  Postgres   │
       │   Cluster   │ │   Cluster   │ │   (Supabase)│
       └─────────────┘ └─────────────┘ └─────────────┘
```

**Changes:**
- Kubernetes or multi-node deployment
- Redis cluster for high availability
- Neo4j managed cloud
- Consider self-hosting LiveKit server

---

## External Service Limits

| Service | Free/Dev Limit | Your Current Plan | Scale Concern |
|---------|----------------|-------------------|---------------|
| **LiveKit Cloud** | 10K participant-min/month | Pay-as-you-go | No limit |
| **Deepgram** | $200 credit | Pay-as-you-go | No limit |
| **Google TTS** | 4M chars/month free | Pay-as-you-go | No limit |
| **Supabase** | 50K MAU free | Free tier | May need upgrade at 500+ |
| **Redis** | Local instance | Self-hosted | Need managed at scale |

---

## Quick Actions for Each Scale

| Scale | Action | Monthly Cost |
|-------|--------|--------------|
| **0-100** | CCX23 (DBs + API) | ~₹2,200 |
| **100-500** | Add Vercel/Supabase Pro | ~₹6,000 |
| **500-1000** | Add 2nd server + LB | ~₹10,500 |
| **1000-2500** | 3-4 servers + managed Redis | €200 |
| **2500+** | Consider Kubernetes | €300+ |

---

## Summary

| Metric | Current Capacity | Bottleneck |
|--------|------------------|------------|
| Concurrent voice sessions | ~20-40 | CPU (TTS) |
| Total users supported | ~200-400 | Peak concurrency |
| First scaling point | ~500 users | Server upgrade |
| Horizontal scaling point | ~1000 users | Load balancer |
| **GPU Switch Point** | **~200-500 Paid MAU**| **Self-host Orpheus 3B** |

---

## Future: GPU Inference Scaling (Self-Hosted TTS)

When you reach **~200-500 paid MAU**, switching from Deepgram/Cartesia to self-hosted **Orpheus 3B** becomes highly profitable.

### GPU Capacity Estimates (Orpheus 3B)

| Hardware | Monthly Cost | Concurrent Sessions | MAU Capacity |
| :--- | :--- | :--- | :--- |
| **RTX 4090 / L4** | ~$100 - $120 | ~15 - 20 | **750 - 1,500** |
| **2x RTX 4090** | ~$220 | ~30 - 40 | **1,500 - 3,000** |

*Calculation: 90-min session with 45-min TTS. At 10x real-time speed, one GPU is actually "busy" for only 4.5 minutes per hour-long session.*

### The "Switch" Economics (1,000 Users)

| Metric | Deepgram Aura 2 ($30) | Self-Hosted Orpheus (L4) |
| :--- | :--- | :--- |
| **Monthly Cost** | ~$1,080 (₹91k) | **~$120 (₹10k)** |
| **% of Revenue** | ~18-20% | **~2%** |
| **Net Savings** | $0 | **~$960/month** |

> [!TIP]
> **Conclusion:** Start with Deepgram Aura 2 (credits + speed). Aim to switch to your own GPU at **150+ paid MAU** to instantly boost margins by ~15-20%.
