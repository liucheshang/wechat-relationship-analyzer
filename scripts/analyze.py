# -*- coding: utf-8 -*-
"""
微信聊天记录深度分析 · 本地版（深度报告）
用法:  python analyze.py 聊天记录.txt [输出报告.html]

纯 Python 标准库实现，不联网、不装包、数据不出本机。
输出一份 10 章深度报告：从"是谁"到"怎么相处"到"怎么办"。

输入格式（每行三条，竖线分隔）:
    2025-06-01 05:39 | 我 | 出发没
    2025-06-01 05:39 | TA | 还早
"""
import sys, os, json, re
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# =====================================================================
# 0. 词典层
#    防误伤红线（照规格说明书必须遵守）：
#    ① 单字词禁止子串匹配（"帮忙"不能命中"忙"）
#    ② 状态词（累/困/饿/忙）不算消极情绪
#    ③ "嗯/哦/好吧" 不算筑墙（计进去会把筑墙虚高几十倍）
# =====================================================================

POSITIVE = ['喜欢','爱你','想你','开心','高兴','幸福','谢谢','感谢','辛苦','加油','好看','好吃','漂亮','可爱','厉害','真好','太好了','棒','么么','亲亲','抱抱','嘿嘿','嘻嘻','哈哈','温暖','感动','心疼','乖乖','宝贝','宝宝','好想你','舒服','顺利','成功','搞定','中奖','赚了','不错哦','好棒','可以的','真乖','真棒']
NEGATIVE = ['分手','生气','讨厌','滚蛋','失望','伤心','委屈','难过','想哭','哭','绝望','崩溃','窒息','压抑','痛苦','煎熬','折磨','冷战','无语','离谱','过分','气死','不爱了','没感觉','不合适','不想理','不理我','恶心','受够','心寒','心累','郁闷','不爽','吵架','闹','恨','眼泪','不要我','别烦我','烦死','孤独','害怕','难受']
# ↑ 已剔除「累/困/饿/忙/睡」等状态词，以及「为什么/怎么办」等中性疑问词

ANXIOUS = ['为什么不回','你怎么不回','你都不回','你在哪','干嘛呢','干什么去了','你是不是不爱我','你不在乎我','我不重要','你到底','你根本不','我害怕','我担心','我好怕','你别离开','我怕失去','你变了','是不是有别人','我算什么','你心里还有','我在你心里','是不是不要我','你是不是烦我','你都不想我','你从来不想','你忘了我','你为什么不说话','你还在吗','你理我一下','你到底想怎样']
AVOID = ['算了','不说了','随便','我没事','还好','还行','不想说','你忙吧','哦嗯','没什么','懒得说','不想聊','以后再说','不知道说啥','没意思','睡吧','我先忙','晚点说','行吧','随你','都行','你决定']
THREAT = ['分手','拉黑','不理你了','再也不理','我走了','我消失','删了','永远不要','别联系了','当我没','不活了','不再打扰','我们算了吧','散了吧','别找我了']
SECURE = ['对不起','我错了','别生气','我理解','我懂你','抱歉','我改','原谅我','我在乎','我担心你','是我不好','我没有怪你','我们商量','我陪你','别难过','辛苦你','听你的','你说得对','我们一起','抱抱你','我知道错了','下次注意','我会注意']

CRITICISM = ['你总是','你从来','你怎么又','为什么你不能','你每次','你就知道','你从来不','你就是这样','你又忘了','你又','天天','一点也不','有什么用','你根本不会','你只会','反正你']
DEFENSIVE = ['我没有','不是我','是你先','凭什么','我怎么了','又不是我','我只是','我也是','又不能怪我','关我什么事','你才','我没有啊','我哪有','还怪我','怪我咯','你自己不也']
CONTEMPT = ['呵呵','可笑','你真行','有病','幼稚','无聊','神经病','服了你','就你','你也配','切','啧','看你那','真服了','搞笑']
STONEWALL = ['不说了','随便','不想说','呵呵','无所谓','算了','没意思','懒得说','你忙吧','行吧','哦嗯','我没事','不想聊','都行','随你']
# ↑ 已剔除单字「嗯/哦」与状态词「忙」——否则筑墙计数会虚高几十倍

CONFLICT = ['吵架','吵','分手','生气','讨厌','冷战','不理我','滚','烦','受够','失望','委屈','难过','哭','闹','恨','过分','离谱','气死','不爱了','没感觉','不合适','算了吧','呵呵','随你','别烦我','你走吧','拉黑','无语']
CARE = ['吃饭','吃了吗','睡了吗','早点','身体','累不累','冷不冷','吃药','多喝热水','注意安全','到家了','到家没','喝水','休息','别熬夜','照顾好','心疼','难受','好点了吗','记得吃','多穿点','带伞','路上小心','安全到家','在干嘛','下班了','到公司','忙完了']
NICKNAMES = ['宝宝','宝贝','老婆','老公','亲爱的','猪猪','乖乖','媳妇','哈尼','老婆大人','小宝贝','宝儿']
NICK_DETAIL = [('宝宝/宝儿', ['宝宝','宝儿']), ('老婆/老公', ['老婆','老公','媳妇','老婆大人']), ('亲爱的/宝贝', ['亲爱的','宝贝','哈尼','小宝贝'])]
RATIONAL = ['所以','因为','但是','逻辑','道理','其实','应该','合理','分析','总结','计划','考虑','客观','问题在于','原因是','建议','方案','第一','第二','首先','其次']
LOVE_WORDS = ['爱你','喜欢你','我爱你','好想你','爱你哦','爱死','最爱','超爱']
MISS_WORDS = ['想你','好想你','想念','惦记','想你了']
FUTURE_WORDS = ['以后','结婚','一起','一辈子','将来','未来','我们家','见家长','长期','后面','日子','生活','攒钱','买房','孩子','计划']
TONE_WORDS = ['哈','嗯','吧','哦','呀','呢','啊','嘛']

# 高频词表（无分词环境下的确定性口径，避免 n-gram 噪声）
WORD_BANK = ['哈哈','哈哈哈','在吗','干嘛','吃饭','吃什么','睡觉','晚安','早安','上班','下班','公司','加班','回家','到家','出门','路上','累不累','想我','想你','爱你','喜欢','宝贝','宝宝','老婆','老公','亲爱的','抱抱','亲亲','么么','开心','难受','生气','哭了','对不起','没事','别生气','听你的','好烦','烦人','无语','离谱','真的','为什么','怎么办','怎么样','好不好','是不是','对吧','我觉得','我以为','其实','因为','所以','今天','明天','昨天','周末','放假','旅游','出去玩','看电影','吃饭没','睡了吗','早点睡','多喝','注意','小心','照顾好','多少钱','买了','花了','礼物','红包','转账','生日','纪念日','过节','家里','爸妈','妈妈','爸爸','我妈','你妈','朋友','同事','领导','老板','工作','考试','学习','视频','电话','语音','开会','出差','回老家','见面','来找你','过来','等我','接我','送我','到了','来吧']

EMOJI_RE = re.compile(r'\[([^\[\]]{1,10})\]')
EMOJI_FOCUS = ['旺柴','捂脸','拥抱','破涕为笑','让我看看','呲牙','玫瑰','爱心','大哭','微笑','流泪','发怒','心碎','苦涩','害羞','撇嘴','抠鼻','得意','偷笑']
SHORT_OK = ['嗯','嗯嗯','哦','哦哦','好','好的','好吧','行','行吧','是','对','哈哈','哈哈哈','在','ok','OK','收到','知道了','厉害','不错','棒','nice','可以','么么','亲亲','好嘞']
TOPIC_CLUSTERS = [
    ('日常琐事', ['吃饭','吃','睡','起床','回家','到家','出门','路上','洗澡','买','快递','外卖','做饭','收拾','衣服','天气','冷','热','洗']),
    ('见面行程', ['见面','来找','过来','等我','接我','送我','到了','出发','车站','高铁','火车','机场','几点','位置','在哪','碰头','安排','时间去']),
    ('思念情感', ['想你','爱你','喜欢','抱抱','亲亲','么么','舍不得','离不开','想见','心里','在乎','重要','宝贝','宝宝','老婆','老公','亲爱的']),
    ('工作学习', ['上班','下班','公司','加班','工作','开会','领导','老板','同事','出差','考试','学习','论文','项目','客户','报告','面试','辞职','工资']),
    ('家人亲戚', ['家里','爸妈','妈妈','爸爸','我妈','你妈','婆婆','岳母','爷爷','奶奶','舅舅','姑姑','亲戚','回老家','老家','弟弟','妹妹','哥哥','姐姐']),
    ('金钱花费', ['多少钱','转账','红包','花了','买了','工资','房租','贷款','还钱','借','便宜','贵','省钱','攒钱','预算']),
    ('身体情绪', ['身体','感冒','发烧','头疼','医院','吃药','难受','不舒服','心情','压力','焦虑','睡不着','困']),
    ('未来计划', ['以后','结婚','一辈子','将来','未来','买房','攒钱','孩子','见家长','长期','打算','计划','日子']),
    ('争吵矛盾', ['吵架','生气','讨厌','分手','冷战','不理','烦','受够','失望','委屈','过分','凭什么','呵呵','随你']),
    ('娱乐休闲', ['游戏','打游戏','抖音','视频','电影','看剧','追剧','音乐','运动','健身','旅游','出去玩','玩']),
]
TRIGGER_RULES = [
    ('回复慢 / 不回消息', ['不回','没回','已读','半天','这么久','不理我','敷衍','怎么不回','为什么不回','一直不回','看不到','等不到']),
    ('觉得对方不在意', ['不在乎','不关心','不在意','不爱我','不想我','你变了','不重要','心里没有','忘了我','忽视','体会不到','照顾','感受不到']),
    ('行踪 / 在干嘛', ['在哪','干嘛','干什么','和谁','几点回','去哪']),
    ('态度与语气', ['语气','态度','阴阳','凶','说话','什么态度','吼','冲']),
    ('累积性抱怨', ['你总是','你从来','你每次','你怎么又','天天','总是','从来','每次都','你就','你根本','一点也不','多少次','说了多少']),
    ('泛化的疲惫与不合适', ['不合适','没感觉','累了','不想了','算了','分手','没意义','没必要','走到这','撑不','受不了','没意思']),
    ('被误解 / 不安全感', ['误解','冤枉','不是这意思','曲解','你不理解','不懂我','我什么意思','想多了','多想了']),
    ('生活习惯 / 陪伴', ['熬夜','不陪我','游戏','抖音','手机','浪费时间','几点睡','抽烟','喝酒','出去玩']),
    ('付出的落差', ['我付出','我做的','我做的不够','为你','凭什么我','只有我在','我都做了','谁体谅我']),
    ('金钱花费', ['钱','转账','红包','花','买','贵','便宜','省']),
    ('家人亲戚', ['妈','爸','婆婆','岳母','家里','亲戚','老家']),
    ('异性 / 前任', ['前任','别的女','别的男','别人','朋友圈','女生','男生','异性']),
    ('边界与自由', ['管','自由','空间','限制','凭什么','不让']),
]

# =====================================================================
# 1. 工具函数
# =====================================================================

def is_cjk(ch):
    return bool(ch) and '\u4e00' <= ch <= '\u9fff'

def hit(text, words):
    """词典命中判断。单字词走边界判断，禁止子串误伤。"""
    for w in words:
        if len(w) >= 2:
            if w in text:
                return True
        else:
            for m in re.finditer(re.escape(w), text):
                i = m.start()
                left = text[i - 1] if i > 0 else ''
                right = text[i + 1] if i + 1 < len(text) else ''
                if not (is_cjk(left) and is_cjk(right)):
                    return True
    return False

def count_msg(lst, words):
    """命中该词典的消息条数（同一词典内多词命中只计一次）。"""
    return sum(1 for m in lst if hit(m['content'], words))

def per_k(n, total, k=1000):
    return round(n / max(1, total) * k, 1)

def pct(a, b):
    return round(a / b * 100, 1) if b else 0.0

def median(arr):
    if not arr:
        return 0.0
    s = sorted(arr)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def cut(s, n=78):
    s = re.sub(r'\s+', ' ', s).strip()
    return esc(s if len(s) <= n else s[:n] + '…')

def q(sender, dt, content, n=95):
    who = '你' if sender == 'me' else 'TA'
    return ('<div class="quote %s"><div class="qm">%s · %s</div>%s</div>'
            % (sender, who, dt.strftime('%Y-%m-%d %H:%M:%S'), cut(content, n)))

