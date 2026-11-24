"""把设计素材包转换为 Web 体积资源（WebP/PNG）。

用法（系统 Python，需 Pillow）：
    python scripts/prepare_assets.py

输出：
    碳惠陇原/public/assets/**       前端静态资源
    tanhui-backend/uploads/demo/**  后端静态资源（商品图/CMS 横幅）
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent
SRC = DESKTOP / "图片素材包"
PUBLIC = ROOT / "public" / "assets"
BACKEND_UPLOADS = DESKTOP / "tanhui-backend" / "uploads" / "demo"

PRODUCTS = [
    ("静宁苹果", "jingning-apple"),
    ("定西马铃薯", "dingxi-potato"),
    ("民勤蜜瓜", "minqin-melon"),
    ("甘肃枸杞", "gansu-goji"),
    ("临泽小枣", "linze-jujube"),
    ("兰州百合", "lanzhou-lily"),
    ("岷县当归", "minxian-danggui"),
]

BANNERS = [
    ("首页主视觉横幅", "home-hero", 2000),
    ("商品页横幅", "catalog-hero", 2200),
    ("产地地图横幅", "origin-map", 2200),
    ("产地合作社横幅", "cooperative", 2200),
    ("助农项目横幅", "aid-project", 2200),
    ("品牌故事横幅", "brand-story", 2200),
    ("绿色消费专区横幅", "green-zone", 2200),
]

CATEGORY_ICONS = [
    ("新鲜水果", "fruit"),
    ("粮油杂粮", "grains"),
    ("特色食品", "food"),
    ("甘味文创", "culture"),
    ("绿色积分", "points"),
]


def ensure_dirs() -> None:
    for path in [
        PUBLIC / "products",
        PUBLIC / "banners",
        PUBLIC / "categories",
        PUBLIC / "brand",
        BACKEND_UPLOADS / "products",
        BACKEND_UPLOADS / "banners",
        BACKEND_UPLOADS / "categories",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def save_webp(image: Image.Image, dest: Path, quality: int = 88, alpha: bool = False) -> None:
    if alpha:
        image.save(dest, "WEBP", quality=quality, method=6, alpha_quality=100)
    else:
        image.convert("RGB").save(dest, "WEBP", quality=quality, method=6)


def square_crop(image: Image.Image, fraction: float, anchor: str = "center") -> Image.Image:
    w, h = image.size
    side = int(min(w, h) * fraction)
    if anchor == "center":
        left = (w - side) // 2
        top = (h - side) // 2
    elif anchor == "bottom":
        left = (w - side) // 2
        top = h - side
    elif anchor == "top":
        left = (w - side) // 2
        top = 0
    else:
        left = (w - side) // 2
        top = (h - side) // 2
    return image.crop((left, top, left + side, top + side))


def product_images() -> None:
    for source_name, slug in PRODUCTS:
        source = SRC / "商品主图" / f"{source_name}.png"
        image = Image.open(source).convert("RGB")
        card = ImageOps.fit(image, (900, 900), method=Image.LANCZOS)
        save_webp(card, PUBLIC / "products" / f"{slug}.webp", 86)
        save_webp(card, BACKEND_UPLOADS / "products" / f"{slug}.webp", 86)

        variants = [
            ("1", image, "full"),
            ("2", square_crop(image, 0.78, "center"), "mid"),
            ("3", square_crop(image, 0.60, "top"), "close"),
            ("4", square_crop(image, 0.90, "bottom"), "table"),
        ]
        for suffix, variant, _kind in variants:
            if variant.size != image.size:
                variant = variant.resize((1200, 1200), Image.LANCZOS)
            else:
                variant = ImageOps.fit(variant, (1200, 1200), method=Image.LANCZOS)
            save_webp(variant, PUBLIC / "products" / f"{slug}-{suffix}.webp", 88)
            save_webp(variant, BACKEND_UPLOADS / "products" / f"{slug}-{suffix}.webp", 88)
        print(f"product {source_name} -> {slug}")


def banner_images() -> None:
    for source_name, slug, width in BANNERS:
        source = SRC / "横幅" / f"{source_name}.png"
        image = Image.open(source).convert("RGB")
        if image.width > width:
            height = round(image.height * width / image.width)
            image = image.resize((width, height), Image.LANCZOS)
        save_webp(image, PUBLIC / "banners" / f"{slug}.webp", 88)
        save_webp(image, BACKEND_UPLOADS / "banners" / f"{slug}.webp", 88)
        print(f"banner {source_name} -> {slug} {image.size}")


def extra_cards() -> None:
    """首页侧栏产地卡片 + 助农项目卡片（从横幅裁切，避开画面内的大字文案）。"""
    origin = Image.open(SRC / "横幅" / "产地地图横幅.png").convert("RGB")
    crop = origin.crop((1250, 0, 2150, 858)).resize((900, 900), Image.LANCZOS)
    save_webp(crop, PUBLIC / "banners" / "origin-map-card.webp", 88)
    save_webp(crop, BACKEND_UPLOADS / "banners" / "origin-map-card.webp", 88)

    cooperative = Image.open(SRC / "横幅" / "产地合作社横幅.png").convert("RGB")
    farm = cooperative.crop((1250, 80, 2747, 780)).resize((1497, 700), Image.LANCZOS)
    save_webp(farm, PUBLIC / "banners" / "aid-card-farm.webp", 88)
    save_webp(farm, BACKEND_UPLOADS / "banners" / "aid-card-farm.webp", 88)

    aid = Image.open(SRC / "横幅" / "助农项目横幅.png").convert("RGB")
    farmer = aid.crop((1300, 80, 2747, 753)).resize((1447, 673), Image.LANCZOS)
    save_webp(farmer, PUBLIC / "banners" / "aid-card-farmer.webp", 88)
    save_webp(farmer, BACKEND_UPLOADS / "banners" / "aid-card-farmer.webp", 88)

    green = Image.open(SRC / "横幅" / "绿色消费专区横幅.png").convert("RGB")
    globe = green.crop((1450, 0, 3072, 768)).resize((1600, 758), Image.LANCZOS)
    save_webp(globe, PUBLIC / "banners" / "green-card.webp", 88)
    print("extra cards done")


def category_icons() -> None:
    for source_name, slug in CATEGORY_ICONS:
        source = SRC / "分类图标" / f"{source_name}.png"
        image = Image.open(source).convert("RGBA")
        image = ImageOps.contain(image, (512, 512), method=Image.LANCZOS)
        save_webp(image, PUBLIC / "categories" / f"{slug}.webp", 90, alpha=True)
        save_webp(image, BACKEND_UPLOADS / "categories" / f"{slug}.webp", 90, alpha=True)
        print(f"category {source_name} -> {slug}")


def brand_assets() -> None:
    logo = Image.open(SRC / "Logo与背景" / "碳惠陇原Logo_透明底.png").convert("RGBA")
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    logo = ImageOps.contain(logo, (1200, 600), method=Image.LANCZOS)
    logo.save(PUBLIC / "brand" / "logo.png", "PNG", optimize=True)

    # 用 Logo 左侧山峰图形做站点图标
    mark_width = int(logo.width * 0.46)
    mark = logo.crop((0, 0, mark_width, logo.height))
    mark_bbox = mark.getbbox()
    if mark_bbox:
        mark = mark.crop(mark_bbox)
    side = max(mark.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2), mark)
    canvas.resize((96, 96), Image.LANCZOS).save(PUBLIC / "brand" / "favicon.png", "PNG", optimize=True)

    background = Image.open(SRC / "Logo与背景" / "登录页背景.png").convert("RGB")
    if background.width > 1920:
        height = round(background.height * 1920 / background.width)
        background = background.resize((1920, height), Image.LANCZOS)
    save_webp(background, PUBLIC / "brand" / "login-bg.webp", 86)
    print("brand assets done")


def main() -> None:
    ensure_dirs()
    product_images()
    banner_images()
    extra_cards()
    category_icons()
    brand_assets()
    print("done")


if __name__ == "__main__":
    main()
