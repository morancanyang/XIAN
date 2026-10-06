import type { Meta, StoryObj } from '@storybook/react';
import { Threads } from './Threads';
import { Particles } from './Particles';
import { Radar } from './Radar';
import { GridScan } from './GridScan';
import { FaultyTerminal } from './FaultyTerminal';
import { LetterGlitch } from './LetterGlitch';
import { DarkVeil } from './DarkVeil';
import { Aurora } from './Aurora';
import { Orb } from './Orb';

const meta: Meta = {
  title: 'Backgrounds/ReactBits',
  parameters: { layout: 'fullscreen' }
};

export default meta;

/** 每个背景组件都必须能在 Storybook 独立预览（技术方案 8.5 组件流程）。 */
export const ThreadsStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <Threads />
    </div>
  )
};

export const ParticlesStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <Particles />
    </div>
  )
};

export const RadarStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <Radar />
    </div>
  )
};

export const GridScanStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <GridScan />
    </div>
  )
};

export const FaultyTerminalStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <FaultyTerminal />
    </div>
  )
};

export const LetterGlitchStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <LetterGlitch />
    </div>
  )
};

export const DarkVeilStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <DarkVeil />
    </div>
  )
};

export const AuroraStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <Aurora />
    </div>
  )
};

export const OrbStory: StoryObj = {
  render: () => (
    <div className="relative h-64 w-full">
      <Orb secScore={88} grade="A" />
    </div>
  )
};