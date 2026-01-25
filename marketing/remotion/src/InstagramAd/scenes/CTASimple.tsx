import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Sparkle } from "../components/Sparkle";

const BLUE = "#0066FF";

interface CTASimpleProps {
  showTagline?: boolean;
}

export const CTASimple: React.FC<CTASimpleProps> = ({ showTagline = false }) => {
  const frame = useCurrentFrame();

  // Fade in
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const scale = interpolate(frame, [0, 20], [0.95, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Button animation (appears after text)
  const buttonOpacity = interpolate(frame, [25, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const buttonY = interpolate(frame, [25, 40], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Sheen effect on button
  const sheenPosition = interpolate(frame, [50, 70], [100, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (showTagline) {
    // Tagline scene: "Voice exams. Smart questions." - white background
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
            gap: 24,
            opacity,
            transform: `scale(${scale})`,
          }}
        >
          <div
            style={{
              fontSize: 72,
              fontWeight: 700,
              color: "#000000",
              textAlign: "center",
              lineHeight: 1.3,
            }}
          >
            Voice exams.
          </div>
          <div
            style={{
              fontSize: 72,
              fontWeight: 700,
              color: BLUE,
              textAlign: "center",
              lineHeight: 1.3,
            }}
          >
            Smart questions.
          </div>
        </div>
      </AbsoluteFill>
    );
  }

  // CTA scene: voxam.in + button
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

      {/* Sparkles */}
      <Sparkle x={80} y={380} size={40} color={BLUE} delay={10} />
      <Sparkle x={960} y={480} size={48} color="#8B5CF6" delay={15} rotationSpeed={0.6} />
      <Sparkle x={130} y={1380} size={36} color={BLUE} delay={20} rotationSpeed={0.4} />
      <Sparkle x={900} y={1330} size={44} color="#8B5CF6" delay={25} />

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: 48,
        }}
      >
        {/* VOXAM Logo */}
        <div
          style={{
            opacity,
            transform: `scale(${scale})`,
          }}
        >
          <div
            style={{
              fontSize: 120,
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: BLUE,
            }}
          >
            VOXAM
          </div>
        </div>

        {/* CTA Button */}
        <div
          style={{
            opacity: buttonOpacity,
            transform: `translateY(${buttonY}px)`,
            marginTop: 16,
          }}
        >
          <div
            style={{
              position: "relative",
              background: BLUE,
              borderRadius: 999,
              padding: "28px 80px",
              color: "#FFFFFF",
              fontWeight: 700,
              fontSize: 40,
              boxShadow: "0 20px 40px rgba(0, 102, 255, 0.3)",
              overflow: "hidden",
            }}
          >
            <span style={{ position: "relative", zIndex: 1 }}>Try Free</span>

            {/* Sheen overlay */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: `linear-gradient(120deg, transparent 30%, rgba(255,255,255,0.4) 50%, transparent 70%)`,
                backgroundSize: "200% 100%",
                backgroundPosition: `${sheenPosition}% 0`,
                pointerEvents: "none",
              }}
            />
          </div>
        </div>

        {/* Website URL - FIXED: voxam.in not voxam.io */}
        <div
          style={{
            opacity,
            color: "#71717A",
            fontSize: 36,
            letterSpacing: "0.1em",
            marginTop: 16,
          }}
        >
          voxam.in
        </div>
      </div>
    </AbsoluteFill>
  );
};
