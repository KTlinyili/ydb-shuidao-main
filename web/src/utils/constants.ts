import type { PestKey, PestKind, RiskLevel } from '@/types/domain';

/** 品牌色（低饱和农业绿） */
export const BRAND = {
  primary: '#2E8B62',
  primaryDeep: '#257450',
  primarySoft: '#E8F3ED',
  text: '#2B333A',
  textSecondary: '#64707C',
  textTertiary: '#8B96A0',
  bgLayout: '#F4F6F5',
  bgCard: '#FFFFFF',
  border: '#E4E9E6',
  borderLight: '#EEF1EF',
};

/** 病虫害元信息表 */
export interface PestMeta {
  key: PestKey;
  name: string;
  shortName: string;
  kind: PestKind;
  /** 图表配色（低饱和分类色板） */
  color: string;
  latin: string;
  /** 主要为害部位 */
  site: string;
  /** 适发环境条件（用于环境风险模型与展示） */
  favorable: string;
}

export const PEST_META: Record<PestKey, PestMeta> = {
  rice_blast: {
    key: 'rice_blast',
    name: '稻瘟病',
    shortName: '稻瘟',
    kind: 'disease',
    color: '#B85C5C',
    latin: 'Magnaporthe oryzae',
    site: '叶、穗颈、节',
    favorable: '24~28℃、相对湿度>90%、结露时间长、偏施氮肥',
  },
  sheath_blight: {
    key: 'sheath_blight',
    name: '纹枯病',
    shortName: '纹枯',
    kind: 'disease',
    color: '#C08A3E',
    latin: 'Rhizoctonia solani',
    site: '叶鞘、叶片',
    favorable: '30℃左右、湿度>95%、密植封行、偏施氮肥',
  },
  bacterial_blight: {
    key: 'bacterial_blight',
    name: '白叶枯病',
    shortName: '白叶枯',
    kind: 'disease',
    color: '#7C9A5B',
    latin: 'Xanthomonas oryzae pv. oryzae',
    site: '叶片',
    favorable: '25~30℃、大风暴雨伤口、淹水灌溉',
  },
  brown_spot: {
    key: 'brown_spot',
    name: '褐斑病',
    shortName: '褐斑',
    kind: 'disease',
    color: '#9A7B4F',
    latin: 'Bipolaris oryzae',
    site: '叶片',
    favorable: '缺肥、土壤贫瘠、酸性土壤、多雨寡照',
  },
  bacterial_streak: {
    key: 'bacterial_streak',
    name: '细菌性条斑病',
    shortName: '细条斑',
    kind: 'disease',
    color: '#5F8FA8',
    latin: 'Xanthomonas oryzae pv. oryzicola',
    site: '叶片',
    favorable: '28~30℃、高湿、暴风雨传播',
  },
  rice_planthopper: {
    key: 'rice_planthopper',
    name: '稻飞虱',
    shortName: '飞虱',
    kind: 'pest',
    color: '#8C7CC7',
    latin: 'Nilaparvata lugens',
    site: '茎基部',
    favorable: '25~28℃、暖冬、偏施氮肥、密植荫蔽',
  },
  rice_leaf_roller: {
    key: 'rice_leaf_roller',
    name: '稻纵卷叶螟',
    shortName: '卷叶螟',
    kind: 'pest',
    color: '#4FA8A0',
    latin: 'Cnaphalocrocis medinalis',
    site: '叶片',
    favorable: '22~28℃、湿度大、嫩叶丰富、迁入峰',
  },
  striped_stem_borer: {
    key: 'striped_stem_borer',
    name: '二化螟',
    shortName: '二化螟',
    kind: 'pest',
    color: '#A87B55',
    latin: 'Chilo suppressalis',
    site: '茎秆',
    favorable: '25~30℃、秧田至拔节期、稻桩残留虫源',
  },
};

export const PEST_ORDER: PestKey[] = [
  'rice_blast',
  'sheath_blight',
  'bacterial_blight',
  'brown_spot',
  'bacterial_streak',
  'rice_planthopper',
  'rice_leaf_roller',
  'striped_stem_borer',
];

/** 风险等级配置 */
export const RISK_LEVEL_META: Record<
  RiskLevel,
  { label: string; color: string; bg: string; border: string; range: string; action: string }
> = {
  low: {
    label: '低风险',
    color: '#2E7D5B',
    bg: '#EAF4EE',
    border: '#CBE5D6',
    range: '0 ~ 34',
    action: '常规巡检',
  },
  medium: {
    label: '中风险',
    color: '#9A6D15',
    bg: '#FAF3E0',
    border: '#EEDFB2',
    range: '35 ~ 54',
    action: '加密监测',
  },
  high: {
    label: '高风险',
    color: '#C05621',
    bg: '#FBEEE5',
    border: '#F3D5BF',
    range: '55 ~ 74',
    action: '限时处置',
  },
  critical: {
    label: '严重风险',
    color: '#B93A3A',
    bg: '#FBECEC',
    border: '#F0CBCB',
    range: '75 ~ 100',
    action: '立即防治',
  },
};

/** 严重程度档位色（低饱和） */
export const SEVERITY_META: Record<string, { color: string }> = {
  轻微: { color: '#5E8C61' },
  中等: { color: '#B08A2E' },
  偏重: { color: '#C05621' },
  严重: { color: '#B93A3A' },
};

/** 综合风险融合权重：视觉 + 环境 + 历史趋势 */
export const RISK_WEIGHTS = { visual: 0.45, env: 0.35, trend: 0.2 };

/** 视觉模型信息（展示用，接入后端后从 /api/v1/model/info 获取） */
export const VISION_MODEL = {
  name: 'YOLOv8s-rice-pest',
  version: 'v2.3.1',
  classesFile: 'classes.txt (8 类)',
  device: 'RK3588 NPU (INT8)',
  inputSize: '640×640',
  classes: PEST_ORDER.length,
};

export const FARM_INFO = {
  name: '金穗智慧农场 · 一号基地',
  region: '江苏省泰州市兴化市',
  season: '2026 年中稻季',
  totalAreaMu: 1860,
  riceType: '粳稻 / 籼粳杂交',
};

/** 仪表盘等页面的时间范围选项 */
export const TIME_RANGE_OPTIONS = [
  { value: '24h', label: '近 24 小时' },
  { value: '7d', label: '近 7 天' },
  { value: '30d', label: '近 30 天' },
] as const;
