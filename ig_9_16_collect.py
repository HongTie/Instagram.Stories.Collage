from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from PIL import Image, ImageColor

VALID_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default="C:/Users/hongtie/Desktop/幣安/2026_03/total",
        help="Folder containing single-card images",
    )
    parser.add_argument(
        "--output",
        default="C:/Users/hongtie/Desktop/幣安/2026_03/限動.png",
        help="Base output collage image path",
    )
    parser.add_argument("--width", type=int, default=1080, help="Canvas width")
    parser.add_argument("--height", type=int, default=1920, help="Canvas height")
    parser.add_argument("--margin", type=int, default=0, help="Outer margin")
    parser.add_argument("--gap", type=int, default=0, help="Gap between images")
    parser.add_argument("--bg", default="#000000", help="Background color")
    parser.add_argument(
        "--fallback-crop-ratio",
        type=float,
        default=0.17,
        help="Bottom crop ratio used if auto-detection fails",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=4,
        help="Fixed number of columns per page",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=7,
        help="Fixed number of rows per page",
    )
    parser.add_argument(
        "--debug-divider",
        action="store_true",
        help="Print detected divider position for each image",
    )

    return parser.parse_args()


def numeric_sort_key(path: Path) -> Tuple[int, str]:
    match = re.search(r"(\d+)", path.stem)
    if match:
        return (int(match.group(1)), path.name.lower())
    return (10**9, path.name.lower())


def list_images(folder: Path) -> List[Path]:
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VALID_EXTS]
    return sorted(files, key=numeric_sort_key)


def row_brightness_scores(img: Image.Image) -> List[float]:
    gray = img.convert("L")
    width, height = gray.size
    pixels = gray.load()

    scores: List[float] = []
    for y in range(height):
        row_sum = 0
        for x in range(width):
            row_sum += pixels[x, y]
        scores.append(row_sum / width)

    return scores


def detect_horizontal_divider_y(img: Image.Image) -> int | None:
    width, height = img.size

    # 👉 只取底部 40%
    crop = img.crop((0, int(height * 0.6), width, height))
    scores = row_brightness_scores(crop)

    start_y = 0
    end_y = len(scores)

    if not scores:
        return None

    local_best_idx = max(range(len(scores)), key=lambda i: scores[i])
    y = int(height * 0.6) + local_best_idx

    return y


def crop_card(img: Image.Image, fallback_crop_ratio: float, debug: bool = False) -> Image.Image:
    width, height = img.size
    divider_y = detect_horizontal_divider_y(img)

    if divider_y is not None:
        crop_y = max(int(height * 0.60), divider_y - 6)
        if debug:
            print(f"Detected divider at y={divider_y}, crop at y={crop_y}")
        return img.crop((0, 0, width, crop_y))

    crop_y = int(height * (1.0 - fallback_crop_ratio))
    if debug:
        print(f"Divider not found, fallback crop at y={crop_y}")
    return img.crop((0, 0, width, crop_y))


def resize_to_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    w, h = img.size
    scale = min(target_w / w, target_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)


def chunk_list(items: Sequence[Path], chunk_size: int) -> Iterable[Sequence[Path]]:
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def build_collage_page(
    image_paths: Sequence[Path],
    output_path: Path,
    canvas_w: int,
    canvas_h: int,
    margin: int,
    gap: int,
    bg: str,
    fallback_crop_ratio: float,
    cols: int,
    rows: int,
    debug: bool,
) -> None:
    if not image_paths:
        raise ValueError("No images found for this page.")

    cropped_images: List[Image.Image] = []
    for path in image_paths:
        with Image.open(path) as im:
            cropped = crop_card(im.convert("RGB"), fallback_crop_ratio, debug=debug)
            cropped_images.append(cropped)

    usable_w = canvas_w - 2 * margin
    usable_h = canvas_h - 2 * margin
    tile_w = int((usable_w - gap * (cols - 1)) / cols)
    tile_h = int((usable_h - gap * (rows - 1)) / rows)

    if tile_w <= 0 or tile_h <= 0:
        raise ValueError("Tile size is invalid. Reduce rows/cols or margins/gaps.")

    bg_rgb = ImageColor.getrgb(bg)
    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_rgb)

    used_rows = math.ceil(len(cropped_images) / cols)
    total_grid_w = cols * tile_w + (cols - 1) * gap
    total_grid_h = used_rows * tile_h + (used_rows - 1) * gap

    start_x = (canvas_w - total_grid_w) // 2
    #start_y = (canvas_h - total_grid_h) // 2
    start_y = margin

    for idx, img in enumerate(cropped_images):
        row = idx // cols
        col = idx % cols
        x = start_x + col * (tile_w + gap)
        y = start_y + row * (tile_h + gap)

        fitted = resize_to_fit(img, tile_w, tile_h)
        paste_x = x + (tile_w - fitted.width) // 2
        paste_y = y + (tile_h - fitted.height) // 2
        canvas.paste(fitted, (paste_x, paste_y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, quality=95)

    print(f"Saved: {output_path}")
    print(f"Images on page: {len(cropped_images)}")
    print(f"Layout: {cols} cols x {used_rows} used rows (fixed max rows: {rows})")
    print(f"Tile: {tile_w} x {tile_h}")
    print(f"Canvas: {canvas_w} x {canvas_h}")

def run_pipeline(
    input_dir: str | Path,
    output_path: str | Path,
    width: int = 1080,
    height: int = 1920,
    margin: int = 18,
    gap: int = 10,
    bg: str = "#000000",
    fallback_crop_ratio: float = 0.17,
    cols: int = 3,
    rows: int = 4,
    debug_divider: bool = False,
) -> None:
    input_dir = Path(input_dir)
    output_path = Path(output_path)

    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input folder not found: {input_dir}")

    image_paths = list_images(input_dir)
    if not image_paths:
        raise ValueError(f"No images found in input folder: {input_dir}")

    if output_path.suffix == "":
        raise ValueError("--output must include a file extension, e.g. summary.png")

    images_per_page = cols * rows
    total_pages = math.ceil(len(image_paths) / images_per_page)

    for page_idx, page_images in enumerate(chunk_list(image_paths, images_per_page), start=1):
        page_output = output_path.with_name(
            f"{output_path.stem}_page{page_idx}{output_path.suffix}"
        )

        build_collage_page(
            image_paths=page_images,
            output_path=page_output,
            canvas_w=width,
            canvas_h=height,
            margin=margin,
            gap=gap,
            bg=bg,
            fallback_crop_ratio=fallback_crop_ratio,
            cols=cols,
            rows=rows,
            debug=debug_divider,
        )

    print(f"Done. Total images: {len(image_paths)}, total pages: {total_pages}")

def main() -> None:
    args = parse_args()
    run_pipeline(
        input_dir=args.input,
        output_path=args.output,
        width=args.width,
        height=args.height,
        margin=args.margin,
        gap=args.gap,
        bg=args.bg,
        fallback_crop_ratio=args.fallback_crop_ratio,
        cols=args.cols,
        rows=args.rows,
        debug_divider=args.debug_divider,
    )


if __name__ == "__main__":
    main()