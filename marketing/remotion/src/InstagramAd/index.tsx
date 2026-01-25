import { AbsoluteFill, Sequence, Audio, staticFile } from "remotion";
import { Hook } from "./scenes/Hook";
import { LogoReveal } from "./scenes/LogoReveal";
import { DocumentShowcase } from "./scenes/DocumentShowcase";
import { ChatDemo } from "./scenes/ChatDemo";
import { ExamMode } from "./scenes/ExamMode";
import { Results } from "./scenes/Results";
import { CTA } from "./scenes/CTA";

// Scene timing (in frames at 30fps) - Total: 31 seconds = 930 frames
// Synced with voiceover.wav (Gemini 2.5 Flash TTS - steady, confident pace)
const SCENE_TIMING = {
  // Part 1: Hook (0-5.3s) - Attention grabber
  hook: { start: 0, duration: 95 },            // 0-3.2s: "Turn your notes into real exam practice"
  logoReveal: { start: 95, duration: 65 },     // 3.2-5.3s: "Introducing VOXAM"

  // Part 2: Features (5.3-21.8s) - Show the product
  documentShowcase: { start: 160, duration: 175 },  // 5.3-11.2s: "Upload any study material..."
  chatDemo: { start: 335, duration: 165 },          // 11.2-16.7s: "Ask to create an exam..."
  examMode: { start: 500, duration: 155 },          // 16.7-21.8s: "Practice with your voice..."

  // Part 3: Results + CTA (21.8-31s) - Close
  results: { start: 655, duration: 155 },      // 21.8-27s: "Get detailed feedback..."
  cta: { start: 810, duration: 120 },          // 27-31s: "Try VOXAM free at voxam.in"
};

// SFX and background music disabled - add audio files to public/ to enable
// See comment at bottom of file for required audio files

export const InstagramAd: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: "#FFFFFF" }}>
      {/* Background music disabled - add music-lofi.mp3 to public/ to enable */}

      {/* Voiceover audio - Gemini 2.5 Flash TTS (Sulafat voice) */}
      <Audio src={staticFile("voiceover.wav")} volume={1} />

      {/* Part 1: Hook - Attention grabber */}
      <Sequence
        from={SCENE_TIMING.hook.start}
        durationInFrames={SCENE_TIMING.hook.duration}
      >
        <Hook />
      </Sequence>

      <Sequence
        from={SCENE_TIMING.logoReveal.start}
        durationInFrames={SCENE_TIMING.logoReveal.duration}
      >
        <LogoReveal />
      </Sequence>

      {/* Part 2: Features - Show the product */}
      <Sequence
        from={SCENE_TIMING.documentShowcase.start}
        durationInFrames={SCENE_TIMING.documentShowcase.duration}
      >
        <DocumentShowcase />
        {/* SFX disabled - add sfx-upload.mp3 to enable */}
      </Sequence>

      <Sequence
        from={SCENE_TIMING.chatDemo.start}
        durationInFrames={SCENE_TIMING.chatDemo.duration}
      >
        <ChatDemo />
        {/* SFX disabled - add sfx-send.mp3 to enable */}
      </Sequence>

      <Sequence
        from={SCENE_TIMING.examMode.start}
        durationInFrames={SCENE_TIMING.examMode.duration}
      >
        <ExamMode />
        {/* SFX disabled - add sfx-mic.mp3 to enable */}
      </Sequence>

      {/* Part 3: Results + CTA */}
      <Sequence
        from={SCENE_TIMING.results.start}
        durationInFrames={SCENE_TIMING.results.duration}
      >
        <Results />
        {/* SFX disabled - add sfx-success.mp3 to enable */}
      </Sequence>

      <Sequence
        from={SCENE_TIMING.cta.start}
        durationInFrames={SCENE_TIMING.cta.duration}
      >
        <CTA />
        {/* SFX disabled - add sfx-button.mp3 to enable */}
      </Sequence>
    </AbsoluteFill>
  );
};

// Total duration: 930 frames = 31 seconds at 30fps
// Synced with voiceover.wav (steady, confident pace)
export const INSTAGRAM_AD_DURATION = 930;
export const INSTAGRAM_AD_FPS = 30;
export const INSTAGRAM_AD_WIDTH = 1080;
export const INSTAGRAM_AD_HEIGHT = 1920;

/*
 * Audio files needed in /public:
 * - voiceover.wav     : Gemini 2.5 Flash TTS (Sulafat voice, ~31s)
 *                       Generate with: python scripts/generate-voiceover-gemini.py
 * - music-lofi.mp3    : Lo-fi background music (30+ seconds, 70-90 BPM) [optional]
 * - sfx-upload.mp3    : Paper whoosh for document upload [optional]
 * - sfx-send.mp3      : Soft click for chat send [optional]
 * - sfx-mic.mp3       : Digital beep for mic activation [optional]
 * - sfx-success.mp3   : Success chime for score reveal [optional]
 * - sfx-button.mp3    : Subtle pop for CTA button [optional]
 */
