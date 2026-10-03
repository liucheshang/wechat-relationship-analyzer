# -*- coding: utf-8 -*-
"""
convert.py —— 把别的工具导出的聊天记录，转成 analyze.py 能吃的格式。

analyze.py 只认这种一行一条的纯文本：
    2024-09-19 22:03 | 我 | 出发没宝宝
    2024-09-19 22:03 | TA | 还早

而各个导出工具（WeChatMsg / chatlog / 留痕 / 各种搬运脚本）吐出来的
是 CSV 或 JSON，字段名五花八门。这个脚本负责自动认字段、自动认时间格式，
转成上面的格式。

用法：
    python convert.py 导出文件.json 聊天记录.txt
    python convert.py 导出文件.csv  聊天记录.txt
    python convert.py 导出文件.csv  聊天记录.txt --contact 宝儿
    python convert.py 导出文件.json 聊天记录.txt --self-names 我,自己,me

只有标准库，不用 pip install 任何东西。Python 3.8+。
"""

import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------- 字段候选名
# 全部按小写、去掉下划线后比较，所以 ts / Ts / _ts 都能命中
TIME_KEYS = ['ts', 'time', 'timestamp', 'createtime', 'createtimestamp', 'date',
             'datetime', 'strtime', 'createtime', 'msgtime', 'sendtime', '时间']
SELF_KEYS = ['is_self', 'isself', 'issend', 'is_sender', 'self', 'from_me',
             'issender', '发送方', '是否本人', 'meflag']
SENDER_KEYS = ['sender', 'talker', 'from', 'username', 'sendername', 'wxid',
               'nickname', '昵称', '发送者', '发信人']
CONTENT_KEYS = ['content', 'message', 'text', 'msg', 'strcontent', 'body', '内容']
TYPE_KEYS = ['msg_type', 'msgtype', 'type', 'contenttype', 'mstype', '类型']
ROOM_KEYS = ['chat_room', 'room', 'chatroom', 'conversation', 'chatname',
             'contact', 'remark', '备注', '群名', '聊天对象']

# 微信/企业微信的文本类型码。认不出来就不筛，省得把数据筛没了。
TEXT_TYPE_CODES = {'1', '0', 'text', 'txt', '文本'}
SKIP_TYPE_CODES = {'10000', '10002'}   # 系统消息 / 撤回提示


def norm(k):
    return re.sub(r'[\s_\-]', '', str(k)).lower()


def pick(d, keys):
    """在字典里按候选名找一个存在的键，返回 (真实键名, 值)。"""
    lut = {norm(k): k for k in d.keys()}
    for want in keys:
        k = lut.get(norm(want))
        if k is not None:
            return k, d[k]
    return None, None


def read_any(path):
    """读文件，返回原始文本（自动处理 BOM 和 GBK）。"""
    raw = open(path, 'rb').read()
    for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', 'ignore')


def parse_time(v):
    """把各种时间写法统一成 datetime。认不出来返回 None。"""
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        n = float(v)
    else:
        s = str(v).strip()
        if not s:
            return None
        # 纯数字：秒 / 毫秒
        if re.fullmatch(r'\d{9,14}', s):
            n = float(s)
        else:
            # 常见文本格式，逐个试
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S',
                        '%Y/%m/%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f',
                        '%Y-%m-%dT%H:%M:%SZ', '%Y年%m月%d日 %H:%M:%S', '%Y%m%d%H%M%S'):
                try:
                    return datetime.strptime(s[:len(fmt) + 10], fmt)
                except ValueError:
                    continue
            m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日]?\s*(\d{1,2}):(\d{1,2})',
                          s)
            if m:
                return datetime(*[int(x) for x in m.groups()])
            return None
    # 数字时间戳：10 位是秒，13 位是毫秒
    if n > 1e11:
        n /= 1000.0
    if n <= 0:
        return None
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc).astimezone().replace(tzinfo=None)
    except (OSError, OverflowError, ValueError):
        return None


def rows_from_json(text):
    data = json.loads(text)
    if isinstance(data, dict):
        for k in ('messages', 'data', 'list', 'items', 'records', 'chat'):
            if isinstance(data.get(k), list):
                return data[k]
        # 单条消息的字典
        return [data]
    if isinstance(data, list):
        # 可能是 [[...]] 或 [{...}]
        if data and isinstance(data[0], list):
            flat = []
            for x in data:
                flat.extend(x if isinstance(x, list) else [x])
            return flat
        return data
    raise ValueError('JSON 结构认不出来')


