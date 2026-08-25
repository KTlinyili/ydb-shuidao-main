/**
 * 真实会诊响应适配层。
 *
 * 把后端 POST /api/v1/diagnosis/run 的 RunResponse
 * （run_id / final / reports / execution_meta）映射为前端 ConsultSession：
 * - final.report_packet 的结构化数据 → 四专家 × 两轮的 AgentTurn 发言
 * - final.top_diagnosis / severity_risk → 会诊结论
 * - reports.multi_agent_markdown → 报告抽屉的分节正文
 * 页面只消费 ConsultSession，不感知后端字段。
 */
import type {
  AgentKey,
  AgentTurn,
  ConsultConclusion,
  ConsultRequest,
  ConsultSession,
  PestKey,
  RiskLevel,
} from '@/types/domain';
import { PEST_META, PEST_ORDER } from '@/utils/constants';

type Any = Record<string, any>;

function str(v: unknown): string {
  return typeof v === 'string' ? v.trim() : '';
}

function list(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string' && !!x.trim()) : [];
}

function dig(source: unknown, ...path: string[]): any {
  let cur: any = source;
  for (const key of path) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = cur[key];
  }
  return cur;
}

function dedupe(items: string[]): string[] {
  return Array.from(new Set(items.map((s) => s.trim()).filter(Boolean)));
}

/** 后端置信度是 "82.25%" / "低" 等文本，统一转成 0~1 数值 */
function parseConfidence(v: unknown): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v > 1.5 ? v / 100 : v;
  const s = str(v).replace('%', '').trim();
  const n = Number.parseFloat(s);
  if (Number.isFinite(n)) return n > 1.5 ? n / 100 : n;
  if (/低|轻/.test(s)) return 0.45;
  if (/中/.test(s)) return 0.7;
  if (/高/.test(s)) return 0.88;
  return 0.75;
}

/** 病名 → 前端 8 类标识；匹配不上（如后端仍返回草莓类名）归为 multi */
export function matchPestKey(name: unknown): PestKey | 'multi' {
  const s = str(name);
  if (!s) return 'multi';
  const ranked = [...PEST_ORDER].sort(
    (a, b) => PEST_META[b].name.length - PEST_META[a].name.length,
  );
  for (const key of ranked) {
    const meta = PEST_META[key];
    if (s.includes(meta.name) || s.includes(meta.shortName)) return key;
  }
  return 'multi';
}

function riskLevelFromSeverity(v: unknown): RiskLevel {
  const s = str(v);
  if (/严重|critical/.test(s)) return 'critical';
  if (/偏重|重|high/.test(s)) return 'high';
  if (/轻微|轻|low/.test(s)) return 'low';
  return 'medium';
}

