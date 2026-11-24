"""把体积过大的 PNG 资源转为 WebP，减小 GitHub Pages 首屏下载量。

背景：管理端商品图 800x800 的 PNG 单张达 1MB，列表页一次加载 20+ 张，
在弱网下会出现"图片迟迟不显示"。转为 WebP 后单张约 30~60KB。

用法：python scripts/optimize_images.py
（转换后需同步把代码中的 .png 引用改为 .webp，并删除旧 PNG）
"""

from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent

# (源文件, 目标宽高, 质量)
TARGETS = [
    (REPO / "public/console-assets/images/apple.png", (640, 640), 80),
    (REPO / "public/console-assets/images/potato.png", (640, 640), 80),
    (REPO / "public/console-assets/images/melon.png", (640, 640), 80),
    (REPO / "public/console-assets/images/goji.png", (640, 640), 80),
    (REPO / "public/console-assets/images/jujube.png", (640, 640), 80),
    (REPO / "public/console-assets/images/lily.png", (640, 640), 80),
    (REPO / "public/console-assets/images/danggui.png", (640, 640), 80),
    (REPO / "public/console-assets/images/login-bg.png", (1600, 900), 78),
    (REPO / "public/images/join/join-hero.png", (1600, 500), 80),
]


def main() -> None:
    total_before = 0
    total_after = 0
    for src, size, quality in TARGETS:
        if not src.exists():
            print(f"跳过（不存在）: {src.relative_to(REPO)}")
            continue
        before = src.stat().st_size
        dst = src.with_suffix(".webp")
        with Image.open(src) as im:
            im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
            # 等比缩放到目标框内，避免变形
            im.thumbnail(size, Image.LANCZOS)
            im.save(dst, "WEBP", quality=quality, method=6)
        after = dst.stat().st_size
        total_before += before
        total_after += after
        print(
            f"{src.name:24s} {before / 1048576:5.2f}MB -> {dst.name:24s} "
            f"{after / 1024:6.1f}KB  ({after / before * 100:.0f}%)"
        )
    print(f"\n合计 {total_before / 1048576:.1f}MB -> {total_after / 1048576:.2f}MB")


if __name__ == "__main__":
    main()
