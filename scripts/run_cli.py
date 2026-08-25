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
    parser = argparse.ArgumentParser(description="水稻病虫害多智能体诊断（默认可直接运行）")
    parser.add_argument(
        "--problem_name",
        type=str,
        default="水稻病虫害默认测试",
        help="问题名称（可选）",
    )
    parser.add_argument(
        "--case_text",
        type=str,
        default="水稻叶片出现褐色病斑和枯死症状，近期高温高湿。",
        help="症状描述（可选）",
    )
    parser.add_argument("--stage", type=str, default="initial", choices=["initial", "final"], help="阶段（可选）")
    parser.add_argument("--n_rounds", type=int, default=2, help="讨论轮次（可选）")
    parser.add_argument("--image_path", type=str, default="", help="图片路径（可选）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    pipeline = DiagnosisPipeline(settings=settings)

    image_bytes: bytes | None = None
    if args.image_path:
        image_bytes = Path(args.image_path).read_bytes()

    result = pipeline.run(
        problem_name=args.problem_name,
        case_text=args.case_text,
        stage=args.stage,
        image_bytes=image_bytes,
        n_rounds=args.n_rounds,
    )
    output = {
        "run_id": result.get("run_id"),
        "knowledge_write_layer": result.get("knowledge_write_layer"),
        "final": result.get("final"),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
