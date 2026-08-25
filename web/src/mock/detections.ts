import dayjs from 'dayjs';
import type { DetectionBox, DetectionRecord, PestKey, Severity } from '@/types/domain';
import { makeRng } from '@/mock/random';
import { plots } from '@/mock/farm';
import { computeVisualRisk } from '@/utils/risk';

/**
 * 检测记录 Mock：过去 7 天，每个摄像头每天若干条自动巡检记录。
 * P01（稻瘟高发）、P03（纹枯+飞虱）、P07（卷叶螟+二化螟）为演示重点地块。
 */

const PLOT_PESTS: Record<string, PestKey[]> = {
  P01: ['rice_blast', 'brown_spot'],
  P02: ['rice_blast'],
  P03: ['sheath_blight', 'rice_planthopper'],
  P04: ['brown_spot'],
  P05: ['bacterial_streak'],
  P06: ['rice_planthopper'],
  P07: ['rice_leaf_roller', 'striped_stem_borer'],
  P08: ['brown_spot'],
};

/** 各病虫害 bbox 典型宽高（比例），病害类偏方形斑块，虫害类偏细长 */
function bboxShapeOf(pest: PestKey): { w: number; h: number } {
  switch (pest) {
    case 'rice_blast':
      return { w: 0.16, h: 0.22 };
    case 'sheath_blight':
      return { w: 0.34, h: 0.14 };
    case 'bacterial_blight':
      return { w: 0.3, h: 0.1 };
    case 'brown_spot':
      return { w: 0.09, h: 0.11 };
    case 'bacterial_streak':
      return { w: 0.08, h: 0.26 };
    case 'rice_planthopper':
      return { w: 0.05, h: 0.05 };
    case 'rice_leaf_roller':
      return { w: 0.18, h: 0.06 };
    case 'striped_stem_borer':
      return { w: 0.06, h: 0.2 };
  }
}

function severityOf(r: ReturnType<typeof makeRng>, risk: number): Severity {
  const roll = r.next() * 100;
  if (risk >= 75) return roll < 45 ? '严重' : '偏重';
  if (risk >= 55) return roll < 30 ? '严重' : roll < 70 ? '偏重' : '中等';
  if (risk >= 35) return roll < 25 ? '偏重' : roll < 75 ? '中等' : '轻微';
  return roll < 70 ? '轻微' : '中等';
}

function makeBoxes(seed: number, pestPool: PestKey[], intensity: number): DetectionBox[] {
  const r = makeRng(seed);
  const n = Math.max(0, Math.round(r.float(0.5, 1.4) * intensity));
  const boxes: DetectionBox[] = [];
  for (let i = 0; i < n; i++) {
    const pest = r.pick(pestPool);
    const shape = bboxShapeOf(pest);
    const w = shape.w * r.float(0.7, 1.35);
    const h = shape.h * r.float(0.7, 1.35);
    const x = r.float(0.04, Math.max(0.05, 0.96 - w));
    const y = r.float(0.08, Math.max(0.09, 0.92 - h));
    const sev = severityOf(r, intensity * 55);
    boxes.push({
      id: `B${seed}${i}`,
      pest,
      confidence: r.float(0.62, 0.97, 3),
      lesionAreaPct: Math.min(
        38,
        (sev === '严重' ? 9 : sev === '偏重' ? 5.5 : sev === '中等' ? 3 : 1.2) *
          r.float(0.6, 1.5, 2) *
          (w * h * 60),
      ),
      severity: sev,
      bbox: [
        Math.round(x * 1000) / 1000,
        Math.round(y * 1000) / 1000,
        Math.round(w * 1000) / 1000,
        Math.round(h * 1000) / 1000,
      ],
    });
  }
  return boxes;
}

/** 以当前时间为基准，保证检测记录始终包含"最新"数据 */
const NOW = dayjs();
let seq = 0;

export const detectionRecords: DetectionRecord[] = (() => {
  const out: DetectionRecord[] = [];
  for (const p of plots) {
    const pool = PLOT_PESTS[p.id] ?? ['brown_spot'];
    const intensity = Math.max(0.4, p.visualRisk / 55);
    for (let d = 7; d >= 0; d--) {
      // 白天每 2 小时一次巡检（07/09/11/13/15/17 时）
      const perDay = 6;
      for (let k = 0; k < perDay; k++) {
        const hour = [7, 9, 11, 13, 15, 17][k] ?? 9;
        const ts = NOW.subtract(d, 'day').hour(hour).minute(makeRng(seq * 7 + k).int(0, 45));
        if (ts.isAfter(NOW)) continue;
        seq += 1;
        const seed = 50000 + seq * 13;
        const boxes = makeBoxes(seed, pool, intensity);
        out.push({
          id: `D${String(seq).padStart(4, '0')}`,
          time: ts.toISOString(),
          plotId: p.id,
          cameraId: `CAM-${p.id}`,
          source: k === perDay - 1 && d % 3 === 0 ? 'scheduled_capture' : 'auto_patrol',
          boxes,
          visualRisk: computeVisualRisk(boxes),
          inferenceMs: makeRng(seed + 3).int(31, 46),
          imageSeed: seed,
          handled: d >= 2 ? true : p.compositeRisk < 55,
        });
      }
    }
  }
  return out.sort((a, b) => (a.time < b.time ? 1 : -1));
})();

export const detectionById = (id: string): DetectionRecord | undefined =>
  detectionRecords.find((d) => d.id === id);

/** 今日最新一条各摄像头记录（实时监测页用） */
export const latestDetections: DetectionRecord[] = plots
  .map((p) => detectionRecords.find((d) => d.plotId === p.id)!)
  .filter(Boolean);
