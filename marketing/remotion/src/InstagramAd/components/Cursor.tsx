import { useCurrentFrame, interpolate } from "remotion";

interface CursorPoint {
  x: number;
  y: number;
  frame: number;
  click?: boolean;
}

interface CursorProps {
  path: CursorPoint[];
  color?: string;
}

export const Cursor: React.FC<CursorProps> = ({
  path,
  color = "#000000",
}) => {
  const frame = useCurrentFrame();

  // Find current position
  let currentX = path[0]?.x || 0;
  let currentY = path[0]?.y || 0;
  let isClicking = false;

  for (let i = 0; i < path.length - 1; i++) {
    const from = path[i];
    const to = path[i + 1];

    if (frame >= from.frame && frame <= to.frame) {
      // Interpolate between points
      const progress = interpolate(
        frame,
        [from.frame, to.frame],
        [0, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
      );

      currentX = interpolate(progress, [0, 1], [from.x, to.x]);
      currentY = interpolate(progress, [0, 1], [from.y, to.y]);

      // Check if clicking at current point
      if (to.click && frame >= to.frame - 5) {
        isClicking = true;
      }
      break;
    } else if (frame > to.frame) {
      currentX = to.x;
      currentY = to.y;

      // Check recent click
      if (to.click && frame <= to.frame + 10) {
        isClicking = true;
      }
    }
  }

  // Click animation
  const clickScale = isClicking ? 0.8 : 1;
  const rippleOpacity = isClicking
    ? interpolate(frame % 15, [0, 15], [0.5, 0])
    : 0;
  const rippleScale = isClicking
    ? interpolate(frame % 15, [0, 15], [1, 2])
    : 1;

  return (
    <div
      style={{
        position: "absolute",
        left: currentX,
        top: currentY,
        pointerEvents: "none",
        zIndex: 1000,
      }}
    >
      {/* Click ripple */}
      {isClicking && (
        <div
          style={{
            position: "absolute",
            width: 40,
            height: 40,
            borderRadius: "50%",
            background: "#9CA3AF",
            opacity: rippleOpacity,
            transform: `translate(-50%, -50%) scale(${rippleScale})`,
          }}
        />
      )}

      {/* Cursor */}
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        style={{
          transform: `scale(${clickScale})`,
          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.2))",
        }}
      >
        <path
          d="M5.5 3.21V20.8c0 .45.54.67.85.35l4.86-4.86a.5.5 0 0 1 .35-.15h6.87a.5.5 0 0 0 .35-.85L6.35 2.86a.5.5 0 0 0-.85.35z"
          fill={color}
          stroke="#FFFFFF"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  );
};
