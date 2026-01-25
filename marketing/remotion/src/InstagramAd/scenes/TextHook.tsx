import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { WordByWordText } from "../components/WordByWordText";

const BLUE = "#0066FF";

interface TextHookProps {
  text: string;
  accentWords?: string[];
}

export const TextHook: React.FC<TextHookProps> = ({ text, accentWords = [] }) => {
  const frame = useCurrentFrame();

  // Fade out near end
  const fadeOut = interpolate(frame, [100, 120], [1, 0], {
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
          padding: 60,
          opacity: fadeOut,
        }}
      >
        <WordByWordText
          text={text}
          accentWords={accentWords}
          accentColor={BLUE}
          fontSize={80}
          fontWeight={700}
          color="#000000"
          wordDelay={5}
          startFrame={0}
        />
      </div>
    </AbsoluteFill>
  );
};
