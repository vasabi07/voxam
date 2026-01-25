import { AbsoluteFill, interpolate, spring, useCurrentFrame } from "remotion";
import { Sparkle } from "../components/Sparkle";

const BLUE = "#0066FF";

export const CTA: React.FC = () => {
  const frame = useCurrentFrame();

  // Logo animation with spring physics
  const logoSpring = spring({
    frame,
    fps: 30,
    config: { mass: 1, damping: 12, stiffness: 100 },
  });

  const logoOpacity = logoSpring;
  const logoScale = 0.85 + logoSpring * 0.15;

  // Button animation with spring
  const buttonStartFrame = 20;
  const buttonSpring = spring({
    frame: Math.max(0, frame - buttonStartFrame),
    fps: 30,
    config: { mass: 1, damping: 12, stiffness: 100 },
  });

  const buttonOpacity = buttonSpring;
  const buttonScale = 0.85 + buttonSpring * 0.15;

  // Fluid float for button - constant gentle motion
  const buttonFloatY = Math.sin(frame / 30) * 5;
  const buttonFloatX = Math.cos(frame / 45) * 3;

  // Sheen effect on button (highlight sweep)
  const sheenStartFrame = buttonStartFrame + 30;
  const sheenPosition = interpolate(
    frame,
    [sheenStartFrame, sheenStartFrame + 20],
    [100, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // URL animation with spring
  const urlStartFrame = 40;
  const urlSpring = spring({
    frame: Math.max(0, frame - urlStartFrame),
    fps: 30,
    config: { mass: 1, damping: 14, stiffness: 100 },
  });

  const urlOpacity = urlSpring;

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

      {/* Sparkles with Fluid Float */}
      <Sparkle x={80} y={380} size={40} color={BLUE} delay={10} />
      <Sparkle x={960} y={480} size={48} color="#8A2BE2" delay={15} rotationSpeed={0.6} />
      <Sparkle x={130} y={1380} size={36} color={BLUE} delay={20} rotationSpeed={0.4} />
      <Sparkle x={900} y={1330} size={44} color="#8A2BE2" delay={25} />
      <Sparkle x={520} y={280} size={36} color={BLUE} delay={30} rotationSpeed={0.8} />

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: 48,
        }}
      >
        {/* VOXAM Logo - 120px headline */}
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

        {/* Tagline - 32px body */}
        <div
          style={{
            opacity: logoOpacity,
            color: "#71717A",
            fontSize: 32,
            fontWeight: 500,
          }}
        >
          Voice-First Learning
        </div>

        {/* CTA Button with Sheen effect + Fluid Float */}
        <div
          style={{
            opacity: buttonOpacity,
            transform: `translateY(${buttonFloatY}px) translateX(${buttonFloatX}px) scale(${buttonScale})`,
            marginTop: 24,
          }}
        >
          <div
            style={{
              position: "relative",
              background: BLUE,
              borderRadius: 999,
              padding: "28px 80px",
              color: "#FFFFFF",
              fontWeight: 700,
              fontSize: 40,
              boxShadow: "0 20px 40px rgba(0, 102, 255, 0.3)",
              overflow: "hidden",
            }}
          >
            {/* Button text */}
            <span style={{ position: "relative", zIndex: 1 }}>Try Free</span>

            {/* Sheen overlay */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: `linear-gradient(120deg, transparent 30%, rgba(255,255,255,0.4) 50%, transparent 70%)`,
                backgroundSize: "200% 100%",
                backgroundPosition: `${sheenPosition}% 0`,
                pointerEvents: "none",
              }}
            />
          </div>
        </div>

        {/* Website URL - 32px body */}
        <div
          style={{
            opacity: urlOpacity,
            color: "#71717A",
            fontSize: 32,
            letterSpacing: "0.1em",
            marginTop: 16,
          }}
        >
          voxam.in
        </div>
      </div>
    </AbsoluteFill>
  );
};
