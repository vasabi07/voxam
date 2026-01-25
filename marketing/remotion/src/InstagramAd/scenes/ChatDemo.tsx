import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { ChatInput } from "../components/ChatInput";

export const ChatDemo: React.FC = () => {
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

  // Subtitle appears after title
  const subtitleStartFrame = 20;
  const subtitleOpacity = interpolate(
    frame,
    [subtitleStartFrame, subtitleStartFrame + 15],
    [0, 1],
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
          gap: 32,
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
              marginBottom: 12,
            }}
          >
            Just ask
          </h1>
          <div style={{ opacity: subtitleOpacity }}>
            {/* Body - 24px */}
            <p
              style={{
                color: "#71717A",
                fontSize: 24,
              }}
            >
              Practice with AI-powered exams
            </p>
          </div>
        </div>

        {/* Chat input with typing */}
        <ChatInput
          text="Exam me on chapter 5"
          showAttachment={true}
          attachmentName="biology-notes.pdf"
          typingSpeed={3}
          startTypingFrame={40}
        />

        {/* Response preview */}
        <ResponsePreview frame={frame} />
      </div>
    </AbsoluteFill>
  );
};

// AI Response preview
const ResponsePreview: React.FC<{ frame: number }> = ({ frame }) => {
  const startFrame = 130;
  const adjustedFrame = frame - startFrame;

  // Simple fade entry (no spring)
  const opacity = interpolate(adjustedFrame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const entryY = interpolate(adjustedFrame, [0, 20], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtle float
  const floatY = Math.sin((frame - startFrame) / 30) * 4;

  if (adjustedFrame < 0) return null;

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${entryY + floatY}px)`,
      }}
    >
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: 20,
          padding: 24,
          boxShadow: "0 16px 32px rgba(0,0,0,0.1)",
          border: "1px solid #E5E7EB",
          maxWidth: 540,
        }}
      >
        {/* AI indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 14,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 10,
              background: "#0066FF15",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#0066FF"
              strokeWidth="2"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          {/* Body font - 24px */}
          <span style={{ color: "#71717A", fontSize: 16, fontWeight: 500 }}>
            VOXAM
          </span>
        </div>

        {/* Response text - 24px body font */}
        <p
          style={{
            color: "#000000",
            fontSize: 20,
            lineHeight: 1.5,
          }}
        >
          Great! I've created a{" "}
          <span style={{ color: "#0066FF", fontWeight: 600 }}>10-question exam</span> on
          Chapter 5: Cell Biology. Ready to start your{" "}
          <span style={{ color: "#0066FF", fontWeight: 600 }}>voice exam</span>?
        </p>
      </div>
    </div>
  );
};
