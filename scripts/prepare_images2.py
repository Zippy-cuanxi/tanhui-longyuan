"""把「图片素材包2」转换为 public/images 资源，并同步后端 uploads/demo。

用法（系统 Python，需要 Pillow）：
    python scripts/prepare_images2.py

约定：
- Logo、分类图标保留透明底 PNG；
- 横幅、商品图、菜品图、登录背景压缩为 WebP；
- 前端使用 /images/... 相对路径，后端使用 /uploads/demo/... 路径。
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent
SRC = DESKTOP / "图片素材包2"
PUBLIC = ROOT / "public" / "images"
BACKENDS = [
    DESKTOP / "tanhui-backend",
    DESKTOP / "碳惠陇原统一后端-tanhui-backend" / "tanhui-backend",
]

PRODUCTS = [
    ("静宁苹果", "jingning-apple"),
    ("定西马铃薯", "dingxi-potato"),
    ("民勤蜜瓜", "minqin-melon"),
    ("甘肃枸杞", "gansu-goji"),
    ("临泽小枣", "linze-jujube"),
    ("兰州百合", "lanzhou-lily"),
    ("岷县当归", "minxian-danggui"),
]

DISHES = [
    ("土豆炖牛腩", "potato-beef"),
    ("枣夹核桃", "jujube-walnut"),
    ("枸杞银耳羹", "goji-soup"),
    ("西芹炒百合", "lily-stirfry"),
]

BANNERS = [
    ("首页主视觉横幅", "home-hero", 2000, "home-hero.webp", "home-hero.webp"),
    ("商品页横幅", "catalog-banner", 2200, "catalog-banner.webp", "catalog-hero.webp"),
    ("产地地图横幅", "origin-map", 2200, "origin-map.webp", "origin-map.webp"),
    ("产地合作社横幅", "origin-coop", 2200, "origin-coop.webp", "cooperative.webp"),
    ("助农项目横幅", "aid", 2200, "aid.webp", "aid-project.webp"),
    ("品牌故事横幅", "brand", 2200, "brand.webp", "brand-story.webp"),
    ("绿色消费专区横幅", "green", 2200, "green.webp", "green-zone.webp"),
]

CATEGORY_NAMES = [
    ("新鲜水果", "fruit"),
    ("粮油杂粮", "grains"),
    ("特色食品", "food"),
    ("甘味文创", "culture"),
    ("绿色积分", "points"),
]


def ensure_dirs() -> None:
    for path in [
        PUBLIC / "logo",
        PUBLIC / "backgrounds",
        PUBLIC / "banners",
        PUBLIC / "categories" / "flat",
        PUBLIC / "categories" / "linear",
        PUBLIC / "products",
        PUBLIC / "dishes",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    for backend in BACKENDS:
        if not backend.exists():
            continue
        for path in [
            backend / "uploads" / "demo" / "products",
            backend / "uploads" / "demo" / "banners",
            backend / "uploads" / "demo" / "categories",
        ]:
            path.mkdir(parents=True, exist_ok=True)


def save_webp(image: Image.Image, dest: Path, quality: int = 88) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(dest, "WEBP", quality=quality, method=6)


def save_alpha_webp(image: Image.Image, dest: Path, quality: int = 90) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "WEBP", quality=quality, method=6, alpha_quality=100)


def save_png(image: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "PNG", optimize=True)


def square_crop(image: Image.Image, fraction: float, anchor: str = "center") -> Image.Image:
    w, h = image.size
    side = int(min(w, h) * fraction)
    left = (w - side) // 2
    top = {"center": (h - side) // 2, "top": 0, "bottom": h - side}.get(anchor, (h - side) // 2)
    return image.crop((left, top, left + side, top + side))


def backend_paths(*parts: str) -> list[Path]:
    paths = []
    for backend in BACKENDS:
        if backend.exists():
            paths.append(backend / "uploads" / "demo" / Path(*parts))
    return paths


def product_images() -> None:
    for source_name, slug in PRODUCTS:
        source = SRC / "商品主图" / f"{source_name}.png"
        image = Image.open(source).convert("RGB")
        card = ImageOps.fit(image, (900, 900), method=Image.LANCZOS)
        save_webp(card, PUBLIC / "products" / f"{slug}.webp", 86)
        for dest in backend_paths("products", f"{slug}.webp"):
            save_webp(card, dest, 86)

        variants = [
            ("1", image, "full"),
            ("2", square_crop(image, 0.78, "center"), "mid"),
            ("3", square_crop(image, 0.60, "top"), "close"),
            ("4", square_crop(image, 0.90, "bottom"), "table"),
        ]
        for suffix, variant, _kind in variants:
            variant = ImageOps.fit(variant, (1200, 1200), method=Image.LANCZOS)
            save_webp(variant, PUBLIC / "products" / f"{slug}-{suffix}.webp", 88)
            for dest in backend_paths("products", f"{slug}-{suffix}.webp"):
                save_webp(variant, dest, 88)
        print(f"product {source_name} -> {slug}")


def dish_images() -> None:
    for source_name, slug in DISHES:
        source = SRC / "菜品图" / f"{source_name}.png"
        image = Image.open(source).convert("RGB")
        card = ImageOps.fit(image, (900, 900), method=Image.LANCZOS)
        save_webp(card, PUBLIC / "dishes" / f"{slug}.webp", 86)
        print(f"dish {source_name} -> {slug}")


def banners() -> None:
    for source_name, slug, width, public_name, backend_name in BANNERS:
        image = Image.open(SRC / "横幅" / f"{source_name}.png").convert("RGB")
        if image.width > width:
            height = round(image.height * width / image.width)
            image = image.resize((width, height), Image.LANCZOS)
        save_webp(image, PUBLIC / "banners" / public_name, 88)
        for dest in backend_paths("banners", backend_name):
            save_webp(image, dest, 88)
        print(f"banner {source_name} -> {public_name} {image.size}")

    category_card = Image.open(SRC / "横幅" / "分类区蓝天梯田小卡.png").convert("RGB")
    category_card = category_card.resize((1400, 1050), Image.LANCZOS)
    save_webp(category_card, PUBLIC / "banners" / "category-card.webp", 88)
    for dest in backend_paths("banners", "category-card.webp"):
        save_webp(category_card, dest, 88)
    print("banner 分类区蓝天梯田小卡 -> category-card.webp")


def derived_cards() -> None:
    origin = Image.open(SRC / "横幅" / "产地地图横幅.png").convert("RGB")
    origin_card = origin.crop((1250, 0, 2150, 858)).resize((900, 900), Image.LANCZOS)
    save_webp(origin_card, PUBLIC / "banners" / "origin-map-card.webp", 88)
    for dest in backend_paths("banners", "origin-map-card.webp"):
        save_webp(origin_card, dest, 88)

    cooperative = Image.open(SRC / "横幅" / "产地合作社横幅.png").convert("RGB")
    farm = cooperative.crop((1250, 80, 2747, 780)).resize((1497, 700), Image.LANCZOS)
    save_webp(farm, PUBLIC / "banners" / "aid-card-farm.webp", 88)
    for dest in backend_paths("banners", "aid-card-farm.webp"):
        save_webp(farm, dest, 88)

    aid = Image.open(SRC / "横幅" / "助农项目横幅.png").convert("RGB")
    farmer = aid.crop((1300, 80, 2747, 753)).resize((1447, 673), Image.LANCZOS)
    save_webp(farmer, PUBLIC / "banners" / "aid-card-farmer.webp", 88)
    for dest in backend_paths("banners", "aid-card-farmer.webp"):
        save_webp(farmer, dest, 88)

    green = Image.open(SRC / "横幅" / "绿色消费专区横幅.png").convert("RGB")
    globe = green.crop((1450, 0, 3072, 768)).resize((1600, 758), Image.LANCZOS)
    save_webp(globe, PUBLIC / "banners" / "green-card.webp", 88)
    for dest in backend_paths("banners", "green-card.webp"):
        save_webp(globe, dest, 88)
    print("derived cards done")


def category_icons() -> None:
    for name, slug in CATEGORY_NAMES:
        flat = Image.open(SRC / "分类图标" / f"{name}.png").convert("RGBA")
        flat = ImageOps.contain(flat, (512, 512), method=Image.LANCZOS)
        save_png(flat, PUBLIC / "categories" / "flat" / f"{slug}.png")
        for dest in backend_paths("categories", f"{slug}.webp"):
            save_alpha_webp(flat, dest, 90)

        linear = Image.open(SRC / "分类图标" / f"线性_{name}.png").convert("RGBA")
        linear = ImageOps.contain(linear, (512, 512), method=Image.LANCZOS)
        save_png(linear, PUBLIC / "categories" / "linear" / f"{slug}.png")
        print(f"category {name} -> {slug}")


def brand_assets() -> None:
    logo = Image.open(SRC / "Logo与背景" / "碳惠陇原Logo_透明底.png").convert("RGBA")
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    logo = ImageOps.contain(logo, (1200, 600), method=Image.LANCZOS)
    save_png(logo, PUBLIC / "logo" / "logo.png")

    mark_width = int(logo.width * 0.46)
    mark = logo.crop((0, 0, mark_width, logo.height))
    mark_bbox = mark.getbbox()
    if mark_bbox:
        mark = mark.crop(mark_bbox)
    side = max(mark.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2), mark)
    save_png(canvas.resize((96, 96), Image.LANCZOS), PUBLIC / "logo" / "favicon.png")

    background = Image.open(SRC / "Logo与背景" / "登录页背景.png").convert("RGB")
    if background.width > 1920:
        height = round(background.height * 1920 / background.width)
        background = background.resize((1920, height), Image.LANCZOS)
    save_webp(background, PUBLIC / "backgrounds" / "login-bg.webp", 86)
    print("brand assets done")


def main() -> None:
    ensure_dirs()
    product_images()
    dish_images()
    banners()
    derived_cards()
    category_icons()
    brand_assets()
    print("done")


if __name__ == "__main__":
    main()
