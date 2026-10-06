import { Radar } from '@xian/ui';

  /** 模式一 CampaignLive 顶部进度/预算区背后装饰层（技术方案 8.7.1）。 */
export function RadarBackdrop({ attacking = false }: { attacking?: boolean }) {
  return <Radar halfSpeed={!attacking} />;
}
