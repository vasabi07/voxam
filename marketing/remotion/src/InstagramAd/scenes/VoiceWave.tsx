import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { CleanWaveform } from "../components/CleanWaveform";

const BLUE = "#0066FF";

export const VoiceWave: React.FC = () => {
  const frame = useCurrentFrame();

  // Fade in
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Mic pulse animation
  const micScale = interpolate(
    frame % 30,
    [0, 15, 30],
    [1, 1.05, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

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
          gap: 60,
          opacity,
        }}
      >
        {/* Microphone icon */}
        <div
          style={{
            width: 140,
            height: 140,
            borderRadius: 70,
            background: `linear-gradient(135deg, ${BLUE} 0%, #8B5CF6 100%)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 20px 50px rgba(0, 102, 255, 0.3)",
            transform: `scale(${micScale})`,
          }}
        >
          <svg width="60" height="60" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 1C10.3431 1 9 2.34315 9 4V12C9 13.6569 10.3431 15 12 15C13.6569 15 15 13.6569 15 12V4C15 2.34315 13.6569 1 12 1Z"
              fill="#FFFFFF"
            />
            <path
              d="M19 10V12C19 15.866 15.866 19 12 19C8.13401 19 5 15.866 5 12V10"
              stroke="#FFFFFF"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <path
              d="M12 19V23M12 23H8M12 23H16"
              stroke="#FFFFFF"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>

        {/* Waveform */}
        <CleanWaveform
          barCount={24}
          width={600}
          height={100}
          color={BLUE}
          isActive={true}
          delayStart={0}
        />
      </div>
    </AbsoluteFill>
  );
};
