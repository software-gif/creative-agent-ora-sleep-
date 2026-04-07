import { Composition } from "remotion";
import { BRoll } from "./BRoll";
import { TerminalScene } from "./scenes/TerminalScene";
import { LogoReveal } from "./scenes/LogoReveal";
import { CodeFlow } from "./scenes/CodeFlow";
import { GlitchTransition } from "./scenes/GlitchTransition";
import { ParticleGrid } from "./scenes/ParticleGrid";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Full B-Roll Composition */}
      <Composition
        id="BRoll"
        component={BRoll}
        durationInFrames={600}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* Individual Scenes for Preview */}
      <Composition
        id="TerminalScene"
        component={TerminalScene}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="LogoReveal"
        component={LogoReveal}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="CodeFlow"
        component={CodeFlow}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="GlitchTransition"
        component={GlitchTransition}
        durationInFrames={60}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="ParticleGrid"
        component={ParticleGrid}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
