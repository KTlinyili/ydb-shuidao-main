import os
import sys
import json
import numpy as np
from pathlib import Path
from ultralytics import YOLO
import cv2

MODEL_PATH = str(Path(__file__).parent.parent / "app" / "models" / "best_cls.pt")
DATA_DIR = str(Path(__file__).parent / "rice_cls" / "val")
CLASSES = ["brown_spot", "healthy", "leaf_blast", "neck_blast"]
IMG_SIZE = 224

def load_val_images():
    images = []
    labels = []
    for cls_idx, cls_name in enumerate(CLASSES):
        cls_dir = os.path.join(DATA_DIR, cls_name)
        if not os.path.isdir(cls_dir):
            print(f"Warning: {cls_dir} not found")
            continue
        for fname in os.listdir(cls_dir):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(cls_dir, fname)
                img = cv2.imread(img_path)
                if img is not None:
                    images.append((img_path, img))
                    labels.append(cls_idx)
    print(f"Loaded {len(images)} validation images")
    return images, labels

def predict_batch(model, images, class_labels):
    correct = 0
    total = len(images)
    for img_path, img in images:
        results = model.predict(img, imgsz=IMG_SIZE, verbose=False)
        pred_cls = int(results[0].probs.top1)
        true_cls = class_labels[images.index((img_path, img))]
        if pred_cls == true_cls:
            correct += 1
    acc = correct / total if total > 0 else 0
    return acc

def apply_brightness(img, factor):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hsv = hsv.astype(np.float64)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255)
    hsv = hsv.astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

def apply_gaussian_blur(img, kernel_size):
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)

def apply_motion_blur(img, angle, distance):
    M = np.zeros((distance, distance), dtype=np.float32)
    M[distance // 2, :] = 1.0
    M /= distance
    kernel = cv2.warpAffine(M, cv2.getRotationMatrix2D((distance / 2, distance / 2), angle, 1.0), (distance, distance))
    return cv2.filter2D(img, -1, kernel)

def apply_gaussian_noise(img, sigma):
    noise = np.random.normal(0, sigma, img.shape).astype(np.float64)
    noisy = np.clip(img.astype(np.float64) + noise, 0, 255).astype(np.uint8)
    return noisy

def apply_salt_pepper(img, density):
    noisy = img.copy()
    total = img.shape[0] * img.shape[1]
    num_salt = int(total * density / 2)
    num_pepper = int(total * density / 2)
    for _ in range(num_salt):
        x, y = np.random.randint(0, img.shape[1]), np.random.randint(0, img.shape[0])
        noisy[y, x] = [255, 255, 255]
    for _ in range(num_pepper):
        x, y = np.random.randint(0, img.shape[1]), np.random.randint(0, img.shape[0])
        noisy[y, x] = [0, 0, 0]
    return noisy

def apply_rotation(img, angle):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h))

def apply_scale(img, scale_factor):
    h, w = img.shape[:2]
    resized = cv2.resize(img, None, fx=scale_factor, fy=scale_factor)
    rh, rw = resized.shape[:2]
    if rw > w and rh > h:
        start_x = (rw - w) // 2
        start_y = (rh - h) // 2
        return resized[start_y:start_y + h, start_x:start_x + w]
    else:
        result = np.zeros((h, w, 3), dtype=np.uint8)
        start_x = (w - rw) // 2
        start_y = (h - rh) // 2
        result[start_y:start_y + rh, start_x:start_x + rw] = resized
        return result

def apply_flip(img):
    return cv2.flip(img, 1)

def apply_center_crop(img, ratio):
    h, w = img.shape[:2]
    ch, cw = int(h * ratio), int(w * ratio)
    start_y = (h - ch) // 2
    start_x = (w - cw) // 2
    cropped = img[start_y:start_y + ch, start_x:start_x + cw]
    return cv2.resize(cropped, (w, h))

def apply_jpeg_compression(img, quality):
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, encoded = cv2.imencode('.jpg', img, encode_param)
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR)

