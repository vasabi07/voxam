import { useCurrentFrame, spring, interpolate } from "remotion";

interface ScoreCardProps {
  grade: string;
  percentage: number;
  startFrame?: number;
}

export const ScoreCard: React.FC<ScoreCardProps> = ({
  grade,
  percentage,
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

  // Number counting animation
  const displayPercentage = Math.min(
    percentage,
    Math.floor(interpolate(adjustedFrame, [10, 45], [0, percentage], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }))
  );

  // Grade color based on percentage
  const gradeColor = percentage >= 80 ? "#10B981" : percentage >= 60 ? "#0066FF" : "#F59E0B";

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
          padding: 48,
          boxShadow: "0 30px 60px rgba(0,0,0,0.15)",
          border: "1px solid #E5E7EB",
          display: "flex",
          alignItems: "center",
          gap: 40,
          width: 520,
        }}
      >
        {/* Grade circle - 200px */}
        <div
          style={{
            width: 200,
            height: 200,
            borderRadius: "50%",
            background: `${gradeColor}15`,
            border: `5px solid ${gradeColor}`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <div
            style={{
              color: gradeColor,
              fontSize: 72,
              fontWeight: 700,
              lineHeight: 1,
            }}
          >
            {grade}
          </div>
          <div
            style={{
              color: "#71717A",
              fontSize: 28,
              fontWeight: 500,
            }}
          >
            {displayPercentage}%
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div
            style={{
              color: "#000000",
              fontSize: 40,
              fontWeight: 700,
            }}
          >
            Exam Complete
          </div>
          <div
            style={{
              color: "#71717A",
              fontSize: 28,
            }}
          >
            10 questions • 7 correct
          </div>
        </div>
      </div>
    </div>
  );
};
