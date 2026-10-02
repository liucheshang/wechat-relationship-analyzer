# -*- coding: utf-8 -*-
"""数据加载：读 wechat_messages.json，输出标准化消息列表。"""
import json, io
from datetime import datetime

def load_messages(path):
    """
    输入 JSON 格式（每条消息）：
    {
      "ts": 1700000000.0,          # unix 时间戳（秒）
      "sender": "对方昵称",         # 显示名
      "sender_wxid": "wxid_xxx",   # 发送者 wxid
      "content": "消息文本",        # 文本内容（非文本消息为占位符）
      "msg_type": 1,               # 1=文本 3=图片 34=语音 43=视频 47=表情 49=链接 50=通话
      "is_self": false,            # 是否本人发送
      "is_group_chat": false
    }
    """
    raw = json.load(io.open(path, encoding="utf-8"))
    msgs = []
    for m in raw:
        if not isinstance(m.get("ts"), (int, float)):
            continue
        if m.get("is_group_chat"):
            continue
        msgs.append({
            "ts": float(m["ts"]),
            "dt": datetime.fromtimestamp(m["ts"]),
            "sender": m.get("sender", ""),
            "is_self": bool(m.get("is_self", False)),
            "content": m.get("content") or "",
            "msg_type": m.get("msg_type", 1),
        })
    msgs.sort(key=lambda x: x["ts"])
    return msgs

def filter_text(msgs):
    """只保留文本消息。"""
    return [m for m in msgs if m["msg_type"] == 1 and isinstance(m["content"], str) and len(m["content"].strip()) >= 2]
