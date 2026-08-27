# YOLOv8 训练 - AI Studio 操作指南

## 准备工作

### 1. 注册 AI Studio
- 打开 https://aistudio.baidu.com
- 用百度账号登录（没有就注册一个）

### 2. 创建项目
1. 点顶部「创建项目」
2. 项目名随便写，比如「水稻病虫害YOLO训练」
3. 框架选「PaddlePaddle」或「Python」都行
4. 环境选「GPU」（免费 V100，每天有额度）
5. 点创建

### 3. 上传文件
在 Notebook 里上传以下文件：
- `data.yaml`（数据集配置）
- `train.py`（训练脚本）
- 你的数据集（打包成 zip 上传，在 Notebook 里解压）

## 数据集格式要求

YOLO 格式数据集目录结构：
```
data/
├── images/
│   ├── train/          # 训练图片
│   │   ├── 001.jpg
│   │   ├── 002.jpg
│   │   └── ...
│   └── val/            # 验证图片
│       ├── 101.jpg
│       └── ...
└── labels/
    ├── train/          # 训练标注（和图片同名）
    │   ├── 001.txt     # 每行一个目标：class x_center y_center width height
    │   ├── 002.txt
    │   └── ...
    └── val/            # 验证标注
        ├── 101.txt
        └── ...
```

标注文件格式（每个 .txt 一行一个目标）：
```
0 0.5 0.4 0.3 0.2
2 0.2 0.6 0.1 0.15
```
格式：`类别编号 x中心 y中心 宽 高`（都是 0~1 的比例值）

## 训练步骤

### 1. 安装 ultralytics
在 Notebook 第一个 cell 运行：
```python
!pip install ultralytics -q
```

### 2. 修改 data.yaml 路径
如果你的数据集不在 `/root/data`，修改 `data.yaml` 里的 train 和 val 路径：
```yaml
train: 你的实际路径/images/train
val: 你的实际路径/images/val
```

### 3. 开始训练
```python
!python train.py
```

或者直接在 Notebook cell 里运行 train.py 的代码。

### 4. 训练时间参考
- 数据集 500 张：约 30-60 分钟
- 数据集 2000 张：约 1-2 小时
- 数据集 5000 张：约 2-4 小时

### 5. 查看结果
训练完后在 `runs/rice_disease/` 目录下：
- `weights/best.pt` — 最好的模型（下载这个）
- `weights/last.pt` — 最后一轮的模型
- `results.png` — 训练曲线
- `confusion_matrix.png` — 混淆矩阵

### 6. 下载模型
- 下载 `best.pt`（PyTorch 格式，给后端推理用）
- 下载 `best.onnx`（ONNX 格式，给 RK3588 转 RKNN 用）

## 常见问题

| 问题 | 解决 |
|------|------|
| 显存不够 | 把 train.py 里 batch 改成 8 或 4 |
| 数据集路径找不到 | 用 `!ls /root/` 看看实际路径 |
| 某个类别没有数据 | data.yaml 里 nc 改小，names 删掉那个类 |
| 训练太慢 | imgsz 改 416，epochs 改 50 |
| mAP 太低 | 数据太少或标注质量差，多找点数据 |

## 训练完之后

1. 把 `best.pt` 下载到本地
2. 告诉我，我帮你接入后端推理
3. 把 `best.onnx` 留着，等开发板到了转 RKNN
