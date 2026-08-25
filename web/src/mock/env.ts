import dayjs from 'dayjs';
import type { EnvSnapshot, RiskPoint, TimeRange } from '@/types/domain';
import { makeRng } from '@/mock/random';
import { plots } from '@/mock/farm';

/**
 * 环境与风险时间序列 Mock 生成器。
 * 环境曲线带日变化节律：温度/光照白天高、夜间低；湿度反之。
 */

/** 以当前时间为基准，保证 Mock 数据始终是"最新"的 */
const NOW = dayjs();

function envAt(hourOfDay: number, seedOffset: number): Omit<EnvSnapshot, 'time'> {
  const rng = makeRng(7000 + Math.floor(hourOfDay * 97) + seedOffset);
  // 8 月中旬：低温 24℃，高温 33℃；光照峰值约 88 klx；湿度夜间 94%，午后 62%
  const t = Math.sin(((hourOfDay - 9) / 24) * 2 * Math.PI);
  const temperature = 28.5 + t * 4.5 + rng.float(-0.8, 0.8, 1);
  const light = Math.max(0, Math.sin(((hourOfDay - 6) / 13) * Math.PI) * 82 + rng.float(-4, 4, 1));
  const humidity = 78 - t * 14 + rng.float(-3, 3, 1);
  const soilMoisture = 42 + Math.sin((hourOfDay / 24) * Math.PI * 2 + 1.2) * 5 + rng.float(-1.5, 1.5, 1);
  return {
    temperature: Math.round(Math.max(23, Math.min(34, temperature)) * 10) / 10,
    humidity: Math.round(Math.max(55, Math.min(97, humidity)) * 10) / 10,
    light: Math.round(Math.max(0, Math.min(92, light)) * 10) / 10,
    soilMoisture: Math.round(Math.max(28, Math.min(58, soilMoisture)) * 10) / 10,
  };
}

/** 生成环境序列：24h 按小时、7d/30d 按日（取 14:00 代表值 + 日均） */
export function genEnvSeries(range: TimeRange, plotId?: string): EnvSnapshot[] {
  const seedOffset = plotId ? plots.findIndex((p) => p.id === plotId) * 31 : 0;
  const out: EnvSnapshot[] = [];
  if (range === '24h') {
    for (let i = 24; i >= 0; i--) {
      const ts = NOW.subtract(i, 'hour');
      out.push({ time: ts.toISOString(), ...envAt(ts.hour() + ts.minute() / 60, seedOffset) });
    }
  } else {
    const days = range === '7d' ? 7 : 30;
    for (let i = days; i >= 0; i--) {
      const ts = NOW.subtract(i, 'day').hour(14);
      const rng = makeRng(9000 + i * 53 + seedOffset);
      const e = envAt(14, seedOffset);
      out.push({
        time: ts.toISOString(),
        temperature: Math.round((e.temperature + rng.float(-1.6, 1.6, 1)) * 10) / 10,
        humidity: Math.round((e.humidity + rng.float(-6, 6, 1)) * 10) / 10,
        light: Math.round((e.light + rng.float(-8, 8, 1)) * 10) / 10,
        soilMoisture: Math.round((e.soilMoisture + rng.float(-4, 4, 1)) * 10) / 10,
      });
    }
  }
  return out;
}

/** 生成风险趋势序列（视觉/环境/趋势/综合），带缓慢上升或波动形态 */
export function genRiskSeries(range: TimeRange, plotId: string): RiskPoint[] {
  const base = plots.find((p) => p.id === plotId);
  const baseVisual = base?.visualRisk ?? 30;
  const baseEnv = base?.envRisk ?? 40;
  const steps = range === '24h' ? 24 : range === '7d' ? 7 : 30;
  const out: RiskPoint[] = [];
  const visualHistory: number[] = [];
  for (let i = steps; i >= 0; i--) {
    const ts =
      range === '24h' ? NOW.subtract(i, 'hour') : NOW.subtract(i, 'day').hour(14);
    const rng = makeRng(11000 + (steps - i) * 71 + plotId.charCodeAt(1) * 7);
    const progress = (steps - i) / steps; // 0→1 逐渐接近当前
    const visual = Math.round(
      baseVisual * (0.55 + 0.45 * progress) + rng.float(-6, 6, 1),
    );
    const env = Math.round(baseEnv * (0.7 + 0.3 * progress) + rng.float(-8, 8, 1));
    const trend = Math.round(20 + 35 * progress + rng.float(-5, 5, 1));
    const composite = Math.round(visual * 0.45 + env * 0.35 + trend * 0.2);
    visualHistory.push(visual);
    out.push({
      time: ts.toISOString(),
      visual: Math.max(4, Math.min(100, visual)),
      env: Math.max(5, Math.min(100, env)),
      trend: Math.max(4, Math.min(100, trend)),
      composite: Math.max(5, Math.min(100, composite)),
    });
  }
  return out;
}

/** 病害面积序列（亩，用于 24h/7d/30d 展示） */
export function genLesionAreaSeries(range: TimeRange, plotId: string): { time: string; areaMu: number }[] {
  const base = plots.find((p) => p.id === plotId);
  const scale = (base?.compositeRisk ?? 30) / 100;
  const steps = range === '24h' ? 12 : range === '7d' ? 7 : 30;
  const out: { time: string; areaMu: number }[] = [];
  for (let i = steps; i >= 0; i--) {
    const ts =
      range === '24h' ? NOW.subtract(i * 2, 'hour') : NOW.subtract(i, 'day').hour(14);
    const rng = makeRng(13000 + (steps - i) * 41 + plotId.charCodeAt(2) * 3);
    const progress = (steps - i) / steps;
    const area = (2.5 + 16 * scale * progress) * (base?.areaMu ?? 200) / 200 + rng.float(-0.3, 0.3, 2);
    out.push({ time: ts.toISOString(), areaMu: Math.max(0.2, Math.round(area * 100) / 100) });
  }
  return out;
}

export const MOCK_NOW = NOW;
