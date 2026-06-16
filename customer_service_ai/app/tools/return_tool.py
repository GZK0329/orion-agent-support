"""
退货申请 Tool
支持 mock 数据和真实 API 两种模式
"""
from langchain_core.tools import tool

from app.config import settings

_APPLIED_RETURNS: set[str] = set()


def _call_real_api(order_id: str, reason: str) -> str:
    """调用真实的退货 API"""
    import requests
    try:
        resp = requests.post(
            settings.return_api_url,
            json={"order_id": order_id, "reason": reason},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        return (
            f"已为您提交订单 {order_id} 的退货申请。\n"
            f"退货原因：{reason}\n"
            f"预计 {data.get('processing_time', '1-2 个工作日')} 内客服会联系您处理。"
        )
    except Exception as e:
        return f"提交退货申请失败（{e}），请稍后重试或联系人工客服。"


def _mock_apply(order_id: str, reason: str) -> str:
    """使用 mock 数据申请退货"""
    from app.tools.order_tool import _MOCK_ORDERS

    order = _MOCK_ORDERS.get(order_id)
    if order is None:
        return f"未找到订单 {order_id}，请确认订单号是否正确。"

    if order["status"] == "待发货":
        return f"订单 {order_id} 尚未发货，建议您取消订单而非申请退货。"

    if order_id in _APPLIED_RETURNS:
        return f"订单 {order_id} 已提交过退货申请，请耐心等待客服处理（1-2个工作日）。"

    _APPLIED_RETURNS.add(order_id)
    return (
        f"已为您提交订单 {order_id}（{order['product']}）的退货申请。\n"
        f"退货原因：{reason}\n"
        f"金额：¥{order['price']:.2f}\n"
        f"预计 1-2 个工作日内客服会联系您处理，请保持电话畅通。"
    )


@tool
def apply_return(order_id: str, reason: str) -> str:
    """
    申请退货退款。
    当用户明确表示要退货、退款、退货退款时使用。
    需要用户提供订单号和退货原因。
    注意：仅对已发货或已签收的订单开放退货。
    """
    if settings.return_api_url:
        return _call_real_api(order_id, reason)
    return _mock_apply(order_id, reason)
