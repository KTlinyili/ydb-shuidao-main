# 稻影知微 Web 前端

React + TypeScript + Vite + Ant Design + ECharts 实现的水稻病虫害监测预警前端，
当前为**纯前端 Mock 演示版**：无需后端即可运行、可交互，直接用于比赛演示。

## 运行

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # 生产构建（dist/）
npm run typecheck  # tsc --noEmit
```

## 页面

| 路由 | 页面 | 要点 |
| --- | --- | --- |
| `/dashboard` | 首页概览 | 今日预警/高风险地块/识别帧数/设备在线率/平均温湿度、重点地块 Top3、监测点地图、实时检测动态、预警列表、病虫害统计、7 天风险趋势、设备状态 |
| `/live` | 实时监测 | 8 路通道卡片、最新推理帧分析视图（检测框标注）、实时检测流水 |
| `/identify` | 病虫害识别 | 上传图片或载入示例帧 → 模拟 RK3588 推理 → 检测框/置信度/病斑面积/严重程度 |
| `/environment` | 环境监测 | 温度/湿度/光照/土壤含水率，24h·7d·30d 趋势，地块对比 |
| `/warnings` | 风险预警 | 四级预警列表、风险构成（视觉/环境/趋势）、处置流转、一键派单 |
| `/consult` | 智能会诊 | 四专家两轮会诊动画、结论（判断/证据/风险等级/防治/田间管理/观察项）、结构化报告 |
| `/map` | 田间地图 | 4×2 地块总平面、风险着色、地块详情与设备清单 |
| `/knowledge` | 知识库 | 植保知识库（RAG 检索）+ 水稻病例库 |
| `/devices` | 设备管理 | 设备台账、边缘节点 NPU/CPU/温度、心跳概况、接入设备 |
| `/history` | 历史记录 | 检测记录归档查询、记录详情抽屉 |
| `/settings` | 系统设置 | 风险权重/阈值、视觉模型参数、多 Agent 配置、数据接口、消息通知 |

## 架构与扩展点

```
src/
  api/services.ts     统一数据入口：USE_MOCK=true 走本地模拟；
                      接后端时置 false 并按 ENDPOINTS 注释实现 fetch
  types/domain.ts     领域类型 = 前后端 DTO 契约
  mock/               种子随机数据（farm/env/detections/warnings/knowledge/consult）
  utils/risk.ts       风险融合纯函数：视觉 45% + 环境 35% + 趋势 20%
  components/         FrameAnalysis（检测帧标注视图）、FieldMap（田间地图）、
                      charts（ECharts 封装）、WarningList、common（统计卡/标签）
  pages/              11 个页面
```

- **视频流接入**：`FrameAnalysis` 背景层替换为 `<video>` 即可，检测框逻辑不变。
- **检测模型接入**：`POST /api/v1/vision/infer` 返回与 `DetectionRecord` 同构 JSON。
- **会诊接入**：`runConsult()` 替换为 `POST /api/v1/diagnosis/run`（FastAPI 后端已具备多 Agent 编排）。

## 视觉规范

企业级后台风格（参考飞书/华为云/阿里云控制台）：浅灰背景 `#F4F6F5`、白色卡片、
低饱和农业绿品牌色 `#2E8B62`、圆角 6–10px、克制阴影；禁用蓝紫渐变、霓虹、
玻璃拟态与夸张圆角。
