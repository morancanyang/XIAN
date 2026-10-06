import * as React from 'react';
import * as echarts from 'echarts/core';
import { LineChart, BarChart, PieChart, RadarChart } from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DatasetComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { EChartsOption } from 'echarts';

echarts.use([
  LineChart,
  BarChart,
  PieChart,
  RadarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DatasetComponent,
  CanvasRenderer
]);

export interface UseEchartsOptions {
  notMerge?: boolean;
}

/** ECharts 实例托管：按容器尺寸自适应，卸载时 dispose，避免内存泄漏。 */
export function useEcharts(option: EChartsOption, options: UseEchartsOptions = {}) {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const chartRef = React.useRef<echarts.ECharts | null>(null);
  const optionRef = React.useRef(option);
  optionRef.current = option;

  React.useEffect(() => {
    if (!containerRef.current) return;
    chartRef.current = echarts.init(containerRef.current, undefined, { renderer: 'canvas' });
    chartRef.current.setOption(optionRef.current);

    const observer = new ResizeObserver(() => chartRef.current?.resize());
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  React.useEffect(() => {
    chartRef.current?.setOption(optionRef.current, { notMerge: options.notMerge ?? false });
  }, [option, options.notMerge]);

  return { containerRef, chartRef };
}