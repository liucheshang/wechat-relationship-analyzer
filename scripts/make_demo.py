# -*- coding: utf-8 -*-
"""生成一份**完全虚构**的演示聊天记录，用来产出 docs/demo_report.html。

为什么要单独有这个文件：
    仓库里的示例报告必须是模拟数据，不能来自任何人的真实聊天记录。
    跑「make_demo.py + analyze.py」就能复现那份示例报告，数据可查、可复现。

用法：
    python make_demo.py                    # 生成 examples/demo_chat.txt + 刷新 docs/demo_report.html
    python make_demo.py 输出路径.txt        # 只生成聊天记录到指定位置

产出规模（固定随机种子，每次一样）：
    ~2 万条 / 约 550 天 / 一次 40 余天的长断联 / 上百段小摩擦
"""

import os
import random
import sys
from datetime import datetime, timedelta

SEED = 20240301
START = datetime(2024, 3, 1)
END = datetime(2025, 8, 31)

# ---- 关系分期 ----
# (名称, 起始日偏移, 结束日偏移, 甜度, 摩擦度, 她的主动度, 每天会话数分布)
# 索引:  0          1          2          3     4      5           6
PHASES = [
    ('热恋期', 0, 120, 0.80, 0.03, 0.65, [1, 2, 3, 4]),
    ('稳定期', 121, 260, 0.55, 0.10, 0.55, [1, 2, 2, 3]),
    ('摩擦期', 261, 330, 0.35, 0.50, 0.62, [1, 1, 2, 3]),
    ('断联期', 331, 371, 0.00, 0.00, 0.00, []),          # 40 天，一条不发
    ('复合期', 372, 450, 0.75, 0.18, 0.68, [1, 2, 3, 3]),
    ('平淡期', 451, 548, 0.42, 0.22, 0.52, [1, 1, 2, 2]),
]

# ---- 内容池：我（保温型 / 问句多 / 偏行动 / 回得慢） ----
ME = {
    'hi_am':    ['早', '起来没', '起来了吗', '上班了吗', '到公司了吗', '今天几点出门'],
    'hi_noon':  ['吃了吗', '中午吃啥了', '吃饭了没', '吃的什么'],
    'hi_pm':    ['在干嘛呢', '忙完了吗', '几点下班', '今天忙不忙', '在忙什么'],
    'hi_night': ['睡了没', '到家了吗', '早点睡', '我先睡了', '晚安'],
    'care':     ['今天累不累', '路上小心', '多穿点', '记得吃饭', '别熬夜了', '早点休息',
                 '喝点热水', '好点了吗', '吃药了吗', '要不我去接你', '外面下雨了带伞',
                 '别太拼了，身体要紧'],
    'plan':     ['几点的车', '我到车站了', '你在哪个口', '我过去找你', '出发了',
                 '堵车了可能晚点', '马上到', '周末出去玩不', '晚上吃什么', '看那个电影不'],
    'ask':      ['怎么不回我', '你在干嘛呀', '你怎么了呀', '我哪里做错了',
                 '你说话呀', '你怎么了', '在吗在吗', '我是不是说错话了', '你有空吗'],
    'sweet':    ['想你了', '抱抱', '爱你', '亲亲', '么么', '乖乖等我', '我也想你',
                 '今天特别想你', '宝贝早点睡'],
    'work':     ['今天加班', '领导又安排活了', '忙死了', '开了一天会', '客户太难缠了',
                 '到家再说', '刚忙完', '今天出差'],
    'soft':     ['对不起', '别生气了', '我说错什么了', '好，听你的', '嗯，我知道了',
                 '我改', '下次注意', '不是那个意思', '你别多想'],
    'argue':    ['算了', '随便你', '我也累了', '你能不能别这样', '你想多了',
                 '那你想我怎样', '我不想吵', '先这样吧', '等你气消了再说'],
}

