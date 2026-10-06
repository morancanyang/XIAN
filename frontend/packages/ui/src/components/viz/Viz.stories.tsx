import type { Meta, StoryObj } from '@storybook/react';
import { RadarScore } from './RadarScore';
import { MetricRing } from './MetricRing';

const meta: Meta = {
  title: 'Viz/Charts',
  parameters: { layout: 'padded' }
};

export default meta;

export const Radar: StoryObj = {
  render: () => (
    <RadarScore
      data={{ 注入: 88, 越权: 72, 外带: 45, 社工: 63, 注入变种: 80, 资源滥用: 30 }}
      compare={{ 注入: 70, 越权: 65, 外带: 30, 社工: 40, 注入变种: 55, 资源滥用: 25 }}
    />
  )
};

export const Rings: StoryObj = {
  render: () => (
    <div className="flex gap-6">
      <MetricRing value={83} label="SecScore" tone="success" />
      <MetricRing value={62} label="预算" tone="coach" />
      <MetricRing value={31} label="ASR" tone="red" />
    </div>
  )
};