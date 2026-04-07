import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

const LINES = [
  { text: "$ claude", delay: 0, color: "#22d3ee" },
  { text: "╭─────────────────────────────────╮", delay: 15, color: "#444" },
  { text: "│  Claude Code v1.0               │", delay: 18, color: "#a78bfa" },
  { text: "│  Powered by Claude Opus 4.6     │", delay: 21, color: "#a78bfa" },
  { text: "╰─────────────────────────────────╯", delay: 24, color: "#444" },
  { text: "", delay: 30, color: "#fff" },
  { text: "> Analyzing codebase...", delay: 35, color: "#fbbf24" },
  { text: "  ✓ 847 files indexed", delay: 55, color: "#34d399" },
  { text: "  ✓ Dependencies resolved", delay: 65, color: "#34d399" },
  { text: "  ✓ Context loaded", delay: 75, color: "#34d399" },
  { text: "", delay: 80, color: "#fff" },
  { text: "> Ready. How can I help?", delay: 85, color: "#22d3ee" },
  { text: "  █", delay: 95, color: "#fff" },
];

export const TerminalScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const windowScale = spring({ frame, fps, from: 0.9, to: 1, durationInFrames: 20 });
  const windowOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0a0a0a",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* Ambient glow */}
      <div
        style={{
          position: "absolute",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%)",
          top: "20%",
          left: "30%",
          filter: "blur(60px)",
        }}
      />

      {/* Terminal Window */}
      <div
        style={{
          opacity: windowOpacity,
          transform: `scale(${windowScale})`,
          width: 900,
          background: "linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%)",
          borderRadius: 16,
          border: "1px solid #333",
          boxShadow: "0 40px 80px rgba(0,0,0,0.6), 0 0 60px rgba(139,92,246,0.1)",
          overflow: "hidden",
        }}
      >
        {/* Title Bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            padding: "14px 20px",
            background: "#1a1a2e",
            borderBottom: "1px solid #222",
            gap: 8,
          }}
        >
          <div style={{ width: 14, height: 14, borderRadius: "50%", background: "#ff5f57" }} />
          <div style={{ width: 14, height: 14, borderRadius: "50%", background: "#febc2e" }} />
          <div style={{ width: 14, height: 14, borderRadius: "50%", background: "#28c840" }} />
          <span
            style={{
              marginLeft: 16,
              color: "#666",
              fontSize: 14,
              fontFamily: "SF Mono, Menlo, monospace",
            }}
          >
            claude-code — zsh
          </span>
        </div>

        {/* Terminal Content */}
        <div style={{ padding: "24px 28px", minHeight: 380 }}>
          {LINES.map((line, i) => {
            const charProgress = interpolate(
              frame,
              [line.delay, line.delay + Math.max(line.text.length * 0.4, 5)],
              [0, line.text.length],
              { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
            );

            if (frame < line.delay) return null;

            const visibleText = line.text.slice(0, Math.floor(charProgress));

            return (
              <div
                key={i}
                style={{
                  fontFamily: "SF Mono, Menlo, Consolas, monospace",
                  fontSize: 18,
                  lineHeight: 1.7,
                  color: line.color,
                  minHeight: 30,
                  whiteSpace: "pre",
                }}
              >
                {visibleText}
                {/* Blinking cursor on last visible line */}
                {i === LINES.length - 1 &&
                  frame >= line.delay &&
                  Math.floor(frame / 15) % 2 === 0 && (
                    <span style={{ color: "#22d3ee" }}>▌</span>
                  )}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
