# Video & Audio Sync Guide for Remotion Ads

This guide documents the principles for syncing video scenes with voiceover audio in VOXAM marketing videos.

## Core Principle

**Audio drives timing, not video.** Generate voiceover first, measure its duration, then adjust video to match.

---

## Workflow

### 1. Write the Script First
Create a voiceover script with timing estimates:

| Scene | Voiceover Line | Est. Duration |
|-------|----------------|---------------|
| Hook | "Attention-grabbing opening line." | 2-3s |
| Feature 1 | "Describe the feature clearly." | 3-4s |
| CTA | "Call to action with URL." | 2-3s |

**Tip:** Add ~15-20% buffer for pauses between sentences.

### 2. Generate Voiceover
```bash
cd marketing/remotion
python scripts/generate-voiceover-gemini.py
```

### 3. Measure Actual Audio Duration
```bash
afinfo public/voiceover.wav | grep "estimated duration"
```

### 4. Adjust Video Duration to Match Audio
Update `INSTAGRAM_AD_DURATION` in `src/InstagramAd/index.tsx` to match:
```
Duration (seconds) × 30 fps = Total frames
```

Example: 26 seconds × 30 = 780 frames

### 5. Fine-tune Scene Timings
Distribute frames across scenes based on voiceover line durations.

---

## Scene Timing Rules

### Frame Calculations
- **30 fps** = 30 frames per second
- 1 second = 30 frames
- 0.5 seconds = 15 frames

### Scene Duration Guidelines

| Scene Type | Recommended Duration | Notes |
|------------|---------------------|-------|
| Hook | 60-90 frames (2-3s) | Short, punchy |
| Logo Reveal | 45-60 frames (1.5-2s) | Brand moment |
| Feature Demo | 90-150 frames (3-5s) | Show the product |
| Results/Proof | 90-130 frames (3-4.3s) | Build credibility |
| CTA | 90-155 frames (3-5s) | Give time to read URL |

### Pacing Principles
- **Rushed feel?** Add 30-60 frames (1-2s) to total duration
- **Dragging?** Tighten scenes by 15-30 frames each
- **Audio cuts off?** Extend CTA scene (end has most flexibility)

---

## Voiceover Generation

### Script Writing Tips
1. **Keep it conversational** - Write how people speak
2. **Short sentences** - Easier to pace, more punchy
3. **Pause markers** - Line breaks in script = natural pauses
4. **Read aloud** - Time yourself reading the script

### Gemini TTS Prompt Template
```python
VOICEOVER_PROMPT = """
You are an energetic, confident presenter. Speak with enthusiasm and a quick, engaging pace.
This is a punchy [X]-second social media ad.

Read this script naturally with brief pauses between sentences:

"[Your script here with line breaks between sentences]"
"""
```

### Voice Selection (Gemini 2.5 Flash TTS)
- **Sulafat** - Warm, tutorish (current default)
- **Zephyr** - Bright, energetic
- **Puck** - Upbeat, playful
- **Kore** - Firm, authoritative
- **Achird** - Friendly, approachable

---

## Troubleshooting

### Audio cuts off at the end
1. Check actual audio duration: `afinfo public/voiceover.wav`
2. Extend `INSTAGRAM_AD_DURATION` to match
3. Add extra frames to CTA scene

### Video feels rushed
- Increase total duration by 2-3 seconds
- Regenerate voiceover with "slower, more deliberate pace" in prompt
- Add more frames to feature scenes

### Scene transitions don't match voiceover
1. Play video and note where each line starts
2. Adjust individual scene `start` values
3. Keep scenes contiguous (no gaps between end and next start)

### Voiceover too long/short
- Adjust prompt: "quick pace" vs "measured pace"
- Simplify script (fewer words = shorter)
- Regenerate - TTS output varies slightly each time

---

## File Reference

| File | Purpose |
|------|---------|
| `scripts/generate-voiceover-gemini.py` | Voiceover generation script |
| `src/InstagramAd/index.tsx` | Scene timings & duration |
| `public/voiceover.wav` | Generated audio file |

---

## Example: 26-Second Ad

```typescript
// 26 seconds = 780 frames @ 30fps
const SCENE_TIMING = {
  hook: { start: 0, duration: 75 },           // 2.5s
  logoReveal: { start: 75, duration: 50 },    // 1.7s
  documentShowcase: { start: 125, duration: 100 }, // 3.3s
  chatDemo: { start: 225, duration: 140 },    // 4.7s
  examMode: { start: 365, duration: 130 },    // 4.3s
  results: { start: 495, duration: 130 },     // 4.3s
  cta: { start: 625, duration: 155 },         // 5.2s
};

export const INSTAGRAM_AD_DURATION = 780;
```

---

## Quick Reference

```
Target Duration → Generate Audio → Measure Actual → Adjust Video → Preview → Fine-tune
```

**Golden rule:** If in doubt, make the video slightly longer than the audio. A moment of visual breathing room at the end is better than cut-off audio.