# ---- 内容池：TA（情绪明牌 / 爱称与语气词多 / 长句倾述 / 回得快） ----
HER = {
    'hi_am':    ['刚醒呢', '我今天起晚了', '准备出门啦', '在上班路上呀', '刚到公司哈'],
    'hi_noon':  ['在吃饭呢', '刚点外卖呀', '你吃了没呀', '今天食堂好难吃哦'],
    'hi_pm':    ['在忙呢', '刚开完会哦', '在公司呀', '今天好忙哦', '刚忙完哈'],
    'hi_night': ['刚洗完澡哈', '还没睡呢', '刚下班哦', '在做饭呢', '你到家了嘛'],
    'care':     ['记得吃饭呀', '别熬夜了哦', '天冷多穿点呀', '到家跟我说一声', '我给你买了点吃的',
                 '你昨天没睡好，今天早点休息呀', '多喝热水哦', '外面降温了，出门加件衣服',
                 '我给你点了外卖，记得收'],
    'plan':     ['好呀', '可以呀', '那我们几点在哪见呀', '我收拾一下哈', '我快到了呢',
                 '你到了吗呀', '等我一下下嘛', '我想吃上次那家呀'],
    'sweet':    ['我也想你呀', '抱抱', '么么', '爱你哦', '好想你呀',
                 '你怎么这么好呀', '宝宝最好啦', '晚安哦', '亲亲嘛', '傻瓜'],
    'mood':     ['你都不理我', '我心里有点难受', '我好委屈', '我有点失望',
                 '你都不理我，我一个人在家好无聊', '你是不是有别的人了',
                 '我等你消息等了一下午，心里凉飕飕的', '你从来都不主动找我',
                 '你不喜欢我了是不是', '我难受的时候你在哪呀', '算了，我自己也可以的',
                 '我是不是很多余', '我越想越难过', '我好害怕你不要我',
                 '有时候真的挺郁闷的', '我心里好煎熬', '我最近好压抑'],
    'press':    ['那我们就别聊了', '算了分手吧', '你是不是不想过了', '我拉黑你了啊',
                 '你走吧', '那我不打扰你了', '我不管了', '随便你吧'],
    'tone':     ['嗯嗯', '好的呀', '哦哦', '是吧', '好嘛', '对呀', '知道啦', '行吧',
                 '哎呀', '真的呀', '可不嘛', '好哦', '嗯呢'],
    'daily':    ['今天同事又气我了', '我妈今天给我打电话了', '我买了个新杯子',
                 '我刚看完那个剧，结局好虐呀', '我同学下周结婚，你去不去呀',
                 '今天上班被领导说了一顿，好烦哦', '我今天走了两万步呢', '我头发剪短了一点',
                 '刚才门口那只猫又来了，蹲了半天'],
    'work':     ['今天开了三个会，累死了', '领导又给我加活了', '客户好难沟通哦',
                 '我明天要出差呢', '今天下班晚了一点', '工资到账啦'],
}

EMOJI = ['[旺柴]', '[捂脸]', '[拥抱]', '[破涕为笑]', '[让我看看]', '[呲牙]',
         '[玫瑰]', '[爱心]', '[大哭]', '[微笑]', '[流泪]', '[发怒]', '[心碎]',
         '[苦涩]', '[害羞]', '[撇嘴]', '[抠鼻]', '[得意]', '[偷笑]']

ME_NAME = ['宝宝', '宝贝', '亲爱的', '老婆']
HER_NAME = ['宝宝', '宝贝', '亲爱的', '老公']


def slot(hour):
    """把小时归到时段，让语料和说话时间对得上。"""
    if 6 <= hour < 11:
        return 'am'
    if 11 <= hour < 14:
        return 'noon'
    if 14 <= hour < 21:
        return 'pm'
    return 'night'


def pick(rng, pool):
    return pool[rng.randrange(len(pool))]


def gen_me(rng, ph, hour):
    sweet, friction = ph[3], ph[4]
    s = slot(hour)
    r = rng.random()
    if r < friction * 0.35:
        text = pick(rng, ME['argue'])
    elif r < friction * 0.35 + 0.08:
        text = pick(rng, ME['soft'])
    elif r < friction * 0.35 + 0.08 + sweet * 0.12:
        text = pick(rng, ME['sweet'])
    else:
        kinds = ['hi_' + s, 'care', 'plan', 'ask', 'work']
        w = [0.30, 0.24, 0.16, 0.18, 0.12]
        if s == 'night':
            w = [0.30, 0.26, 0.06, 0.22, 0.16]
        elif s == 'pm':
            w = [0.24, 0.20, 0.20, 0.20, 0.16]
        text = pick(rng, ME[rng.choices(kinds, w)[0]])
    if rng.random() < sweet * 0.07:
        text = text + '，' + rng.choice(ME_NAME)
    if rng.random() < 0.08:
        text = text + rng.choice(EMOJI)
    return text


def gen_her(rng, ph, hour):
    sweet, friction = ph[3], ph[4]
    s = slot(hour)
    r = rng.random()
    if r < friction * 0.45:
        text = pick(rng, HER['press'] if rng.random() < 0.30 else HER['mood'])
    elif r < friction * 0.45 + 0.10:
        text = pick(rng, HER['tone'])
    elif r < friction * 0.45 + 0.10 + sweet * 0.11:
        text = pick(rng, HER['sweet'])
    else:
        kinds = ['hi_' + s, 'care', 'plan', 'daily', 'work']
        w = [0.26, 0.22, 0.16, 0.24, 0.12]
        if s == 'night':
            w = [0.30, 0.24, 0.06, 0.26, 0.14]
        elif s == 'pm':
            w = [0.22, 0.18, 0.20, 0.26, 0.14]
        text = pick(rng, HER[rng.choices(kinds, w)[0]])
    if rng.random() < sweet * 0.08:
        text = text + '，' + rng.choice(HER_NAME)
    if rng.random() < 0.12:
        text = text + rng.choice(EMOJI)
    return text


def phase_of(day_idx):
    for ph in PHASES:
        if ph[1] <= day_idx <= ph[2]:
            return ph
    return PHASES[-1]


