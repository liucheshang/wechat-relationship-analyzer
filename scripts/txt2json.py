#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
兜底工具：把「纯文本 / CSV 聊天记录」转成分析脚本能吃的 JSON。

什么时候用它？
  拿不到密钥、或者不想用调试器的时候，你可以用别的方式弄到聊天记录文本
  （手机微信导出、手动复制、第三方工具导出的 txt/csv），
  先用这个脚本转成标准格式，后面三个分析脚本照样能跑。

支持三种输入（自动识别）：

  A. 微信「导出聊天记录」风格
        2024-09-19 22:03:04 暖木
        在吗
        2024-09-19 22:04:11 宝儿
        怎么了

  B. 一行一条风格（时间 + 人 + 冒号 + 内容）
        2024-09-19 22:03:04 暖木: 在吗
        2024-09-19 22:04:11 宝儿: 怎么了

  C. CSV（带表头，列名会智能识别）
        time,sender,content
        2024-09-19 22:03:04,暖木,在吗

用法：
    python txt2json.py --src 记录.txt --out wechat_messages.json --me 暖木
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ap = argparse.ArgumentParser(description='把 txt/csv 聊天记录转成分析脚本可用的 JSON')
ap.add_argument('--src', required=True, help='输入的 txt 或 csv 文件')
ap.add_argument('--out', required=True, help='输出的 wechat_messages.json')
ap.add_argument('--me', required=True, help='你自己的显示名（在记录里出现的那个）')
ap.add_argument('--other', default='', help='对方显示名（可留空，自动取出现最多的另一个名字）')
ap.add_argument('--me-left', action='store_true',
                help='记录里你自己在左边（默认按 --me 的名字判断，不依赖位置）')
A = ap.parse_args()

