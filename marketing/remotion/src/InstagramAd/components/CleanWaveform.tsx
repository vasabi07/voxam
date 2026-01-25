import { useCurrentFrame, spring, interpolate } from "remotion";

interface CleanWaveformProps {
  barCount?: number;
  width?: number;
  height?: number;
  color?: string;
  isActive?: boolean;
  delayStart?: number;
}

export const CleanWaveform: React.FC<CleanWaveformProps> = ({
  barCount = 20,
  width = 400,
  height = 60,
  color = "#0066FF",
  isActive = true,
  delayStart = 0,
}) => {
  const frame = useCurrentFrame();

  const barWidth = Math.max(8, width / (barCount * 2));
  const activeFrame = Math.max(0, frame - delayStart);

  // Spring physics for entry animation
  const entrySpring = spring({
    frame: activeFrame,
    fps: 30,
    config: { mass: 1, damping: 12, stiffness: 100 },
  });

  const opacity = entrySpring;
  const scale = 0.8 + entrySpring * 0.2;

  return (
    <div
      style={{
        width,
        height,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: barWidth * 0.6,
        opacity,
        transform: `scaleY(${scale})`,
      }}
    >
      {Array.from({ length: barCount }).map((_, i) => {
        // Each bar has its own phase for natural variation
        const phase = i * 0.7;
        const speed = 0.12 + (i % 3) * 0.02;

        // Animate bar height with smoother transitions
        const baseHeight = isActive
          ? Math.sin(activeFrame * speed + phase) * 0.4 + 0.55
          : 0.15;

        // Add some randomness based on bar index
        const heightVariation = (Math.sin(i * 2.5) * 0.2 + 0.8) * baseHeight;

        // Calculate actual height
        const barHeight = Math.max(0.1, heightVariation) * height;

        // Subtle opacity variation
        const barOpacity = interpolate(heightVariation, [0.2, 1], [0.65, 1]);

        return (
          <div
            key={i}
            style={{
              width: barWidth,
              height: barHeight,
              backgroundColor: color,
              borderRadius: barWidth / 2,
              opacity: barOpacity,
            }}
          />
        );
      })}
    </div>
  );
};
