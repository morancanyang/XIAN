import { Orb } from '@xian/ui';

  /** SecScore 评分卡 / 关卡通关结算卡底层（技术方案 8.7.1）。 */
export function OrbBackdrop({
  secScore,
  grade,
  className,
  opacity,
  timeScale,
  hoverIntensity,
  rotateOnHover,
  inline
}: {
  secScore: number;
  grade: string;
  className?: string;
  /** 整体不透明度；整页氛围取 0.65~0.75，卡片内嵌装饰要压低到 0.2 左右 */
  opacity?: number;
  /** 噪声演化速率倍率，1 为上游默认；<1 放缓流动 */
  timeScale?: number;
  /** 鼠标靠近时的增亮幅度，默认随 secScore 涨到 0.6，氛围装饰应显式压到 0.05 以下 */
  hoverIntensity?: number;
  /** 鼠标靠近时是否旋转，氛围装饰一律关掉，避免用户一晃鼠标整个光环跟着转 */
  rotateOnHover?: boolean;
  /** 内联到定位祖先内（卡片内嵌装饰用），详见 BackgroundLayerProps.inline */
  inline?: boolean;
}) {
  return (
    <Orb
      secScore={secScore}
      grade={grade}
      className={className}
      opacity={opacity}
      timeScale={timeScale}
      hoverIntensity={hoverIntensity}
      rotateOnHover={rotateOnHover}
      inline={inline}
    />
  );
}
