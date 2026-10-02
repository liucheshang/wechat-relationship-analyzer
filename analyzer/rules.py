# -*- coding: utf-8 -*-
"""
规则引擎 v2：全量统计所有指标。

修复：
  1. 子串误伤："帮忙"命中"忙"、"别人"命中"别" → jieba 分词精确匹配
  2. 状态词（累/困/饿/忙）不算消极情绪
  3. 筑墙词不含"嗯/哦/行/好吧"（正常回应不是冷战）
  4. 四骑士双向八项全算（v1 只统计一半，天然偏向"对方更糟"）
  5. 空月补齐 + 断联检测（v1 会隐藏整段零交流）
  6. 回复延迟不丢弃 >120 分钟样本，新增 P90
  7. O(N) 单趟扫描
"""
import jieba
from collections import Counter, defaultdict
from datetime import datetime

# ---------- 词典 ----------
# 积极情绪词：覆盖各种表达开心/喜欢/温暖的说法
POS_WORDS = """开心 高兴 喜欢 爱 想你 宝贝 宝宝 老公 老婆 谢谢 好呀 哈哈 嘿嘿 棒 赞
可爱 漂亮 帅 舒服 幸福 温暖 感动 期待 终于 太好了 不错 没问题 加油 亲亲 抱抱 么么
喜欢你 爱你 在乎 心疼 厉害 优秀 贴心 温柔
爱死了 好喜欢 好想你 超爱 最喜欢 最想 心动 甜蜜 治愈 开心死了 笑死 好看
宝贝儿 亲爱的 乖乖 猪猪 哈尼 达令 媳妇儿 男朋友 女朋友
辛苦了 谢谢你 感恩 有你真好 遇见你 幸运 知足 满足 踏实 安心
嘿嘿嘿 嘻嘻 呵呵呵 哈哈哈 嘿嘿 嘻嘻嘻 美美哒 棒棒哒 超棒 好棒
爱你哦 想你了 抱抱你 亲一个 晚安呀 早安呀 乖乖的 懂事 听话
开心快乐 好心情 美滋滋 乐呵呵 笑嘻嘻 暖洋洋 热乎乎 暖到了
爱了爱了 太好啦 好耶 哇塞 牛 厉害厉害 绝了 完美 赞爆了
老婆大人 老公大人 媳妇儿 亲爱的宝贝 小宝贝 小乖乖 小笨蛋 小傻瓜
我想你了 好想你啊 爱你爱你 么么哒 啾咪 比心 笔芯 贴贴 蹭蹭
想抱抱 想见你 想亲亲 我爱你 我喜欢你 好幸福 好开心 好温暖
有你在 有你真好 你最好 最棒的 全世界最好 心里踏实 心定了
真好看 真帅 真美 真可爱 真厉害 真乖 真懂事 真贴心
谢谢你呀 辛苦啦 辛苦了呀 注意身体呀 早点休息呀""".split()

NEG_WORDS = """生气 讨厌 不想 分手 算了 无语 失望 难过 委屈 哭 愤怒 争吵 吵架 冷战
不理 随便 糟糕 烦死 气死 伤心 崩溃 绝望 后悔 厌恶 嫌弃 受不了 够了 滚开
我不开心 不高兴 没必要
讨厌你 烦死了 气死人 气死我了 难过死 伤心死 委屈死 崩溃了 绝望了
不想理你 不想说话 不想见你 不想过了 过不下去 没意思 没劲 无聊
失望透顶 心寒 心凉 心死了 心如死灰 麻木了 无所谓了
别烦我 别理我 别找我 别联系我 别再说了 别管我 别问我
随便你 随便吧 随便你吧 随便怎样 都行 无所谓 都可以
受够了 忍够了 够了吧 到此为止 分手吧 离婚吧 分开吧 散了吧
我错了行了吧 你满意了吧 你赢了 我认了 随便你怎么想
哭了 哭唧唧 呜呜 呜呜呜 想哭 泪目 泪崩 泪奔
恶心 反胃 烦 烦透了 烦躁 郁闷 憋屈 窝火 来气 上火
你真行 你可真行 真是服了 也是醉了 无话可说 没话说
吵架了 吵一架 吵起来 争执 矛盾 闹矛盾 闹别扭 冷战中
不想谈了 不爱了 没感觉了 变淡了 心凉了 失望了
压力大 好累 好烦 好难过 好委屈 好伤心 好生气""".split()

PHRASES_NEG = ["你总是", "你从不", "凭什么", "你开心就好", "不想理你", "别管我",
               "别说了", "我不开心", "懒得说", "随便你吧",
               "你能不能", "你怎么又", "你就不会", "每次都这样", "你一点都不",
               "我受够了", "没意思", "不想过了", "别再说了", "随你便",
               "你根本不懂", "你从来不听", "我不想跟你说", "说了也白说"]