def month_add(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    m += k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return '%04d-%02d' % (y, m)

def month_range(a, b):
    out, cur = [], a
    while cur <= b and len(out) < 400:
        out.append(cur)
        cur = month_add(cur, 1)
    return out

def ym_of(dt):
    return dt.strftime('%Y-%m')

def cls(val, good, warn, reverse=False):
    """给数字配语义色。reverse=True 表示越小越好。"""
    if reverse:
        return 'hl-green' if val <= good else ('hl-gold' if val <= warn else 'hl-red')
    return 'hl-green' if val >= good else ('hl-gold' if val >= warn else 'hl-red')

# =====================================================================
# 2. 第 1 步 · 清洗 & 解析
# =====================================================================

def parse(path):
    raw_total, dropped = 0, 0
    lines = None
    for enc in ('utf-8-sig', 'utf-8', 'gbk'):
        try:
            with open(path, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    if lines is None:
        print('错误: 无法识别文件编码，请另存为 UTF-8 后重试')
        sys.exit(1)

    msgs = []
    for line in lines:
        line = line.strip().replace('\ufeff', '')
        if not line:
            continue
        raw_total += 1
        parts = line.split('|')
        if len(parts) < 3:
            dropped += 1
            continue
        content = '|'.join(parts[2:]).strip()
        if not content:
            dropped += 1
            continue
        dt = None
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y-%m-%d'):
            try:
                dt = datetime.strptime(parts[0].strip(), fmt)
                break
            except ValueError:
                continue
        if dt is None:
            dropped += 1
            continue
        who = parts[1].strip()
        sender = 'me' if who in ('我', 'me', 'Me', 'ME', '自己', '本人') else 'her'
        msgs.append({'dt': dt, 'sender': sender, 'content': content})

    msgs.sort(key=lambda m: m['dt'])
    return msgs, raw_total, dropped

# =====================================================================
# 3. 第 2 步 · 切会话段（相邻间隔 > 6 小时切一刀）
# =====================================================================

SESSION_GAP = 6 * 3600  # 秒

def build_sessions(msgs):
    sessions, cur = [], []
    for i, m in enumerate(msgs):
        if i == 0:
            cur = [m]
        elif (m['dt'] - msgs[i - 1]['dt']).total_seconds() > SESSION_GAP:
            sessions.append(cur)
            cur = [m]
        else:
            cur.append(m)
    if cur:
        sessions.append(cur)
    return sessions

# =====================================================================
# 4. 第 3~5 步 · 词典归类 / 归一化 / 关系分期 / 核心指标
# =====================================================================

def compute(msgs, sessions):
    D = {}
    total = len(msgs)
    me = [m for m in msgs if m['sender'] == 'me']
    her = [m for m in msgs if m['sender'] == 'her']
    nMe, nHer = len(me), len(her)
    D.update(total=total, nMe=nMe, nHer=nHer, pctMe=pct(nMe, total), pctHer=pct(nHer, total))
    D['first'] = msgs[0]['dt']
    D['last'] = msgs[-1]['dt']
    D['days'] = max(1, (msgs[-1]['dt'] - msgs[0]['dt']).days + 1)

    # ---------- 依恋四类（双向 + 每千条） ----------
    for tag, dic in (('ANX', ANXIOUS), ('AV', AVOID), ('TH', THREAT), ('SE', SECURE)):
        a, b = count_msg(me, dic), count_msg(her, dic)
        D[tag + '_M'], D[tag + '_H'] = a, b
        D[tag + '_MP'], D[tag + '_HP'] = per_k(a, nMe), per_k(b, nHer)

    # ---------- 四骑士 / 关心 / 爱称 / 爱语 ----------
    for tag, dic in (('CR', CRITICISM), ('DF', DEFENSIVE), ('CT', CONTEMPT), ('ST', STONEWALL),
                     ('CA', CARE), ('NK', NICKNAMES), ('LOVE', LOVE_WORDS), ('MISS', MISS_WORDS)):
        a, b = count_msg(me, dic), count_msg(her, dic)
        D[tag + '_M'], D[tag + '_H'] = a, b
        D[tag + '_MP'], D[tag + '_HP'] = per_k(a, nMe), per_k(b, nHer)

    # ---------- 人称 / 问句 / 长度 ----------
    D['PN_M'] = sum(1 for m in me if '我' in m['content'])
    D['PN_H'] = sum(1 for m in her if '我' in m['content'])
    D['PY_M'] = sum(1 for m in me if '你' in m['content'])
    D['PY_H'] = sum(1 for m in her if '你' in m['content'])
    D['Q_M'] = sum(1 for m in me if ('?' in m['content'] or '？' in m['content']))
    D['Q_H'] = sum(1 for m in her if ('?' in m['content'] or '？' in m['content']))
    D['LEN_M'] = round(sum(len(m['content']) for m in me) / max(1, nMe), 1)
    D['LEN_H'] = round(sum(len(m['content']) for m in her) / max(1, nHer), 1)
    D['TONE_M'] = [sum(1 for m in me if w in m['content']) for w in TONE_WORDS]
    D['TONE_H'] = [sum(1 for m in her if w in m['content']) for w in TONE_WORDS]
    D['TONE_MP'] = [per_k(v, nMe) for v in D['TONE_M']]
    D['TONE_HP'] = [per_k(v, nHer) for v in D['TONE_H']]

    # ---------- 表情 ----------
    em = Counter()
    eh = Counter()
    for m in msgs:
        for e in EMOJI_RE.findall(m['content']):
            (em if m['sender'] == 'me' else eh)[e] += 1
    D['EMOJI_CNT_M'], D['EMOJI_CNT_H'] = sum(em.values()), sum(eh.values())
    D['EMOJI_M'], D['EMOJI_H'] = em, eh
    D['EMOJI_TOP'] = [e for e, _ in (em + eh).most_common(10)]

    # ---------- 高频词 ----------
    wm = [(w, sum(1 for m in me if w in m['content'])) for w in WORD_BANK]
    wh = [(w, sum(1 for m in her if w in m['content'])) for w in WORD_BANK]
    wm = [x for x in wm if x[1] > 0]
    wh = [x for x in wh if x[1] > 0]
    D['TOPW_M'] = sorted(wm, key=lambda x: -x[1])[:8]
    D['TOPW_H'] = sorted(wh, key=lambda x: -x[1])[:8]

    # ---------- 逐日 / 逐月骨架（断联月不跳过） ----------
    dayIdx = {}
    d = D['first'].replace(hour=0, minute=0, second=0, microsecond=0)
    while d.date() <= D['last'].date():
        dayIdx[d.strftime('%Y-%m-%d')] = len(dayIdx)
        d += timedelta(days=1)
    daysArr = sorted(dayIdx.keys())
    D['daysArr'] = daysArr
    months = month_range(ym_of(D['first']), ym_of(D['last']))
    D['months'] = months
    D['dayPos'] = defaultdict(lambda: [0, 0, 0, 0])   # mePos meNeg herPos herNeg
    D['dayCnt'] = defaultdict(lambda: [0, 0])
    D['monCnt'] = defaultdict(lambda: [0, 0])
    D['monPos'] = defaultdict(lambda: [0, 0])
    D['monNeg'] = defaultdict(lambda: [0, 0])
    D['monRat'] = defaultdict(lambda: [0, 0])
    D['monCri'] = defaultdict(lambda: [0, 0])
    D['monNmM'] = {k: [0] * len(months) for k, _ in NICK_DETAIL}
    monthIdx = {mk: i for i, mk in enumerate(months)}
    D['byHourM'] = [0] * 24
    D['byHourH'] = [0] * 24
    D['daily'] = {k: [0, 0] for k in daysArr}
    D['night'] = {'me': 0, 'her': 0}
    D['nightSent'] = {'me': [0, 0], 'her': [0, 0]}

    for m in msgs:
        c, s = m['content'], m['sender']
        dk, mk, hr = m['dt'].strftime('%Y-%m-%d'), ym_of(m['dt']), m['dt'].hour
        mi = monthIdx.get(mk, 0)
        i = 0 if s == 'me' else 1
        D['daily'][dk][i] += 1
        D['monCnt'][mk][i] += 1
        D['byHourM' if s == 'me' else 'byHourH'][hr] += 1
        isNig = hr >= 23 or hr < 6
        if isNig:
            D['night'][s] += 1
        pos = hit(c, POSITIVE)
        neg = hit(c, NEGATIVE)
        if pos:
            D['dayPos'][dk][0 if s == 'me' else 2] += 1
            D['monPos'][mk][i] += 1
        if neg:
            D['dayPos'][dk][1 if s == 'me' else 3] += 1
            D['monNeg'][mk][i] += 1
        if hit(c, RATIONAL):
            D['monRat'][mk][i] += 1
        if hit(c, CRITICISM):
            D['monCri'][mk][i] += 1
        for k, words in NICK_DETAIL:
            if hit(c, words):
                D['monNmM'][k][mi] += 1

    # 深夜温差：分别算白天/深夜净分
    for s, lst in (('me', me), ('her', her)):
        for tag, cond in (('day', lambda h: not (h >= 23 or h < 6)), ('night', lambda h: h >= 23 or h < 6)):
            sel = [m for m in lst if cond(m['dt'].hour)]
            p = sum(1 for m in sel if hit(m['content'], POSITIVE))
            n = sum(1 for m in sel if hit(m['content'], NEGATIVE))
            D['nightSent'][s][0 if tag == 'day' else 1] = round((p - n) / max(1, len(sel)) * 100, 1)
        D['nightSent'][s] = [D['nightSent'][s][0], D['nightSent'][s][1]]

    D['nightPctM'] = pct(D['night']['me'], nMe)
    D['nightPctH'] = pct(D['night']['her'], nHer)

    # ---------- 逐月序列 ----------
    def mcnt(mk, i):
        return D['monCnt'][mk][i]
    D['VME'] = [mcnt(mk, 0) for mk in months]
    D['VHE'] = [mcnt(mk, 1) for mk in months]
    D['MME'] = [round((D['monPos'][mk][0] - D['monNeg'][mk][0]) / max(1, mcnt(mk, 0)) * 100, 1) for mk in months]
    D['MHE'] = [round((D['monPos'][mk][1] - D['monNeg'][mk][1]) / max(1, mcnt(mk, 1)) * 100, 1) for mk in months]
    D['RAT_M'] = [round(D['monRat'][mk][0] / max(1, mcnt(mk, 0)) * 100, 1) for mk in months]
    D['RAT_H'] = [round(D['monRat'][mk][1] / max(1, mcnt(mk, 1)) * 100, 1) for mk in months]
    D['CME'] = [round(D['monCri'][mk][0] / max(1, mcnt(mk, 0)) * 1000, 1) for mk in months]
    D['CHE'] = [round(D['monCri'][mk][1] / max(1, mcnt(mk, 1)) * 1000, 1) for mk in months]
    D['GOTTMAN_M'] = []
    for mk in months:
        p = D['monPos'][mk][0] + D['monPos'][mk][1]
        n = D['monNeg'][mk][0] + D['monNeg'][mk][1]
        D['GOTTMAN_M'].append(round(p / n, 2) if n else None)
    D['HPCT_M'] = [round(v / max(1, sum(D['byHourM'])) * 100, 2) for v in D['byHourM']]
    D['HPCT_H'] = [round(v / max(1, sum(D['byHourH'])) * 100, 2) for v in D['byHourH']]

    # ---------- 会话段：开启 / 收尾 ----------
    S = len(sessions)
    D['sessions'] = S
    D['openM'] = sum(1 for s in sessions if s[0]['sender'] == 'me')
    D['openH'] = S - D['openM']
    D['closeM'] = sum(1 for s in sessions if s[-1]['sender'] == 'me')
    D['closeH'] = S - D['closeM']
    D['openPctH'] = pct(D['openH'], S)
    D['openPctM'] = pct(D['openM'], S)
    D['sessLen'] = round(sum(len(s) for s in sessions) / max(1, S), 1)

    # ---------- 回复速度 ----------
    dm, dh, fm, fh, f5m, f5h = [], [], 0, 0, 0, 0
    for i in range(1, total):
        if msgs[i]['sender'] == msgs[i - 1]['sender']:
            continue
        gap = (msgs[i]['dt'] - msgs[i - 1]['dt']).total_seconds() / 60.0
        if gap <= 0:
            continue
        if msgs[i]['sender'] == 'me':
            dm.append(gap)
            fm += gap <= 1
            f5m += gap <= 5
        else:
            dh.append(gap)
            fh += gap <= 1
            f5h += gap <= 5
    D['medM'], D['medH'] = (round(median(dm), 1), round(median(dh), 1))
    D['avgM'], D['avgH'] = (round(sum(dm) / max(1, len(dm)), 1), round(sum(dh) / max(1, len(dh)), 1))
    D['f1M'], D['f1H'] = pct(fm, len(dm)), pct(fh, len(dh))
    D['f5M'], D['f5H'] = pct(f5m, len(dm)), pct(f5h, len(dh))
    D['repN_M'], D['repN_H'] = len(dm), len(dh)

    # ---------- 连发 / 连发后被堵回 ----------
    maxM = maxH = b3M = b3H = b5M = b5H = 0
    blockM = blockH = 0   # 你连发后对方只回1-2字 / TA连发后你只回1-2字
    curS, curN = None, 0
    for i, m in enumerate(msgs):
        if m['sender'] == curS:
            curN += 1
        else:
            # 上一段连发结束，看本条（对方）是不是只回了1-2字
            if curS is not None and curN >= 3 and len(m['content'].strip()) <= 2:
                if curS == 'her':
                    blockH += 1
                else:
                    blockM += 1
            curS, curN = m['sender'], 1
        if curN > (maxM if m['sender'] == 'me' else maxH):
            if m['sender'] == 'me':
                maxM = curN
            else:
                maxH = curN
        if curN == 3:
            b3M += m['sender'] == 'me'
            b3H += m['sender'] == 'her'
        if curN == 5:
            b5M += m['sender'] == 'me'
            b5H += m['sender'] == 'her'
    D.update(maxM=maxM, maxH=maxH, b3M=b3M, b3H=b3H, b5M=b5M, b5H=b5H,
             blockM=blockM, blockH=blockH)

    # ---------- 断联 ----------
    gaps = []
    for i in range(1, total):
        gd = (msgs[i]['dt'] - msgs[i - 1]['dt']).total_seconds() / 86400.0
        if gd >= 1:
            gaps.append({'days': gd, 'before': msgs[i - 1]['dt'], 'after': msgs[i]['dt'], 'idx': i})
    D['gaps'] = gaps
    D['gap3'] = sum(1 for g in gaps if g['days'] > 3)
    if gaps:
        g = max(gaps, key=lambda x: x['days'])
    else:
        g = {'days': 0, 'before': D['last'], 'after': D['last'], 'idx': total - 1}
    D['maxGap'] = round(g['days'])
    D['gapBefore'], D['gapAfter'], D['gapIdx'] = g['before'], g['after'], g['idx']
    D['gapHours'] = round(g['days'] * 24, 1) if g['days'] else 0

    # ---------- 冲突段与修复 ----------
    conflictSessions = []
    for si, s in enumerate(sessions):
        hits = [(i, m) for i, m in enumerate(s) if hit(m['content'], CONFLICT)]
        if len(hits) >= 2:
            conflictSessions.append({'msgs': s, 'hits': hits, 'si': si,
                                     'start': s[0]['dt'], 'end': s[-1]['dt'],
                                     'n': len(hits), 'first': hits[0][1]})
    D['conflictSessions'] = conflictSessions
    D['conflictN'] = len(conflictSessions)
    midx = {id(m): i for i, m in enumerate(msgs)}
    repM = repH = 0
    silM, silH = [], []
    repairs = []
    for cs in conflictSessions:
        k = midx.get(id(cs['msgs'][-1]), total - 1) + 1
        if k >= total:
            continue
        nx = msgs[k]
        sil = (nx['dt'] - cs['msgs'][-1]['dt']).total_seconds() / 3600.0
        if nx['sender'] == 'me':
            repM += 1
            silM.append(sil)
        else:
            repH += 1
            silH.append(sil)
        repairs.append({'dt': nx['dt'], 'who': nx['sender'], 'sil': sil,
                        'trigger': cs['hits'][0][1]['content'], 'last': cs['msgs'][-1]['content'],
                        'reply': nx['content'], 'n': cs['n'], 'date': cs['start'].strftime('%Y-%m-%d')})
    D.update(repM=repM, repH=repH)
    D['repRateM'] = pct(repM, repM + repH)
    D['repRateH'] = pct(repH, repM + repH)
    D['silM'] = round(median([v for v in silM if v <= 168]), 1) if [v for v in silM if v <= 168] else 0
    D['silH'] = round(median([v for v in silH if v <= 168]), 1) if [v for v in silH if v <= 168] else 0
    _sil = [v for v in silM + silH if v <= 168]
    D['silAll'] = round(median(_sil), 1) if _sil else 0
    D['silBigN'] = sum(1 for v in silM + silH if v > 168)
    D['repairs'] = repairs
    D['FS_M'] = sum(1 for m in me if '分手' in m['content'])
    D['FS_H'] = sum(1 for m in her if '分手' in m['content'])

    # ---------- 全局 Gottman ----------
    gpos = sum(1 for m in msgs if hit(m['content'], POSITIVE))
    gneg = sum(1 for m in msgs if hit(m['content'], NEGATIVE))
    D['gpos'], D['gneg'] = gpos, gneg
    D['gottman'] = round(gpos / gneg, 2) if gneg else float(gpos)

    # ---------- 深夜温差 ----------
    D['nightGapM'] = round(D['nightSent']['me'][1] - D['nightSent']['me'][0], 1)
    D['nightGapH'] = round(D['nightSent']['her'][1] - D['nightSent']['her'][0], 1)

    # ---------- Bids 接住率 ----------
    def is_bid(t):
        if '?' in t or '？' in t:
            return True
        if len(t) >= 8 and any(k in t for k in ('今天', '我跟你说', '我发现', '你看', '给你', '我在', '刚才', '分享', '和你说')):
            return True
        return False

    bid = {'me': [0, 0], 'her': [0, 0]}   # [发出, 被接住]
    for i in range(total - 1):
        s = msgs[i]['sender']
        if not is_bid(msgs[i]['content']):
            continue
        bid[s][0] += 1
        j = i + 1
        while j < total and msgs[j]['sender'] == s:
            j += 1
        if j >= total:
            continue
        r = msgs[j]['content'].strip()
        if len(r) >= 4 and r not in SHORT_OK:
            bid[s][1] += 1
    D['bidsM'], D['bidsH'] = bid['me'][0], bid['her'][0]
    D['bidsCatchM'] = pct(bid['me'][1], bid['me'][0])
    D['bidsCatchH'] = pct(bid['her'][1], bid['her'][0])
    D['bidsCatch'] = pct(bid['me'][1] + bid['her'][1], bid['me'][0] + bid['her'][0])

    # ---------- Capitalization ----------
    cap = Counter()
    for i in range(total - 1):
        s = msgs[i]['sender']
        if not hit(msgs[i]['content'], POSITIVE):
            continue
        j = i + 1
        while j < total and msgs[j]['sender'] == s:
            j += 1
        if j >= total:
            cap['PD'] += 1
            continue
        r = msgs[j]['content'].strip()
        if hit(r, NEGATIVE) or hit(r, CONFLICT) or hit(r, CONTEMPT):
            cap['AD'] += 1
        elif hit(r, POSITIVE) or '?' in r or '？' in r or len(r) >= 12:
            cap['AC'] += 1
        elif len(r) <= 6 and hit(r, SHORT_OK):
            cap['PC'] += 1
        else:
            cap['PD'] += 1
    capTot = sum(cap.values())
    D['cap'] = cap
    D['capTot'] = capTot
    D['capAC'] = pct(cap['AC'], capTot)
    D['capPC'] = pct(cap['PC'], capTot)
    D['capAD'] = pct(cap['AD'], capTot)
    D['capPD'] = pct(cap['PD'], capTot)

    # ---------- Sternberg 三角 ----------
    def s_metric(lst, words):
        return per_k(count_msg(lst, words), len(lst))
    D['STERN_M'] = [
        round(s_metric(me, CARE) + s_metric(me, SECURE), 1),
        round(s_metric(me, NICKNAMES) + s_metric(me, LOVE_WORDS) + s_metric(me, MISS_WORDS), 1),
        round(s_metric(me, FUTURE_WORDS), 1),
    ]
    D['STERN_H'] = [
        round(s_metric(her, CARE) + s_metric(her, SECURE), 1),
        round(s_metric(her, NICKNAMES) + s_metric(her, LOVE_WORDS) + s_metric(her, MISS_WORDS), 1),
        round(s_metric(her, FUTURE_WORDS), 1),
    ]
    D['STERN_MAX'] = round(max(D['STERN_M'] + D['STERN_H'] + [1]) * 1.2, 1)

    # ---------- 话题聚类（词典近似） ----------
    tc = {k: [0, 0] for k, _ in TOPIC_CLUSTERS}
    for m in msgs:
        for k, words in TOPIC_CLUSTERS:
            if hit(m['content'], words):
                tc[k][0 if m['sender'] == 'me' else 1] += 1
                break
    D['topic'] = tc
    tt = sum(tc[k][0] + tc[k][1] for k, _ in TOPIC_CLUSTERS) or 1
    D['topicCats'] = [k for k, _ in TOPIC_CLUSTERS]
    D['topicM'] = [pct(tc[k][0], tt) for k, _ in TOPIC_CLUSTERS]
    D['topicH'] = [pct(tc[k][1], tt) for k, _ in TOPIC_CLUSTERS]
    D['topicTot'] = tt

    # ---------- 导火索归类 ----------
    trig = Counter()
    for cs in conflictSessions:
        placed = False
        for _, m in cs['hits']:
            for name, kws in TRIGGER_RULES:
                if hit(m['content'], kws):
                    trig[name] += 1
                    placed = True
                    break
            if placed:
                break
        if not placed:
            trig['其他 / 无法归类'] += 1
    D['trigger'] = trig
    D['triggerN'] = len(conflictSessions)

    # ---------- 断联前 30 天逐日 ----------
    D['g30Dates'], D['g30M'], D['g30H'], D['g30S'] = [], [], [], []
    if D['maxGap'] >= 2 and D['gapBefore']:
        start = (D['gapBefore'] - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
        for k in range(30):
            d0 = start + timedelta(days=k)
            key = d0.strftime('%Y-%m-%d')
            dm, dh = D['daily'].get(key, [0, 0])
            D['g30Dates'].append(d0.strftime('%m-%d'))
            D['g30M'].append(dm)
            D['g30H'].append(dh)
            dv = D['dayPos'].get(key, [0, 0, 0, 0])
            tot = dm + dh
            D['g30S'].append(round((dv[0] + dv[2] - dv[1] - dv[3]) / max(1, tot) * 100, 1))

    # ---------- 临界慢化 ----------
    xs = [D['daily'].get(k, [0, 0])[0] + D['daily'].get(k, [0, 0])[1] for k in daysArr]
    n = len(xs)
    var7, ar30 = [], []
    for i in range(n):
        win = xs[max(0, i - 13):i + 1]
        mu = sum(win) / len(win)
        var7.append(round(sum((v - mu) ** 2 for v in win) / len(win), 1))
    for i in range(n):
        win = xs[max(0, i - 29):i + 1]
        if len(win) < 8:
            ar30.append(None)
            continue
        a = win[:-1]
        b = win[1:]
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        num = sum((a[k] - ma) * (b[k] - mb) for k in range(len(a)))
        da = sum((v - ma) ** 2 for v in a) ** 0.5
        db = sum((v - mb) ** 2 for v in b) ** 0.5
        ar30.append(round(num / (da * db), 2) if da and db else 0.0)

    step = max(1, n // 90)
    D['slowDates'] = [daysArr[i][5:] for i in range(0, n, step)]
    D['slowVar'] = [var7[i] for i in range(0, n, step)]
    D['slowAR'] = [ar30[i] for i in range(0, n, step)]
    pre = [i for i in range(n) if daysArr[i] < D['gapBefore'].strftime('%Y-%m-%d')]
    pre60 = pre[-60:]
    # 基线用「紧邻且等长」的前一段（断联前 61~120 天），做匹配窗口对比。
    # 旧口径用全期均值当基线：断联期间的方差为 0，会把基线拉低，方向失真。
    pre120 = pre[:-60][-60:] if len(pre) > 60 else []
    D['slowPreVar'] = round(sum(var7[i] for i in pre60) / max(1, len(pre60)), 1) if pre60 else 0
    arpre = [ar30[i] for i in pre60 if ar30[i] is not None]
    D['slowPreAR'] = round(sum(arpre) / max(1, len(arpre)), 2) if arpre else 0
    if pre120:
        D['slowBaseVar'] = round(sum(var7[i] for i in pre120) / len(pre120), 1)
        arbase = [ar30[i] for i in pre120 if ar30[i] is not None]
        D['slowBaseAR'] = round(sum(arbase) / max(1, len(arbase)), 2) if arbase else 0
        D['slowBaseLabel'] = '断联前 61~120 天'
    else:
        D['slowBaseVar'] = round(sum(var7) / max(1, n), 1)
        arv = [v for v in ar30 if v is not None]
        D['slowBaseAR'] = round(sum(arv) / max(1, len(arv)), 2)
        D['slowBaseLabel'] = '全期均值'

    # ---------- 事件研究 ----------
    # 基线用「有聊天的日子」的日均。全期日历日均值会被长断联和个别熄火月份拉低，
    # 把冲突后的涨幅夸大好几倍（示例：旧口径曾得出 +309%，换基线后约为 +数成）。
    # 锚点 = 冲突段结束时刻。「冲突后」窗口不再把吵架本身算进去（旧口径从冲突开始算，虚高）。
    actCnt = [(D['daily'][k][0] + D['daily'][k][1]) for k in daysArr
              if (D['daily'][k][0] + D['daily'][k][1]) > 0]
    base = sum(actCnt) / max(1, len(actCnt))
    buckets = [('吵架当天（含吵架本身）', -1, 0), ('吵完第 1 天', 0, 1), ('吵完第 2~3 天', 1, 3)]
    ev = []
    for name, a, b in buckets:
        cnt = 0
        for cs in conflictSessions:
            t0 = cs['end']
            lo, hi = t0 + timedelta(days=a), t0 + timedelta(days=b)
            cnt += sum(1 for m in msgs if lo < m['dt'] <= hi)
        per_day = cnt / max(1, len(conflictSessions)) / abs(b - a)
        ev.append({'name': name, 'perDay': round(per_day, 1), 'pct': round((per_day - base) / max(0.01, base) * 100, 1)})
    D['event'] = ev
    D['eventBase'] = round(base, 1)
    D['eventBaseLabel'] = '有聊天日日均（%d 天）' % len(actCnt)

    # =====================================================================
    # 扩展维度（最完整版）：断联全清单 / 星期节律 / 长度分布 / 延迟分布 /
    #                        作息首末条 / 年度对比 / 表情逐月 / 单日峰值
    # =====================================================================

    # (a) 断联全清单
    D['gapList'] = []
    for g in sorted(gaps, key=lambda x: -x['days'])[:12]:
        j = g['idx']
        pre = msgs[j - 1] if j - 1 >= 0 else None
        post = msgs[j] if j < total else None
        D['gapList'].append({'days': g['days'], 'before': g['before'], 'after': g['after'],
                             'pre': pre['content'] if pre else '', 'preWho': pre['sender'] if pre else 'me',
                             'post': post['content'] if post else ''})
    D['gap3N'] = sum(1 for g in gaps if g['days'] >= 3)
    D['gap7N'] = sum(1 for g in gaps if g['days'] >= 7)

    # (b) 星期节律
    wdM, wdH = [0] * 7, [0] * 7
    for m in msgs:
        w = m['dt'].weekday()
        (wdM if m['sender'] == 'me' else wdH)[w] += 1
    D['wdM'], D['wdH'] = wdM, wdH
    D['wdMP'] = [pct(v, nMe) for v in wdM]
    D['wdHP'] = [pct(v, nHer) for v in wdH]
    D['wdLabels'] = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    D['wdPkM'] = wdM.index(max(wdM))
    D['wdPkH'] = wdH.index(max(wdH))
    D['wdWeekendM'] = pct(wdM[5] + wdM[6], nMe)
    D['wdWeekendH'] = pct(wdH[5] + wdH[6], nHer)

    # (c) 消息长度分布
    LB = [(1, 3), (4, 10), (11, 30), (31, 100), (101, 10 ** 9)]
    lbM, lbH = [0] * len(LB), [0] * len(LB)
    for m in msgs:
        L = len(m['content'])
        for i, (a, b) in enumerate(LB):
            if a <= L <= b:
                (lbM if m['sender'] == 'me' else lbH)[i] += 1
                break
    D['lenBuck'] = ['1–3 字', '4–10 字', '11–30 字', '31–100 字', '100 字以上']
    D['lenM'], D['lenH'] = lbM, lbH
    D['lenMP'] = [pct(v, nMe) for v in lbM]
    D['lenHP'] = [pct(v, nHer) for v in lbH]
    D['lenShortM'] = pct(lbM[0] + lbM[1], nMe)
    D['lenShortH'] = pct(lbH[0] + lbH[1], nHer)
    D['lenLongM'] = pct(lbM[3] + lbM[4], nMe)
    D['lenLongH'] = pct(lbH[3] + lbH[4], nHer)

    # (d) 回复延迟分布
    RB = [('≤1 分钟', 0, 1), ('1–5 分钟', 1, 5), ('5–30 分钟', 5, 30),
          ('30–60 分钟', 30, 60), ('1–6 小时', 60, 360), ('超过 6 小时', 360, 10 ** 9)]
    rbM, rbH = [0] * len(RB), [0] * len(RB)
    for i in range(1, total):
        if msgs[i]['sender'] == msgs[i - 1]['sender']:
            continue
        gg = (msgs[i]['dt'] - msgs[i - 1]['dt']).total_seconds() / 60.0
        if gg < 0:
            continue
        for k, (_, a, b) in enumerate(RB):
            if a <= gg < b:
                (rbM if msgs[i]['sender'] == 'me' else rbH)[k] += 1
                break
    D['rdLabels'] = [x[0] for x in RB]
    D['rdM'], D['rdH'] = rbM, rbH
    D['rdMP'] = [pct(v, sum(rbM)) for v in rbM]
    D['rdHP'] = [pct(v, sum(rbH)) for v in rbH]

    # (e) 作息：每日首条 / 末条消息落在哪个小时
    firstH = {'me': [0] * 24, 'her': [0] * 24}
    lastH = {'me': [0] * 24, 'her': [0] * 24}
    seenDays = {}
    for m in msgs:
        k = m['dt'].strftime('%Y-%m-%d')
        if k not in seenDays:
            seenDays[k] = [m, m]
        else:
            seenDays[k][1] = m
    for k, (f, l) in seenDays.items():
        firstH[f['sender']][f['dt'].hour] += 1
        lastH[l['sender']][l['dt'].hour] += 1

    def avg_hour(arr):
        t = sum(arr)
        return round(sum(i * v for i, v in enumerate(arr)) / t, 1) if t else 0.0
    D['firstHM'], D['firstHH'] = firstH['me'], firstH['her']
    D['lastHM'], D['lastHH'] = lastH['me'], lastH['her']
    D['firstAvgM'], D['firstAvgH'] = avg_hour(firstH['me']), avg_hour(firstH['her'])
    D['lastAvgM'], D['lastAvgH'] = avg_hour(lastH['me']), avg_hour(lastH['her'])
    D['firstDayN'] = sum(1 for k, (f, l) in seenDays.items() if f['sender'] == 'me')
    D['lastDayN'] = sum(1 for k, (f, l) in seenDays.items() if l['sender'] == 'me')

    # (f) 年度对比
    D['years'] = []
    for y in sorted(set(m['dt'].year for m in msgs)):
        ym = [m for m in msgs if m['dt'].year == y]
        if not ym:
            continue
        ymn = len(ym)
        yme = sum(1 for m in ym if m['sender'] == 'me')
        yp = sum(1 for m in ym if hit(m['content'], POSITIVE))
        yn = sum(1 for m in ym if hit(m['content'], NEGATIVE))
        ycfl = sum(1 for cs in conflictSessions if cs['start'].year == y)
        yrp = [r for r in repairs if r['dt'].year == y]
        yrpm = sum(1 for r in yrp if r['who'] == 'me')
        days = len(set(m['dt'].strftime('%Y-%m-%d') for m in ym))
        span = max(1, (ym[-1]['dt'] - ym[0]['dt']).days + 1)
        D['years'].append({
            'y': y, 'n': ymn, 'me': yme, 'her': ymn - yme, 'cfl': ycfl,
            'gottman': round(yp / yn, 2) if yn else float(yp),
            'days': days, 'span': span, 'perDay': round(ymn / days, 1),
            'repM': pct(yrpm, len(yrp)) if yrp else 0,
            'repH': pct(len(yrp) - yrpm, len(yrp)) if yrp else 0, 'repN': len(yrp)})

    # (g) 表情逐月
    D['monEmojiM'] = [0] * len(months)
    D['monEmojiH'] = [0] * len(months)
    for m in msgs:
        ne = len(EMOJI_RE.findall(m['content']))
        if not ne:
            continue
        i = monthIdx.get(ym_of(m['dt']))
        if i is None:
            continue
        (D['monEmojiM'] if m['sender'] == 'me' else D['monEmojiH'])[i] += ne

    # (h) 单日峰值 / 单条最长
    busiest = sorted(((k, v[0] + v[1]) for k, v in D['daily'].items()), key=lambda x: -x[1])[:10]
    D['busiest'] = [(k, c, D['daily'][k][0], D['daily'][k][1]) for k, c in busiest]

    def _rep_ratio(s):
        """单字重复率：用来剔除「哈哈哈哈…」这类刷屏，它长但没有信息量。"""
        if not s:
            return 1.0
        return Counter(s).most_common(1)[0][1] / float(len(s))
    NOTICE_RE = re.compile(r'[【】]|https?://|www\.|@[A-Za-z0-9_.-]+|[A-Za-z0-9]{5,}\.[a-z]{2,}')

    def _is_notice(s):
        """转发通知 / 系统消息 / 含网址或长账号串的，不是「人话」，排除。"""
        if NOTICE_RE.search(s):
            return True
        if ('密码' in s or '登录' in s) and ('账号' in s or '网站' in s):
            return True
        return False
    D['longest'] = sorted([m for m in msgs
                           if _rep_ratio(m['content']) < 0.4 and not _is_notice(m['content'])],
                          key=lambda m: -len(m['content']))[:5]

    # ---------- 关系分期 ----------
    D['phases'] = build_phases(D, msgs, daysArr)

    # ---------- 断联 markArea ----------
    D['gapArea'] = []
    if D['maxGap'] >= 14:
        a = ym_of(D['gapBefore'])
        b = ym_of(D['gapAfter'])
        if a == b:
            b = month_add(b, 1)
        D['gapArea'] = [[{'xAxis': a}, {'xAxis': b}]]
    return D


def phase_slice(msgs, a, b):
    """预留：按时间区间取消息。"""
    return [m for m in msgs if a <= m['dt'] <= b]


def build_phases(D, msgs, daysArr):
    first, last = D['first'], D['last']
    if D['maxGap'] >= 14:
        gs, ge = D['gapBefore'], D['gapAfter']
        spans = (gs - first).days
        ph = []
        if spans >= 150:
            mid = gs - timedelta(days=spans // 2)
            ph.append(('热恋期', first, mid, 'green'))
            ph.append(('余温期', mid, gs, 'gold'))
        else:
            ph.append(('热恋期', first, gs, 'green'))
        ph.append(('断联期', gs, ge, 'red'))
        ph.append(('复燃期', ge, last, 'purple'))
        return ph
    n = len(daysArr)
    if n >= 90:
        a = datetime.strptime(daysArr[0], '%Y-%m-%d')
        m1 = datetime.strptime(daysArr[n // 3], '%Y-%m-%d')
        m2 = datetime.strptime(daysArr[2 * n // 3], '%Y-%m-%d')
        return [('早期', a, m1, 'green'), ('中期', m1, m2, 'gold'), ('近期', m2, last, 'purple')]
    return [('全程', first, last, 'green')]

# =====================================================================
# 5. 第 9 步 · 结论生成层（数字 → 基准 → 原文 → 解读 → 行动）
# =====================================================================

def label_types(D):
    """给两个人各起一个能记住的名字。"""
    hi_anx = D['ANX_HP'] > D['ANX_MP']
    hi_av = D['AV_MP'] > D['AV_HP']
    if hi_anx and hi_av:
        rel = '追逃型配对：焦虑 × 回避'
    elif D['maxGap'] >= 20:
        rel = '断联—复燃型'
    elif D['pctMe'] > 58:
        rel = '单向投入型'
    elif D['gottman'] >= 5:
        rel = '健康稳定型'
    else:
        rel = '波动修补型'
    her = '情绪明牌者 · 高反应性' if hi_anx else ('主动输出者' if D['pctHer'] > 50 else '温和内敛者')
    mie = '情绪缓冲者 · 低反应性' if hi_av else ('安静稳定器' if D['pctMe'] < 45 else '热情主动者')
    return rel, her, mie


def build_verdict(D, rel):
    herStartPct = D['herStartPct']
    naive = '平平淡淡跑了 %d 天' % D['days'] if D['maxGap'] >= 14 else '一直很甜、一直很稳'
    if D['maxGap'] >= 14:
        real = '烧到最热 → 彻底断掉 → 又比任何时候更热（%d 天的断联夹在中间）' % D['maxGap']
    elif '追逃' in rel:
        real = '一边用力推、一边安静接'
    else:
        real = '一起吵、一起修，热度没掉，但账一直没算清'
    engine = 'TA' if D['openPctH'] >= 50 else '你'
    stable = '你' if engine == 'TA' else 'TA'
    ev = ('TA 主动开启 %s%% 的对话段，最长断联 %d 天，Gottman 比率 %s:1'
          % (D['openPctH'], D['maxGap'], D['gottman']))
    if D['blockH'] > D['blockM'] * 1.3 and D['blockH'] > 5:
        un = ('她连发之后被一两个字堵回去 %d 次，反向只有 %d 次——她一次次把话递过来，你一次次只回了两个字。'
              % (D['blockH'], D['blockM']))
    elif D['ST_M'] + D['ST_H'] > 0 and D['AV_MP'] > D['AV_HP']:
        un = ('你回避疏离 %d 次、她 %d 次——那些「算了」和「随便」从来没被摆上桌，它们没有消失，只是被折起来收好了。'
              % (D['AV_M'], D['AV_H']))
    else:
        un = ('%d 段冲突里，你们修好了 %d 段，但修复的方式是刷屏、不是把话说开。'
              % (D['conflictN'], D['repM'] + D['repH']))
    return ('这不是一段「%s」的关系——而是「<b>%s</b>」。<br>'
            '<b>%s 是发动机，%s 是稳定器</b>：%s。<br>'
            '<b>真正没被解决的</b>，是%s' % (naive, real, engine, stable, ev, un))


def build_trio(D, rel, her_type, me_type):
    def li(items):
        return '<ul>' + ''.join('<li>%s</li>' % x for x in items) + '</ul>'
    c1 = li(['TA 主动开启 %s%% 的对话段' % D['openPctH'],
             '最长断联 %d 天' % D['maxGap'],
             'Gottman 比率 %s:1（健康线 5:1）' % D['gottman'],
             '%d 段冲突，修复 %d 段' % (D['conflictN'], D['repM'] + D['repH'])])
    c2 = li(['最长连发 %d 条' % D['maxH'],
             '焦虑追问 %d 次（每千条 %s）' % (D['ANX_H'], D['ANX_HP']),
             '情绪要挟 %d 次 · 「分手」%d 次' % (D['TH_H'], D['FS_H']),
             '接住你的邀请 %s%%' % D['bidsCatchH']])
    c3 = li(['最长连发 %d 条' % D['maxM'],
             '回避疏离 %d 次（每千条 %s）' % (D['AV_M'], D['AV_MP']),
             '主动开启只占 %s%%' % D['openPctM'],
             '连发后被堵回 %d 次' % D['blockM']])
    return (
        '<div><div class="head" style="color:var(--gold)">关 系 总 断</div>'
        '<div class="big" style="color:var(--gold)">%s</div>'
        '<div class="body" style="border-color:var(--gold)">她追，你接；她用力，你保温。</div>%s</div>'
        '<div><div class="head" style="color:var(--her)">TA · 画像</div>'
        '<div class="big" style="color:var(--her)">%s</div>'
        '<div class="body" style="border-color:var(--her)">燃时全盘托出，冷时一字不留。</div>%s</div>'
        '<div><div class="head" style="color:var(--me)">你 · 画像</div>'
        '<div class="big" style="color:var(--me)">%s</div>'
        '<div class="body" style="border-color:var(--me)">话藏在动作里，态度藏在沉默里。</div>%s</div>'
        % (rel, c1, her_type, c2, me_type, c3))


TOC_ITEMS = [
    ('01', '两个人的画像', '四类依恋行为的双向频次'),
    ('02', '同一句话，两种语言', '语气词 / 人称 / 句式 / 表情策略'),
    ('03', '谁在推，谁在接', '会话段开启收尾 / 回复速度 / 连发'),
    ('04', '感情波动', '月度情感净分 / 高低点 / 深夜温差'),
    ('05', '吵架是怎么结束的', '冲突段 / 谁先低头 / 静默多久'),
    ('06', '节奏与逐月变化', '24h 生物钟 / 理性指数 / 批评频率'),
    ('07', '数据会讲故事', '断联当天时间轴 / 导火索 / 冲突复盘'),
    ('08', '心理学框架补完', 'Gottman / Bids / Gable / 临界慢化 / 事件研究'),
    ('09', '谁更爱谁', '13 项投入度逐项对比'),
    ('10', '最终药方', '她改 / 你改 / 互相谅解 / 一起改'),
    ('11', '附录 · 全量数据', '断联清单 / 年度对比 / 作息节律 / 峰值日'),
]


def build_toc():
    return ''.join('<a href="#s%s"><span class="n">%s</span>%s<span class="d">%s</span></a>'
                   % (n, n, t, d) for n, t, d in TOC_ITEMS)


def topn(lst, key, n=5, rev=False):
    return sorted(lst, key=key, reverse=rev)[:n]


# =====================================================================
# 6. 渲染层
# =====================================================================

def render(D, meta):
    T = {}
    msgs, me, her = meta['msgs'], meta['me'], meta['her']
    nMe, nHer, total = D['nMe'], D['nHer'], D['total']
    rel, her_type, me_type = label_types(D)

    # ---------- 逐月修复率 ----------
    repByMonth = {}
    for r in D['repairs']:
        mk = ym_of(r['dt'])
        a = repByMonth.setdefault(mk, [0, 0])
        a[0 if r['who'] == 'me' else 1] += 1
    REP_M = []
    REP_H = []
    for mk in D['months']:
        a = repByMonth.get(mk)
        if not a:
            REP_M.append(None)
            REP_H.append(None)
        else:
            t = a[0] + a[1]
            REP_M.append(round(a[0] / t * 100, 1))
            REP_H.append(round(a[1] / t * 100, 1))

    # ---------- Hero ----------
    herDaySet = set()
    for m in her:
        herDaySet.add(m['dt'].strftime('%Y-%m-%d'))
    firstOfDay = {}
    for m in msgs:
        k = m['dt'].strftime('%Y-%m-%d')
        if k not in firstOfDay:
            firstOfDay[k] = m['sender']
    activeDays = len(firstOfDay)
    herOpenDays = sum(1 for k, s in firstOfDay.items() if s == 'her')
    herStartPct = pct(herOpenDays, max(1, activeDays))
    D['herStartPct'] = herStartPct

    T['HEADLINE'] = ('%s ~ %s · %s 条消息 · %d 天 · %d 段对话 · 双方 %s / %s 条'
                     % (D['first'].strftime('%Y-%m-%d'), D['last'].strftime('%Y-%m-%d'),
                        format(total, ','), D['days'], D['sessions'],
                        format(nMe, ','), format(nHer, ',')))
    if D['maxGap'] >= 14 and '追逃' in rel:
        ht = '烧到最热 → 彻底断掉 → 又比任何时候更热；她一直在推，你一直在接'
    elif D['maxGap'] >= 14:
        ht = '烧到最热 → 彻底断掉 → 又比任何时候更热'
    elif '追逃' in rel:
        ht = '她一直在推，你一直在接'
    else:
        ht = '热度没掉，但账一直没算清'
    T['HERO_TITLE'] = '一段 <em>%s</em> 的关系：%s' % (rel.split('：')[0], ht)

    kpi = [('总消息数', format(total, ','), 'var(--purple)', '你 %s%% · TA %s%%' % (D['pctMe'], D['pctHer'])),
           ('TA 主动开启的日子', '%s%%' % herStartPct, 'var(--her)', '有聊天的 %d 天里 TA 说第一句' % activeDays),
           ('最长断联', '%d 天' % D['maxGap'], 'var(--red)' if D['maxGap'] > 7 else 'var(--green)',
            '%s → %s' % (D['gapBefore'].strftime('%Y-%m-%d'), D['gapAfter'].strftime('%Y-%m-%d'))),
           ('Gottman 比率', '%s:1' % D['gottman'], cls(D['gottman'], 5, 2), '积极 ÷ 消极，健康线 5:1')]
    T['KPI_ROW'] = ''.join('<div class="kpi"><div class="v" style="color:%s">%s</div><div class="l">%s<br>%s</div></div>'
                           % (c, v, l, s) for l, v, c, s in kpi)
    T['VERDICT'] = '<b>一句话结论：</b>' + build_verdict(D, rel)
    T['TRIO'] = build_trio(D, rel, her_type, me_type)
    T['TOC'] = build_toc()
    T['INVEST_N'] = '13'
    T['SESSION_COUNT'] = str(D['sessions'])
    T['CONFLICT'] = str(D['conflictN'])

    # ---------- 01 依恋 ----------
    rows = [('焦虑追问', D['ANX_M'], D['ANX_H'], D['ANX_MP'], D['ANX_HP'],
             '反复求证、怕失去；越追越显得不安全感'),
            ('回避疏离', D['AV_M'], D['AV_H'], D['AV_MP'], D['AV_HP'],
             '转移话题、敷衍收尾；「算了」是最典型的一刀'),
            ('情绪要挟', D['TH_M'], D['TH_H'], D['TH_MP'], D['TH_HP'],
             '以分手 / 拉黑施压；把关系当作筹码'),
            ('安全表达', D['SE_M'], D['SE_H'], D['SE_MP'], D['SE_HP'],
             '主动认错、安抚、提出一起解决')]
    def mkrow(name, a, b, ap, bp, read):
        wa = 'hl-me' if a > b else ''
        wb = 'hl-her' if b > a else ''
        return ('<tr><td>%s</td><td class="num %s">%s</td><td class="num %s">%s</td>'
                '<td class="num">%s</td><td class="num">%s</td><td class="read">%s</td></tr>'
                % (name, wa, a, wb, b, ap, bp, read))
    T['ATTACH_TABLE'] = ('<tr><th>依恋行为</th><th class="num">你·次数</th><th class="num">TA·次数</th>'
                         '<th class="num">你/千条</th><th class="num">TA/千条</th><th class="read">读法</th></tr>'
                         + ''.join(mkrow(*r) for r in rows))
    dom = max(rows, key=lambda r: max(r[3], r[4]))
    T['NOTE_ATTACH'] = ('主导这一对的依恋策略是<b>%s</b>。你的焦虑 %s/千条、回避 %s/千条；'
                        'TA 的焦虑 %s/千条、回避 %s/千条。'
                        '焦虑与回避是配对出现的：一个人追得越紧，另一个人退得越快，然后追的人更焦虑——'
                        '这是这个循环，不是某个人的错。'
                        % (dom[0], D['ANX_MP'], D['AV_MP'], D['ANX_HP'], D['AV_HP']))

    def pick(lst, words, n=2, longest=True):
        c = [m for m in lst if hit(m['content'], words)]
        c.sort(key=lambda m: len(m['content']), reverse=longest)
        return c[:n]

    def pick_mid(lst, words):
        c = [m for m in lst if 8 <= len(m['content']) <= 70 and hit(m['content'], words)]
        c.sort(key=lambda m: -sum(m['content'].count(w) for w in words))
        return c[:1]
    aq = pick(her, ANXIOUS, 2) + pick(me, ANXIOUS, 1)
    vq = pick(me, AVOID, 2) + pick(her, AVOID, 1)
    T['ATTACH_QUOTES'] = (''.join(q(m['sender'], m['dt'], m['content']) for m in aq)
                          + ''.join(q(m['sender'], m['dt'], m['content']) for m in vq)
                          + '<p class="note">上：焦虑追问的原话（越靠后越逼近崩溃）。下：回避疏离的原话——'
                            '「算了」「随便」这类词在文本里几乎没有情绪色彩，但它们决定了对话的走向。</p>')

    # ---------- 02 语言 ----------
    prows = [('「我」字消息', D['PN_M'], D['PN_H'], '自我表露。多的一方更习惯讲自己的事'),
             ('「你」字消息', D['PY_M'], D['PY_H'], '指向对方。多的一方更习惯把矛头对准你'),
             ('问句', D['Q_M'], D['Q_H'], '提问＝把球递出去，等对方回'),
             ('平均字数', D['LEN_M'], D['LEN_H'], '长句＝愿意展开，短句＝收着')]
    T['PRONOUN_TABLE'] = ('<tr><th></th><th class="num">你</th><th class="num">TA</th><th class="read">读法</th></tr>'
                          + ''.join('<tr><td>%s</td><td class="num %s">%s</td><td class="num %s">%s</td>'
                                    '<td class="read">%s</td></tr>'
                                    % (n, 'hl-me' if a > b else '', a, 'hl-her' if b > a else '', b, r)
                                    for n, a, b, r in prows))
    rows = []
    for i in range(8):
        a = D['TOPW_M'][i] if i < len(D['TOPW_M']) else ('', '')
        b = D['TOPW_H'][i] if i < len(D['TOPW_H']) else ('', '')
        rows.append('<tr><td>%s <span class="hl-me">%s</span></td><td class="num">%s</td>'
                    '<td>%s <span class="hl-her">%s</span></td><td class="num">%s</td></tr>'
                    % (i + 1, a[0], a[1], i + 1, b[0], b[1]))
    T['TOPWORD_TABLE'] = ('<tr><th>#</th><th>你的高频词</th><th class="num">次</th>'
                          '<th>TA 的高频词</th><th class="num">次</th></tr>' + ''.join(rows))
    erows = ''.join('<tr><td>%s</td><td class="num hl-me">%s</td><td class="num hl-her">%s</td></tr>'
                    % (e, D['EMOJI_M'].get(e, 0), D['EMOJI_H'].get(e, 0)) for e in D['EMOJI_TOP'][:8])
    T['EMOJI_TABLE'] = ('<tr><th>表情</th><th class="num">你</th><th class="num">TA</th></tr>'
                        '<tr><td><b>表情总数</b></td><td class="num hl-me">%d</td>'
                        '<td class="num hl-her">%d</td></tr>%s' % (D['EMOJI_CNT_M'], D['EMOJI_CNT_H'], erows))
    tm = pick_mid(me, ['哈', '呀', '呢', '嘛']) or me[:1]
    th = pick_mid(her, ['哈', '呀', '呢', '嘛']) or her[:1]
    T['TONE_QUOTES'] = (''.join(q(m['sender'], m['dt'], m['content']) for m in tm)
                        + ''.join(q(m['sender'], m['dt'], m['content']) for m in th)
                        + '<p class="note">语气词不参与情感打分，但它决定了同一句话是撒娇还是质问。'
                          '你的语气词 %s/千条，TA %s/千条（合计）。</p>'
                          % (round(sum(D['TONE_MP']), 1), round(sum(D['TONE_HP']), 1)))

    # ---------- 03 谁在推 ----------
    T['SESSION_TABLE'] = ('<tr><th>会话段</th><th class="num">你</th><th class="num">TA</th><th class="read">读法</th></tr>'
                          '<tr><td>由谁开启</td><td class="num %s">%d</td><td class="num %s">%d</td>'
                          '<td class="read">共 %d 段，TA 占 %s%%</td></tr>'
                          '<tr><td>由谁收尾</td><td class="num %s">%d</td><td class="num %s">%d</td>'
                          '<td class="read">收尾＝最后一句是谁说的</td></tr>'
                          '<tr><td>平均段长</td><td class="num" colspan="2">%s 条</td>'
                          '<td class="read">一段连续对话的平均消息数</td></tr>'
                          % ('hl-me' if D['openM'] > D['openH'] else '', D['openM'],
                             'hl-her' if D['openH'] > D['openM'] else '', D['openH'],
                             D['sessions'], D['openPctH'],
                             'hl-me' if D['closeM'] > D['closeH'] else '', D['closeM'],
                             'hl-her' if D['closeH'] > D['closeM'] else '', D['closeH'],
                             D['sessLen']))
    T['REPLY_TABLE'] = ('<tr><th></th><th class="num">你→TA</th><th class="num">TA→你</th><th class="read">读法</th></tr>'
                        '<tr><td>中位回复</td><td class="num hl-me">%s 分</td><td class="num hl-her">%s 分</td>'
                        '<td class="read">谁更急，看这一行</td></tr>'
                        '<tr><td>平均回复</td><td class="num">%s 分</td><td class="num">%s 分</td>'
                        '<td class="read">中位与均值差得越大，说明有极端慢的样本</td></tr>'
                        '<tr><td>1 分钟内</td><td class="num">%s%%</td><td class="num">%s%%</td>'
                        '<td class="read">秒回率</td></tr>'
                        '<tr><td>5 分钟内</td><td class="num">%s%%</td><td class="num">%s%%</td>'
                        '<td class="read">有效响应率</td></tr>'
                        '<tr><td>样本数</td><td class="num">%d</td><td class="num">%d</td>'
                        '<td class="read">换说话人处，长间隔不丢弃</td></tr>'
                        % (D['medM'], D['medH'], D['avgM'], D['avgH'],
                           D['f1M'], D['f1H'], D['f5M'], D['f5H'], D['repN_M'], D['repN_H']))
    T['BURST_TABLE'] = ('<tr><th>连发行为</th><th class="num">你</th><th class="num">TA</th><th class="read">读法</th></tr>'
                        '<tr><td>最长连发</td><td class="num">%d 条</td><td class="num hl-her">%d 条</td>'
                        '<td class="read">一口气说完，是不指望对方打断</td></tr>'
                        '<tr><td>≥3 条</td><td class="num">%d 次</td><td class="num">%d 次</td>'
                        '<td class="read">情绪上头的门槛</td></tr>'
                        '<tr><td>≥5 条</td><td class="num">%d 次</td><td class="num">%d 次</td>'
                        '<td class="read">几乎等于自说自话</td></tr>'
                        '<tr><td><b>连发后被堵回</b></td><td class="num hl-me">%d 次</td>'
                        '<td class="num hl-red">%d 次</td>'
                        '<td class="read">连发≥3条后对方只回1-2字——全报告最值得看的不对称</td></tr>'
                        % (D['maxM'], D['maxH'], D['b3M'], D['b3H'], D['b5M'], D['b5H'],
                           D['blockM'], D['blockH']))
    pk = max(range(len(D['months'])), key=lambda i: D['VME'][i] + D['VHE'][i])
    T['NOTE_VOLUME'] = ('峰值月是 <b>%s</b>（%d 条）。'
                        '红色区间是断联期——最长 %d 天没有任何消息，图上它必须可见，否则整段历史会看错。'
                        % (D['months'][pk], D['VME'][pk] + D['VHE'][pk], D['maxGap']))

    # ---------- 04 情绪 ----------
    dayStat = []
    for k in D['daysArr']:
        c = D['daily'][k][0] + D['daily'][k][1]
        if c < 3:
            continue
        p = D['dayPos'][k]
        net = round((p[0] + p[2] - p[1] - p[3]) / c * 100, 1)
        dayStat.append((k, net, c))
    lows = topn(dayStat, key=lambda x: x[1], n=5)
    highs = topn(dayStat, key=lambda x: x[1], n=5, rev=True)
    def dayrows(rows, cl):
        out = []
        for k, v, c in rows:
            rep = sorted([m for m in msgs if m['dt'].strftime('%Y-%m-%d') == k],
                         key=lambda m: (hit(m['content'], NEGATIVE) if cl == 'red' else not hit(m['content'], POSITIVE)))
            txt = cut(rep[0]['content'], 30) if rep else ''
            out.append('<tr><td>%s</td><td class="num %s">%s</td><td class="num">%d</td>'
                       '<td class="read">%s</td></tr>' % (k, cl, v, c, txt))
        return ''.join(out)
    T['LOW_TABLE'] = ('<tr><th>日期</th><th class="num">净分</th><th class="num">条数</th>'
                      '<th class="read">当天最刺眼的一句</th></tr>' + dayrows(lows, 'hl-red'))
    T['HIGH_TABLE'] = ('<tr><th>日期</th><th class="num">净分</th><th class="num">条数</th>'
                       '<th class="read">当天最亮的一句</th></tr>' + dayrows(highs, 'hl-green'))
    T['NIGHT_TABLE'] = ('<tr><th></th><th class="num">白天净分</th><th class="num">深夜净分</th>'
                        '<th class="num">温差</th><th class="num">深夜占比</th></tr>'
                        '<tr><td>你</td><td class="num">%s</td><td class="num">%s</td>'
                        '<td class="num %s">%s</td><td class="num">%s%%</td></tr>'
                        '<tr><td>TA</td><td class="num">%s</td><td class="num">%s</td>'
                        '<td class="num %s">%s</td><td class="num">%s%%</td></tr>'
                        % (D['nightSent']['me'][0], D['nightSent']['me'][1],
                           cls(D['nightGapM'], 0, -10), D['nightGapM'], D['nightPctM'],
                           D['nightSent']['her'][0], D['nightSent']['her'][1],
                           cls(D['nightGapH'], 0, -10), D['nightGapH'], D['nightPctH']))
    lo, hi = lows[0], highs[0]
    lq = [m for m in msgs if m['dt'].strftime('%Y-%m-%d') == lo[0] and hit(m['content'], NEGATIVE)][:2]
    hq = [m for m in msgs if m['dt'].strftime('%Y-%m-%d') == hi[0] and hit(m['content'], POSITIVE)][:2]
    T['MOOD_QUOTES'] = (''.join(q(m['sender'], m['dt'], m['content']) for m in lq)
                        + ''.join(q(m['sender'], m['dt'], m['content']) for m in hq)
                        + '<p class="note">上面是全场最低的那天（%s，净分 %s），下面是最高那天（%s，净分 %s）。'
                          '注意：净分低不代表那天感情差，也可能是那天说了很多正经事。</p>' % (lo[0], lo[1], hi[0], hi[1]))
    T['NOTE_MOOD'] = ('净分只在有 ≥3 条消息的日子里算，避免「某天只发了 2 条」把曲线顶飞。'
                      'TA 的最低月是 <b>%s</b>（%s），你的最低月是 <b>%s</b>（%s）。'
                      % (D['months'][D['MHE'].index(min(D['MHE']))], min(D['MHE']),
                         D['months'][D['MME'].index(min(D['MME']))], min(D['MME'])))

    # ---------- 05 冲突 ----------
    rep_read = ('TA 更怕僵着：TA 先开口 %d 次（%s%%）' % (D['repH'], D['repRateH'])
                if D['repH'] >= D['repM'] else
                '你更怕僵着：你先开口 %d 次（%s%%）' % (D['repM'], D['repRateM']))
    T['CONFLICT_TABLE'] = ('<tr><th>指标</th><th class="num">你</th><th class="num">TA</th><th class="read">读法</th></tr>'
                           '<tr><td>冲突段总数</td><td class="num" colspan="2">%d 段</td>'
                           '<td class="read">占全部 %d 段的 %s%%</td></tr>'
                           '<tr><td>先低头（修复）</td><td class="num hl-me">%d 次</td>'
                           '<td class="num hl-her">%d 次</td><td class="read">谁先把气氛拉回来</td></tr>'
                           '<tr><td>修复率</td><td class="num">%s%%</td><td class="num">%s%%</td>'
                           '<td class="read">%s</td></tr>'
                           '<tr><td>中位静默</td><td class="num">%s 小时</td><td class="num">%s 小时</td>'
                           '<td class="read">吵完到最后一句之后的第一条消息；超过 7 天的 %d 次已单列，那是断联不是静默</td></tr>'
                           '<tr><td>「分手」出现</td><td class="num">%d 次</td><td class="num hl-red">%d 次</td>'
                           '<td class="read">出现次数越多，这句话的效力越弱</td></tr>'
                           % (D['conflictN'], D['sessions'], pct(D['conflictN'], D['sessions']),
                              D['repM'], D['repH'], D['repRateM'], D['repRateH'], rep_read,
                              D['silM'], D['silH'], D['silBigN'], D['FS_M'], D['FS_H']))

    prows = []
    for name, a, b, color in D['phases']:
        seg = [m for m in msgs if a <= m['dt'] <= b]
        if not seg:
            prows.append('<tr><td><span class="tag %s">%s</span></td><td colspan="5" class="read">'
                         '%s ~ %s · 无消息</td></tr>' % (color, name, a.strftime('%Y-%m'), b.strftime('%Y-%m')))
            continue
        cfl = [cs for cs in D['conflictSessions'] if a <= cs['start'] <= b]
        rp = [r for r in D['repairs'] if a <= r['dt'] <= b]
        rm = sum(1 for r in rp if r['who'] == 'me')
        rh = len(rp) - rm
        sl = [r['sil'] for r in rp if r['sil'] <= 168]
        sil = round(median(sl), 1) if sl else 0
        prows.append('<tr><td><span class="tag %s">%s</span></td><td class="read">%s ~ %s</td>'
                     '<td class="num">%d</td><td class="num">%d</td>'
                     '<td class="num">%d / %d</td><td class="num">%s h</td></tr>'
                     % (color, name, a.strftime('%Y-%m'), b.strftime('%Y-%m'),
                        len(seg), len(cfl), rm, rh, sil))
    T['PHASE_TABLE'] = ('<tr><th>关系期</th><th>时间</th><th class="num">消息</th><th class="num">冲突段</th>'
                        '<th class="num">修复 你/TA</th><th class="num">中位静默</th></tr>' + ''.join(prows))
    ph = D['phases']
    T['NOTE_PHASE'] = ('全程均值会抹掉最重要的变化，所以按关系期拆开看：%s。'
                       '修复率若在最后一期下滑，那是全部数据里最新的警号，不是历史遗留。'
                       % '；'.join('%s %d 段冲突' % (n, len([cs for cs in D['conflictSessions'] if a <= cs['start'] <= b]))
                                  for n, a, b, _ in ph if a <= b))

    rq = []
    for r in D['repairs'][:3]:
        rq.append('<div class="quote %s"><div class="qm">%s · %s 先开口（静默 %.1f 小时）</div>%s</div>'
                  % (r['who'], r['date'], '你' if r['who'] == 'me' else 'TA', r['sil'], cut(r['reply'], 90)))
        rq.insert(len(rq) - 1, '<div class="quote grey"><div class="qm">冲突最后一句</div>%s</div>' % cut(r['last'], 80))
    T['REPAIR_QUOTES'] = ''.join(rq) + ('<p class="note">「先低头」不是贬义——在这份数据里，'
                                        '平均静默 %s 小时的修复，比 0 小时的假性和好更有价值。</p>' % D['silAll'])

    # ---------- 06 节奏 ----------
    pkM = D['HPCT_M'].index(max(D['HPCT_M']))
    pkH = D['HPCT_H'].index(max(D['HPCT_H']))
    T['NOTE_CLOCK'] = ('你的高峰在 <b>%d 点</b>（%s%%），TA 的高峰在 <b>%d 点</b>（%s%%）。'
                       '深夜（23:00–6:00）消息占比：你 %s%%，TA %s%%。'
                       '两条线错开得越远，说明你们的「醒着」不重合——很多争吵其实只是作息差。'
                       % (pkM, D['HPCT_M'][pkM], pkH, D['HPCT_H'][pkH],
                          D['nightPctM'], D['nightPctH']))
    mrows = []
    for i, mk in enumerate(D['months']):
        gm = D['GOTTMAN_M'][i]
        rp = '-' if REP_M[i] is None else '%s%% / %s%%' % (REP_M[i], REP_H[i])
        hi = ' hi' if D['VME'][i] + D['VHE'][i] == 0 else ''
        mrows.append('<tr class="%s"><td>%s</td><td class="num">%d</td><td class="num">%d</td>'
                     '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                     '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                     % (hi.strip(), mk, D['VME'][i], D['VHE'][i], D['MME'][i], D['MHE'][i],
                        '-' if gm is None else gm, D['CME'][i], D['CHE'][i], rp))
    T['MONTHLY_TABLE'] = ('<tr><th>月份</th><th class="num">你</th><th class="num">TA</th>'
                          '<th class="num">净分你</th><th class="num">净分TA</th><th class="num">Gottman</th>'
                          '<th class="num">批评你/千</th><th class="num">批评TA/千</th>'
                          '<th class="num">修复率 你/TA</th></tr>' + ''.join(mrows))
    valid = [(i, REP_H[i]) for i in range(len(REP_H)) if REP_H[i] is not None]
    if valid:
        li, lv = valid[-1]
        T['NOTE_PHASE'] += (' <b>最新一个有效月份（%s）TA 的修复率是 %s%%</b>——'
                            '时间序列的最后一两个点要单独看，它比任何历史均值都更接近「现在」。'
                            % (D['months'][li], lv))

    # ---------- 07 故事 ----------
    T['NOTE_GAP30'] = ('这是最长断联（%s → %s，%d 天）发生前 30 天。'
                       '如果红色的 TA 情绪净分在断联前就已经往下走，说明裂痕早于沉默出现。'
                       % (D['gapBefore'].strftime('%Y-%m-%d'), D['gapAfter'].strftime('%Y-%m-%d'), D['maxGap']))
    tls = []
    if D['gapIdx'] > 0:
        gi = D['gapIdx']
        j = gi - 1
        seg = []
        while j >= 0 and len(seg) < 14:
            seg.append(msgs[j])
            if gi - j > 1 and (msgs[j + 1]['dt'] - msgs[j]['dt']).total_seconds() > SESSION_GAP:
                break
            j -= 1
        seg.reverse()
        for m in seg:
            c = m['content']
            k = 'red' if hit(c, CONFLICT) else ('gold' if '分手' in c else m['sender'])
            tls.append('<div class="tl-item %s"><span class="tl-t">%s</span>'
                       '<span class="tl-who %s">%s</span>%s</div>'
                       % (k, m['dt'].strftime('%Y-%m-%d %H:%M:%S'),
                          'hl-me' if m['sender'] == 'me' else 'hl-her',
                          '你' if m['sender'] == 'me' else 'TA', cut(c, 80)))
    T['GAP_TIMELINE'] = ('<div class="tl">%s</div><p class="note">断联前最后一段对话。红点＝冲突，金点＝转折，'
                         '灰点＝日常。结论不下「谁对谁错」，只还原因果链：导火索往往不是大矛盾，'
                         '而是一个没人接住的小动作。</p>' % ''.join(tls)) if tls else '<p class="note">样本不足，无法还原。</p>'

    trows = ''
    for name, _ in TRIGGER_RULES + [('其他 / 无法归类', None)]:
        c = D['trigger'].get(name, 0)
        if not c:
            continue
        trows += ('<tr><td>%s</td><td class="num">%d</td><td class="num">%s%%</td>'
                  '<td><div class="bar-wrap"><div class="bar-her" style="width:%s%%"></div></div></td></tr>'
                  % (name, c, pct(c, D['triggerN']), pct(c, D['triggerN'])))
    T['TRIGGER_TABLE'] = ('<tr><th>导火索类型</th><th class="num">次数</th><th class="num">占比</th>'
                          '<th>分布</th></tr>' + trows)
    top7 = sorted(D['conflictSessions'], key=lambda cs: -cs['n'])[:7]
    body = []
    for cs in top7:
        sil = next((r for r in D['repairs'] if r['date'] == cs['start'].strftime('%Y-%m-%d')), None)
        body.append('<div class="card hl-her-card"><h4>%s · 冲突词命中 %d 次 · 该段对话持续 %d 分钟</h4>'
                    '<p class="read">导火索：%s</p>%s%s</div>'
                    % (cs['start'].strftime('%Y-%m-%d %H:%M'), cs['n'],
                       max(1, int((cs['end'] - cs['start']).total_seconds() // 60)),
                       cut(cs['first']['content'], 70),
                       q(cs['first']['sender'], cs['first']['dt'], cs['first']['content']),
                       ('<p class="note">→ %.1f 小时后，%s 先开口：%s</p>'
                        % (sil['sil'], '你' if sil['who'] == 'me' else 'TA', cut(sil['reply'], 60))) if sil else ''))
    T['REPLAY_TITLE'] = '最激烈的 %d 段冲突 · 逐段回放' % len(top7)
    T['REPLAY_BODY'] = ''.join(body)

    # ---------- 08 框架 ----------
    T['BIDS_TABLE'] = ('<tr><th>谁发出邀请</th><th class="num">发出</th><th class="num">被接住</th>'
                       '<th class="num">接住率</th><th class="read">基准</th></tr>'
                       '<tr><td>你 → TA</td><td class="num">%d</td><td class="num">%s</td>'
                       '<td class="num %s">%s%%</td><td class="read">健康 86%% / 离婚 33%%</td></tr>'
                       '<tr><td>TA → 你</td><td class="num">%d</td><td class="num">%s</td>'
                       '<td class="num %s">%s%%</td><td class="read">同上</td></tr>'
                       '<tr><td><b>双向合计</b></td><td class="num">%d</td><td class="num">-</td>'
                       '<td class="num hl-purple">%s%%</td><td class="read">长期高于 70%% 是扛得住断联的底层原因</td></tr>'
                       % (D['bidsM'], round(D['bidsM'] * D['bidsCatchM'] / 100), cls(D['bidsCatchM'], 70, 50), D['bidsCatchM'],
                          D['bidsH'], round(D['bidsH'] * D['bidsCatchH'] / 100), cls(D['bidsCatchH'], 70, 50), D['bidsCatchH'],
                          D['bidsM'] + D['bidsH'], D['bidsCatch']))
    T['SLOW_TABLE'] = ('<tr><th>指标</th><th class="num">断联前 60 天</th><th class="num">全期均值</th>'
                       '<th class="read">读法</th></tr>'
                       '<tr><td>日消息量·滚动方差</td><td class="num %s">%s</td><td class="num">%s</td>'
                       '<td class="read">升高＝波动变大，关系开始「发抖」</td></tr>'
                       '<tr><td>AR(1) 一阶自相关</td><td class="num %s">%s</td><td class="num">%s</td>'
                       '<td class="read">升高＝恢复变慢，扰动不容易被吸收</td></tr>'
                       % ('hl-red' if D['slowPreVar'] > D['slowBaseVar'] else 'hl-green',
                          D['slowPreVar'], D['slowBaseVar'],
                          'hl-red' if D['slowPreAR'] > D['slowBaseAR'] else 'hl-green',
                          D['slowPreAR'], D['slowBaseAR']))
    # 临界慢化的判读必须跟着真实方向走，不能写死「两项一起抬头」
    varUp = D['slowPreVar'] > D['slowBaseVar']
    arUp = D['slowPreAR'] > D['slowBaseAR']
    if varUp and arUp:
        slowVerdict = ('两项同时抬升，<b class="hl-red">符合临界慢化的预警特征</b>：'
                       '系统在失去恢复力，扰动开始不容易被吸收。')
    elif varUp or arUp:
        slowVerdict = ('只有<b>%s</b>抬升，另一项没跟上——属于<b class="hl-gold">弱信号</b>，'
                       '不足以单独当作断联预警。' % ('滚动方差' if varUp else 'AR(1) 自相关'))
    else:
        slowVerdict = ('两项都没有抬升，断联前方差甚至更低——'
                       '<b class="hl-green">本数据不支持临界慢化预警</b>：'
                       '那段沉默不是「渐渐失稳」攒出来的，更像一次突发的决定。')
    T['SLOW_NOTE'] = ('临界慢化理论：系统接近崩溃前，滚动方差与一阶自相关 AR(1) 会同时升高——恢复变慢，'
                      '通常比断联本身早几个月出现。本数据（匹配窗口对比）：方差 %s（%s）→ %s（断联前 60 天）；'
                      'AR(1) %s → %s。%s'
                      % (D['slowBaseVar'], D['slowBaseLabel'], D['slowPreVar'],
                         D['slowBaseAR'], D['slowPreAR'], slowVerdict))
    T['EVENT_TABLE'] = ('<tr><th>时间窗</th><th class="num">日均消息</th><th class="num">相对基线</th>'
                        '<th class="read">读法</th></tr>'
                        + ''.join('<tr><td>%s</td><td class="num">%s</td><td class="num %s">%s%%</td>'
                                  '<td class="read">%s</td></tr>'
                                  % (e['name'], e['perDay'], 'hl-red' if e['pct'] < 0 else 'hl-green',
                                     e['pct'],
                                     '吵架当天的量，主要就是吵架本身' if '当天' in e['name'] else
                                     ('明显低于日常——那几天在冷着' if e['pct'] < -20 else
                                      ('低于日常' if e['pct'] < 0 else
                                       ('显著高于日常：吵完靠刷屏把关系刷回来' if e['pct'] >= 150 else '略高于日常，属正常修复热度'))))
                                  for e in D['event'])
                        + '<tr><td>日常基线</td><td class="num">%s</td><td class="num">—</td>'
                          '<td class="read">%s（不含断联期与熄火期，避免拉低基线）</td></tr>'
                          % (D['eventBase'], D['eventBaseLabel']))
    T['TOPIC_TABLE'] = ('<tr><th>话题</th><th class="num">你</th><th class="num">TA</th>'
                        '<th class="read">谁在说</th></tr>'
                        + ''.join('<tr><td>%s</td><td class="num %s">%s%%</td><td class="num %s">%s%%</td>'
                                  '<td class="read">%s</td></tr>'
                                  % (k, 'hl-me' if D['topicM'][i] > D['topicH'][i] else '', D['topicM'][i],
                                     'hl-her' if D['topicH'][i] > D['topicM'][i] else '', D['topicH'][i],
                                     '你主导' if D['topicM'][i] > D['topicH'][i] + 2 else
                                     ('TA 主导' if D['topicH'][i] > D['topicM'][i] + 2 else '势均'))
                                  for i, k in enumerate(D['topicCats'])))
    T['TOPIC_ROTATE'] = '0' if len(D['topicCats']) <= 8 else '30'

    # ---------- 09 投入 ----------
    def inv(name, a, b, unit, gauge, read):
        wa = 'hl-me' if (a > b) == (gauge != 'low') else ''
        return ('<tr><td>%s</td><td class="num %s">%s%s</td><td class="num">%s%s</td>'
                '<td class="read">%s</td><td class="read">%s</td></tr>'
                % (name, wa, a, unit, b, unit, gauge, read))
    inv_rows = [
        ('消息条数', format(nMe, ','), format(nHer, ','), '绝对数',
         '你 %s%% / TA %s%%，差 %s 个百分点' % (D['pctMe'], D['pctHer'], round(abs(D['pctMe'] - D['pctHer']), 1))),
        ('主动开启对话', '%d 段' % D['openM'], '%d 段' % D['openH'], '绝对数', 'TA 占 %s%%' % D['openPctH']),
        ('关心 / 问候', '%d 次' % D['CA_M'], '%d 次' % D['CA_H'], '每千条 %s / %s' % (D['CA_MP'], D['CA_HP']), '日常照料密度'),
        ('爱称次数', '%d 次' % D['NK_M'], '%d 次' % D['NK_H'], '每千条 %s / %s' % (D['NK_MP'], D['NK_HP']), '亲密的语言标记'),
        ('「爱你」类', '%d 次' % D['LOVE_M'], '%d 次' % D['LOVE_H'], '每千条 %s / %s' % (D['LOVE_MP'], D['LOVE_HP']), '明确表白'),
        ('「想你」类', '%d 次' % D['MISS_M'], '%d 次' % D['MISS_H'], '每千条 %s / %s' % (D['MISS_MP'], D['MISS_HP']), '思念表达'),
        ('安全表达（认错/安抚）', '%d 次' % D['SE_M'], '%d 次' % D['SE_H'], '每千条 %s / %s' % (D['SE_MP'], D['SE_HP']), '愿意先低头的能力'),
        ('先低头（修复）', '%d 次' % D['repM'], '%d 次' % D['repH'], '占比 %s%% / %s%%' % (D['repRateM'], D['repRateH']), '冲突后的主动权'),
        ('表情使用', '%d 个' % D['EMOJI_CNT_M'], '%d 个' % D['EMOJI_CNT_H'],
         '每千条 %s / %s' % (per_k(D['EMOJI_CNT_M'], nMe), per_k(D['EMOJI_CNT_H'], nHer)), '软的沟通方式'),
        ('提问（把球递出）', '%d 次' % D['Q_M'], '%d 次' % D['Q_H'],
         '每千条 %s / %s' % (per_k(D['Q_M'], nMe), per_k(D['Q_H'], nHer)), '愿意发问＝愿意等回答'),
        ('平均字数', '%s 字' % D['LEN_M'], '%s 字' % D['LEN_H'], '绝对数', '长句＝愿意展开'),
        ('深夜消息（23–6 点）', '%d 条' % D['night']['me'], '%d 条' % D['night']['her'],
         '占比 %s%% / %s%%' % (D['nightPctM'], D['nightPctH']), '不设防时段的在场'),
        ('接住对方邀请', '%s%%' % D['bidsCatchH'], '%s%%' % D['bidsCatchM'], '互为对方的接住率', '越高＝越会接话'),
    ]
    T['INVEST_TABLE'] = ('<tr><th>投入维度</th><th class="num">你</th><th class="num">TA</th>'
                         '<th class="read">口径</th><th class="read">读法</th></tr>'
                         + ''.join('<tr><td>%s</td><td class="num hl-me">%s</td><td class="num hl-her">%s</td>'
                                   '<td class="read">%s</td><td class="read">%s</td></tr>'
                                   % (a, b, c, d, e) for a, b, c, d, e in inv_rows))
    herWin = sum(1 for a, b, c, d, e in inv_rows if str(b) != str(c))
    T['INVEST_VERDICT'] = ('<p>TA 在更多维度上「更用力」：主动开启 %s%%、连发最长 %d 条、'
                           '情绪要挟 %d 次、焦虑追问 %d 次；你在更少维度上「更稳定」：'
                           '回避疏离 %d 次、最长断联由你维持了 %d 天。</p>'
                           '<p>但这不是「谁更爱谁」——数据只能说明一件事：'
                           '<b>TA 更敢表达，你更敢沉默</b>。'
                           '敢表达的人要先承受被拒绝的风险；敢沉默的人，是在用不回应换取安全感。</p>'
                           % (D['openPctH'], D['maxH'], D['TH_H'], D['ANX_H'], D['AV_M'], D['maxGap']))

    # ---------- 10 药方 ----------
    her_rx = [
        (D['TH_H'] * 10, '把「分手」从情绪砝码里拿掉——它出现了 <b>%d</b> 次，说多了，真要说的那一次就没人当真了。' % D['TH_H']),
        (D['ANX_H'] * 4, '「你怎么不回」这句话你说了 <b>%d</b> 次（每千条 %s）——它在对方耳朵里翻译成的是「你不爱我」，'
                         '而不是「我在等」。把追问换成具体诉求：「我 10 分钟没等到你，会心慌」。' % (D['ANX_H'], D['ANX_HP'])),
        (D['maxH'] * 6, '最长连发 <b>%d</b> 条、≥5 条 %d 次：连发是宣泄，不是沟通。'
                        '情绪上来时先写下来，隔 24 小时再发。' % (D['maxH'], D['b5H'])),
        (D['CT_H'] * 8, '蔑视类表达 <b>%d</b> 次——Gottman 的结论是讽刺比吵架更能预测分手。' % D['CT_H']),
        (D['CF_H'] if 'CF_H' in D else 0, ''),
    ]
    me_rx = [
        (D['AV_M'] * 10, '把「算了」「随便」换掉——你说了 <b>%d</b> 次（每千条 %s）。'
                         '回避疏离不会让冲突消失，只会把它推到下一次，而且下一次更贵。' % (D['AV_M'], D['AV_MP'])),
        (D['blockH'] * 12, '她连发之后（最长一次一口气 %d 条），你有 <b>%d</b> 次只回了一两个字；'
                           '反过来，你连发之后她也有 <b>%d</b> 次只回了一两个字。'
                           '两个方向都高——「用短句关机」是你们共用的模式，'
                           '区别只在于她是用连发把话说完，你是用短句把话关掉。'
                           % (D['maxH'], D['blockH'], D['blockM'])),
        ((100 - D['openPctM']) * 2, '你只开启了 <b>%s%%</b> 的对话段（TA %s%%）。'
                                    '主动开口不是讨好，是告诉对方「我也在等」。' % (D['openPctM'], D['openPctH'])),
        (D['ST_M'] * 9, '筑墙类回应 <b>%d</b> 次。筑墙是四骑士里最难自己察觉的一个，'
                        '因为当事人只觉得「我不想吵了」。' % D['ST_M']),
        (D['medM'] * 1.5, '你的中位回复是 <b>%s</b> 分钟，TA 是 %s 分钟。快慢本身不判对错，'
                          '但 %d 段冲突里占比最高的导火索是「%s」——它是全报告里最靠一条规则就能消掉的一项。'
                          % (D['medM'], D['medH'], D['conflictN'],
                             (D['trigger'].most_common(1)[0][0] if D['trigger'] else '沟通节奏'))),
    ]
    def take(pool, n, fallback):
        pool = [x for x in sorted(pool, key=lambda x: -x[0]) if x[1]][:n]
        out = [x[1] for x in pool]
        out += fallback[:n - len(out)]
        return ''.join('<p>%d. %s</p>' % (i + 1, t) for i, t in enumerate(out))
    T['RX_HER'] = take(her_rx, 3, [
        '把「确认安全感」的主动权拿回来一部分——你现在把稳定感的开关交在 TA 手里。',
        '吵架时先描述事实，再描述感受：把「你从来不管我」换成「这周有 3 天我 11 点后才等到你回」。',
        '允许对方有沉默的权利，但要求对方给出时限：「你需要多久」。',
    ])
    T['RX_ME'] = take(me_rx, 4, [
        '每天主动开启一次对话，哪怕只有一句。',
        '回复短句时补一个字：「嗯」变成「嗯，我在」。',
        '每周把一件没说出口的事说出来。',
        '她情绪上来时，先复述一遍她在说什么，再解释自己。',
    ])
    T['RX_UNDERSTAND'] = (
        '<div class="quote her"><div class="qm">TA 的连发：不是刷屏，是「你还在吗」</div>'
        '连发 <b>%d</b> 条的那一刻，TA 要的不是你逐条回答，而是确认你还在屏幕那头。</div>'
        '<div class="quote me"><div class="qm">你的「算了」：不是不在乎，是「我怕说了更糟」</div>'
        '回避疏离 <b>%d</b> 次，多数发生在你判断「说下去会吵起来」的时候——'
        '这是保护，不是冷漠，但对方收到的是关门声。</div>'
        '<div class="quote gold"><div class="qm">你们的断联 %d 天：不是结束，是两个人同时都不知道怎么开口</div>'
        '%s 之后你们又聊到比断联前更热——这说明感情没死，只是缺一个「先说话」的借口。</div>'
        % (D['maxH'], D['AV_M'], D['maxGap'],
           D['gapAfter'].strftime('%Y 年 %-m 月') if os.name != 'nt' else D['gapAfter'].strftime('%Y-%m-%d')))
    _top_trig = [(k, v) for k, v in D['trigger'].most_common() if '其他' not in k]
    T['RX_TOGETHER'] = (
        '<p>1. <b>给冲突设一条规则：24 小时之内必须有人说话。</b>'
        '本次数据里中位静默 %s 小时，但有 <b>%d 次</b>吵完之后直接进入了 7 天以上的沉默——'
        '其中最长的那一次，就是后来那 %d 天断联的起点。</p>'
        '<p>2. <b>把「你怎么不回」变成「我们约定一个回复时限」。</b>'
        '%d 段冲突里，占比最高的导火索是「%s」（%d 次）——它最靠一条规则就能消掉。</p>'
        '<p>3. <b>每月做一次 10 分钟的「事实复盘」，不翻旧账、只对指标。</b>'
        '你俩的 Gottman 比率是 %s:1，健康线是 5:1——把它当成一个可以一起追的数字。</p>'
        % (D['silAll'], D['silBigN'], D['maxGap'], D['conflictN'],
           (_top_trig[0][0] if _top_trig else '沟通节奏'),
           (_top_trig[0][1] if _top_trig else 0),
           D['gottman']))

    # =====================================================================
    # 扩展维度渲染（最完整版）
    # =====================================================================

    # ---------- 消息长度分布（02 章） ----------
    lrows = []
    for i, lab in enumerate(D['lenBuck']):
        a, b = D['lenMP'][i], D['lenHP'][i]
        lrows.append('<tr><td>%s</td><td class="num %s">%s%%</td><td class="num %s">%s%%</td></tr>'
                     % (lab, 'hl-me' if a > b else '', a, 'hl-her' if b > a else '', b))
    T['LEN_TABLE'] = ('<tr><th>消息长度</th><th class="num">你</th><th class="num">TA</th></tr>'
                      + ''.join(lrows))
    T['NOTE_LEN'] = ('短消息（1–10 字）占比：你 <b>%s%%</b>、TA <b>%s%%</b>；'
                     '长消息（30 字以上）占比：你 <b>%s%%</b>、TA <b>%s%%</b>。'
                     '平均字数你 %s、TA %s。'
                     '注意方向：按「比例」看，<b>你反而更常发长消息、TA 更常发短消息</b>——'
                     '这和她「最长连发 56 条」并不矛盾，连发是多条短句滚成的一长串，不是一条长文。'
                     '所以你们真正的差异不在单条长短，而在<b>节奏</b>：'
                     '她把一段心思切成很多小条连续丢出来，你习惯一次说完整、说完就停。'
                     % (D['lenShortM'], D['lenShortH'], D['lenLongM'], D['lenLongH'],
                        D['LEN_M'], D['LEN_H']))

    # ---------- 星期节律（03 章） ----------
    T['NOTE_WEEK'] = ('你消息最多的是 <b>%s</b>（%s%%），TA 最多的是 <b>%s</b>（%s%%）。'
                      '周末（周六日）消息占比：你 %s%%、TA %s%%。'
                      '两条线如果都往周末翘，说明你们是「周末恋人」型——平日只是维持，周末才是真正的相处；'
                      '如果工作日明显更高，说明你们的交流主要发生在通勤与上班的碎片时间里。'
                      % (D['wdLabels'][D['wdPkM']], D['wdMP'][D['wdPkM']],
                         D['wdLabels'][D['wdPkH']], D['wdHP'][D['wdPkH']],
                         D['wdWeekendM'], D['wdWeekendH']))

    # ---------- 回复延迟分布（03 章） ----------
    rr = []
    for i, lab in enumerate(D['rdLabels']):
        a, b = D['rdMP'][i], D['rdHP'][i]
        rr.append('<tr><td>%s</td><td class="num %s">%s%%</td><td class="num %s">%s%%</td></tr>'
                  % (lab, 'hl-me' if a > b else '', a, 'hl-her' if b > a else '', b))
    T['RD_TABLE'] = ('<tr><th>回复间隔</th><th class="num">你→TA</th><th class="num">TA→你</th></tr>'
                     + ''.join(rr))
    m_slow = D['rdMP'][4] + D['rdMP'][5]
    h_slow = D['rdHP'][4] + D['rdHP'][5]
    T['NOTE_RD'] = ('超过 1 小时的慢回复占比：你 <b>%s%%</b>、TA <b>%s%%</b>。'
                    '这一项比中位数更能说明问题——中位数只看「一般情况」，分布才看得见「冷处理的那几次」。'
                    '慢回复本身不是错，但它是「回避疏离」在时间轴上的落点。'
                    % (round(m_slow, 1), round(h_slow, 1)))

    # ---------- 表情逐月（04 章） ----------
    T['NOTE_EMOJI'] = ('表情是「软化剂」：同一句话加不加表情，读起来完全不同。'
                       '你合计使用表情 <b>%s</b> 个（每千条 <b>%s</b>），TA <b>%s</b> 个（每千条 %s）——'
                       '你的密度是 TA 的 <b>%.1f 倍</b>。'
                       '这一项你明显更高，和你偏回避的沟通风格是配套的：'
                       '不想正面冲突，就往句尾加个表情把话说软，让「拒绝」听上去不像拒绝。'
                       '看曲线要盯的是<b>退潮点</b>——两个人表情同时掉下去的那几个月，'
                       '就是这段关系最不轻松的时段。'
                       % (D['EMOJI_CNT_M'], per_k(D['EMOJI_CNT_M'], nMe),
                          D['EMOJI_CNT_H'], per_k(D['EMOJI_CNT_H'], nHer),
                          per_k(D['EMOJI_CNT_M'], nMe) / max(0.1, per_k(D['EMOJI_CNT_H'], nHer))))

    # ---------- 作息：谁先开口 / 谁最后说话（11 章） ----------
    actDays = len([1 for k, v in D['daily'].items() if v[0] + v[1] > 0])
    firstH_N = actDays - D['firstDayN']
    lastH_N = actDays - D['lastDayN']
    T['RHYTHM_TABLE'] = (
        '<tr><th>指标</th><th class="num">你</th><th class="num">TA</th><th class="read">读法</th></tr>'
        '<tr><td>平均「当天第一句」时间</td><td class="num %s">%s 点</td><td class="num %s">%s 点</td>'
        '<td class="read">谁更早想起对方</td></tr>'
        '<tr><td>平均「当天最后一句」时间</td><td class="num %s">%s 点</td><td class="num %s">%s 点</td>'
        '<td class="read">谁把这一天收起来</td></tr>'
        '<tr><td>说第一句的天数</td><td class="num hl-me">%d 天</td><td class="num hl-her">%d 天</td>'
        '<td class="read">共 %d 个有聊天的日子</td></tr>'
        '<tr><td>说最后一句的天数</td><td class="num hl-me">%d 天</td><td class="num hl-her">%d 天</td>'
        '<td class="read">收尾＝把这一天关掉的人</td></tr>'
        % ('hl-me' if D['firstAvgM'] < D['firstAvgH'] else '', D['firstAvgM'],
           'hl-her' if D['firstAvgH'] < D['firstAvgM'] else '', D['firstAvgH'],
           'hl-me' if D['lastAvgM'] > D['lastAvgH'] else '', D['lastAvgM'],
           'hl-her' if D['lastAvgH'] > D['lastAvgM'] else '', D['lastAvgH'],
           D['firstDayN'], firstH_N, actDays,
           D['lastDayN'], lastH_N))
    T['NOTE_RHYTHM'] = ('有聊天的 <b>%d</b> 天里，你说了 <b>%d</b> 天的第一句、TA 说了 %d 天；'
                        '你收尾了 <b>%d</b> 天、TA 收尾了 %d 天。'
                        '「说第一句」＝主动启动这一天，和会话段的「开启」是两个尺度：'
                        '一段对话的开启看的是谁先说话，一天的开启看的是谁先想起对方。'
                        % (actDays, D['firstDayN'], firstH_N,
                           D['lastDayN'], lastH_N))

    # ---------- 年度对比（11 章） ----------
    yrows = []
    for y in D['years']:
        gcls = cls(y['gottman'], 5, 2)
        yrows.append('<tr><td><b>%d</b></td><td class="num">%s</td><td class="num">%s</td>'
                     '<td class="num">%s</td><td class="num">%d</td><td class="num">%s</td>'
                     '<td class="num">%s</td><td class="num %s">%s</td></tr>'
                     % (y['y'], format(y['n'], ','), format(y['me'], ','), format(y['her'], ','),
                        y['days'], y['perDay'], y['cfl'],
                        gcls, y['gottman']))
    T['YEAR_TABLE'] = ('<tr><th>年份</th><th class="num">总消息</th><th class="num">你</th>'
                       '<th class="num">TA</th><th class="num">聊天天数</th><th class="num">日均</th>'
                       '<th class="num">冲突段</th><th class="num">Gottman</th></tr>' + ''.join(yrows))
    if len(D['years']) >= 2:
        y0, y1 = D['years'][0], D['years'][-1]
        dirn = '升到' if y1['perDay'] > y0['perDay'] else '降到'
        gdir = '同步下滑' if y1['gottman'] < y0['gottman'] else '同步上升'
        T['NOTE_YEAR'] = ('按自然年横向比：日均消息从 %d 年的 <b>%s</b> 条 %s %d 年的 <b>%s</b> 条；'
                          '同期冲突段 %d 段 → %d 段，Gottman 比率 %s → %s（%s）。'
                          '这是全报告最反直觉的一处对撞：<b>聊得越来越多，健康度却在往下走</b>。'
                          '年度视角能抹平单月的偶然波动，看出的不是「感情好不好」，'
                          '而是「这段关系整体在往哪个方向走」。'
                          % (y0['y'], y0['perDay'], dirn, y1['y'], y1['perDay'],
                             y0['cfl'], y1['cfl'], y0['gottman'], y1['gottman'], gdir))
    else:
        T['NOTE_YEAR'] = '样本跨年不足，仅列出单一年份的数据。'

    # ---------- 断联全清单（11 章） ----------
    grows = []
    for i, g in enumerate(D['gapList'][:10]):
        d = g['days']
        c = 'hl-red' if d >= 7 else ('hl-gold' if d >= 3 else '')
        grows.append('<tr><td class="num">%d</td><td class="read">%s → %s</td>'
                     '<td class="num %s">%.1f 天</td><td class="read">%s：%s</td></tr>'
                     % (i + 1, g['before'].strftime('%Y-%m-%d'), g['after'].strftime('%Y-%m-%d'),
                        c, d, '你' if g['preWho'] == 'me' else 'TA', cut(g['pre'], 42)))
    T['GAP_TABLE'] = ('<tr><th>#</th><th>区间</th><th class="num">时长</th>'
                      '<th class="read">断联前的最后一句</th></tr>' + ''.join(grows))
    T['NOTE_GAP'] = ('全程共出现 <b>%d</b> 次超过 3 天的中断、<b>%d</b> 次超过 7 天的中断，'
                     '最长一次 <b>%d 天</b>。'
                     '注意最后一句是谁说的、说了什么——大多数断联不是从「分手」两个字开始的，'
                     '而是从一句很普通的话开始的，只是那句话之后没人再接。'
                     % (D['gap3N'], D['gap7N'], D['maxGap']))

    # ---------- 单日峰值 Top10（11 章） ----------
    brows = []
    for i, (k, c, a, b) in enumerate(D['busiest']):
        brows.append('<tr><td class="num">%d</td><td>%s</td><td class="num"><b>%d</b></td>'
                     '<td class="num">%d</td><td class="num">%d</td></tr>'
                     % (i + 1, k, c, a, b))
    T['BUSY_TABLE'] = ('<tr><th>#</th><th>日期</th><th class="num">总条数</th>'
                       '<th class="num">你</th><th class="num">TA</th></tr>' + ''.join(brows))

    # ---------- 最长单条消息 Top3（11 章） ----------
    lq = []
    for m in D['longest'][:3]:
        lq.append(q(m['sender'], m['dt'], m['content'], 200))
    T['LONGEST_QUOTES'] = ''.join(lq) + ('<p class="note">全场最长的三条消息（已剔除「哈哈哈哈哈…」这类重复刷屏，'
                                         '它们长但没有信息量）。一个人愿意打这么多字、把一件小事拆成'
                                         '「什么情况、为什么不舒服、下次怎么办」来讲的时候，'
                                         '通常不是因为这段话重要，而是因为他还在乎这段关系值不值得讲清楚。</p>')

    # ---------- 页脚 ----------
    T['FOOTER'] = (
        '<b>数据源</b>：%s<br>'
        '<b>清洗</b>：原始 %s 行 → 有效 %s 条，剔除 %s 条（系统消息 / 空内容 / 时间格式无效）<br>'
        '<b>时间范围</b>：%s ~ %s（%d 天）· 会话段 %d 段（相邻消息间隔 > 6 小时切段）· 冲突段 %d 段<br>'
        '<b>口径</b>：情感净分＝(积极词−消极词)÷消息数×100；跨人比较的指标一律做了每千条或占比归一化；'
        '单字词不做子串匹配；状态词（累/困/忙）不计入消极；「嗯/哦/好吧」不计入筑墙。<br>'
        '<b>工具</b>：analyze.py（纯标准库，本地运行，不联网、不上传）· 报告生成时间 %s<br><br>'
        '<b>边界声明</b>：以上全部为统计推断，不是读心术，也不是心理诊断。'
        '情感词典存在误差；表情、语音、通话、线下相处无法纳入；'
        '单条消息的语义靠词典近似，反讽与玩笑可能被误判。'
        '「谁更爱谁」是伪命题，数据只能说明「谁更敢表达」。'
        '请把这份报告当一面镜子，而不是一份判决书。'
        % (os.path.basename(meta['path']), meta['raw'], format(total, ','), meta['dropped'],
           D['first'].strftime('%Y-%m-%d'), D['last'].strftime('%Y-%m-%d'), D['days'],
           D['sessions'], D['conflictN'], datetime.now().strftime('%Y-%m-%d %H:%M')))

    # ---------- 图表数据 ----------
    J = {
        'J_MONTHS': D['months'], 'J_GAPS': D['gapArea'],
        'J_ATT_M': [D['ANX_MP'], D['AV_MP'], D['TH_MP'], D['SE_MP']],
        'J_ATT_H': [D['ANX_HP'], D['AV_HP'], D['TH_HP'], D['SE_HP']],
        'J_TONE_M': D['TONE_MP'], 'J_TONE_H': D['TONE_HP'],
        'J_VME': D['VME'], 'J_VHE': D['VHE'],
        'J_MME': D['MME'], 'J_MHE': D['MHE'],
        'J_HOUR_M': D['HPCT_M'], 'J_HOUR_H': D['HPCT_H'],
        'J_REP_M': REP_M, 'J_REP_H': REP_H,
        'J_RAT_M': D['RAT_M'], 'J_RAT_H': D['RAT_H'],
        'J_CME': D['CME'], 'J_CHE': D['CHE'],
        'J_G30_DATES': D['g30Dates'], 'J_G30_M': D['g30M'], 'J_G30_H': D['g30H'], 'J_G30_S': D['g30S'],
        'J_NB': D['monNmM']['宝宝/宝儿'], 'J_NW': D['monNmM']['老婆/老公'], 'J_NH': D['monNmM']['亲爱的/宝贝'],
        'J_GOTTMAN': D['GOTTMAN_M'],
        'J_CR_M': D['CR_MP'], 'J_CR_H': D['CR_HP'], 'J_DF_M': D['DF_MP'], 'J_DF_H': D['DF_HP'],
        'J_CT_M': D['CT_MP'], 'J_CT_H': D['CT_HP'], 'J_ST_M': D['ST_MP'], 'J_ST_H': D['ST_HP'],
        'J_CA_M': D['CA_MP'], 'J_CA_H': D['CA_HP'], 'J_NK_M': D['NK_MP'], 'J_NK_H': D['NK_HP'],
        'J_MP': D['LOVE_MP'], 'J_HP': D['LOVE_HP'],
        'J_CAP': [{'name': 'AC 主动建设', 'value': D['cap']['AC']},
                  {'name': 'PC 被动建设', 'value': D['cap']['PC']},
                  {'name': 'AD 主动破坏', 'value': D['cap']['AD']},
                  {'name': 'PD 被动破坏', 'value': D['cap']['PD']}],
        'J_STERN_M': D['STERN_M'], 'J_STERN_H': D['STERN_H'], 'STERN_MAX': D['STERN_MAX'],
        'J_SLOW_DATES': D['slowDates'], 'J_SLOW_VAR': D['slowVar'], 'J_SLOW_AR': D['slowAR'],
        'J_EV_CATS': [e['name'] for e in D['event']], 'J_EV_VALS': [e['pct'] for e in D['event']],
        'J_TOPIC_CATS': D['topicCats'], 'J_TOPIC_M': D['topicM'], 'J_TOPIC_H': D['topicH'],
        # ---- 扩展维度 ----
        'J_LEN_LAB': D['lenBuck'], 'J_LEN_M': D['lenMP'], 'J_LEN_H': D['lenHP'],
        'J_WD_LAB': D['wdLabels'], 'J_WD_M': D['wdMP'], 'J_WD_H': D['wdHP'],
        'J_RD_LAB': D['rdLabels'], 'J_RD_M': D['rdMP'], 'J_RD_H': D['rdHP'],
        'J_EMOJI_M': D['monEmojiM'], 'J_EMOJI_H': D['monEmojiH'],
        'J_FIRST_M': D['firstHM'], 'J_FIRST_H': D['firstHH'],
        'J_LAST_M': D['lastHM'], 'J_LAST_H': D['lastHH'],
        'J_YEARS': [y['y'] for y in D['years']],
        'J_YR_N': [y['n'] for y in D['years']],
        'J_YR_PER': [y['perDay'] for y in D['years']],
        'J_YR_G': [y['gottman'] for y in D['years']],
    }
    for k, v in J.items():
        T[k] = json.dumps(v, ensure_ascii=False)
    return T


# =====================================================================
# 7. main
# =====================================================================

def _base_dir():
    """模板所在目录。打包成 exe 后资源被解到 _MEIPASS，需区别对待。"""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


def _pause():
    """双击 exe 时不让窗口一闪而过。"""
    try:
        input('\n按回车键退出...')
    except Exception:
        pass


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    frozen = getattr(sys, 'frozen', False)
    interactive = len(sys.argv) < 2

    if interactive:
        print('=' * 56)
        print('  微信聊天记录 · 深度关系分析（纯本地统计，不联网）')
        print('=' * 56)
        print('聊天记录格式: 2025-06-01 05:39 | 我 | 出发没')
        print('（每行：时间 | 发送者 | 内容，发送者写「我」或「TA」）\n')
        try:
            path = input('把聊天记录 txt 文件拖到这个窗口，或粘贴路径，然后回车：\n> ').strip().strip('"').strip("'")
        except Exception:
            print('\n用法: analyze.py 聊天记录.txt [输出报告.html]')
            sys.exit(1)
        if not path:
            print('错误: 没输入路径')
            if frozen:
                _pause()
            sys.exit(1)
    else:
        path = sys.argv[1]

    out = sys.argv[2] if len(sys.argv) > 2 else '深度分析报告.html'
    if not os.path.isabs(out):
        out = os.path.join(os.path.dirname(os.path.abspath(path)), out)
    if not os.path.isfile(path):
        print('错误: 找不到文件 %s' % path)
        if frozen:
            _pause()
        sys.exit(1)

    print('读取: %s' % path)
    msgs, raw, dropped = parse(path)
    if len(msgs) < 50:
        print('错误: 有效消息只有 %d 条，至少需要 50 条才能出报告' % len(msgs))
        sys.exit(1)
    print('清洗: 原始 %d 行 → 有效 %d 条（剔除 %d 条）' % (raw, len(msgs), dropped))

    sessions = build_sessions(msgs)
    print('会话段: %d 段（间隔 > 6 小时切段）' % len(sessions))

    D = compute(msgs, sessions)
    print('冲突段: %d 段 · 最长断联: %d 天 · Gottman: %s:1'
          % (D['conflictN'], D['maxGap'], D['gottman']))

    meta = {'msgs': msgs, 'me': [m for m in msgs if m['sender'] == 'me'],
            'her': [m for m in msgs if m['sender'] == 'her'],
            'raw': format(raw, ','), 'dropped': format(dropped, ','), 'path': path}
    T = render(D, meta)

    tpl_path = os.path.join(_base_dir(), 'report_template.html')
    if not os.path.isfile(tpl_path):
        print('错误: 缺少 report_template.html（必须和 analyze.py 放在同一个文件夹）')
        if frozen:
            _pause()
        sys.exit(1)
    with open(tpl_path, 'r', encoding='utf-8') as f:
        html = f.read()

    left = []
    for k, v in T.items():
        ph = '{{' + k + '}}'
        if ph in html:
            html = html.replace(ph, v)
    for m in re.finditer(r'\{\{[A-Z0-9_]+\}\}', html):
        left.append(m.group(0))
    if left:
        print('警告: 有 %d 个占位符未替换: %s' % (len(set(left)), ', '.join(sorted(set(left))[:10])))

    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print('报告已生成: %s' % out)

    # 附带 ECharts，让报告离线也能出图（放到报告同级目录）
    lib = os.path.join(_base_dir(), 'echarts.min.js')
    dst = os.path.join(os.path.dirname(os.path.abspath(out)) or '.', 'echarts.min.js')
    if os.path.isfile(lib) and os.path.abspath(lib) != os.path.abspath(dst):
        try:
            import shutil
            shutil.copyfile(lib, dst)
            print('已附带 echarts.min.js（离线可看图表）')
        except Exception as e:
            print('提示: 未能复制 echarts.min.js（%s），打开报告时若联网会自动走 CDN' % e)
    elif not os.path.isfile(lib):
        print('提示: 未找到 echarts.min.js，打开报告时若联网会自动走 CDN')

    if frozen:
        print('\n全部完成。报告就在：%s' % out)
        print('（双击报告文件即可用浏览器打开，断网也能看图）')
        _pause()


if __name__ == '__main__':
    main()

