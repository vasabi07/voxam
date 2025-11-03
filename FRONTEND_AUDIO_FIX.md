# Frontend Audio Playback Fix

## Problem
Audio from the backend was generating and streaming correctly, but the frontend wasn't playing it. The UI showed "Listening" when it should have shown "Agent Speaking", and audio would only play after all chunks were complete (if at all).

## Root Causes

### 1. WebRTC MediaStream Behavior
- **Issue**: MediaStreams from WebRTC don't behave like regular audio files
- **Problem**: No `onended` event fires for continuous streams
- **Solution**: Use backend `audio_start`/`audio_complete` messages to control UI state

### 2. Browser Autoplay Policy
- **Issue**: Browsers block autoplay of audio without user interaction
- **Problem**: `audio.play()` fails silently or throws an error
- **Solution**: Explicitly call `play()` and handle the promise rejection

### 3. Missing Audio Element Configuration
- **Issue**: Audio element wasn't properly configured with all necessary event listeners
- **Problem**: No visibility into what's happening with audio playback
- **Solution**: Added comprehensive event listeners for debugging

## Changes Made

### `/nextjs/app/authenticated/exam/page.tsx`

#### 1. Added Comprehensive Audio Event Listeners
```typescript
remoteAudioRef.current.onloadedmetadata = () => {
    addLog('📊 Audio metadata loaded');
};

remoteAudioRef.current.oncanplay = () => {
    addLog('✅ Audio can play');
};

remoteAudioRef.current.onplaying = () => {
    addLog('🔊 Audio is actively playing');
};

// ... more listeners for debugging
```

#### 2. Explicit play() Call with Error Handling
```typescript
const playPromise = remoteAudioRef.current.play();
if (playPromise !== undefined) {
    playPromise
        .then(() => {
            addLog('✅ Audio playback started successfully');
        })
        .catch(err => {
            addLog(`❌ Autoplay failed: ${err.name} - ${err.message}`);
            addLog('💡 Tip: User interaction may be required.');
        });
}
```

#### 3. Proper UI State Management
```typescript
// UI state is controlled by backend messages
else if (data.type === 'audio_start') {
    addLog('🗣️ Agent started speaking');
    setIsPlayingAudio(true);  // Show "Agent Speaking" in UI
}
else if (data.type === 'audio_complete') {
    addLog('✅ Agent finished speaking, your turn...');
    setIsPlayingAudio(false);  // Show "Listening" in UI
}
```

## How It Works Now

1. **Backend starts TTS** → Streams audio via WebRTC
2. **Frontend receives track** → `ontrack` event fires
3. **Audio element created** → `srcObject` set to WebRTC stream
4. **Explicit play() called** → Handles autoplay restrictions
5. **Backend sends `audio_start`** → UI shows "Agent Speaking"
6. **Audio plays in real-time** → No delay, no buffering
7. **Backend sends `audio_complete`** → UI shows "Listening"

## Expected Behavior

✅ **Immediate Audio**: Audio starts playing ~200-300ms after agent responds
✅ **Correct UI State**: "Agent Speaking" when audio plays, "Listening" when done
✅ **Real-time Streaming**: Each sentence plays as it's generated
✅ **No Buffering**: Audio flows continuously without waiting for all chunks

## Testing

1. Open browser console to see detailed logs
2. Start exam
3. Speak an answer
4. Watch for:
   - `🔊 Audio is actively playing` log
   - UI showing "Agent Speaking" orb
   - Audio playing immediately

## Troubleshooting

### If audio still doesn't play:

1. **Check browser console** for autoplay errors
2. **Try user interaction**: Click somewhere on the page first
3. **Check audio permissions**: Ensure microphone permission is granted
4. **Check volume**: System volume and browser tab not muted
5. **Test WebRTC**: Visit https://test.webrtc.org/ to verify WebRTC works

### Common Issues:

- **"Autoplay failed"**: Browser blocking autoplay → Click on page first
- **"No audio tracks"**: WebRTC connection issue → Check network/firewall
- **Audio cuts off**: Backend not streaming properly → Check Python logs