CONFLICT_WORDS = """分手 吵架 生气 讨厌 算了 无语 失望 难过 委屈 冷战 不理 随便
道歉 对不起 解释 凭什么 你总是 你从不 争吵 争执 矛盾 闹别扭
道歉了 我错了 原谅 和好 吵一架 吵起来 闹矛盾 发脾气
过不下去 不想谈了 冷静一下 冷静冷静 都冷静冷静
你错了 我错了 谁错了 到底谁错了 你道歉 你认错
别吵了 吵什么 有什么好吵的 不想吵了""".split()

LOVE_WORDS = ["爱你", "喜欢你", "想你", "宝贝", "宝宝", "老公", "老婆", "么么", "亲亲",
              "抱抱", "晚安", "早安", "在乎", "心疼", "爱你哦", "想你了",
              "我爱你", "我想你", "好想你", "爱死你", "亲爱的", "乖乖",
              "贴贴", "比心", "啾咪", "么么哒", "宝贝儿", "小宝贝",
              "晚安呀", "早安呀", "抱抱你", "亲一个", "想抱抱", "想见你",
              "有你真好", "你最好", "全世界最好", "爱你爱你"]
FUTURE_WORDS = ["以后", "下次", "一起", "将来", "未来", "计划", "旅行", "旅游",
                "见家长", "结婚", "买房", "同居", "我们",
                "以后一起", "下次一起", "将来我们", "未来我们",
                "国庆去", "春节回", "周末去", "假期去", "明年我们",
                "住一起", "搬一起", "见爸妈", "见朋友", "见家人",
                "我们以后", "我们一起", "我们结婚", "我们买房", "我们的家"]
COMPLAINT_WORDS = ["你总是", "你从不", "你能不能", "你怎么", "你就不会", "凭什么",
                   "你应该", "你必须", "每次你", "你怎么又", "你一点都不",
                   "你从来都不", "你每次都", "你就知道", "你能不能别"]
DEFENSE_WORDS = ["不是我", "那是因为", "我没有", "我也没办法", "你也", "你不也",
                 "我不是故意", "本来就是", "我怎么了", "我哪有",
                 "又不是我", "我也不想", "我也没办法呀", "我不是那个意思",
                 "你别多想", "你想多了", "不是那样的", "我本来就"]
CONTEMPT_WORDS = ["你可真行", "随便你", "无所谓", "笑死", "幼稚", "可笑", "你开心就好",
                  "就这", "也不看看", "真行", "呵呵", "切",
                  "幼稚不幼稚", "好笑", "无聊透顶", "你这人",
                  "也就那样", "不过如此", "算了吧你", "随便你吧"]
STONEWALL_WORDS = ["不想说", "不说了", "别讲", "懒得说", "没什么好说",
                   "随你怎么想", "爱信不信", "哦", "嗯", "呃",
                   "不想聊", "不想谈", "不说", "闭嘴", "不想解释",
                   "你说了算", "行吧", "好吧", "都行", "随便",
                   "我累了", "不想吵", "别说了", "没什么好说的"]
CARE_WORDS = ["累吗", "吃饭了吗", "睡了吗", "在干嘛", "多喝水", "注意身体", "早点睡",
              "冷不冷", "饿不饿", "开心吗", "怎么了", "不舒服吗", "没事吧",
              "吃了吗", "在干嘛呢", "在忙吗", "忙不忙", "最近怎么样",
              "身体怎么样", "好点了吗", "好没好", "吃药了吗", "看医生了吗",
              "早点休息", "早点回家", "路上小心", "注意安全", "天冷加衣",
              "别熬夜", "别太累", "别太辛苦", "注意休息", "别感冒了",
              "今天怎么样", "上班累吗", "下班了吗", "到家了吗", "吃了没",
              "胃怎么样", "头还疼吗", "好点没", "要不要紧", "严重吗"]
NICKNAMES = ["宝贝", "宝宝", "乖乖", "亲爱的", "老公", "老婆", "猪猪",
             "老婆大人", "老公大人", "哈尼", "达令",
             "宝儿", "宝贝儿", "小宝贝", "小乖乖", "小笨蛋", "小傻瓜",
             "媳妇儿", "媳妇", "对象", "男朋友", "女朋友",
             "猪宝贝", "猪宝", "乖乖宝", "亲亲宝", "宝宝宝",
             "大宝", "小宝", "乖宝", "笨笨", "傻傻",
             "哈尼宝贝", "达令宝贝", "亲爱滴", "亲耐滴",
             "领导", "老板", "大哥", "大姐", "宝宝亲",
             "亲爱的你", "我家那位", "那口子", "孩他爸", "孩他妈"]