def apply_resize(img, target_size):
    return cv2.resize(img, (target_size, target_size))

def apply_fog(img, intensity):
    fog = np.ones_like(img, dtype=np.float64) * 255 * intensity
    result = img.astype(np.float64) * (1 - intensity) + fog
    return np.clip(result, 0, 255).astype(np.uint8)

def apply_rain(img, intensity):
    result = img.copy().astype(np.float64)
    h, w = img.shape[:2]
    num_drops = int(h * w * intensity / 10000)
    for _ in range(num_drops):
        x = np.random.randint(0, w)
        y = np.random.randint(0, h - 10)
        length = np.random.randint(5, 15)
        cv2.line(result, (x, y), (x + 2, y + length), (180, 180, 180), 1)
    return np.clip(result, 0, 255).astype(np.uint8)

def run_test(model, images, labels, name, transform_func, *args):
    print(f"\n--- {name} ---")
    transformed = []
    for img_path, img in images:
        t_img = transform_func(img, *args) if args else transform_func(img)
        transformed.append((img_path, t_img))
    correct = 0
    for i, (img_path, t_img) in enumerate(transformed):
        results = model.predict(t_img, imgsz=IMG_SIZE, verbose=False)
        pred_cls = int(results[0].probs.top1)
        if pred_cls == labels[i]:
            correct += 1
    acc = correct / len(transformed) if transformed else 0
    print(f"  Top-1: {acc:.4f} ({correct}/{len(transformed)})")
    return acc

