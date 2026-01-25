import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from "remotion";

export const MyComposition = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo fade and scale
  const logoOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const logoScale = spring({
    frame,
    fps,
    config: {
      damping: 12,
      stiffness: 100,
    },
  });

  // Tagline slide up
  const taglineY = spring({
    frame: frame - 15,
    fps,
    config: {
      damping: 15,
      stiffness: 80,
    },
  });

  const taglineOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill className="bg-slate-900 flex items-center justify-center">
      {/* Gradient background */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(99, 102, 241, 0.15) 0%, transparent 70%)",
        }}
      />

      <div className="flex flex-col items-center gap-6">
        {/* Logo/Brand */}
        <div
          style={{
            opacity: logoOpacity,
            transform: `scale(${logoScale})`,
          }}
          className="text-7xl font-bold"
        >
          <span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">
            VOXAM
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            opacity: taglineOpacity,
            transform: `translateY(${interpolate(taglineY, [0, 1], [20, 0])}px)`,
          }}
          className="text-xl text-slate-400"
        >
          AI-Powered Voice Exams
        </div>
      </div>
    </AbsoluteFill>
  );
};
