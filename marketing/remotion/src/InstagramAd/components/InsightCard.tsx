import { useCurrentFrame, interpolate } from "remotion";

interface InsightCardProps {
  title: string;
  items: string[];
  type: "strength" | "weakness";
  startFrame?: number;
  direction?: "left" | "right";
}

export const InsightCard: React.FC<InsightCardProps> = ({
  title,
  items,
  type,
  startFrame = 0,
  direction = "left",
}) => {
  const frame = useCurrentFrame();
  const adjustedFrame = frame - startFrame;

  // Simple fade entry animation (no spring)
  const entryOpacity = interpolate(adjustedFrame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const xOffset = interpolate(
    adjustedFrame,
    [0, 20],
    [direction === "left" ? -50 : 50, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Colors based on type
  const color = type === "strength" ? "#10B981" : "#F59E0B";
  const bgColor = type === "strength" ? "rgba(16, 185, 129, 0.1)" : "rgba(245, 158, 11, 0.1)";

  const icon =
    type === "strength" ? (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5">
        <polyline points="20 6 9 17 4 12" />
      </svg>
    ) : (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.5">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    );

  return (
    <div
      style={{
        opacity: entryOpacity,
        transform: `translateX(${xOffset}px)`,
      }}
    >
      <div
        style={{
          background: bgColor,
          borderRadius: 20,
          padding: 28,
          border: `1px solid ${color}30`,
          width: 520,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            marginBottom: 20,
          }}
        >
          {icon}
          <span
            style={{
              color,
              fontSize: 24,
              fontWeight: 700,
            }}
          >
            {title}
          </span>
        </div>

        {/* Items - uses 20px font */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {items.map((item, i) => (
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
                  background: color,
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
  );
};
