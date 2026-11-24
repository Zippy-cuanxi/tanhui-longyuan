"""导出 OpenAPI 契约与 API 清单。

用法：
    python -m scripts.export_openapi
生成：
    docs/openapi.yaml  —— OpenAPI 3.1 契约（前端 AI 依据此文件生成 client）
    docs/api-list.md   —— 三端 API 清单（按 tag 分组）
"""
import json
from collections import defaultdict
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def main() -> None:
    import yaml  # 若无 pyyaml 则回退仅导出 json

    import app.main  # noqa: F401 触发路由注册
    from app.main import app

    spec = app.openapi()
    DOCS.mkdir(exist_ok=True)

    (DOCS / "openapi.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:
        with open(DOCS / "openapi.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(spec, f, allow_unicode=True, sort_keys=False)
    except ImportError:
        print("(未安装 pyyaml，跳过 yaml 输出)")

    # ---- API 清单 ----
    groups: dict[str, list[str]] = defaultdict(list)
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            tag = (op.get("tags") or ["other"])[0]
            groups[tag].append(f"| `{method.upper()}` | `{path}` | {op.get('summary','')} |")

    lines = [
        "# API 清单（自动生成，请勿手改）",
        "",
        f"总接口数：{sum(len(v) for v in groups.values())}",
        "",
    ]
    for tag in sorted(groups):
        lines += [f"## {tag}", "", "| 方法 | 路径 | 说明 |", "|---|---|---|"]
        lines += sorted(groups[tag]) + [""]
    (DOCS / "api-list.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ 已生成 docs/openapi.yaml / openapi.json / api-list.md，"
          f"共 {sum(len(v) for v in groups.values())} 个接口")


if __name__ == "__main__":
    main()
