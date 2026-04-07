import { AbsoluteFill, useCurrentFrame, interpolate, random } from "remotion";

const GRID_COLS = 24;
const GRID_ROWS = 14;
const PARTICLES = Array.from({ length: GRID_COLS * GRID_ROWS }, (_, i) => {
  const col = i % GRID_COLS;
  const row = Math.floor(i / GRID_COLS);
  return {
    baseX: (col / (GRID_COLS - 1)) * 1920,
    baseY: (row / (GRID_ROWS - 1)) * 1080,
    phase: random(i) * Math.PI * 2,
    speed: 0.5 + random(i + 100) * 1.5,
    size: 2 + random(i + 200) * 3,
    hue: random(i + 300) > 0.7 ? 180 : 270, // cyan or purple
  };
});

// Connection lines between nearby particles
const CONNECTIONS: Array<[number, number]> = [];
for (let i = 0; i < PARTICLES.length; i++) {
  for (let j = i + 1; j < PARTICLES.length; j++) {
    const dx = PARTICLES[i].baseX - PARTICLES[j].baseX;
    const dy = PARTICLES[i].baseY - PARTICLES[j].baseY;
    if (Math.sqrt(dx * dx + dy * dy) < 120) {
      CONNECTIONS.push([i, j]);
    }
  }
}

export const ParticleGrid: React.FC = () => {
  const frame = useCurrentFrame();

  const fadeIn = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [120, 150], [1, 0], { extrapolateRight: "clamp" });
  const masterOpacity = fadeIn * fadeOut;

  // Compute current positions
  const positions = PARTICLES.map((p) => ({
    x: p.baseX + Math.sin(frame * 0.02 * p.speed + p.phase) * 15,
    y: p.baseY + Math.cos(frame * 0.015 * p.speed + p.phase) * 10,
  }));

  // Wave that reveals particles from center
  const waveRadius = interpolate(frame, [0, 60], [0, 1500], { extrapolateRight: "clamp" });
  const centerX = 960;
  const centerY = 540;

  return (
    <AbsoluteFill style={{ backgroundColor: "#060612" }}>
      <svg width={1920} height={1080} style={{ opacity: masterOpacity }}>
        {/* Connection lines */}
        {CONNECTIONS.map(([i, j], idx) => {
          const a = positions[i];
          const b = positions[j];
          const midDist = Math.sqrt(
            ((a.x + b.x) / 2 - centerX) ** 2 + ((a.y + b.y) / 2 - centerY) ** 2
          );
          if (midDist > waveRadius) return null;

          return (
            <line
              key={idx}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="rgba(139,92,246,0.12)"
              strokeWidth={0.5}
            />
          );
        })}

        {/* Particles */}
        {PARTICLES.map((p, i) => {
          const pos = positions[i];
          const dist = Math.sqrt((pos.x - centerX) ** 2 + (pos.y - centerY) ** 2);
          if (dist > waveRadius) return null;

          const localOpacity = interpolate(dist, [waveRadius - 100, waveRadius], [1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          const pulse = 0.5 + Math.sin(frame * 0.05 + p.phase) * 0.5;

          return (
            <circle
              key={i}
              cx={pos.x}
              cy={pos.y}
              r={p.size * (0.8 + pulse * 0.4)}
              fill={`hsla(${p.hue}, 70%, 65%, ${localOpacity * (0.4 + pulse * 0.3)})`}
            />
          );
        })}
      </svg>

      {/* Center text */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          opacity: interpolate(frame, [40, 60, 110, 135], [0, 1, 1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            fontFamily: "SF Pro Display, system-ui, sans-serif",
            background: "linear-gradient(135deg, #c084fc, #22d3ee)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            letterSpacing: -3,
          }}
        >
          Ora Sleep
        </div>
        <div
          style={{
            fontSize: 26,
            color: "#666",
            fontFamily: "SF Pro Display, system-ui, sans-serif",
            marginTop: 12,
            letterSpacing: 6,
            textTransform: "uppercase",
          }}
        >
          Claude Code × Gemini
        </div>
      </div>
    </AbsoluteFill>
  );
};
