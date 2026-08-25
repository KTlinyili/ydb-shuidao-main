# 稻影知微 RiceGuard · 水稻病虫害智能监测与预警系统

面向智慧大田场景的水稻病虫害智能监测与预警系统（大田农作物病虫害智能检测与预警赛题参赛项目）。系统由 **RK3588 边缘终端** 接入 RGB 摄像头与温度、空气湿度、光照、土壤含水率等传感器，完成本地视觉推理与环境数据汇聚；Web 端融合视觉风险、环境风险与历史趋势形成综合风险分级预警，并提供多 Agent 智能会诊与防治决策支持。

## 系统组成

```
┌─ 传感层 ────────────────────────────────────────┐
│ RGB 摄像头 ×8 · 气象站 ×8 · 土壤墒情仪 ×4 · 网关 │
└────────────────────┬─────────────────────────────┘
                     │ RTSP / Modbus / LoRaWAN
┌─ 边缘层（RK3588）──┴─────────────────────────────┐
│ YOLOv8s-rice-pest（RKNN INT8，38ms/帧）           │
│ 检测：稻瘟病/纹枯病/白叶枯病/褐斑病/细菌性条斑病  │
│ 　　　稻飞虱/稻纵卷叶螟/二化螟                    │
│ 输出：检测框·类别·置信度·病斑面积·严重程度        │
└────────────────────┬─────────────────────────────┘
                     │ MQTT / HTTP
┌─ 平台层（本仓库）─┴─────────────────────────────┐
│ Web 前端（React + TS + Vite + AntD + ECharts）    │
│ 风险融合：视觉×45% + 环境×35% + 趋势×20%          │
│ 分级预警：低/中/高/严重（<35/35-54/55-74/≥75）     │
│ 多 Agent：证据官→鉴别官→植保专家→田间管理官        │
└──────────────────────────────────────────────────┘
```

## 仓库结构

```
web/                  Web 前端（当前为纯前端 Mock 版，可直接演示）
  src/pages/          11 个页面：首页概览/实时监测/病虫害识别/环境监测/
                      风险预警/智能会诊/田间地图/知识库/设备管理/历史记录/系统设置
  src/api/services.ts 统一数据入口（Mock 开关 + 后端接口映射）
  src/mock/           演示数据（地块/设备/检测/环境/预警/知识库/病例）
  src/utils/risk.ts   风险融合模型（纯函数）
app/                  FastAPI 多 Agent 诊断后端（自 OminiBerry 迁移，适配中）
knowledge_bases/      植保知识库（RAG 文档源）
case_library/         水稻病例库（verified / unverified）
classes.txt           视觉模型类别表（8 类，前后端契约）
```

## 快速开始（Web 前端）

```bash
cd web
npm install
npm run dev        # http://localhost:5173
npm run build      # 生产构建
npm run typecheck  # 类型检查
```

Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`，后端启动后无需改配置。

## 接入后端（预留）

前端所有数据经 `web/src/api/services.ts` 统一取数，`USE_MOCK = false` 即切换为
API 模式。已预留的接口契约：

| 能力 | 接口 |
| --- | --- |
| 地块/设备 | `GET /api/v1/plots`、`GET /api/v1/devices` |
| 视觉检测 | `GET /api/v1/detections`、`WS /api/v1/stream/detection` |
| 环境序列 | `GET /api/v1/env/series?range=24h\|7d\|30d` |
| 风险序列 | `GET /api/v1/risk/series`、`GET /api/v1/risk/lesion-area` |
| 预警 | `GET /api/v1/warnings` |
| 知识/病例 | `GET /api/v1/knowledge/docs?q=`、`GET /api/v1/cases` |
| 多 Agent 会诊 | `POST /api/v1/diagnosis/run` |

## 后端（OminiBerry 迁移说明）

多 Agent 编排沿自莓影知微（OminiBerry），角色调整为：病虫害证据官、鉴别诊断官、
植保专家、田间管理官。运行方式：

```bash
python -m pip install -r requirements.txt
cp .env.example .env   # 填入 LLM 配置
python scripts/run_api.py
```

## 说明

- 当前 Web 端为纯前端 Mock 演示版，数据为模拟数据（2026-08-17 基准），
  风险数值由 `src/utils/risk.ts` 中的融合模型实时计算。
- 更换视觉模型时须保证输出类别顺序与 `classes.txt` 一致。
