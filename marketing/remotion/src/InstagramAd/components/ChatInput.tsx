import { useCurrentFrame, spring, useVideoConfig, interpolate } from "remotion";

interface ChatInputProps {
  text: string;
  showAttachment?: boolean;
  attachmentName?: string;
  typingSpeed?: number;
  startTypingFrame?: number;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  text,
  showAttachment = false,
  attachmentName = "chapter5.pdf",
  typingSpeed = 2,
  startTypingFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entry animation
  const entryScale = spring({
    frame,
    fps,
    config: { mass: 1, damping: 10, stiffness: 100 },
  });

  const entryOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Typing animation
  const adjustedFrame = Math.max(0, frame - startTypingFrame);
  const charsToShow = Math.floor(adjustedFrame / typingSpeed);
  const displayText = text.slice(0, charsToShow);
  const isTypingComplete = charsToShow >= text.length;

  // Attachment chip animation
  const attachmentStartFrame = startTypingFrame + text.length * typingSpeed + 10;
  const attachmentOpacity = interpolate(
    frame,
    [attachmentStartFrame, attachmentStartFrame + 10],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const attachmentScale = spring({
    frame: frame - attachmentStartFrame,
    fps,
    config: { mass: 1, damping: 10, stiffness: 120 },
  });

  return (
    <div
      style={{
        opacity: entryOpacity,
        transform: `scale(${Math.max(0, entryScale)})`,
      }}
    >
      <div
        style={{
          background: "#F3F4F6",
          borderRadius: 999,
          padding: "20px 32px",
          boxShadow: "0 20px 40px rgba(0,0,0,0.1)",
          border: "1px solid #E5E7EB",
          minWidth: 500,
          maxWidth: 700,
        }}
      >
        {/* Attachment chip */}
        {showAttachment && (
          <div
            style={{
              opacity: attachmentOpacity,
              transform: `scale(${Math.max(0, attachmentScale)})`,
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "#FFFFFF",
              borderRadius: 8,
              padding: "8px 12px",
              marginBottom: 12,
              border: "1px solid #E5E7EB",
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#0066FF"
              strokeWidth="2"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span style={{ color: "#0066FF", fontSize: 14, fontWeight: 500 }}>
              {attachmentName}
            </span>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#71717A"
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </div>
        )}

        {/* Input text */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1 }}>
            <span
              style={{
                color: displayText ? "#000000" : "#9CA3AF",
                fontSize: 32,
                fontWeight: 500,
              }}
            >
              {displayText || "Ask anything..."}
              {!isTypingComplete && displayText && (
                <span
                  style={{
                    opacity: Math.sin(frame * 0.2) > 0 ? 1 : 0,
                    color: "#0066FF",
                  }}
                >
                  |
                </span>
              )}
            </span>
          </div>

          {/* Send button */}
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: "50%",
              background: isTypingComplete && displayText ? "#0066FF" : "#E5E7EB",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "background 0.2s",
            }}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke={isTypingComplete && displayText ? "#FFFFFF" : "#9CA3AF"}
              strokeWidth="2"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
};
