import { interpolate, useCurrentFrame } from "remotion";

interface WordByWordTextProps {
  text: string;
  accentWords?: string[];
  accentColor?: string;
  fontSize?: number;
  fontWeight?: number;
  color?: string;
  wordDelay?: number;
  startFrame?: number;
  gap?: number;
  lineHeight?: number;
  center?: boolean;
}

export const WordByWordText: React.FC<WordByWordTextProps> = ({
  text,
  accentWords = [],
  accentColor = "#0066FF",
  fontSize = 90,
  fontWeight = 700,
  color = "#000000",
  wordDelay = 6,
  startFrame = 0,
  gap = 16,
  lineHeight = 1.2,
  center = true,
}) => {
  const frame = useCurrentFrame();
  const words = text.split(" ");
  const adjustedFrame = frame - startFrame;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap,
        fontSize,
        fontWeight,
        lineHeight,
        justifyContent: center ? "center" : "flex-start",
      }}
    >
      {words.map((word, i) => {
        const wordFrame = adjustedFrame - i * wordDelay;
        const opacity = interpolate(wordFrame, [0, 10], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const y = interpolate(wordFrame, [0, 10], [10, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const blur = interpolate(wordFrame, [0, 10], [4, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        // Check if this word (without punctuation) is an accent word
        const cleanWord = word.replace(/[.,!?;:'"]/g, "").toLowerCase();
        const isAccent = accentWords.some(
          (aw) => cleanWord === aw.toLowerCase()
        );

        return (
          <span
            key={i}
            style={{
              opacity,
              transform: `translateY(${y}px)`,
              filter: `blur(${blur}px)`,
              color: isAccent ? accentColor : color,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};