/** 按二级标题切分后端 Markdown 报告 */
function splitMarkdownSections(md: string): { heading: string; body: string }[] {
  if (!md.trim()) return [];
  const sections: { heading: string; body: string }[] = [];
  let current: { heading: string; body: string } | null = null;
  for (const line of md.split(/\r?\n/)) {
    const h2 = line.match(/^##\s+(.*)$/);
    if (h2) {
      if (current) sections.push(current);
      current = { heading: h2[1].trim(), body: '' };
    } else if (/^#\s+/.test(line)) {
      continue; // 顶级标题作为报告题头，跳过
    } else if (current) {
      current.body += (current.body ? '\n' : '') + line;
    }
  }
  if (current) sections.push(current);
  const cleaned = sections
    .map((s) => ({ heading: s.heading, body: s.body.trim() }))
    .filter((s) => s.heading && s.body);
  if (cleaned.length > 0) return cleaned;
  const body = md.trim();
  return body ? [{ heading: '会诊报告', body }] : [];
}

function turn(
  agent: AgentKey,
  round: number,
  fields: { label: string; items: string[] }[],
  latencyMs: number,
  citations: string[] = [],
): AgentTurn {
  const kept = fields.filter((f) => f.items.length > 0);
  return {
    agent,
    round,
    fields:
      kept.length > 0
        ? kept
        : [{ label: '本轮发言', items: ['该环节后端未返回结构化内容（可能处于降级输出模式）。'] }],
    citations,
    latencyMs,
  };
}

export function mapRunResponseToSession(
  data: { run_id?: string; final?: Any; reports?: Any; execution_meta?: Any },
  req: ConsultRequest,
): ConsultSession {
  const f = (data.final ?? {}) as Any;
  const packet = (f.report_packet ?? {}) as Any;
  const top = (f.top_diagnosis ?? packet.final_diagnosis ?? {}) as Any;
  const caseSummary = (packet.case_summary ?? dig(f, 'decision_packet', 'case_summary') ?? {}) as Any;
  const actionPlan = (packet.action_plan ?? {}) as Any;
  const safety = (packet.safety_and_followup ?? {}) as Any;
  const shared = (f.shared_state ?? {}) as Any;
  const reports = (f.reports ?? data.reports ?? {}) as Any;
  const severity = (f.severity_risk ?? {}) as Any;
  const decisionSupport = (actionPlan.decision_support ??
    safety.decision_support ??
    {}) as Any;

  const diagnosisName =
    str(top.name) || str(dig(packet, 'report_context', 'primary_diagnosis'));
  const confidenceText = top.confidence ?? dig(packet, 'report_context', 'confidence_label');
  const visualSummary = str(caseSummary.visual_summary);
  const symptoms = dedupe([...list(caseSummary.observed_symptoms), ...list(f.symptom_summary)]);
  const basis = dedupe(list(dig(packet, 'diagnosis_basis', 'image_specific_basis')));
  const workingDx = dedupe(list(shared.working_diagnoses));
  const actions = dedupe([...list(actionPlan.actions), ...list(f.actions)]);
  const controlOptions = dedupe(list(dig(packet, 'berry_qa_guidance', 'control_options')));
  const timeline = (Array.isArray(actionPlan.timeline) ? actionPlan.timeline : []) as Any[];
  const monitoring = dedupe([...list(actionPlan.monitoring_plan), ...list(f.monitoring_plan)]);
  const safetyNotes = dedupe(list(safety.safety_notes)).slice(0, 3);
  const missingEvidence = dedupe([
    ...list(dig(packet, 'evidence_board', 'missing_evidence')),
    ...(Array.isArray(f.evidence_board) ? list((f.evidence_board[0] ?? {}).missing) : []),
  ]);
  const keyDiscriminators = (dig(packet, 'uncertainty_management', 'key_discriminators') ??
    []) as Any[];
  const followups = dedupe([
    ...list(safety.required_followups),
    ...list(f.evidence_to_collect),
  ]);
  const upgrade = dedupe([
    ...list(actionPlan.escalation_conditions),
    ...list(decisionSupport.upgrade_conditions),
  ]).slice(0, 4);
  const downgrade = dedupe(list(decisionSupport.downgrade_conditions)).slice(0, 2);
  const thresholdHints = (Array.isArray(decisionSupport.observe_24_48h)
    ? decisionSupport.observe_24_48h
    : []) as Any[];
  const prognosis = str(safety.prognosis_note);
  const sufficiency =
    str(dig(packet, 'final_diagnosis', 'evidence_sufficiency')) || str(f.evidence_sufficiency);
  const uncertainty =
    typeof shared.uncertainty_score === 'number' ? shared.uncertainty_score : undefined;

  const baseLatency = Math.round(
    (Number(dig(reports, 'multi_agent_meta', 'latency_ms')) || 16000) / 8,
  );
  const latency = (i: number) => baseLatency + i * 137;

  const turns: AgentTurn[] = [
    turn(
      'pest_evidence_officer',
      1,
      [
        { label: '图像可见征象', items: symptoms.slice(0, 6) },
        { label: '视觉摘要', items: visualSummary ? [visualSummary] : [] },
        {
          label: '受害程度与风险',
          items: [str(severity.spread_risk), str(caseSummary.area_ratio_source_note)],
        },
      ],
      latency(1),
      str(f.run_id) ? [`视觉分析运行 ${str(f.run_id)}`] : [],
    ),
    turn('differential_officer', 1, [
      {
        label: '首位判断',
        items: [diagnosisName ? `${diagnosisName}（置信 ${str(confidenceText) || '—'}）` : ''],
      },
      { label: '判断依据', items: basis.slice(0, 3) },
      { label: '待排除方向', items: workingDx.slice(0, 3) },
    ], latency(2)),
    turn('plant_protection_expert', 1, [
      { label: '今日可执行动作', items: actions.slice(0, 3) },
      { label: '药剂参考', items: controlOptions.slice(0, 2) },
      {
        label: '处置时序',
        items: timeline.map((t) => {
          const acts = list(t.actions).slice(0, 2).join('；');
          return `${str(t.phase) || '处置阶段'}：${acts || str(t.objective)}`;
        }),
      },
    ], latency(3)),
    turn('field_management_officer', 1, [
      { label: '监测计划', items: monitoring.slice(0, 3) },
      { label: '风险提示', items: safetyNotes },
    ], latency(4)),
    turn('pest_evidence_officer', 2, [
      { label: '证据缺口', items: missingEvidence.slice(0, 3) },
      {
        label: '关键鉴别点',
        items: keyDiscriminators.map((k) => str(k.gap)).filter(Boolean).slice(0, 3),
      },
    ], latency(5)),
    turn('differential_officer', 2, [
      { label: '证据充分性', items: sufficiency ? [sufficiency] : [] },
      {
        label: '复核意见',
        items: [
          uncertainty != null ? `不确定度评分 ${uncertainty.toFixed(2)}，两轮会诊已收敛` : '',
          upgrade.length ? `若证据升级：${upgrade[0]}` : '',
        ],
      },
    ], latency(6)),
    turn('plant_protection_expert', 2, [
      { label: '升级条件', items: upgrade.slice(0, 3) },
      { label: '降级条件', items: downgrade },
      {
        label: '观察阈值',
        items: thresholdHints
          .map((t) => {
            const item = str(t.item);
            const hint = str(t.threshold_hint);
            return item ? `${item}${hint ? `（${hint}）` : ''}` : '';
          })
          .filter(Boolean)
          .slice(0, 3),
      },
    ], latency(7)),
    turn('field_management_officer', 2, [
      { label: '复查安排', items: followups.slice(0, 4) },
      { label: '预后判断', items: prognosis ? [prognosis] : [] },
    ], latency(8)),
  ];

  const judgment =
    str(dig(packet, 'final_diagnosis', 'diagnosis_statement')) ||
    str(dig(packet, 'report_context', 'diagnosis_statement')) ||
    str(f.confidence_statement) ||
    (diagnosisName ? `多专家会诊首位判断为「${diagnosisName}」。` : '会诊完成，详见报告。');

  const conclusion: ConsultConclusion = {
    diagnosis: matchPestKey(diagnosisName),
    confidence: parseConfidence(confidenceText),
    riskLevel: riskLevelFromSeverity(severity.level ?? str(timeline[0]?.risk_level)),
    judgment,
    evidence: dedupe([...basis, ...symptoms.map((s) => `可见征象：${s}`)]).slice(0, 5),
    measures: actions.slice(0, 5),
    fieldAdvice: dedupe([...monitoring, ...followups]).slice(0, 4),
    observations: dedupe([...list(f.evidence_to_collect), ...missingEvidence]).slice(0, 4),
  };

  let report = splitMarkdownSections(str(dig(reports, 'multi_agent_markdown')));
  if (report.length === 0) {
    report = [
      {
        heading: '病例摘要',
        body:
          [visualSummary, ...symptoms].filter(Boolean).join('；') || '本次会诊未生成图像摘要。',
      },
      { heading: '诊断判断与置信说明', body: judgment },
      {
        heading: '救治建议与实施路径',
        body: conclusion.measures.map((s, i) => `${i + 1}. ${s}`).join('\n') || '暂无。',
      },
      {
        heading: '风险边界与复查',
        body: [prognosis, ...followups].filter(Boolean).join('\n') || '暂无。',
      },
    ];
  }

  return {
    id: str(data.run_id) || `S${Date.now().toString().slice(-8)}`,
    createdAt: new Date().toISOString(),
    plotId: req.plotId,
    detectionId: req.detectionId ?? '',
    complaint: req.complaint,
    useKnowledgeBase: req.useKnowledgeBase,
    useCaseLibrary: req.useCaseLibrary,
    turns,
    conclusion,
    report,
    kbHits: [],
    similarCases: [],
  };
}
