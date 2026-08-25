import type { DetectionBox, EnvSnapshot, PestKey, RiskLevel, Severity } from '@/types/domain';
import { RISK_WEIGHTS } from '@/utils/constants';

/**
 * 风险融合模型（纯函数，接入后端后可由 /api/v1/risk/compute 替代）
 *
 * 综合风险 = 45% 视觉风险 + 35% 环境风险 + 20% 趋势风险
 * 分级：低 <35 ≤ 中 <55 ≤ 高 <75 ≤ 严重
 */

export function severityToScore(sev: Severity): number {
  switch (sev) {
    case '轻微':
      return 25;
    case '中等':
      return 50;
    case '偏重':
      return 75;
    case '严重':
      return 92;
  }
}

/** 视觉风险：由检测框的置信度、病斑面积与严重程度聚合 */
export function computeVisualRisk(boxes: DetectionBox[]): number {
  if (boxes.length === 0) return 6;
  let max = 0;
  let sum = 0;
  for (const b of boxes) {
    const s =
      severityToScore(b.severity) * 0.5 +
      Math.min(100, b.lesionAreaPct * 6) * 0.25 + // 病斑面积占比放大
      b.confidence * 100 * 0.25;
    max = Math.max(max, s);
    sum += s;
  }
  const avg = sum / boxes.length;
  return Math.round(Math.min(100, max * 0.7 + avg * 0.3 + Math.min(10, boxes.length)));
}

/** 各病虫害的适发环境因子（温度℃ / 湿度% / 土壤含水率%） */
interface EnvWindow {
  temp: [number, number];
  humidity: [number, number];
  soil: [number, number];
}

const ENV_WINDOWS: Record<PestKey, EnvWindow> = {
  rice_blast: { temp: [22, 29], humidity: [88, 100], soil: [32, 55] },
  sheath_blight: { temp: [26, 33], humidity: [90, 100], soil: [38, 60] },
  bacterial_blight: { temp: [23, 32], humidity: [80, 100], soil: [30, 60] },
  brown_spot: { temp: [20, 30], humidity: [82, 100], soil: [20, 38] },
  bacterial_streak: { temp: [24, 32], humidity: [85, 100], soil: [30, 60] },
  rice_planthopper: { temp: [22, 30], humidity: [70, 95], soil: [30, 55] },
  rice_leaf_roller: { temp: [20, 30], humidity: [75, 100], soil: [28, 55] },
  striped_stem_borer: { temp: [22, 32], humidity: [60, 90], soil: [28, 55] },
};

function inWindowScore(v: number, [lo, hi]: [number, number], tolerance: number): number {
  if (v >= lo && v <= hi) return 1;
  if (v < lo) return Math.max(0, 1 - (lo - v) / tolerance);
  return Math.max(0, 1 - (v - hi) / tolerance);
}

/** 环境风险：给定环境快照与当前发生的病虫害，评估环境适发程度 0-100 */
export function computeEnvRisk(env: EnvSnapshot, pests: PestKey[]): number {
  if (pests.length === 0) pests = ['sheath_blight'];
  let max = 0;
  for (const p of pests) {
    const w = ENV_WINDOWS[p];
    const s =
      inWindowScore(env.temperature, w.temp, 6) * 0.28 +
      inWindowScore(env.humidity, w.humidity, 14) * 0.47 +
      inWindowScore(env.soilMoisture, w.soil, 16) * 0.25;
    max = Math.max(max, s);
  }
  // 适发≠发病：适发度映射到 15~88 的风险带，留出地块间区分度
  return Math.round(Math.max(15, Math.min(88, max * 100 - 16)));
}

/** 趋势风险：由近期病害面积/风险序列的上升斜率评估 0-100 */
export function computeTrendRisk(series: number[]): number {
  if (series.length < 2) return 30;
  const n = series.length;
  const recent = series.slice(Math.max(0, n - 3));
  const before = series.slice(Math.max(0, n - 6), Math.max(0, n - 3));
  const ra = recent.reduce((a, b) => a + b, 0) / recent.length;
  const ba = before.length ? before.reduce((a, b) => a + b, 0) / before.length : ra;
  const slope = ra - ba; // 正为恶化
  const base = Math.min(100, (ra / 100) * 42 + 14);
  return Math.round(Math.max(6, Math.min(90, base + slope * 1.6)));
}

export function fuseComposite(visual: number, env: number, trend: number): number {
  const v = Math.round(
    visual * RISK_WEIGHTS.visual + env * RISK_WEIGHTS.env + trend * RISK_WEIGHTS.trend,
  );
  return Math.max(0, Math.min(100, v));
}

export function riskLevelOf(composite: number): RiskLevel {
  if (composite >= 75) return 'critical';
  if (composite >= 55) return 'high';
  if (composite >= 35) return 'medium';
  return 'low';
}
