# Audio/Visual Sync Verification Checklist

## Summary
- **Video Duration**: 28.5 seconds (855 frames @ 30fps)
- **Voiceover Duration**: 26.7 seconds
- **Voice**: Gemini 2.5 Flash TTS - Sulafat (warm)
- **Pacing**: 25% faster than original

## Verification Steps

Run the dev server:
```bash
cd marketing/remotion && npm run dev
```

Check sync at these key moments:

| Frame | Time   | Visual                      | Audio Should Say              |
|-------|--------|-----------------------------|-----------------------------|
| 0     | 0:00   | "Turn your notes" text      | "Turn your notes..."        |
| 112   | 3:73   | Logo appears                | "Introducing VOXAM"         |
| 202   | 6:73   | Document cards appear       | "Upload any study material" |
| 337   | 11:23  | Chat input visible          | "Just ask to create..."     |
| 495   | 16:50  | Exam mode card              | "Practice with your voice"  |
| 653   | 21:77  | Score appears               | "Get instant feedback..."   |
| 765   | 25:50  | CTA button visible          | "Try free at voxam.in"      |
| 855   | 28:50  | End                         | (silence - CTA breathing room) |

## Regenerating Voiceover

```bash
cd marketing/remotion
source ../../python/.venv/bin/activate
python scripts/generate-voiceover-gemini.py
```

## Scene Timing Reference

| Scene            | Start Frame | Duration | Time Range |
|------------------|-------------|----------|------------|
| Hook             | 0           | 112      | 0-3.7s     |
| LogoReveal       | 112         | 90       | 3.7-6.7s   |
| DocumentShowcase | 202         | 135      | 6.7-11.2s  |
| ChatDemo         | 337         | 158      | 11.2-16.5s |
| ExamMode         | 495         | 158      | 16.5-21.8s |
| Results          | 653         | 112      | 21.8-25.5s |
| CTA              | 765         | 90       | 25.5-28.5s |

## Optional SFX Files

- `music-lofi.mp3` - Background music (30+ seconds)
- `sfx-upload.mp3` - Paper whoosh
- `sfx-send.mp3` - Chat send click
- `sfx-mic.mp3` - Mic activation beep
- `sfx-success.mp3` - Score reveal chime
- `sfx-button.mp3` - CTA button pop
