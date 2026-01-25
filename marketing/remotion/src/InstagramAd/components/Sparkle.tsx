import { useCurrentFrame } from "remotion";

interface SparkleProps {
  size?: number;
  color?: string;
  x: number;
  y: number;
  delay?: number;
  rotationSpeed?: number;
}

export const Sparkle: React.FC<SparkleProps> = ({
  size = 40,
  color = "#0066FF",
  x,
  y,
  delay = 0,
  rotationSpeed = 0.5,
}) => {
  const frame = useCurrentFrame();
  const adjustedFrame = Math.max(0, frame - delay);
  const rotation = adjustedFrame * rotationSpeed;
  const scale = Math.sin(adjustedFrame * 0.08) * 0.2 + 0.8;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `rotate(${rotation}deg) scale(${scale})`,
        opacity: adjustedFrame > 0 ? 1 : 0,
      }}
    >
      <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
        {/* 4-point star */}
        <path d="M12 0L14 10L24 12L14 14L12 24L10 14L0 12L10 10L12 0Z" />
      </svg>
    </div>
  );
};
