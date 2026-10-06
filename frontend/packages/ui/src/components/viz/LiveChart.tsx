import * as React from 'react';
import { useReducedMotion } from '../motion/useReducedMotion';
import type { EChartsOption } from 'echarts';
import { useEcharts } from './useEcharts';
import { cn } from '../../lib/cn';

export interface LiveChartProps {
  /** x 轴类目 */
  labels: string[];
  /** 序列名 → 数值数组 */
  series: Record<string, number[]>;
  height?: number;
  className?: string;
  /** 追加模式：为 true 时不清空画布，实现流式推进 */
  stream?: boolean;
}

/** 实时折线：驾驶舱趋势 / ASR live（技术方案 8.4 LiveChart，基于 ECharts）。 */
export function LiveChart({ labels, series, height = 240, className, stream = true }: LiveChartProps) {
  const reduced = useReducedMotion();
  const option: EChartsOption = React.useMemo(
    () => ({
      animation: !reduced,
      animationDuration: 250,
      grid: { left: 36, right: 12, top: 24, bottom: 22 },
      tooltip: { trigger: 'axis' },
      legend: { textStyle: { color: 'var(--text-secondary)', fontSize: 11 }, top: 0 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: 'var(--border)' } },
        axisLabel: { color: 'var(--text-secondary)', fontSize: 10 }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: 'var(--border)' } },
        axisLabel: { color: 'var(--text-secondary)', fontSize: 10 }
      },
      series: Object.entries(series).map(([name, values], i) => ({
        name,
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: values,
        lineStyle: {
          width: 2,
          color: i === 0 ? 'var(--color-blue-team)' : i === 1 ? 'var(--color-red-team)' : 'var(--color-coach)'
        },
        itemStyle: { color: i === 0 ? 'var(--color-blue-team)' : 'var(--color-red-team)' },
        areaStyle: i === 0 ? { color: 'rgba(59,130,246,0.10)' } : undefined
      }))
    }),
    [labels, series, reduced]
  );

  const { containerRef } = useEcharts(option, { notMerge: !stream });

  return <div ref={containerRef} className={cn('w-full', className)} style={{ height }} />;
}