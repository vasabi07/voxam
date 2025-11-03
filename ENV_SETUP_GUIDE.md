# Environment Variables Setup Guide

## 📋 Overview

This guide shows you how to configure environment variables for the LiveKit-based voice exam system.

## 🔑 Python Backend (`/python/.env`)

Create or update `/Users/vasanth/voxam/python/.env`:

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=your-secret-key-here

# Speech-to-Text
DEEPGRAM_API_KEY=your-deepgram-api-key

# Text-to-Speech (Google Cloud)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account.json

# Database
REDIS_URL=redis://localhost:6379

# Other existing variables...
```

### How to Get LiveKit Credentials

**Option 1: LiveKit Cloud (Recommended)**
1. Go to https://livekit.io/cloud
2. Sign up for free tier
3. Create a new project
4. Copy credentials from dashboard:
   - WebSocket URL → `LIVEKIT_URL`
   - API Key → `LIVEKIT_API_KEY`
   - API Secret → `LIVEKIT_API_SECRET`

**Option 2: Self-Hosted**
```bash
brew install livekit
livekit-server --dev

# Use these values:
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

## 🌐 Next.js Frontend (`/nextjs/.env.local`)

Create `/Users/vasanth/voxam/nextjs/.env.local`:

```bash
# LiveKit WebSocket URL (public - safe to expose to client)
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Note:** 
- Use the **same** `LIVEKIT_URL` as your Python backend
- `NEXT_PUBLIC_` prefix makes it available in browser
- Frontend only needs the URL, not API keys (tokens come from backend)

## ✅ Verification

### Test Python Environment

```bash
cd /Users/vasanth/voxam/python
source .venv/bin/activate
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('LIVEKIT_URL:', os.getenv('LIVEKIT_URL'))"
```

### Test Next.js Environment

```bash
cd /Users/vasanth/voxam/nextjs
npm run dev
# Check browser console for NEXT_PUBLIC_* variables
```

## 🚀 Running the System

**Terminal 1 - Python Backend:**
```bash
cd /Users/vasanth/voxam/python
source .venv/bin/activate
uvicorn api:app --reload
```

**Terminal 2 - Next.js Frontend:**
```bash
cd /Users/vasanth/voxam/nextjs
npm run dev
```

**Terminal 3 - Redis (if not running):**
```bash
redis-server
```

## 🔒 Security Notes

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Python `.env`** contains secrets - keep secure
3. **Next.js `.env.local`** - `NEXT_PUBLIC_*` vars are exposed to browser
4. **Production**: Use proper secrets management (AWS Secrets Manager, etc.)

## 📝 File Structure

```
voxam/
├── python/
│   ├── .env                 # Backend secrets (git-ignored)
│   ├── .env.example         # Template for team
│   ├── api.py              # Uses: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
│   └── agents/
│       └── realtime.py     # Uses: LIVEKIT_URL, DEEPGRAM_API_KEY
│
└── nextjs/
    ├── .env.local          # Frontend config (git-ignored)
    ├── .env.local.example  # Template for team
    └── app/authenticated/exam-livekit/
        └── page.tsx        # Uses: NEXT_PUBLIC_LIVEKIT_URL, NEXT_PUBLIC_API_URL
```

## ❓ Troubleshooting

**Error: "Missing LIVEKIT_URL"**
- Check `.env` file exists in `/python/`
- Verify no typos in variable names
- Restart server after adding variables

**Frontend can't connect:**
- Check `NEXT_PUBLIC_LIVEKIT_URL` matches backend `LIVEKIT_URL`
- Restart `npm run dev` after changing `.env.local`
- Check browser console for errors

**Agent not joining room:**
- Verify `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` are correct
- Check LiveKit Cloud dashboard for errors
- Test token creation: `python -c "from api import create_livekit_token; print(create_livekit_token('test', 'room'))"`
