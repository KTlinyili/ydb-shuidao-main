from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any
import sys

DEFAULT_CLASSIFIER_CLASS_NAMES = (
    "angular_leafspot",
    "leaf_spot",
    "gray_mold",
    "powdery_mildew_leaf",
    "leaf_spot",
    "leaf",
    "leaf_spot",
    "leaf",
    "leaf",
    "healthy",
)


def _normalize_label(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _disease_slug_for_match(name: str) -> str:
    """对齐 PlantVillage 式「gray_mold」与分割 classes.txt 里「gray_mold」等同义病名。"""
    raw = str(name).strip()
    if "___" in raw:
        raw = raw.split("___", 1)[-1]
    return _normalize_label(raw)


def _segmentation_name_matches_classifier(seg_class_name: str, classifier_class_name: str) -> bool:
    s = _disease_slug_for_match(seg_class_name)
    c = _disease_slug_for_match(classifier_class_name)
    if not s or not c:
        return False
    if s == c:
        return True
    return len(s) >= 4 and (s in c or c in s)


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _strip_dataparallel_prefix(state: dict[str, Any]) -> dict[str, Any]:
    keys = [k for k in state if isinstance(k, str)]
    if keys and all(k.startswith("module.") for k in keys):
        return {str(k)[len("module.") :]: v for k, v in state.items()}
    return state


@dataclass(frozen=True)
class DinoV3Paths:
    repo_dir: Path
    backbone_weights: Path
    classifier_head_weights: Path
    segmentation_head_weights: Path
    classes_file: Path
    classifier_classes: tuple[str, ...] = ()
    image_size: int = 256
    segmentation_threshold: float = 0.5
    prefer_cuda: bool = True


class LocalDinoV3Diagnoser:
    def __init__(self, paths: DinoV3Paths):
        self.paths = paths
        self._lock = Lock()
        self._loaded = False
        self._torch: Any | None = None
        self._nn: Any | None = None
        self._F: Any | None = None
        self._transforms: Any | None = None
        self._Image: Any | None = None
        self._device: Any | None = None
        self._backbone: Any | None = None
        self._classifier_head: Any | None = None
        self._seg_head: Any | None = None
        self._layer_indices: list[int] = []
        self._segmentation_classes: list[str] = []
        self._classifier_classes: list[str] = []
        self._leaf_index: int | None = None
        self._healthy_index: int | None = None
        self._disease_indices: list[int] = []

    @classmethod
    def from_project_root(
        cls,
        project_root: Path,
        *,
        image_size: int = 256,
        segmentation_threshold: float = 0.5,
        prefer_cuda: bool = True,
    ) -> LocalDinoV3Diagnoser:
        model_dir = project_root / "model"
        return cls(
            DinoV3Paths(
                repo_dir=model_dir / "dinov3",
                backbone_weights=model_dir / "dinov3_vitl16_pretrain.pth",
                classifier_head_weights=model_dir / "best_classifier_head.pth",
                segmentation_head_weights=model_dir / "best_segmentation_head.pth",
                classes_file=model_dir / "classes.txt",
                image_size=image_size,
                segmentation_threshold=segmentation_threshold,
                prefer_cuda=prefer_cuda,
            )
        )

    def is_available(self) -> bool:
        required = [
            self.paths.repo_dir,
            self.paths.backbone_weights,
            self.paths.classifier_head_weights,
            self.paths.segmentation_head_weights,
            self.paths.classes_file,
        ]
        return all(path.exists() for path in required)

    def analyze_image_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        if not image_bytes:
            raise ValueError("图像字节内容为空")
        self._ensure_loaded()
        image = self._Image.open(BytesIO(image_bytes)).convert("RGB")
        return self._analyze_pil_image(image)

    def analyze_image_path(self, image_path: str | Path) -> dict[str, Any]:
        self._ensure_loaded()
        image = self._Image.open(image_path).convert("RGB")
        return self._analyze_pil_image(image)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._load_runtime_dependencies()
            self._build_models()
            self._loaded = True

    def _load_runtime_dependencies(self) -> None:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        import torchvision.transforms as transforms
        from PIL import Image

        self._torch = torch
        self._nn = nn
        self._F = F
        self._transforms = transforms
        self._Image = Image

    def _ensure_repo_on_path(self) -> None:
        repo_dir = str(self.paths.repo_dir.resolve())
        if repo_dir not in sys.path:
            sys.path.insert(0, repo_dir)

    def _load_class_names(self) -> list[str]:
        names = [
            line.strip()
            for line in self.paths.classes_file.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
        if not names:
            raise RuntimeError(f"在 {self.paths.classes_file} 中未找到类别名称")
        return names

    def _resolve_classifier_class_names(self, segmentation_names: list[str], classifier_dim: int) -> list[str]:
        explicit = [str(name).strip() for name in self.paths.classifier_classes if str(name).strip()]
        if explicit:
            if len(explicit) != classifier_dim:
                raise RuntimeError(
                    "配置的分类头类别数量与分类头输出维度不一致："
                    f"{len(explicit)} != {classifier_dim}"
                )
            return explicit

        if classifier_dim == len(DEFAULT_CLASSIFIER_CLASS_NAMES):
            return list(DEFAULT_CLASSIFIER_CLASS_NAMES)

        if len(segmentation_names) == classifier_dim:
            return segmentation_names

        leaf_filtered = [name for name in segmentation_names if _normalize_label(name) != "leaf"]
        if len(leaf_filtered) >= classifier_dim:
            return leaf_filtered[:classifier_dim]

        padded = list(segmentation_names[:classifier_dim])
        while len(padded) < classifier_dim:
            padded.append(f"class_{len(padded)}")
        return padded

    def _build_models(self) -> None:
        self._ensure_repo_on_path()
        from dinov3.models.vision_transformer import DinoVisionTransformer

        torch = self._torch
        nn = self._nn
        F = self._F

        class LinearSegmentationHead(nn.Module):
            def __init__(self, in_channels_list: list[int], num_classes: int, dropout: float = 0.1):
                super().__init__()
                total_channels = sum(in_channels_list)
                self.bn = nn.BatchNorm2d(total_channels)
                self.dropout = nn.Dropout2d(dropout)
                self.conv = nn.Conv2d(total_channels, num_classes, kernel_size=1)
                nn.init.normal_(self.conv.weight, mean=0.0, std=0.01)
                nn.init.constant_(self.conv.bias, 0.0)

            def forward(self, features_list: list[Any]) -> Any:
                target_size = features_list[0].shape[2:]
                upsampled = []
                for feat in features_list:
                    if feat.shape[2:] != target_size:
                        feat = F.interpolate(feat, size=target_size, mode="bilinear", align_corners=False)
                    upsampled.append(feat)
                x = torch.cat(upsampled, dim=1)
                x = self.bn(x)
                x = self.dropout(x)
                return self.conv(x)

        class EnhancedSegmentationHead(nn.Module):
            """与 train_segmentation_head / 独立推理脚本中的增强分割头结构一致。"""

            def __init__(
                self,
                in_channels_list: list[int],
                num_classes: int,
                hidden_dim: int = 256,
                dropout: float = 0.1,
                use_skip: bool = True,
            ):
                super().__init__()
                self.total_in = sum(in_channels_list)
                self.num_classes = num_classes
                self.use_skip = use_skip

                self.reduce = nn.Sequential(
                    nn.Conv2d(self.total_in, hidden_dim, kernel_size=1, bias=False),
                    nn.BatchNorm2d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout2d(dropout),
                )
                self.refine = nn.Sequential(
                    nn.Conv2d(hidden_dim, hidden_dim, kernel_size=3, padding=1, bias=False),
                    nn.BatchNorm2d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout2d(dropout * 0.5),
                    nn.Conv2d(hidden_dim, hidden_dim, kernel_size=3, padding=1, bias=False),
                    nn.BatchNorm2d(hidden_dim),
                    nn.ReLU(inplace=True),
                )
                self.out = nn.Conv2d(hidden_dim, num_classes, kernel_size=1)
                if self.use_skip:
                    self.skip_weight = nn.Parameter(torch.ones(1) * 0.3)
                    self.skip_reduce = nn.Sequential(
                        nn.Conv2d(self.total_in, hidden_dim, kernel_size=1, bias=False),
                        nn.BatchNorm2d(hidden_dim),
                        nn.ReLU(inplace=True),
                    )
                nn.init.normal_(self.out.weight, mean=0.0, std=0.01)
                nn.init.constant_(self.out.bias, 0.0)

            def forward(self, features_list: list[Any]) -> Any:
                target_size = features_list[0].shape[2:]
                upsampled = []
                for feat in features_list:
                    if feat.shape[2:] != target_size:
                        feat = F.interpolate(feat, size=target_size, mode="bilinear", align_corners=False)
                    upsampled.append(feat)
                x = torch.cat(upsampled, dim=1)
                x = self.reduce(x)
                x = self.refine(x)
                if self.use_skip:
                    skip_feats = []
                    for feat in features_list:
                        skip = F.interpolate(feat, size=target_size, mode="bilinear", align_corners=False)
                        skip_feats.append(skip)
                    skip_cat = torch.cat(skip_feats, dim=1)
                    x = x + self.skip_weight * self.skip_reduce(skip_cat)
                return self.out(x)

        device = torch.device("cuda" if self.paths.prefer_cuda and torch.cuda.is_available() else "cpu")
        backbone = DinoVisionTransformer(
            img_size=224,
            patch_size=16,
            in_chans=3,
            pos_embed_rope_base=100,
            pos_embed_rope_normalize_coords="separate",
            pos_embed_rope_rescale_coords=2,
            pos_embed_rope_dtype="fp32",
            embed_dim=1024,
            depth=24,
            num_heads=16,
            ffn_ratio=4,
            qkv_bias=True,
            drop_path_rate=0.0,
            layerscale_init=1.0e-05,
            norm_layer="layernormbf16",
            ffn_layer="mlp",
            ffn_bias=True,
            proj_bias=True,
            n_storage_tokens=4,
            mask_k_bias=True,
            untie_global_and_local_cls_norm=False,
        )
        backbone_state = torch.load(self.paths.backbone_weights, map_location="cpu")
        backbone.load_state_dict(backbone_state, strict=True)

        classifier_state = torch.load(self.paths.classifier_head_weights, map_location="cpu")
        if not isinstance(classifier_state, dict) or "weight" not in classifier_state:
            raise RuntimeError("分类头权重文件格式不符合预期")
        classifier_dim = int(classifier_state["weight"].shape[0])
        classifier_head = nn.Linear(backbone.embed_dim, classifier_dim)
        classifier_head.load_state_dict(classifier_state, strict=True)

        raw_seg = torch.load(self.paths.segmentation_head_weights, map_location="cpu")
        segmentation_state: dict[str, Any]
        if isinstance(raw_seg, dict) and "state_dict" in raw_seg and isinstance(raw_seg["state_dict"], dict):
            segmentation_state = raw_seg["state_dict"]
        elif isinstance(raw_seg, dict):
            segmentation_state = raw_seg
        else:
            raise RuntimeError("分割头权重文件格式不符合预期：应为 state_dict 或包含 state_dict 的字典")

        segmentation_state = _strip_dataparallel_prefix(segmentation_state)

        layer_indices = [4, 11, 17, 23]
        in_ch = [backbone.embed_dim] * len(layer_indices)

        if "conv.weight" in segmentation_state:
            segmentation_dim = int(segmentation_state["conv.weight"].shape[0])
            seg_head = LinearSegmentationHead(
                in_channels_list=in_ch,
                num_classes=segmentation_dim,
                dropout=0.1,
            )
            seg_head.load_state_dict(segmentation_state, strict=True)
        elif "out.weight" in segmentation_state:
            segmentation_dim = int(segmentation_state["out.weight"].shape[0])
            use_skip = "skip_weight" in segmentation_state or any(
                str(k).startswith("skip_reduce") for k in segmentation_state
            )
            seg_head = EnhancedSegmentationHead(
                in_channels_list=in_ch,
                num_classes=segmentation_dim,
                hidden_dim=256,
                dropout=0.1,
                use_skip=use_skip,
            )
            seg_head.load_state_dict(segmentation_state, strict=True)
        else:
            raise RuntimeError(
                "分割头权重文件格式不符合预期：未找到 conv.weight（旧线性头）或 out.weight（增强头），"
                "请确认权重与 train_segmentation_head 导出一致。"
            )

        segmentation_names = self._load_class_names()
        if len(segmentation_names) < segmentation_dim:
            segmentation_names.extend(
                [f"class_{idx}" for idx in range(len(segmentation_names), segmentation_dim)]
            )
        segmentation_names = segmentation_names[:segmentation_dim]
        classifier_names = self._resolve_classifier_class_names(segmentation_names, classifier_dim)

        leaf_index = next(
            (idx for idx, name in enumerate(segmentation_names) if _normalize_label(name) == "leaf"),
            None,
        )
        healthy_index = next(
            (idx for idx, name in enumerate(segmentation_names) if _normalize_label(name) == "healthy"),
            None,
        )
        disease_indices = [
            idx
            for idx, name in enumerate(segmentation_names)
            if idx not in {leaf_index, healthy_index} and _normalize_label(name) != "leaf"
        ]

        backbone.to(device).eval()
        classifier_head.to(device).eval()
        seg_head.to(device).eval()

        self._device = device
        self._backbone = backbone
        self._classifier_head = classifier_head
        self._seg_head = seg_head
        self._layer_indices = layer_indices
        self._segmentation_classes = segmentation_names
        self._classifier_classes = classifier_names
        self._leaf_index = leaf_index
        self._healthy_index = healthy_index
        self._disease_indices = disease_indices

    def _preprocess(self, image: Any) -> tuple[Any, tuple[int, int]]:
        transform = self._transforms.Compose(
            [
                self._transforms.Resize((self.paths.image_size, self.paths.image_size)),
                self._transforms.ToTensor(),
                self._transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
        width, height = image.size
        tensor = transform(image).unsqueeze(0)
        return tensor, (height, width)

    def _resolve_leaf_mask(self, segmentation_mask: Any) -> tuple[Any, str]:
        """叶片区域 = 分割头 leaf 通道（与独立推理脚本里 leaf_pixels = pred_mask[0].sum() 一致）。

        当 classes.txt 中**存在** leaf 类别时，**即使该通道全为 0** 也仍用该通道，而不用
        disease∪healthy 作分母——后者会把「叶片像素」撑成几乎整图，导致病斑/叶片占比严重失真。
        仅当配置里根本没有 leaf 通道时，才退回用 disease∪healthy 近似叶片区域。
        """
        torch = self._torch
        if self._leaf_index is not None and self._leaf_index < segmentation_mask.shape[0]:
            return segmentation_mask[self._leaf_index], "leaf_channel"
        if self._disease_indices:
            disease_union = segmentation_mask[self._disease_indices].any(dim=0)
        else:
            disease_union = torch.zeros_like(segmentation_mask[0])
        healthy_mask = (
            segmentation_mask[self._healthy_index]
            if self._healthy_index is not None and self._healthy_index < segmentation_mask.shape[0]
            else torch.zeros_like(disease_union)
        )
        fallback_mask = disease_union | healthy_mask
        return fallback_mask, "union_fallback"

    def _analyze_pil_image(self, image: Any) -> dict[str, Any]:
        torch = self._torch
        F = self._F
        tensor, original_size = self._preprocess(image)
        height, width = original_size
        tensor = tensor.to(self._device)

        with torch.inference_mode():
            feature_dict = self._backbone.forward_features(tensor)
            cls_token = feature_dict["x_norm_clstoken"]
            logits = self._classifier_head(cls_token)
            probs = torch.softmax(logits, dim=1)[0]

            backbone_features = list(
                self._backbone.get_intermediate_layers(
                    tensor,
                    n=self._layer_indices,
                    reshape=True,
                    return_class_token=False,
                )
            )
            seg_logits = self._seg_head(backbone_features)
            seg_logits = F.interpolate(seg_logits, size=(height, width), mode="bilinear", align_corners=False)
            seg_probs = torch.sigmoid(seg_logits)[0]
            seg_mask = (seg_probs >= float(self.paths.segmentation_threshold)).to(torch.bool)

        pred_index = int(torch.argmax(probs).item())
        predicted_class = self._classifier_classes[pred_index]
        predicted_confidence = float(probs[pred_index].item())
        top_k = min(3, len(self._classifier_classes))
        top_scores, top_indices = torch.topk(probs, k=top_k)

        leaf_mask, leaf_area_source = self._resolve_leaf_mask(seg_mask)
        leaf_pixels = int(leaf_mask.sum().item())
        # 病斑面积占比：病害并集 / (病害并集 + 叶片通道像素)。病斑视为叶面组成部分，分母不再单用叶片通道。
        if self._disease_indices:
            disease_any = seg_mask[self._disease_indices].any(dim=0)
            diseased_pixels = int((disease_any & leaf_mask).sum().item())
        else:
            diseased_pixels = 0
        denom_pixels = diseased_pixels + leaf_pixels
        damage_ratio = float(diseased_pixels / denom_pixels) if denom_pixels > 0 else 0.0
        healthy_pixels = (
            int((seg_mask[self._healthy_index] & leaf_mask).sum().item())
            if self._healthy_index is not None and self._healthy_index < seg_mask.shape[0]
            else 0
        )

        disease_area_details: list[dict[str, Any]] = []
        dominant_segmentation_class = ""
        dominant_segmentation_ratio = 0.0
        for idx in self._disease_indices:
            # 单类占比：与总体一致，分母为 病害并集 + 叶片通道（多标签下各类可重叠）
            class_mask = seg_mask[idx] & leaf_mask
            pixels = int(class_mask.sum().item())
            if pixels == 0:
                ratio_of_leaf = 0.0
                mean_probability = float(seg_probs[idx].max().item())
            else:
                ratio_of_leaf = float(pixels / denom_pixels) if denom_pixels > 0 else 0.0
                mean_probability = float(seg_probs[idx][class_mask].mean().item())
            disease_area_details.append(
                {
                    "class_id": idx,
                    "class_name": self._segmentation_classes[idx],
                    "pixels": pixels,
                    "ratio_of_leaf": ratio_of_leaf,
                    "mean_probability": mean_probability,
                }
            )
            if ratio_of_leaf > dominant_segmentation_ratio:
                dominant_segmentation_class = self._segmentation_classes[idx]
                dominant_segmentation_ratio = ratio_of_leaf

        classifier_match_ratio = 0.0
        for item in disease_area_details:
            if _segmentation_name_matches_classifier(str(item["class_name"]), predicted_class):
                classifier_match_ratio = float(item["ratio_of_leaf"])
                break

        return {
            "model_name": "dinov3_vitl16_local_classifier_and_segmentation",
            "device": str(self._device),
            "image_size": {"width": width, "height": height},
            "predicted_class_id": pred_index,
            "predicted_class": predicted_class,
            "confidence": predicted_confidence,
            "top_predictions": [
                {
                    "class_id": int(class_idx.item()),
                    "class_name": self._classifier_classes[int(class_idx.item())],
                    "confidence": float(class_score.item()),
                }
                for class_score, class_idx in zip(top_scores, top_indices)
            ],
            "segmentation_threshold": float(self.paths.segmentation_threshold),
            "leaf_area_source": leaf_area_source,
            "leaf_pixels": leaf_pixels,
            "healthy_pixels": healthy_pixels,
            "diseased_pixels": diseased_pixels,
            "damaged_area_ratio_of_leaf": _clamp_unit(damage_ratio),
            "predicted_class_damage_ratio_of_leaf": _clamp_unit(classifier_match_ratio),
            "dominant_segmentation_class": dominant_segmentation_class,
            "dominant_segmentation_ratio_of_leaf": _clamp_unit(dominant_segmentation_ratio),
            "disease_area_details": disease_area_details,
            "segmentation_classes": list(self._segmentation_classes),
            "classifier_classes": list(self._classifier_classes),
        }
