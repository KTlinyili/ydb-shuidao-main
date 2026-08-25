from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_MODULES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn[standard]",
    "jinja2": "Jinja2",
    "multipart": "python-multipart",
}


def _ensure_runtime_deps() -> None:
    missing: list[str] = []
    for module_name, package_name in REQUIRED_MODULES.items():
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            missing.append(package_name)
    if not missing:
        return

    unique_packages = []
    for package_name in missing:
        if package_name not in unique_packages:
            unique_packages.append(package_name)

    packages = " ".join(unique_packages)
    raise SystemExit(
        "Missing runtime dependencies. Install them first with:\n"
        f"python -m pip install -r requirements.txt {packages}"
    )


def main() -> None:
    _ensure_runtime_deps()

    from app.core.config import get_settings
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
