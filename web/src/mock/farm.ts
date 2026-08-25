import dayjs from 'dayjs';
import type { Device, EdgeNodeStatus, Plot } from '@/types/domain';
import { makeRng, DEMO_SEED } from '@/mock/random';

const rng = makeRng(DEMO_SEED + 1);

/** 8 个地块，按 4×2 栅格布局在田间地图上 */
const PLOT_DEFS: {
  id: string;
  name: string;
  variety: string;
  stage: Plot['stage'];
  row: number;
  col: number;
  risk: [number, number, number];
}[] = [
  { id: 'P01', name: '东区 1 号田', variety: '南粳 9108', stage: '拔节期', row: 0, col: 0, risk: [78, 70, 62] },
  { id: 'P02', name: '东区 2 号田', variety: '南粳 9108', stage: '拔节期', row: 0, col: 1, risk: [52, 58, 44] },
  { id: 'P03', name: '东区 3 号田', variety: '淮稻 5 号', stage: '孕穗期', row: 0, col: 2, risk: [64, 66, 55] },
  { id: 'P04', name: '东区 4 号田', variety: '淮稻 5 号', stage: '孕穗期', row: 0, col: 3, risk: [30, 42, 25] },
  { id: 'P05', name: '西区 1 号田', variety: '甬优 1540', stage: '分蘖期', row: 1, col: 0, risk: [26, 38, 20] },
  { id: 'P06', name: '西区 2 号田', variety: '甬优 1540', stage: '分蘖期', row: 1, col: 1, risk: [44, 50, 38] },
  { id: 'P07', name: '西区 3 号田', variety: '扬粳 805', stage: '抽穗期', row: 1, col: 2, risk: [58, 62, 60] },
  { id: 'P08', name: '西区 4 号田', variety: '扬粳 805', stage: '灌浆期', row: 1, col: 3, risk: [22, 30, 18] },
];

const MANAGERS = ['周建明', '吴春华', '陈国平', '刘春梅'];

export const plots: Plot[] = PLOT_DEFS.map((d) => {
  const composite = Math.round(d.risk[0] * 0.45 + d.risk[1] * 0.35 + d.risk[2] * 0.2);
  return {
    id: d.id,
    name: d.name,
    variety: d.variety,
    stage: d.stage,
    areaMu: rng.int(160, 320),
    grid: { row: d.row, col: d.col },
    manager: rng.pick(MANAGERS),
    riskLevel:
      composite >= 75 ? 'critical' : composite >= 55 ? 'high' : composite >= 35 ? 'medium' : 'low',
    compositeRisk: composite,
    visualRisk: d.risk[0],
    envRisk: d.risk[1],
    trendRisk: d.risk[2],
  };
});

/** 设备清单：每地块 1 摄像头 + 1 环境传感器，部分加土壤传感器；2 边缘节点 + 1 网关 */
export const devices: Device[] = [];
for (const p of plots) {
  devices.push({
    id: `CAM-${p.id}`,
    name: `${p.name} · 高清枪机`,
    kind: 'camera',
    plotId: p.id,
    model: '海康威视 DS-2CD3T46',
    protocol: 'GB28181 / RTSP',
    status: p.id === 'P04' ? 'offline' : 'online',
    batteryPct: null,
    signal: rng.int(72, 98),
    lastHeartbeat: dayjs().subtract(4, 'minute').toISOString(),
    firmware: 'V5.7.3',
    streamUrl: `rtsp://edge-01.farm.local/${p.id}/main`,
  });
  devices.push({
    id: `ENV-${p.id}`,
    name: `${p.name} · 气象站`,
    kind: 'env_sensor',
    plotId: p.id,
    model: '建大仁科 RS-FSXJT',
    protocol: 'Modbus-RTU / 485',
    status: 'online',
    batteryPct: null,
    signal: rng.int(65, 95),
    lastHeartbeat: dayjs().subtract(2, 'minute').toISOString(),
    firmware: 'V2.1.0',
  });
  if (['P01', 'P03', 'P05', 'P07'].includes(p.id)) {
    devices.push({
      id: `SOIL-${p.id}`,
      name: `${p.name} · 土壤墒情仪`,
      kind: 'soil_sensor',
      plotId: p.id,
      model: '邯郸清易 QY-100',
      protocol: 'LoRaWAN',
      status: p.id === 'P05' ? 'fault' : 'online',
      batteryPct: rng.int(28, 88),
      signal: rng.int(54, 82),
      lastHeartbeat: dayjs().subtract(6, 'minute').toISOString(),
      firmware: 'V1.8.2',
    });
  }
}
devices.push(
  {
    id: 'EDGE-01',
    name: '一号边缘计算节点（RK3588）',
    kind: 'edge',
    plotId: 'P01',
    model: '瑞芯微 RK3588 / 8GB',
    protocol: '以太网',
    status: 'online',
    batteryPct: null,
    signal: 100,
    lastHeartbeat: dayjs().subtract(1, 'minute').toISOString(),
    firmware: 'Debian 11 / RKNN 2.3.0',
  },
  {
    id: 'EDGE-02',
    name: '二号边缘计算节点（RK3588）',
    kind: 'edge',
    plotId: 'P07',
    model: '瑞芯微 RK3588 / 8GB',
    protocol: '以太网',
    status: 'online',
    batteryPct: null,
    signal: 100,
    lastHeartbeat: dayjs().subtract(1, 'minute').toISOString(),
    firmware: 'Debian 11 / RKNN 2.3.0',
  },
  {
    id: 'GW-01',
    name: '农场物联网关',
    kind: 'gateway',
    plotId: null,
    model: '有人 USR-G806',
    protocol: '4G / 以太网上联',
    status: 'online',
    batteryPct: null,
    signal: rng.int(80, 92),
    lastHeartbeat: dayjs().subtract(3, 'minute').toISOString(),
    firmware: 'V3.4.1',
  },
);

export const edgeStatuses: EdgeNodeStatus[] = [
  {
    id: 'EDGE-01',
    name: '一号边缘节点',
    status: 'online',
    cpuPct: 63,
    memPct: 58,
    npuPct: 71,
    tempC: 58.4,
    uptimeHours: 1296,
    model: 'YOLOv8s-rice-pest v2.3.1',
    inferenceMs: 38,
    fps: 12.6,
  },
  {
    id: 'EDGE-02',
    name: '二号边缘节点',
    status: 'online',
    cpuPct: 41,
    memPct: 46,
    npuPct: 52,
    tempC: 52.1,
    uptimeHours: 984,
    model: 'YOLOv8s-rice-pest v2.3.1',
    inferenceMs: 36,
    fps: 13.4,
  },
];

export const plotById = (id: string): Plot => plots.find((p) => p.id === id) ?? plots[0];
export const deviceById = (id: string): Device | undefined => devices.find((d) => d.id === id);
