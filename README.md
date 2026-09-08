# 稻影知微 RiceGuard · 水稻病虫害智能监测与预警系统

面向智慧大田场景的水稻病虫害智能监测与预警系统（大田农作物病虫害智能检测与预警赛题参赛项目）。系统由 **RK3588 边缘终端** 接入 RGB 摄像头与温度、空气湿度、光照、土壤含水率等传感器，完成本地视觉推理与环境数据汇聚；Web 端融合视觉风险、环境风险与历史趋势形成综合风险分级预警，并提供多 Agent 智能会诊与防治决策支持。

## 功能特性

- **多模态识别**：支持文字描述、静态图片、视频文件三种输入方式
- **可视化监测**：实时视频流检测，检测框 + 类别 + 置信度 + FPS 叠加显示
- **环境实时感知**：温度、空气湿度、光照、土壤含水率四指标实时监测
- **智能风险预警**：视觉×45% + 环境×35% + 趋势×20% 综合风险融合，四级预警
- **多 Agent 会诊**：证据官→鉴别官→植保专家→田间管理官 链式诊断
- **移动端适配**：响应式设计，手机浏览器直接访问，底部导航栏
- **环境模拟器**：内置环境数据模拟器，支持异常状态注入，便于演示测试

## 系统组成

```
┌─ 传感层 ────────────────────────────────────────┐
│ RGB 摄像头 ×8 · 气象站 ×8 · 土壤墒情仪 ×4 · 网关 │
└────────────────────┬─────────────────────────────┘
                     │ RTSP / Modbus / LoRaWAN
┌─ 边缘层（RK3588）──┴─────────────────────────────┐
│ YOLOv8 检测 + 分类模型（RKNN INT8）               │
│ 检测：稻瘟病/纹枯病/白叶枯病/褐斑病/细菌性条斑病  │
│ 分类：健康/棕色斑点/叶斑病/细菌性条斑病            │
│ 输出：检测框·类别·置信度·病斑面积·严重程度        │
└────────────────────┬─────────────────────────────┘
                     │ MQTT / HTTP
┌─ 平台层（本仓库）─┴─────────────────────────────┐
│ Web 前端（React + TS + Vite + AntD + ECharts）    │
│ 移动端响应式 · 视频检测 · 环境模拟器 · 风险预警   │
│ 风险融合：视觉×45% + 环境×35% + 趋势×20%          │
│ 分级预警：低/中/高/严重                            │
│ 多 Agent：证据官→鉴别官→植保专家→田间管理官        │
└──────────────────────────────────────────────────┘
```

## 仓库结构

```
web/                          Web 前端
  src/pages/                  11 个页面
  src/layouts/MainLayout.tsx  主布局（含移动端适配）
  src/styles/global.css       全局样式（含响应式媒体查询）
  src/api/services.ts         统一数据入口
  src/mock/                   演示数据

app/                          FastAPI 后端
  api/
    routes_diagnosis.py       智能会诊接口
    routes_vision.py          图片分类识别接口
    routes_video.py           视频检测接口（异步任务）
    routes_text_diagnosis.py  文字症状诊断接口
    routes_environment.py     环境监测 + 模拟器接口
    routes_warnings.py        风险预警接口
  core/vision/
    yolo_cls_service.py       YOLO 分类模型服务
  services/
    environment_simulator.py  环境数据模拟器
    risk_service.py           风险计算与预警服务
    text_diagnosis.py         文字症状分析引擎
  models/                     模型权重
    best.pt / best.onnx       检测模型
    best_cls.pt / best_cls.onnx  分类模型（4类）

yolo_train/                   模型训练相关
  rice_cls/                   分类数据集
  train_cls.py                分类训练脚本
  robust_test.py              鲁棒性测试脚本
  robust_test_results.json    鲁棒测试结果

docs/
  robust_test_report.html     鲁棒测试与对比实验报告

knowledge_bases/              植保知识库
case_library/                 水稻病例库
classes.txt                   视觉模型类别表
```

## 快速开始

### Web 前端

```bash
cd web
npm install
npm run dev        # http://localhost:5173
npm run build      # 生产构建
npm run typecheck  # 类型检查
```

Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`。

### 移动端访问

前端已内置响应式适配：
- **平板（<992px）**：侧边栏抽屉模式，点击菜单按钮展开
- **手机（<768px）**：底部导航栏，核心页面一键直达

用手机浏览器访问局域网地址即可直接使用。

### 后端

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 LLM 配置
python -m uvicorn app.main:app --reload --port 8000
```

