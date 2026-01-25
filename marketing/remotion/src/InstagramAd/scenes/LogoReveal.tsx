import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FloatingFolder } from "../components/FloatingFolder";
import { WordByWordText } from "../components/WordByWordText";

const BLUE = "#0066FF";

export const LogoReveal: React.FC = () => {
  const frame = useCurrentFrame();

  // Folder entrance animation - simple fade (no spring)
  const folderOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const folderScale = interpolate(frame, [0, 20], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // "Introducing" text appears
  const introStartFrame = 20;
  const introOpacity = interpolate(
    frame,
    [introStartFrame, introStartFrame + 15],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // VOXAM logo appears
  const logoStartFrame = 40;
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
          <FloatingFolder size={180} color={BLUE} showDocuments={true} />
        </div>

        {/* "Introducing" text - 32px body */}
        <div
          style={{
            opacity: introOpacity,
            marginTop: 20,
          }}
        >
          <WordByWordText
            text="Introducing"
            fontSize={32}
            fontWeight={500}
            color="#71717A"
            startFrame={introStartFrame}
            wordDelay={4}
          />
        </div>

        {/* VOXAM logo - 120px headline */}
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