def gen():
    rng = random.Random(SEED)
    out = []
    day = START
    day_idx = 0
    while day <= END:
        ph = phase_of(day_idx)
        day_idx += 1
        if not ph[6]:                      # 断联期：一条消息都不发
            day += timedelta(days=1)
            continue
        # 有些天完全没聊（真实聊天本来就断断续续）
        if rng.random() < 0.12 + 0.15 * (1 - ph[3]):
            day += timedelta(days=1)
            continue

        n_sessions = rng.choice(ph[6])
        hours = sorted(rng.sample(range(7, 24), min(n_sessions, 17)))
        t = day.replace(hour=hours[0], minute=rng.randrange(0, 60), second=rng.randrange(0, 60))

        for si in range(n_sessions):
            if si > 0:
                t = t + timedelta(hours=rng.randint(3, 8), minutes=rng.randrange(0, 60))
                if t.hour > 23 or t.hour < 6:
                    t = t.replace(hour=rng.randrange(9, 22))
            n_msgs = rng.randint(4, 46)
            # 她更可能主动开场
            cur = 'her' if rng.random() < ph[5] else 'me'
            for _ in range(n_msgs):
                text = gen_her(rng, ph, t.hour) if cur == 'her' else gen_me(rng, ph, t.hour)
                out.append((t, cur, text))
                # 连发：同一人接着发；我回得慢，她回得快
                if rng.random() < (0.34 if cur == 'her' else 0.24):
                    t = t + timedelta(seconds=rng.randint(15, 240) if cur == 'her'
                                      else rng.randint(40, 600))
                    continue
                cur = 'me' if cur == 'her' else 'her'
                t = t + timedelta(seconds=rng.randint(60, 900) if cur == 'me'
                                  else rng.randint(30, 420))
            if t.day != day.day:
                break
        day += timedelta(days=1)

    out.sort(key=lambda x: x[0])
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_txt = os.path.join(root, 'examples', 'demo_chat.txt')
    dst = sys.argv[1] if len(sys.argv) > 1 else default_txt
    d = os.path.dirname(os.path.abspath(dst))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

    rows = gen()
    with open(dst, 'w', encoding='utf-8') as f:
        for dt, who, content in rows:
            f.write('%s | %s | %s\n' % (dt.strftime('%Y-%m-%d %H:%M:%S'),
                                        '我' if who == 'me' else 'TA', content))
    me = sum(1 for r in rows if r[1] == 'me')
    print('已生成模拟聊天记录: %s' % dst)
    print('  共 %d 条（我 %d / TA %d），%s ~ %s' % (
        len(rows), me, len(rows) - me,
        rows[0][0].strftime('%Y-%m-%d'), rows[-1][0].strftime('%Y-%m-%d')))
    print('  这份数据是随机生成的，与任何真实聊天记录无关。')

    # 没指定输出路径时，顺手把示例报告也刷一遍，保证「数据 → 报告」可复现
    if dst == default_txt:
        build_report(dst, os.path.join(root, 'docs', 'demo_report.html'))


def build_report(txt, out):
    """用 analyze.py 跑出示例报告；图表走 CDN，标题标「示例」。"""
    import importlib.util
    import re
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location('_relanalyze',
                                                 os.path.join(here, 'analyze.py'))
    A = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(A)

    msgs, raw, dropped = A.parse(txt)
    if len(msgs) < 50:
        print('  跳过报告: 有效消息不足')
        return
    sessions = A.build_sessions(msgs)
    D = A.compute(msgs, sessions)
    meta = {'msgs': msgs,
            'me': [m for m in msgs if m['sender'] == 'me'],
            'her': [m for m in msgs if m['sender'] == 'her'],
            'raw': format(raw, ','), 'dropped': format(dropped, ','), 'path': txt}
    T = A.render(D, meta)
    with open(os.path.join(here, 'report_template.html'), encoding='utf-8') as f:
        html = f.read()
    for k, v in T.items():
        ph = '{{' + k + '}}'
        if ph in html:
            html = html.replace(ph, v)
    left = sorted(set(re.findall(r'\{\{[A-Z0-9_]+\}\}', html)))
    if left:
        print('  警告: 有 %d 个占位符未替换: %s' % (len(left), ', '.join(left[:8])))

    # 示例报告只在页面上用 CDN 加载图表，不把 1MB 的 echarts 塞进仓库
    html = html.replace('<script src="echarts.min.js"></script>',
                        '<script src="https://cdn.jsdelivr.net/npm/'
                        'echarts@5/dist/echarts.min.js"></script>')
    html = re.sub(r'<script>if\(!window\.echarts\)\{document\.write\(.*?</script>\s*',
                  '', html, flags=re.S)
    html = html.replace('<title>亲密关系深度分析报告</title>',
                        '<title>亲密关系深度分析报告 · 示例</title>')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print('示例报告已更新: %s' % out)
    print('  （内容全部来自上面那份模拟数据，与真实聊天记录无关）')


if __name__ == '__main__':
    main()
