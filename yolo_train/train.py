"""
YOLOv8n 水稻病虫害检测训练脚本
在百度 AI Studio 的 GPU Notebook（VSCode）里运行

步骤：
1. pip install ultralytics
2. 把数据集文件夹上传到 AI Studio
3. 修改下面的 DATA_PATH 为你的数据集实际路径
4. python train.py
"""

import os
from ultralytics import YOLO

# ===== 修改这里：改成你的数据集实际路径 =====
DATA_PATH = "./data.yaml"  # data.yaml 文件路径
# ==========================================


def main():
    # 1. 加载预训练模型（YOLOv8n 最小最快，适合边缘端）
    print("正在加载 YOLOv8n 预训练模型...")
    model = YOLO("yolov8n.pt")

    # 2. 训练
    print("开始训练...")
    results = model.train(
        data=DATA_PATH,
        epochs=100,          # 训练轮数
        imgsz=640,           # 图片尺寸
        batch=4,             # 批大小，CPU 用小一点防止内存爆
        device='cpu',       # 用 CPU（免费）
        workers=2,           # 数据加载线程
        project="runs",     # 输出目录
        name="rice_disease", # 实验名
        patience=20,        # 20轮没提升就早停
        save=True,          # 保存模型
        plots=True,          # 画训练曲线
    )

    # 3. 验证模型效果
    print("\n=== 验证结果 ===")
    metrics = model.val()
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")

    # 4. 导出 ONNX 模型（给 RK3588 用）
    print("\n=== 导出 ONNX 模型 ===")
    onnx_path = model.export(format="onnx", imgsz=640, simplify=True)
    print(f"ONNX 模型路径: {onnx_path}")
    print("下载 best.pt 和 best.onnx 到本地，后面接入后端用")


if __name__ == "__main__":
    main()
