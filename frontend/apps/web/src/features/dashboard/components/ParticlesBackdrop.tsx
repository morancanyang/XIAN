import { Particles } from '@xian/ui';

  /** 驾驶舱 Home / Agent 资产页背景（技术方案 8.7.1）。 */
export function ParticlesBackdrop({ className }: { className?: string }) {
  return <Particles className={className} />;
}
