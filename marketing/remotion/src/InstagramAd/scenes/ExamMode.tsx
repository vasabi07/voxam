import { AbsoluteFill, spring, interpolate, useCurrentFrame } from "remotion";
import { ExamCard } from "../components/ExamCard";
import { CleanWaveform } from "../components/CleanWaveform";

const BLUE = "#0066FF";

export const ExamMode: React.FC = () => {
  const frame = useCurrentFrame();

  // Waveform animation with spring physics
  const waveformStartFrame = 60;
  const waveformSpring = spring({
    frame: Math.max(0, frame - waveformStartFrame),
    fps: 30,
    config: { mass: 1, damping: 12, stiffness: 100 },
  });

  const waveformOpacity = waveformSpring;
  const waveformScale = 0.85 + waveformSpring * 0.15;

  // Fluid float for waveform section
  const waveFloatY = Math.sin(frame / 30) * 5;
  const waveFloatX = Math.cos(frame / 45) * 3;

  // Title appears at the end with spring
  const titleStartFrame = 130;
  const titleSpring = spring({
    frame: Math.max(0, frame - titleStartFrame),
    fps: 30,
    config: { mass: 1, damping: 12, stiffness: 100 },
  });

  const titleOpacity = titleSpring;
  const titleY = interpolate(titleSpring, [0, 1], [30, 0]);

  return (
    <AbsoluteFill style={{ background: "#FFFFFF" }}>
      {/* Subtle vignette */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.03) 100%)",
        }}
      />

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: 40,
          padding: 40,
        }}
      >
        {/* Exam card - simplified */}
        <ExamCard
          question="Compare the light-dependent and light-independent reactions in photosynthesis."
          startFrame={10}
        />

        {/* Voice waveform section - enlarged */}
        <div
          style={{
            opacity: waveformOpacity,
            transform: `translateY(${waveFloatY}px) translateX(${waveFloatX}px) scale(${waveformScale})`,
            display: "flex",
            alignItems: "center",
            gap: 24,
          }}
        >
          {/* Mic icon - enlarged to 80px */}
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: "50%",
              background: `${BLUE}15`,
              border: `3px solid ${BLUE}30`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke={BLUE}
              strokeWidth="2"
            >
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          </div>

          {/* Waveform - enlarged to 700x120 */}
          <CleanWaveform
            barCount={32}
            width={700}
            height={120}
            color={BLUE}
            isActive={frame > waveformStartFrame}
            delayStart={0}
          />
        </div>

        {/* Title - enlarged to 64px */}
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            textAlign: "center",
          }}
        >
          <h2
            style={{
              color: "#000000",
              fontSize: 64,
              fontWeight: 700,
              marginBottom: 16,
            }}
          >
            Real-time voice exam
          </h2>
          {/* Body - 28px */}
          <p
            style={{
              color: "#71717A",
              fontSize: 28,
            }}
          >
            Just speak naturally — AI understands
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};