### 一键启动

```bash
# Windows 下双击即可
run_all.bat       # 前后端一起启动
run_backend.bat   # 仅启动后端
run_frontend.bat  # 仅启动前端
```

### Mock / 真实模式切换

前端 `src/api/services.ts` 中 `USE_MOCK = true` 为演示模式（不依赖后端），
设为 `false` 后自动调用真实后端接口。

## API 接口

### 视觉识别

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/vision/image` | POST | 图片分类识别 |
| `/api/v1/vision/models` | GET | 可用模型列表 |
| `/api/v1/video/video` | POST | 视频检测（返回 job_id） |
| `/api/v1/video/{job_id}/status` | GET | 查询视频检测进度 |

### 文字症状诊断

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/text/diagnose` | POST | 文字症状分析（规则匹配+知识库） |
| `/api/v1/text/keywords` | GET | 病害关键词库 |

支持8种水稻病害的文字症状匹配：稻瘟病、纹枯病、褐斑病、细菌性条斑病、稻飞虱、稻纵卷叶螟、二化螟、稻曲病。输入症状描述后返回匹配度排序的候选病害、风险等级和治疗建议。

### 环境监测

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/environment/current` | GET | 当前环境数据 |
| `/api/v1/environment/series` | GET | 环境数据历史序列 |
| `/api/v1/environment/devices` | GET | 设备列表 |
| `/api/v1/environment/simulator/status` | GET | 模拟器状态 |
| `/api/v1/environment/simulator/anomaly` | POST | 设置异常状态 |
| `/api/v1/environment/simulator/config` | POST | 配置模拟器参数 |

### 风险预警

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/warnings` | GET | 预警列表 |
| `/api/v1/warnings/{id}/ack` | POST | 确认预警 |
| `/api/v1/warnings/{id}/close` | POST | 关闭预警 |
| `/api/v1/warnings/risk/compute` | GET | 计算综合风险 |
| `/api/v1/warnings/risk/weights` | GET | 风险权重配置 |

### 智能会诊

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/diagnosis/run` | POST | 运行多 Agent 会诊 |
| `/api/v1/knowledge/docs` | GET | 知识库检索 |
| `/api/v1/cases` | GET | 病例库 |

## 模型

### 分类模型（YOLOv8n-cls）

- **类别**：棕色斑点 / 健康 / 叶斑病（稻瘟病）/ 细菌性条斑病
- **准确率**：Top-1 96.25%，Top-5 100%
- **参数量**：1.44M
- **模型大小**：2.83MB (.pt) / 5.5MB (.onnx)
- **输入尺寸**：224×224

### 检测模型（YOLOv8n）

- **类别**：15类水稻病虫害
- **模型大小**：6.0MB (.pt) / 12MB (.onnx)
- **输入尺寸**：640×640

## 环境模拟器使用

启动后端后模拟器自动运行，每5秒生成一条环境数据。

```bash
# 查看当前数据
curl http://localhost:8000/api/v1/environment/current

# 触发高温异常
curl -X POST "http://localhost:8000/api/v1/environment/simulator/anomaly?anomaly=high_temp"

# 恢复正常
curl -X POST "http://localhost:8000/api/v1/environment/simulator/anomaly?anomaly=normal"

# 设置高湿
curl -X POST "http://localhost:8000/api/v1/environment/simulator/anomaly?anomaly=high_humidity"

# 土壤过湿
curl -X POST "http://localhost:8000/api/v1/environment/simulator/anomaly?anomaly=soil_wet"
```

## 实验报告

完整实验报告：`docs/experiment_report.html`

包含：
- **鲁棒性测试**：9项干扰条件（亮度增减、高斯模糊、高斯噪声、JPEG压缩、翻转、旋转）下的准确率变化
- **消融实验**：5组对比验证各模块（视觉检测/环境监测/趋势分析/知识库）对整体性能的贡献
- **对比实验**：YOLOv8-cls vs ResNet-50 / EfficientNet-B0 / MobileNetV3 / VGG-16 的准确率、推理速度、模型大小对比
- **分类详细指标**：Precision / Recall / F1-Score

## 说明

- 比赛提交材料执行匿名要求，界面中不显示学校、团队成员等身份信息
- 更换视觉模型时须保证输出类别顺序与类别定义一致
- 模型权重文件直接存放在 `app/models/` 目录下
