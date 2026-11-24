"""导出数据库字段字典（ER 图 + 每表字段说明）。

用法：
    python -m scripts.export_dictionary
生成：
    docs/er-diagram.md       —— Mermaid ER 图（关系按外键推导）
    docs/field-dictionary.md —— 字段字典（表/字段/类型/可空/索引/说明）
"""
from pathlib import Path

import app.modules.models_registry  # noqa: F401
from app.core.base import Base
from app.core.types import GUID, Amount, JSONBType, UTCDatetime

DOCS = Path(__file__).resolve().parent.parent / "docs"

TYPE_MAP = {GUID: "UUID", Amount: "NUMERIC(12,2)", JSONBType: "JSONB", UTCDatetime: "TIMESTAMPTZ"}


def _col_type(col) -> str:
    if type(col.type) in TYPE_MAP:
        return TYPE_MAP[type(col.type)]
    return str(col.type)


def _fk_target(fk) -> str:
    return f"{fk.column.table.name}.{fk.column.name}"


def main() -> None:
    meta = Base.metadata
    DOCS.mkdir(exist_ok=True)

    # ---------- ER 图（Mermaid）----------
    er = [
        "# ER 图（自动生成，请勿手改）",
        "",
        "> 关系连线由外键推导；金额列均为 NUMERIC(12,2)；主键统一 UUID。",
        "",
        "```mermaid",
        "erDiagram",
    ]
    for table in sorted(meta.tables.values(), key=lambda t: t.name):
        fields = []
        for col in table.columns:
            t = _col_type(col)
            if col.primary_key:
                fields.append(f"{col.name} {t} PK")
            elif col.foreign_keys:
                fields.append(f"{col.name} {t} FK")
            elif col.name in ("created_at", "updated_at"):
                continue  # 省略公共时间列，保持图面简洁
            else:
                fields.append(f"{col.name} {t}")
        er.append('    "' + table.name + '" {')
        er += [f"        {f}" for f in fields[:14]]  # 每表最多展示14字段
        if len(fields) > 14:
            er.append("        ... 其余字段见字段字典")
        er.append("    }")
        seen = set()
        for col in table.columns:
            for fk in col.foreign_keys:
                key = (fk.column.table.name, table.name)
                if key not in seen:
                    er.append(f"    {fk.column.table.name} ||--o{{ {table.name} : has")
                    seen.add(key)
    er += ["```", ""]
    (DOCS / "er-diagram.md").write_text("\n".join(er), encoding="utf-8")

    # ---------- 字段字典 ----------
    lines = [
        "# 数据库字段字典（自动生成，请勿手改）",
        "",
        f"共 {len(meta.tables)} 张表。通用约定：",
        "- 主键 `id` UUID；`created_at`/`updated_at` TIMESTAMPTZ(UTC)",
        "- 金额 NUMERIC(12,2)；JSONB 用于审计详情/规则配置/页面快照",
        "",
    ]
    for table in sorted(meta.tables.values(), key=lambda t: t.name):
        lines += [f"## {table.name}", "", "| 字段 | 类型 | 可空 | 默认 | 说明 |", "|---|---|---|---|---|"]
        for col in table.columns:
            note = []
            if col.primary_key:
                note.append("主键")
            for fk in col.foreign_keys:
                note.append(f"→ {_fk_target(fk)}")
            if col.unique:
                note.append("唯一")
            if col.index:
                note.append("索引")
            default = "" if col.default is None else str(col.default.arg) if hasattr(col.default, "arg") else str(col.default)
            lines.append(
                f"| {col.name} | {_col_type(col)} | {'是' if col.nullable else '否'} "
                f"| {default} | {'，'.join(note)} |"
            )
        lines.append("")
    (DOCS / "field-dictionary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ 已生成 docs/er-diagram.md / field-dictionary.md（{len(meta.tables)} 表）")


if __name__ == "__main__":
    main()
