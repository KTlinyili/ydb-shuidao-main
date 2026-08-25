import type {
  AgentKey,
  AgentTurn,
  ConsultSession,
  DetectionRecord,
  Plot,
} from '@/types/domain';
import { PEST_META } from '@/utils/constants';
import { computeEnvRisk, computeTrendRisk, riskLevelOf } from '@/utils/risk';
import { genEnvSeries, genRiskSeries } from '@/mock/env';
import { caseRecords } from '@/mock/knowledge';

/**
 * 多 Agent 会诊 Mock：本地模拟后端 orchestrator 的四专家多轮流程。
 * 接入后端后由 POST /api/v1/diagnosis/run 替代，字段与 protocol_schema 对齐。
 */

const AGENT_NAMES: Record<AgentKey, string> = {
  pest_evidence_officer: '病虫害证据官',
  differential_officer: '鉴别诊断官',
  plant_protection_expert: '植保专家',
  field_management_officer: '田间管理官',
};

const AGENT_ROLES: Record<AgentKey, string> = {
  pest_evidence_officer: '将视觉检测与环境征象翻译为病理语言，构建候选假设',
  differential_officer: '质疑与证伪假设，校验必要条件，挖掘矛盾点',
  plant_protection_expert: '给出具体可操作的防治方案与用药时机',
  field_management_officer: '提供水肥、晒田、清园等环境调控与复查安排',
};

export { AGENT_NAMES, AGENT_ROLES };

const LAYER1: AgentKey[] = ['pest_evidence_officer', 'differential_officer'];
const LAYER2: AgentKey[] = ['plant_protection_expert', 'field_management_officer'];

/** 由检测记录生成第一轮证据官发言 */
function evidenceTurn(det: DetectionRecord, plot: Plot, round: number): AgentTurn {
  const pests = Array.from(new Set(det.boxes.map((b) => b.pest)));
  const primary = pests[0];
  const meta = PEST_META[primary];
  const worst = det.boxes.reduce((a, b) => (b.severity > a.severity ? b : a), det.boxes[0]);
  const fields = [
    {
      label: '可见征象',
      items: det.boxes.slice(0, 4).map(
        (b) =>
          `${PEST_META[b.pest].name}病斑/虫体 ${Math.round(b.confidence * 100)}% 置信，${b.severity}，病斑面积约 ${b.lesionAreaPct.toFixed(1)}%`,
      ),
    },
    {
      label: '候选假设',
      items: pests.slice(0, 3).map(
        (p, i) =>
          `${i === 0 ? '首要' : '次要'}假设：${PEST_META[p].name}（${PEST_META[p].latin}），为害部位 ${PEST_META[p].site}`,
      ),
    },
    {
      label: '证据强度',
      items: [
        `视觉模型单帧检出 ${det.boxes.length} 处目标，最高置信 ${Math.round(worst.confidence * 100)}%，推理耗时 ${det.inferenceMs} ms`,
        `地块处于${plot.stage}，品种 ${plot.variety}，当前视觉风险分 ${det.visualRisk}`,
      ],
    },
  ];
  if (round === 2) {
    fields.push({
      label: '补充证据',
      items: [
        `结合历史：${plot.name} 近 7 日视觉风险由 ${Math.max(8, det.visualRisk - 18)} 升至 ${det.visualRisk}，呈上行趋势`,
        `环境侧：当前环境风险分 ${computeEnvRisk(genEnvSeries('24h', plot.id).at(-1)!, pests)}，适发条件参考「${meta.favorable}」`,
      ],
    });
  }
  return {
    agent: 'pest_evidence_officer',
    round,
    fields,
    citations: [`视觉检测记录 ${det.id}`, `地块档案 ${plot.id}`],
    latencyMs: 420 + round * 90,
  };
}

