import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const BLUE = "#0066FF";

export const UploadCard: React.FC = () => {
  const frame = useCurrentFrame();

  // Card drops in from top
  const cardY = interpolate(frame, [0, 25], [-200, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fade in
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtle bounce effect
  const bounce = interpolate(frame, [25, 35, 45], [0, -10, 0], {
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
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
        }}
      >
        {/* PDF Card */}
        <div
          style={{
            opacity,
            transform: `translateY(${cardY + bounce}px)`,
            background: "#FFFFFF",
            borderRadius: 24,
            padding: 48,
            boxShadow: "0 20px 60px rgba(0, 0, 0, 0.15)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 24,
            minWidth: 400,
          }}
        >
          {/* PDF Icon */}
          <div
            style={{
              width: 120,
              height: 150,
              background: "#FEE2E2",
              borderRadius: 16,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
            }}
          >
            {/* Corner fold */}
            <div
              style={{
                position: "absolute",
                top: 0,
                right: 0,
                width: 30,
                height: 30,
                background: "#FECACA",
                borderBottomLeftRadius: 8,
              }}
            />
            <span
              style={{
                fontSize: 36,
                fontWeight: 700,
                color: "#DC2626",
              }}
            >
              PDF
            </span>
          </div>

          {/* File name */}
          <div
            style={{
              fontSize: 32,
              fontWeight: 600,
              color: "#18181B",
            }}
          >
            Chapter_5.pdf
          </div>

          {/* Upload indicator */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              color: BLUE,
              fontSize: 24,
              fontWeight: 500,
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 16V8M12 8L8 12M12 8L16 12"
                stroke={BLUE}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M3 15V16C3 18.2091 4.79086 20 7 20H17C19.2091 20 21 18.2091 21 16V15"
                stroke={BLUE}
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
            Uploading...
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
