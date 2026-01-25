import { useCurrentFrame, interpolate, spring } from "remotion";

interface DocumentCardProps {
  title: string;
  subtitle: string;
  color: string;
  icon: "pdf" | "book" | "notes" | "file";
  index: number;
  scrollOffset: number;
  isActive?: boolean;
}

const DocumentCard: React.FC<DocumentCardProps> = ({
  title,
  subtitle,
  color,
  icon,
  index,
  scrollOffset,
  isActive = true,
}) => {
  const frame = useCurrentFrame();

  // Staggered spring entry - each card enters 3 frames after the previous
  const staggerDelay = index * 3;
  const staggerFrame = Math.max(0, frame - staggerDelay);

  // Spring physics for entry animation
  const entrySpring = spring({
    frame: staggerFrame,
    fps: 30,
    config: { mass: 1, damping: 12, stiffness: 100 },
  });

  // Scale bounces from 0.8 to 1.0
  const entryScale = 0.8 + entrySpring * 0.2;
  const entryOpacity = entrySpring;

  // Fluid Float animation - each card has unique phase offsets (constant gentle motion)
  const phaseOffset = index * 1.2;
  const floatY = Math.sin(frame / 30 + phaseOffset) * 6;
  const floatX = Math.cos(frame / 45 + phaseOffset) * 3;
  const floatRotation = Math.sin(frame / 60 + phaseOffset) * 1.5;

  // Active/inactive dimming for cognitive focus
  const targetOpacity = isActive ? 1 : 0.4;
  const targetScale = isActive ? 1.05 : 1;

  const icons = {
    pdf: (
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <path d="M9 15h6" />
        <path d="M9 11h6" />
      </svg>
    ),
    book: (
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    ),
    notes: (
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
        <path d="M12 18v-6" />
        <path d="M9 15h6" />
      </svg>
    ),
    file: (
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
        <polyline points="13 2 13 9 20 9" />
      </svg>
    ),
  };

  return (
    <div
      style={{
        transform: `translateY(${scrollOffset + floatY}px) translateX(${floatX}px) rotate(${floatRotation}deg) scale(${entryScale * targetScale})`,
        opacity: entryOpacity * targetOpacity,
        transition: "opacity 0.3s ease, transform 0.3s ease",
      }}
    >
      <div
        style={{
          width: 480,
          height: 300,
          background: "#FFFFFF",
          borderRadius: 24,
          boxShadow: "0 24px 48px rgba(0,0,0,0.14)",
          padding: 32,
          display: "flex",
          flexDirection: "column",
          border: "1px solid #E5E7EB",
        }}
      >
        <div
          style={{
            width: 100,
            height: 100,
            borderRadius: 20,
            background: `${color}15`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 20,
          }}
        >
          {icons[icon]}
        </div>
        <div style={{ color: "#000000", fontSize: 28, fontWeight: 600, marginBottom: 8 }}>
          {title}
        </div>
        <div style={{ color: "#71717A", fontSize: 22 }}>{subtitle}</div>
      </div>
    </div>
  );
};

interface DocumentGridProps {
  activeIndex?: number;
}

export const DocumentGrid: React.FC<DocumentGridProps> = ({ activeIndex }) => {
  const frame = useCurrentFrame();

  // Scroll animation - documents scroll up (reduced movement)
  const scrollOffset = interpolate(frame, [0, 120], [60, -120], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const documents = [
    { title: "Biology Notes", subtitle: "Chapter 5 - Cells", color: "#0066FF", icon: "notes" as const },
    { title: "Physics Textbook", subtitle: "Thermodynamics", color: "#8A2BE2", icon: "book" as const },
    { title: "Chemistry PDF", subtitle: "Organic Reactions", color: "#10B981", icon: "pdf" as const },
    { title: "Math Formulas", subtitle: "Calculus II", color: "#F59E0B", icon: "file" as const },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gap: 16,
        padding: 16,
      }}
    >
      {documents.map((doc, i) => (
        <DocumentCard
          key={i}
          {...doc}
          index={i}
          scrollOffset={scrollOffset + (i % 2 === 0 ? 0 : 20)}
          isActive={activeIndex === undefined || activeIndex === i}
        />
      ))}
    </div>
  );
};
