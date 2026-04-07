import { AbsoluteFill, Sequence } from "remotion";
import { TerminalScene } from "./scenes/TerminalScene";
import { LogoReveal } from "./scenes/LogoReveal";
import { CodeFlow } from "./scenes/CodeFlow";
import { GlitchTransition } from "./scenes/GlitchTransition";
import { ParticleGrid } from "./scenes/ParticleGrid";

export const BRoll: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {/* Scene 1: Particle Grid Intro (0-150) */}
      <Sequence from={0} durationInFrames={150}>
        <ParticleGrid />
      </Sequence>

      {/* Scene 2: Glitch Transition (140-200) */}
      <Sequence from={140} durationInFrames={60}>
        <GlitchTransition />
      </Sequence>

      {/* Scene 3: Terminal / CLI Animation (180-330) */}
      <Sequence from={180} durationInFrames={150}>
        <TerminalScene />
      </Sequence>

      {/* Scene 4: Glitch Transition (320-380) */}
      <Sequence from={320} durationInFrames={60}>
        <GlitchTransition />
      </Sequence>

      {/* Scene 5: Code Flow (360-510) */}
      <Sequence from={360} durationInFrames={150}>
        <CodeFlow />
      </Sequence>

      {/* Scene 6: Logo Reveal Outro (510-600) */}
      <Sequence from={510} durationInFrames={90}>
        <LogoReveal />
      </Sequence>
    </AbsoluteFill>
  );
};
