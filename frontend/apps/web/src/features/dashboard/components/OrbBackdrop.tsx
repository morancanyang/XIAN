import { Orb } from '@xian/ui';

  /** SecScore 评分卡 / 关卡通关结算卡底层（技术方案 8.7.1）。 */
export function OrbBackdrop({
  secScore,
  grade,
  className,
  opacity,
  timeScale
}: {
  secScore: number;
  grade: string;
  className?: string;
  /** 整体不透明度；静谧场景取 0.65~0.75 */
  opacity?: number;
  /** 噪声演化速率倍率，1 为上游默认；<1 放缓流动 */
  timeScale?: number;
}) {
  return <Orb secScore={secScore} grade={grade} className={className} opacity={opacity} timeScale={timeScale} />;
}
