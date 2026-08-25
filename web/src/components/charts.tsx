import ReactECharts from 'echarts-for-react';
import type { RiskPoint, TimeRange } from '@/types/domain';
import { RISK_LEVEL_META } from '@/utils/constants';
import { fmtTime } from '@/utils/format';

const AXIS = {
  axisLine: { lineStyle: { color: '#E4E9E6' } },
  axisTick: { show: false },
  axisLabel: { color: '#8B96A0', fontSize: 11 },
  splitLine: { lineStyle: { color: '#F0F2F1', type: 'dashed' as const } },
};

/** 风险趋势面积图：综合 + 三个分量 */
export function RiskTrendChart({
  data,
  range,
  height = 300,
  compact = false,
}: {
  data: RiskPoint[];
  range: TimeRange;
  height?: number;
  compact?: boolean;
}) {
  const markArea = [
    [
      { yAxis: 75, itemStyle: { color: 'rgba(185,58,58,0.045)' } },
      { yAxis: 100 },
    ],
    [
      { yAxis: 55, itemStyle: { color: 'rgba(192,86,33,0.045)' } },
      { yAxis: 75 },
    ],
  ];
  const option = {
    grid: { top: compact ? 28 : 34, left: 44, right: 16, bottom: compact ? 22 : 28 },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: number) => String(v),
    },
    legend: {
      show: !compact,
      top: 0,
      right: 0,
      itemWidth: 14,
      itemHeight: 8,
      icon: 'roundRect',
      textStyle: { color: '#64707C', fontSize: 11 },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map((d) => fmtTime(d.time, range === '24h' ? 'HH:mm' : 'MM-DD')),
      ...AXIS,
      splitLine: { show: false },
    },
    yAxis: { type: 'value', min: 0, max: 100, ...AXIS },
    series: [
      {
        name: '综合风险',
        type: 'line',
        data: data.map((d) => d.composite),
        smooth: 0.3,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        lineStyle: { width: 2.2, color: '#2E8B62' },
        itemStyle: { color: '#2E8B62' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(46,139,98,0.16)' },
              { offset: 1, color: 'rgba(46,139,98,0.01)' },
            ],
          },
        },
        markArea: compact ? undefined : { silent: true, data: markArea },
      },
      {
        name: '视觉风险',
        type: 'line',
        data: data.map((d) => d.visual),
        smooth: 0.3,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#B85C5C', type: 'solid' },
        itemStyle: { color: '#B85C5C' },
      },
      {
        name: '环境风险',
        type: 'line',
        data: data.map((d) => d.env),
        smooth: 0.3,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#C08A3E' },
        itemStyle: { color: '#C08A3E' },
      },
      {
        name: '趋势风险',
        type: 'line',
        data: data.map((d) => d.trend),
        smooth: 0.3,
        showSymbol: false,
        lineStyle: { width: 1.2, color: '#7C93AB' },
        itemStyle: { color: '#7C93AB' },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height }} notMerge />;
}

/** 环境多指标趋势（双 Y 轴：温湿度左、光照右） */
export function EnvTrendChart({
  data,
  range,
  height = 300,
  metrics,
}: {
  data: { time: string; temperature: number; humidity: number; light: number; soilMoisture: number }[];
  range: TimeRange;
  height?: number;
  metrics: { key: 'temperature' | 'humidity' | 'light' | 'soilMoisture'; name: string; unit: string; color: string }[];
}) {
  const hasRight = metrics.some((m) => m.key === 'light');
  const option = {
    grid: { top: 34, left: 44, right: hasRight ? 44 : 16, bottom: 28 },
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0, right: 0, itemWidth: 14, itemHeight: 8, icon: 'roundRect',
      textStyle: { color: '#64707C', fontSize: 11 },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map((d) => fmtTime(d.time, range === '24h' ? 'HH:mm' : 'MM-DD')),
      ...AXIS,
      splitLine: { show: false },
    },
    yAxis: [
      { type: 'value', ...AXIS },
      { type: 'value', ...AXIS, splitLine: { show: false } },
    ],
    series: metrics.map((m) => ({
      name: `${m.name}(${m.unit})`,
      type: 'line' as const,
      smooth: 0.35,
      showSymbol: false,
      yAxisIndex: m.key === 'light' ? 1 : 0,
      data: data.map((d) => d[m.key]),
      lineStyle: { width: 1.6, color: m.color },
      itemStyle: { color: m.color },
      areaStyle:
        metrics.length === 1
          ? {
              color: {
                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: `${m.color}22` },
                  { offset: 1, color: `${m.color}02` },
                ],
              },
            }
          : undefined,
    })),
  };
  return <ReactECharts option={option} style={{ height }} notMerge />;
}

/** 病虫害分布条形图（按检出次数） */
export function PestBarChart({
  data,
  height = 260,
}: {
  data: { name: string; value: number; color: string }[];
  height?: number;
}) {
  const option = {
    grid: { top: 8, left: 64, right: 30, bottom: 24 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', ...AXIS },
    yAxis: {
      type: 'category',
      data: data.map((d) => d.name),
      ...AXIS,
      splitLine: { show: false },
      axisLabel: { color: '#4A5560', fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        barWidth: 12,
        data: data.map((d) => ({ value: d.value, itemStyle: { color: d.color, borderRadius: [0, 3, 3, 0] } })),
        label: { show: true, position: 'right', color: '#64707C', fontSize: 11 },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height }} notMerge />;
}

/** 病害面积堆叠趋势 */
export function LesionAreaChart({
  data,
  range,
  height = 240,
}: {
  data: { time: string; areaMu: number }[];
  range: TimeRange;
  height?: number;
}) {
  const option = {
    grid: { top: 30, left: 44, right: 16, bottom: 28 },
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${v} 亩` },
    legend: { top: 0, right: 0, itemWidth: 14, itemHeight: 8, icon: 'roundRect', textStyle: { color: '#64707C', fontSize: 11 } },
    xAxis: {
      type: 'category',
      data: data.map((d) => fmtTime(d.time, range === '24h' ? 'DD日HH时' : 'MM-DD')),
      ...AXIS,
      splitLine: { show: false },
    },
    yAxis: { type: 'value', name: '亩', nameTextStyle: { color: '#8B96A0', fontSize: 11 }, ...AXIS },
    series: [
      {
        name: '病害面积',
        type: 'bar',
        barWidth: '52%',
        data: data.map((d) => d.areaMu),
        itemStyle: { color: '#7FA88F', borderRadius: [3, 3, 0, 0] },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height }} notMerge />;
}

/** 严重程度构成环图 */
export function SeverityPieChart({
  data,
  height = 220,
}: {
  data: { name: string; value: number; color: string }[];
  height?: number;
}) {
  const option = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 处 ({d}%)' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: '#64707C', fontSize: 11 } },
    series: [
      {
        type: 'pie',
        radius: ['52%', '74%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 3 },
        label: { show: false },
        data,
      },
    ],
  };
  return <ReactECharts option={option} style={{ height }} notMerge />;
}

export function riskLegendNote() {
  return (
    <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#8B96A0' }}>
      {(Object.keys(RISK_LEVEL_META) as (keyof typeof RISK_LEVEL_META)[]).map((k) => (
        <span key={k}>
          <span
            style={{
              display: 'inline-block',
              width: 8,
              height: 8,
              borderRadius: 2,
              background: RISK_LEVEL_META[k].color,
              marginRight: 4,
            }}
          />
          {RISK_LEVEL_META[k].label} {RISK_LEVEL_META[k].range}
        </span>
      ))}
    </div>
  );
}
