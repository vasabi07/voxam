import { useCurrentFrame, interpolate } from "remotion";
import { Sparkle } from "./Sparkle";

interface FloatingFolderProps {
  size?: number;
  color?: string;
  showDocuments?: boolean;
}

export const FloatingFolder: React.FC<FloatingFolderProps> = ({
  size = 200,
  color = "#0066FF",
  showDocuments = true,
}) => {
  const frame = useCurrentFrame();

  // Fluid Float animation for main folder
  const floatY = Math.sin(frame / 30) * 10;
  const floatX = Math.cos(frame / 45) * 5;
  const floatRotation = Math.sin(frame / 60) * 2;

  // Simple fade entry animation (no spring)
  const entryOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const entryScale = interpolate(frame, [0, 20], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Documents flying out
  const documents = [
    { delay: 15, x: -80, y: -60, rotation: -15, phase: 0 },
    { delay: 22, x: 70, y: -50, rotation: 12, phase: 1.2 },
    { delay: 30, x: -60, y: 40, rotation: -8, phase: 2.4 },
    { delay: 38, x: 80, y: 50, rotation: 10, phase: 3.6 },
  ];

  return (
    <div
      style={{
        position: "relative",
        width: size * 2,
        height: size * 2,
        opacity: entryOpacity,
        transform: `scale(${entryScale}) translateY(${floatY}px) translateX(${floatX}px) rotate(${floatRotation}deg)`,
      }}
    >
      {/* Sparkles with Fluid Float - sizes 36-48px */}
      <Sparkle x={-40} y={0} size={36} color={color} delay={10} />
      <Sparkle x={size * 2 - 20} y={20} size={48} color="#8A2BE2" delay={15} rotationSpeed={0.7} />
      <Sparkle x={size} y={-30} size={36} color={color} delay={20} rotationSpeed={0.4} />
      <Sparkle x={10} y={size * 2 - 20} size={44} color="#8A2BE2" delay={25} />

      {/* Flying documents with Fluid Float */}
      {showDocuments &&
        documents.map((doc, i) => {
          const docFrame = frame - doc.delay;
          const docOpacity = interpolate(docFrame, [0, 15], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          // Simple scale instead of spring
          const docScale = interpolate(docFrame, [0, 15], [0.5, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const docY = interpolate(docFrame, [0, 20], [0, doc.y], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const docX = interpolate(docFrame, [0, 20], [0, doc.x], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          // Fluid Float for documents
          const docFloatY = Math.sin(frame / 30 + doc.phase) * 6;
          const docFloatX = Math.cos(frame / 45 + doc.phase) * 3;

          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: size,
                top: size,
                opacity: docOpacity,
                transform: `translate(${docX + docFloatX}px, ${docY + docFloatY}px) rotate(${doc.rotation}deg) scale(${Math.max(0, docScale)})`,
              }}
            >
              <div
                style={{
                  width: 60,
                  height: 75,
                  background: "#FFFFFF",
                  borderRadius: 8,
                  boxShadow: "0 15px 35px rgba(0,0,0,0.15)",
                  border: "1px solid #E5E7EB",
                  display: "flex",
                  flexDirection: "column",
                  padding: 8,
                  gap: 4,
                }}
              >
                {/* Document lines */}
                <div style={{ background: "#E5E7EB", height: 4, borderRadius: 2, width: "80%" }} />
                <div style={{ background: "#E5E7EB", height: 4, borderRadius: 2, width: "60%" }} />
                <div style={{ background: "#E5E7EB", height: 4, borderRadius: 2, width: "70%" }} />
                <div style={{ background: color, height: 4, borderRadius: 2, width: "40%", marginTop: 8 }} />
              </div>
            </div>
          );
        })}

      {/* Main folder */}
      <div
        style={{
          position: "absolute",
          left: size / 2,
          top: size / 2,
          width: size,
          height: size * 0.8,
        }}
      >
        {/* Folder shadow */}
        <div
          style={{
            position: "absolute",
            inset: -10,
            background: color,
            opacity: 0.2,
            filter: "blur(30px)",
            borderRadius: 24,
          }}
        />
        {/* Folder back */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: size * 0.7,
            background: `linear-gradient(135deg, ${color} 0%, #0052CC 100%)`,
            borderRadius: 16,
          }}
        />
        {/* Folder tab */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: size * 0.4,
            height: size * 0.15,
            background: `linear-gradient(135deg, ${color} 0%, #0052CC 100%)`,
            borderRadius: "12px 12px 0 0",
          }}
        />
        {/* Folder front */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: size * 0.65,
            background: `linear-gradient(180deg, #3388FF 0%, ${color} 100%)`,
            borderRadius: "0 16px 16px 16px",
          }}
        />
        {/* Folder highlight */}
        <div
          style={{
            position: "absolute",
            top: size * 0.15,
            left: 10,
            right: 10,
            height: 2,
            background: "rgba(255,255,255,0.3)",
            borderRadius: 1,
          }}
        />
      </div>
    </div>
  );
};