def main():
    print("=" * 60)
    print("RiceGuard 鲁棒性测试")
    print("=" * 60)

    model = YOLO(MODEL_PATH)
    print(f"Model loaded: {MODEL_PATH}")

    images, labels = load_val_images()
    if len(images) == 0:
        print("No validation images found!")
        return

    np.random.seed(42)
    results = {}

    print("\n=== 基线测试 ===")
    baseline = run_test(model, images, labels, "Baseline (No Distortion)", lambda img: img)
    results["baseline"] = baseline

    print("\n=== 1. 光照干扰 ===")
    results["light_low_30"] = run_test(model, images, labels, "低光照 -30%", apply_brightness, 0.7)
    results["light_low_50"] = run_test(model, images, labels, "低光照 -50%", apply_brightness, 0.5)
    results["light_low_70"] = run_test(model, images, labels, "低光照 -70%", apply_brightness, 0.3)
    results["light_high_30"] = run_test(model, images, labels, "过曝光 +30%", apply_brightness, 1.3)
    results["light_high_50"] = run_test(model, images, labels, "过曝光 +50%", apply_brightness, 1.5)

    print("\n=== 2. 模糊干扰 ===")
    results["blur_k3"] = run_test(model, images, labels, "高斯模糊 k=3", apply_gaussian_blur, 3)
    results["blur_k5"] = run_test(model, images, labels, "高斯模糊 k=5", apply_gaussian_blur, 5)
    results["blur_k7"] = run_test(model, images, labels, "高斯模糊 k=7", apply_gaussian_blur, 7)
    results["motion_0_10"] = run_test(model, images, labels, "运动模糊 0° 10px", apply_motion_blur, 0, 10)
    results["motion_45_15"] = run_test(model, images, labels, "运动模糊 45° 15px", apply_motion_blur, 45, 15)

    print("\n=== 3. 噪声干扰 ===")
    results["gauss_s10"] = run_test(model, images, labels, "高斯噪声 σ=10", apply_gaussian_noise, 10)
    results["gauss_s25"] = run_test(model, images, labels, "高斯噪声 σ=25", apply_gaussian_noise, 25)
    results["gauss_s50"] = run_test(model, images, labels, "高斯噪声 σ=50", apply_gaussian_noise, 50)
    results["sp_5"] = run_test(model, images, labels, "椒盐噪声 5%", apply_salt_pepper, 0.05)
    results["sp_10"] = run_test(model, images, labels, "椒盐噪声 10%", apply_salt_pepper, 0.10)

    print("\n=== 4. 几何变换 ===")
    results["rot_15"] = run_test(model, images, labels, "旋转 ±15°", apply_rotation, 15)
    results["rot_30"] = run_test(model, images, labels, "旋转 ±30°", apply_rotation, 30)
    results["scale_075"] = run_test(model, images, labels, "缩放 0.75x", apply_scale, 0.75)
    results["scale_15"] = run_test(model, images, labels, "缩放 1.5x", apply_scale, 1.5)
    results["flip_h"] = run_test(model, images, labels, "水平翻转", apply_flip)
    results["crop_80"] = run_test(model, images, labels, "中心裁剪 80%", apply_center_crop, 0.8)

    print("\n=== 5. 压缩干扰 ===")
    results["jpeg_50"] = run_test(model, images, labels, "JPEG quality=50", apply_jpeg_compression, 50)
    results["jpeg_20"] = run_test(model, images, labels, "JPEG quality=20", apply_jpeg_compression, 20)
    results["resize_112"] = run_test(model, images, labels, "分辨率 112x112", apply_resize, 112)
    results["resize_64"] = run_test(model, images, labels, "分辨率 64x64", apply_resize, 64)

    print("\n=== 6. 天气仿真 ===")
    results["fog_light"] = run_test(model, images, labels, "雾天 轻度", apply_fog, 0.2)
    results["fog_heavy"] = run_test(model, images, labels, "雾天 重度", apply_fog, 0.5)
    results["rain_light"] = run_test(model, images, labels, "雨天 轻度", apply_rain, 1.0)
    results["rain_heavy"] = run_test(model, images, labels, "雨天 重度", apply_rain, 3.0)

    print("\n" + "=" * 60)
    print("鲁棒性测试完成！结果汇总：")
    print("=" * 60)
    print(f"\n基线准确率: {results['baseline']:.4f}")
    print("\n各干扰项准确率及相对下降：")
    for key, val in sorted(results.items()):
        if key == "baseline":
            continue
        drop = results["baseline"] - val
        print(f"  {key:20s}: {val:.4f}  (下降 {drop:.4f})")

    output_path = str(Path(__file__).parent / "robust_test_results.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存到: {output_path}")

    # 生成混淆矩阵
    print("\n=== 混淆矩阵 ===")
    matrix = np.zeros((len(CLASSES), len(CLASSES)), dtype=int)
    for i, (img_path, img) in enumerate(images):
        pred = model.predict(img, imgsz=IMG_SIZE, verbose=False)
        pred_cls = int(pred[0].probs.top1)
        true_cls = labels[i]
        matrix[true_cls][pred_cls] += 1

    print("\n混淆矩阵 (行=真实, 列=预测):")
    label = "真实/预测"
    header = f"{label:15s}"
    for cls in CLASSES:
        header += f"{cls:15s}"
    header += f"{'召回率':10s}"
    print(header)

    for i, cls in enumerate(CLASSES):
        row = f"{cls:15s}"
        row_total = matrix[i].sum()
        for j in range(len(CLASSES)):
            row += f"{matrix[i][j]:15d}"
        recall = matrix[i][i] / row_total if row_total > 0 else 0
        row += f"{recall:.4f}      "
        print(row)

    print()
    precision_header = f"{'精确率':15s}"
    for j in range(len(CLASSES)):
        col_total = matrix[:, j].sum()
        precision = matrix[j][j] / col_total if col_total > 0 else 0
        precision_header += f"{precision:15.4f}"
    print(precision_header)

    overall_acc = np.trace(matrix) / matrix.sum()
    print(f"\n总体准确率: {overall_acc:.4f}")

    cm_data = {
        "classes": CLASSES,
        "matrix": matrix.tolist(),
        "overall_accuracy": overall_acc,
    }
    cm_path = str(Path(__file__).parent / "confusion_matrix_data.json")
    with open(cm_path, 'w', encoding='utf-8') as f:
        json.dump(cm_data, f, indent=2, ensure_ascii=False)
    print(f"混淆矩阵数据已保存到: {cm_path}")

if __name__ == "__main__":
    main()
