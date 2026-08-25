import dayjs from 'dayjs';
import type { PestKey, WarningRecord } from '@/types/domain';
import { detectionRecords } from '@/mock/detections';
import { plots, plotById } from '@/mock/farm';
import { computeEnvRisk, computeTrendRisk, fuseComposite, riskLevelOf } from '@/utils/risk';
import { genEnvSeries, genRiskSeries } from '@/mock/env';
import { PEST_META } from '@/utils/constants';
import { makeRng } from '@/mock/random';

/**
 * 预警 Mock：从检测记录推导。中高风险以上生成预警，附处置建议。
 */

const ADVICE_BANK: Record<PestKey, string[]> = {
  rice_blast: [
    '破口前后各施药 1 次：75% 三环唑可湿性粉剂 20~30 g/亩，对水 30 kg 均匀喷雾',
    '控制氮肥用量，晒田控苗，降低田间郁闭度',
    '发病中心周边 5 m 范围补喷，重点喷施穗颈部',
    '若遇连阴雨天气，施药后 4 小时遇雨需补施',
  ],
  sheath_blight: [
    '选用 24% 噻呋酰胺悬浮剂 20 mL/亩 或 5% 井冈霉素水剂 150 mL/亩 喷雾，重点喷基部',
    '排水晒田 3~5 天，降低田间湿度',
    '及时清除田边杂草，减少菌源',
    '拔除重病株带出田外处理，控制蔓延',
  ],
  bacterial_blight: [
    '选用 20% 噻唑锌悬浮剂 100 mL/亩 或 3% 中生菌素喷雾防治',
    '避免大风天气施药与农事操作，减少伤口传染',
    '停用串灌漫灌，改为浅水勤灌',
    '台风暴雨过后 24 小时内全面补查一次',
  ],
  brown_spot: [
    '叶面喷施磷酸二氢钾 100 g/亩 + 30% 苯甲·丙环唑 15 mL，补充营养兼防病',
    '测土配方补施钾肥硅肥，增强抗性',
    '酸性土壤结合晒田撒施石灰 30~50 kg/亩',
  ],
  bacterial_streak: [
    '选用 20% 噻菌铜悬浮剂 120 mL/亩 喷雾，间隔 7 天再施 1 次',
    '发病田块单独排灌，防止田水串灌传病',
    '避免清晨露水未干时下田作业',
  ],
  rice_planthopper: [
    '百丛虫量达 500 头时用药：50% 吡蚜酮水分散粒剂 15 g/亩 或 25% 呋虫胺 20 mL/亩',
    '药液喷向稻丛基部，保持浅水层 3~5 cm 提高防效',
    '轮换用药延缓抗性，添加激渗助剂',
    '保护蜘蛛、黑肩绿盲蝽等天敌，田埂留草带',
  ],
  rice_leaf_roller: [
    '卵孵化高峰至 2 龄幼虫期用药：20% 氯虫苯甲酰胺悬浮剂 10 mL/亩',
    '束叶出现初期人工捏杀配合药剂挑治',
    '防治适期在傍晚，幼虫活动旺盛时施药',
  ],
  striped_stem_borer: [
    '卵盛孵期用药：10% 阿维·氟酰胺悬浮剂 30 mL/亩 或 200 g/L 氯虫苯甲酰胺 10 mL/亩',
    '田间出现枯心苗时及时拔除并带出田外',
    '冬季深翻灭茬，减少越冬虫源',
    '性诱捕器每 2 亩 1 个，监测成虫峰期',
  ],
};

function adviceFor(pests: PestKey[], plotName: string): string[] {
  const out: string[] = [];
  for (const p of pests.slice(0, 2)) {
    out.push(`${PEST_META[p].name}：${ADVICE_BANK[p][0]}`);
  }
  out.push(`安排 ${plotName} 田间管理员 24 小时内复核一次防治效果`);
  return out;
}

export const warningRecords: WarningRecord[] = (() => {
  const out: WarningRecord[] = [];
  const envByPlot: Record<string, number> = {};
  for (const p of plots) {
    const pests = Array.from(
      new Set(
        detectionRecords
          .filter((d) => d.plotId === p.id)
          .slice(0, 6)
          .flatMap((d) => d.boxes.map((b) => b.pest)),
      ),
    );
    // 每地块用各自的传感器快照，环境风险呈现地块差异
    const plotEnv = genEnvSeries('24h', p.id).at(-1)!;
    envByPlot[p.id] = computeEnvRisk(plotEnv, pests);
  }
  let seq = 0;
  for (const det of detectionRecords) {
    if (det.boxes.length === 0) continue;
    const p = plotById(det.plotId);
    if (det.visualRisk < 32) continue;
    const series = genRiskSeries('7d', p.id).map((x) => x.composite);
    const trend = computeTrendRisk(series);
    const env = envByPlot[p.id];
    const composite = fuseComposite(det.visualRisk, env, trend);
    const level = riskLevelOf(composite);
    if (level === 'low') continue;
    const pests = Array.from(new Set(det.boxes.map((b) => b.pest)));
    const r = makeRng(30000 + seq * 17);
    seq += 1;
    const triggerParts: string[] = [];
    if (det.visualRisk >= 55) triggerParts.push(`视觉风险 ${det.visualRisk}（${pests.map((x) => PEST_META[x].shortName).join('+')} 检出 ${det.boxes.length} 处）`);
    if (env >= 55) triggerParts.push(`环境风险 ${env}（温湿度进入适发区间）`);
    if (trend >= 55) triggerParts.push(`趋势风险 ${trend}（近 3 日风险上行）`);
    out.push({
      id: `W${String(seq).padStart(4, '0')}`,
      time: det.time,
      plotId: p.id,
      pest: pests.length > 1 ? 'multi' : pests[0],
      level,
      compositeRisk: composite,
      visualRisk: det.visualRisk,
      envRisk: env,
      trendRisk: trend,
      trigger: triggerParts.join('；') || '常规阈值触发',
      status:
        dayjs(det.time).isBefore(dayjs().subtract(3, 'day'))
          ? 'resolved'
          : det.visualRisk >= 70
            ? r.bool(0.7)
              ? 'processing'
              : 'pending'
            : r.bool(0.4)
              ? 'processing'
              : r.bool(0.5)
                ? 'pending'
                : 'resolved',
      detectionId: det.id,
      advice: adviceFor(pests, p.name),
      handler: undefined,
    });
  }
  // 补充处理人与解决时间
  for (const w of out) {
    if (w.status !== 'pending') {
      const r = makeRng(40000 + Number(w.id.slice(1)) * 3);
      w.handler = r.pick(['周建明', '吴春华', '陈国平', '刘春梅']);
      if (w.status === 'resolved') {
        w.resolvedAt = dayjs(w.time).add(r.int(2, 26), 'hour').toISOString();
      }
    }
  }
  return out.sort((a, b) => (a.time < b.time ? 1 : -1));
})();

export const warningById = (id: string): WarningRecord | undefined =>
  warningRecords.find((w) => w.id === id);
