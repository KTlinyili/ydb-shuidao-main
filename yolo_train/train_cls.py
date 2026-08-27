"""
水稻病虫害分类模型训练脚本（YOLOv8n-cls）
官方4类数据：健康 / 叶斑病 / 棕色斑点 / 细菌性条斑病
"""
import os
from ultralytics import YOLO

# 1. 加载预训练分类模型
print("加载 YOLOv8n-cls 预训练模型...")
model = YOLO("yolov8n-cls.pt")

# 2. 训练
print("\n开始训练...")
results = model.train(
    data="./rice_cls",      # 数据集路径（当前目录下的 rice_cls/）
    epochs=50,              # 训练轮数
    imgsz=224,              # 分类模型输入尺寸
    batch=16,               # 批次大小
    device='cpu',           # CPU训练（AI Studio无GPU时用）
    workers=2,              # 数据加载线程数
    project="runs_cls",     # 输出目录
    name="rice_cls",        # 实验名
    patience=15,            # 早停耐心值
    save=True,              # 保存模型
    plots=True,             # 保存训练曲线
)

# 3. 验证
print("\n验证模型...")
metrics = model.val()
print(f"Top-1 准确率: {metrics.top1:.4f}")
print(f"Top-5 准确率: {metrics.top5:.4f}")

# 4. 导出 ONNX
print("\n导出 ONNX 模型...")
onnx_path = model.export(format="onnx", imgsz=224, simplify=True)
print(f"ONNX 模型已保存: {onnx_path}")

print("\n=== 训练完成 ===")
print("下载 best.pt 和 best.onnx 到本地，接入后端用")
