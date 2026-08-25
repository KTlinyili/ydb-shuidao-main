from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.pipeline.diagnosis_pipeline import DiagnosisPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Qwen3-VL + DINOv3 image probe on one image")
    parser.add_argument("--image_path", type=str, required=True, help="Path to an input image")
    parser.add_argument("--case_text", type=str, default="", help="Optional case text")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    pipeline = DiagnosisPipeline(settings=settings)
    result = pipeline.inspect_image(
        image_bytes=Path(args.image_path).read_bytes(),
        case_text=args.case_text,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
