import { useCurrentFrame, interpolate } from "remotion";

interface FeatureCardProps {
  title: string;
  icon: "voice" | "brain" | "chart";
  color?: string;
  index: number;
}

export const FeatureCard: React.FC<FeatureCardProps> = ({
  title,
  icon,
  color = "#0066FF",
  index,
}) => {
  const frame = useCurrentFrame();

  // Staggered entry - simple fade + slide up
  const staggerFrame = frame - index * 8;

  const entryOpacity = interpolate(staggerFrame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const entryY = interpolate(staggerFrame, [0, 20], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fluid Float animation - each card has unique phase offsets
  const phaseOffset = index * 1.5;
  const floatY = Math.sin(frame / 30 + phaseOffset) * 8;
  const floatX = Math.cos(frame / 45 + phaseOffset) * 4;
  const floatRotation = Math.sin(frame / 60 + phaseOffset) * 1.5;

  const icons = {
    voice: (
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
      </svg>
    ),
    brain: (
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54" />
        <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54" />
      </svg>
    ),
    chart: (
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <line x1="18" y1="20" x2="18" y2="10" strokeLinecap="round" />
        <line x1="12" y1="20" x2="12" y2="4" strokeLinecap="round" />
        <line x1="6" y1="20" x2="6" y2="14" strokeLinecap="round" />
      </svg>
    ),
  };

  return (
    <div
      style={{
        opacity: entryOpacity,
        transform: `translateY(${entryY + floatY}px) translateX(${floatX}px) rotate(${floatRotation}deg)`,
      }}
    >
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: 24,
          padding: 28,
          boxShadow: "0 20px 40px rgba(0,0,0,0.12)",
          border: "1px solid #E5E7EB",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
          width: 240,
          height: 200,
        }}
      >
        {/* Icon container */}
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: 18,
            background: `${color}15`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {icons[icon]}
        </div>

        {/* Title - single font size only */}
        <div
          style={{
            color: "#000000",
            fontSize: 20,
            fontWeight: 600,
            textAlign: "center",
            whiteSpace: "nowrap",
          }}
        >
          {title}
        </div>
      </div>
    </div>
  );
};
