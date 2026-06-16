"""
订单查询 Tool
支持 mock 数据和真实 API 两种模式
"""
from langchain_core.tools import tool

from app.config import settings

_MOCK_ORDERS = {
    "12345": {
        "order_id": "12345", "status": "已发货",
        "product": "智能手环 Pro", "price": 299.00,
        "create_time": "2026-06-10 14:30:00",
    },
    "12346": {
        "order_id": "12346", "status": "已签收",
        "product": "蓝牙耳机", "price": 159.00,
        "create_time": "2026-06-05 10:00:00",
    },
    "12347": {
        "order_id": "12347", "status": "待发货",
        "product": "无线充电器", "price": 89.00,
        "create_time": "2026-06-15 16:20:00",
    },
}


def _call_real_api(order_id: str) -> str:
    """调用真实的订单 API"""
    import requests
    try:
        resp = requests.get(
            f"{settings.order_api_url}/{order_id}",
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        return (
            f"订单 {data['order_id']}：\n"
            f"商品：{data['product']}\n"
            f"金额：¥{data['price']:.2f}\n"
            f"状态：{data['status']}\n"
            f"下单时间：{data['create_time']}"
        )
    except Exception as e:
        return f"查询订单失败（{e}），请稍后重试。"


def _mock_query(order_id: str) -> str:
    """使用 mock 数据查询"""
    order = _MOCK_ORDERS.get(order_id)
    if order is None:
        return f"未找到订单 {order_id}，请确认订单号是否正确。"
    return (
        f"订单 {order['order_id']}：\n"
        f"商品：{order['product']}\n"
        f"金额：¥{order['price']:.2f}\n"
        f"状态：{order['status']}\n"
        f"下单时间：{order['create_time']}"
    )


@tool
def query_order_status(order_id: str) -> str:
    """
    查询订单状态。
    当用户询问订单状态（如是否发货、是否签收、物流进展等）时使用。
    需要用户提供订单号作为参数。
    """
    if settings.order_api_url:
        return _call_real_api(order_id)
    return _mock_query(order_id)
