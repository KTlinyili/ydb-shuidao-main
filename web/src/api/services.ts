/**
 * API 服务层：统一的数据入口。
 *
 * 当前为纯前端 Mock 模式（USE_MOCK = true）。
 * 接入后端时将 USE_MOCK 置为 false，并在 ENDPOINTS 中核对路径 ——
 * 页面与组件只依赖本文件导出的函数，不感知数据来源。
 */
import dayjs from 'dayjs';
import type {
  AgentTurn,
  CaseRecord,
  DashboardStats,
  DetectionRecord,
  Device,
  EdgeNodeStatus,
  EnvSnapshot,
  KnowledgeDoc,
  Plot,
  RiskPoint,
  TimeRange,
  WarningRecord,
  ConsultRequest,
  ConsultSession,
} from '@/types/domain';
import { plots, devices, edgeStatuses } from '@/mock/farm';
import { detectionRecords, latestDetections } from '@/mock/detections';
import { warningRecords } from '@/mock/warnings';
import { knowledgeDocs, caseRecords } from '@/mock/knowledge';
import { genEnvSeries, genLesionAreaSeries, genRiskSeries, MOCK_NOW } from '@/mock/env';
import { buildConsultSession } from '@/mock/consult';
import { computeEnvRisk } from '@/utils/risk';
import { mapRunResponseToSession } from './consultAdapter';

export const USE_MOCK = true;

/**
 * 智能会诊页数据来源开关：true = 上传田间照片调用真实后端
 * POST /api/v1/diagnosis/run（Vite 已将 /api 代理到 127.0.0.1:8000）。
 * 其余页面仍走 USE_MOCK。
 */
export const CONSULT_USE_REAL_API = true;

/**
 * 后端接口映射（预留）。后端就绪后按此路径实现 fetch 封装：
 * - GET  /api/v1/plots                      → listPlots
 * - GET  /api/v1/devices                    → listDevices
 * - GET  /api/v1/detections?plotId=&days=   → listDetections
 * - GET  /api/v1/detections/:id             → getDetection
 * - GET  /api/v1/env/series?range=&plotId=  → getEnvSeries
 * - GET  /api/v1/risk/series?range=&plotId= → getRiskSeries
 * - GET  /api/v1/risk/lesion-area           → getLesionAreaSeries
 * - GET  /api/v1/warnings?status=&level=    → listWarnings
 * - GET  /api/v1/knowledge/docs?q=          → searchKnowledge
 * - GET  /api/v1/cases                      → listCases
 * - POST /api/v1/diagnosis/run              → runConsult（多 Agent 会诊）
 * - GET  /api/v1/dashboard/stats            → getDashboardStats
 * - WS   /api/v1/stream/detection           → 实时检测帧推送（WebSocket）
 */
export const ENDPOINTS = {
  plots: '/api/v1/plots',
  devices: '/api/v1/devices',
  detections: '/api/v1/detections',
  envSeries: '/api/v1/env/series',
  riskSeries: '/api/v1/risk/series',
  lesionArea: '/api/v1/risk/lesion-area',
  warnings: '/api/v1/warnings',
  knowledge: '/api/v1/knowledge/docs',
  cases: '/api/v1/cases',
  diagnosisRun: '/api/v1/diagnosis/run',
  dashboardStats: '/api/v1/dashboard/stats',
  detectionStream: '/api/v1/stream/detection',
} as const;

const delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** 以最新预警与最新检测校准地块风险，保证地图/卡片/预警列表口径一致 */
function calibratedPlots(): Plot[] {
  const latestWarn = new Map<string, WarningRecord>();
  for (const w of warningRecords) {
    const prev = latestWarn.get(w.plotId);
    if (!prev || w.time > prev.time) latestWarn.set(w.plotId, w);
  }
  const latestDet = new Map<string, DetectionRecord>();
  for (const d of detectionRecords) {
    const prev = latestDet.get(d.plotId);
    if (!prev || d.time > prev.time) latestDet.set(d.plotId, d);
  }
  return plots.map((p) => {
    const w = latestWarn.get(p.id);
    const d = latestDet.get(p.id);
    const visual = d ? d.visualRisk : p.visualRisk;
    if (!w) {
      const composite = Math.round(visual * 0.45 + p.envRisk * 0.35 + p.trendRisk * 0.2);
      return {
        ...p,
        visualRisk: visual,
        compositeRisk: composite,
        riskLevel: composite >= 75 ? 'critical' : composite >= 55 ? 'high' : composite >= 35 ? 'medium' : 'low',
      };
    }
    return {
      ...p,
      visualRisk: visual,
      envRisk: w.envRisk,
      trendRisk: w.trendRisk,
      compositeRisk: w.compositeRisk,
      riskLevel: w.level,
    };
  });
}

export async function listPlots(): Promise<Plot[]> {
  await delay(60);
  return calibratedPlots();
}

export async function listDevices(): Promise<Device[]> {
  await delay(60);
  return devices;
}

export async function listEdgeStatuses(): Promise<EdgeNodeStatus[]> {
  await delay(40);
  return edgeStatuses;
}

export async function listDetections(plotId?: string, days = 7): Promise<DetectionRecord[]> {
  await delay(80);
  const from = MOCK_NOW.subtract(days, 'day');
  return detectionRecords.filter(
    (d) => (!plotId || d.plotId === plotId) && dayjsMin(d.time, from),
  );
}

function dayjsMin(a: string, bDayjs: import('dayjs').Dayjs): boolean {
  return new Date(a) >= bDayjs.toDate();
}

export async function getDetection(id: string): Promise<DetectionRecord | undefined> {
  await delay(40);
  return detectionRecords.find((d) => d.id === id);
}

export async function getLatestDetections(): Promise<DetectionRecord[]> {
  await delay(50);
  return latestDetections;
}

export async function getEnvSeries(range: TimeRange, plotId?: string): Promise<EnvSnapshot[]> {
  await delay(60);
  return genEnvSeries(range, plotId);
}

export async function getRiskSeries(range: TimeRange, plotId: string): Promise<RiskPoint[]> {
  await delay(60);
  return genRiskSeries(range, plotId);
}

export async function getLesionAreaSeries(
  range: TimeRange,
  plotId: string,
): Promise<{ time: string; areaMu: number }[]> {
  await delay(60);
  return genLesionAreaSeries(range, plotId);
}

export async function listWarnings(): Promise<WarningRecord[]> {
  await delay(70);
  return warningRecords;
}

export async function searchKnowledge(q: string): Promise<KnowledgeDoc[]> {
  await delay(120);
  if (!q.trim()) return knowledgeDocs;
  const needle = q.trim().toLowerCase();
  return knowledgeDocs
    .map((d) => {
      let score = 0;
      if (d.title.toLowerCase().includes(needle)) score += 0.6;
      for (const t of d.tags) if (t.toLowerCase().includes(needle)) score += 0.25;
      for (const s of d.sections) {
        if (s.heading.toLowerCase().includes(needle)) score += 0.15;
        if (s.body.toLowerCase().includes(needle)) score += 0.2;
      }
      return { ...d, score: Math.min(0.98, score || 0) };
    })
    .filter((d) => (d.score ?? 0) > 0)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
}

export async function listCases(): Promise<CaseRecord[]> {
  await delay(60);
  return caseRecords;
}

export async function runConsult(req: ConsultRequest): Promise<ConsultSession> {
  if (CONSULT_USE_REAL_API) {
    return runConsultRemote(req);
  }
  // Mock 分支：模拟多 Agent 两轮推理耗时
  await delay(1800);
  const plot = plots.find((p) => p.id === req.plotId) ?? plots[0];
  const det =
    detectionRecords.find((d) => d.id === req.detectionId) ??
    detectionRecords.find((d) => d.plotId === req.plotId) ??
    detectionRecords[0];
  return buildConsultSession(
    plot,
    det,
    req.complaint,
    req.useKnowledgeBase,
    req.useCaseLibrary,
    `S${Date.now().toString().slice(-8)}`,
  );
}

