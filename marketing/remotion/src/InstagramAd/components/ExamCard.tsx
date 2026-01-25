import { useCurrentFrame, spring, interpolate } from "remotion";

interface ExamCardProps {
  question: string;
  startFrame?: number;
}

export const ExamCard: React.FC<ExamCardProps> = ({
  question,
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const adjustedFrame = Math.max(0, frame - startFrame);

  // Spring physics for entry animation
  const entrySpring = spring({
    frame: adjustedFrame,
    fps: 30,
    config: { mass: 1, damping: 12, stiffness: 100 },
  });

  const entryScale = 0.85 + entrySpring * 0.15;
  const entryOpacity = entrySpring;

  // Fluid float animation - constant gentle motion
  const floatY = Math.sin(frame / 30) * 6;
  const floatX = Math.cos(frame / 45) * 3;

  return (
    <div
      style={{
        opacity: entryOpacity,
        transform: `translateY(${floatY}px) translateX(${floatX}px) scale(${entryScale})`,
      }}
    >
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: 28,
          padding: 40,
          width: 800,
          boxShadow: "0 24px 48px rgba(0,0,0,0.14)",
          border: "1px solid #E5E7EB",
        }}
      >
        {/* Question text - enlarged to 36px */}
        <div
          style={{
            color: "#000000",
            fontSize: 36,
            lineHeight: 1.5,
            fontWeight: 500,
          }}
        >
          {question}
        </div>
      </div>
    </div>
  );
};
