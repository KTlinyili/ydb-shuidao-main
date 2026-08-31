# RiceGuard 移动端

基于 Flutter 的水稻病虫害智能检测与预警系统移动端应用。

## 功能

- **首页**：风险仪表盘 + 环境四指标 + 最新预警入口
- **识别**：图片分类 / 文字诊断 / 视频检测（三标签页）
- **监测**：实时视频流 + 检测框 + FPS/延迟 + 事件列表
- **预警**：风险列表 + 确认/关闭操作
- **设置**：语言/主题/API地址/模型版本

## 离线/在线模式

- **离线模式**：TFLite 模型本地推理，仅支持图片分类
- **在线模式**：连接 FastAPI 后端，支持全部功能

## 技术栈

- Flutter 3.35+
- Riverpod（状态管理）
- Go Router（路由）
- TFLite Flutter（离线推理）
- HTTP（在线 API 调用）
- Google Fonts（Noto Sans SC）

## 项目结构

```
mobile/
  assets/
    models/          TFLite 模型
    data/            病害知识库
    images/          图片资源
  lib/
    main.dart        入口
    app/
      router.dart    路由配置
    pages/           5个页面
    widgets/         UI组件
    services/        推理/API/知识库服务
```

## 构建

```bash
flutter pub get
flutter run
flutter build apk --release
```
