import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FloatingFolder } from "../components/FloatingFolder";

const BLUE = "#0066FF";

export const LogoRevealSimple: React.FC = () => {
  const frame = useCurrentFrame();

  // Folder entrance animation
  const folderOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const folderScale = interpolate(frame, [0, 20], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // VOXAM logo appears after folder
  const logoStartFrame = 15;
  const logoOpacity = interpolate(
    frame,
    [logoStartFrame, logoStartFrame + 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const logoScale = interpolate(
    frame,
    [logoStartFrame, logoStartFrame + 20],
    [0.9, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

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
          gap: 20,
        }}
      >
        {/* Floating folder with documents */}
        <div
          style={{
            opacity: folderOpacity,
            transform: `scale(${folderScale})`,
          }}
        >
          <FloatingFolder size={140} color={BLUE} showDocuments={true} />
        </div>

        {/* VOXAM logo */}
        <div
          style={{
            opacity: logoOpacity,
            transform: `scale(${logoScale})`,
          }}
        >
          <div
            style={{
              fontSize: 120,
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: BLUE,
            }}
          >
            VOXAM
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