/** 鉴别诊断官 */
function differentialTurn(det: DetectionRecord, plot: Plot, round: number): AgentTurn {
  const pests = Array.from(new Set(det.boxes.map((b) => b.pest)));
  const primary = pests[0];
  const competitor = pests[1] ?? (primary === 'rice_blast' ? 'brown_spot' : 'rice_blast');
  const fields = [
    {
      label: '必要条件校验',
      items: [
        `${PEST_META[primary].name}：${PEST_META[primary].site}受害特征齐全，环境条件匹配（${PEST_META[primary].favorable.split('、').slice(0, 2).join('、')}）`,
        `${PEST_META[competitor].name}：${competitor === primary ? '（缺同科对照）' : `部分症状重叠，但 ${PEST_META[competitor].site} 未见对应典型特征`}`,
      ],
    },
    {
      label: '矛盾点',
      items: [
        `检出框中有 ${det.boxes.filter((b) => b.confidence < 0.75).length} 处置信度低于 75%，建议人工复核`,
        det.boxes.some((b) => b.lesionAreaPct < 1.5)
          ? '部分病斑面积过小，处于侵染早期，症状不典型'
          : '病斑面积分布集中，支持中期判断',
      ],
    },
    {
      label: `排序结论`,
      items: [
        `维持 ${PEST_META[primary].name} 为第一诊断，置信下调至 ${Math.round((pests.length > 1 ? 0.82 : 0.9) * 100)}%`,
        round === 2
          ? '两轮一致，无新增矛盾证据，可进入决策层'
          : '建议第二轮补充近景抓拍，重点复核低置信目标',
      ],
    },
  ];
  return {
    agent: 'differential_officer',
    round,
    fields,
    citations: [`知识库 ${PEST_META[primary].name}诊断条目`],
    latencyMs: 380 + round * 70,
  };
}

/** 植保专家 */
function plantProtectionTurn(det: DetectionRecord, plot: Plot, round: number): AgentTurn {
  const pests = Array.from(new Set(det.boxes.map((b) => b.pest)));
  const primary = pests[0];
  const protocol: Record<string, string[]> = {
    rice_blast: [
      '75% 三环唑 WP 25 g/亩 对水 30 kg 全田均匀喷雾',
      '发病中心及周边 5 m 加量补喷，标记观察',
      '若近破口期，破口前 3~5 天与齐穗期各防一次穗颈瘟',
    ],
    sheath_blight: [
      '24% 噻呋酰胺 SC 20 mL/亩，喷头对准稻株中下部',
      '施药时保持 3~5 cm 薄水层提高药液展着',
      '10 天后复查防效，必要时补施井冈霉素',
    ],
    bacterial_blight: [
      '20% 噻唑锌 SC 100 mL/亩 喷雾，间隔 7 天连防 2 次',
      '避免露水未干时施药与农事操作',
      '暴雨后 24 小时内补查一次，防伤口传染扩散',
    ],
    brown_spot: [
      '叶面喷施磷酸二氢钾 100 g/亩 + 30% 苯甲·丙环唑 15 mL',
      '测土补施钾肥 5 kg/亩，酸性土撒施石灰 40 kg/亩',
      '两周后复查叶色与新病斑数',
    ],
    bacterial_streak: [
      '20% 噻菌铜 SC 120 mL/亩 喷雾，7~10 天后复施',
      '发病田块独立排灌，严禁串灌',
      '农事作业安排在露水干后进行',
    ],
    rice_planthopper: [
      '50% 吡蚜酮 WDG 15 g/亩 粗喷雾至稻丛基部',
      '田间保水 4 cm，药后 3 天内不排水',
      '8 天后盘拍复查，虫口降幅 <80% 轮换呋虫胺补防',
    ],
    rice_leaf_roller: [
      '20% 氯虫苯甲酰胺 SC 10 mL/亩，傍晚幼虫取食高峰施药',
      '重点喷上部三张功能叶，水量充足',
      '5 天后调查虫苞新增数评估防效',
    ],
    striped_stem_borer: [
      '10% 阿维·氟酰胺 SC 30 mL/亩，卵盛孵期施药',
      '枯心苗人工拔除带出田外',
      '性诱捕器加密至每 2 亩 1 个监测成虫',
    ],
  };
  const items = protocol[primary] ?? [];
  const fields = [
    { label: '今日可执行动作', items: items.slice(0, round === 1 ? 2 : 3) },
    {
      label: '药剂与时机',
      items: [
        `防治对象：${pests.map((p) => PEST_META[p].name).join('、')}`,
        `施药窗口：${plot.stage === '孕穗期' ? '破口前完成首次用药' : '未来 48 小时内，避开中午高温'}`,
      ],
    },
    {
      label: round === 1 ? '初步建议' : '最终方案',
      items: round === 1 ? items.slice(0, 2) : [...items.slice(0, 3), `防治后 ${plot.stage === '灌浆期' ? 5 : 8} 天组织效果复查`],
    },
  ];
  return {
    agent: 'plant_protection_expert',
    round,
    fields,
    citations: [`${PEST_META[primary].name}防治技术规程`, '绿色防控技术集成方案'],
    latencyMs: 450 + round * 60,
  };
}