/** 真实多专家会诊：上传田间照片，走 FastAPI 诊断管线 */
async function runConsultRemote(req: ConsultRequest): Promise<ConsultSession> {
  if (!req.image) throw new Error('请先上传待会诊的田间照片');
  const plot = plots.find((p) => p.id === req.plotId) ?? plots[0];
  const det = detectionRecords.find((d) => d.id === req.detectionId);
  const context = [
    `地块：${plot.id} ${plot.name}（品种 ${plot.variety}，${plot.stage}，管理员 ${plot.manager}）`,
    det
      ? `关联视觉检测：${det.id}，检出 ${det.boxes.length} 处目标，视觉风险分 ${det.visualRisk}`
      : '',
    `田间主诉：${req.complaint}`,
  ]
    .filter(Boolean)
    .join('\n');

  const form = new FormData();
  form.append('problem_name', '水稻病虫害图像诊断报告');
  form.append('case_text', context);
  form.append('stage', 'initial');
  form.append('n_rounds', '2');
  form.append('image', req.image, req.image.name || 'upload.jpg');

  let resp: Response;
  try {
    resp = await fetch(ENDPOINTS.diagnosisRun, { method: 'POST', body: form });
  } catch {
    throw new Error('无法连接会诊服务：请确认后端已启动（127.0.0.1:8000）');
  }
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const err = (await resp.json()) as { detail?: unknown };
      if (typeof err.detail === 'string') detail = err.detail;
    } catch {
      // 非 JSON 错误体时保留状态码信息
    }
    throw new Error(`会诊服务返回错误（${detail}）`);
  }
  const data = await resp.json();
  return mapRunResponseToSession(data, req);
}

export async function getDashboardStats(): Promise<DashboardStats> {
  await delay(50);
  const today = MOCK_NOW.format('YYYY-MM-DD');
  const isToday = (iso: string) => dayjs(iso).format('YYYY-MM-DD') === today;
  const todayWarnings = warningRecords.filter((w) => isToday(w.time));
  const yesterday = MOCK_NOW.subtract(1, 'day').format('YYYY-MM-DD');
  const yesterdayWarnings = warningRecords.filter(
    (w) => dayjs(w.time).format('YYYY-MM-DD') === yesterday,
  );
  const online = devices.filter((d) => d.status === 'online').length;
  const env = genEnvSeries('24h');
  const calibrated = calibratedPlots();
  return {
    todayWarnings: todayWarnings.length,
    todayWarningsDelta: todayWarnings.length - yesterdayWarnings.length,
    highRiskPlots: calibrated.filter(
      (p) => p.riskLevel === 'high' || p.riskLevel === 'critical',
    ).length,
    totalPlots: calibrated.length,
    todayDetections: detectionRecords.filter((d) => isToday(d.time)).length,
    deviceOnlineRate: Math.round((online / devices.length) * 1000) / 10,
    onlineDevices: online,
    totalDevices: devices.length,
    avgHumidity: Math.round((env.reduce((a, b) => a + b.humidity, 0) / env.length) * 10) / 10,
    avgTemperature: Math.round((env.reduce((a, b) => a + b.temperature, 0) / env.length) * 10) / 10,
  };
}

export async function getEnvRiskNow(plotId: string): Promise<number> {
  await delay(30);
  const env = genEnvSeries('24h', plotId).at(-1)!;
  const pests = Array.from(
    new Set(
      detectionRecords
        .filter((d) => d.plotId === plotId)
        .slice(0, 5)
        .flatMap((d) => d.boxes.map((b) => b.pest)),
    ),
  );
  return computeEnvRisk(env, pests);
}

/** 检测框画布按 agent 顺序播放轮次（会诊页动画用） */
export function orderTurns(turns: AgentTurn[]): AgentTurn[] {
  return [...turns].sort((a, b) => a.round - b.round);
}