# --------------------------------------------------------------- 时间解析
TIME_PATS = [
    (re.compile(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日]?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?'), 'ymdhms'),
    (re.compile(r'(\d{4})(\d{2})(\d{2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?'), 'ymdhms'),
    (re.compile(r'(\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?'), 'mdhms'),
]


def parse_time(s):
    for pat, kind in TIME_PATS:
        m = pat.search(s)
        if not m:
            continue
        g = m.groups()
        try:
            if kind == 'ymdhms':
                y, mo, d, h, mi, sec = (int(g[0]), int(g[1]), int(g[2]),
                                        int(g[3]), int(g[4]), int(g[5] or 0))
            else:
                y, mo, d, h, mi, sec = (datetime.now().year, int(g[0]), int(g[1]),
                                        int(g[2]), int(g[3]), int(g[4] or 0))
            return datetime(y, mo, d, h, mi, sec).timestamp(), m
        except ValueError:
            continue
    return None, None


# --------------------------------------------------------------- 读取
path = A.src
enc = None
for e in ('utf-8-sig', 'utf-8', 'gbk', 'gb18030', 'utf-16'):
    try:
        text = open(path, encoding=e).read()
        enc = e
        break
    except (UnicodeDecodeError, UnicodeError):
        continue
if enc is None:
    sys.exit('无法识别文件编码，请另存为 UTF-8 后重试')
print('编码：%s' % enc)

lines = text.split('\n')
print('总行数：%d' % len(lines))

records = []

# ---- 先试 CSV ----
if path.lower().endswith('.csv') or (lines and ',' in lines[0] and ':' not in lines[0][:20]):
    try:
        rows = list(csv.reader(io.StringIO(text)))
        if rows:
            hdr = [h.strip().lower() for h in rows[0]]
            def col(*names):
                for n in names:
                    for i, h in enumerate(hdr):
                        if n in h:
                            return i
                return None
            ci_t, ci_s, ci_c = col('time', 'date', '时间', '日期'), col('sender', 'from', '发送', '昵称', 'who'), col('content', 'msg', 'text', '内容', '消息')
            if ci_t is not None and ci_c is not None:
                for r in rows[1:]:
                    if len(r) <= max(ci_t, ci_c):
                        continue
                    ts, _ = parse_time(r[ci_t])
                    if ts is None:
                        continue
                    sender = r[ci_s].strip() if ci_s is not None and len(r) > ci_s else '未知'
                    records.append((ts, sender, r[ci_c]))
                print('按 CSV 解析：%d 条' % len(records))
    except Exception as e:
        print('CSV 解析失败（忽略）：%s' % e)

# ---- 试「头部行 + 正文行」交错格式（微信导出风格 A）----
if not records:
    cur = None
    for ln in lines:
        s = ln.rstrip('\r')
        st = s.strip()
        if not st:
            continue
        ts, m = parse_time(st)
        # 判定为头部：有时间，且时间后面还有别的东西（名字），且不是「名字: 内容」
        if ts is not None:
            rest = st.replace(m.group(0), '', 1).strip(' ]\t')
            if rest and not re.match(r'^[:：]', rest) and len(rest) <= 24 and ':' not in rest and '：' not in rest:
                cur = [ts, rest, []]
                records.append(cur)
                continue
        if cur is not None:
            cur[2].append(st)
        # 没有头部就丢弃
    records = [(t, n, '\n'.join(c)) for t, n, c in records]
    if records:
        print('按「头部+正文」格式解析：%d 条' % len(records))

# ---- 试「一行一条」（风格 B）----
if not records:
    for ln in lines:
        st = ln.strip()
        if not st:
            continue
        ts, m = parse_time(st)
        if ts is None:
            continue
        rest = st[m.end():].strip(' ]\t')
        mm = re.match(r'^(.*?)\s*[:：]\s*(.*)$', rest)
        if not mm:
            continue
        records.append((ts, mm.group(1).strip(), mm.group(2)))
    if records:
        print('按「一行一条」格式解析：%d 条' % len(records))

if not records:
    sys.exit('解析不出任何消息。请检查文件格式，或者先把前 10 行贴给 AI 让它写个专用解析。')

# --------------------------------------------------------------- 输出
records.sort(key=lambda x: x[0])

# 推断对方是谁
names = {}
for _, n, _ in records:
    names[n] = names.get(n, 0) + 1
other = A.other
if not other:
    cand = [n for n in names if n != A.me]
    if cand:
        other = max(cand, key=lambda n: names[n])
    else:
        sys.exit('记录里找不到 --me 指定的名字「%s」。出现的名字有：%s' % (A.me, list(names)))

print('识别到的说话人：%s' % names)
print('本人 = %s   对方 = %s' % (A.me, other))

out = []
for ts, n, c in records:
    is_self = (n == A.me)
    out.append({
        'ts': int(ts),
        'sender': n,
        'sender_wxid': None,
        'chat_room': None,
        'conversation_id': other,
        'content': c,
        'msg_type': 1,                 # 纯文本一律按文本处理
        'is_self': is_self,
        'account_id': None,
        'thread_id': None,
        'server_id': None,
        'source_offset': None,
        'conversation_type': 'direct',
        'is_group_chat': False,
    })

os.makedirs(os.path.dirname(os.path.abspath(A.out)) or '.', exist_ok=True)
json.dump(out, open(A.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

me_n = sum(1 for x in out if x['is_self'])
print('\n写出 -> %s' % A.out)
print('  共 %d 条（本人 %d / 对方 %d）' % (len(out), me_n, len(out) - me_n))
print('  时间范围：%s ~ %s' % (
    datetime.fromtimestamp(out[0]['ts']).strftime('%Y-%m-%d %H:%M'),
    datetime.fromtimestamp(out[-1]['ts']).strftime('%Y-%m-%d %H:%M')))
print('\n⚠️ 图片/语音/表情在这里都变成了空内容或被丢弃，'
      '所以「消息类型分布」「表情统计」这类指标会失真 —— 只有文字统计是准的。')
print('\n下一步：')
print('  python analyze_full.py --src "%s" --out "full_stats.json" --me %s --other %s' % (A.out, A.me, other))
