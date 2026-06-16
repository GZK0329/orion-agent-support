"""
会话记忆存储
支持内存 + 文件持久化，服务重启不丢失
"""
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

_MAX_HISTORY_TURNS = 10
_STORE_FILE = Path(__file__).parent.parent / "data" / "sessions.json"
_lock = threading.Lock()


def _now() -> int:
    import time
    return int(time.time() * 1000)


class SessionStore:
    """文件持久化的会话记忆存储"""

    def __init__(self) -> None:
        self._sessions: Dict[str, dict] = {}
        self._load()

    # ---- 序列化 ----

    def _path(self) -> Path:
        return _STORE_FILE.resolve()

    def _load(self) -> None:
        path = self._path()
        if not path.exists():
            return
        try:
            raw: dict = json.loads(path.read_text("utf-8"))
        except Exception:
            self._sessions = {}
            return

        converted: Dict[str, dict] = {}
        for sid, val in raw.items():
            # 兼容旧格式：session_id -> [msg_dict, ...]
            if isinstance(val, list):
                converted[sid] = {"created_at": _now(), "messages": val}
            else:
                converted[sid] = val
        self._sessions = converted

    def _save(self) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            path.write_text(
                json.dumps(self._sessions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # ---- 读取 ----

    def get_history(self, session_id: str) -> List[BaseMessage]:
        raw_list = self._sessions.get(session_id, {}).get("messages", [])
        try:
            return messages_from_dict(raw_list)
        except Exception:
            return []

    def list_sessions(self) -> List[dict]:
        """列出所有会话摘要（按创建时间倒序）"""
        result = []
        for sid, data in self._sessions.items():
            msgs = data.get("messages", [])
            title = "新对话"
            for m in msgs:
                if m.get("type") == "human":
                    content = m.get("data", {}).get("content", "")
                    if content:
                        title = content[:30] + "…" if len(content) > 30 else content
                    break
            result.append({
                "session_id": sid,
                "title": title,
                "message_count": len(msgs),
                "created_at": data.get("created_at", 0),
            })
        result.sort(key=lambda x: -(x["created_at"] or 0))
        return result

    def get_raw_messages(self, session_id: str) -> list:
        """获取会话的原始消息列表（dict 格式），供 API 返回"""
        return self._sessions.get(session_id, {}).get("messages", [])

    # ---- 写入 ----

    def add_messages(self, session_id: str, messages: List[BaseMessage]) -> None:
        raw_list = messages_from_dict(
            self._sessions.get(session_id, {}).get("messages", [])
        ) if session_id in self._sessions else []
        raw_list.extend(messages)
        max_len = _MAX_HISTORY_TURNS * 2
        if len(raw_list) > max_len:
            raw_list = raw_list[-max_len:]

        entry = self._sessions.setdefault(session_id, {"created_at": _now(), "messages": []})
        entry["messages"] = [message_to_dict(m) for m in raw_list]
        self._save()

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._save()
            return True
        return False

    def clear(self, session_id: str) -> None:
        self.delete_session(session_id)


session_store = SessionStore()