def rows_from_csv(text):
    # 自动认分隔符：逗号 / 制表符 / 分号
    sample = text[:5000]
    delim = ','
    for d in ('\t', ',', ';'):
        if sample.count(d) > sample.count(delim):
            delim = d
    rdr = csv.DictReader(io.StringIO(text), delimiter=delim)
    return [dict(r) for r in rdr if any(v for v in r.values())]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    src, dst = sys.argv[1], sys.argv[2]
    contact = None
    self_names = ['我', '自己', 'me', 'self', '我(发送)', '本人', '我本人']
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == '--contact' and i + 1 < len(args):
            contact = args[i + 1]
            i += 2
        elif args[i] == '--self-names' and i + 1 < len(args):
            self_names = [x.strip() for x in args[i + 1].split(',') if x.strip()]
            i += 2
        else:
            i += 1

    if not os.path.exists(src):
        print('找不到文件：%s' % src)
        sys.exit(1)

    text = read_any(src).strip()
    if not text:
        print('文件是空的。')
        sys.exit(1)

    if text[0] in '[{':
        rows = rows_from_json(text)
    else:
        rows = rows_from_csv(text)

    if not rows or not isinstance(rows[0], dict):
        print('读出来的不是消息列表，前 200 个字符长这样：\n%s' % text[:200])
        sys.exit(1)

    sample = rows[0]
    k_time, _ = pick(sample, TIME_KEYS)
    k_self, _ = pick(sample, SELF_KEYS)
    k_sender, _ = pick(sample, SENDER_KEYS)
    k_content, _ = pick(sample, CONTENT_KEYS)
    k_type, _ = pick(sample, TYPE_KEYS)
    k_room, _ = pick(sample, ROOM_KEYS)

    print('识别到的字段：')
    print('  时间   → %s' % (k_time or '❌ 没认出来'))
    print('  内容   → %s' % (k_content or '❌ 没认出来'))
    print('  发送者 → %s' % (k_self or k_sender or '❌ 没认出来（默认全部记为 TA）'))
    print('  类型   → %s' % (k_type or '（没有，不过滤）'))
    print('  会话   → %s' % (k_room or '（没有，不筛选）'))
    print('共 %d 行' % len(rows))

    if not k_time or not k_content:
        print('\n关键字段没认全，没法转。把文件头几行发我，我给你加规则。')
        sys.exit(1)

    out, skipped_time, skipped_type, skipped_contact = [], 0, 0, 0
    for r in rows:
        if k_room and contact:
            room = str(r.get(k_room, ''))
            if contact not in room:
                skipped_contact += 1
                continue
        if k_type:
            t = str(r.get(k_type, '')).strip().lower()
            if t in SKIP_TYPE_CODES:
                skipped_type += 1
                continue
            # 只在类型码看起来是微信那套数字时才筛文本
            if t and re.fullmatch(r'\d+', t) and t not in TEXT_TYPE_CODES:
                skipped_type += 1
                continue
        dt = parse_time(r.get(k_time))
        if dt is None:
            skipped_time += 1
            continue
        who = None
        if k_self:
            v = str(r.get(k_self, '')).strip().lower()
            if v in ('1', 'true', 'yes', 'y', '是'):
                who = '我'
            elif v in ('0', 'false', 'no', 'n', '否'):
                who = 'TA'
        if who is None and k_sender:
            s = str(r.get(k_sender, '')).strip()
            who = '我' if any(n and n in s for n in self_names) else 'TA'
        if who is None:
            who = 'TA'
        c = str(r.get(k_content, ''))
        c = c.replace('\r', ' ').replace('\n', ' ').strip()
        if not c:
            continue
        out.append('%s | %s | %s' % (dt.strftime('%Y-%m-%d %H:%M'), who, c))

    out.sort()
    with open(dst, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    print('\n转换完成 → %s' % dst)
    print('  写入 %d 条' % len(out))
    if out:
        print('  时间范围 %s ~ %s' % (out[0][:16], out[-1][:16]))
        print('  你 %d 条 / TA %d 条' % (sum(' | 我 | ' in x for x in out),
                                        sum(' | TA | ' in x for x in out)))
    if skipped_time:
        print('  跳过 %d 条（时间认不出来）' % skipped_time)
    if skipped_type:
        print('  跳过 %d 条（非文本消息）' % skipped_type)
    if skipped_contact:
        print('  跳过 %d 条（不是「%s」这个会话）' % (skipped_contact, contact))
    print('\n接下来：python analyze.py "%s" 报告.html' % dst)


if __name__ == '__main__':
    main()
