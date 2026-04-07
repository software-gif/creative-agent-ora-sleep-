import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const LogoReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, from: 0.3, to: 1, durationInFrames: 30, config: { damping: 12 } });
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const glowIntensity = interpolate(frame, [20, 50], [0, 1], { extrapolateRight: "clamp" });
  const subtitleY = spring({ frame: Math.max(0, frame - 30), fps, from: 30, to: 0, durationInFrames: 20 });
  const subtitleOpacity = interpolate(frame, [30, 45], [0, 1], { extrapolateRight: "clamp" });

  // Rotating gradient angle
  const angle = interpolate(frame, [0, 90], [0, 360]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#050510",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* Animated gradient background orbs */}
      <div
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: `conic-gradient(from ${angle}deg, #8b5cf6, #06b6d4, #8b5cf6)`,
            opacity: 0.12 * glowIntensity,
            filter: "blur(100px)",
            top: "30%",
            left: "35%",
            transform: "translate(-50%, -50%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            width: 400,
            height: 400,
            borderRadius: "50%",
            background: "radial-gradient(circle, #d946ef 0%, transparent 70%)",
            opacity: 0.08 * glowIntensity,
            filter: "blur(80px)",
            bottom: "20%",
            right: "25%",
          }}
        />
      </div>

      {/* Logo Container */}
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
        }}
      >
        {/* Claude Logo Mark — Abstract diamond/spark */}
        <div
          style={{
            width: 120,
            height: 120,
            position: "relative",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: `conic-gradient(from ${angle}deg, #8b5cf6, #06b6d4, #d946ef, #8b5cf6)`,
              borderRadius: 28,
              transform: "rotate(45deg)",
              boxShadow: `0 0 ${40 * glowIntensity}px rgba(139,92,246,0.5)`,
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 4,
              background: "#0a0a1a",
              borderRadius: 24,
              transform: "rotate(45deg)",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              fontSize: 56,
              color: "#fff",
              fontWeight: 200,
              fontFamily: "system-ui, sans-serif",
            }}
          >
            ✦
          </div>
        </div>

        {/* Title */}
        <div
          style={{
            fontSize: 64,
            fontWeight: 700,
            fontFamily: "SF Pro Display, system-ui, sans-serif",
            background: `linear-gradient(135deg, #fff 30%, #8b5cf6 60%, #06b6d4 100%)`,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            letterSpacing: -2,
          }}
        >
          Claude Code
        </div>

        {/* Subtitle */}
        <div
          style={{
            opacity: subtitleOpacity,
            transform: `translateY(${subtitleY}px)`,
            fontSize: 24,
            color: "#888",
            fontFamily: "SF Pro Display, system-ui, sans-serif",
            fontWeight: 400,
            letterSpacing: 4,
            textTransform: "uppercase",
          }}
        >
          AI-Powered Development
        </div>
      </div>
    </AbsoluteFill>
  );
};
