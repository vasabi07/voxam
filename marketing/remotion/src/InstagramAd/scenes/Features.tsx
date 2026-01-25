import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FeatureCard } from "../components/FeatureCard";

export const Features: React.FC = () => {
  const frame = useCurrentFrame();

  // Title animation - simple fade (no spring)
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const titleY = interpolate(frame, [0, 20], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const features = [
    { title: "Voice Exams", icon: "voice" as const, color: "#0066FF" },
    { title: "Smart Questions", icon: "brain" as const, color: "#8A2BE2" },
    { title: "Detailed Reports", icon: "chart" as const, color: "#10B981" },
  ];

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
          gap: 40,
          padding: 40,
        }}
      >
        {/* Title - 48px headline */}
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            textAlign: "center",
          }}
        >
          <h1
            style={{
              color: "#000000",
              fontSize: 48,
              fontWeight: 700,
            }}
          >
            Everything you need
          </h1>
        </div>

        {/* Feature cards with Fluid Float */}
        <div
          style={{
            display: "flex",
            gap: 20,
            justifyContent: "center",
          }}
        >
          {features.map((feature, i) => (
            <FeatureCard
              key={i}
              title={feature.title}
              icon={feature.icon}
              color={feature.color}
              index={i}
            />
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