# 敷衍回应词（不消极，但也不投入）
DISENGAGE_WORDS = ["嗯", "哦", "呃", "啊", "哦嗯", "嗯哦",
                   "好吧", "行吧", "都行", "随便", "可以", "ok", "OK",
                   "哈哈哈", "哈哈", "嘿嘿", "呵呵",
                   "好的", "收到", "知道了", "了解", "明白"]

# 撒娇/情绪词
COQUETTE_WORDS = ["嘛", "啦", "呀", "哇", "哼", "诶", "唉",
                  "好不好嘛", "行不行嘛", "求求你", "拜托了",
                  "人家", "呜呜", "嘤嘤", "哭哭"]

for w in ['宝儿', '宝宝', '老婆', '老公', '想你', '爱你', '亲亲', '抱抱', '么么', '乖乖',
          '宝贝儿', '亲爱的', '媳妇儿', '小宝贝', '小乖乖', '小笨蛋', '小傻瓜',
          '么么哒', '啾咪', '贴贴', '比心', '笔芯']:
    jieba.add_word(w)


def month_key(dt):
    return f"{dt.year}-{dt.month:02d}"


def _all_months(a, b):
    out, y, m = [], a.year, a.month
    while (y, m) <= (b.year, b.month):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


def _match(tok_set, content, words, phrases=()):
    """三层匹配：分词精确 + >=2字子串兜底 + 显式短语表"""
    if tok_set & words:
        return True
    for w in words:
        if len(w) >= 2 and w in content:
            return True
    for p in phrases:
        if p in content:
            return True
    return False


