import { GridScan } from '@xian/ui';

  /** 攻击矩阵 Matrix / 武器库页背景（技术方案 8.7.1）。 */
export function GridScanBackdrop({ cell = 48, className }: { cell?: number; className?: string }) {
  return <GridScan cell={cell} className={className} />;
}
