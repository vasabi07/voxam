import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const BLUE = "#0066FF";

/*
 * Results Scene Timing (150 frames = 5 seconds)
 * - Score circle entry: 0-20 (0.67s)
 * - Score counting: 10-45 (1.2s)
 * - Insight card entry: 50-70 (0.67s)
 * - Title entry: 80-100 (0.67s)
 * - Hold time: 100-150 (1.67s) - Reading time for feedback
 */

export const Results: React.FC = () => {
  const frame = useCurrentFrame();

  // Score circle animation - simple fade + slide
  const scoreOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const scoreY = interpolate(frame, [0, 20], [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Number counting animation
  const percentage = 73;
  const displayPercentage = Math.min(
    percentage,
    Math.floor(interpolate(frame, [10, 45], [0, percentage], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }))
  );

  // Insight card animation - simple fade + slide (earlier entry for reading time)
  const cardStartFrame = 50;
  const cardOpacity = interpolate(
    frame,
    [cardStartFrame, cardStartFrame + 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const cardY = interpolate(
    frame,
    [cardStartFrame, cardStartFrame + 20],
    [30, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Title animation - earlier entry so it completes well before scene ends
  const titleStartFrame = 80;
  const titleOpacity = interpolate(
    frame,
    [titleStartFrame, titleStartFrame + 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const titleYAnim = interpolate(
    frame,
    [titleStartFrame, titleStartFrame + 20],
    [20, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const strengths = ["Strong concept recall", "Clear explanations"];
  const focusAreas = ["Application practice", "ATP synthesis details"];

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
          gap: 28,
          padding: 40,
        }}
      >
        {/* Score circle - 200px */}
        <div
          style={{
            opacity: scoreOpacity,
            transform: `translateY(${scoreY}px)`,
          }}
        >
          <div
            style={{
              width: 200,
              height: 200,
              borderRadius: "50%",
              background: "#FFFFFF",
              border: `6px solid ${BLUE}`,
              boxShadow: "0 20px 40px rgba(0,0,0,0.1)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* Grade - larger for visibility */}
            <div
              style={{
                color: BLUE,
                fontSize: 72,
                fontWeight: 700,
                lineHeight: 1,
              }}
            >
              B+
            </div>
            {/* Percentage - 20px body */}
            <div
              style={{
                color: "#71717A",
                fontSize: 28,
                fontWeight: 500,
                marginTop: 4,
              }}
            >
              {displayPercentage}%
            </div>
          </div>
        </div>

        {/* Unified insight card - 520px wide */}
        <div
          style={{
            opacity: cardOpacity,
            transform: `translateY(${cardY}px)`,
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: 20,
              padding: 28,
              boxShadow: "0 16px 32px rgba(0,0,0,0.08)",
              border: "1px solid #E5E7EB",
              width: 520,
            }}
          >
            {/* What went well - 20px body font */}
            <div style={{ marginBottom: 20 }}>
              <div
                style={{
                  color: "#000000",
                  fontSize: 20,
                  fontWeight: 600,
                  marginBottom: 12,
                }}
              >
                What went well
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {strengths.map((item, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                    }}
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={BLUE} strokeWidth="2.5">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <span
                      style={{
                        color: "#374151",
                        fontSize: 20,
                      }}
                    >
                      {item}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Focus areas - 20px body font */}
            <div>
              <div
                style={{
                  color: "#000000",
                  fontSize: 20,
                  fontWeight: 600,
                  marginBottom: 12,
                }}
              >
                Focus areas
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {focusAreas.map((item, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                    }}
                  >
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: BLUE,
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        color: "#374151",
                        fontSize: 20,
                      }}
                    >
                      {item}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Title - 48px headline */}
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleYAnim}px)`,
            textAlign: "center",
            marginTop: 8,
          }}
        >
          <h2
            style={{
              color: "#000000",
              fontSize: 48,
              fontWeight: 700,
              marginBottom: 12,
            }}
          >
            Instant feedback
          </h2>
          {/* Body - 20px */}
          <p
            style={{
              color: "#71717A",
              fontSize: 20,
            }}
          >
            Know exactly where to improve
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};
