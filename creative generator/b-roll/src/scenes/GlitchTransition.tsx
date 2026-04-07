import { AbsoluteFill, useCurrentFrame, interpolate, random } from "remotion";

export const GlitchTransition: React.FC = () => {
  const frame = useCurrentFrame();

  const intensity = interpolate(frame, [0, 15, 30, 45, 60], [0, 1, 1, 0.5, 0], {
    extrapolateRight: "clamp",
  });

  const flash = frame >= 12 && frame <= 16 ? 1 : 0;

  // Generate glitch slices
  const slices = Array.from({ length: 12 }, (_, i) => {
    const seed = i * 100 + Math.floor(frame / 2);
    const offsetX = (random(seed) - 0.5) * 200 * intensity;
    const height = 30 + random(seed + 1) * 70;
    const y = random(seed + 2) * 1080;
    const hue = random(seed + 3) * 360;

    return { offsetX, height, y, hue };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {/* Horizontal glitch slices */}
      {slices.map((slice, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: 0,
            top: slice.y,
            width: "100%",
            height: slice.height,
            transform: `translateX(${slice.offsetX}px)`,
            background: `linear-gradient(90deg, transparent, hsla(${slice.hue}, 80%, 60%, ${0.15 * intensity}), transparent)`,
            opacity: intensity,
          }}
        />
      ))}

      {/* RGB split lines */}
      {frame % 3 === 0 && intensity > 0.3 && (
        <>
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(255,0,0,0.05)",
              transform: `translateX(${3 * intensity}px)`,
              mixBlendMode: "screen",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(0,255,255,0.05)",
              transform: `translateX(${-3 * intensity}px)`,
              mixBlendMode: "screen",
            }}
          />
        </>
      )}

      {/* Flash */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "#fff",
          opacity: flash * 0.8,
        }}
      />

      {/* Scan lines */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.15) 2px, rgba(0,0,0,0.15) 4px)",
          opacity: intensity * 0.5,
        }}
      />
    </AbsoluteFill>
  );
};
