"""
物流查询 Tool
支持 mock 数据和真实 API 两种模式
"""
from langchain_core.tools import tool

from app.config import settings

_MOCK_LOGISTICS = {
    "12345": [
        {"time": "2026-06-11 10:00:00", "location": "上海分拣中心", "status": "已分拣"},
        {"time": "2026-06-11 18:30:00", "location": "上海转运中心", "status": "已发出"},
        {"time": "2026-06-12 09:15:00", "location": "杭州转运中心", "status": "已到达"},
        {"time": "2026-06-12 14:00:00", "location": "杭州配送站", "status": "配送中"},
    ],
    "12346": [
        {"time": "2026-06-06 08:00:00", "location": "深圳分拣中心", "status": "已分拣"},
        {"time": "2026-06-07 20:00:00", "location": "深圳转运中心", "status": "已发出"},
        {"time": "2026-06-08 11:30:00", "location": "北京转运中心", "status": "已到达"},
        {"time": "2026-06-09 10:00:00", "location": "北京朝阳配送站", "status": "已签收"},
    ],
}


def _call_real_api(order_id: str) -> str:
    """调用真实的物流 API"""
    import requests
    try:
        resp = requests.get(
            f"{settings.logistics_api_url}/{order_id}",
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        lines = [f"订单 {order_id} 物流轨迹："]
        for t in data.get("track", []):
            lines.append(f"  {t['time']} - {t['location']} - {t['status']}")
        return "\n".join(lines)
    except Exception as e:
        return f"查询物流失败（{e}），请稍后重试。"


def _mock_query(order_id: str) -> str:
    """使用 mock 数据查询"""
    track = _MOCK_LOGISTICS.get(order_id)
    if track is None:
        from app.tools.order_tool import _MOCK_ORDERS
        if order_id in _MOCK_ORDERS and _MOCK_ORDERS[order_id]["status"] == "待发货":
            return f"订单 {order_id} 尚未发货，暂无物流信息。"
        return f"未找到订单 {order_id} 的物流信息，请确认订单号是否正确。"

    lines = [f"订单 {order_id} 物流轨迹："]
    for t in track:
        lines.append(f"  {t['time']} - {t['location']} - {t['status']}")
    return "\n".join(lines)


@tool
def query_logistics(order_id: str) -> str:
    """
    查询物流信息。
    当用户询问快递物流轨迹（如包裹到哪了、物流进度）时使用。
    需要用户提供订单号作为参数。
    """
    if settings.logistics_api_url:
        return _call_real_api(order_id)
    return _mock_query(order_id)
