import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { WordByWordText } from "../components/WordByWordText";

export const Hook: React.FC = () => {
  const frame = useCurrentFrame();

  // Scene phases
  const showFirstLine = frame < 45;
  const showSecondLine = frame >= 45;

  // Fade transition between lines
  const firstLineOpacity = interpolate(frame, [40, 50], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const secondLineOpacity = interpolate(frame, [45, 55], [0, 1], {
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
          padding: 60,
        }}
      >
        {/* First line: "Turn your notes" */}
        {showFirstLine && (
          <div style={{ opacity: firstLineOpacity }}>
            <WordByWordText
              text="Turn your notes"
              accentWords={["notes"]}
              fontSize={85}
              fontWeight={700}
              startFrame={0}
            />
          </div>
        )}

        {/* Second line: "Into exam practice" */}
        {showSecondLine && (
          <div style={{ opacity: secondLineOpacity }}>
            <WordByWordText
              text="Into exam practice"
              accentWords={["exam", "practice"]}
              fontSize={85}
              fontWeight={700}
              startFrame={45}
            />
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