/** 田间管理官 */
function fieldManagementTurn(plot: Plot, round: number): AgentTurn {
  const fields = [
    {
      label: '水肥管理',
      items: [
        '立即排水晒田 3~5 天，降低田间小气候湿度',
        '暂停施氮，叶色卡读数 ≥4 的田块增施钾肥 5 kg/亩',
      ],
    },
    {
      label: '农事安排',
      items: [
        `施药与复查作业安排在 09:00 前或 16:00 后，避开蜜蜂活动与高温药害时段`,
        `${plot.name}（管理员：${plot.manager}）单独排灌，工具专用防止带菌传病`,
      ],
    },
    {
      label: '复查节点',
      items: [
        '防治后第 3 天：巡查新发病斑/虫苞数量',
        '防治后第 8 天：复拍同机位对比，评估防治效果',
        round === 2 ? '下次巡检加密至每日 2 次，持续 1 周' : '巡检频次暂维持每日 1 次',
      ],
    },
  ];
  return {
    agent: 'field_management_officer',
    round,
    fields,
    citations: ['稻田水肥管理与病虫害关系'],
    latencyMs: 350 + round * 50,
  };
}

export function buildConsultSession(
  plot: Plot,
  det: DetectionRecord,
  complaint: string,
  useKb: boolean,
  useCase: boolean,
  sessionId: string,
): ConsultSession {
  const env = genEnvSeries('24h', plot.id).at(-1)!;
  const pests = Array.from(new Set(det.boxes.map((b) => b.pest)));
  const envRisk = computeEnvRisk(env, pests);
  const trendRisk = computeTrendRisk(genRiskSeries('7d', plot.id).map((x) => x.composite));
  const composite = Math.round(det.visualRisk * 0.45 + envRisk * 0.35 + trendRisk * 0.2);
  const primary = pests[0];

  const turns: AgentTurn[] = [
    evidenceTurn(det, plot, 1),
    differentialTurn(det, plot, 1),
    plantProtectionTurn(det, plot, 1),
    fieldManagementTurn(plot, 1),
    evidenceTurn(det, plot, 2),
    differentialTurn(det, plot, 2),
    plantProtectionTurn(det, plot, 2),
    fieldManagementTurn(plot, 2),
  ];

  const similarCases = caseRecords
    .filter((c) => c.diagnosis === primary)
    .slice(0, 2)
    .map((c) => ({ caseId: c.id, similarity: c.confidence - 0.02 }));

  const kbHits = useKb
    ? [
        { docId: 'KB001', title: '稻瘟病识别与防治技术规程', snippet: '慢性型病斑呈梭形，两端有沿叶脉延伸的褐色坏死线……', score: 0.92 },
        { docId: 'KB007', title: '水稻主要病虫害绿色防控技术集成', snippet: '以生态调控为基础、理化诱控为重点、科学用药为底线……', score: 0.74 },
      ].filter((h) => h.docId === 'KB001' || primary !== 'rice_blast')
    : [];

  return {
    id: sessionId,
    createdAt: new Date().toISOString(),
    plotId: plot.id,
    detectionId: det.id,
    complaint,
    useKnowledgeBase: useKb,
    useCaseLibrary: useCase,
    turns,
    conclusion: {
      diagnosis: pests.length > 1 ? 'multi' : primary,
      confidence: pests.length > 1 ? 0.84 : 0.9,
      riskLevel: riskLevelOf(composite),
      judgment:
        pests.length > 1
          ? `综合判断为 ${pests.map((p) => PEST_META[p].name).join(' 并发 ')}，病变处于扩展期，建议 48 小时内完成首次防治`
          : `综合判断为${PEST_META[primary].name}（${PEST_META[primary].latin}），置信度 ${Math.round(0.9 * 100)}%，${plot.stage}发生，处于可防可控窗口`,
      evidence: [
        `视觉证据：单帧检出 ${det.boxes.length} 处目标，病斑总面积占比约 ${det.boxes.reduce((a, b) => a + b.lesionAreaPct, 0).toFixed(1)}%`,
        `环境证据：当前气温 ${env.temperature}℃ / 湿度 ${env.humidity}% / 土壤含水率 ${env.soilMoisture}%，环境风险分 ${envRisk}${
          envRisk >= 55 ? '，已进入适发区间' : '，环境压力中等，以视觉与趋势证据为主'
        }（适发条件：${PEST_META[primary].favorable}）`,
        `趋势证据：近 7 日视觉风险持续上行，趋势风险分 ${trendRisk}`,
        similarCases.length
          ? `病例佐证：${similarCases.map((c) => c.caseId).join('、')} 号历史病例症状高度相似`
          : '暂无高度相似历史病例，以知识库条目为主要依据',
      ],
      measures: plantProtectionTurn(det, plot, 2).fields[2].items,
      fieldAdvice: [
        '排水晒田 3~5 天，控制群体湿度',
        '暂停氮肥、增施钾肥，提高植株抗性',
        `防治后第 3、8 天由 ${plot.manager} 组织两次定点复查`,
      ],
      observations: [
        `明日同机位（${det.cameraId}）定时抓拍对比病斑扩展`,
        `关注 48 小时内降雨预报，施药需保证药后 4 小时无雨`,
        '若出现急性型病斑或虫口突增，立即升级处置并复核防治方案',
      ],
    },
    report: [
      {
        heading: '病例摘要',
        body: `${plot.name}（${plot.id}，${plot.variety}，${plot.stage}）${new Date().toLocaleDateString('zh-CN')} 自动巡检触发会诊。视觉模型检出 ${det.boxes.length} 处病虫害目标，以${PEST_META[primary].name}为主，环境条件处于适发区间。`,
      },
      {
        heading: '诊断判断与置信说明',
        body: `四专家两轮会诊一致判定为${PEST_META[primary].name}，综合置信度 ${pests.length > 1 ? 84 : 90}%。低置信目标已由鉴别诊断官标记人工复核。`,
      },
      {
        heading: '防治建议与实施路径',
        body: plantProtectionTurn(det, plot, 2).fields[2].items.map((s, i) => `${i + 1}. ${s}`).join('；') + '。',
      },
      {
        heading: '风险边界与复查安排',
        body: `当前综合风险 ${composite} 分（${riskLevelOf(composite) === 'critical' ? '严重' : riskLevelOf(composite) === 'high' ? '高' : riskLevelOf(composite) === 'medium' ? '中' : '低'}风险）。复查节点：防治后第 3 天与第 8 天；若风险上行越过 75 分阈值，系统将自动升级预警等级。`,
      },
    ],
    kbHits,
    similarCases,
  };
}
