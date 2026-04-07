import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

const CODE_BLOCKS = [
  {
    code: `import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const message = await client.messages.create({
  model: "claude-opus-4-6",
  max_tokens: 1024,
  messages: [
    { role: "user", content: "Build me something amazing" }
  ],
});`,
    x: -50,
    y: -200,
    speed: 0.8,
  },
  {
    code: `def analyze_codebase(path: str) -> Report:
    files = glob("**/*.py", root_dir=path)
    ast_trees = [parse(f) for f in files]

    dependencies = resolve_imports(ast_trees)
    complexity = calculate_complexity(ast_trees)

    return Report(
        files=len(files),
        complexity=complexity,
        suggestions=generate_fixes(ast_trees),
    )`,
    x: 100,
    y: 100,
    speed: 0.6,
  },
  {
    code: `model GeminiNano2 {
  id        String   @id @default(uuid())
  benchmark Float    @default(0)
  tasks     Task[]

  @@map("nano_banana_2")
}`,
    x: -200,
    y: 350,
    speed: 1.0,
  },
];

export const CodeFlow: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#060612",
        overflow: "hidden",
      }}
    >
      {/* Grid background */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(139,92,246,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(139,92,246,0.05) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          transform: `translateY(${interpolate(frame, [0, 150], [0, -30])}px)`,
        }}
      />

      {/* Floating code blocks */}
      {CODE_BLOCKS.map((block, i) => {
        const fadeIn = interpolate(frame, [i * 15, i * 15 + 20], [0, 1], {
          extrapolateRight: "clamp",
          extrapolateLeft: "clamp",
        });
        const floatY = Math.sin((frame + i * 40) * 0.03) * 12;
        const floatX = Math.cos((frame + i * 60) * 0.02) * 8;
        const drift = frame * block.speed * 0.3;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `calc(50% + ${block.x + floatX}px)`,
              top: `calc(50% + ${block.y + floatY - drift}px)`,
              transform: "translate(-50%, -50%)",
              opacity: fadeIn * interpolate(frame, [120, 150], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
            }}
          >
            <div
              style={{
                background: "rgba(15, 15, 30, 0.85)",
                border: "1px solid rgba(139, 92, 246, 0.2)",
                borderRadius: 12,
                padding: "20px 24px",
                backdropFilter: "blur(20px)",
                boxShadow: "0 20px 60px rgba(0,0,0,0.4), 0 0 30px rgba(139,92,246,0.05)",
                maxWidth: 580,
              }}
            >
              <pre
                style={{
                  fontFamily: "SF Mono, Menlo, Consolas, monospace",
                  fontSize: 15,
                  lineHeight: 1.6,
                  color: "#c4b5fd",
                  margin: 0,
                  whiteSpace: "pre-wrap",
                }}
              >
                {colorizeCode(block.code, frame, i)}
              </pre>
            </div>
          </div>
        );
      })}

      {/* Center title overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          opacity: interpolate(frame, [40, 60, 110, 130], [0, 0.9, 0.9, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div
          style={{
            fontSize: 48,
            fontWeight: 700,
            fontFamily: "SF Pro Display, system-ui, sans-serif",
            color: "#fff",
            textShadow: "0 0 40px rgba(139,92,246,0.4)",
            letterSpacing: -1,
          }}
        >
          Code in Motion
        </div>
      </div>
    </AbsoluteFill>
  );
};

function colorizeCode(code: string, _frame: number, _blockIndex: number) {
  // Simple syntax highlighting via spans
  return code.split("\n").map((line, lineIdx) => {
    let colored = line
      .replace(
        /(import|from|const|await|def|return|model|class)\b/g,
        (m) => `%%KW%%${m}%%/KW%%`
      )
      .replace(
        /(".*?"|'.*?'|`.*?`)/g,
        (m) => `%%STR%%${m}%%/STR%%`
      )
      .replace(
        /(@\w+)/g,
        (m) => `%%DEC%%${m}%%/DEC%%`
      );

    const parts: React.ReactNode[] = [];
    let remaining = colored;
    let key = 0;

    while (remaining.length > 0) {
      const kwStart = remaining.indexOf("%%KW%%");
      const strStart = remaining.indexOf("%%STR%%");
      const decStart = remaining.indexOf("%%DEC%%");

      const indices = [
        kwStart >= 0 ? kwStart : Infinity,
        strStart >= 0 ? strStart : Infinity,
        decStart >= 0 ? decStart : Infinity,
      ];
      const minIdx = Math.min(...indices);

      if (minIdx === Infinity) {
        parts.push(remaining);
        break;
      }

      if (minIdx > 0) {
        parts.push(remaining.slice(0, minIdx));
      }

      if (minIdx === kwStart) {
        const end = remaining.indexOf("%%/KW%%", kwStart);
        const content = remaining.slice(kwStart + 6, end);
        parts.push(
          <span key={`${lineIdx}-${key++}`} style={{ color: "#c084fc" }}>
            {content}
          </span>
        );
        remaining = remaining.slice(end + 7);
      } else if (minIdx === strStart) {
        const end = remaining.indexOf("%%/STR%%", strStart);
        const content = remaining.slice(strStart + 7, end);
        parts.push(
          <span key={`${lineIdx}-${key++}`} style={{ color: "#34d399" }}>
            {content}
          </span>
        );
        remaining = remaining.slice(end + 8);
      } else if (minIdx === decStart) {
        const end = remaining.indexOf("%%/DEC%%", decStart);
        const content = remaining.slice(decStart + 7, end);
        parts.push(
          <span key={`${lineIdx}-${key++}`} style={{ color: "#fbbf24" }}>
            {content}
          </span>
        );
        remaining = remaining.slice(end + 8);
      } else {
        parts.push(remaining);
        break;
      }
    }

    return (
      <div key={lineIdx}>
        {parts}
      </div>
    );
  });
}
