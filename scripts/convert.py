# -*- coding: utf-8 -*-
"""
convert.py —— 把别的工具导出的聊天记录，转成 analyze.py 能吃的格式。

analyze.py 只认这种一行一条的纯文本：
    2025-06-01 05:39 | 我 | 出发没
    2025-06-01 05:41 | TA | 到啦

而各个导出工具（WeChatMsg / chatlog / 留痕 / 各种搬运脚本）吐出来的
是 CSV 或 JSON，字段名五花八门。这个脚本负责自动认字段、自动认时间格式，
转成上面的格式。

用法：
    python convert.py 导出文件.json 聊天记录.txt
    python convert.py 导出文件.csv  聊天记录.txt
    python convert.py 导出文件.csv  聊天记录.txt --contact 小美
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

# 微信消息类型码 → 占位符文本
MSG_TYPE_MAP = {
    '1': None,        # 文本，保留原内容
    '3': '[图片]',
    '34': '[语音]',
    '43': '[视频]',
    '47': '[动画表情]',
    '49': '[链接]',
    '50': '[通话]',
    '10000': None,    # 系统消息：撤回 / 拍一拍原文要保留，分析器靠它统计
}
SKIP_TYPE_CODES = {'10002'}   # 只有撤回提示这种纯系统噪声才跳过


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


def convert_file(src, dst, contact=None, self_names=None, log=print):
    """把 src 转成 analyze.py 认的格式，写到 dst。返回统计 dict，失败抛 ValueError。"""
    if self_names is None:
        self_names = ['我', '自己', 'me', 'self', '我(发送)', '本人', '我本人']

    if not os.path.exists(src):
        raise ValueError('找不到文件：%s' % src)

    text = read_any(src).strip()
    if not text:
        raise ValueError('文件是空的。')

    if text[0] in '[{':
        rows = rows_from_json(text)
    else:
        rows = rows_from_csv(text)

    if not rows or not isinstance(rows[0], dict):
        raise ValueError('读出来的不是消息列表，前 200 个字符长这样：\n%s' % text[:200])

    sample = rows[0]
    k_time, _ = pick(sample, TIME_KEYS)
    k_self, _ = pick(sample, SELF_KEYS)
    k_sender, _ = pick(sample, SENDER_KEYS)
    k_content, _ = pick(sample, CONTENT_KEYS)
    k_type, _ = pick(sample, TYPE_KEYS)
    k_room, _ = pick(sample, ROOM_KEYS)

    log('识别到的字段：')
    log('  时间   → %s' % (k_time or '❌ 没认出来'))
    log('  内容   → %s' % (k_content or '❌ 没认出来'))
    log('  发送者 → %s' % (k_self or k_sender or '❌ 没认出来（默认全部记为 TA）'))
    log('  类型   → %s' % (k_type or '（没有，不过滤）'))
    log('  会话   → %s' % (k_room or '（没有，不筛选）'))
    log('共 %d 行' % len(rows))

    if not k_time or not k_content:
        raise ValueError('关键字段没认全，没法转。把文件头几行发我，我给你加规则。')

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
            # 非文本消息不跳过，替换成占位符；文本(1)与系统原文保留
            if t in MSG_TYPE_MAP:
                ph = MSG_TYPE_MAP[t]
                if ph is None:
                    c = str(r.get(k_content, ''))
                    # 系统消息里的 XML：取出 <content> 正文（撤回/拍一拍通知在里面），
                    # 纯噪声才降级为 [其他]
                    if c.lstrip().startswith('<'):
                        mm = re.search(r'<content>(.*?)</content>', c, re.S)
                        c = mm.group(1).strip() if mm else '[其他]'
                else:
                    c = ph
            elif t and re.fullmatch(r'\d+', t):
                c = '[其他]'
            else:
                c = str(r.get(k_content, ''))
        else:
            c = str(r.get(k_content, ''))
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
        c = c.replace('\r', ' ').replace('\n', ' ').strip()
        if not c:
            continue
        out.append('%s | %s | %s' % (dt.strftime('%Y-%m-%d %H:%M'), who, c))

    out.sort()
    with open(dst, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    stat = {'rows': len(rows), 'written': len(out), 'skipped_time': skipped_time,
            'skipped_type': skipped_type, 'skipped_contact': skipped_contact,
            'me': sum(' | 我 | ' in x for x in out),
            'ta': sum(' | TA | ' in x for x in out),
            'first': out[0][:16] if out else '', 'last': out[-1][:16] if out else ''}
    log('转换完成 → %s' % dst)
    log('  写入 %d 条' % stat['written'])
    if out:
        log('  时间范围 %s ~ %s' % (stat['first'], stat['last']))
        log('  你 %d 条 / TA %d 条' % (stat['me'], stat['ta']))
    if skipped_time:
        log('  跳过 %d 条（时间认不出来）' % skipped_time)
    if skipped_type:
        log('  跳过 %d 条（非文本消息）' % skipped_type)
    if skipped_contact:
        log('  跳过 %d 条（不是「%s」这个会话）' % (skipped_contact, contact))
    return stat


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    src, dst = sys.argv[1], sys.argv[2]
    contact = None
    self_names = None
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

    try:
        convert_file(src, dst, contact, self_names)
    except ValueError as e:
        print('\n%s' % e)
        sys.exit(1)
    print('\n接下来：python analyze.py "%s" 报告.html' % dst)


if __name__ == '__main__':
    main()