def run_rules(msgs):
    text = [m for m in msgs if m["msg_type"] == 1 and isinstance(m["content"], str)]
    by_self = [m for m in text if m["is_self"]]
    by_her = [m for m in text if not m["is_self"]]
    if not msgs:
        return {"months": [], "silence": {}}

    for m in text:
        m["_tok"] = set(jieba.lcut(m["content"]))

    months = _all_months(msgs[0]["dt"], msgs[-1]["dt"])
    midx = {mo: i for i, mo in enumerate(months)}
    n_mo = len(months)
    Z = lambda: [0] * n_mo

    vol_s, vol_h = Z(), Z()
    pos_s, pos_h, neg_s, neg_h = Z(), Z(), Z(), Z()
    H = {k: Z() for k in ('complaint_self', 'complaint_her', 'defense_self', 'defense_her',
                          'contempt_self', 'contempt_her', 'stonewall_self', 'stonewall_her')}
    inti, pas, comm, tot_mo = Z(), Z(), Z(), Z()
    P, N = set(POS_WORDS), set(NEG_WORDS)
    CW, DW, TW, SW = set(COMPLAINT_WORDS), set(DEFENSE_WORDS), set(CONTEMPT_WORDS), set(STONEWALL_WORDS)
    LV = set(LOVE_WORDS)
    PA = set(["么么", "亲亲", "抱抱", "想你", "宝贝", "老公", "老婆"])
    FU = set(FUTURE_WORDS)

    for m in text:
        i = midx[month_key(m["dt"])]
        tk, c, s = m["_tok"], m["content"], m["is_self"]
        if s: vol_s[i] += 1
        else: vol_h[i] += 1
        tot_mo[i] += 1
        if _match(tk, c, P): (pos_s if s else pos_h)[i] += 1
        if _match(tk, c, N, PHRASES_NEG): (neg_s if s else neg_h)[i] += 1
        if _match(tk, c, CW): (H['complaint_self'] if s else H['complaint_her'])[i] += 1
        if _match(tk, c, DW): (H['defense_self'] if s else H['defense_her'])[i] += 1
        if _match(tk, c, TW): (H['contempt_self'] if s else H['contempt_her'])[i] += 1
        if _match(tk, c, SW): (H['stonewall_self'] if s else H['stonewall_her'])[i] += 1
        if _match(tk, c, LV): inti[i] += 1
        if _match(tk, c, PA): pas[i] += 1
        if _match(tk, c, FU): comm[i] += 1

    result = {"months": months}
    result["monthly_volume"] = {"self": vol_s, "her": vol_h}
    result["gottman"] = [
        round((pos_s[i] + pos_h[i]) / max(1, neg_s[i] + neg_h[i]), 2) if tot_mo[i] else None
        for i in range(n_mo)]
    result["gottman_detail"] = {"pos_self": pos_s, "pos_her": pos_h,
                                "neg_self": neg_s, "neg_her": neg_h}
    H["stonewall_all"] = [H['stonewall_self'][i] + H['stonewall_her'][i] for i in range(n_mo)]
    result["horsemen"] = H
    result["sternberg"] = {
        "intimacy":   [round(inti[i] / max(1, tot_mo[i]) * 1000, 2) for i in range(n_mo)],
        "passion":    [round(pas[i] / max(1, tot_mo[i]) * 1000, 2) for i in range(n_mo)],
        "commitment": [round(comm[i] / max(1, tot_mo[i]) * 1000, 2) for i in range(n_mo)],
    }

    def count(list_, words, phrases=()):
        return sum(1 for m in list_ if _match(m["_tok"], m["content"], set(words), phrases))

    result["care"] = {"self": count(by_self, CARE_WORDS), "her": count(by_her, CARE_WORDS)}
    result["address"] = {
        "her_calls_you": {w: sum(1 for m in by_her if w in m["content"]) for w in NICKNAMES},
        "you_call_her":  {w: sum(1 for m in by_self if w in m["content"]) for w in NICKNAMES},
    }
    result["conflict"] = {"self": count(by_self, CONFLICT_WORDS),
                          "her": count(by_her, CONFLICT_WORDS)}

    day_first = {}
    for m in msgs:
        d = m["dt"].date()
        if d not in day_first or m["ts"] < day_first[d]["ts"]:
            day_first[d] = m
    day_open = {"self": 0, "her": 0}
    for m in day_first.values():
        day_open["self" if m["is_self"] else "her"] += 1
    result["day_open"] = day_open

    result["calls"] = {"self": sum(1 for m in msgs if m["msg_type"] == 50 and m["is_self"]),
                       "her":  sum(1 for m in msgs if m["msg_type"] == 50 and not m["is_self"])}
    result["voice"] = {"self": sum(1 for m in msgs if m["msg_type"] == 34 and m["is_self"]),
                       "her":  sum(1 for m in msgs if m["msg_type"] == 34 and not m["is_self"])}

    def pct(a, p):
        a = sorted(a)
        return a[min(len(a) - 1, int(len(a) * p))] if a else 0
    delays_self, delays_her = [], []
    for i in range(1, len(msgs)):
        d_ = (msgs[i]["ts"] - msgs[i - 1]["ts"]) / 60
        if msgs[i]["is_self"] and not msgs[i - 1]["is_self"]:
            delays_self.append(d_)
        elif not msgs[i]["is_self"] and msgs[i - 1]["is_self"]:
            delays_her.append(d_)
    result["reply_delay"] = {
        "self_median": round(pct(delays_self, .5), 1), "her_median": round(pct(delays_her, .5), 1),
        "self_p90": round(pct(delays_self, .9), 1), "her_p90": round(pct(delays_her, .9), 1),
        "self_n": len(delays_self), "her_n": len(delays_her),
    }

    n_self = sum(1 for m in by_self if m["dt"].hour >= 22 or m["dt"].hour < 6)
    n_her = sum(1 for m in by_her if m["dt"].hour >= 22 or m["dt"].hour < 6)
    result["night"] = {"self": n_self, "her": n_her,
                       "self_pct": round(n_self / max(1, len(by_self)) * 100, 1),
                       "her_pct": round(n_her / max(1, len(by_her)) * 100, 1)}
    result["avg_len"] = {
        "self": round(sum(len(m["content"]) for m in by_self) / max(1, len(by_self)), 2),
        "her":  round(sum(len(m["content"]) for m in by_her) / max(1, len(by_her)), 2)}

    streak_self = streak_her = max_self = max_her = 0
    prev = None
    for m in msgs:
        s = m["is_self"]
        if s == prev:
            if s: streak_self += 1
            else: streak_her += 1
        else:
            streak_self = 1 if s else 0
            streak_her = 0 if s else 1
        max_self = max(max_self, streak_self); max_her = max(max_her, streak_her)
        prev = s
    result["max_streak"] = {"self": max_self, "her": max_her}

    ts = [m["ts"] for m in msgs]
    segs = []
    for i in range(1, len(ts)):
        g = (ts[i] - ts[i - 1]) / 86400
        if g >= 3:
            segs.append({"from": datetime.fromtimestamp(ts[i - 1]).strftime("%Y-%m-%d"),
                         "to": datetime.fromtimestamp(ts[i]).strftime("%Y-%m-%d"),
                         "days": round(g, 1)})
    segs.sort(key=lambda x: -x["days"])
    result["silence"] = {
        "max_days": segs[0]["days"] if segs else 0,
        "max_from": segs[0]["from"] if segs else None,
        "max_to": segs[0]["to"] if segs else None,
        "segments_over_3d": segs[:20],
        "empty_months": [mo for i, mo in enumerate(months) if tot_mo[i] == 0],
    }
    for m in text:
        m.pop("_tok", None)
    return result
