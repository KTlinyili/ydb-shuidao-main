/**
 * 稻影知微 · 领域类型定义
 *
 * 这些类型同时作为 Mock 数据与后端 API DTO 的契约：
 * 后续接入 FastAPI 后端时，仅需在 src/api/services.ts 中替换数据来源，
 * 页面与组件无需改动。
 */

/** 病虫害类别标识（与边缘端视觉模型 classes.txt 对齐） */
export type PestKey =
  | 'rice_blast' // 稻瘟病
  | 'sheath_blight' // 纹枯病
  | 'bacterial_blight' // 白叶枯病
  | 'brown_spot' // 褐斑病（胡麻斑病）
  | 'bacterial_streak' // 细菌性条斑病
  | 'rice_planthopper' // 稻飞虱
  | 'rice_leaf_roller' // 稻纵卷叶螟
  | 'striped_stem_borer'; // 二化螟

/** 病虫害大类 */
export type PestKind = 'disease' | 'pest';

/** 严重程度（视觉检测输出） */
export type Severity = '轻微' | '中等' | '偏重' | '严重';

/** 综合风险等级（视觉 + 环境 + 趋势融合后的分级预警） */
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

/** 预警处理状态 */
export type WarningStatus = 'pending' | 'processing' | 'resolved';

/** 设备类型 */
export type DeviceKind = 'camera' | 'env_sensor' | 'soil_sensor' | 'edge' | 'gateway';

/** 设备在线状态 */
export type DeviceStatus = 'online' | 'offline' | 'fault';

/** 检测记录来源 */
export type DetectSource = 'auto_patrol' | 'scheduled_capture' | 'manual_upload';

/** 生育期 */
export type GrowthStage = '分蘖期' | '拔节期' | '孕穗期' | '抽穗期' | '灌浆期';

/** 单个检测框 */
export interface DetectionBox {
  id: string;
  pest: PestKey;
  /** 置信度 0-1 */
  confidence: number;
  /** 病斑面积占比（占画面/叶片区域，%） */
  lesionAreaPct: number;
  severity: Severity;
  /** 归一化边界框 [x, y, w, h]，取值 0-1 */
  bbox: [number, number, number, number];
}

/** 一次视觉检测记录 */
export interface DetectionRecord {
  id: string;
  time: string; // ISO
  plotId: string;
  cameraId: string;
  source: DetectSource;
  boxes: DetectionBox[];
  /** 视觉风险分 0-100 */
  visualRisk: number;
  /** 推理耗时 ms（RK3588 NPU） */
  inferenceMs: number;
  /** 用于复现画面的种子 */
  imageSeed: number;
  handled: boolean;
}

/** 地块 */
export interface Plot {
  id: string;
  name: string;
  variety: string;
  stage: GrowthStage;
  areaMu: number;
  /** 在田间地图栅格中的位置 */
  grid: { row: number; col: number };
  manager: string;
  riskLevel: RiskLevel;
  compositeRisk: number;
  visualRisk: number;
  envRisk: number;
  trendRisk: number;
}

/** 设备 */
export interface Device {
  id: string;
  name: string;
  kind: DeviceKind;
  plotId: string | null;
  model: string;
  protocol: string;
  status: DeviceStatus;
  batteryPct: number | null;
  signal: number; // 0-100
  lastHeartbeat: string; // ISO
  firmware: string;
  /** 摄像头流地址（预留） */
  streamUrl?: string;
}

/** 边缘节点运行状态（RK3588） */
export interface EdgeNodeStatus {
  id: string;
  name: string;
  status: DeviceStatus;
  cpuPct: number;
  memPct: number;
  npuPct: number;
  tempC: number;
  uptimeHours: number;
  model: string;
  inferenceMs: number;
  fps: number;
}

/** 环境指标键 */
export type EnvMetricKey = 'temperature' | 'humidity' | 'light' | 'soilMoisture';

/** 单时刻环境快照 */
export interface EnvSnapshot {
  time: string; // ISO
  temperature: number; // °C
  humidity: number; // %RH
  light: number; // klx
  soilMoisture: number; // %VWC
}

/** 环境时间序列查询范围 */
export type TimeRange = '24h' | '7d' | '30d';

/** 风险时间点（按日聚合或按时段聚合） */
export interface RiskPoint {
  time: string;
  visual: number;
  env: number;
  trend: number;
  composite: number;
}

/** 预警记录 */
export interface WarningRecord {
  id: string;
  time: string; // ISO
  plotId: string;
  pest: PestKey | 'multi';
  level: RiskLevel;
  compositeRisk: number;
  visualRisk: number;
  envRisk: number;
  trendRisk: number;
  /** 触发规则说明 */
  trigger: string;
  status: WarningStatus;
  /** 关联检测记录 */
  detectionId: string;
  /** 处置建议 */
  advice: string[];
  handler?: string;
  resolvedAt?: string;
}

/** 知识库文档 */
export interface KnowledgeDoc {
  id: string;
  title: string;
  category: PestKey | 'general';
  source: string;
  tags: string[];
  updatedAt: string;
  /** 结构化正文分节 */
  sections: { heading: string; body: string }[];
  /** 检索匹配度（仅搜索结果携带） */
  score?: number;
}

/** 病例库病例 */
export interface CaseRecord {
  id: string;
  time: string;
  plotId: string;
  diagnosis: PestKey;
  confidence: number;
  severity: Severity;
  status: 'verified' | 'unverified';
  summary: string;
  treatment: string;
  outcome: '已恢复' | '观察中' | '防治中';
  imageSeed: number;
  agentHighlights: { agent: string; point: string }[];
}

/** 多 Agent 角色（与后端 orchestrator 对齐） */
export type AgentKey =
  | 'pest_evidence_officer' // 病虫害证据官
  | 'differential_officer' // 鉴别诊断官
  | 'plant_protection_expert' // 植保专家
  | 'field_management_officer'; // 田间管理官

/** Agent 发言轮次 */
export interface AgentTurn {
  agent: AgentKey;
  round: number;
  /** 结构化要点，键名与后端 protocol_schema 字段对齐 */
  fields: { label: string; items: string[] }[];
  citations: string[];
  latencyMs: number;
}

/** 会诊结论 */
export interface ConsultConclusion {
  diagnosis: PestKey | 'multi';
  confidence: number;
  riskLevel: RiskLevel;
  judgment: string;
  evidence: string[];
  measures: string[];
  fieldAdvice: string[];
  observations: string[];
}

/** 一次完整会诊会话 */
export interface ConsultSession {
  id: string;
  createdAt: string;
  plotId: string;
  detectionId: string;
  complaint: string;
  useKnowledgeBase: boolean;
  useCaseLibrary: boolean;
  turns: AgentTurn[];
  conclusion: ConsultConclusion | null;
  report: { heading: string; body: string }[] | null;
  kbHits: { docId: string; title: string; snippet: string; score: number }[];
  similarCases: { caseId: string; similarity: number }[];
}

/** 会诊请求参数（映射后端 POST /api/v1/diagnosis/run） */
export interface ConsultRequest {
  plotId: string;
  detectionId?: string;
  complaint: string;
  useKnowledgeBase: boolean;
  useCaseLibrary: boolean;
  /** 待诊断的田间照片（真实后端模式必传） */
  image?: File;
}

/** Dashboard 汇总指标 */
export interface DashboardStats {
  todayWarnings: number;
  todayWarningsDelta: number;
  highRiskPlots: number;
  totalPlots: number;
  todayDetections: number;
  deviceOnlineRate: number;
  onlineDevices: number;
  totalDevices: number;
  avgHumidity: number;
  avgTemperature: number;
}
