import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const BLUE = "#0066FF";

export const ChatBubble: React.FC = () => {
  const frame = useCurrentFrame();

  // Bubble slides in from right
  const bubbleX = interpolate(frame, [0, 20], [100, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fade in
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Checkmark appears after bubble
  const checkOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const checkScale = interpolate(frame, [40, 60], [0.5, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

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
        }}
      >
        {/* Chat bubble */}
        <div
          style={{
            opacity,
            transform: `translateX(${bubbleX}px)`,
            background: BLUE,
            borderRadius: 32,
            borderBottomRightRadius: 8,
            padding: "32px 48px",
            maxWidth: 700,
            boxShadow: "0 15px 40px rgba(0, 102, 255, 0.25)",
          }}
        >
          <div
            style={{
              fontSize: 42,
              fontWeight: 600,
              color: "#FFFFFF",
              textAlign: "center",
            }}
          >
            "Create my exam"
          </div>
        </div>

        {/* Checkmark confirmation */}
        <div
          style={{
            opacity: checkOpacity,
            transform: `scale(${checkScale})`,
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div
            style={{
              width: 60,
              height: 60,
              borderRadius: 30,
              background: "#22C55E",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path
                d="M5 12L10 17L19 8"
                stroke="#FFFFFF"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            style={{
              fontSize: 36,
              fontWeight: 600,
              color: "#22C55E",
            }}
          >
            Instantly
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
