import { AbsoluteFill, interpolate, spring, useCurrentFrame } from "remotion";
import { DocumentGrid } from "../components/DocumentGrid";
import { useMemo } from "react";

export const DocumentShowcase: React.FC = () => {
  const frame = useCurrentFrame();

  // Title animation with spring physics
  const titleSpring = spring({
    frame,
    fps: 30,
    config: { mass: 1, damping: 12, stiffness: 100 },
  });

  const titleOpacity = titleSpring;
  const titleY = interpolate(titleSpring, [0, 1], [30, 0]);

  // Voiceover-synced highlights - active card index changes over time
  const activeCardIndex = useMemo(() => {
    if (frame < 30) return 0; // Biology Notes
    if (frame < 60) return 1; // Physics Textbook
    if (frame < 90) return 2; // Chemistry PDF
    if (frame < 120) return 3; // Math Formulas
    return undefined; // All cards active after sequence
  }, [frame]);

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

      {/* Z-Axis Tunnel container for depth effect */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          perspective: 1000,
          perspectiveOrigin: "center center",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
            paddingTop: 40,
          }}
        >
          {/* Title - 48px headline */}
          <div
            style={{
              opacity: titleOpacity,
              transform: `translateY(${titleY}px)`,
              textAlign: "center",
              marginBottom: 12,
              paddingLeft: 40,
              paddingRight: 40,
            }}
          >
            <h1
              style={{
                color: "#000000",
                fontSize: 48,
                fontWeight: 700,
                marginBottom: 8,
              }}
            >
              Your study materials
            </h1>
            {/* Subtitle - 20px body */}
            <p
              style={{
                color: "#71717A",
                fontSize: 20,
              }}
            >
              PDFs, textbooks, notes — all supported
            </p>
          </div>

          {/* Document grid with Z-axis depth */}
          <div
            style={{
              flex: 1,
              overflow: "hidden",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transformStyle: "preserve-3d",
            }}
          >
            <DocumentGrid activeIndex={activeCardIndex} />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
