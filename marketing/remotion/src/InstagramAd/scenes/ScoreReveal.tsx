import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const BLUE = "#0066FF";

export const ScoreReveal: React.FC = () => {
  const frame = useCurrentFrame();

  // Scale in animation
  const scale = interpolate(frame, [0, 25], [0.7, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fade in
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Score counter animation (73%)
  const scoreValue = Math.round(
    interpolate(frame, [15, 50], [0, 73], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  // Circle progress animation
  const progress = interpolate(frame, [15, 50], [0, 73], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Grade reveal
  const gradeOpacity = interpolate(frame, [50, 65], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const gradeScale = interpolate(frame, [50, 65], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Circle properties
  const circleSize = 350;
  const strokeWidth = 20;
  const radius = (circleSize - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

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
          opacity,
          transform: `scale(${scale})`,
        }}
      >
        {/* Score circle */}
        <div
          style={{
            position: "relative",
            width: circleSize,
            height: circleSize,
          }}
        >
          {/* Background circle */}
          <svg
            width={circleSize}
            height={circleSize}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              transform: "rotate(-90deg)",
            }}
          >
            <circle
              cx={circleSize / 2}
              cy={circleSize / 2}
              r={radius}
              fill="none"
              stroke="#E5E7EB"
              strokeWidth={strokeWidth}
            />
            <circle
              cx={circleSize / 2}
              cy={circleSize / 2}
              r={radius}
              fill="none"
              stroke={BLUE}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
            />
          </svg>

          {/* Score text inside circle */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {/* Grade */}
            <div
              style={{
                fontSize: 80,
                fontWeight: 700,
                color: BLUE,
                opacity: gradeOpacity,
                transform: `scale(${gradeScale})`,
              }}
            >
              B+
            </div>

            {/* Percentage */}
            <div
              style={{
                fontSize: 64,
                fontWeight: 700,
                color: "#18181B",
              }}
            >
              {scoreValue}%
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
