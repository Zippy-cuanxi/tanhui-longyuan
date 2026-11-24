"""CMS 测试：白名单校验、发布快照、回滚、客户端安全降级。"""
import uuid

from app.core.database import SessionLocal
from app.modules.cms.models import CmsSection
from tests.conftest import admin_headers


def _page(client):
    admin = admin_headers(client, "cms-admin@example.com")
    resp = client.post(
        "/api/v1/cms/pages",
        json={"page_key": "home", "title": "首页配置"},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    return admin, resp.json()["data"]["id"]


def test_cms_component_whitelist_and_publish(client):
    admin, page_id = _page(client)

    # 未白名单组件 → 拒绝
    resp = client.post(
        f"/api/v1/cms/pages/{page_id}/sections",
        json={"section_type": "evil_script", "config": {"code": "alert(1)"}},
        headers=admin,
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "CMS_COMPONENT_UNKNOWN"

    # 外链非 https → 拒绝
    resp = client.post(
        f"/api/v1/cms/pages/{page_id}/sections",
        json={
            "section_type": "banner",
            "config": {
                "title": "新店开业",
                "image_url": "https://cdn.example.com/b.jpg",
                "link_type": "external",
                "link_url": "http://unsafe.example.com",
            },
        },
        headers=admin,
    )
    assert resp.status_code == 422

    # 合法 banner + 商品宫格 → 保存成功
    resp = client.post(
        f"/api/v1/cms/pages/{page_id}/sections",
        json={
            "section_type": "banner",
            "config": {
                "title": "甘肃好物",
                "image_url": "https://cdn.example.com/a.jpg",
                "link_type": "internal",
                "link_url": "/products",
            },
        },
        headers=admin,
    )
    assert resp.status_code == 200, resp.text

    # 发布 → 版本 v1
    resp = client.post(f"/api/v1/cms/pages/{page_id}/publish", headers=admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["version"] == 1

    # 客户端读取（公开）
    resp = client.get("/api/v1/client/config/home")
    assert resp.status_code == 200
    assert resp.headers.get("etag")
    body = resp.json()
    assert body["page"]["page_key"] == "home"
    assert len(body["sections"]) == 1


def test_cms_rollback_and_safe_degrade(client):
    admin, page_id = _page(client)
    client.post(
        f"/api/v1/cms/pages/{page_id}/sections",
        json={
            "section_type": "banner",
            "config": {
                "title": "v1",
                "image_url": "https://cdn.example.com/v1.jpg",
                "link_type": "internal",
                "link_url": "/a",
            },
        },
        headers=admin,
    )
    client.post(f"/api/v1/cms/pages/{page_id}/publish", headers=admin)  # v1

    # 再改内容 → 发布 v2
    client.post(
        f"/api/v1/cms/pages/{page_id}/sections",
        json={
            "section_type": "banner",
            "config": {
                "title": "v2",
                "image_url": "https://cdn.example.com/v2.jpg",
                "link_type": "internal",
                "link_url": "/b",
            },
        },
        headers=admin,
    )
    resp = client.post(f"/api/v1/cms/pages/{page_id}/publish", headers=admin)
    assert resp.status_code == 200, resp.text
    v2 = resp.json()["data"]
    assert v2["version"] == 2

    resp = client.get("/api/v1/client/config/home")
    titles = [s["config"]["title"] for s in resp.json()["sections"]]
    assert "v2" in titles and "v1" in titles  # 新增区块已随 v2 发布

    # 回滚到 v1
    resp = client.get(f"/api/v1/cms/pages/{page_id}/versions", headers=admin)
    versions = resp.json()["data"]
    v1 = next(v for v in versions if v["version"] == 1)
    resp = client.post(
        f"/api/v1/cms/pages/{page_id}/rollback/{v1['id']}", headers=admin
    )
    assert resp.status_code == 200, resp.text
    resp = client.get("/api/v1/client/config/home")
    assert resp.json()["sections"][0]["config"]["title"] == "v1"

    # 安全降级：手工在库中插入未知组件，客户端读取时跳过且不报错
    db = SessionLocal()
    db.add(
        CmsSection(
            page_id=uuid.UUID(page_id),
            section_type="future_component",
            sort=99,
            enabled=True,
            config={"anything": True},
        )
    )
    db.commit()
    db.close()
    resp = client.get("/api/v1/client/config/home")
    assert resp.status_code == 200
    assert all(s["section_type"] != "future_component" for s in resp.json()["sections"])


def test_unpublished_page_404(client):
    resp = client.get("/api/v1/client/config/never-published")
    assert resp.status_code == 404
    assert resp.json()["code"] == "CMS_PAGE_NOT_PUBLISHED"
