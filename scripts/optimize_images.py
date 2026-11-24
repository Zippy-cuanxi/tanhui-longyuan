"""图片性能优化：按实际显示尺寸上限重采样 + WebP 压缩。

背景：分类图标 512x512 PNG（200KB+/张）、商品图 1200x1200 WebP（150~250KB/张）、
首页 hero 2379x991（363KB），而显示宽度只有 50~1000px，首屏图片合计近 3MB。

规则：
- 源 .webp：原地覆盖（文件名不变，引用无需改动）
- 源 .png ：另存同名 .webp（原 PNG 保留作源文件，代码引用改为 .webp）

用法：python scripts/optimize_images.py [--dry]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
DRY = "--dry" in sys.argv

# (路径前缀, 最大宽度, 质量)
RULES: list[tuple[str, int, int]] = [
    ("public/images/logo/logo.png", 480, 88),
    ("public/images/categories/flat/", 176, 82),
    ("public/images/categories/linear/", 128, 82),
    ("public/images/join/", 240, 82),
    ("public/images/products/", 800, 76),
    ("public/images/dishes/", 700, 74),
    ("public/images/banners/home-main-visual", 1600, 76),
    ("public/images/banners/home-hero", 1600, 76),
    ("public/images/banners/", 1400, 76),
    ("public/images/backgrounds/", 1600, 72),
    ("public/images/", 360, 82),  # 其余（头像 / 空状态 / 店铺 Logo 等）
    ("tanhui-backend/uploads/demo/products/", 800, 76),
    ("tanhui-backend/uploads/demo/banners/", 1400, 76),
    ("tanhui-backend/uploads/demo/categories/", 240, 82),
]

SUFFIXES = {".webp", ".png", ".jpg", ".jpeg"}


def rule_for(rel: str) -> tuple[int, int]:
    for prefix, width, quality in RULES:
        if rel.startswith(prefix):
            return width, quality
    return 360, 82


def main() -> None:
    files = sorted(
        p
        for p in list((REPO / "public/images").rglob("*"))
        + list((REPO / "tanhui-backend/uploads").rglob("*"))
        if p.suffix.lower() in SUFFIXES and p.is_file() and "favicon" not in p.name
    )
    before = after = 0
    for path in files:
        rel = path.relative_to(REPO).as_posix()
        if path.suffix.lower() == ".webp" and path.with_suffix(".png").exists():
            # 已有同名 WebP 的旧 PNG，跳过重复处理
            pass
        max_w, quality = rule_for(rel)
        size_before = path.stat().st_size
        try:
            with Image.open(path) as source:
                im = source.convert("RGBA") if source.mode in ("RGBA", "LA", "P") else source.convert("RGB")
                if im.width > max_w:
                    target_h = round(im.height * max_w / im.width)
                    im = im.resize((max_w, target_h), Image.LANCZOS)
                out = path.with_suffix(".webp")
                if not DRY:
                    im.save(out, "WEBP", quality=quality, method=6)
                    if path.suffix.lower() == ".webp":
                        out.replace(path)
            size_after = out.stat().st_size if not DRY else 0
            before += size_before
            after += size_after
            print(
                f"{size_before // 1024:5d}KB -> {size_after // 1024:4d}KB  "
                f"{im.width}x{im.height}  {rel}"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"SKIP {rel}: {exc}")
    print(f"\n合计 {before / 1048576:.1f} MB -> {after / 1048576:.1f} MB")
    if DRY:
        print("（dry-run，未写盘）")


if __name__ == "__main__":
    main()
