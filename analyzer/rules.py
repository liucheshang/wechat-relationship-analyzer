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
POS_WORDS = """开心 高兴 喜欢 爱 想你 宝贝 宝宝 老公 老婆 谢谢 好呀 哈哈 嘿嘿 棒 赞
可爱 漂亮 帅 舒服 幸福 温暖 感动 期待 终于 太好了 不错 没问题 加油 亲亲 抱抱 么么
喜欢你 爱你 在乎 心疼 厉害 优秀 贴心 温柔""".split()

NEG_WORDS = """生气 讨厌 不想 分手 算了 无语 失望 难过 委屈 哭 愤怒 争吵 吵架 冷战
不理 随便 糟糕 烦死 气死 伤心 崩溃 绝望 后悔 厌恶 嫌弃 受不了 够了 滚开
我不开心 不高兴 没必要""".split()

PHRASES_NEG = ["你总是", "你从不", "凭什么", "你开心就好", "不想理你", "别管我",
               "别说了", "我不开心", "懒得说", "随便你吧"]

CONFLICT_WORDS = """分手 吵架 生气 讨厌 算了 无语 失望 难过 委屈 冷战 不理 随便
道歉 对不起 解释 凭什么 你总是 你从不""".split()

LOVE_WORDS = ["爱你", "喜欢你", "想你", "宝贝", "宝宝", "老公", "老婆", "么么", "亲亲",
              "抱抱", "晚安", "早安", "在乎", "心疼"]
FUTURE_WORDS = ["以后", "下次", "一起", "将来", "未来", "计划", "旅行", "旅游",
                "见家长", "结婚", "买房", "同居", "我们"]
COMPLAINT_WORDS = ["你总是", "你从不", "你能不能", "你怎么", "你就不会", "凭什么",
                   "你应该", "你必须", "每次你"]
DEFENSE_WORDS = ["不是我", "那是因为", "我没有", "我也没办法", "你也", "你不也",
                 "我不是故意", "本来就是"]
CONTEMPT_WORDS = ["你可真行", "随便你", "无所谓", "笑死", "幼稚", "可笑", "你开心就好",
                  "就这", "也不看看", "真行"]
STONEWALL_WORDS = ["不想说", "不说了", "别讲", "懒得说", "没什么好说",
                   "随你怎么想", "爱信不信"]
CARE_WORDS = ["累吗", "吃饭了吗", "睡了吗", "在干嘛", "多喝水", "注意身体", "早点睡",
              "冷不冷", "饿不饿", "开心吗", "怎么了", "不舒服吗", "没事吧"]
NICKNAMES = ["宝贝", "宝宝", "乖乖", "亲爱的", "老公", "老婆", "猪猪",
             "老婆大人", "老公大人", "哈尼", "达令"]

for w in ['宝儿', '宝宝', '老婆', '老公', '想你', '爱你', '亲亲', '抱抱', '么么', '乖乖']:
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
