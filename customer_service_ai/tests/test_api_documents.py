import io

import pytest

SKIP_REASON = "需要真实 Embedding API 才能初始化 ChromaDB"


@pytest.mark.asyncio
async def test_list_documents_requires_auth(client, admin_headers):
    resp = await client.get("/documents/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_unsupported_format(client, admin_headers):
    resp = await client.post(
        "/documents/upload",
        files={"file": ("test.exe", io.BytesIO(b"dummy"))},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "不支持的格式" in resp.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.skip(reason=SKIP_REASON)
async def test_upload_md_file(client, admin_headers):
    content = "# 测试文档\n\n这是测试内容。".encode("utf-8")
    resp = await client.post(
        "/documents/upload",
        files={"file": ("test_upload.md", io.BytesIO(content))},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "导入成功" in data["message"]


@pytest.mark.asyncio
@pytest.mark.skip(reason=SKIP_REASON)
async def test_delete_document_not_found(client, admin_headers):
    resp = await client.delete("/documents/nonexistent.md", headers=admin_headers)
    assert resp.status_code == 204
