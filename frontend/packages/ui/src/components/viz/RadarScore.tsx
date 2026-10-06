import * as React from 'react';
import { useReducedMotion } from '../motion/useReducedMotion';
import { cn } from '../../lib/cn';

export interface RadarScoreProps {
  /** 维度名 → 0~100 分值 */
  data: Record<string, number>;
  size?: number;
  className?: string;
  /** 对比序列（上一次评分），用于展示涨幅 */
  compare?: Record<string, number>;
}

/** 雷达图：个人中心能力画像 / Session 雷达（技术方案 8.4）。纯 SVG，无额外依赖。 */
export function RadarScore({ data, size = 260, className, compare }: RadarScoreProps) {
  const reduced = useReducedMotion();
  const softId = `xian-radar-soft-${React.useId().replace(/:/g, '')}`;
  const [progress, setProgress] = React.useState(reduced ? 1 : 0);
  const entries = React.useMemo(() => Object.entries(data), [data]);
  const compareEntries = React.useMemo(() => (compare ? Object.entries(compare) : []), [compare]);

  React.useEffect(() => {
    if (reduced) {
      setProgress(1);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const dur = 900;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / dur);
      setProgress(1 - Math.pow(1 - p, 3));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reduced]);

  if (entries.length < 3) {
    return <div className={cn('text-xs text-content-faint', className)}>维度不足（至少 3 项）</div>;
  }

  const radius = size / 2 - 34;
  const center = size / 2;
  const angleStep = (Math.PI * 2) / entries.length;
  const pointAt = (index: number, ratio: number) => {
    const angle = angleStep * index - Math.PI / 2;
    return [center + Math.cos(angle) * radius * ratio, center + Math.sin(angle) * radius * ratio] as const;
  };

  // 全部维度为 0：多边形会塌缩成一个点，肉眼看不见，直接给空态而不是画个看不见的图
  const hasData = entries.some(([, v]) => Number(v) > 0);
  if (!hasData) {
    return (
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className={className}
        role="img"
        aria-label="能力雷达图（暂无数据）"
      >
        {/* 轻微高斯柔边：统一磨砂质感，消除锐利硬轮廓 */}
        <defs>
          <filter id={softId} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="0.7" />
          </filter>
        </defs>
        <g filter={`url(#${softId})`}>
          {[0.25, 0.5, 0.75, 1].map((r) => (
            <polygon
              key={r}
              points={entries.map((_, i) => pointAt(i, r).join(',')).join(' ')}
              fill="none"
              stroke="var(--border)"
              strokeWidth="0.75"
              strokeOpacity="0.4"
            />
          ))}
          {entries.map((_, i) => {
            const [x, y] = pointAt(i, 1);
            return (
              <line
                key={`axis-${i}`}
                x1={center}
                y1={center}
                x2={x}
                y2={y}
                stroke="var(--border)"
                strokeWidth="0.75"
                strokeOpacity="0.4"
              />
            );
          })}
        </g>
        {entries.map(([label], i) => {
          const [x, y] = pointAt(i, 1.12);
          return (
            <text
              key={label}
              x={x}
              y={y}
              fill="var(--text-tertiary)"
              fillOpacity="0.75"
              fontSize="10"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {label}
            </text>
          );
        })}
        <text
          x={center}
          y={center}
          fill="var(--text-tertiary)"
          fillOpacity="0.6"
          fontSize="11"
          textAnchor="middle"
          dominantBaseline="middle"
        >
          暂无数据
        </text>
      </svg>
    );
  }

  const polygon = (values: number[]) =>
    values.map((v, i) => pointAt(i, Math.min(1, Math.max(0, v / 100)) * progress).join(',')).join(' ');

  const comparePoly = compareEntries.length === entries.length ? polygon(compareEntries.map(([, v]) => v)) : null;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      role="img"
      aria-label="能力雷达图"
    >
      {/* 轻微高斯柔边：统一磨砂质感，消除锐利硬轮廓 */}
      <defs>
        <filter id={softId} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.7" />
        </filter>
      </defs>
      {/* 网格：细线 + 浅灰半透明 */}
      <g filter={`url(#${softId})`}>
        {[0.25, 0.5, 0.75, 1].map((r) => (
          <polygon
            key={r}
            points={entries.map((_, i) => pointAt(i, r).join(',')).join(' ')}
            fill="none"
            stroke="var(--border)"
            strokeWidth="0.75"
            strokeOpacity="0.4"
          />
        ))}
        {entries.map((_, i) => {
          const [x, y] = pointAt(i, 1);
          return (
            <line
              key={`axis-${i}`}
              x1={center}
              y1={center}
              x2={x}
              y2={y}
              stroke="var(--border)"
              strokeWidth="0.75"
              strokeOpacity="0.4"
            />
          );
        })}
      </g>
      {entries.map(([label], i) => {
        const [x, y] = pointAt(i, 1.12);
        return (
          <text
            key={label}
            x={x}
            y={y}
            fill="var(--text-tertiary)"
            fillOpacity="0.75"
            fontSize="10"
            textAnchor="middle"
            dominantBaseline="middle"
          >
            {label}
          </text>
        );
      })}
      {comparePoly ? (
        <polygon
          points={comparePoly}
          fill="none"
          stroke="var(--color-coach)"
          strokeWidth="1"
          strokeOpacity="0.5"
          strokeDasharray="3 4"
          strokeLinejoin="round"
        />
      ) : null}
      {/* 数据面：低透明度淡填充 + 纤细柔边描边 */}
      <polygon
        points={polygon(entries.map(([, v]) => v))}
        fill="var(--color-blue-team)"
        fillOpacity="0.1"
        stroke="var(--color-blue-team)"
        strokeWidth="1.25"
        strokeOpacity="0.7"
        strokeLinejoin="round"
        strokeLinecap="round"
        filter={`url(#${softId})`}
      />
    </svg>
  );
}