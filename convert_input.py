# -*- coding: utf-8 -*-
"""
格式转换：把各提取工具的输出转成 analyzer 能直接用的 messages.json

支持：
- WeChatMsg 导出的 CSV（文本/图片/语音等分类）
- WeChatMsg 导出的 JSON
- chatlog-keeper 输出的 wechat_messages.json（已经是标准格式，直接用）
- WeLive 输出的 JSONL

用法：
    python convert_input.py --input 导出文件.csv --output messages.json
    python convert_input.py --input 导出文件.json --output messages.json
"""
import argparse, csv, io, json, os, sys
from datetime import datetime


def detect_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return "wechatmsg_csv"
    if ext == ".jsonl":
        return "welive_jsonl"
    if ext == ".json":
        with io.open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if "ts" in first and "is_self" in first:
                return "already_ok"
            if "CreateTime" in first or "create_time" in first:
                return "wechatmsg_json"
    return "unknown"


def convert_wechatmsg_csv(path):
    msgs = []
    with io.open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_str = row.get("时间", row.get("time", ""))
            sender = row.get("发送者", row.get("sender", ""))
            msg_type_str = row.get("类型", row.get("type", "文本"))
            content = row.get("内容", row.get("content", ""))
            is_self = row.get("是否本人", row.get("is_self", "否"))
            try:
                ts = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").timestamp()
            except Exception:
                continue
            type_map = {"文本": 1, "图片": 3, "语音": 34, "视频": 43, "表情": 47, "通话": 50, "系统消息": 10000}
            msg_type = type_map.get(msg_type_str, 1)
            self_map = {"是": True, "否": False, "True": True, "False": False}
            is_self_bool = self_map.get(is_self, is_self == "是")
            msgs.append({"ts": ts, "sender": sender, "content": content, "msg_type": msg_type, "is_self": is_self_bool, "is_group_chat": False})
    return msgs


def convert_wechatmsg_json(path):
    with io.open(path, encoding="utf-8") as f:
        raw = json.load(f)
    msgs = []
    for m in raw:
        ts = m.get("CreateTime", m.get("create_time", 0))
        if isinstance(ts, str):
            try:
                ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").timestamp()
            except Exception:
                continue
        msgs.append({"ts": float(ts), "sender": m.get("Sender", m.get("sender", "")), "content": m.get("StrContent", m.get("content", "")), "msg_type": m.get("Type", m.get("type", 1)), "is_self": m.get("IsSender", m.get("is_self", False)), "is_group_chat": False})
    return msgs


def convert_welive_jsonl(path):
    msgs = []
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
            except Exception:
                continue
            ts = m.get("ts", m.get("timestamp", 0))
            msgs.append({"ts": float(ts), "sender": m.get("sender", m.get("talker", "")), "content": m.get("content", ""), "msg_type": m.get("msg_type", m.get("type", 1)), "is_self": m.get("is_self", m.get("is_sender", False)), "is_group_chat": False})
    return msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="messages.json")
    args = ap.parse_args()
    fmt = detect_format(args.input)
    print(f"检测到格式: {fmt}")
    if fmt == "already_ok":
        import shutil
        shutil.copy(args.input, args.output)
        print("已经是标准格式，直接复制")
        return
    converters = {"wechatmsg_csv": convert_wechatmsg_csv, "wechatmsg_json": convert_wechatmsg_json, "welive_jsonl": convert_welive_jsonl}
    if fmt not in converters:
        print(f"不认识的格式 {fmt}，请手动整理成：")
        print(json.dumps({"ts": 1700000000.0, "sender": "对方", "content": "你好", "msg_type": 1, "is_self": False}, ensure_ascii=False, indent=2))
        sys.exit(1)
    msgs = converters[fmt](args.input)
    with io.open(args.output, "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=2)
    print(f"转换完成: {len(msgs)} 条消息 → {args.output}")


if __name__ == "__main__":
    main()
