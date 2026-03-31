from __future__ import annotations

import sys
from pathlib import Path
import re

# 讓 exe 能正確抓到同資料夾
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from ig_9_16_collect import run_pipeline


def month_sort_key(folder: Path):
    match = re.fullmatch(r"(\d{4})_(\d{1,2})", folder.name)
    if not match:
        return (-1, -1)
    return (int(match.group(1)), int(match.group(2)))


def find_latest_month_folder(base_dir: Path) -> Path:
    candidates = [
        p for p in base_dir.iterdir()
        if p.is_dir() and re.fullmatch(r"\d{4}_\d{1,2}", p.name)
    ]

    if not candidates:
        raise FileNotFoundError(f"No month folders found under: {base_dir}")

    return max(candidates, key=month_sort_key)


def main():
    print("START")

    latest_month_dir = find_latest_month_folder(BASE_DIR)
    input_dir = latest_month_dir / "total"
    output_file = latest_month_dir / "限動.png"

    print("BASE_DIR:", BASE_DIR)
    print("Latest:", latest_month_dir)
    print("Input:", input_dir)
    print("Output:", output_file)

    run_pipeline(
        input_dir=input_dir,
        output_path=output_file,
        width=1080,
        height=1920,
        margin=0,
        gap=0,
        bg="#000000",
        fallback_crop_ratio=0.17,
        cols=4,
        rows=7,
        debug_divider=False,
    )

    print("DONE")


if __name__ == "__main__":
    main()